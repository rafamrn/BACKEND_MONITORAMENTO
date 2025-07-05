from fastapi import FastAPI, Depends, HTTPException, status, Query, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import FileResponse
from fastapi.encoders import jsonable_encoder
from fastapi.security import OAuth2PasswordRequestForm
from starlette.middleware.trustedhost import TrustedHostMiddleware
from utils import get_integracao_por_plataforma
from services.performance_service import (
    get_performance_diaria,
    get_performance_7dias,
    get_performance_30dias
)
from clients.isolarcloud_client import ApiSolarCloud
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
from typing import List, Optional
from uuid import uuid4
from clients.deye_client import ApiDeye
import os
import secrets
# Internos
from database import SessionLocal, get_db
from modelos import User, Integracao, Convite
from esquemas import (
    UserCreate, IntegracaoCreate, IntegracaoOut, ClienteCreate, ClienteOut,
    RegistroComConvite, RegisterRequest
)
from utils import agrupar_usinas_por_nome, hash_password, verify_password
from auth import create_access_token, decode_access_token
from dependencies import get_current_admin_user, get_current_user
from config.settings import settings
from services.performance_service import (
    get_performance_diaria, get_performance_7dias, get_performance_30dias
)
from models.usina import UsinaModel
from clients.isolarcloud_client import ApiSolarCloud
from clients.huawei_client import ApiHuawei
from clients.deye_client import ApiDeye
from routers import projection
from routes import convites
from rotas import solarcloud_routes
from passlib.hash import bcrypt
from clients.isolarcloud_client import ApiSolarCloud
from services.scheduler import start_scheduler



# ============== ⬇ APP ==============
app = FastAPI()

# ============== ⬇ MIDDLEWARES ==============
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "https://frontendmonitoramento-production.up.railway.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if os.getenv("ENV") == "production":
    app.add_middleware(HTTPSRedirectMiddleware)

app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# ============== ⬇ CLIENTES DAS APIS ==============
huawei = ApiHuawei(settings.HUAWEI_USER, settings.HUAWEI_PASS)
deye = ApiDeye(settings.DEYE_USER, settings.DEYE_PASS, settings.DEYE_APPID, settings.DEYE_APPSECRET)



start_scheduler()

# ============== ⬇ ROTAS PRINCIPAIS ==============

@app.get("/usina", response_model=List[UsinaModel])
def listar_usinas(usuario_logado: User = Depends(get_current_user), db: Session = Depends(get_db)):
    usinas = []

    # DEYE
    try:
        integracao_deye = get_integracao_por_plataforma(db, usuario_logado.id, "deye")
        print("🔎 Integração Deye:", integracao_deye)
        if integracao_deye:
            deye = ApiDeye(
                username=integracao_deye.username,
                password=integracao_deye.senha
            )
            usinas += deye.get_usinas()
        else:
            print("⚠️ Integração Deye não encontrada.")
    except Exception as e:
        print("⚠️ Erro ao buscar usinas da Deye:", str(e))

    # SUNGROW (nome correto no banco é "Sungrow")
    try:
        print(f"🔎 Tentando buscar integração Sungrow para cliente ID: {usuario_logado.id}")
        integracao_solar = get_integracao_por_plataforma(db, usuario_logado.id, "Sungrow")
        print("🔁 Resultado:", integracao_solar)
        if integracao_solar:
            isolarcloud = ApiSolarCloud(db=db, integracao=integracao_solar)
            usinas += isolarcloud.get_usinas()
        else:
            print("⚠️ Integração Sungrow não encontrada para o cliente.")
    except Exception as e:
        print("⚠️ Erro ao buscar usinas da Sungrow:", str(e))

    print(f"📦 Total de usinas retornadas: {len(usinas)}")
    return agrupar_usinas_por_nome(usinas)




@app.get("/geracoes_diarias")
def listar_geracoes_diarias(
    db: Session = Depends(get_db),
    usuario_logado: User = Depends(get_current_user)
):
    geracoes = []

    try:
        integracao_solar = get_integracao_por_plataforma(db, usuario_logado.id, "Sungrow")
        if integracao_solar:
            isolarcloud = ApiSolarCloud(db=db, integracao=integracao_solar)
            geracoes += isolarcloud.get_geracao().get("diario", [])
        else:
            print("⚠️ Integração Sungrow não encontrada")
    except Exception as e:
        print("⚠️ Erro ao obter geração da iSolarCloud:", str(e))

    try:
        integracao_deye = get_integracao_por_plataforma(db, usuario_logado.id, "deye")
        if integracao_deye:
            deye = ApiDeye(
                username=integracao_deye.username,
                password=integracao_deye.senha
            )
            geracoes += deye.get_geracao().get("diario", [])
        else:
            print("⚠️ Integração Deye não encontrada")
    except Exception as e:
        print("⚠️ Erro ao obter geração da Deye:", str(e))

    return geracoes


@app.get("/performance_diaria")
def performance_diaria(
    db: Session = Depends(get_db),
    usuario_logado: User = Depends(get_current_user)
):
    integracao_sungrow = get_integracao_por_plataforma(db, usuario_logado.id, "Sungrow")
    integracao_deye = get_integracao_por_plataforma(db, usuario_logado.id, "deye")

    sungrow_api = None
    deye_api = None

    if integracao_sungrow:
        sungrow_api = ApiSolarCloud(db=db, integracao=integracao_sungrow)

    if integracao_deye:
        deye_api = ApiDeye(
            username=integracao_deye.username,
            password=integracao_deye.senha
        )

    return get_performance_diaria(sungrow_api, deye_api, db, usuario_logado.id)



@app.get("/performance_7dias")
def performance_7dias(db: Session = Depends(get_db), usuario_logado: User = Depends(get_current_user)):
    integracao_sungrow = get_integracao_por_plataforma(db, usuario_logado.id, "Sungrow")
    integracao_deye = get_integracao_por_plataforma(db, usuario_logado.id, "deye")

    sungrow_api = None
    deye_api = None

    if integracao_sungrow:
        sungrow_api = ApiSolarCloud(db=db, integracao=integracao_sungrow)

    if integracao_deye:
        deye_api = ApiDeye(
            username=integracao_deye.username,
            password=integracao_deye.senha
        )

    return get_performance_7dias(sungrow_api, deye_api, db, usuario_logado.id)

@app.get("/performance_30dias")
def performance_30dias(
    db: Session = Depends(get_db),
    usuario_logado: User = Depends(get_current_user)
):
    integracao_sungrow = get_integracao_por_plataforma(db, usuario_logado.id, "Sungrow")
    integracao_deye = get_integracao_por_plataforma(db, usuario_logado.id, "deye")

    sungrow_api = None
    deye_api = None

    if integracao_sungrow:
        sungrow_api = ApiSolarCloud(db=db, integracao=integracao_sungrow)
    if integracao_deye:
        deye_api = ApiDeye(
            username=integracao_deye.username,
            password=integracao_deye.senha
        )

    return get_performance_30dias(sungrow_api, deye_api, db, usuario_logado.id)


@app.get("/dados_tecnicos")
def obter_dados_tecnicos(
    plant_id: int,
    db: Session = Depends(get_db),
    usuario_logado: User = Depends(get_current_user)
):
    integracao = db.query(Integracao).filter_by(cliente_id=usuario_logado.id, plataforma="sungrow").first()

    if not integracao:
        raise HTTPException(status_code=404, detail="Integração da plataforma Sungrow não encontrada")

    isolarcloud = ApiSolarCloud(db=db, integracao=integracao)
    return isolarcloud.get_dados_tecnicos(plant_id=plant_id)

@app.get("/api/geracao/mensal")
def obter_geracao_mensal(
    date: str = Query(..., regex=r"^\d{4}-\d{2}$"),
    plant_id: int = Query(...),
    db: Session = Depends(get_db),
    usuario_logado: User = Depends(get_current_user)
):
    integracao = db.query(Integracao).filter_by(cliente_id=usuario_logado.id, plataforma="sungrow").first()
    if not integracao:
        raise HTTPException(status_code=404, detail="Integração da plataforma Sungrow não encontrada")

    isolarcloud = ApiSolarCloud(db=db, integracao=integracao)
    return isolarcloud.get_geracao_mes(data=date, plant_id=plant_id)

@app.get("/api/geracao/anual")
def obter_geracao_anual(
    year: str = Query(..., regex=r"^\d{4}$"),
    plant_id: int = Query(...),
    db: Session = Depends(get_db),
    usuario_logado: User = Depends(get_current_user)
):
    integracao = db.query(Integracao).filter_by(cliente_id=usuario_logado.id, plataforma="sungrow").first()
    if not integracao:
        raise HTTPException(status_code=404, detail="Integração da plataforma Sungrow não encontrada")

    isolarcloud = ApiSolarCloud(db=db, integracao=integracao)
    return isolarcloud.get_geracao_ano(ano=year, plant_id=plant_id)

@app.get("/protegido")
def rota_protegida(usuario_logado: User = Depends(get_current_user)):
    return {"msg": f"Bem-vindo, {usuario_logado.email}!"}

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    access_token = create_access_token(data={"sub": user.email}, is_admin=user.is_admin)
    return {"access_token": access_token, "token_type": "bearer"}

# ============== ⬇ REGISTRO DE CLIENTE COM CONVITE ==============

@app.post("/register")
def register_user(request: RegisterRequest, db: Session = Depends(get_db)):
    convite = db.query(Convite).filter(Convite.token == str(request.token)).first()
    if not convite:
        raise HTTPException(status_code=400, detail="Token inválido ou não encontrado")
    if convite.usado:
        raise HTTPException(status_code=400, detail="Token já utilizado")
    if convite.expiracao < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Token expirado")

    # Encontra o usuário já criado com email do convite
    user = db.query(User).filter(User.email == convite.email).first()
    if not user:
        raise HTTPException(status_code=400, detail="Usuário não encontrado para este convite")

    # Atualiza os dados do usuário criado via /clientes
    user.name = request.name.strip()
    user.hashed_password = bcrypt.hash(request.password)
    user.email = request.email.strip()  # Novo e-mail real do cliente

    convite.usado = True
    db.commit()
    db.refresh(user)

    return {"message": "Usuário registrado com sucesso"}
    

# ============== ⬇ CLIENTES ==============

@app.post("/clientes")
def criar_cliente(cliente: ClienteCreate, db: Session = Depends(get_db)):
    email_fake = f"{secrets.token_hex(8)}@placeholder.com"
    senha_fake = secrets.token_urlsafe(12)
    hashed = bcrypt.hash(senha_fake)

    novo_cliente = User(
        email=email_fake,
        hashed_password=hashed,
        name=None,
        company=cliente.company,
        cnpj=cliente.cnpj,
        telefone=cliente.telefone,
        plan=cliente.plan,
        status="active",
        payment_status="up-to-date",
        created_at=date.today(),
        last_payment=date.today(),
        is_admin=False,
    )
    db.add(novo_cliente)
    db.commit()
    db.refresh(novo_cliente)

    token = str(uuid4())
    convite = Convite(
        email=email_fake,
        token=token,
        cliente_id=novo_cliente.id,
        usado=False,
        expiracao=datetime.utcnow() + timedelta(days=7),
        criado_em=datetime.utcnow(),
    )
    db.add(convite)
    db.commit()

    return {
        "message": "Cliente criado com sucesso",
        "id": novo_cliente.id,
        "token": token
    }

@app.get("/clientes", response_model=List[ClienteOut])
def listar_clientes(db: Session = Depends(get_db)):
    return db.query(User).all()

@app.delete("/clientes/{cliente_id}", status_code=204)
def deletar_cliente(cliente_id: int, db: Session = Depends(get_db)):
    cliente = db.query(User).filter(User.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    db.delete(cliente)
    db.commit()

# ============== ⬇ INTEGRAÇÕES ==============

integracao_router = APIRouter(prefix="/integracoes", tags=["Integrações"])

@integracao_router.post("/")
def criar_integracao(integracao: IntegracaoCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    nova = Integracao(
        cliente_id=user.id,
        nome=user.name,
        plataforma=integracao.plataforma,
        username=integracao.username,
        senha=integracao.senha,
    )
    db.add(nova)
    db.commit()
    db.refresh(nova)
    return {"message": "Integração salva com sucesso", "id": nova.id}

@integracao_router.get("/", response_model=List[IntegracaoOut])
def listar_integracoes(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Integracao).filter(Integracao.cliente_id == user.id).all()

# ============== ⬇ ADMIN ==============

admin_router = APIRouter(prefix="/admin", tags=["Admin"])

@admin_router.get("/integracoes", response_model=List[IntegracaoOut])
def listar_integracoes_admin(db: Session = Depends(get_db), usuario_logado: User = Depends(get_current_admin_user)):
    integracoes = db.query(Integracao).all()
    resultado = []
    for i in integracoes:
        integracao_dict = jsonable_encoder(i)
        integracao_dict["nome"] = i.cliente.name if i.cliente else None
        resultado.append(integracao_dict)
    return resultado

@admin_router.put("/integracoes/{id}")
def atualizar_chaves_admin(id: int, payload: dict, db: Session = Depends(get_db), usuario: User = Depends(get_current_admin_user)):
    integracao = db.query(Integracao).filter(Integracao.id == id).first()
    if not integracao:
        raise HTTPException(status_code=404, detail="Integração não encontrada")
    integracao.appkey = payload.get("appkey")
    integracao.x_access_key = payload.get("x_access_key")
    db.commit()
    db.refresh(integracao)
    return {"detail": "Chaves atualizadas com sucesso"}

# ============== ⬇ INCLUDES ==============

app.include_router(projection.router)
app.include_router(convites.router)
app.include_router(integracao_router)
app.include_router(admin_router)
app.include_router(solarcloud_routes.router)

