from sqlalchemy import Column, Integer, Float, DateTime, func, ForeignKey
from database import Base

class MonthlyProjection(Base):
    __tablename__ = "monthly_projections"

    id = Column(Integer, primary_key=True, index=True)
    plant_id = Column(Integer, nullable=False)
    month = Column(Integer, nullable=False)
    year = Column(Integer, nullable=False)
    projection_kwh = Column(Float, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    cliente_id = Column(Integer, ForeignKey("users.id"))