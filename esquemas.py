from pydantic import BaseModel

class UserCreate(BaseModel):
    username: str
    password: str

class IntegracaoCreate(BaseModel):
    plataforma: str
    usuario: str
    senha: str

class IntegracaoOut(IntegracaoCreate):
    id: int
    x_access_key: str | None = None
    appkey: str | None = None

    class Config:
        model_config = {"from_attributes": True}