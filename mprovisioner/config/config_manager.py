import yaml
import logging
import os


logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)

#
class ConfigManager(object):
  #
  _instance = None

  def __new__(cls, config_file, dry_run = False):
    if cls._instance is None:
      log.info(f'Creating the ConfigManager object utilizing: {config_file}')
      cls._instance = super(ConfigManager, cls).__new__(cls)
      # initialize instance attributes
      cls._instance.config_file = config_file
      cls._instance.dry_run = dry_run
    return cls._instance

  def parse_config(self, environment):
    with open(self.config_file) as cf:
      log.info(f'Parsing config from environment: {environment}')
      data = yaml.load(cf, Loader=yaml.FullLoader)

      # TODO: Re-organize the data here to feed this info to the aws api layer
    
    return data
