from sqlalchemy.orm import Session
from models.monthly_projection import MonthlyProjection
from datetime import datetime, timedelta
import calendar

# Cache global
_performance_cache = None
_performance_cache_timestamp = None

# Função para calcular performance de uma usina
def calcular_performance_diaria(plant_id: int, energia_gerada: float, db: Session):
    hoje = datetime.now()
    mes = hoje.month
    ano = hoje.year

    projecao = db.query(MonthlyProjection).filter_by(
        plant_id=plant_id,
        month=mes,
        year=ano
    ).first()

    if not projecao or projecao.projection_kwh == 0:
        return {
            "plant_id": plant_id,
            "performance": None,
            "mensagem": "Projeção mensal não encontrada ou igual a 0"
        }

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

# Função para obter performance de todas as usinas com cache
def get_performance_diaria(isolarcloud, deye, db: Session):
    global _performance_cache, _performance_cache_timestamp

    agora = datetime.now()

    # Verifica se o cache ainda é válido (menos de 10 minutos)
    if _performance_cache and _performance_cache_timestamp:
        if (agora - _performance_cache_timestamp) < timedelta(minutes=10):
            print("🔁 Retornando performance do cache (menos de 10 min)")
            return _performance_cache

    print("⚙️ Calculando nova performance diária...")

    geracoes_isolarcloud = isolarcloud.get_geracao()
    geracoes_deye = deye.get_geracao()

    geracoes = geracoes_isolarcloud + geracoes_deye
    resultados = []

    for g in geracoes:
        ps_id = g.get("ps_id")
        energia = g.get("energia_gerada_kWh")
        if ps_id and energia is not None:
            resultado = calcular_performance_diaria(ps_id, energia, db)
            resultados.append(resultado)

    _performance_cache = resultados
    _performance_cache_timestamp = agora
    print("✅ Performance salva em cache")

    return resultados
