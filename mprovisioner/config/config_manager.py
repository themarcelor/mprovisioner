import yaml
import logging
import os


logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO"))
log = logging.getLogger(__name__)


class ConfigManager(object):
    """
    Manage the environments configuration
    """

    _instance = None

    def __new__(cls, config_file, dry_run=False):
        if cls._instance is None:
            log.info(f"Creating the ConfigManager object utilizing: {config_file}")
            cls._instance = super(ConfigManager, cls).__new__(cls)
            # initialize instance attributes
            cls._instance.config_file = config_file
            cls._instance.dry_run = dry_run
        return cls._instance

    def parse_config(self, environment):
        """
        Parses the configuration parameters from environments.yaml

        Args:
            environment (str): Utilized to retrieve a specific configuration block

        Return:
            dictionary containing the merged settings from 'commons' and the selected environment

        Raises:
            YAMLError if the parsing function finds an invalid YAML
        """
        with open(self.config_file) as cf:
            log.info(f"Parsing config from environment: {environment}")

            try:
                data = yaml.load(cf, Loader=yaml.FullLoader)
            except yaml.YAMLError as ye:
                log.error(f"Error while parsing YAML file: {self.config_file}")
                raise ye

            commons_settings = data["commons"]
            env_settings = data["environments"][environment]["server"]

            env_settings.update(commons_settings)

        return env_settings
