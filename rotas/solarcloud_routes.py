from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db
from modelos import User
from dependencies import get_current_user
from integracoes.solarcloud_service import get_api_instance

router = APIRouter(prefix="/solarcloud", tags=["Sungrow / iSolarCloud"])

@router.get("/usinas")
def listar_usinas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    api = get_api_instance(db, current_user.id)
    return api.get_usinas()


@router.get("/geracao")
def obter_geracao(
    period: str = Query(..., regex="^(day|month|year)$"),
    date: str = Query(...),
    plant_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    api = get_api_instance(db, current_user.id)
    return api.get_geracao(period=period, date=date, plant_id=plant_id)


@router.get("/geracao/mensal")
def obter_geracao_mensal(
    date: str = Query(..., regex=r"^\d{4}-\d{2}$"),  # ex: 2025-07
    plant_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    api = get_api_instance(db, current_user.id)
    return api.get_geracao_mes(data=date, plant_id=plant_id)


@router.get("/geracao/anual")
def obter_geracao_anual(
    year: str = Query(..., regex=r"^\d{4}$"),  # ex: 2025
    plant_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    api = get_api_instance(db, current_user.id)
    return api.get_geracao_ano(ano=year, plant_id=plant_id)


@router.get("/dados-tecnicos")
def obter_dados_tecnicos(
    plant_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    api = get_api_instance(db, current_user.id)
    return api.get_dados_tecnicos(plant_id=plant_id)
