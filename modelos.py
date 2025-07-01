from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, Date
from sqlalchemy.orm import relationship
from database import Base
import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    integracoes = relationship("Integracao", back_populates="cliente")

class Usuario(Base):
    __tablename__ = "usuarios"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    senha = Column(String)
    nome = Column(String)
    is_admin = Column(Boolean, default=False)  # <--- este campo

class Integracao(Base):
    __tablename__ = "integracoes"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("users.id"))
    plataforma = Column(String, nullable=False)  # Ex: "Huawei", "Sungrow", "Deye"
    usuario = Column(String, nullable=False)
    senha = Column(String, nullable=False)
    x_access_key = Column(String, nullable=True)
    appkey = Column(String, nullable=True)

    cliente = relationship("User", back_populates="integracoes")

class Cliente(Base):
    __tablename__ = "clientes"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    company = Column(String, nullable=True)
    plan = Column(String, nullable=True)
    status = Column(String, default="active")
    payment_status = Column(String, default="up-to-date")
    last_payment = Column(Date, default=datetime.date.today)
    created_at = Column(Date, default=datetime.date.today)
