"""Headless GUI smoke tests (QT_QPA_PLATFORM=offscreen)."""
import os
import sys
import tempfile
import unittest

# Must set before Qt imports
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def _isolate(tmpdir: str):
    import netops_commander.config as cfgmod
    import netops_commander.database.database as dbmod

    db_path = os.path.join(tmpdir, "gui.db")
    cfg_path = os.path.join(tmpdir, "config.yaml")
    with open(cfg_path, "w", encoding="utf-8") as f:
        f.write(
            "app:\n"
            f"  database_path: \"{db_path.replace(os.sep, '/')}\"\n"
            "  theme: dark\n"
        )
    dbmod.reset_engine()
    cfgmod._global_config = cfgmod.ConfigManager(cfg_path)
    dbmod.init_database()
    return dbmod


class GuiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            from PySide6.QtWidgets import QApplication
        except ImportError:
            raise unittest.SkipTest("PySide6 not installed")
        cls._td = tempfile.TemporaryDirectory()
        cls.dbmod = _isolate(cls._td.name)
        cls.app = QApplication.instance() or QApplication([])

    @classmethod
    def tearDownClass(cls):
        cls.dbmod.reset_engine()
        cls._td.cleanup()

    def test_main_window_builds(self):
        from netops_commander.gui.main_window import MainWindow

        win = MainWindow()
        self.assertTrue(win.windowTitle().startswith("NetOps Commander"))
        self.assertIsNotNone(win.dashboard)
        self.assertIsNotNone(win.device_table)
        win.close()

    def test_scan_dialog_validates(self):
        from netops_commander.gui.scan_dialog import ScanDialog

        dlg = ScanDialog(initial_cidr="192.168.1.0/24")
        self.assertTrue(dlg._ok.isEnabled())
        dlg.cidr_edit.setText("not-a-cidr")
        self.assertFalse(dlg._ok.isEnabled())
        dlg.cidr_edit.setText("10.0.0.0/8")  # too large
        self.assertFalse(dlg._ok.isEnabled())
        dlg.close()

    def test_settings_dialog_builds(self):
        from netops_commander.gui.settings_dialog import SettingsDialog

        dlg = SettingsDialog()
        self.assertEqual(dlg.windowTitle(), "Settings")
        dlg.close()

    def test_sparkline_samples(self):
        from netops_commander.gui.widgets.sparkline import LatencySparkline

        w = LatencySparkline()
        w.add_sample(10.0)
        w.add_sample(None)
        w.add_sample(20.5)
        self.assertEqual(len(w.samples), 3)
        w.clear()
        self.assertEqual(w.samples, [])
        w.close()

    def test_device_table_empty_state(self):
        from netops_commander.gui.device_table import DeviceTableWidget

        table = DeviceTableWidget()
        self.assertEqual(table.table.rowCount(), 0)
        # isVisible() is False until shown in a window; isHidden tracks setVisible
        self.assertFalse(table.empty_label.isHidden())
        self.assertTrue(table.table.isHidden())
        table.close()

    def test_ping_tool_builds(self):
        from netops_commander.gui.tools.ping_tool import PingToolWidget

        dlg = PingToolWidget(initial_host="127.0.0.1")
        self.assertEqual(dlg.host.text(), "127.0.0.1")
        self.assertIsNotNone(dlg.sparkline)
        dlg.close()


if __name__ == "__main__":
    unittest.main()
