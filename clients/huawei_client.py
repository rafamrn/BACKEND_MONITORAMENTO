import requests
import time

class ApiHuawei:
    base_url = "https://la5.fusionsolar.huawei.com/thirdData/"
    cache_expiry = 600 # 10 minutos

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.xsrf = None
        self.last_token_time = 0
        self.cached_data = None
        self.last_cache_time = 0
        self.session = requests.Session()

    def login_huawei(self):
        if self.xsrf and (time.time() - self.last_token_time < self.cache_expiry):
            return self.xsrf  # Reutiliza token válido

        url = self.base_url + "login"
        payload = {
            "userName": self.username,
            "systemCode": self.password
        }
        session = requests.Session()
        response = session.post(url, json=payload)
        self.xsrf = response.headers.get('xsrf-token')
        self.last_token_time = time.time()
        print(f"Novo Token Huawei Obtido: {self.xsrf}")
        return self.xsrf

    def _post_with_auth(self, url, body):
        if not self.xsrf:
            self.login_huawei()

        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "xsrf-token": self.xsrf
        }

        response = self.session.post(url, json=body, headers=headers)

        if response.status_code in (401, 403):
            print("Token Huawei expirado. Renovando...")
            self.xsrf = None
            self.login_huawei()
            headers["xsrf-token"] = self.xsrf
            response = self.session.post(url, json=body, headers=headers)

        return response

    def get_usinas(self):
        if self.cached_data and (time.time() - self.last_cache_time < self.cache_expiry):
            return self.cached_data  # Reutiliza dados se ainda não expiraram

        self.login_huawei()

        url_stations = self.base_url + "stations"
        url_kpi = self.base_url + "getStationRealKpi"
        url_dev = self.base_url + "getDevList"
        url_real = self.base_url + "getDevRealKpi"

        response = self._post_with_auth(url_stations, {"pageNo": 1})
        if response.status_code != 200:
            print("Erro ao buscar usinas Huawei:", response.status_code)
            return []

        dados = response.json()
        dados_usinas = []

        for usina in dados.get("data", {}).get("list", []):
            station_code = usina.get("plantCode")
            if not station_code:
                continue

            resp_kpi = self._post_with_auth(url_kpi, {"stationCodes": station_code})
            resp_dev = self._post_with_auth(url_dev, {"stationCodes": station_code})

            # Valores padrão
            id_usina = "--"
            total_energy = today_energy = co2_total = income_total = curr_power = 0.0
            ps_fault_status = 0

            try:
                kpi_data = resp_kpi.json().get("data", [])
                if kpi_data:
                    dados_kpi = kpi_data[0].get("dataItemMap", {})
                    total_energy = float(dados_kpi.get("total_power", 0))
                    today_energy = float(dados_kpi.get("day_power", 0))
                    co2_total = float(dados_kpi.get("co2_reduction", 0))
                    income_total = float(dados_kpi.get("total_income", 0))
                    ps_fault_status = int(dados_kpi.get("real_health_state", 0))

                dev_data = resp_dev.json().get("data", [])
                if dev_data:
                    id_usina = dev_data[0].get("id", "--")

                if id_usina and id_usina != "--":
                    resp_real = self._post_with_auth(url_real, {
                        "devIds": id_usina,
                        "devTypeId": "1"
                    })

                    real_data = resp_real.json().get("data", [])
                    if real_data:
                        dados_real = real_data[0].get("dataItemMap", {})
                        curr_power = float(dados_real.get("active_power", 0))

            except Exception as e:
                print(f"[Huawei] Erro ao processar usina {station_code}: {e}")

            dados_usinas.append({
                "ps_id": station_code.replace("NE=", ""),
                "id_usina": id_usina,
                "curr_power": curr_power/1000,
                "ps_name": usina.get("plantName", "sem nome"),
                "location": usina.get("address", "--"),
                "capacidade": float(usina.get("capacity", 0)),
                "total_energy": total_energy,
                "today_energy": today_energy,
                "co2_total": co2_total,
                "income_total": income_total,
                "ps_fault_status": ps_fault_status
            })

        self.cached_data = dados_usinas
        self.last_cache_time = time.time()
        return dados_usinas