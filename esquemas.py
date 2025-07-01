from pydantic import BaseModel, EmailStr
from datetime import date

class UserCreate(BaseModel):
    email: EmailStr
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

class ClienteCreate(BaseModel):
    name: str
    email: EmailStr
    company: str
    plan: str
    status: str = "active"
    payment_status: str = "up-to-date"
    last_payment: date
    created_at: date

class ClienteOut(ClienteCreate):
    id: int

    class Config:
        model_config = {"from_attributes": True}
