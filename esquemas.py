from pydantic import BaseModel, EmailStr, constr
from datetime import datetime, date
from typing import Optional
import uuid

# --------------------------
# 📌 MODELOS DE USUÁRIO
# --------------------------

class UserCreate(BaseModel):
    name: Optional[str]
    email: EmailStr
    password: str
    company: Optional[str]
    cnpj: Optional[str]
    telefone: Optional[str]
    plan: Optional[str]

# --------------------------
# 📌 MODELOS DE CLIENTE
# --------------------------

class ClienteCreate(BaseModel):
    company: Optional[str]
    cnpj: Optional[str]
    telefone: Optional[str]
    plan: str

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
    last_payment: Optional[date]
    created_at: Optional[date]

    class Config:
        from_attributes = True

# --------------------------
# 📌 MODELOS DE INTEGRAÇÃO
# --------------------------

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
    appid: Optional[str] = None  # ✅ novo
    appsecret: Optional[str] = None  # ✅ novo
    status: Optional[str] = None
    nome: Optional[str] = None
    ultima_sincronizacao: Optional[datetime] = None

    class Config:
        from_attributes = True
# --------------------------
# 📌 MODELOS DE CONVITE
# --------------------------

class ConviteOut(BaseModel):
    id: int
    email: str
    token: str
    usado: bool
    expiracao: datetime
    criado_em: datetime

    class Config:
        from_attributes = True

# --------------------------
# 📌 REGISTRO COM CONVITE
# --------------------------

class RegistroComConvite(BaseModel):
    password: str
    token: str

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: constr(min_length=6)
    confirmPassword: str
    token: uuid.UUID

class ConviteCreate(BaseModel):
    email: EmailStr
    expiracao: Optional[datetime] = None  # Pode ser gerado automaticamente no backend

