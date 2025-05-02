from sqlalchemy.orm import Session
from models.monthly_projection import MonthlyProjection
from datetime import datetime
import calendar

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
