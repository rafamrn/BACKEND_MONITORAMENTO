from sqlalchemy.orm import Session
from models.monthly_projection import MonthlyProjection
from datetime import datetime, timedelta
import calendar
from functools import lru_cache
from clients.isolarcloud_client import ApiSolarCloud

# 🔒 Cache por cliente
_performance_diaria_cache = {}
_performance_diaria_cache_timestamp = {}
_performance_7dias_cache = {}
_performance_7dias_cache_timestamp = {}
_performance_30dias_cache = {}
_performance_30dias_cache_timestamp = {}

# 🔁 Instância com cache da API SolarCloud
@lru_cache(maxsize=32)
def get_solarcloud_instance(username, password, appkey, x_access_key):
    return ApiSolarCloud(username, password, appkey=appkey, x_access_key=x_access_key)

# 📊 Performance diária
def calcular_performance_diaria(plant_id: int, energia_gerada: float, db: Session):
    hoje = datetime.now()
    mes = hoje.month
    ano = hoje.year

    projecao = db.query(MonthlyProjection).filter_by(
        plant_id=plant_id, month=mes, year=ano
    ).first()

    if not projecao or projecao.projection_kwh == 0:
        return {
            "plant_id": plant_id,
            "performance": None,
            "mensagem": "Projeção mensal não encontrada ou igual a 0"
        }

    dias_do_mes = calendar.monthrange(ano, mes)[1]
    media_diaria = projecao.projection_kwh / dias_do_mes
    if media_diaria == 0:
        return {
            "plant_id": plant_id,
            "performance": None,
            "mensagem": "Média diária igual a 0"
        }

    performance = energia_gerada / media_diaria

    return {
        "plant_id": plant_id,
        "mes": mes,
        "dias_do_mes": dias_do_mes,
        "projecao_mensal": projecao.projection_kwh,
        "media_diaria_proj": round(media_diaria, 2),
        "gerado_ontem": energia_gerada,
        "performance_percentual": round(performance * 100)
    }

# 📊 Performance 7 dias
def calcular_performance_7dias(plant_id: int, energia_gerada: float, db: Session):
    hoje = datetime.now()
    mes = hoje.month
    ano = hoje.year

    projecao = db.query(MonthlyProjection).filter_by(
        plant_id=plant_id, month=mes, year=ano
    ).first()

    if not projecao or projecao.projection_kwh == 0:
        return {
            "plant_id": plant_id,
            "performance": None,
            "mensagem": "Projeção mensal não encontrada ou igual a 0"
        }

    dias_do_mes = calendar.monthrange(ano, mes)[1]
    media_diaria = projecao.projection_kwh / dias_do_mes
    media_7dias = media_diaria * 7
    if media_7dias == 0:
        return {
            "plant_id": plant_id,
            "performance": None,
            "mensagem": "Média de 7 dias igual a 0"
        }

    performance = energia_gerada / media_7dias

    return {
        "plant_id": plant_id,
        "mes": mes,
        "dias_do_mes": dias_do_mes,
        "projecao_mensal": projecao.projection_kwh,
        "media_7dias_proj": round(media_7dias, 2),
        "gerado_7dias": energia_gerada,
        "performance_percentual": round(performance * 100)
    }

# 📊 Performance 30 dias
def calcular_performance_30dias(plant_id: int, energia_gerada: float, db: Session):
    hoje = datetime.now()
    mes = hoje.month
    ano = hoje.year

    projecao = db.query(MonthlyProjection).filter_by(
        plant_id=plant_id, month=mes, year=ano
    ).first()

    if not projecao or projecao.projection_kwh == 0:
        return {
            "plant_id": plant_id,
            "performance": None,
            "mensagem": "Projeção mensal não encontrada ou igual a 0"
        }

    performance = energia_gerada / projecao.projection_kwh

    return {
        "plant_id": plant_id,
        "mes": mes,
        "projecao_mensal": projecao.projection_kwh,
        "gerado_30dias": energia_gerada,
        "performance_percentual": round(performance * 100)
    }

# 🔁 Funções públicas com cache por cliente
def get_performance_diaria(isolarcloud, deye, db: Session, cliente_id: int):
    agora = datetime.now()
    if cliente_id in _performance_diaria_cache:
        if (agora - _performance_diaria_cache_timestamp[cliente_id]) < timedelta(minutes=5):
            print("🔁 Cache performance diária (cliente:", cliente_id, ")")
            return _performance_diaria_cache[cliente_id]

    print("⚙️ Calculando performance diária...")

    geracoes_isolar = isolarcloud.get_geracao().get("diario", []) if isolarcloud else []
    geracoes_deye = deye.get_geracao().get("diario", []) if deye else []
    geracoes = geracoes_isolar + geracoes_deye

    resultados = []
    for g in geracoes:
        ps_id = g.get("ps_id")
        energia = g.get("energia_gerada_kWh")
        if ps_id and energia is not None:
            resultados.append(calcular_performance_diaria(ps_id, energia, db))

    _performance_diaria_cache[cliente_id] = resultados
    _performance_diaria_cache_timestamp[cliente_id] = agora
    return resultados

def get_performance_7dias(isolarcloud, deye, db: Session, cliente_id: int):
    agora = datetime.now()
    if cliente_id in _performance_7dias_cache:
        if (agora - _performance_7dias_cache_timestamp[cliente_id]) < timedelta(minutes=10):
            print("🔁 Cache performance 7 dias (cliente:", cliente_id, ")")
            return _performance_7dias_cache[cliente_id]

    print("⚙️ Calculando performance 7 dias...")

    geracoes_isolar = isolarcloud.get_geracao().get("setedias", []) if isolarcloud else []
    geracoes_deye = deye.get_geracao().get("setedias", []) if deye else []
    geracoes = geracoes_isolar + geracoes_deye

    resultados = []
    for g in geracoes:
        ps_id = g.get("ps_id")
        energia = g.get("energia_gerada_kWh")
        if ps_id and energia is not None:
            resultados.append(calcular_performance_7dias(ps_id, energia, db))

    _performance_7dias_cache[cliente_id] = resultados
    _performance_7dias_cache_timestamp[cliente_id] = agora
    return resultados

def get_performance_30dias(isolarcloud, deye, db: Session, cliente_id: int):
    agora = datetime.now()
    if cliente_id in _performance_30dias_cache:
        if (agora - _performance_30dias_cache_timestamp[cliente_id]) < timedelta(minutes=10):
            print("🔁 Cache performance 30 dias (cliente:", cliente_id, ")")
            return _performance_30dias_cache[cliente_id]

    print("⚙️ Calculando performance 30 dias...")

    geracoes_isolar = isolarcloud.get_geracao().get("mensal", {}).get("por_usina", []) if isolarcloud else []
    geracoes_deye = deye.get_geracao().get("mensal", {}).get("por_usina", []) if deye else []
    geracoes = geracoes_isolar + geracoes_deye

    resultados = []
    for g in geracoes:
        ps_id = g.get("ps_id")
        energia = g.get("energia_gerada_kWh")
        if ps_id and energia is not None:
            resultados.append(calcular_performance_30dias(ps_id, energia, db))

    _performance_30dias_cache[cliente_id] = resultados
    _performance_30dias_cache_timestamp[cliente_id] = agora
    return resultados
