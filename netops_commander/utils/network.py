"""General network utilities."""
import socket
import ipaddress
import subprocess
import platform
import re
from typing import Dict, List, Tuple, Optional, Any
from ..utils.logger import get_logger

log = get_logger(__name__)


def get_active_interface() -> Dict[str, Any]:
    """Return active network interface info."""
    info = {
        "name": "Unknown", "ip": "127.0.0.1", "netmask": "255.0.0.0",
        "gateway": None, "dns": [], "mac": None, "is_up": False,
    }
    try:
        import psutil
        stats = psutil.net_if_addrs()
        try:
            gateways = psutil.net_if_gateways()
            default_gw = gateways.get("default", {})
        except Exception:
            default_gw = {}
        for iface, addrs in stats.items():
            if iface in ("lo", "Loopback") or "Loopback" in iface:
                continue
            for addr in addrs:
                if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                    info["name"] = iface
                    info["ip"] = addr.address
                    info["netmask"] = addr.netmask
                    info["mac"] = addr.address if addr.family == psutil.AF_LINK else info.get("mac")
                    info["is_up"] = True
                    gwf = default_gw.get(socket.AF_INET)
                    if gwf:
                        info["gateway"] = gwf[0]
                    break
            if info["gateway"]:
                break
    except Exception as e:
        log.error(f"Interface detection error: {e}")
    return info


def get_public_ip(timeout: float = 5.0) -> Optional[str]:
    """Fetch public IP from multiple endpoints."""
    from ..config import get_config
    endpoints = get_config().get("app.public_ip_endpoints", [])
    for ep in endpoints:
        try:
            import urllib.request
            with urllib.request.urlopen(ep, timeout=timeout) as r:
                return r.read().decode("utf-8").strip()
        except Exception:
            continue
    return None


def get_dns_servers() -> List[str]:
    servers = []
    try:
        if platform.system().lower() == "windows":
            result = subprocess.run(
                ["netsh", "interface", "ip", "show", "dns"],
                capture_output=True, text=True, timeout=5,
            )
            for line in result.stdout.splitlines():
                m = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
                if m:
                    servers.append(m.group(1))
        else:
            with open("/etc/resolv.conf") as f:
                for line in f:
                    if line.startswith("nameserver"):
                        servers.append(line.split()[1])
    except Exception as e:
        log.debug(f"DNS read failed: {e}")
    return list(dict.fromkeys(servers))[:4]


def get_local_subnet() -> str:
    info = get_active_interface()
    ip = info["ip"]
    mask = info["netmask"] or "255.255.255.0"
    try:
        net = ipaddress.IPv4Network(f"{ip}/{mask}", strict=False)
        return f"{net.network_address}/{net.prefixlen}"
    except Exception:
        return f"{ip}/24"