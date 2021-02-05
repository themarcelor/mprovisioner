import boto3
from config.config_manager import ConfigManager
from cloud.aws import AWSAPIHandler

# 
class MProvisioner(object):
  # 
  def get_config_manager(self, config_file):
    return ConfigManager(config_file)

  def provision(self, params):
    cm = self.get_config_manager(params['config_file'])
    print(cm.parse_config("dev"))

    cloud = AWSAPIHandler()
    cloud.provision_vms()

if __name__ == '__main__':
  params = {
    "config_file": "./environments.yaml"
  }
  mp = MProvisioner()
  mp.provision(params)

