from fastapi import FastAPI, Depends, HTTPException, status, Query, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import FileResponse
from fastapi.encoders import jsonable_encoder
from fastapi.security import OAuth2PasswordRequestForm
from starlette.middleware.trustedhost import TrustedHostMiddleware
from services.performance_service import calcular_performance_diaria, calcular_performance_7dias, calcular_performance_30dias
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
from services.performance_service import (
    get_performance_diaria, get_performance_7dias, get_performance_30dias
)
from clients.isolarcloud_client import ApiSolarCloud
from clients.huawei_client import ApiHuawei
from clients.deye_client import ApiDeye
from routers import projection
from routes import convites
from rotas import solarcloud_routes
from passlib.hash import bcrypt
from clients.isolarcloud_client import ApiSolarCloud
from services.scheduler import start_scheduler
from utils import hash_sha256
from clients.huawei_client import ApiHuawei
import traceback

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

start_scheduler()

# ============== ⬇ ROTAS PRINCIPAIS ==============

@app.get("/alarmes_atuais/todos")
def listar_todos_atuais(db: Session = Depends(get_db), usuario_logado: User = Depends(get_current_user)):
    integracao = db.query(Integracao).filter_by(cliente_id=usuario_logado.id, plataforma="Sungrow").first()
    if not integracao:
        raise HTTPException(status_code=404, detail="Integração não encontrada")

    solarcloud = ApiSolarCloud(db=db, integracao=integracao)
    return solarcloud.get_todos_alarmes_atuais()

@app.get("/alarmes_historico/todos")
def listar_todos_historico(db: Session = Depends(get_db), usuario_logado: User = Depends(get_current_user)):
    integracao = db.query(Integracao).filter_by(cliente_id=usuario_logado.id, plataforma="Sungrow").first()
    if not integracao:
        raise HTTPException(status_code=404, detail="Integração não encontrada")

    solarcloud = ApiSolarCloud(db=db, integracao=integracao)
    return solarcloud.get_todos_alarmes_historico()


@app.get("/alarmes_atuais")
def obter_alarmes_atuais(
    plant_id: int = Query(...),
    db: Session = Depends(get_db),
    usuario_logado: User = Depends(get_current_user)
):
    integracao = db.query(Integracao).filter_by(cliente_id=usuario_logado.id, plataforma="Sungrow").first()

    if not integracao:
        raise HTTPException(status_code=404, detail="Integração da plataforma Sungrow não encontrada")

    isolarcloud = ApiSolarCloud(db=db, integracao=integracao)

    try:
        return isolarcloud.get_alarmes_atuais(plant_id=plant_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter alarmes atuais: {str(e)}")

@app.get("/alarmes_historico")
def obter_alarmes_historico(
    plant_id: int = Query(...),
    db: Session = Depends(get_db),
    usuario_logado: User = Depends(get_current_user)
):
    integracao = db.query(Integracao).filter_by(cliente_id=usuario_logado.id, plataforma="Sungrow").first()

    if not integracao:
        raise HTTPException(status_code=404, detail="Integração da plataforma Sungrow não encontrada")

    isolarcloud = ApiSolarCloud(db=db, integracao=integracao)

    try:
        return isolarcloud.get_alarmes_historico(plant_id=plant_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao obter alarmes históricos: {str(e)}")

@app.get("/usina")
def listar_usinas(
    usuario_logado: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    usinas = []

    # Busca todas as integrações desse usuário
    integracoes = db.query(Integracao).filter_by(cliente_id=usuario_logado.id).all()

    if not integracoes:
        print("⚠️ Nenhuma integração encontrada para o cliente.")
        return []

    for integracao in integracoes:
        try:
            print(f"🔍 Verificando integração: {integracao.plataforma}")
            plataforma = integracao.plataforma.lower()

            if plataforma == "sungrow":
                client = ApiSolarCloud(db=db, integracao=integracao)
            elif plataforma == "deye":
                client = ApiDeye(db=db, integracao=integracao)
            else:
                print(f"⚠️ Plataforma não suportada: {plataforma}")
                continue

            usinas += client.get_usinas()

        except Exception as e:
            print(f"❌ Erro ao buscar usinas da plataforma {integracao.plataforma}:", e)
            continue

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
    apis = []
    integracao_sungrow = get_integracao_por_plataforma(db, usuario_logado.id, "Sungrow")
    integracao_deye = get_integracao_por_plataforma(db, usuario_logado.id, "Deye")

    if integracao_sungrow:
        apis.append(ApiSolarCloud(db=db, integracao=integracao_sungrow))
    if integracao_deye:
        apis.append(ApiDeye(integracao=integracao_deye, db=db))

    return get_performance_diaria(apis, db, usuario_logado.id)



@app.get("/performance_7dias")
def performance_7dias(
    db: Session = Depends(get_db),
    usuario_logado: User = Depends(get_current_user)
):
    apis = []
    integracao_sungrow = get_integracao_por_plataforma(db, usuario_logado.id, "Sungrow")
    integracao_deye = get_integracao_por_plataforma(db, usuario_logado.id, "Deye")

    if integracao_sungrow:
        apis.append(ApiSolarCloud(db=db, integracao=integracao_sungrow))
    if integracao_deye:
        apis.append(ApiDeye(integracao=integracao_deye, db=db))

    return get_performance_7dias(apis, db, usuario_logado.id)

@app.get("/performance_30dias")
def performance_30dias(
    db: Session = Depends(get_db),
    usuario_logado: User = Depends(get_current_user)
):
    apis = []
    integracao_sungrow = get_integracao_por_plataforma(db, usuario_logado.id, "Sungrow")
    integracao_deye = get_integracao_por_plataforma(db, usuario_logado.id, "Deye")

    if integracao_sungrow:
        apis.append(ApiSolarCloud(db=db, integracao=integracao_sungrow))
    if integracao_deye:
        apis.append(ApiDeye(integracao=integracao_deye, db=db))

    return get_performance_30dias(apis, db, usuario_logado.id)

@app.get("/dados_tecnicos")
def obter_dados_tecnicos(
    plant_id: int,
    db: Session = Depends(get_db),
    usuario_logado: User = Depends(get_current_user)
):
    integracao = db.query(Integracao).filter_by(cliente_id=usuario_logado.id, plataforma="Sungrow").first()

    if not integracao:
        raise HTTPException(status_code=404, detail="Integração da plataforma Sungrow não encontrada")

    isolarcloud = ApiSolarCloud(db=db, integracao=integracao)
    return isolarcloud.get_dados_tecnicos(plant_id=plant_id)

@app.get("/api/geracao")
def obter_geracao_diaria(
    period: str = Query(..., regex="^day$"),
    date: str = Query(..., regex=r"^\d{4}-\d{2}-\d{2}$"),
    plant_id: int = Query(...),
    db: Session = Depends(get_db),
    usuario_logado: User = Depends(get_current_user)
):
    if period != "day":
        raise HTTPException(status_code=400, detail="Parâmetro 'period' deve ser 'day'")

    integracao = db.query(Integracao).filter_by(cliente_id=usuario_logado.id, plataforma="Sungrow").first()
    if not integracao:
        raise HTTPException(status_code=404, detail="Integração da plataforma Sungrow não encontrada")

    isolarcloud = ApiSolarCloud(db=db, integracao=integracao)
    return isolarcloud.get_geracao(period="day", date=date, plant_id=plant_id)


@app.get("/api/geracao/mensal")
def obter_geracao_mensal(
    date: str = Query(..., regex=r"^\d{4}-\d{2}$"),
    plant_id: int = Query(...),
    db: Session = Depends(get_db),
    usuario_logado: User = Depends(get_current_user)
):
    integracao = db.query(Integracao).filter_by(cliente_id=usuario_logado.id, plataforma="Sungrow").first()
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
    integracao = db.query(Integracao).filter_by(cliente_id=usuario_logado.id, plataforma="Sungrow").first()
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

from utils import hash_sha256  # certifique-se de importar isso no topo
from utils import get_apis_ativas
@app.post("/forcar_calculo_performance")
def forcar_performance(
    db: Session = Depends(get_db),
    usuario_logado: User = Depends(get_current_user)
):
    from services.performance_service import (
        get_performance_diaria, get_performance_7dias, get_performance_30dias
    )
    from utils import get_apis_ativas

    apis = get_apis_ativas(db, usuario_logado.id)  # ← busca todas APIs daquele cliente

    if not apis:
        raise HTTPException(status_code=404, detail="Nenhuma integração ativa encontrada.")

    print(f"🚀 Recalculando performance para cliente_id={usuario_logado.id}")

    diaria = get_performance_diaria(apis, db, usuario_logado.id, forcar=True)
    dias7 = get_performance_7dias(apis, db, usuario_logado.id, forcar=True)
    dias30 = get_performance_30dias(apis, db, usuario_logado.id, forcar=True)

    return {
        "mensagem": f"Performance recalculada para o cliente.",
        "diaria": diaria,
        "7dias": dias7,
        "30dias": dias30
    }

@integracao_router.post("/")
def criar_integracao(
    integracao: IntegracaoCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user)
):
    # Cria a integração com a senha pura
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

    # Se for Deye, converte a senha em SHA256 e atualiza
    if integracao.plataforma.lower() == "deye":
        nova.senha = hash_sha256(integracao.senha)
        db.commit()

    return {"message": "Integração salva com sucesso", "id": nova.id}


@integracao_router.get("/", response_model=List[IntegracaoOut])
def listar_integracoes(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.query(Integracao).filter(Integracao.cliente_id == user.id).all()

# ============== ⬇ ADMIN ==============

admin_router = APIRouter(prefix="/admin", tags=["Admin"])

@admin_router.delete("/integracoes/{integracao_id}")
def deletar_integracao(
    integracao_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user)  # garante acesso apenas a admins
):
    integracao = db.query(Integracao).filter(Integracao.id == integracao_id).first()

    if not integracao:
        raise HTTPException(status_code=404, detail="Integração não encontrada")

    db.delete(integracao)
    db.commit()
    return {"message": "Integração removida com sucesso"}

@admin_router.get("/integracoes", response_model=List[IntegracaoOut])
def listar_integracoes_admin(db: Session = Depends(get_db), usuario_logado: User = Depends(get_current_admin_user)):
    integracoes = db.query(Integracao).all()
    resultado = []
    for i in integracoes:
        integracao_dict = jsonable_encoder(i)
        integracao_dict["nome"] = i.cliente.name if i.cliente else None
        integracao_dict["appid"] = i.appid
        integracao_dict["appsecret"] = i.appsecret
        resultado.append(integracao_dict)
    return resultado

@admin_router.put("/integracoes/{id}")
def atualizar_chaves_admin(id: int, payload: dict, db: Session = Depends(get_db), usuario: User = Depends(get_current_admin_user)):
    integracao = db.query(Integracao).filter(Integracao.id == id).first()
    if not integracao:
        raise HTTPException(status_code=404, detail="Integração não encontrada")
    integracao.appkey = payload.get("appkey")
    integracao.x_access_key = payload.get("x_access_key")
    integracao.appid = payload.get("appid")
    integracao.appsecret = payload.get("appsecret")
    
    db.commit()
    db.refresh(integracao)
    return {"detail": "Chaves atualizadas com sucesso"}


# ============== ⬇ TESTES ==============

router = APIRouter()

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from models.monthly_projection import MonthlyProjection
from esquemas import ProjecaoMensalCreate
from dependencies import get_current_user
from database import get_db
from services.performance_service import (
    get_performance_diaria,
    get_performance_7dias,
    get_performance_30dias
)
from utils import get_apis_ativas
import traceback

router = APIRouter()

@router.post("/projecoes/salvar_e_recalcular")
def salvar_e_recalcular_projecao(
    data: ProjecaoMensalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    try:
        plant_id = data.plant_id
        year = data.year

        # 🔁 Remove projeções existentes
        db.query(MonthlyProjection).filter_by(
            plant_id=plant_id,
            year=year,
            cliente_id=current_user.id
        ).delete()

        # 💾 Salva novas projeções
        for proj in data.projections:
            nova = MonthlyProjection(
                plant_id=plant_id,
                month=proj.month,
                year=year,
                projection_kwh=proj.kwh,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                cliente_id=current_user.id
            )
            db.add(nova)
        db.commit()

        print(f"✅ Projeções salvas com sucesso. Recalculando performance para plant_id={plant_id}")

        # ⚙️ Recalcular performance apenas dessa usina
        apis = get_apis_ativas(db, current_user.id)
        diaria = get_performance_diaria(apis, db, current_user.id, forcar=True, apenas_plant_id=plant_id)
        dias7 = get_performance_7dias(apis, db, current_user.id, forcar=True, apenas_plant_id=plant_id)
        dias30 = get_performance_30dias(apis, db, current_user.id, forcar=True, apenas_plant_id=plant_id)

        return {
            "message": "Projeções atualizadas e performance recalculada com sucesso.",
            "plant_id": plant_id,
            "diaria": diaria,
            "7dias": dias7,
            "30dias": dias30
        }

    except Exception as e:
        db.rollback()
        print("❌ Erro ao salvar projeções e recalcular:")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="Erro ao recalcular performance para a usina.")


@router.get("/huawei/testar_token")
def testar_token_huawei(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # Busca a integração Huawei do usuário autenticado
    integracao = db.query(Integracao).filter_by(
        cliente_id=user.id,
        plataforma="Huawei"
    ).first()

    if not integracao:
        raise HTTPException(status_code=404, detail="Integração Huawei não encontrada.")

    api = ApiHuawei(integracao, db)
    try:
        token = api.get_token_valido()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "message": "Token Huawei válido",
        "token": token,
        "token_updated_at": integracao.token_updated_at
    }

# ============== ⬇ INCLUDES ==============

app.include_router(projection.router)
app.include_router(convites.router)
app.include_router(integracao_router)
app.include_router(admin_router)
app.include_router(solarcloud_routes.router)

