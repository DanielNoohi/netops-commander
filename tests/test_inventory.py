"""Inventory purge / reconcile / retention (isolated temp DB)."""
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def _isolate(tmpdir: str):
    import netops_commander.config as cfgmod
    import netops_commander.database.database as dbmod

    db_path = os.path.join(tmpdir, "test.db")
    cfg_path = os.path.join(tmpdir, "config.yaml")
    with open(cfg_path, "w", encoding="utf-8") as f:
        f.write(f"app:\n  database_path: \"{db_path.replace(os.sep, '/')}\"\n")
    dbmod.reset_engine()
    cfgmod._global_config = cfgmod.ConfigManager(cfg_path)
    dbmod.init_database()
    return dbmod


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.dbmod = _isolate(self._td.name)

    def tearDown(self):
        self.dbmod.reset_engine()
        self._td.cleanup()

    def test_purge_ghost_devices(self):
        from netops_commander.core.scanner import purge_ghost_devices
        from netops_commander.database.database import session_scope
        from netops_commander.database.models import Device

        with session_scope() as s:
            s.add(Device(ip_address="192.168.1.10", mac_address=None, online=True))
            s.add(Device(ip_address="192.168.1.11", mac_address="", online=True))
            s.add(
                Device(
                    ip_address="192.168.1.12",
                    mac_address="AA:BB:CC:DD:EE:FF",
                    online=True,
                )
            )
            s.add(
                Device(
                    ip_address="192.168.1.13",
                    mac_address=None,
                    online=True,
                    notes="keep me",
                )
            )

        removed = purge_ghost_devices()
        self.assertEqual(removed, 2)
        with session_scope() as s:
            rows = s.query(Device).all()
            ips = {d.ip_address for d in rows}
            self.assertEqual(ips, {"192.168.1.12", "192.168.1.13"})
            kept = s.query(Device).filter_by(ip_address="192.168.1.13").one()
            self.assertFalse(kept.online)

    def test_reconcile_removes_stale_cidr_hosts(self):
        from netops_commander.core.discovery import DiscoveredDevice
        from netops_commander.core.scanner import reconcile_scan_results
        from netops_commander.database.database import session_scope
        from netops_commander.database.models import Device

        with session_scope() as s:
            s.add(
                Device(
                    ip_address="10.0.0.1",
                    mac_address="11:22:33:44:55:66",
                    online=True,
                )
            )
            s.add(
                Device(
                    ip_address="10.0.0.2",
                    mac_address="11:22:33:44:55:77",
                    online=True,
                )
            )
            s.add(
                Device(
                    ip_address="10.0.0.3",
                    mac_address="11:22:33:44:55:88",
                    online=True,
                    is_monitored=True,
                )
            )

        found = [
            DiscoveredDevice(
                ip_address="10.0.0.1",
                online=True,
                mac_address="11:22:33:44:55:66",
            )
        ]
        saved, removed = reconcile_scan_results("10.0.0.0/24", found)
        self.assertGreaterEqual(saved, 1)
        self.assertEqual(removed, 1)  # .2 deleted; .3 curated → offline
        with session_scope() as s:
            ips = {d.ip_address: d for d in s.query(Device).all()}
            self.assertIn("10.0.0.1", ips)
            self.assertNotIn("10.0.0.2", ips)
            self.assertIn("10.0.0.3", ips)
            self.assertFalse(ips["10.0.0.3"].online)

    def test_retention_purge(self):
        from netops_commander.core.maintenance import purge_old_history
        from netops_commander.database.database import session_scope
        from netops_commander.database.models import Alert, Device, MonitorResult, ScanHistory

        old = datetime.now(timezone.utc) - timedelta(days=60)
        fresh = datetime.now(timezone.utc) - timedelta(days=1)
        with session_scope() as s:
            d = Device(ip_address="10.1.1.1", mac_address="AA:BB:CC:DD:EE:01", online=True)
            s.add(d)
            s.flush()
            s.add(ScanHistory(device_id=d.id, scan_type="ping", timestamp=old, online=True))
            s.add(ScanHistory(device_id=d.id, scan_type="ping", timestamp=fresh, online=True))
            s.add(MonitorResult(device_id=d.id, timestamp=old, online=True))
            s.add(Alert(alert_type="offline", severity="warning", message="old", timestamp=old))
            s.add(Alert(alert_type="offline", severity="warning", message="new", timestamp=fresh))

        counts = purge_old_history(days=30)
        self.assertEqual(counts["scan_history"], 1)
        self.assertEqual(counts["monitor_results"], 1)
        self.assertEqual(counts["alerts"], 1)
        with session_scope() as s:
            self.assertEqual(s.query(ScanHistory).count(), 1)
            self.assertEqual(s.query(Alert).count(), 1)


if __name__ == "__main__":
    unittest.main()
