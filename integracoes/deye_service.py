from fastapi import HTTPException
from sqlalchemy.orm import Session
from modelos import Integracao
from clients.deye_client import ApiDeye

def get_api_instance(db: Session, cliente_id: int) -> ApiDeye:
    integracao = (
        db.query(Integracao)
        .filter(Integracao.cliente_id == cliente_id, Integracao.plataforma == "deye")
        .first()
    )

    if not integracao:
        raise HTTPException(status_code=404, detail="Integração Deye não encontrada.")

    return ApiDeye(
        username=integracao.username,
        password=integracao.senha,
        app_id=integracao.appkey,
        app_secret=integracao.x_access_key
    )
