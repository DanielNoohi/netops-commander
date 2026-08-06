"""ARP / ghost-host discovery rules (no live network)."""
import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from netops_commander.core.discovery import (
    DiscoveredDevice,
    _enrich_host,
    _is_real_host_mac,
    _norm_mac,
    discover_host,
)


class MacHelpersTests(unittest.TestCase):
    def test_norm_and_real_mac(self):
        self.assertEqual(_norm_mac("aa-bb-cc-dd-ee-ff"), "AA:BB:CC:DD:EE:FF")
        self.assertTrue(_is_real_host_mac("34:5A:60:43:EC:C1"))
        self.assertFalse(_is_real_host_mac(None))
        self.assertFalse(_is_real_host_mac("00:00:00:00:00:00"))
        self.assertFalse(_is_real_host_mac("FF:FF:FF:FF:FF:FF"))
        # Multicast bit set
        self.assertFalse(_is_real_host_mac("01:00:5E:00:00:01"))


class DiscoverHostTests(unittest.IsolatedAsyncioTestCase):
    def _cfg_require_arp(self):
        cfg = MagicMock()
        cfg.get.side_effect = lambda key, default=None: True if key == "app.require_arp" else default
        return cfg

    async def test_ghost_icmp_rejected_when_require_arp(self):
        iface = {"ip": "192.168.10.180", "mac": "34:5A:60:43:EC:C1", "gateway": "192.168.10.1"}
        with (
            patch("netops_commander.utils.network.get_active_interface", return_value=iface),
            patch("netops_commander.config.get_config", return_value=self._cfg_require_arp()),
            patch("netops_commander.core.discovery.async_ping", new_callable=AsyncMock) as ping,
            patch(
                "netops_commander.core.discovery._lookup_mac_after_ping",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "netops_commander.core.discovery.get_mac_via_arp_lookup",
                new_callable=AsyncMock,
                return_value="78:9A:18:A3:2A:47",
            ),
            patch(
                "netops_commander.core.discovery.async_tcp_connect",
                new_callable=AsyncMock,
            ) as tcp,
        ):
            ping.return_value = (True, 1.2)
            device = await discover_host("192.168.10.50")
            self.assertFalse(device.online)
            self.assertTrue(device.extras.get("ghost_icmp"))
            tcp.assert_not_called()

    async def test_proxy_arp_rejected(self):
        iface = {"ip": "192.168.10.180", "mac": "34:5A:60:43:EC:C1", "gateway": "192.168.10.1"}
        gw_mac = "78:9A:18:A3:2A:47"
        with (
            patch("netops_commander.utils.network.get_active_interface", return_value=iface),
            patch("netops_commander.config.get_config", return_value=self._cfg_require_arp()),
            patch("netops_commander.core.discovery.async_ping", new_callable=AsyncMock) as ping,
            patch(
                "netops_commander.core.discovery._lookup_mac_after_ping",
                new_callable=AsyncMock,
                return_value=gw_mac,
            ),
            patch(
                "netops_commander.core.discovery.get_mac_via_arp_lookup",
                new_callable=AsyncMock,
                return_value=gw_mac,
            ),
        ):
            ping.return_value = (True, 0.8)
            device = await discover_host("192.168.10.99")
            self.assertFalse(device.online)
            self.assertTrue(device.extras.get("proxy_arp") or device.extras.get("ghost_icmp"))

    async def test_confirmed_arp_host_online(self):
        iface = {"ip": "192.168.10.180", "mac": "34:5A:60:43:EC:C1", "gateway": "192.168.10.1"}
        host_mac = "8C:DE:F9:A3:CB:7C"
        with (
            patch("netops_commander.utils.network.get_active_interface", return_value=iface),
            patch("netops_commander.config.get_config", return_value=self._cfg_require_arp()),
            patch("netops_commander.core.discovery.async_ping", new_callable=AsyncMock) as ping,
            patch(
                "netops_commander.core.discovery._lookup_mac_after_ping",
                new_callable=AsyncMock,
                return_value=host_mac,
            ),
            patch(
                "netops_commander.core.discovery.get_mac_via_arp_lookup",
                new_callable=AsyncMock,
                return_value="78:9A:18:A3:2A:47",
            ),
            patch(
                "netops_commander.core.discovery._enrich_host",
                new_callable=AsyncMock,
            ),
        ):
            ping.return_value = (True, 2.0)
            device = await discover_host("192.168.10.103")
            self.assertTrue(device.online)
            self.assertEqual(device.mac_address, host_mac)

    async def test_enrichment_timeout_does_not_raise(self):
        device = DiscoveredDevice(
            ip_address="192.168.10.1",
            online=True,
            mac_address="78:9A:18:A3:2A:47",
        )

        async def boom(*_a, **_k):
            raise TimeoutError("dns slow")

        with (
            patch("netops_commander.core.discovery.reverse_dns_lookup", side_effect=boom),
            patch("netops_commander.core.discovery.get_hostname_smb", side_effect=boom),
        ):
            await _enrich_host(device)
        self.assertTrue(device.online)
        self.assertEqual(device.mac_address, "78:9A:18:A3:2A:47")


if __name__ == "__main__":
    unittest.main()
