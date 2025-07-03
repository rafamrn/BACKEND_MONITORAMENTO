from fastapi import HTTPException
from sqlalchemy.orm import Session
from modelos import Integracao
from clients.isolarcloud_client import ApiSolarCloud

def get_api_instance(db: Session, cliente_id: int) -> ApiSolarCloud:
    integracao = (
        db.query(Integracao)
        .filter(
    Integracao.cliente_id == cliente_id,
    Integracao.plataforma.in_(["isolarcloud", "Sungrow"])
)

        .first()
    )

    if not integracao:
        raise HTTPException(status_code=404, detail="Integração não encontrada.")

    return ApiSolarCloud(
        username=integracao.username,
        password=integracao.senha,
        x_access_key=integracao.x_access_key,
        appkey=integracao.appkey
    )