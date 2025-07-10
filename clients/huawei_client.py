import requests
from datetime import datetime, timedelta
from pytz import timezone
from sqlalchemy.orm import Session
from modelos import Integracao
from utils import get_horario_brasilia

class ApiHuawei:
    base_url = "https://la5.fusionsolar.huawei.com/thirdData/"

    def __init__(self, integracao: Integracao, db: Session):
        self.username = integracao.username
        self.password = integracao.senha
        self.integracao = integracao
        self.db = db
        self.session = requests.Session()
        self.xsrf = integracao.token_acesso
        self.token_updated_at = integracao.token_updated_at

# ----------------------LOGIN------------------------#

    def login_huawei(self):
        url = self.base_url + "login"
        payload = {
            "userName": self.username,
            "systemCode": self.password
        }

        response = self.session.post(url, json=payload)

        if response.status_code != 200:
            print(f"Erro ao fazer login Huawei: {response.status_code} - {response.text}")
            return False

        token = response.headers.get("xsrf-token")
        if not token:
            print("Token não encontrado no header da resposta.")
            return False

        # Atualiza o token no banco
        horario = get_horario_brasilia()
        self.integracao.token_acesso = token
        self.integracao.token_updated_at = horario
        self.db.commit()
        self.db.refresh(self.integracao)

        # Salva na instância
        self.xsrf = token
        self.token_updated_at = horario
        return True

    def token_expirado(self):
        if not self.token_updated_at or not self.xsrf:
            return True
        return get_horario_brasilia() > self.token_updated_at + timedelta(minutes=30)

    def get_token_valido(self):
        if self.token_expirado():
            print("🔁 Token expirado ou inexistente. Fazendo login Huawei...")
            if not self.login_huawei():
                raise Exception("❌ Falha ao renovar token Huawei.")
        return self.xsrf

# ----------------------GET USINAS------------------------#

    # def get_usinas(self):
        if self.cached_data and (time.time() - self.last_cache_time < self.cache_expiry):
            return self.cached_data  # Reutiliza dados se ainda não expiraram

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
                "ps_id": station_code,
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
        if  dados_usinas:
            print("Dados das usinas obtidos com sucesso!")

        return dados_usinas
    
    # OBTENDO GERAÇÃO

    def get_geracao(self):
        print("Chamando get_geracao() no Railway 🚀")
        brasil = timezone("America/Sao_Paulo")
        agora = datetime.now(brasil)

        if self.cached_data and (time.time() - self.last_cache_time < self.cache_expiry):
            return self.cached_data  # Reutiliza dados se ainda não expiraram

        if not hasattr(self, "xsrf") or not self.xsrf:
            self.login_huawei()

        if not hasattr(self, "cached_data") or not self.cached_data:
            self.get_usinas()

        # Calcula ontem em milissegundos
        ontem = agora - timedelta(days=1)
        inicio = datetime(ontem.year, ontem.month, ontem.day, 0, 0, 0, tzinfo=brasil)
        fim = inicio + timedelta(days=1)

        start_ms = int(inicio.timestamp() * 1000)
        end_ms = int(fim.timestamp() * 1000)

        energia_por_usina = {}

        for usina in self.cached_data:
            ps_id = usina.get("ps_id")
            if not ps_id:
                continue

            url_device_list = self.base_url + "getDevList"
            body_device = {"stationCodes": ps_id}

            response = self._post_with_auth(url_device_list, body_device)
            print(f"🔁 Consultando inversores da usina {ps_id}")
            if response.status_code != 200:
                print(f"Erro ao buscar inversores da usina {ps_id}")
                continue

            try:
                data = response.json()
                device_list = data["data"]

                for device in device_list:
                    ps_key = device.get("id")
                    if not ps_key:
                        continue

                    url_energy = self.base_url + "getDevHistoryKpi"
                    body_energy = {
                        "devIds": ps_key,
                        "devTypeId": 1,
                        "startTime": start_ms,
                        "endTime": end_ms
                    }

                    print(f"🔁 Consultando geração para ps_key {ps_key}")
                    r = self._post_with_auth(url_energy, body_energy)
                    if r.status_code != 200:
                        print(f"Erro ao buscar energia para ps_key {ps_key}")
                        continue

                    try:
                        energia_data = r.json()
                        dados = energia_data.get("result_data", {})
                        if not dados:
                            continue

                        chave = next(iter(dados))
                        lista_p1 = dados[chave].get("p1", [])
                        if not lista_p1:
                            continue

                        ultimo_ponto = lista_p1[-1]
                        valor_str = ultimo_ponto.get("day_cap", "0") or ultimo_ponto.get("2", "0")
                        energia_total = float(valor_str)

                        if ps_id not in energia_por_usina:
                            energia_por_usina[ps_id] = 0.0
                        energia_por_usina[ps_id] += energia_total

                    except Exception as e:
                        import traceback
                        print(f"❌ Erro ao extrair energia para ps_key {ps_key}: {e}")
                        traceback.print_exc()
                        continue

            except Exception as e:
                print(f"Erro ao processar ps_id {ps_id}: {e}")
                continue

        ps_daily_energy = [
            {
                "ps_id": ps_id,
                "data": inicio.strftime("%Y%m%d"),
                "energia_gerada_kWh": round(energia_total / 1000, 2)
            }
            for ps_id, energia_total in energia_por_usina.items()
        ]

        self._geracao_cache = ps_daily_energy
        self._geracao_cache_timestamp = agora
        print("✅ Geração salva em cache")
        print(f"✅ Total de registros obtidos: {len(ps_daily_energy)}")
        return ps_daily_energy