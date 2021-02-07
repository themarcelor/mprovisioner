from abc import ABC, abstractmethod


class APIHandler(ABC):
    """
    Abstract class to facilitate the injection of different cloud api providers
    """

    def __init__(self, environment_config, api_rate_limit_retry_max=3):
        self.environment_config = environment_config
        self.api_rate_limit_retry_max = api_rate_limit_retry_max
        super().__init__()

    @abstractmethod
    def provision_vms(self):
        pass
