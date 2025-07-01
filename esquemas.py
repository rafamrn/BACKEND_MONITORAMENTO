from pydantic import BaseModel, EmailStr, Field
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
    company: str
    plan: str
    status: str
    paymentStatus: str = Field(..., alias="payment_status")
    lastPayment: date = Field(..., alias="last_payment")
    createdAt: date = Field(..., alias="created_at")

    class Config:
        from_attributes = True
        validate_by_name = True