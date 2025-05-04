import requests
import json
import time
from utils import parse_float
from datetime import datetime, timedelta
from pytz import timezone
from typing import Optional


class ApiSolarCloud:
    base_url = "https://gateway.isolarcloud.com.hk/openapi/"
    appkey = "03A0E186C87230B4DE9E028F90491A58"
    headers = {
        "Content-Type": "application/json",
        "x-access-key": "4ey7zficrz2np518aqku2a8997ha1ebz",
        "sys_code": "901"
    }

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.token = None
        self.usinas_cache = None
        self.token_cache = None
        self.token_timestamp = None
        self.usinas_timestamp = None
        self.session = requests.Session()
        self._geracao_cache = None
        self._geracao_cache_timestamp = None
        self.geracao7_cache = None
        

    def login_solarcloud(self):
        if self.token_cache and time.time() - self.token_timestamp < 600:  # 10 minutos de cache
            return self.token_cache
        
        url = self.base_url + "login"
        body = {
            "appkey": self.appkey,
            "user_password": self.password,
            "user_account": self.username
        }
        response = self.session.post(url, json=body, headers=self.headers)
        if response.status_code != 200:
            print("Erro no login:", response.status_code, response.text)
            return None
        dados = response.json()
        try:
            self.token = dados["result_data"]["token"]
            self.token_cache = self.token
            self.token_timestamp = time.time()
        except KeyError:
            print("Token não encontrado na resposta:", dados)
            return None
        print("Novo token SUNGROW obtido:", self.token)
        return self.token

    def _post_with_auth(self, url, body):
        if not self.token_cache:
            self.login_solarcloud()

        body["token"] = self.token_cache
        response = self.session.post(url, json=body, headers=self.headers)

        if response.status_code in (401, 403):  # token expirado ou inválido
            print("Token expirado ou inválido. Renovando...")
            self.token_cache = None
            self.login_solarcloud()
            body["token"] = self.token_cache
            response = self.session.post(url, json=body, headers=self.headers)

        return response

    def get_usinas(self):
        if self.usinas_cache and time.time() - self.usinas_timestamp < 600:  # Cache de usinas por 10 minutos
            return self.usinas_cache

        url = self.base_url + "getPowerStationList"
        body = {
            "curPage": 1,
            "appkey": self.appkey,
            "size": 100,
            "lang": "_pt_BR"
        }

        response = self._post_with_auth(url, body)
        if response.status_code != 200:
            print("Erro ao buscar usinas:", response.status_code, response.text)
            return []

        dados = response.json()
        dados_usinas = []

        try:
            for usina in dados["result_data"]["pageList"]:
                # Sempre pegue o ps_fault_status aqui, fora de qualquer try
                ps_fault_status = usina.get("ps_fault_status", None)

                # Trata o valor de potência
                curr_power_raw = usina.get("curr_power", {}).get("value", "0")
                today_energy_raw = usina.get("today_energy", {}).get("value","0")
                try:
                    curr_power_str = str(curr_power_raw).replace(".", "")  # Remove pontos separadores
                    curr_power_float = float(curr_power_str)
                    curr_power_kw = curr_power_float  # Tudo convertido de W para kW
                except (ValueError, TypeError):
                    curr_power_kw = 0

                dados_usinas.append({
                    "ps_id": usina.get("ps_id"),
                    "curr_power": curr_power_kw,
                    "ps_name": usina.get("ps_name"),
                    "location": usina.get("ps_location"),
                    "capacidade": usina.get("total_capcity", {}).get("value", "0"),
                 "total_energy": usina.get("total_energy", {}).get("value", "0"),
                 "today_energy": parse_float(today_energy_raw),
                 "co2_total": usina.get("co2_reduce_total", {}).get("value"),
                 "income_total": usina.get("total_income", {}).get("value"),
                 "ps_fault_status": ps_fault_status
    })


                
        except KeyError as e:
            print("Erro ao acessar dados da resposta:", e)
            return []

        self.usinas_cache = dados_usinas
        self.usinas_timestamp = time.time()

        return dados_usinas

# OBTENDO PS_KEYS E SERIAL NUMBER E DEMAIS DADOS
    

    def get_geracao(self, period: Optional[str] = None, date: Optional[str] = None, plant_id: Optional[int] = None):
        print("Chamando get_geracao() no Railway 🚀")
        brasil = timezone("America/Sao_Paulo")
        agora = datetime.now(brasil)

        if period == "day" and date and plant_id:
            if not self.token_cache:
                self.login_solarcloud()

            if not self.usinas_cache:
                self.get_usinas()

            print(f"🔍 Buscando geração do dia {date} para plant_id={plant_id}")
            return self.get_geracao_dia(data=date, plant_id=plant_id)

        # Demais chamadas padrão da dashboard (sem filtro específico)
        if self._geracao_cache and self._geracao_cache_timestamp:
            if (agora - self._geracao_cache_timestamp) < timedelta(minutes=10):
                print("🔁 Retornando geração do cache diário")
                return {
                    "diario": self._geracao_cache,
                    "setedias": self.geracao7_cache or []
                }

        if not self.token_cache:
            self.login_solarcloud()

        if not self.usinas_cache:
            self.get_usinas()

        self.anteontem = (agora - timedelta(days=2)).strftime("%Y%m%d")
        self.ontem = (agora - timedelta(days=1)).strftime("%Y%m%d")
        sete_dias_atras = (agora - timedelta(days=8)).strftime("%Y%m%d")
        self.mes_atras = (agora - timedelta(days=31)).strftime("%Y%m%d")


        # ✅ Lógica de cache para resposta padrão da dashboard
        if self._geracao_cache and self._geracao_cache_timestamp:
            if (agora - self._geracao_cache_timestamp) < timedelta(minutes=10):
                print("🔁 Retornando geração do cache diário")
                return {
                    "diario": self._geracao_cache,
                    "setedias": self.geracao7_cache or []
                }

        if not self.token_cache:
            self.login_solarcloud()

        if not self.usinas_cache:
            self.get_usinas()

        self.anteontem = (agora - timedelta(days=2)).strftime("%Y%m%d")
        self.ontem = (agora - timedelta(days=1)).strftime("%Y%m%d")
        sete_dias_atras = (agora - timedelta(days=8)).strftime("%Y%m%d")
        self.mes_atras = (agora - timedelta(days=31)).strftime("%Y%m%d")

        energia_por_usina = {}
        energia_7dias_por_usina = {}
        energia_30dias_por_usina = {}

        for usina in self.usinas_cache:
            ps_id = usina.get("ps_id")
            if not ps_id:
                continue

            url_device_list = self.base_url + "getDeviceList"
            body_device = {
                "appkey": self.appkey,
                "token": self.token_cache,
                "curPage": 1,
                "size": 100,
                "ps_id": ps_id,
                "device_type_list": [1],
                "lang": "_pt_BR"
            }

            response = self._post_with_auth(url_device_list, body_device)
            if response.status_code != 200:
                print(f"Erro ao buscar inversores da usina {ps_id}")
                continue

            try:
                data = response.json()
                device_list = data["result_data"]["pageList"]

                for device in device_list:
                    ps_key = device.get("ps_key")

                    # Geração diária
                    body_energy_1d = {
                        "appkey": self.appkey,
                        "token": self.token_cache,
                        "data_point": "p1",
                        "end_time": self.ontem,
                        "query_type": "1",
                        "start_time": self.anteontem,
                        "ps_key_list": [ps_key],
                        "data_type": "2",
                        "order": "0"
                    }

                    r1 = self._post_with_auth(self.base_url + "getDevicePointsDayMonthYearDataList", body_energy_1d)
                    if r1.status_code == 200:
                        try:
                            dados1 = r1.json()["result_data"]
                            chave = next(iter(dados1))
                            lista_p1 = dados1[chave]["p1"]
                            valor_str = lista_p1[0].get("2", "0")
                            energia_total = float(valor_str)
                            energia_por_usina[ps_id] = energia_por_usina.get(ps_id, 0.0) + energia_total
                        except Exception as e:
                            print(f"Erro extraindo geração 1d de {ps_key}: {e}")

                    # Geração 7 dias
                    body_energy_7d = {
                        "appkey": self.appkey,
                        "token": self.token_cache,
                        "data_point": "p1",
                        "end_time": self.ontem,
                        "query_type": "1",
                        "start_time": sete_dias_atras,
                        "ps_key_list": [ps_key],
                        "data_type": "2",
                        "order": "0"
                    }

                    r2 = self._post_with_auth(self.base_url + "getDevicePointsDayMonthYearDataList", body_energy_7d)
                    if r2.status_code == 200:
                        try:
                            dados2 = r2.json()["result_data"]
                            chave = next(iter(dados2))
                            lista_p1 = dados2[chave]["p1"]
                            soma_7dias = sum(float(p.get("2", "0")) for p in lista_p1)
                            energia_7dias_por_usina[ps_id] = energia_7dias_por_usina.get(ps_id, 0.0) + soma_7dias
                        except Exception as e:
                            print(f"Erro extraindo geração 7d de {ps_key}: {e}")

                    # Geração 30 dias
                    body_energy_mes = {
                        "appkey": self.appkey,
                        "token": self.token_cache,
                        "data_point": "p1",
                        "end_time": self.ontem,
                        "query_type": "1",
                        "start_time": self.mes_atras,
                        "ps_key_list": [ps_key],
                        "data_type": "2",
                        "order": "0"
                    }

                    r3 = self._post_with_auth(self.base_url + "getDevicePointsDayMonthYearDataList", body_energy_mes)
                    if r3.status_code == 200:
                        try:
                            dados3 = r3.json()["result_data"]
                            chave = next(iter(dados3))
                            lista_p2 = dados3[chave]["p1"]
                            soma_30dias = sum(float(p.get("2", "0")) for p in lista_p2)
                            energia_30dias_por_usina[ps_id] = energia_30dias_por_usina.get(ps_id, 0.0) + soma_30dias
                        except Exception as e:
                            print(f"Erro extraindo geração 30d de {ps_key}: {e}")

            except Exception as e:
                print(f"Erro processando usina {ps_id}: {e}")
                continue

        ps_daily_energy = [
            {
                "ps_id": ps_id,
                "data": self.ontem,
                "energia_gerada_kWh": round(valor / 1000, 2)
            }
            for ps_id, valor in energia_por_usina.items()
        ]

        ps_7dias_energy = [
            {
                "ps_id": ps_id,
                "periodo": f"{sete_dias_atras} a {self.ontem}",
                "energia_gerada_kWh": round(valor / 1000, 2)
            }
            for ps_id, valor in energia_7dias_por_usina.items()
        ]

        ps_30dias_energy = [
            {
                "ps_id": ps_id,
                "periodo": f"{self.mes_atras} a {self.ontem}",
                "energia_gerada_kWh": round(valor / 1000, 2)
            }
            for ps_id, valor in energia_30dias_por_usina.items()
        ]

        total_30dias = sum(item["energia_gerada_kWh"] for item in ps_30dias_energy)

        # Salvar no cache
        self._geracao_cache = ps_daily_energy
        self.geracao7_cache = ps_7dias_energy
        self.geracao30_cache = ps_30dias_energy
        self._geracao_cache_timestamp = agora

        print("✅ Geração salva em cache")
        return {
            "diario": ps_daily_energy,
            "setedias": ps_7dias_energy,
            "mensal": {
                "total": round(total_30dias, 2),
                "por_usina": ps_30dias_energy
            }
        }

    
    #OBTENDO GERAÇÃO HISTÓRICA

    def get_geracao_dia(self, data: str, ps_key: str = None, plant_id: int = None):
        """
        Consulta a potência p24 a cada 15min, somando os dados de todos os ps_key da usina (caso existam vários).
        Também busca o ponto p1 (geração diária total acumulada).
        """
        from datetime import datetime, timedelta
        from pytz import timezone
        import time
        import requests
        from collections import defaultdict

        brasil = timezone("America/Sao_Paulo")
        data_dt = datetime.strptime(data, "%Y-%m-%d").replace(tzinfo=brasil)

        if not self.token_cache or time.time() - self.token_timestamp > 600:
            self.login_solarcloud()

        if not self.usinas_cache:
            self.get_usinas()

        url = self.base_url + "getDeviceList"
        ps_id = str(plant_id)

        # Obtem todos os ps_key dessa usina
        body_device = {
            "appkey": self.appkey,
            "token": self.token_cache,
            "curPage": 1,
            "size": 100,
            "ps_id": ps_id,
            "device_type_list": [1],
            "lang": "_pt_BR"
        }

        res_device = self._post_with_auth(url, body_device)
        if res_device.status_code != 200:
            raise Exception(f"Erro ao obter ps_keys da usina {plant_id}")

        data_device = res_device.json()
        dispositivos = data_device["result_data"]["pageList"]
        ps_keys = [d.get("ps_key") for d in dispositivos if d.get("ps_key")]

        if not ps_keys:
            raise ValueError(f"Nenhum ps_key encontrado para a usina {plant_id}")

        print(f"✅ ps_keys encontrados: {ps_keys}")

        dados_por_hora = defaultdict(float)
        geracoes_p1 = []

        for key in ps_keys:
            for bloco in range(0, 24, 3):
                inicio = data_dt.replace(hour=bloco, minute=0, second=0)
                fim = inicio + timedelta(hours=3, seconds=-1)

                start_str = inicio.strftime("%Y%m%d%H%M%S")
                end_str = fim.strftime("%Y%m%d%H%M%S")

                body = {
                    "appkey": self.appkey,
                    "token": self.token_cache,
                    "start_time_stamp": start_str,
                    "end_time_stamp": end_str,
                    "minute_interval": 15,
                    "points": "p24,p1",  # ✅ inclui p1
                    "ps_key_list": [key],
                    "is_get_data_acquisition_time": "1"
                }

                print(f"⏱️ Requisição: {start_str} → {end_str}")
                res = requests.post(self.base_url + "getDevicePointMinuteDataList", json=body, headers=self.headers)

                if res.status_code != 200:
                    print(f"❌ Erro HTTP ({res.status_code}) no bloco {start_str} - {end_str}")
                    continue

                res_json = res.json()
                if res_json.get("result_code") != "1" or "result_data" not in res_json:
                    print(f"⚠️ Falha API no bloco {start_str} - {end_str}: {res_json}")
                    continue

                for item in res_json["result_data"].get(key, []):
                    timestamp = item.get("time_stamp")
                    potencia = item.get("p24", "0")
                    energia_total = item.get("p1")  # ✅ captura p1

                    if timestamp:
                        horario = timestamp[8:10] + ":" + timestamp[10:12]
                        try:
                            dados_por_hora[horario] += float(potencia)
                        except ValueError:
                            print(f"⚠️ Valor inválido de potência: {potencia}")

                    if energia_total:
                        try:
                            geracoes_p1.append(float(energia_total))
                        except ValueError:
                            print(f"⚠️ Valor inválido de p1: {energia_total}")

        resultado = [
            {"time": horario, "production": round(valor / 1000, 2)}
            for horario, valor in sorted(dados_por_hora.items())
        ]

        return {
            "p1": round(max(geracoes_p1) / 1000, 2) if geracoes_p1 else None,
            "diario": resultado
        }
