import requests
import json
import time
from utils import parse_float
from datetime import datetime, timedelta
from pytz import timezone
from typing import Optional
from calendar import monthrange
from models .codificacoes_sungrow import ponto_legivel
from collections import defaultdict

_token_cache_por_cliente = {}

class ApiSolarCloud:
    base_url = "https://gateway.isolarcloud.com.hk/openapi/"

    def __init__(self, username, password, x_access_key=None, appkey=None):
        self.username = username
        self.password = password
        self.appkey = appkey
        self.x_access_key = x_access_key

        self.headers = {
            "Content-Type": "application/json",
            "x-access-key": self.x_access_key,
            "sys_code": "901"
        }

        self.token = None
        self.token_timestamp = None
        self.usinas_cache = None
        self.usinas_timestamp = None
        self.session = requests.Session()
        self._geracao_cache = None
        self._geracao_cache_timestamp = None
        self.geracao7_cache = None
        self.geracao30_cache = None

    def _login(self):
        now = time.time()
        cache = _token_cache_por_cliente.get(self.username)

        if cache and now - cache["timestamp"] < 3600:
            self.token = cache["token"]
            self.token_timestamp = cache["timestamp"]
            return self.token

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
            self.token_timestamp = now
            _token_cache_por_cliente[self.username] = {
                "token": self.token,
                "timestamp": now
            }
        except KeyError:
            print("Token não encontrado na resposta:", dados)
            return None

        print("✅ Novo token SUNGROW obtido:", self.token)
        return self.token


    def _post_with_auth(self, url, body):
        if not self.token:
            self._login()

        body["token"] = self.token
        response = self.session.post(url, json=body, headers=self.headers)

        if response.status_code in (401, 403):
            print("Token expirado ou inválido. Renovando...")
            self._login()
            body["token"] = self.token
            response = self.session.post(url, json=body, headers=self.headers)

        return response


    def get_usinas(self):
        import time  # garante que time está disponível

        # Expira cache após 10 minutos (300 segundos)
        if self.usinas_cache and (time.time() - getattr(self, "usinas_timestamp", 0)) < 300:
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
                ps_fault_status = usina.get("ps_fault_status", None)

                curr_power_raw = usina.get("curr_power", {}).get("value", "0")
                today_energy_raw = usina.get("today_energy", {}).get("value", "0")

                try:
                    curr_power_str = str(curr_power_raw).replace(".", "")
                    curr_power_float = float(curr_power_str)
                except (ValueError, TypeError):
                    curr_power_float = 0

                dados_usinas.append({
                    "ps_id": usina.get("ps_id"),
                    "ps_name": usina.get("ps_name"),
                    "location": usina.get("ps_location"),
                    "capacidade": usina.get("total_capcity", {}).get("value", "0"),
                    "curr_power": curr_power_float,
                    "total_energy": usina.get("total_energy", {}).get("value", "0"),
                    "today_energy": parse_float(today_energy_raw),
                    "co2_total": usina.get("co2_reduce_total", {}).get("value"),
                    "income_total": usina.get("total_income", {}).get("value"),
                    "ps_fault_status": ps_fault_status
                })

        except KeyError as e:
            print("Erro ao acessar dados da resposta:", e)
            return []

        # Salva no cache com timestamp
        self.usinas_cache = dados_usinas
        self.usinas_timestamp = time.time()

        return dados_usinas

# OBTENDO PS_KEYS E SERIAL NUMBER E DEMAIS DADOS
    

    def get_geracao(self, period: Optional[str] = None, date: Optional[str] = None, plant_id: Optional[int] = None):
        print("Chamando get_geracao() no Railway 🚀")
        brasil = timezone("America/Sao_Paulo")
        agora = datetime.now(brasil)

        if not self.token:
            self._login()

        if not self.usinas_cache:
            self.get_usinas()

        # Se chamada específica por dia + usina
        if period == "day" and date and plant_id:
            print(f"🔍 Buscando geração do dia {date} para plant_id={plant_id}")
            return self.get_geracao_dia(data=date, plant_id=plant_id)

        # Cache: se ainda válido, retorna direto
        if self._geracao_cache and self._geracao_cache_timestamp:
            if (agora - self._geracao_cache_timestamp) < timedelta(minutes=10):
                print("🔁 Retornando geração do cache diário")
                return {
                    "diario": self._geracao_cache,
                    "setedias": self.geracao7_cache or [],
                    "mensal": {
                        "total": round(sum(item["energia_gerada_kWh"] for item in self.geracao30_cache), 2),
                        "por_usina": self.geracao30_cache,
                    }
                }

        # Datas de referência
        ontem = (agora - timedelta(days=1)).strftime("%Y%m%d")
        sete_dias_atras = (agora - timedelta(days=8)).strftime("%Y%m%d")
        trinta_dias_atras = (agora - timedelta(days=31)).strftime("%Y%m%d")

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
                "token": self.token,
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
            except Exception as e:
                print(f"Erro processando usina {ps_id}: {e}")
                continue

            for device in device_list:
                ps_key = device.get("ps_key")

                def get_energia(start, end):
                    body = {
                        "appkey": self.appkey,
                        "token": self.token,
                        "data_point": "p1",
                        "end_time": end,
                        "query_type": "1",
                        "start_time": start,
                        "ps_key_list": [ps_key],
                        "data_type": "2",
                        "order": "0"
                    }
                    r = self._post_with_auth(self.base_url + "getDevicePointsDayMonthYearDataList", body)
                    if r.status_code == 200:
                        try:
                            dados = r.json()["result_data"]
                            chave = next(iter(dados))
                            lista_p1 = dados[chave]["p1"]
                            return sum(float(p.get("2", "0")) for p in lista_p1)
                        except Exception as e:
                            print(f"Erro extraindo geração {start} a {end} de {ps_key}: {e}")
                    return 0.0

                energia_por_usina[ps_id] = energia_por_usina.get(ps_id, 0.0) + get_energia(ontem, ontem)
                energia_7dias_por_usina[ps_id] = energia_7dias_por_usina.get(ps_id, 0.0) + get_energia(sete_dias_atras, ontem)
                energia_30dias_por_usina[ps_id] = energia_30dias_por_usina.get(ps_id, 0.0) + get_energia(trinta_dias_atras, ontem)

        # Formatação final
        ps_daily_energy = [
            {"ps_id": ps_id, "data": ontem, "energia_gerada_kWh": round(valor / 1000, 2)}
            for ps_id, valor in energia_por_usina.items()
        ]
        ps_7dias_energy = [
            {"ps_id": ps_id, "periodo": f"{sete_dias_atras} a {ontem}", "energia_gerada_kWh": round(valor / 1000, 2)}
            for ps_id, valor in energia_7dias_por_usina.items()
        ]
        ps_30dias_energy = [
            {"ps_id": ps_id, "periodo": f"{trinta_dias_atras} a {ontem}", "energia_gerada_kWh": round(valor / 1000, 2)}
            for ps_id, valor in energia_30dias_por_usina.items()
        ]
        total_30dias = sum(item["energia_gerada_kWh"] for item in ps_30dias_energy)

        # Cache
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

    def get_geracao_dia(self, data: str, plant_id: int):
        """
        Consulta a potência p24 a cada 15min, somando os dados de todos os ps_key da usina.
        Também busca o ponto p1 (geração acumulada do dia).
        """
        brasil = timezone("America/Sao_Paulo")
        data_dt = datetime.strptime(data, "%Y-%m-%d").replace(tzinfo=brasil)

        if not self.token:
            self._login()

        if not self.usinas_cache:
            self.get_usinas()

        ps_id = str(plant_id)
        url = self.base_url + "getDeviceList"
        body_device = {
            "appkey": self.appkey,
            "token": self.token,
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
        p1_por_inversor = defaultdict(list)

        for key in ps_keys:
            for bloco in range(0, 24, 3):
                inicio = data_dt.replace(hour=bloco, minute=0, second=0)
                fim = inicio + timedelta(hours=3, seconds=-1)

                start_str = inicio.strftime("%Y%m%d%H%M%S")
                end_str = fim.strftime("%Y%m%d%H%M%S")

                body = {
                    "appkey": self.appkey,
                    "token": self.token,
                    "start_time_stamp": start_str,
                    "end_time_stamp": end_str,
                    "minute_interval": 5,
                    "points": "p24,p1",
                    "ps_key_list": [key],
                    "is_get_data_acquisition_time": "1"
                }

                print(f"⏱️ Requisição: {start_str} → {end_str}")
                res = self._post_with_auth(self.base_url + "getDevicePointMinuteDataList", body)

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
                    energia_total = item.get("p1")

                    if timestamp:
                        horario = f"{timestamp[8:10]}:{timestamp[10:12]}"
                        try:
                            dados_por_hora[horario] += float(potencia)
                        except ValueError:
                            print(f"⚠️ Valor inválido de potência: {potencia}")

                    if energia_total:
                        try:
                            p1_float = float(energia_total)
                            p1_por_inversor[key].append(p1_float)
                        except ValueError:
                            print(f"⚠️ Valor inválido de p1: {energia_total}")

        resultado = [
            {"time": horario, "production": round(valor / 1000, 2)}
            for horario, valor in sorted(dados_por_hora.items())
        ]

        p1_total_wh = sum(max(valores) for valores in p1_por_inversor.values() if valores)
        p1_total_kwh = p1_total_wh / 1000

        return {
            "p1": round(p1_total_kwh, 2),
            "diario": resultado
        }



    def get_geracao_mes(self, data: str, ps_key: str = None, plant_id: int = None):
        from calendar import monthrange

        if not self.token:
            self._login()

        if not self.usinas_cache:
            self.get_usinas()

        url = self.base_url + "getDeviceList"
        body_dispositivos = {
            "appkey": self.appkey,
            "token": self.token,
            "curPage": 1,
            "size": 100,
            "ps_id": str(plant_id),
            "device_type_list": [1],
            "lang": "_pt_BR"
        }

        res = self._post_with_auth(url, body_dispositivos)
        if res.status_code != 200:
            raise Exception(f"Erro ao buscar dispositivos da usina {plant_id}")

        try:
            data_device = res.json()
            inversores = data_device.get("result_data", {}).get("pageList", [])
            ps_keys = [inv.get("ps_key") for inv in inversores if inv.get("ps_key")]
        except Exception as e:
            raise Exception(f"Erro ao interpretar JSON de dispositivos: {e}")

        if not ps_keys:
            raise ValueError("Nenhum ps_key encontrado para a usina.")

        # Define intervalo
        ano, mes = data.split("-")
        hoje = datetime.now()
        if int(ano) == hoje.year and int(mes) == hoje.month:
            ultimo_dia = hoje.day
        else:
            _, ultimo_dia = monthrange(int(ano), int(mes))

        start_time = f"{ano}{mes}01"
        end_time = f"{ano}{mes}{str(ultimo_dia).zfill(2)}"

        dados_acumulados = {}

        for key in ps_keys:
            body_energy = {
                "token": self.token,
                "appkey": self.appkey,
                "data_point": "p1",
                "start_time": start_time,
                "end_time": end_time,
                "query_type": "1",
                "data_type": "2",
                "order": "0",
                "ps_key_list": [key]
            }

            res = requests.post(
                self.base_url + "getDevicePointsDayMonthYearDataList",
                json=body_energy,
                headers=self.headers
            )

            if res.status_code != 200:
                print(f"⚠️ Erro HTTP para ps_key {key}")
                continue

            try:
                res_json = res.json()
                if res_json.get("result_code") != "1":
                    print(f"⚠️ API retornou erro para ps_key {key}: {res_json}")
                    continue

                dados = res_json.get("result_data", {}).get(key, {}).get("p1", [])
                for item in dados:
                    timestamp = item.get("time_stamp")
                    valor_raw = item.get("2")
                    if timestamp and valor_raw:
                        data_str = f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}"
                        try:
                            valor = round(float(valor_raw) / 1000, 2)
                            dados_acumulados[data_str] = dados_acumulados.get(data_str, 0) + valor
                        except ValueError:
                            print(f"⚠️ Valor inválido ({valor_raw}) para ps_key {key} em {data_str}")
            except Exception as e:
                print(f"❌ Erro processando dados para ps_key {key}: {e}")
                continue

        resultado = [
            {"date": k, "production": round(v, 2)}
            for k, v in sorted(dados_acumulados.items())
        ]
        soma_total = round(sum(item["production"] for item in resultado), 2)

        return {
            "mensal": resultado,
            "total": soma_total
        }

    
    def get_geracao_ano(self, ano: str, ps_key: str = None, plant_id: int = None):
        if not self.token:
            self._login()

        if not self.usinas_cache:
            self.get_usinas()

        url = self.base_url + "getDeviceList"
        body = {
            "appkey": self.appkey,
            "token": self.token,
            "curPage": 1,
            "size": 100,
            "ps_id": str(plant_id),
            "device_type_list": [1],
            "lang": "_pt_BR"
        }

        res = self._post_with_auth(url, body)
        data_device = res.json()
        inversores = data_device.get("result_data", {}).get("pageList", [])
        ps_keys = [inv.get("ps_key") for inv in inversores if inv.get("ps_key")]

        if not ps_keys:
            raise ValueError("Nenhum ps_key encontrado.")

        start_time = f"{ano}01"
        end_time = f"{ano}12"

        dados_acumulados = {}
        soma_total = 0

        for key in ps_keys:
            body = {
                "token": self.token,
                "appkey": self.appkey,
                "data_point": "p1",
                "start_time": start_time,
                "end_time": end_time,
                "query_type": "2",
                "data_type": "4",
                "order": "0",
                "ps_key_list": [key]
            }

            res = requests.post(
                self.base_url + "getDevicePointsDayMonthYearDataList",
                json=body,
                headers=self.headers
            )

            res_json = res.json()
            if res.status_code != 200 or res_json.get("result_code") != "1":
                print(f"⚠️ Erro para ps_key {key}: {res_json}")
                continue

            dados = res_json.get("result_data", {}).get(key, {}).get("p1", [])
            for item in dados:
                timestamp = item.get("time_stamp")
                valor_raw = item.get("4")
                if timestamp and valor_raw:
                    data_str = f"{timestamp[:4]}-{timestamp[4:6]}"  # YYYY-MM
                    valor = round(float(valor_raw) / 1000, 2)
                    dados_acumulados[data_str] = dados_acumulados.get(data_str, 0) + valor

        resultado = [{"date": k, "production": round(v, 2)} for k, v in sorted(dados_acumulados.items())]
        soma_total = sum([item["production"] for item in resultado])

        return {
            "anual": resultado,
            "total": round(soma_total, 2)
        }


    def get_dados_tecnicos(self, ps_key: str = None, plant_id: int = 1563706):
        # Atualiza o token se expirado
        if not self.token:
            self._login()

        # Se ps_key não for fornecido, obtém todos os da usina
        if not ps_key:
            if not self.usinas_cache:
                self.get_usinas()

            url = self.base_url + "getDeviceList"
            body_device_list = {
                "appkey": self.appkey,
                "token": self.token,
                "curPage": 1,
                "size": 10,
                "ps_id": str(plant_id),
                "device_type_list": [1],
                "lang": "_pt_BR"
            }

            res = self._post_with_auth(url, body_device_list)
            if res.status_code != 200:
                raise Exception(f"Erro ao obter ps_keys da usina {plant_id} (status {res.status_code})")

            try:
                data_device = res.json()
                inversores = data_device.get("result_data", {}).get("pageList", [])
                if not inversores:
                    raise ValueError("Nenhum inversor encontrado para essa usina.")

                ps_keys = [inv.get("ps_key") for inv in inversores if inv.get("ps_key")]
                if not ps_keys:
                    raise ValueError("Nenhum ps_key válido encontrado.")
            except Exception as e:
                raise Exception(f"Erro ao interpretar resposta da API ao buscar ps_keys: {e}")
        else:
            ps_keys = [ps_key]  # transforma string em lista

        # Prepara body para dados técnicos
        body_dados = {
            "appkey": self.appkey,
            "token": self.token,
            "device_type": 1,
            "point_id_list": [
                "6", "8", "10", "46", "48", "50", "52", "54", "56", "58", "7451", "7452",
                "5", "7", "9", "45", "47", "49", "51", "53", "55", "57", "7401", "7402",
                "18", "19", "20", "21", "22", "23", "27", "4", "96", "97", "98", "99",
                "100", "101", "102", "103", "104", "105", "106", "107", "108", "109",
                "110", "111", "112", "113", "7166", "7167", "7168", "7169", "7170",
                "7171", "70", "71", "72", "73", "74", "75", "76", "77", "78", "79",
                "80", "81", "82", "83", "84", "85", "92", "93", "313", "314", "315",
                "316", "317", "318"
            ],
            "ps_key_list": ps_keys
        }

        res_dados = requests.post(
            self.base_url + "getDeviceRealTimeData",
            json=body_dados,
            headers=self.headers
        )

        if res_dados.status_code != 200:
            raise Exception(f"Erro ao buscar dados técnicos (status {res_dados.status_code})")

        try:
            res_json = res_dados.json()
            dados = res_json.get("result_data", {}).get("device_point_list", [])
            if not dados:
                raise ValueError("Nenhum dado técnico retornado.")

            # Extrai apenas os pontos legíveis
            device_points = [item.get("device_point", {}) for item in dados]
            device_points_legiveis = [
                {ponto_legivel.get(k, k): v for k, v in dp.items() if v is not None}
                for dp in device_points
            ]

            return {"dados": device_points_legiveis}
        except Exception as e:
            raise Exception(f"Erro ao processar resposta de dados técnicos: {e}")
