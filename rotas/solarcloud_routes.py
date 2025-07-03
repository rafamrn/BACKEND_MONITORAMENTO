from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from modelos import User
from dependencies import get_current_user
from integracoes.solarcloud_service import get_api_instance as get_solarcloud_instance
from integracoes.deye_service import get_api_instance as get_deye_instance
from utils import agrupar_usinas_por_nome
from services.performance_service import (
    get_performance_diaria,
    get_performance_7dias,
    get_performance_30dias,
)

router = APIRouter(tags=["Sungrow / iSolarCloud", "Deye"])

# 🔹 Listar usinas do cliente logado
@router.get("/usinas")
def listar_usinas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    solarcloud = get_solarcloud_instance(db, current_user.id)
    deye = get_deye_instance(db, current_user.id)

    usinas = solarcloud.get_usinas() + deye.get_usinas()
    return agrupar_usinas_por_nome(usinas)

# 🔹 Performance diária
@router.get("/performance_diaria")
def performance_diaria(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    solarcloud = get_solarcloud_instance(db, current_user.id)
    deye = get_deye_instance(db, current_user.id)
    return get_performance_diaria(solarcloud, deye, db)

# 🔹 Performance 7 dias
@router.get("/performance_7dias")
def performance_7dias(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    solarcloud = get_solarcloud_instance(db, current_user.id)
    deye = get_deye_instance(db, current_user.id)
    return get_performance_7dias(solarcloud, deye, db)

# 🔹 Performance 30 dias
@router.get("/performance_30dias")
def performance_30dias(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    solarcloud = get_solarcloud_instance(db, current_user.id)
    deye = get_deye_instance(db, current_user.id)
    return get_performance_30dias(solarcloud, deye, db)
