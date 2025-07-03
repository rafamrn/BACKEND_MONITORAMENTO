from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from modelos import User
from dependencies import get_current_user

from integracoes.solarcloud_service import get_api_instance

router = APIRouter(prefix="/solarcloud", tags=["Sungrow / iSolarCloud"])

# Exemplo de rota para listar usinas da iSolarCloud
@router.get("/usinas")
def listar_usinas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    api = get_api_instance(db, current_user.id)
    return api.get_usinas()
