from sqlalchemy.orm import Session
from models.monthly_projection import MonthlyProjection
from datetime import datetime, timedelta
import calendar

# Cache global
_performance_diaria_cache = None
_performance_diaria_cache_timestamp = None
_performance_7dias_cache = None
_performance_7dias_cache_timestamp = None
_performance_30dias_cache = None
_performance_30dias_cache_timestamp = None

# Performance diária
def calcular_performance_diaria(plant_id: int, energia_gerada: float, db: Session, cliente_id: int):
    hoje = datetime.now()
    mes = hoje.month
    ano = hoje.year

    projecao = db.query(MonthlyProjection).filter_by(
        plant_id=plant_id,
        month=mes,
        year=ano,
        cliente_id=cliente_id
    ).first()

    if not projecao or projecao.projection_kwh == 0:
        return {"plant_id": plant_id, "performance": None, "mensagem": "Sem projeção"}

    dias_do_mes = calendar.monthrange(ano, mes)[1]
    media_diaria = projecao.projection_kwh / dias_do_mes
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


# Performance 7 dias
def calcular_performance_7dias(plant_id: int, energia_gerada: float, db: Session, cliente_id: int):
    hoje = datetime.now()
    mes = hoje.month
    ano = hoje.year

    projecao = db.query(MonthlyProjection).filter_by(
        plant_id=plant_id,
        month=mes,
        year=ano,
        cliente_id=cliente_id
    ).first()

    if not projecao or projecao.projection_kwh == 0:
        return {"plant_id": plant_id, "performance": None, "mensagem": "Sem projeção"}

    dias_do_mes = calendar.monthrange(ano, mes)[1]
    media_diaria = projecao.projection_kwh / dias_do_mes
    media_7dias = media_diaria * 7
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


# Performance 30 dias
def calcular_performance_30dias(plant_id: int, energia_gerada: float, db: Session, cliente_id: int):
    hoje = datetime.now()
    mes = hoje.month
    ano = hoje.year

    projecao = db.query(MonthlyProjection).filter_by(
        plant_id=plant_id,
        month=mes,
        year=ano,
        cliente_id=cliente_id
    ).first()

    if not projecao or projecao.projection_kwh == 0:
        return {"plant_id": plant_id, "performance": None, "mensagem": "Sem projeção"}

    dias_do_mes = calendar.monthrange(ano, mes)[1]
    performance = energia_gerada / projecao.projection_kwh

    return {
        "plant_id": plant_id,
        "mes": mes,
        "dias_do_mes": dias_do_mes,
        "projecao_mensal": projecao.projection_kwh,
        "gerado_30dias": energia_gerada,
        "performance_percentual": round(performance * 100)
    }


# Obter performance diária
def get_performance_diaria(isolarcloud, deye, db: Session, cliente_id: int):
    global _performance_diaria_cache, _performance_diaria_cache_timestamp

    agora = datetime.now()
    if _performance_diaria_cache and _performance_diaria_cache_timestamp:
        if (agora - _performance_diaria_cache_timestamp) < timedelta(minutes=5):
            print("🔁 Retornando performance diária do cache")
            return _performance_diaria_cache

    print("⚙️ Calculando nova performance diária...")

    resultado_geracao_isolarcloud = {}
    resultado_geracao_deye = {}

    if isolarcloud:
        try:
            resultado_geracao_isolarcloud = isolarcloud.get_geracao()
        except Exception as e:
            print("⚠️ Erro ao obter geração isolarcloud:", e)

    if deye:
        try:
            resultado_geracao_deye = deye.get_geracao()
        except Exception as e:
            print("⚠️ Erro ao obter geração deye:", e)

    geracoes = resultado_geracao_isolarcloud.get("diario", []) + resultado_geracao_deye.get("diario", [])
    resultados = []

    for g in geracoes:
        ps_id = g.get("ps_id")
        energia = g.get("energia_gerada_kWh")
        if ps_id and energia is not None:
            resultado = calcular_performance_diaria(ps_id, energia, db, cliente_id)
            resultados.append(resultado)

    _performance_diaria_cache = resultados
    _performance_diaria_cache_timestamp = agora
    print("✅ Performance diária salva em cache")
    return resultados



# Obter performance 7 dias
def get_performance_7dias(isolarcloud, deye, db: Session, cliente_id: int):
    global _performance_7dias_cache, _performance_7dias_cache_timestamp

    agora = datetime.now()
    if _performance_7dias_cache and _performance_7dias_cache_timestamp:
        if (agora - _performance_7dias_cache_timestamp) < timedelta(minutes=10):
            print("🔁 Retornando performance de 7 dias do cache")
            return _performance_7dias_cache

    print("⚙️ Calculando nova performance dos últimos 7 dias...")

    resultado_geracao_isolarcloud = {}
    resultado_geracao_deye = {}

    if isolarcloud:
        try:
            resultado_geracao_isolarcloud = isolarcloud.get_geracao()
        except Exception as e:
            print("⚠️ Erro ao obter geração isolarcloud:", e)

    if deye:
        try:
            resultado_geracao_deye = deye.get_geracao()
        except Exception as e:
            print("⚠️ Erro ao obter geração deye:", e)

    geracoes = resultado_geracao_isolarcloud.get("setedias", []) + resultado_geracao_deye.get("setedias", [])
    resultados = []

    for g in geracoes:
        ps_id = g.get("ps_id")
        energia = g.get("energia_gerada_kWh")
        if ps_id and energia is not None:
            resultado = calcular_performance_7dias(ps_id, energia, db, cliente_id)
            resultados.append(resultado)

    _performance_7dias_cache = resultados
    _performance_7dias_cache_timestamp = agora
    print("✅ Performance 7 dias salva em cache")
    return resultados




# Obter performance 30 dias
def get_performance_30dias(isolarcloud, deye, db: Session, cliente_id: int):
    global _performance_30dias_cache, _performance_30dias_cache_timestamp

    agora = datetime.now()
    if _performance_30dias_cache and _performance_30dias_cache_timestamp:
        if (agora - _performance_30dias_cache_timestamp) < timedelta(minutes=10):
            print("🔁 Retornando performance de 30 dias do cache")
            return _performance_30dias_cache

    print("⚙️ Calculando nova performance dos últimos 30 dias...")

    resultado_geracao_isolarcloud = {}
    resultado_geracao_deye = {}

    if isolarcloud:
        try:
            resultado_geracao_isolarcloud = isolarcloud.get_geracao()
        except Exception as e:
            print("⚠️ Erro ao obter geração isolarcloud:", e)

    if deye:
        try:
            resultado_geracao_deye = deye.get_geracao()
        except Exception as e:
            print("⚠️ Erro ao obter geração deye:", e)

    geracoes_isolar = resultado_geracao_isolarcloud.get("mensal", {}).get("por_usina", [])
    geracoes_deye = resultado_geracao_deye.get("mensal", {}).get("por_usina", [])

    geracoes = geracoes_isolar + geracoes_deye
    resultados = []

    for g in geracoes:
        ps_id = g.get("ps_id")
        energia = g.get("energia_gerada_kWh")
        if ps_id and energia is not None:
            resultado = calcular_performance_30dias(ps_id, energia, db, cliente_id)
            resultados.append(resultado)

    _performance_30dias_cache = resultados
    _performance_30dias_cache_timestamp = agora
    print("✅ Performance 30 dias salva em cache")
    return resultados