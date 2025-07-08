from apscheduler.schedulers.background import BackgroundScheduler
from services.performance_service import (
    get_performance_diaria,
    get_performance_7dias,
    get_performance_30dias
)
from database import SessionLocal
from integracoes.solarcloud_service import get_api_instance
import logging

# Configura logging em vez de prints (melhor para produção)
logger = logging.getLogger("scheduler")
logger.setLevel(logging.INFO)

def executar_rotina_1h():
    logger.info("🕐 Executando cálculo de performance às 01h...")
    db = SessionLocal()

    try:
        clientes = db.execute("SELECT id FROM users").fetchall()
        for cliente in clientes:
            cliente_id = cliente[0]
            try:
                # Busca todas as integrações desse cliente
                integracoes = db.execute(
                    "SELECT plataforma, username, senha FROM integracoes WHERE cliente_id = :cid",
                    {"cid": cliente_id}
                ).fetchall()

                apis = []
                for integracao in integracoes:
                    plataforma = integracao[0].lower()
                    username = integracao[1]
                    senha = integracao[2]

                    if plataforma == "sungrow":
                        from clients.isolarcloud_client import ApiSolarCloud
                        from utils import get_integracao_por_plataforma
                        integracao_solar = get_integracao_por_plataforma(db, cliente_id, "Sungrow")
                        if integracao_solar:
                            apis.append(ApiSolarCloud(db=db, integracao=integracao_solar))

                    elif plataforma == "deye":
                        from clients.deye_client import ApiDeye
                        apis.append(ApiDeye(username=username, password=senha, db=db))

                    # Adicione outras plataformas aqui no mesmo padrão

                if apis:
                    get_performance_diaria(apis, db, cliente_id)
                    get_performance_7dias(apis, db, cliente_id)
                    get_performance_30dias(apis, db, cliente_id)
                    logger.info(f"✅ Performance atualizada para cliente {cliente_id}")
                else:
                    logger.warning(f"⚠️ Nenhuma integração ativa para cliente {cliente_id}")

            except Exception as e:
                logger.error(f"❌ Erro ao calcular performance para cliente {cliente_id}: {e}")

    except Exception as e:
        logger.error(f"❌ Erro geral na rotina de performance: {e}")
    finally:
        db.close()


def start_scheduler():
    scheduler = BackgroundScheduler()
    scheduler.add_job(executar_rotina_1h, 'cron', hour=1, minute=0)
    scheduler.start()
    logger.info("✅ Scheduler iniciado com rotina diária às 01h")
