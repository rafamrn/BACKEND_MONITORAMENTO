from pydantic import BaseModel, EmailStr, Field, constr
from datetime import datetime, date
from typing import Optional
import uuid


# Usuário para registro/login
class UserCreate(BaseModel):
    name: Optional[str]
    email: EmailStr
    password: str
    company: Optional[str]
    cnpj: Optional[str]
    telefone: Optional[str]
    plan: Optional[str]

# Integrações
class IntegracaoCreate(BaseModel):
    plataforma: str
    username: str
    senha: str


class IntegracaoOut(BaseModel):
    id: int
    cliente_id: Optional[int] = None
    plataforma: str
    username: str
    senha: str
    appkey: Optional[str] = None
    x_access_key: Optional[str] = None

    # Novo campo: nome do cliente via relação
    nome: Optional[str] = None

    class Config:
        orm_mode = True


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
    email: str
    name: Optional[str]
    company: Optional[str]
    cnpj: Optional[str]
    telefone: Optional[str]
    plan: Optional[str]
    status: Optional[str]
    payment_status: Optional[str]
    last_payment: Optional[datetime.date]
    created_at: Optional[datetime.date]

    class Config:
        orm_mode = True

    class Config:
        from_attributes = True
        validate_by_name = True

class ClienteCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    company: Optional[str]
    cnpj: Optional[str]
    telefone: Optional[str]
    plan: str
    status: str
    payment_status: str
    last_payment: datetime.date
    created_at: datetime.date

class ConviteOut(BaseModel):
    id: int
    email: str
    token: str
    usado: bool
    expiracao: datetime
    criado_em: datetime

    class Config:
        orm_mode = True

class RegistroComConvite(BaseModel):
    password: str
    token: str

class RegisterRequest(BaseModel):
    name: str
    password: constr(min_length=6)
    confirmPassword: str
    token: uuid.UUID