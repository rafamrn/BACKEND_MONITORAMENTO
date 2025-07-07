from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import datetime

#testeteste
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)

    name = Column(String, nullable=True)
    company = Column(String, nullable=True)
    cnpj = Column(String, nullable=True)
    telefone = Column(String, nullable=True)
    plan = Column(String, nullable=True)
    status = Column(String, default="active")
    payment_status = Column(String, default="up-to-date")
    last_payment = Column(Date, default=datetime.date.today)
    created_at = Column(Date, default=datetime.date.today)
    
    is_admin = Column(Boolean, default=False)  # <--- incluído aqui
    integracoes = relationship("Integracao", back_populates="cliente")

class Integracao(Base):
    __tablename__ = "integracoes"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("users.id"))
    plataforma = Column(String, nullable=False)
    username = Column(String)
    senha = Column(String)

    appid = Column(String)          # 🔑 Novo campo para AppID (Deye)
    appsecret = Column(String)      # 🔐 Novo campo para AppSecret (Deye)
    companyid = Column(String)      # 🏢 Novo campo para Company ID (Deye)

    x_access_key = Column(String)   # usado apenas pela Sungrow
    appkey = Column(String)         # usado apenas pela Sungrow

    token_acesso = Column(String)
    token_updated_at = Column(DateTime)
    token_expira_em = Column(DateTime)
    status = Column(String, default="inactive")
    ultima_sincronizacao = Column(DateTime)

    cliente = relationship("User", back_populates="integracoes")


    
class Convite(Base):
    __tablename__ = "convites"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=True)
    token = Column(String, unique=True, nullable=False)
    cliente_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    usado = Column(Boolean, default=False)
    expiracao = Column(DateTime, nullable=False)
    criado_em = Column(DateTime, default=datetime.datetime.utcnow)

    cliente = relationship("User")