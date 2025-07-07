from pydantic import BaseModel
from typing import List

class ProjectionItem(BaseModel):
    month: int
    kwh: float

class MonthlyProjectionCreate(BaseModel):
    plant_id: int
    year: int
    projections: List[ProjectionItem]
