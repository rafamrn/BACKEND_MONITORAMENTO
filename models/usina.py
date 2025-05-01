from pydantic import BaseModel
from typing import Optional

class UsinaModel(BaseModel):
    ps_id: int
    ps_name: str
    location: Optional[str]
    capacidade: Optional[float]
    curr_power: float
    total_energy: Optional[float]
    today_energy: Optional[float]
    co2_total: Optional[float]
    income_total: Optional[float]
    ps_fault_status: Optional[int]
