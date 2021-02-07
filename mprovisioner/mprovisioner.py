import boto3
from config.config_manager import ConfigManager
from cloud.aws import AWSAPIHandler
import logging
import os


logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)


class MProvisioner(object):
    """
    Marcelo's Provisioner manages environments' configuration and
    interact with multiple Cloud providers to provision the underlying infrastructure for your services
    """

    def get_config_manager(self, config_file):
        return ConfigManager(config_file)

    def provision(self, params):
        cm = self.get_config_manager(params["config_file"])
        environment_config = cm.parse_config(params["environment"])

        cloud = AWSAPIHandler(environment_config)
        cloud.provision_vms()


if __name__ == "__main__":
    params = {"config_file": "./environments.yaml", "environment": "dev"}
    mp = MProvisioner()
    mp.provision(params)
