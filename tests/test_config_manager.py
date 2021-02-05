import unittest
from mprovisioner.config.config_manager import ConfigManager

class ConfigManagerTestCase(unittest.TestCase):
    """Tests for config_manager.py"""

    def test_parse_config(self):
        cm = ConfigManager("./tests/fake_environments.yaml")
        config_data = cm.parse_config("dev")

        self.assertEqual(
          {
            "instance_type": "t2.micro",
            "min_count": 1,
            "max_count": 1
          },
          config_data["environments"]["dev"]["server"],
                'Must return a dev server configuration containing the instance type, min and max values',
       )


if __name__ == "__main__":
    unittest.main(verbosity=2)
