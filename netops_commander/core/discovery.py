"""
Network discovery module.

Implements device discovery using:
- ICMP ping
- ARP table (via OS-specific commands, never shell=True)
- TCP fallback for hosts that block ping
- Hostname lookup (NetBIOS + reverse DNS)
- MAC address via ARP
- Vendor lookup via IEEE OUI database (local cache)
"""

import asyncio
import json
import platform
import re
import subprocess
import socket
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple

from ..utils.logger import get_logger


log = get_logger(__name__)


@dataclass
class DiscoveredDevice:
    ip_address: str
    hostname: Optional[str] = None
    mac_address: Optional[str] = None
    vendor: Optional[str] = None
    device_type: Optional[str] = None
    os_info: Optional[str] = None
    online: bool = False
    latency_ms: Optional[float] = None
    open_ports: List[int] = field(default_factory=list)
    discovery_method: str = ""
    last_seen: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    extras: Dict[str, Any] = field(default_factory=dict)


# Common MAC vendor prefixes (small subset for offline fallback)
LOCAL_VENDORS: Dict[str, str] = {
    "00:50:56": "VMware",
    "00:0C:29": "VMware",
    "00:1C:42": "Parallels",
    "08:00:27": "VirtualBox",
    "00:1B:44": "Apple",
    "00:25:00": "Apple",
    "F0:F6:1C": "Apple",
    "00:1E:C2": "Apple",
    "00:1F:F3": "Apple",
    "60:33:4B": "Apple",
    "00:23:6C": "Apple",
    "B8:27:EB": "Raspberry Pi",
    "DC:A6:32": "Raspberry Pi",
    "E4:5F:01": "Raspberry Pi",
    "00:1A:2B": "Microsoft",
    "00:50:F2": "Microsoft",
    "7C:1E:52": "Microsoft",
    "60:45:BD": "Microsoft",
    "00:1D:D8": "Microsoft",
    "F8:1E:DF": "HP",
    "00:08:02": "HP",
    "00:14:38": "HP",
    "00:17:A4": "HP",
    "00:18:71": "HP",
    "00:1A:4B": "HP",
    "00:21:5A": "HP",
    "00:23:7D": "HP",
    "28:80:23": "HP",
    "00:0B:CD": "Dell",
    "00:13:72": "Dell",
    "00:14:22": "Dell",
    "00:18:8B": "Dell",
    "00:1C:C4": "Dell",
    "00:1D:09": "Dell",
    "00:1E:4F": "Dell",
    "00:1E:C9": "Dell",
    "20:47:47": "Dell",
    "B0:83:FE": "Dell",
    "EC:F4:BB": "Dell",
}


async def async_ping(host: str, timeout: float = 2.0) -> Tuple[bool, Optional[float]]:
    """
    Asynchronously ping a host and return (online, latency_ms).
    Returns latency=None if ping succeeded but latency couldn't be parsed.
    """
    is_windows = platform.system().lower() == "windows"
    timeout_ms = max(1, int(timeout * 1000))

    cmd = ["ping", "-n", "1", "-w", str(timeout_ms), host] if is_windows \
        else ["ping", "-c", "1", "-W", str(int(timeout)), host]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout + 2)
        out = stdout.decode("utf-8", errors="ignore")
        if proc.returncode == 0 or "TTL=" in out or "ttl=" in out:
            m = re.search(r"time[=<](\d+(?:\.\d+)?)\s*ms", out)
            latency = float(m.group(1)) if m else None
            return True, latency
        return False, None
    except (asyncio.TimeoutError, OSError) as e:
        log.debug(f"Ping timeout/error for {host}: {e}")
        return False, None


async def async_tcp_connect(host: str, port: int, timeout: float = 1.0) -> bool:
    """Open TCP connection to host:port. Returns True if successful."""
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout,
        )
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return True
    except Exception:
        return False


async def reverse_dns_lookup(ip: str, timeout: float = 2.0) -> Optional[str]:
    """Reverse DNS lookup using gethostbyaddr (synchronous wrapped in thread)."""
    def _do():
        try:
            hostname, _, _ = socket.gethostbyaddr(ip)
            return hostname
        except (socket.herror, socket.gaierror, OSError):
            return None

    return await asyncio.wait_for(asyncio.to_thread(_do), timeout=timeout)


async def get_hostname_smb(ip: str, timeout: float = 1.0) -> Optional[str]:
    """Get hostname via NetBIOS name lookup (Windows)."""
    if platform.system().lower() != "windows":
        return None
    try:
        proc = await asyncio.create_subprocess_exec(
            "nbtstat", "-A", ip,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout + 1)
        out = stdout.decode("utf-8", errors="ignore")
        # Look for unique name in NetBIOS response
        m = re.search(r"UNIQUE\s+(\S+)", out)
        if m:
            name = m.group(1).strip()
            if name.upper() != "UNKNOWN" and len(name) > 1:
                return name
    except (asyncio.TimeoutError, OSError, FileNotFoundError):
        pass
    return None


async def get_arp_entry(ip: str) -> Optional[str]:
    """Get MAC address for IP from local ARP table."""
    is_windows = platform.system().lower() == "windows"
    cmd = ["arp", "-a", ip] if is_windows else ["arp", "-n", ip]

    def _do():
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3,
                check=False,
            )
            out = result.stdout
            # Match MAC address format (XX:XX:XX:XX:XX:XX on Windows, xx:xx:xx:xx:xx:xx on Unix)
            m = re.search(
                r"([0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}"
                r"[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2})",
                out,
            )
            return m.group(1).upper().replace("-", ":") if m else None
        except Exception:
            return None

    return await asyncio.to_thread(_do)


def local_arp_table() -> Dict[str, str]:
    """Get local ARP table as {ip: mac} dict."""
    is_windows = platform.system().lower() == "windows"
    cmd = ["arp", "-a"] if is_windows else ["arp", "-an"]

    table: Dict[str, str] = {}
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        for line in result.stdout.splitlines():
            m = re.search(
                r"(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}"
                r"[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2})",
                line,
            )
            if m:
                ip, mac = m.group(1), m.group(2).upper().replace("-", ":")
                if mac != "FF:FF:FF:FF:FF:FF":
                    table[ip] = mac
    except Exception as e:
        log.debug(f"Failed to read ARP table: {e}")
    return table


def lookup_vendor(mac: str) -> Optional[str]:
    """Resolve vendor from MAC prefix using local OUI database."""
    if not mac or len(mac) < 8:
        return None
    prefix = mac[:8].upper()
    return LOCAL_VENDORS.get(prefix)


def classify_device(open_ports: List[int], vendor: Optional[str], hostname: Optional[str]) -> str:
    """Classify device type based on ports, vendor, hostname."""
    if hostname:
        h = hostname.lower()
        if "router" in h or "gateway" in h:
            return "Router/Gateway"
        if "switch" in h:
            return "Switch"
        if "ap" in h or "access-point" in h or "wifi" in h:
            return "Access Point"
        if "printer" in h or "print" in h:
            return "Printer"
        if "nas" in h:
            return "NAS"
        if "server" in h:
            return "Server"

    if vendor:
        v = vendor.lower()
        if any(x in v for x in ("vmware", "virtualbox", "parallels")):
            return "Virtual Machine"
        if "raspberry" in v:
            return "Single-board Computer"
        if any(x in v for x in ("apple",)):
            return "Apple Device"
        if any(x in v for x in ("microsoft",)):
            return "Windows/Server"
        if any(x in v for x in ("cisco", "ubiquiti", "mikrotik", "tp-link", "netgear")):
            return "Network Equipment"
        if any(x in v for x in ("hp", "dell", "lenovo", "asus")):
            return "Computer/Server"

    # Port-based classification
    if 80 in open_ports or 443 in open_ports:
        if 22 in open_ports or 3389 in open_ports:
            return "Server/Computer"
        if 8080 in open_ports or 8443 in open_ports:
            return "Web Server"
    if 9100 in open_ports or 631 in open_ports:
        return "Printer"
    if 22 in open_ports:
        return "Linux Server"
    if 3389 in open_ports:
        return "Windows Computer"
    if 53 in open_ports:
        return "DNS Server"
    if 161 in open_ports or 162 in open_ports:
        return "Network Device"

    return "Unknown"


async def discover_host(
    ip: str,
    ping_timeout: float = 2.0,
    tcp_ports: Tuple[int, ...] = (80, 443, 22, 3389),
    tcp_timeout: float = 1.0,
    methods: Tuple[str, ...] = ("icmp", "arp", "tcp_fallback"),
) -> DiscoveredDevice:
    """Discover a single host with configurable methods."""
    device = DiscoveredDevice(ip_address=ip, discovery_method=",".join(methods))

    online = False
    latency: Optional[float] = None

    if "icmp" in methods:
        online, latency = await async_ping(ip, timeout=ping_timeout)
        device.discovery_method = "icmp"

    if not online and "tcp_fallback" in methods:
        for port in tcp_ports:
            if await async_tcp_connect(ip, port, timeout=tcp_timeout):
                online = True
                device.discovery_method = f"tcp:{port}"
                break

    if not online:
        # Even if not directly responding, check ARP table (might be reachable on other host)
        if "arp" in methods:
            mac = await get_arp_entry(ip)
            if mac:
                # Host appears in ARP table - probably online even if not pinging
                online = True
                device.discovery_method = "arp"

    device.online = online
    device.latency_ms = latency

    if online:
        # Get hostname in parallel with MAC/vendor lookups
        tasks = []
        tasks.append(reverse_dns_lookup(ip))
        tasks.append(get_hostname_smb(ip))
        tasks.append(get_arp_entry(ip))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        dns_name, smb_name, mac = results

        if isinstance(dns_name, str):
            device.hostname = dns_name
        elif isinstance(smb_name, str):
            device.hostname = smb_name

        if isinstance(mac, str):
            device.mac_address = mac
            device.vendor = lookup_vendor(mac)

        # Quick port scan for classification
        device.open_ports = await quick_port_scan(ip, tcp_timeout=0.4)

        device.device_type = classify_device(device.open_ports, device.vendor, device.hostname)

    device.last_seen = datetime.now(timezone.utc)
    return device


async def quick_port_scan(
    host: str,
    ports: Tuple[int, ...] = (21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445, 3389),
    tcp_timeout: float = 0.4,
    concurrency: int = 32,
) -> List[int]:
    """Quick port scan to detect common services. Returns list of open ports."""
    sem = asyncio.Semaphore(concurrency)

    async def check(port: int) -> Optional[int]:
        async with sem:
            if await async_tcp_connect(host, port, timeout=tcp_timeout):
                return port
        return None

    tasks = [check(p) for p in ports]
    results = await asyncio.gather(*tasks)
    return sorted([p for p in results if p is not None])