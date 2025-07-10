from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from models.monthly_projection import MonthlyProjection
from schemas.monthly_projection import MonthlyProjectionCreate
from database import get_db
from fastapi.responses import JSONResponse
from dependencies import get_current_user
from modelos import User
from utils import get_apis_ativas
from services.performance_service import (
    get_performance_diaria,
    get_performance_7dias,
    get_performance_30dias,
)

router = APIRouter()

@router.get("/existe")
def verificar_projecoes_existem(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    existe = db.query(MonthlyProjection).filter(MonthlyProjection.cliente_id == user.id).first()
    return {"existe": bool(existe)}

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

from schemas.monthly_projection import MonthlyProjectionCreate
from models.monthly_projection import MonthlyProjection
from services.performance_service import (
    calcular_performance_diaria,
    calcular_performance_7dias,
    calcular_performance_30dias
)
from utils import get_apis_ativas

@router.post("/projecoes/salvar_e_recalcular")
def salvar_e_recalcular_projecao(
    data: MonthlyProjectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        print(f"📥 Recebido para salvar: plant_id={data.plant_id} year={data.year} projections={data.projections}")

        # Apaga as projeções anteriores
        db.query(MonthlyProjection).filter(
            MonthlyProjection.cliente_id == current_user.id,
            MonthlyProjection.plant_id == data.plant_id,
            MonthlyProjection.year == data.year
        ).delete()

        for item in data.projections:
            proj = MonthlyProjection(
                cliente_id=current_user.id,
                plant_id=data.plant_id,
                month=item.month,
                year=data.year,
                projection_kwh=item.kwh
            )
            db.add(proj)

        db.commit()
        print("✅ Projeções salvas com sucesso.")

    except Exception as e:
        db.rollback()
        print("❌ Erro ao salvar projeções:", str(e))
        raise HTTPException(status_code=500, detail=f"Erro ao salvar projeções: {e}")

    # 🔄 Recalcular performance da usina específica
    print(f"⚙️ Recalculando performance para usina {data.plant_id}")

    apis = get_apis_ativas(db, current_user.id)
    if not apis:
        raise HTTPException(status_code=404, detail="Nenhuma integração ativa encontrada.")

    resultado_1d = resultado_7d = resultado_30d = None

    for api in apis:
        try:
            dados = api.get_geracao_por_usina(data.plant_id)  # ✅ Nova função otimizada
            if not dados or not dados.get("ps_id"):
                continue

            resultado_1d = calcular_performance_diaria(data.plant_id, dados["diario_kWh"], db, current_user.id)
            resultado_7d = calcular_performance_7dias(data.plant_id, dados["7dias_kWh"], db, current_user.id)
            resultado_30d = calcular_performance_30dias(data.plant_id, dados["30dias_kWh"], db, current_user.id)

            break  # ✅ Já achou uma API válida, não precisa das outras

        except Exception as e:
            print(f"❌ Erro ao recalcular performance via {api.__class__.__name__}: {e}")

    if resultado_1d is None:
        raise HTTPException(status_code=500, detail="Erro ao recalcular performance para a usina.")

    return {
        "message": f"Projeção salva e performance recalculada para usina {data.plant_id}.",
        "diaria": resultado_1d,
        "7dias": resultado_7d,
        "30dias": resultado_30d,
    }

