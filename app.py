from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List

from config.settings import settings
from database import get_db
from modelos import User
from esquemas import UserCreate
from utils import agrupar_usinas_por_nome, hash_password, verify_password
from auth import create_access_token, decode_access_token
from clients.isolarcloud_client import ApiSolarCloud
from clients.huawei_client import ApiHuawei
from clients.deye_client import ApiDeye
from models.usina import UsinaModel
from routers import projection
from services.performance_service import get_performance_diaria, get_performance_7dias, get_performance_30dias

# Instanciando clientes das APIs externas
isolarcloud = ApiSolarCloud(settings.ISOLAR_USER, settings.ISOLAR_PASS)
huawei = ApiHuawei(settings.HUAWEI_USER, settings.HUAWEI_PASS)
deye = ApiDeye(settings.DEYE_USER, settings.DEYE_PASS, settings.DEYE_APPID, settings.DEYE_APPSECRET)

# App FastAPI
app = FastAPI()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")
app.include_router(projection.router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "https://frontendmonitoramento-production.up.railway.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependência: verificar usuário autenticado
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    email = decode_access_token(token)
    if not email:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")
    
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuário não encontrado")
    
    return user

# Rotas
@app.get("/usina", response_model=List[UsinaModel])
def listar_usinas(usuario_logado: User = Depends(get_current_user)):
    usinas = deye.get_usinas() + isolarcloud.get_usinas() + huawei.get_usinas()
    return agrupar_usinas_por_nome(usinas)

@app.get("/geracoes_diarias")
def listar_geracoes_diarias():
    return isolarcloud.get_geracao() + deye.get_geracao() + huawei.get_geracao()

@app.get("/performance_diaria")
def performance_diaria(db: Session = Depends(get_db)):
    return get_performance_diaria(isolarcloud, deye, db)

@app.get("/performance_7dias")
def performance_7dias(db: Session = Depends(get_db)):
    return get_performance_7dias(isolarcloud, deye, db)

@app.get("/performance_30dias")
def performance_30dias(db: Session = Depends(get_db)):
    return get_performance_30dias(isolarcloud, deye, db)


@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Usuário já existe")
    
    novo_usuario = User(email=user.email, hashed_password=hash_password(user.password))
    db.add(novo_usuario)
    db.commit()
    return {"message": f"Usuário '{user.email}' criado com sucesso!"}

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
    
    token = create_access_token(data={"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}

@app.get("/protegido")
def rota_protegida(usuario_logado: User = Depends(get_current_user)):
    return {"msg": f"Bem-vindo, {usuario_logado.email}!"}