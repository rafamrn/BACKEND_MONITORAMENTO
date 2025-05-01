from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# String de conexão usando os dados do Railway
DATABASE_URL = "postgresql://postgres:QmslMSrgrmtYoFfyGnzbHqbjmSMZnaXK@centerbeam.proxy.rlwy.net:51113/railway"

# Criando o engine e sessão
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base para os modelos
Base = declarative_base()

# Dependência para injeção nas rotas
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()