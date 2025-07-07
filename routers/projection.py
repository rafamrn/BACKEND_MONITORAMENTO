from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from models.monthly_projection import MonthlyProjection
from schemas.monthly_projection import MonthlyProjectionCreate
from database import get_db
from fastapi.responses import JSONResponse
from dependencies import get_current_user
from modelos import User
from typing import List

router = APIRouter()

@router.post("/projecoes")
def salvar_projecoes(
    data: MonthlyProjectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        print("📥 Recebido para salvar:", data)

        # Apaga as projeções anteriores do mesmo cliente/usina/ano
        db.query(MonthlyProjection).filter(
            MonthlyProjection.cliente_id == current_user.id,
            MonthlyProjection.plant_id == data.plant_id,
            MonthlyProjection.year == data.year
        ).delete()

        for item in data.projections:
            nova_proj = MonthlyProjection(
                cliente_id=current_user.id,
                plant_id=data.plant_id,
                month=item.month,
                year=data.year,
                projection_kwh=item.kwh
            )
            db.add(nova_proj)

        db.commit()
        print("✅ Projeções salvas com sucesso.")
        return {"message": "Projeções salvas com sucesso"}

    except Exception as e:
        db.rollback()
        print("❌ Erro ao salvar projeções:", str(e))
        raise HTTPException(status_code=500, detail=f"Erro ao salvar projeções: {e}")


@router.get("/projecoes/{plant_id}")
def obter_projecoes(
    plant_id: int,
    year: int = Query(...),
    db: Session = Depends(get_db)
):
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
