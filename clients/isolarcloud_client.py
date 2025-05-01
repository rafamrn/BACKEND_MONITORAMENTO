import requests
import json
import time
from utils import parse_float

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
