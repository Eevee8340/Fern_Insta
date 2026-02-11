import unittest
import sys
import os

# Add root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.config_manager import ConfigManager

class TestConfig(unittest.TestCase):
    def test_singleton(self):
        c1 = ConfigManager()
        c2 = ConfigManager()
        self.assertIs(c1, c2)

    def test_load_main(self):
        cm = ConfigManager()
        conf = cm.main_config
        self.assertIn("BOT_NAME", conf)
        self.assertIn("BOT_HANDLE", conf)

if __name__ == '__main__':
    unittest.main()
