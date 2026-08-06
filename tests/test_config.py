"""ConfigManager unit tests (no GUI)."""
import copy
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from netops_commander.config import ConfigManager, DEFAULT_CONFIG


class TestConfigManager(unittest.TestCase):
    def test_set_theme_persists_and_does_not_mutate_defaults(self):
        defaults_theme = copy.deepcopy(DEFAULT_CONFIG)["app"]["theme"]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.yaml"
            cfg = ConfigManager(str(path))
            self.assertEqual(cfg.get("app.theme"), defaults_theme)
            cfg.set("app.theme", "light")
            self.assertEqual(cfg.get("app.theme"), "light")
            self.assertTrue(path.exists())
            # Reload from disk
            cfg2 = ConfigManager(str(path))
            self.assertEqual(cfg2.get("app.theme"), "light")
        # DEFAULT_CONFIG must stay pristine (deepcopy in __init__)
        self.assertEqual(DEFAULT_CONFIG["app"]["theme"], defaults_theme)


if __name__ == "__main__":
    unittest.main()
