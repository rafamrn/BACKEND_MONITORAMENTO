from fastapi import FastAPI
from utils import agrupar_usinas_por_nome
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from config.settings import settings
from clients.isolarcloud_client import ApiSolarCloud
from clients.huawei_client import ApiHuawei
from clients.deye_client import ApiDeye
from models.usina import UsinaModel
from routers import projection
from fastapi import Depends
from database import get_db
from sqlalchemy.orm import Session
from services.performance_service import get_performance_diaria


isolarcloud = ApiSolarCloud(settings.ISOLAR_USER, settings.ISOLAR_PASS)
huawei = ApiHuawei(settings.HUAWEI_USER, settings.HUAWEI_PASS)
deye = ApiDeye(settings.DEYE_USER, settings.DEYE_PASS, settings.DEYE_APPID, settings.DEYE_APPSECRET)

app = FastAPI()

app.include_router(projection.router)

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

@app.get("/usina", response_model=List[UsinaModel])
def listar_usinas():
    usinas = huawei.get_usinas() + deye.get_usinas() + isolarcloud.get_usinas()
    return agrupar_usinas_por_nome(usinas)

@app.get("/geracoes_diarias")
def listar_geracoes_diarias():
    return isolarcloud.get_geracao()

@app.get("/performance_diaria")
def performance_diaria(db: Session = Depends(get_db)):
    return get_performance_diaria(isolarcloud, db)
