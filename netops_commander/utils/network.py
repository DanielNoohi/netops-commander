"""General network utilities."""
import socket
import ipaddress
import subprocess
import platform
import re
from typing import Dict, List, Optional, Any
from ..utils.logger import get_logger

log = get_logger(__name__)


def _default_gateway_from_psutil(psutil_mod) -> Optional[str]:
    """Best-effort default IPv4 gateway. psutil APIs differ by version."""
    # Modern psutil: net_if_gateways()
    try:
        gateways = psutil_mod.net_if_gateways()
        default = gateways.get("default", {})
        gwf = default.get(socket.AF_INET)
        if gwf:
            return gwf[0]
        # Fallback: first AF_INET gateway entry across interfaces
        for key, entries in gateways.items():
            if key == "default":
                continue
            if isinstance(entries, list):
                for entry in entries:
                    if entry and entry[0]:
                        return entry[0]
    except AttributeError:
        pass
    except Exception as e:
        log.debug(f"psutil gateways unavailable: {e}")

    # Older / alternate: net_if_stats + route parse
    return _gateway_from_os()


def _gateway_from_os() -> Optional[str]:
    """Parse OS routing table for default gateway (no shell=True)."""
    system = platform.system().lower()
    try:
        if system == "windows":
            proc = subprocess.run(
                ["route", "print", "0.0.0.0"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            for line in proc.stdout.splitlines():
                parts = line.split()
                # 0.0.0.0  0.0.0.0  <gateway>  <iface>  <metric>
                if len(parts) >= 3 and parts[0] == "0.0.0.0" and parts[1] == "0.0.0.0":
                    cand = parts[2]
                    try:
                        ipaddress.ip_address(cand)
                        return cand
                    except ValueError:
                        continue
        else:
            proc = subprocess.run(
                ["ip", "route", "show", "default"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            m = re.search(r"default via (\S+)", proc.stdout)
            if m:
                return m.group(1)
            proc = subprocess.run(
                ["route", "-n"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            for line in proc.stdout.splitlines():
                parts = line.split()
                if parts and parts[0] == "0.0.0.0" and len(parts) >= 2:
                    return parts[1]
    except Exception as e:
        log.debug(f"OS gateway parse failed: {e}")
    return None


def get_active_interface() -> Dict[str, Any]:
    """Return active network interface info (IP, netmask, gateway, MAC)."""
    info: Dict[str, Any] = {
        "name": "Unknown",
        "ip": "127.0.0.1",
        "netmask": "255.0.0.0",
        "gateway": None,
        "dns": [],
        "mac": None,
        "is_up": False,
    }
    try:
        import psutil

        stats = psutil.net_if_addrs()
        gateway = _default_gateway_from_psutil(psutil)
        info["gateway"] = gateway

        # AF_LINK constant varies; fall back to socket constant if present
        af_link = getattr(psutil, "AF_LINK", None)
        if af_link is None:
            af_link = getattr(socket, "AF_LINK", None)
        if af_link is None:
            af_link = getattr(socket, "AF_PACKET", 17)

        for iface, addrs in stats.items():
            if iface in ("lo", "Loopback") or "Loopback" in iface:
                continue

            ipv4 = None
            mac = None
            netmask = None
            for addr in addrs:
                if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                    ipv4 = addr.address
                    netmask = addr.netmask
                elif af_link is not None and addr.family == af_link:
                    # Skip empty / placeholder MACs
                    if addr.address and addr.address not in ("00:00:00:00:00:00",):
                        mac = addr.address

            if ipv4:
                info["name"] = iface
                info["ip"] = ipv4
                info["netmask"] = netmask or info["netmask"]
                info["mac"] = mac
                info["is_up"] = True
                # Prefer interface that matches default gateway path when possible
                if gateway:
                    break
        # If still no MAC on chosen iface, leave None (do not invent)
    except Exception as e:
        log.error(f"Interface detection error: {e}")
    return info


def get_public_ip(timeout: float = 5.0) -> Optional[str]:
    """Fetch public IP from multiple endpoints."""
    from ..config import get_config
    import urllib.request

    endpoints = get_config().get(
        "app.public_ip_endpoints",
        [
            "https://api.ipify.org",
            "https://ifconfig.me/ip",
            "https://icanhazip.com",
        ],
    )
    for url in endpoints:
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:
                text = resp.read().decode("utf-8", errors="ignore").strip()
                ipaddress.ip_address(text)
                return text
        except Exception:
            continue
    return None


def get_dns_servers() -> List[str]:
    """Return configured DNS servers (best-effort, cross-platform)."""
    servers: List[str] = []
    system = platform.system().lower()
    try:
        if system == "windows":
            proc = subprocess.run(
                ["ipconfig", "/all"],
                capture_output=True,
                text=True,
                timeout=8,
                check=False,
            )
            for line in proc.stdout.splitlines():
                if "DNS Servers" in line or "DNS-Server" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        cand = parts[1].strip()
                        try:
                            ipaddress.ip_address(cand)
                            servers.append(cand)
                        except ValueError:
                            pass
                elif servers and line.strip() and ":" not in line[:20]:
                    cand = line.strip()
                    try:
                        ipaddress.ip_address(cand)
                        servers.append(cand)
                    except ValueError:
                        pass
        else:
            try:
                with open("/etc/resolv.conf", encoding="utf-8") as f:
                    for line in f:
                        if line.startswith("nameserver"):
                            parts = line.split()
                            if len(parts) >= 2:
                                servers.append(parts[1])
            except OSError:
                pass
    except Exception as e:
        log.debug(f"DNS detection failed: {e}")
    # Dedupe preserve order
    seen = set()
    out = []
    for s in servers:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def get_local_subnet() -> str:
    """Guess local CIDR from active interface IP/netmask."""
    info = get_active_interface()
    try:
        net = ipaddress.IPv4Network(f"{info['ip']}/{info['netmask']}", strict=False)
        return str(net)
    except Exception:
        return "192.168.1.0/24"
