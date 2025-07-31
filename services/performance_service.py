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
    print(f"🔍 Buscando projeção para plant_id={plant_id} | mês={mes} | ano={ano} | cliente_id={cliente_id}")
    print("🔎 Projeção encontrada:", projecao)
    if projecao:
        print("➡️ kWh previsto:", projecao.projection_kwh)

    if not projecao or projecao.projection_kwh == 0:
        print("⚠️ Nenhuma projeção válida encontrada.")
        return {
            "plant_id": plant_id,
            "mes": mes,
            "dias_do_mes": calendar.monthrange(ano, mes)[1],
            "gerado_ontem": energia_gerada,
            "projecao_mensal": None,
            "media_diaria_proj": None,
            "performance_percentual": None,
            "mensagem": "Sem projeção"
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

    dias_do_mes = calendar.monthrange(ano, mes)[1]
    media_diaria = projecao.projection_kwh / dias_do_mes if projecao and projecao.projection_kwh else None
    media_7dias = media_diaria * 7 if media_diaria else None
    performance = energia_gerada / media_7dias if media_7dias else None

    return {
        "plant_id": plant_id,
        "mes": mes,
        "dias_do_mes": dias_do_mes,
        "projecao_mensal": projecao.projection_kwh if projecao else None,
        "media_7dias_proj": round(media_7dias, 2) if media_7dias else None,
        "gerado_7dias": energia_gerada,
        "performance_percentual": round(performance * 100) if performance is not None else None,
        "mensagem": "Sem projeção" if not projecao or projecao.projection_kwh == 0 else None
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

    dias_do_mes = calendar.monthrange(ano, mes)[1]
    projecao_kwh = projecao.projection_kwh if projecao else None
    performance = energia_gerada / projecao_kwh if projecao_kwh else None

    return {
        "plant_id": plant_id,
        "mes": mes,
        "dias_do_mes": dias_do_mes,
        "projecao_mensal": projecao_kwh,
        "gerado_30dias": energia_gerada,
        "performance_percentual": round(performance * 100) if performance is not None else None,
        "mensagem": "Sem projeção" if not projecao or projecao_kwh == 0 else None
    }


# Obter performance diária
from datetime import datetime, timedelta
import traceback

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
            if isinstance(r, dict):
                novos_resultados.append(r)
            else:
                print("⚠️ Resultado não é um dicionário:", r)
        except Exception as e:
            print("❌ Erro ao calcular performance individual:")
            traceback.print_exc()

    antigos = cache.resultado_json if cache else []

    def extrair_plant_id(item):
        if isinstance(item, dict):
            return item.get("plant_id")
        print("⚠️ item inesperado em novos_resultados:", item)
        return None

    novos_ids = {extrair_plant_id(r) for r in novos_resultados if extrair_plant_id(r) is not None}
    preservados = [r for r in antigos if extrair_plant_id(r) not in novos_ids]

    resultado_final = preservados + novos_resultados

    # 🔍 Verificando o que está prestes a ser salvo no cache
    print("🧾 Resultado final para salvar no cache:", resultado_final)

    try:
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
    except Exception as e:
        print("❌ Erro ao salvar resultado_final no banco:")
        traceback.print_exc()
        raise

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

    def extrair_plant_id(item):
        return item.get("plant_id")

    antigos = cache.resultado_json if cache else []
    novos_ids = {extrair_plant_id(r) for r in novos_resultados}
    preservados = [r for r in antigos if extrair_plant_id(r) not in novos_ids]
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

    def extrair_plant_id(item):
        return item.get("plant_id")

    antigos = cache.resultado_json if cache else []
    novos_ids = {extrair_plant_id(r) for r in novos_resultados}
    preservados = [r for r in antigos if extrair_plant_id(r) not in novos_ids]
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