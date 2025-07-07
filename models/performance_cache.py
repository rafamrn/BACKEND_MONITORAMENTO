from sqlalchemy import Column, Integer, String, DateTime, JSON
from sqlalchemy.sql import func
from database import Base

class PerformanceCache(Base):
    __tablename__ = "performance_cache"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, nullable=False)
    plant_id = Column(Integer, nullable=True)
    tipo = Column(String, nullable=False)  # diaria / 7dias / 30dias
    resultado_json = Column(JSON, nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
