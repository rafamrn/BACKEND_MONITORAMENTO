from clients.base_client import BaseClient

class PowerPlantService:
    def __init__(self, client: BaseClient):
        self.client = client

    def get_performance_data(self, ps_id: str, period: str = "monthly"):
        device_info = self.client.get_device_info(ps_id)
        generation = self.client.get_generation_data(ps_id, period)
        # Aqui você pode aplicar cálculos, comparar com estimativas, etc.
        return {
            "device": device_info,
            "generation": generation
        }