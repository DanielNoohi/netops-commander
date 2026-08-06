"""Alert severity helpers."""
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from netops_commander.core.alerts import severity_for


class AlertSeverityTests(unittest.TestCase):
    def test_known_types(self):
        self.assertEqual(severity_for("offline"), "critical")
        self.assertEqual(severity_for("recovery"), "info")
        self.assertEqual(severity_for("high_latency"), "warning")

    def test_unknown_defaults_info(self):
        self.assertEqual(severity_for("not_a_real_type"), "info")


if __name__ == "__main__":
    unittest.main()
