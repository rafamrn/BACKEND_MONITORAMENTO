from sqlalchemy.orm import Session
from models.monthly_projection import MonthlyProjection
from datetime import datetime, timedelta
import calendar
from models.performance_cache import PerformanceCache


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
def get_performance_diaria(apis, db: Session, cliente_id: int):
    from models.performance_cache import PerformanceCache

    cache = (
        db.query(PerformanceCache)
        .filter_by(cliente_id=cliente_id, tipo="diaria")
        .order_by(PerformanceCache.updated_at.desc())
        .first()
    )
    if cache and (datetime.now() - cache.updated_at) < timedelta(hours=23):
        print("🔁 Cache diária do banco")
        return cache.resultado_json

    print("⚙️ Calculando nova performance diária...")

    resultado_geracao = []
    for api in apis:
        try:
            geracao = api.get_geracao()
            print(f"🔍 Geração {api.__class__.__name__}: {geracao}")
            resultado_geracao += geracao.get("diario", [])
        except Exception as e:
            print(f"❌ Erro ao obter geração de {api.__class__.__name__}: {e}")

    print("📦 Resultado de geração:", resultado_geracao)

    resultados = []
    for g in resultado_geracao:
        try:
            r = calcular_performance_diaria(g["ps_id"], g["energia_gerada_kWh"], db, cliente_id)
            print("✅ Resultado performance:", r)
            resultados.append(r)
        except Exception as e:
            print(f"❌ Erro ao calcular performance para {g}: {e}")

    if resultados:
        db.add(PerformanceCache(cliente_id=cliente_id, tipo="diaria", resultado_json=resultados))
        db.commit()
        print("📝 Performance diária salva no cache com sucesso!")
    else:
        print("⚠️ Nenhum resultado válido para salvar no cache.")

    return resultados







def get_performance_7dias(apis: list, db: Session, cliente_id: int):
    from models.performance_cache import PerformanceCache

    cache = (
        db.query(PerformanceCache)
        .filter_by(cliente_id=cliente_id, tipo="7dias")
        .order_by(PerformanceCache.updated_at.desc())
        .first()
    )
    if cache and (datetime.now() - cache.updated_at) < timedelta(hours=23):
        print("🔁 Cache 7 dias do banco")
        return cache.resultado_json

    print("⚙️ Calculando nova performance dos últimos 7 dias...")
    resultado_geracao = []
    for api in apis:
        resultado_geracao += api.get_geracao().get("7dias", [])

    resultados = [
        calcular_performance_7dias(g["ps_id"], g["energia_gerada_kWh"], db, cliente_id)
        for g in resultado_geracao
    ]

    db.add(PerformanceCache(cliente_id=cliente_id, tipo="7dias", resultado_json=resultados))
    db.commit()
    return resultados


def get_performance_30dias(apis: list, db: Session, cliente_id: int):
    from models.performance_cache import PerformanceCache

    cache = (
        db.query(PerformanceCache)
        .filter_by(cliente_id=cliente_id, tipo="30dias")
        .order_by(PerformanceCache.updated_at.desc())
        .first()
    )
    if cache and (datetime.now() - cache.updated_at) < timedelta(hours=23):
        print("🔁 Cache 30 dias do banco")
        return cache.resultado_json

    print("⚙️ Calculando nova performance dos últimos 30 dias...")
    resultado_geracao = []
    for api in apis:
        resultado_geracao += api.get_geracao().get("30dias", {}).get("por_usina", [])

    resultados = [
        calcular_performance_30dias(g["ps_id"], g["energia_gerada_kWh"], db, cliente_id)
        for g in resultado_geracao
    ]

    db.add(PerformanceCache(cliente_id=cliente_id, tipo="30dias", resultado_json=resultados))
    db.commit()
    return resultados