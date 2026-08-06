"""Monitor edge-triggered alert transitions (temp DB)."""
import os
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def _isolate(tmpdir: str):
    import netops_commander.config as cfgmod
    import netops_commander.database.database as dbmod

    db_path = os.path.join(tmpdir, "test.db")
    cfg_path = os.path.join(tmpdir, "config.yaml")
    with open(cfg_path, "w", encoding="utf-8") as f:
        f.write(
            "app:\n"
            f"  database_path: \"{db_path.replace(os.sep, '/')}\"\n"
            "  monitor_max_devices: 5\n"
            "  monitoring_interval: 60\n"
        )
    dbmod.reset_engine()
    cfgmod._global_config = cfgmod.ConfigManager(cfg_path)
    dbmod.init_database()
    return dbmod


class MonitorAlertTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.dbmod = _isolate(self._td.name)

    def tearDown(self):
        self.dbmod.reset_engine()
        self._td.cleanup()

    async def test_offline_and_recovery_edges(self):
        from netops_commander.core.monitoring import MonitorController
        from netops_commander.database.database import session_scope
        from netops_commander.database.models import Alert, Device

        with session_scope() as s:
            d = Device(ip_address="10.9.9.9", mac_address="AA:BB:CC:DD:EE:FF", online=True)
            s.add(d)
            s.flush()
            device_id = d.id

        ctl = MonitorController(interval=60)
        ctl.add_device(device_id, "10.9.9.9")
        ctl._prev_online[device_id] = True
        events = []
        ctl.alert_callback = lambda sev, msg, did=None: events.append((sev, msg, did))

        with patch(
            "netops_commander.core.monitoring.async_ping",
            new_callable=AsyncMock,
            return_value=(False, None),
        ):
            await ctl._run_pass()

        with session_scope() as s:
            alerts = s.query(Alert).all()
            self.assertEqual(len(alerts), 1)
            self.assertEqual(alerts[0].alert_type, "offline")
        self.assertTrue(any(e[0] == "critical" for e in events))

        # Recovery edge
        events.clear()
        with patch(
            "netops_commander.core.monitoring.async_ping",
            new_callable=AsyncMock,
            return_value=(True, 12.0),
        ):
            await ctl._run_pass()

        with session_scope() as s:
            types = [a.alert_type for a in s.query(Alert).all()]
            self.assertIn("recovery", types)

    async def test_high_latency_edge_once(self):
        from netops_commander.core.monitoring import MonitorController, HIGH_LATENCY_MS
        from netops_commander.database.database import session_scope
        from netops_commander.database.models import Alert, Device

        with session_scope() as s:
            d = Device(ip_address="10.9.9.8", mac_address="AA:BB:CC:DD:EE:01", online=True)
            s.add(d)
            s.flush()
            device_id = d.id

        ctl = MonitorController(interval=60)
        ctl.add_device(device_id, "10.9.9.8")
        ctl._prev_online[device_id] = True

        with patch(
            "netops_commander.core.monitoring.async_ping",
            new_callable=AsyncMock,
            return_value=(True, HIGH_LATENCY_MS + 50),
        ):
            await ctl._run_pass()
            await ctl._run_pass()  # second pass should not re-alert

        with session_scope() as s:
            highs = s.query(Alert).filter_by(alert_type="high_latency").all()
            self.assertEqual(len(highs), 1)

    def test_max_devices_cap(self):
        from netops_commander.core.monitoring import MonitorController

        ctl = MonitorController(interval=60)
        ctl._max_devices = 2
        ctl.add_device(1, "1.1.1.1")
        ctl.add_device(2, "1.1.1.2")
        ctl.add_device(3, "1.1.1.3")
        self.assertEqual(len(ctl.devices), 2)


if __name__ == "__main__":
    unittest.main()
