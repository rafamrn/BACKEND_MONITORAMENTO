from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from modelos import Convite
from esquemas import ConviteCreate, ConviteOut
from app import get_db, get_current_admin_user
import secrets
from datetime import datetime, timedelta

router = APIRouter(prefix="/admin/convites", tags=["Convites"])

@router.post("/", response_model=ConviteOut)
def criar_convite(dados: ConviteCreate, db: Session = Depends(get_db), admin_user = Depends(get_current_admin_user)):
    token = secrets.token_urlsafe(32)

    convite = Convite(
        email=dados.email,
        token=token,
        cliente_id=dados.cliente_id,
        usado=False,
        expiracao=datetime.utcnow() + timedelta(days=2),
    )
    db.add(convite)
    db.commit()
    db.refresh(convite)
    return convite

@router.get("/", response_model=list[ConviteOut])
def listar_convites(db: Session = Depends(get_db), admin_user = Depends(get_current_admin_user)):
    return db.query(Convite).all()