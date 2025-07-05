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
                sungrow = get_api_instance(db, cliente_id)
                deye = None  # adapte para outras plataformas
                get_performance_diaria(sungrow, deye, db, cliente_id)
                get_performance_7dias(sungrow, deye, db, cliente_id)
                get_performance_30dias(sungrow, deye, db, cliente_id)
                logger.info(f"✅ Performance atualizada para cliente {cliente_id}")
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
