import requests
import json
import time
from utils import parse_float
from datetime import datetime, timedelta
from pytz import timezone
from modelos import Integracao
from sqlalchemy.orm import Session

class ApiDeye:
    base_url = "https://us1-developer.deyecloud.com/v1.0/"
    cache_expiry = 600 # 10 minutos
    headers_login = {
        'Content-Type': 'application/json'
    }
    
    def __init__(self, integracao: Integracao, db: Session):
        self.db = db
        self.integracao = integracao

        self.username = integracao.username
        self.password = integracao.senha
        self.appid = integracao.appid
        self.appsecret = integracao.appsecret
        self.companyId = integracao.companyid  # ← caso você queira usar dinamicamente
        self.accesstoken = None
        self.last_token_time = 0
        self.cached_data = None
        self.last_cache_time = 0
        self.session = requests.Session()
        self._geracao_cache = None
        self._geracao_cache_timestamp = None



    def autenticar(self):
        """
        Verifica se já há token válido salvo no banco.
        Caso contrário, faz:
        1. login sem companyId,
        2. obtém companyId,
        3. login com companyId,
        4. salva token final e companyId no banco.
        """
        TOKEN_EXPIRACAO_SEGUNDOS = 7200  # 2 horas

        # ✅ 1. Verifica se já existe um token válido no banco
        if self.integracao.token_acesso and self.integracao.token_updated_at:
            tempo_passado = (datetime.utcnow() - self.integracao.token_updated_at).total_seconds()
            if tempo_passado < TOKEN_EXPIRACAO_SEGUNDOS:
                print("✅ Token Deye válido encontrado no banco — reutilizando")
                self.accesstoken = self.integracao.token_acesso
                return self.accesstoken

        print("🔁 Nenhum token válido — iniciando nova autenticação Deye")

        # 2. Primeiro login sem companyId
        url_login_inicial = self.base_url + f"account/token?appId={self.appid}"
        body_inicial = {
            "appSecret": self.appsecret,
            "email": self.username,
            "password": self.password
        }

        resp_inicial = self.session.post(url_login_inicial, json=body_inicial, headers=self.headers_login)
        if resp_inicial.status_code != 200:
            print("❌ Erro no primeiro login Deye:", resp_inicial.status_code)
            print(resp_inicial.text)
            return None

        token_temporario = resp_inicial.json().get("accessToken")
        if not token_temporario:
            print("❌ Token temporário ausente na resposta inicial.")
            return None

        # 3. Obter companyId
        url_info = self.base_url + "account/info"
        headers_info = {
            "Authorization": f"Bearer {token_temporario}",
            "Content-Type": "application/json"
        }

        resp_info = self.session.post(url_info, headers=headers_info)
        if resp_info.status_code != 200:
            print("❌ Erro ao buscar companyId:", resp_info.status_code)
            print(resp_info.text)
            return None

        orgs = resp_info.json().get("orgInfoList", [])
        if not orgs:
            print("⚠️ Nenhum companyId encontrado.")
            return None

        company_id = str(orgs[0].get("companyId"))
        print("🏢 companyId obtido:", company_id)

        # 4. Login final com companyId
        body_final = {
            "appSecret": self.appsecret,
            "email": self.username,
            "password": self.password,
            "companyId": company_id
        }

        resp_final = self.session.post(url_login_inicial, json=body_final, headers=self.headers_login)
        if resp_final.status_code != 200:
            print("❌ Erro no login final com companyId:", resp_final.status_code)
            print(resp_final.text)
            return None

        token_final = resp_final.json().get("accessToken")
        if not token_final:
            print("❌ Erro ao obter token final.")
            return None

        # 5. Salvar token e companyId no banco
        self.integracao.companyid = company_id
        self.integracao.token_acesso = token_final
        self.integracao.token_updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(self.integracao)

        self.accesstoken = token_final
        self.last_token_time = time.time()

        print("✅ Autenticação Deye concluída com sucesso — novo token salvo")
        return token_final


    def get_usinas(self):
        # 🔐 Garante token válido com fluxo completo
        if not self.autenticar():
            return []

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {self.accesstoken}"
        }

        if self.cached_data and time.time() - self.last_cache_time < self.cache_expiry:
            return self.cached_data

        url = self.base_url + "station/list"
        body = {
            "page": 1,
            "size": 50,
        }

        response = self.session.post(url, json=body, headers=headers)
        if response.status_code != 200:
            print("❌ Erro ao buscar usinas:", response.status_code, response.text)
            return []

        dados = response.json()
        dados_usinas = []

        try:
            for usina in dados.get("stationList", []):
                today_energy = 0.0
                try:
                    hoje = datetime.now(timezone("America/Sao_Paulo")).strftime("%Y-%m-%d")
                    amanha = (datetime.now(timezone("America/Sao_Paulo")) + timedelta(days=1)).strftime("%Y-%m-%d")

                    url_energy = self.base_url + "station/history"
                    body_energy = {
                        "stationId": usina.get("id"),
                        "startAt": hoje,
                        "endAt": amanha,
                        "granularity": 2,
                    }

                    response_energy = self.session.post(url_energy, json=body_energy, headers=headers)
                    if response_energy.status_code == 200:
                        energy_data = response_energy.json()
                        items = energy_data.get("stationDataItems", [])
                        if items:
                            today_energy = round(float(items[0].get("generationValue", 0.0)), 2)

                except Exception as e:
                    print(f"⚠️ Erro ao buscar today_energy para usina {usina.get('id')}: {e}")

                try:
                    curr_power = float(usina.get("generationPower", 0))
                except (ValueError, TypeError):
                    curr_power = 0.0

                try:
                    capacidade = float(usina.get("installedCapacity", 0))
                except (ValueError, TypeError):
                    capacidade = 0.0

                # Mapear connectionStatus para ps_fault_status
                raw_status = usina.get("connectionStatus", "").upper()
                if raw_status == "NORMAL":
                    fault_status = 3
                elif raw_status == "ALARM":
                    fault_status = 2
                elif raw_status == "ERROR" or raw_status == "ALL_OFFLINE":
                    fault_status = 1
                else:
                    fault_status = 0

                dados_usinas.append({
                    "ps_id": usina.get("id"),
                    "ps_name": usina.get("name"),
                    "location": usina.get("locationAddress", ""),
                    "curr_power": curr_power,
                    "total_energy": 0.0,
                    "today_energy": today_energy,
                    "capacidade": capacidade,
                    "co2_total": 0.0,
                    "income_total": 0.0,
                    "ps_fault_status": fault_status,
                })

        except Exception as e:
            print("❌ Erro ao processar dados das usinas:", e)
            return []

        self.cached_data = dados_usinas
        self.last_cache_time = time.time()
        return dados_usinas

    
    # OBTENDO PS_KEYS E SERIAL NUMBER E DEMAIS DADOS

    def get_geracao(self):
        print("Chamando get_geracao() para Deye 🚀")
        brasil = timezone("America/Sao_Paulo")
        agora = datetime.now(brasil)

        # 🔁 Cache local (10 minutos)
        if self._geracao_cache and self._geracao_cache_timestamp:
            if (agora - self._geracao_cache_timestamp) < timedelta(minutes=10):
                print("🔁 Retornando geração do cache local")
                return self._geracao_cache

        # 🔐 Garante token atualizado e válido
        if not self.autenticar():
            return []

        usinas = self.get_usinas()
        if not usinas:
            return []

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {self.accesstoken}"
        }

        # Datas para os 3 períodos
        hoje = agora.strftime("%Y-%m-%d")
        ontem = (agora - timedelta(days=1)).strftime("%Y-%m-%d")
        anteontem = (agora - timedelta(days=2)).strftime("%Y-%m-%d")
        sete_dias_atras = (agora - timedelta(days=8)).strftime("%Y-%m-%d")
        trinta_dias_atras = (agora - timedelta(days=31)).strftime("%Y-%m-%d")

        diario = []
        setedias = []
        mensal = []

        for usina in usinas:
            ps_id = usina.get("ps_id")
            if not ps_id:
                continue

            url = self.base_url + "station/history"

            body_diario = {
                "stationId": ps_id,
                "startAt": anteontem,
                "endAt": ontem,
                "granularity": 2
            }

            body_7dias = {
                "stationId": ps_id,
                "startAt": sete_dias_atras,
                "endAt": ontem,
                "granularity": 2
            }

            body_30dias = {
                "stationId": ps_id,
                "startAt": trinta_dias_atras,
                "endAt": ontem,
                "granularity": 2
            }

            try:
                # Diária
                res_d = self.session.post(url, json=body_diario, headers=headers)
                if res_d.status_code == 200:
                    data = res_d.json()
                    items = data.get("stationDataItems", [])
                    if items:
                        v = round(float(items[0].get("generationValue", 0.0)), 2)
                        diario.append({"ps_id": ps_id, "data": ontem, "energia_gerada_kWh": v})

                # 7 dias
                res_7 = self.session.post(url, json=body_7dias, headers=headers)
                if res_7.status_code == 200:
                    data = res_7.json()
                    items = data.get("stationDataItems", [])
                    soma_7 = round(sum(float(p.get("generationValue", 0.0)) for p in items), 2)
                    setedias.append({"ps_id": ps_id, "periodo": f"{sete_dias_atras} a {ontem}", "energia_gerada_kWh": soma_7})

                # 30 dias
                res_30 = self.session.post(url, json=body_30dias, headers=headers)
                if res_30.status_code == 200:
                    data = res_30.json()
                    items = data.get("stationDataItems", [])
                    soma_30 = round(sum(float(p.get("generationValue", 0.0)) for p in items), 2)
                    mensal.append({"ps_id": ps_id, "periodo": f"{trinta_dias_atras} a {ontem}", "energia_gerada_kWh": soma_30})

            except Exception as e:
                import traceback
                print(f"❌ Erro ao consultar usina {ps_id}: {e}")
                traceback.print_exc()
                continue

        total_30dias = sum(item["energia_gerada_kWh"] for item in mensal)

        resultado = {
            "diario": diario,
            "setedias": setedias,
            "mensal": {
                "total": round(total_30dias, 2),
                "por_usina": mensal
            }
        }

        self._geracao_cache = resultado
        self._geracao_cache_timestamp = agora

        print("✅ Geração Deye salva em cache")
        return resultado
