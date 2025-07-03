from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from models.monthly_projection import MonthlyProjection
from schemas.monthly_projection import MonthlyProjectionCreate
from database import get_db
from fastapi import Query
from typing import List
from fastapi.responses import JSONResponse

router = APIRouter()

@router.post("/projecoes")
def salvar_projecoes(data: MonthlyProjectionCreate, db: Session = Depends(get_db)):
    for item in data.projections:
        nova_proj = MonthlyProjection(
            plant_id=data.plant_id,
            month=item.month,
            year=data.year,
            projection_kwh=item.kwh
        )
        db.add(nova_proj)
    db.commit()
    return {"message": "Projeções salvas com sucesso"}

@router.get("/projecoes/{plant_id}")
def obter_projecoes(plant_id: int, year: int = Query(...), db: Session = Depends(get_db)):
    resultados = (
        db.query(MonthlyProjection)
        .filter(MonthlyProjection.plant_id == plant_id, MonthlyProjection.year == year)
        .order_by(MonthlyProjection.month)
        .all()
    )

    resposta = [
        {
            "month": r.month,
            "projection_kwh": r.projection_kwh
        }
        for r in resultados
    ]

    return JSONResponse(content=resposta)
