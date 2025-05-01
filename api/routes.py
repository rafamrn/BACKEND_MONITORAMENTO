from fastapi import APIRouter, HTTPException, Query
from clients.isolarcloud_client import iSolarCloudClient
from services.power_plant_service import PowerPlantService

router = APIRouter()

# Substitua com suas credenciais reais
client = iSolarCloudClient("contato@rms7energia.com", "rms7@SUNGROW")
service = PowerPlantService(client)

@router.get("/dados")
def get_dados(ps_id: str = Query(...)):
    try:
        return service.get_performance_data(ps_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))