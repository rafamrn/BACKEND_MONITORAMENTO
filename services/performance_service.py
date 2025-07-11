from sqlalchemy.orm import Session
from models.monthly_projection import MonthlyProjection
from datetime import datetime, timedelta
import calendar
from models.performance_cache import PerformanceCache
import json


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
def get_performance_diaria(apis, db, cliente_id, forcar=False, apenas_plant_id=None):
    cache = (
        db.query(PerformanceCache)
        .filter_by(cliente_id=cliente_id, tipo="diaria")
        .order_by(PerformanceCache.updated_at.desc())
        .first()
    )

    if not forcar and cache and (datetime.now() - cache.updated_at) < timedelta(hours=23):
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

    novos_resultados = []
    for g in resultado_geracao:
        if apenas_plant_id and g["ps_id"] != apenas_plant_id:
            continue
        try:
            r = calcular_performance_diaria(g["ps_id"], g["energia_gerada_kWh"], db, cliente_id)
            print("✅ Resultado performance:", r)
            novos_resultados.append(r)
        except Exception as e:
            print(f"❌ Erro ao calcular performance para {g}: {e}")

    # Mantém dados anteriores e só substitui os plant_ids alterados
    antigos = cache.resultado_json if cache else []
    novos_ids = {r["plant_id"] for r in novos_resultados}
    preservados = [r for r in antigos if r["plant_id"] not in novos_ids]
    resultado_final = preservados + novos_resultados

    if cache:
        cache.resultado_json = resultado_final
        cache.updated_at = datetime.now()
    else:
        db.add(PerformanceCache(
            cliente_id=cliente_id,
            tipo="diaria",
            resultado_json=resultado_final
        ))

    db.commit()
    print("📝 Performance diária atualizada no cache com sucesso!")
    return resultado_final



def get_performance_7dias(apis, db, cliente_id, forcar=False, apenas_plant_id=None):
    cache = (
        db.query(PerformanceCache)
        .filter_by(cliente_id=cliente_id, tipo="7dias")
        .order_by(PerformanceCache.updated_at.desc())
        .first()
    )

    if not forcar and cache and (datetime.now() - cache.updated_at) < timedelta(hours=23):
        print("🔁 Cache 7 dias do banco")
        return cache.resultado_json

    print("⚙️ Calculando nova performance dos últimos 7 dias...")

    resultado_geracao = []
    for api in apis:
        try:
            geracao = api.get_geracao()
            resultado_geracao += geracao.get("7dias", [])
        except Exception as e:
            print(f"❌ Erro ao obter geração de {api.__class__.__name__}: {e}")

    novos_resultados = []
    for g in resultado_geracao:
        if apenas_plant_id and g["ps_id"] != apenas_plant_id:
            continue
        try:
            r = calcular_performance_7dias(g["ps_id"], g["energia_gerada_kWh"], db, cliente_id)
            print("✅ Resultado performance:", r)
            novos_resultados.append(r)
        except Exception as e:
            print(f"❌ Erro ao calcular performance para {g}: {e}")

    antigos = cache.resultado_json if cache else []
    novos_ids = {r["plant_id"] for r in novos_resultados}
    preservados = [r for r in antigos if r["plant_id"] not in novos_ids]
    resultado_final = preservados + novos_resultados

    if cache:
        cache.resultado_json = resultado_final
        cache.updated_at = datetime.now()
    else:
        db.add(PerformanceCache(
            cliente_id=cliente_id,
            tipo="7dias",
            resultado_json=resultado_final
        ))

    db.commit()
    print("📝 Performance 7 dias salva no cache com sucesso!")
    return resultado_final




def get_performance_30dias(apis, db, cliente_id, forcar=False, apenas_plant_id=None):
    cache = (
        db.query(PerformanceCache)
        .filter_by(cliente_id=cliente_id, tipo="30dias")
        .order_by(PerformanceCache.updated_at.desc())
        .first()
    )

    if not forcar and cache and (datetime.now() - cache.updated_at) < timedelta(hours=23):
        print("🔁 Cache 30 dias do banco")
        return cache.resultado_json

    print("⚙️ Calculando nova performance dos últimos 30 dias...")

    resultado_geracao = []
    for api in apis:
        try:
            geracao = api.get_geracao()
            resultado_geracao += geracao.get("30dias", {}).get("por_usina", [])
        except Exception as e:
            print(f"❌ Erro ao obter geração de {api.__class__.__name__}: {e}")

    novos_resultados = []
    for g in resultado_geracao:
        if apenas_plant_id and g["ps_id"] != apenas_plant_id:
            continue
        try:
            r = calcular_performance_30dias(g["ps_id"], g["energia_gerada_kWh"], db, cliente_id)
            print("✅ Resultado performance:", r)
            novos_resultados.append(r)
        except Exception as e:
            print(f"❌ Erro ao calcular performance para {g}: {e}")

    antigos = cache.resultado_json if cache else []
    novos_ids = {r["plant_id"] for r in novos_resultados}
    preservados = [r for r in antigos if r["plant_id"] not in novos_ids]
    resultado_final = preservados + novos_resultados

    if cache:
        cache.resultado_json = resultado_final
        cache.updated_at = datetime.now()
    else:
        db.add(PerformanceCache(
            cliente_id=cliente_id,
            tipo="30dias",
            resultado_json=resultado_final
        ))

    db.commit()
    print("📝 Performance 30 dias salva no cache com sucesso!")
    return resultado_final

