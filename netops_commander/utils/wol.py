"""Wake-on-LAN magic packet helpers."""
from __future__ import annotations

import socket
from typing import Tuple

from ..constants import WOL_BROADCAST, WOL_UDP_PORT


def normalize_mac(mac: str) -> bytes:
    """Normalize MAC string to 6 raw bytes. Raises ValueError if invalid."""
    text = mac.strip().replace("-", "").replace(":", "").replace(".", "")
    if len(text) != 12 or any(c not in "0123456789abcdefABCDEF" for c in text):
        raise ValueError(f"Invalid MAC address: {mac!r}")
    return bytes.fromhex(text)


def is_valid_mac(mac: str) -> bool:
    try:
        normalize_mac(mac)
        return True
    except ValueError:
        return False


def build_magic_packet(mac: str) -> bytes:
    """Build a standard WOL magic packet (6x FF + MAC repeated 16 times)."""
    mac_bytes = normalize_mac(mac)
    return b"\xff" * 6 + mac_bytes * 16


def send_magic_packet(
    mac: str,
    broadcast: str = WOL_BROADCAST,
    port: int = WOL_UDP_PORT,
) -> Tuple[bool, str]:
    """Send a WOL magic packet. Returns (ok, message)."""
    try:
        packet = build_magic_packet(mac)
    except ValueError as e:
        return False, str(e)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.sendto(packet, (broadcast, port))
        return True, f"Sent WOL packet for {mac} → {broadcast}:{port}"
    except OSError as e:
        return False, f"Failed to send WOL packet: {e}"
