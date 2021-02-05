from abc import ABC, abstractmethod
 
class APIHandler(ABC):
 
    def __init__(self, api_rate_limit_retry_max=3):
        self.api_rate_limit_retry_max = api_rate_limit_retry_max
        super().__init__()
    
    @abstractmethod
    def provision_vms(self):
        pass
