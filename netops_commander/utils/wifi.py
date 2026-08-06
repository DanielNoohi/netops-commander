"""Wi-Fi status helpers (best-effort, OS-specific)."""
from __future__ import annotations

import platform
import re
import subprocess
from typing import Any, Dict, Optional

from .logger import get_logger

log = get_logger(__name__)


def get_wifi_info() -> Dict[str, Any]:
    """
    Return Wi-Fi association info when available.

    Keys: connected (bool), ssid, signal, radio, bssid, channel, note
    """
    info: Dict[str, Any] = {
        "connected": False,
        "ssid": None,
        "signal": None,
        "radio": None,
        "bssid": None,
        "channel": None,
        "note": None,
    }
    system = platform.system().lower()
    try:
        if system == "windows":
            return _wifi_windows(info)
        if system == "linux":
            return _wifi_linux(info)
        if system == "darwin":
            info["note"] = "macOS Wi-Fi details not implemented"
            return info
    except Exception as e:
        log.debug("wifi info failed: %s", e)
        info["note"] = str(e)
    return info


def _wifi_windows(info: Dict[str, Any]) -> Dict[str, Any]:
    proc = subprocess.run(
        ["netsh", "wlan", "show", "interfaces"],
        capture_output=True,
        text=True,
        timeout=8,
        check=False,
    )
    text = proc.stdout or ""
    if not text.strip():
        info["note"] = "No WLAN interface (or netsh unavailable)"
        return info

    def _field(pattern: str) -> Optional[str]:
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        return m.group(1).strip() if m else None

    state = (_field(r"^\s*State\s*:\s*(.+)$") or "").lower()
    ssid = _field(r"^\s*SSID\s*:\s*(.+)$")
    signal = _field(r"^\s*Signal\s*:\s*(.+)$")
    radio = _field(r"^\s*Radio type\s*:\s*(.+)$")
    bssid = _field(r"^\s*BSSID\s*:\s*(.+)$")
    channel = _field(r"^\s*Channel\s*:\s*(.+)$")

    info["ssid"] = ssid if ssid and ssid != "" else None
    info["signal"] = signal
    info["radio"] = radio
    info["bssid"] = bssid
    info["channel"] = channel
    info["connected"] = "connected" in state and bool(info["ssid"])
    if not info["connected"] and "disconnected" in state:
        info["note"] = "Wi-Fi adapter present, not connected"
    elif not info["ssid"] and "there is no wireless" in text.lower():
        info["note"] = "No wireless interface"
    return info


def _wifi_linux(info: Dict[str, Any]) -> Dict[str, Any]:
    # Prefer nmcli; use ASCII unit separator to avoid BSSID colon splits
    proc = subprocess.run(
        ["nmcli", "-t", "-f", "ACTIVE,SSID,SIGNAL,CHAN", "dev", "wifi"],
        capture_output=True,
        text=True,
        timeout=8,
        check=False,
    )
    if proc.returncode == 0 and proc.stdout.strip():
        for line in proc.stdout.splitlines():
            parts = line.split(":")
            if len(parts) >= 2 and parts[0] == "yes":
                info["connected"] = True
                info["ssid"] = parts[1] or None
                if len(parts) > 2 and parts[2]:
                    info["signal"] = f"{parts[2]}%"
                if len(parts) > 3 and parts[3]:
                    info["channel"] = parts[3]
                return info
        info["note"] = "Wi-Fi networks visible, none active"
        return info
    info["note"] = "nmcli unavailable"
    return info


def format_wifi_summary(info: Optional[Dict[str, Any]] = None) -> str:
    info = info or get_wifi_info()
    if info.get("connected") and info.get("ssid"):
        bits = [f"SSID {info['ssid']}"]
        if info.get("signal"):
            bits.append(str(info["signal"]))
        if info.get("channel"):
            bits.append(f"ch {info['channel']}")
        return " · ".join(bits)
    return info.get("note") or "Not connected / N/A"
