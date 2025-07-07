import requests
import time

class ApiHyponCloud:
    base_url = "https://api.hypon.cloud/v2/"
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