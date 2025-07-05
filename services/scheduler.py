from apscheduler.schedulers.background import BackgroundScheduler
from services.performance_service import (
    get_performance_diaria,
    get_performance_7dias,
    get_performance_30dias
)
from dependencies import get_db
from database import SessionLocal
from utils import get_api_instance
import time

def executar_rotina_1h():
    print("🕐 Executando cálculo de performance diária às 01h...")
    db = SessionLocal()
    clientes = db.execute("SELECT id FROM users").fetchall()
    
    for cliente in clientes:
        cliente_id = cliente[0]
        try:
            sungrow = get_api_instance(db, cliente_id)
            deye = None  # adapte se necessário
            get_performance_diaria(sungrow, deye, db, cliente_id)
            get_performance_7dias(sungrow, deye, db, cliente_id)
            get_performance_30dias(sungrow, deye, db, cliente_id)
            print(f"✅ Performance atualizada para cliente {cliente_id}")
        except Exception as e:
            print(f"❌ Erro ao calcular performance para cliente {cliente_id}: {e}")
    
    db.close()

scheduler = BackgroundScheduler()
scheduler.add_job(executar_rotina_1h, 'cron', hour=1, minute=0)  # 01:00 da manhã
scheduler.start()
