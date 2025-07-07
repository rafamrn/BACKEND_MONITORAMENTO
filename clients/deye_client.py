import requests
import json
import time
from utils import parse_float
from datetime import datetime, timedelta
from pytz import timezone
from sqlalchemy.orm import Session
from modelos import Integracao


class ApiDeye:
    base_url = "https://us1-developer.deyecloud.com/v1.0/"
    cache_expiry = 600 # 10 minutos
    headers_login = {
        'Content-Type': 'application/json'
    }

    def __init__(self, db: Session, integracao: Integracao):
        self.db = db
        self.integracao = integracao

        self.username = integracao.username
        self.password = integracao.senha
        self.appid = integracao.appid
        self.appsecret = integracao.appsecret
        self.companyId = integracao.companyid  # ← pode já vir do banco

        self.accesstoken = integracao.token_acesso
        self.last_token_time = time.mktime(integracao.token_updated_at.timetuple()) if integracao.token_updated_at else 0

        self.session = requests.Session()
        self.cached_data = None
        self.last_cache_time = 0
        self._geracao_cache = None
        self._geracao_cache_timestamp = None

        self.headers_login = {
            'Content-Type': 'application/json'
        }

        self.db.refresh(self.integracao)

        # Passo 1: Login inicial sem companyId
        print("🔐 Iniciando login inicial Deye (sem companyId)...")
        self.fazer_login(incluir_company_id=False)

        # Passo 2: Buscar companyId, se não estiver no banco
        if not self.companyId:
            print("🔎 Buscando companyId da conta Deye...")
            company_id = self.obter_company_id()
            if company_id:
                self.companyId = company_id
                self.integracao.companyid = str(company_id)
                self.db.commit()
                print(f"🏢 CompanyId armazenado: {company_id}")
            else:
                print("⚠️ Não foi possível obter o companyId da Deye.")

        # Passo 3: Login final com companyId
        if self.companyId:
            print("🔐 Efetuando login final Deye com companyId...")
            self.fazer_login(incluir_company_id=True)



    def fazer_login(self, incluir_company_id=False):
        if self.accesstoken and (time.time() - self.last_token_time < self.cache_expiry):
            return self.accesstoken  # Reutiliza token válido

        url = self.base_url + f"account/token?appId={self.appid}"
        body = {
            "appSecret": self.appsecret,
            "email": self.username,
            "password": self.password,
        }

        if incluir_company_id and self.companyId:
            body["companyId"] = self.companyId

        response = self.session.post(url, json=body, headers=self.headers_login)

        if response.status_code != 200:
            print("Erro ao autenticar na API Deye:", response.status_code)
            print(response.text)
            return None

        dados = response.json()

        try:
            self.accesstoken = dados["accessToken"]
            self.last_token_time = time.time()

            # Atualiza no banco o novo token e hora
            self.integracao.token_acesso = self.accesstoken
            self.integracao.token_updated_at = datetime.utcnow()
            self.db.commit()

            print("🔐 Token Deye obtido com sucesso:", self.accesstoken)
            return self.accesstoken
        except KeyError:
            print("Erro ao extrair token Deye:", dados)
            return None


    def obter_company_id(self):
        token = self.fazer_login()
        if not token:
            print("❌ Token não obtido. Impossível buscar companyId.")
            return None

        url = self.base_url + "v1.0/account/info"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        response = self.session.get(url, headers=headers)

        if response.status_code != 200:
            print("❌ Erro ao obter informações da conta:", response.status_code)
            print(response.text)
            return None

        dados = response.json()

        try:
            orgs = dados["orgInfoList"]
            if not orgs:
                print("⚠️ Nenhuma organização encontrada.")
                return None

            company_id = orgs[0]["companyId"]
            company_name = orgs[0].get("companyName", "")
            print(f"🏢 Company ID: {company_id} | Nome: {company_name}")
            self.companyId = company_id
            # Salva no banco de dados
            self.integracao.companyid = str(company_id)
            self.db.commit()
            self.db.refresh(self.integracao)
            return company_id
        except (KeyError, IndexError) as e:
            print("⚠️ Erro ao extrair companyId:", dados)
            return None

    def get_usinas(self):
        # Garante token válido (refaz login se necessário)
        token = self.fazer_login()
        if not token:
            print("❌ Falha ao autenticar para buscar usinas.")
            return []

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {self.accesstoken}"
        }

        # Usa cache local se válido
        if self.cached_data and time.time() - self.last_cache_time < self.cache_expiry:
            return self.cached_data

        url = self.base_url + "station/list"
        body = {
            "page": 1,
            "size": 50
        }

        response = self.session.post(url, json=body, headers=headers)
        if response.status_code != 200:
            print("❌ Erro ao buscar usinas:", response.status_code, response.text)
            return []

        try:
            dados = response.json()
            lista = dados.get("stationList", [])
        except Exception as e:
            print("❌ Erro ao interpretar resposta da listagem de usinas:", e)
            return []

        dados_usinas = []

        for usina in lista:
            today_energy = 0.0
            try:
                hoje = datetime.now(timezone("America/Sao_Paulo")).strftime("%Y-%m-%d")
                amanha = (datetime.now(timezone("America/Sao_Paulo")) + timedelta(days=1)).strftime("%Y-%m-%d")

                url_energy = self.base_url + "station/history"
                body_energy = {
                    "stationId": usina.get("id"),
                    "startAt": hoje,
                    "endAt": amanha,
                    "granularity": 2
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

            # Mapeia o status da usina
            raw_status = usina.get("connectionStatus", "").upper()
            if raw_status == "NORMAL":
                fault_status = 3
            elif raw_status == "ALARM":
                fault_status = 2
            else:
                fault_status = 1  # Para ERROR, ALL_OFFLINE ou outros

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

        self.cached_data = dados_usinas
        self.last_cache_time = time.time()
        return dados_usinas

    
    # OBTENDO PS_KEYS E SERIAL NUMBER E DEMAIS DADOS

    def get_geracao(self):
        print("Chamando get_geracao() para Deye 🚀")
        fuso = timezone("America/Sao_Paulo")
        agora = datetime.now(fuso)

        # Usa cache local se válido
        if self._geracao_cache and self._geracao_cache_timestamp:
            if (agora - self._geracao_cache_timestamp) < timedelta(minutes=10):
                print("🔁 Retornando geração do cache diário")
                return self._geracao_cache

        # Garante token válido
        if not self.fazer_login():
            return []

        usinas = self.get_usinas()
        if not usinas:
            return []

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {self.accesstoken}"
        }

        # Datas de referência
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

            bodies = {
                "diario": {
                    "stationId": ps_id,
                    "startAt": anteontem,
                    "endAt": ontem,
                    "granularity": 2
                },
                "sete_dias": {
                    "stationId": ps_id,
                    "startAt": sete_dias_atras,
                    "endAt": ontem,
                    "granularity": 2
                },
                "trinta_dias": {
                    "stationId": ps_id,
                    "startAt": trinta_dias_atras,
                    "endAt": ontem,
                    "granularity": 2
                }
            }

            try:
                # 📆 Geração Diária
                res_d = self.session.post(url, json=bodies["diario"], headers=headers)
                if res_d.status_code == 200:
                    dados = res_d.json()
                    items = dados.get("stationDataItems", [])
                    if items:
                        v = round(float(items[0].get("generationValue", 0.0)), 2)
                        diario.append({
                            "ps_id": ps_id,
                            "data": ontem,
                            "energia_gerada_kWh": v
                        })

                # 📅 Geração 7 dias
                res_7 = self.session.post(url, json=bodies["sete_dias"], headers=headers)
                if res_7.status_code == 200:
                    dados = res_7.json()
                    items = dados.get("stationDataItems", [])
                    soma_7 = round(sum(float(item.get("generationValue", 0.0)) for item in items), 2)
                    setedias.append({
                        "ps_id": ps_id,
                        "periodo": f"{sete_dias_atras} a {ontem}",
                        "energia_gerada_kWh": soma_7
                    })

                # 📆 Geração 30 dias
                res_30 = self.session.post(url, json=bodies["trinta_dias"], headers=headers)
                if res_30.status_code == 200:
                    dados = res_30.json()
                    items = dados.get("stationDataItems", [])
                    soma_30 = round(sum(float(item.get("generationValue", 0.0)) for item in items), 2)
                    mensal.append({
                        "ps_id": ps_id,
                        "periodo": f"{trinta_dias_atras} a {ontem}",
                        "energia_gerada_kWh": soma_30
                    })

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

        # Atualiza cache
        self._geracao_cache = resultado
        self._geracao_cache_timestamp = agora

        print("✅ Geração Deye salva em cache")
        return resultado
