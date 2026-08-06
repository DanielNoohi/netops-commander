"""Network utility parsing (no live network)."""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from netops_commander.utils.network import _gateway_from_os
from netops_commander.utils.wifi import _wifi_windows


class GatewayParseTests(unittest.TestCase):
    def test_windows_route_print(self):
        stdout = """
===========================================================================
Network Destination        Netmask          Gateway       Interface  Metric
          0.0.0.0          0.0.0.0    192.168.10.1   192.168.10.180     25
"""
        proc = MagicMock(stdout=stdout, returncode=0)
        with (
            patch("netops_commander.utils.network.platform.system", return_value="Windows"),
            patch("netops_commander.utils.network.subprocess.run", return_value=proc),
        ):
            gw = _gateway_from_os()
        self.assertEqual(gw, "192.168.10.1")

    def test_linux_ip_route(self):
        proc = MagicMock(stdout="default via 10.0.0.1 dev eth0\n", returncode=0)
        with (
            patch("netops_commander.utils.network.platform.system", return_value="Linux"),
            patch("netops_commander.utils.network.subprocess.run", return_value=proc),
        ):
            gw = _gateway_from_os()
        self.assertEqual(gw, "10.0.0.1")


class WifiParseTests(unittest.TestCase):
    def test_windows_netsh_connected(self):
        stdout = """
There is 1 interface on the system:

    Name                   : Wi-Fi
    State                  : connected
    SSID                   : OfficeNet
    BSSID                  : aa:bb:cc:dd:ee:ff
    Signal                 : 88%
    Radio type             : 802.11ax
    Channel                : 36
"""
        proc = MagicMock(stdout=stdout, returncode=0)
        with patch("netops_commander.utils.wifi.subprocess.run", return_value=proc):
            info = _wifi_windows({})
        self.assertTrue(info["connected"])
        self.assertEqual(info["ssid"], "OfficeNet")
        self.assertEqual(info["signal"], "88%")
        self.assertEqual(info["channel"], "36")


if __name__ == "__main__":
    unittest.main()
