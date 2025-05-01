import requests
import time


class ApiDeye:
    base_url = "https://us1-developer.deyecloud.com/v1.0/"
    cache_expiry = 600 # 10 minutos
    companyId = 5402
    headers_login = {
        'Content-Type': 'application/json'
    }

    def __init__(self, username, password, appid, appsecret):
        self.username = username
        self.password = password
        self.appid = appid
        self.appsecret = appsecret
        self.accesstoken = None
        self.last_token_time = 0
        self.cached_data = None
        self.last_cache_time = 0
        self.session = requests.Session()

    def fazer_login(self):
        if self.accesstoken and (time.time() - self.last_token_time < self.cache_expiry):
            return self.accesstoken  # Reutiliza token válido

        url = self.base_url + f"account/token?appId={self.appid}"
        body = {
            "appSecret": self.appsecret,
            "email": self.username,
            "password": self.password,
            "companyId": self.companyId
        }

        response = self.session.post(url, json=body, headers=self.headers_login)

        if response.status_code != 200:
            print("Erro ao autenticar na API Deye:", response.status_code)
            print(response.text)
            return None

        dados = response.json()

        try:
            self.accesstoken = dados["accessToken"]
            self.last_token_time = time.time()
            print("Token Deye obtido com sucesso:", self.accesstoken)
            return self.accesstoken
        except KeyError:
            print("Erro ao extrair token Deye:", dados)
            return None



    def get_usinas(self):
        # Garante token válido
        if not self.fazer_login():
            return []

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f"bearer {self.accesstoken}"
        }

        if self.cached_data and time.time() - self.last_cache_time < self.cache_expiry:
            return self.cached_data

        url = self.base_url + "station/list"
        body = {
            "page": 1,
            "size": 50
        }

        response = self.session.post(url, json=body, headers=headers)
        if response.status_code != 200:
            print("Erro ao buscar usinas:", response.status_code, response.text)
            return []

        dados = response.json()
        dados_usinas = []

        try:
            for usina in dados.get("stationList", []):
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
                elif raw_status == "ERROR":
                    fault_status = 1
                elif raw_status == "ALL_OFFLINE":
                    fault_status = 1

                dados_usinas.append({
                    "ps_id": usina.get("id"),
                    "ps_name": usina.get("name"),
                    "location": usina.get("locationAddress", ""),
                    "curr_power": curr_power,
                    "total_energy": 0.0,
                    "today_energy": 0.0,
                    "capacidade": capacidade,
                    "co2_total": 0.0,
                    "income_total": 0.0,
                    "ps_fault_status": fault_status,
                })

        except Exception as e:
            print("Erro ao processar dados das usinas:", e)
            return []

        self.cached_data = dados_usinas
        self.last_cache_time = time.time()
        return dados_usinas