"""Unit tests for traceroute / TLS / DNS / launchers / wifi formatters."""
import os
import sys
import unittest
from datetime import timezone
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from netops_commander.utils.traceroute import build_traceroute_cmd
from netops_commander.utils.tls_check import _parse_cert_time, _name_to_str
from netops_commander.utils.dns_lookup import lookup_a_aaaa, lookup_records
from netops_commander.utils.wifi import format_wifi_summary
from netops_commander.utils.launchers import open_http
from netops_commander.utils.validators import validate_targets
from netops_commander.constants import PORT_SCAN_MAX_TARGETS


class TracerouteTests(unittest.TestCase):
    def test_build_cmd_windows(self):
        with patch("netops_commander.utils.traceroute.platform.system", return_value="Windows"):
            cmd = build_traceroute_cmd("1.1.1.1", max_hops=15)
            self.assertEqual(cmd[0], "tracert")
            self.assertIn("1.1.1.1", cmd)
            self.assertIn("15", cmd)

    def test_build_cmd_linux(self):
        with patch("netops_commander.utils.traceroute.platform.system", return_value="Linux"):
            cmd = build_traceroute_cmd("example.com", max_hops=20)
            self.assertEqual(cmd[0], "traceroute")
            self.assertIn("-n", cmd)


class TlsHelperTests(unittest.TestCase):
    def test_parse_cert_time(self):
        dt = _parse_cert_time("Aug  6 12:00:00 2026 GMT")
        self.assertIsNotNone(dt)
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.tzinfo, timezone.utc)
        self.assertIsNone(_parse_cert_time(None))
        self.assertIsNone(_parse_cert_time("not-a-date"))

    def test_name_to_str(self):
        name = ((("commonName", "example.com"),), (("organizationName", "Ex"),))
        s = _name_to_str(name)
        self.assertIn("commonName=example.com", s)
        self.assertEqual(_name_to_str(None), "")


class DnsTests(unittest.TestCase):
    def test_lookup_a_aaaa_mocked(self):
        import socket
        fake = [
            (socket.AF_INET, 1, 6, "", ("1.2.3.4", 0)),
            (socket.AF_INET6, 1, 6, "", ("2001:db8::1", 0, 0, 0)),
        ]
        with patch("netops_commander.utils.dns_lookup.socket.getaddrinfo", return_value=fake):
            data = lookup_a_aaaa("example.com")
        self.assertEqual(data["A"], ["1.2.3.4"])
        self.assertEqual(data["AAAA"], ["2001:db8::1"])

    def test_lookup_records_a(self):
        with patch(
            "netops_commander.utils.dns_lookup.lookup_a_aaaa",
            return_value={"A": ["9.9.9.9"], "AAAA": []},
        ):
            source, lines = lookup_records("dns.google", "A")
        self.assertEqual(source, "stdlib")
        self.assertTrue(any("9.9.9.9" in ln for ln in lines))


class WifiFormatTests(unittest.TestCase):
    def test_format_connected(self):
        s = format_wifi_summary(
            {"connected": True, "ssid": "HomeLAN", "signal": "80%", "channel": "6"}
        )
        self.assertIn("HomeLAN", s)
        self.assertIn("80%", s)

    def test_format_note(self):
        s = format_wifi_summary({"connected": False, "note": "No wireless interface"})
        self.assertIn("No wireless", s)


class LauncherTests(unittest.TestCase):
    def test_open_http(self):
        with patch("netops_commander.utils.launchers.webbrowser.open") as opener:
            ok, msg = open_http("192.168.1.1", https=True)
        self.assertTrue(ok)
        opener.assert_called_once()
        self.assertIn("https://192.168.1.1", opener.call_args[0][0])

    def test_open_http_empty(self):
        ok, msg = open_http("  ")
        self.assertFalse(ok)


class ValidatorExtraTests(unittest.TestCase):
    def test_validate_targets_cap(self):
        ok, msg = validate_targets(list(range(PORT_SCAN_MAX_TARGETS + 1)))
        self.assertFalse(ok)
        ok2, _ = validate_targets(["a", "b"])
        self.assertTrue(ok2)


if __name__ == "__main__":
    unittest.main()
