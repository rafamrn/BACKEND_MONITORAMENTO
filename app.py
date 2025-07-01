from fastapi import FastAPI, Depends, HTTPException, status, Query, APIRouter
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List, Optional
from config.settings import settings
from database import SessionLocal
from database import get_db
from modelos import User, Integracao
from esquemas import UserCreate, IntegracaoCreate, IntegracaoOut, ClienteCreate, ClienteOut
from utils import agrupar_usinas_por_nome, hash_password, verify_password
from auth import create_access_token, decode_access_token
from clients.isolarcloud_client import ApiSolarCloud
from clients.huawei_client import ApiHuawei
from clients.deye_client import ApiDeye
from models.usina import UsinaModel
from routers import projection
from pydantic import BaseModel, EmailStr
from starlette.middleware.trustedhost import TrustedHostMiddleware
import tempfile
from services.performance_service import get_performance_diaria, get_performance_7dias, get_performance_30dias

# Instanciando clientes das APIs externas
isolarcloud = ApiSolarCloud(settings.ISOLAR_USER, settings.ISOLAR_PASS)
huawei = ApiHuawei(settings.HUAWEI_USER, settings.HUAWEI_PASS)
deye = ApiDeye(settings.DEYE_USER, settings.DEYE_PASS, settings.DEYE_APPID, settings.DEYE_APPSECRET)

# App FastAPI
app = FastAPI()
# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://frontendmonitoramento-production.up.railway.app"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")
app.include_router(projection.router)

class UserCreate(BaseModel):
    email: EmailStr
    password: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


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
    usinas = deye.get_usinas() + isolarcloud.get_usinas()
    return agrupar_usinas_por_nome(usinas)

@app.get("/geracoes_diarias")
def listar_geracoes_diarias():
    return isolarcloud.get_geracao() + deye.get_geracao()

@app.get("/performance_diaria")
def performance_diaria(db: Session = Depends(get_db)):
    return get_performance_diaria(isolarcloud, deye, db)

@app.get("/performance_7dias")
def performance_7dias(db: Session = Depends(get_db)):
    return get_performance_7dias(isolarcloud, deye, db)

@app.get("/performance_30dias")
def performance_30dias(db: Session = Depends(get_db)):
    return get_performance_30dias(isolarcloud, deye, db)

@app.get("/dados_tecnicos")
def obter_dados_tecnicos(
    plant_id: int = Query(...),
    usuario_logado: User = Depends(get_current_user)
):
    """
    Retorna dados técnicos com base na usina.
    """
    return isolarcloud.get_dados_tecnicos(plant_id=plant_id)


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
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado")
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Senha incorreta")

    access_token = create_access_token(data={"sub": user.email}, is_admin=False)
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/protegido")
def rota_protegida(usuario_logado: User = Depends(get_current_user)):
    return {"msg": f"Bem-vindo, {usuario_logado.email}!"}

@app.get("/api/geracao")
def obter_geracao(
    period: str = Query(..., regex="^(day|month|year)$"),
    date: str = Query(...),
    plant_id: int = Query(...),
    usuario_logado: User = Depends(get_current_user)
):
    """
    Retorna dados de geração com base na usina, data e tipo de período selecionado.
    """
    return isolarcloud.get_geracao(period=period, date=date, plant_id=plant_id)

@app.get("/api/geracao/mensal")
def obter_geracao_mensal(
    date: str = Query(..., regex=r"^\d{4}-\d{2}$"),  # exemplo: "2025-05"
    plant_id: int = Query(...),
    usuario_logado: User = Depends(get_current_user)
):
    """
    Retorna geração mensal (p1) da usina com base em um mês específico.
    """
    try:
        return isolarcloud.get_geracao_mes(data=date, plant_id=plant_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/api/geracao/anual")
def obter_geracao_anual(
    year: str = Query(..., regex=r"^\d{4}$"),  # Ex: "2025"
    plant_id: int = Query(...),
    usuario_logado: User = Depends(get_current_user)
):
    """
    Retorna a geração mensal (p1) para cada mês do ano informado.
    """
    try:
        return isolarcloud.get_geracao_ano(ano=year, plant_id=plant_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/users")
def create_user_route(user: UserCreate, db: Session = Depends(get_db)):
    user_exists = db.query(User).filter(User.email == user.email).first()
    if user_exists:
        raise HTTPException(status_code=400, detail="Usuário já existe.")

    db_user = User(
        email=user.email,
        hashed_password=hash_password(user.password)
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"message": "Usuário criado com sucesso", "user_id": db_user.id}

router = APIRouter(prefix="/integracoes", tags=["Integrações"])

@router.post("/")
def criar_integracao(
    integracao: IntegracaoCreate,
    db: Session = Depends(get_db),
    user: dict = Depends(get_current_user)  # opcional, se usa autenticação
):
    nova = Integracao(
        cliente_id=user.get("id") if user else None,  # opcional
        plataforma=integracao.plataforma,
        usuario=integracao.usuario,
        senha=integracao.senha
    )
    db.add(nova)
    db.commit()
    db.refresh(nova)
    return {"message": "Integração salva com sucesso", "id": nova.id}

@app.get("/admin/integracoes", response_model=List[IntegracaoOut])
def listar_todas_integracoes(db: Session = Depends(get_db), usuario_logado: User = Depends(get_current_user)):
    if not usuario_logado.is_admin:
        raise HTTPException(status_code=403, detail="Acesso restrito a administradores.")
    
    return db.query(Integracao).all()


@app.post("/clientes", response_model=ClienteOut)
def criar_cliente(cliente: ClienteCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == cliente.email).first():
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    novo = User(
        email=cliente.email,
        hashed_password=hash_password(cliente.password),
        name=cliente.name,
        company=cliente.company,
        plan=cliente.plan,
        status=cliente.status,
        payment_status=cliente.payment_status,
        last_payment=cliente.last_payment,
        created_at=cliente.created_at,
    )
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return novo

@app.get("/clientes", response_model=List[ClienteOut], response_model_by_alias=False)
def listar_clientes(db: Session = Depends(get_db)):
    return db.query(User).all()

@app.delete("/clientes/{cliente_id}", status_code=204)
def deletar_cliente(cliente_id: int, db: Session = Depends(get_db)):
    cliente = db.query(User).filter(User.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    db.delete(cliente)
    db.commit()
    return

app.include_router(router)