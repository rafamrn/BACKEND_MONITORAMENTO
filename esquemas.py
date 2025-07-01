from pydantic import BaseModel, EmailStr
from datetime import date
from typing import Optional

# Usuário para registro/login
class UserCreate(BaseModel):
    email: EmailStr
    password: str

# Integrações
class IntegracaoCreate(BaseModel):
    plataforma: str
    username: str
    senha: str


class IntegracaoOut(IntegracaoCreate):
    id: int
    x_access_key: Optional[str] = None
    appkey: Optional[str] = None

    class Config:
        from_attributes = True  # para FastAPI funcionar com ORM

# Cadastro de clientes (herda de UserCreate se preferir)
class ClienteCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    company: Optional[str] = None
    plan: Optional[str] = None
    status: str = "active"
    payment_status: str = "up-to-date"
    last_payment: Optional[date] = None
    created_at: Optional[date] = None

class ClienteOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    company: Optional[str]
    plan: Optional[str]
    status: str
    payment_status: str
    last_payment: Optional[date]
    created_at: Optional[date]

    class Config:
        from_attributes = True
