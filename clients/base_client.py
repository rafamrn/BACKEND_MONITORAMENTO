from abc import ABC, abstractmethod

class BaseClient(ABC):
    @abstractmethod
    def authenticate(self):
        pass

    @abstractmethod
    def get_generation_data(self, ps_id: str, period: str = "monthly"):
        pass

    @abstractmethod
    def get_device_info(self, ps_id: str):
        pass