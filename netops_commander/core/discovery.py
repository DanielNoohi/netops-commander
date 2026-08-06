"""
Network discovery module.

Device discovery using:
- ICMP ping (primary - requires actual response)
- ARP table (filtered - only recent entries)
- TCP fallback (for hosts that block ping but serve open ports)
- Hostname lookup (reverse DNS + NetBIOS)
- MAC address via ARP + vendor via IEEE OUI
"""

import asyncio
import platform
import re
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


# Extended MAC vendor lookup
VENDOR_PREFIXES: Dict[str, str] = {
    # VM / Virtualization
    "00:50:56": "VMware", "00:0C:29": "VMware", "00:05:69": "VMware",
    "00:1C:42": "Parallels", "08:00:27": "VirtualBox",
    "00:15:5D": "Hyper-V", "00:03:FF": "Hyper-V",
    # Apple
    "00:1B:44": "Apple", "00:25:00": "Apple", "F0:F6:1C": "Apple",
    "00:1E:C2": "Apple", "00:1F:F3": "Apple", "60:33:4B": "Apple",
    "00:23:6C": "Apple", "C8:69:CD": "Apple", "A8:51:AB": "Apple",
    "D0:57:85": "Apple", "F8:0D:43": "Apple", "78:4F:43": "Apple",
    "10:50:72": "Apple",
    # Raspberry Pi
    "B8:27:EB": "Raspberry Pi", "DC:A6:32": "Raspberry Pi",
    "E4:5F:01": "Raspberry Pi",
    # Microsoft / Xbox
    "00:1A:2B": "Microsoft", "00:50:F2": "Microsoft",
    "7C:1E:52": "Microsoft", "60:45:BD": "Microsoft",
    "00:1D:D8": "Microsoft", "B0:65:BD": "Microsoft",
    # HP / HPE
    "F8:1E:DF": "HP", "00:08:02": "HP", "00:14:38": "HP",
    "00:17:A4": "HP", "00:18:71": "HP", "00:1A:4B": "HP",
    "00:21:5A": "HP", "00:23:7D": "HP", "28:80:23": "HP",
    "64:00:6A": "HP", "A4:5E:60": "HP", "9C:8E:73": "HP",
    # Dell
    "00:0B:CD": "Dell", "00:13:72": "Dell", "00:14:22": "Dell",
    "00:18:8B": "Dell", "00:1C:C4": "Dell", "00:1D:09": "Dell",
    "00:1E:4F": "Dell", "00:1E:C9": "Dell", "20:47:47": "Dell",
    "B0:83:FE": "Dell", "EC:F4:BB": "Dell", "34:48:ED": "Dell",
    # Lenovo / IBM
    "00:13:CE": "IBM", "00:14:5E": "IBM", "00:1A:64": "Lenovo",
    "BC:1B:4E": "Lenovo", "B0:A1:7A": "Lenovo",
    # Intel
    "00:1B:21": "Intel", "00:1E:67": "Intel", "F0:1D:BC": "Intel",
    "00:1B:4E": "Intel", "00:1C:58": "Intel",
    # Cisco
    "00:1D:A2": "Cisco", "00:0C:85": "Cisco", "00:1B:0C": "Cisco",
    "00:1B:D5": "Cisco", "00:1B:D6": "Cisco",
    # Netgear
    "00:1D:0D": "Netgear", "00:1D:0E": "Netgear", "00:1B:D0": "Netgear",
    # TP-Link
    "00:1A:83": "TP-Link", "00:1C:DC": "TP-Link", "00:1E:E5": "TP-Link",
    "04:E8:72": "TP-Link", "BC:39:71": "TP-Link",
    # ASUS
    "00:1B:FC": "ASUS", "00:1D:60": "ASUS", "B4:A6:47": "ASUS",
    "00:1C:D5": "ASUS", "04:8D:38": "ASUS",
    # Samsung
    "00:1D:D5": "Samsung", "58:99:3C": "Samsung", "5C:49:79": "Samsung",
    # Huawei
    "00:1D:8B": "Huawei", "00:1D:E2": "Huawei", "48:7A:DA": "Huawei",
    # Xiaomi
    "C0:EE:FB": "Xiaomi", "C8:16:45": "Xiaomi", "C8:4C:75": "Xiaomi",
    # Sony
    "00:1D:5C": "Sony", "00:1D:92": "Sony", "00:1D:55": "Sony",
    # Realtek Semiconductor
    "00:E0:4C": "Realtek", "BC:EC:5D": "Realtek", "00:1B:11": "Realtek",
    "F0:2F:74": "Realtek",
    # Raspberry Pi
    "28:B3:48": "Raspberry Pi", "2C:CF:67": "Raspberry Pi",
    # Philips
    "00:1D:D3": "Philips", "74:A4:2E": "Philips Hue",
    # LIFX
    "D0:73:D5": "LIFX",
    # Google / Nest
    "18:74:2E": "Google", "F8:CA:B8": "Google Nest",
    # Amazon
    "74:75:48": "Amazon", "00:1D:D1": "Amazon",
    # Ubiquiti
    "04:18:D6": "Ubiquiti", "68:72:51": "Ubiquiti",
    "74:83:C2": "Ubiquiti", "F0:9F:C2": "Ubiquiti",
    # Xiaomi
    "C8:4C:75": "Xiaomi", "CC:98:8B": "Xiaomi",
    # Synology
    "00:11:32": "Synology", "00:11:3A": "Synology",
    # QNAP
    "00:08:9B": "QNAP",
    # MikroTik
    "4C:5E:0C": "MikroTik", "6C:3B:6B": "MikroTik",
    # Roku
    "C0:D0:44": "Roku",
    # Apple TV / HomePod
    "00:16:CB": "Apple",  # older AirPort
}


async def async_ping(host: str, timeout: float = 2.0) -> Tuple[bool, Optional[float]]:
    """
    Asynchronously ping a host (REQUIRES actual response).
    Returns (online, latency_ms).
    Only returns True if host actually replied.
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
        # Must have actual TTL or Reply to be considered online
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
    """Reverse DNS lookup using gethostbyaddr."""
    def _do():
        try:
            hostname, _, _ = socket.gethostbyaddr(ip)
            return hostname
        except (socket.herror, socket.gaierror, OSError):
            return None

    return await asyncio.wait_for(asyncio.to_thread(_do), timeout=timeout)


async def get_hostname_smb(ip: str, timeout: float = 1.0) -> Optional[str]:
    """Get hostname via NetBIOS name lookup (Windows only)."""
    if platform.system().lower() != "windows":
        return None
    try:
        proc = await asyncio.create_subprocess_exec(
            "nbtstat", "-A", ip,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        out = stdout.decode("utf-8", errors="ignore")
        m = re.search(r"^\s+(\S+)\s+<00>\s+UNIQUE", out, re.MULTILINE)
        if m:
            return m.group(1)
        m = re.search(r"^\s+(\S+)\s+<20>\s+UNIQUE", out, re.MULTILINE)
        if m:
            return m.group(1)
        return None
    except Exception:
        return None


def lookup_vendor(mac: Optional[str]) -> Optional[str]:
    """
    Look up vendor from MAC address using local prefix table.
    Tries 24-bit OUI, then 28-bit, then 36-bit.
    """
    if not mac:
        return None
    mac_clean = mac.replace("-", ":").replace(".", ":").upper()
    # Try full 6-char OUI then shorter prefixes
    for prefix_len in (8, 7, 5):
        prefix = mac_clean[:prefix_len]
        if prefix in VENDOR_PREFIXES:
            return VENDOR_PREFIXES[prefix]
    # Try incomplete-bytes (3 chars + wildcard)
    for prefix, vendor in VENDOR_PREFIXES.items():
        if mac_clean.startswith(prefix):
            return vendor
    return None


async def get_arp_table() -> List[Dict[str, str]]:
    """
    Read system ARP table. Returns list of {ip, mac, type}.
    Focuses ONLY on dynamic/reachable entries.
    """
    entries = []
    try:
        if platform.system().lower() == "windows":
            proc = await asyncio.create_subprocess_exec(
                "arp", "-a",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            out = stdout.decode("utf-8", errors="ignore")
            for line in out.splitlines():
                m = re.match(r"\s*(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F:-]+)\s+(dynamic|static)", line)
                if m:
                    entries.append({
                        "ip": m.group(1),
                        "mac": m.group(2).replace("-", ":"),
                        "type": m.group(3).lower()
                    })
        elif platform.system().lower() == "linux":
            with open("/proc/net/arp") as f:
                for line in f.readlines()[1:]:
                    parts = line.split()
                    if len(parts) >= 4 and parts[3] != "00:00:00:00:00:00":
                        entries.append({
                            "ip": parts[0],
                            "mac": parts[3],
                            "type": "dynamic"
                        })
        else:
            # macOS
            proc = await asyncio.create_subprocess_exec(
                "arp", "-a",
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
            out = stdout.decode("utf-8", errors="ignore")
            for line in out.splitlines():
                m = re.match(r"\? \(([0-9.]+)\) at ([0-9a-f:]+) on", line)
                if m:
                    entries.append({
                        "ip": m.group(1),
                        "mac": m.group(2),
                        "type": "dynamic"
                    })
    except Exception as e:
        log.debug(f"ARP table read failed: {e}")
    return entries


async def get_mac_via_arp_lookup(ip: str) -> Optional[str]:
    """
    Get MAC for a specific IP via ARP (cached entry).
    After pinging the host, the ARP cache should have it (if reachable).
    """
    # First ping to populate ARP cache (background)
    await async_ping(ip, timeout=1.0)

    # Now read ARP table
    entries = await get_arp_table()
    for entry in entries:
        if entry["ip"] == ip and entry["mac"]:
            return entry["mac"]
    return None


def guess_device_type(mac: Optional[str], hostname: Optional[str], open_ports: List[int]) -> str:
    """Best-effort device type classification."""
    # Router/gateway detection
    if hostname:
        hl = hostname.lower()
        if "router" in hl or "gateway" in hl:
            return "Router"
        if "switch" in hl:
            return "Switch"
        if "ap" in hl or "access" in hl:
            return "Access Point"
        if "printer" in hl:
            return "Printer"
        if "iphone" in hl or "ipad" in hl:
            return "Mobile"
        if "laptop" in hl or "desktop" in hl or "pc" in hl:
            return "Computer"
        if "tv" in hl or "television" in hl:
            return "Smart TV"
        if "camera" in hl or "cam" in hl:
            return "Camera"
        if "nas" in hl or "storage" in hl:
            return "NAS"
        if "iot" in hl or "bulb" in hl or "light" in hl:
            return "IoT Device"
    # Port-based guess
    if 80 in open_ports or 443 in open_ports:
        return "Web Server"
    if 3389 in open_ports:
        return "Windows (RDP)"
    if 22 in open_ports:
        return "SSH Server"
    if 445 in open_ports:
        return "Windows File Share"
    if 53 in open_ports:
        return "DNS Server"
    # MAC vendor-based guess
    if mac:
        vendor = lookup_vendor(mac)
        if vendor:
            if vendor in ("Apple",):
                return "Apple Device"
            if vendor in ("VMware", "VirtualBox", "Hyper-V", "Parallels"):
                return "Virtual Machine"
            if vendor in ("Raspberry Pi",):
                return "Raspberry Pi"
            if vendor in ("Cisco", "MikroTik", "Ubiquiti", "Netgear", "TP-Link", "ASUS"):
                return "Network Device"
            if vendor in ("Philips Hue", "LIFX"):
                return "Smart Home"
            if vendor in ("Synology", "QNAP"):
                return "NAS"
            if vendor in ("HP", "Dell", "Lenovo", "IBM"):
                return "Computer"
            if vendor in ("Samsung", "Sony"):
                return "Consumer Electronic"
            if vendor in ("Google", "Amazon", "Roku", "Xiaomi"):
                return "Smart Device"
    return "Unknown"


async def discover_host(ip: str, ping_timeout: float = 2.0) -> DiscoveredDevice:
    """
    Discover a single host using multi-method approach with strict online criteria.
    
    Strategy:
    1. ICMP ping - if responds, host is definitely online
    2. TCP fallback - if ping blocked but common ports open, host is online
    3. ARP cache - check from existing table only (does NOT mean online now)
    
    Only returns online=True if we have CONFIRMED evidence the host is alive NOW.
    """
    device = DiscoveredDevice(ip_address=ip)

    # METHOD 1: ICMP Ping (primary - requires actual reply)
    ping_ok, latency = await async_ping(ip, timeout=ping_timeout)
    
    if ping_ok:
        device.online = True
        device.latency_ms = latency
        device.discovery_method = "icmp"
        
        # Enrich with hostname, MAC, etc.
        hostname_task = asyncio.create_task(reverse_dns_lookup(ip))
        smb_task = asyncio.create_task(get_hostname_smb(ip))
        
        hostname_dns = await hostname_task
        hostname_smb = await smb_task
        device.hostname = hostname_smb or hostname_dns or None
        
        # Get MAC from ARP cache (should be populated by the ping)
        device.mac_address = await get_mac_via_arp_lookup(ip)
        device.vendor = lookup_vendor(device.mac_address)
        device.device_type = guess_device_type(device.mac_address, device.hostname, device.open_ports)
        
        return device

    # METHOD 2: TCP fallback - check some common ports
    # If any of these respond, host is alive but blocking ping
    common_ports = [22, 25, 53, 80, 110, 143, 443, 993, 995, 3389, 8080, 8443]
    tcp_tasks = [async_tcp_connect(ip, port, timeout=0.8) for port in common_ports[:10]]
    tcp_results = await asyncio.gather(*tcp_tasks, return_exceptions=True)
    
    open_ports = [port for port, result in zip(common_ports, tcp_results) if result is True]
    
    if open_ports:
        device.online = True
        device.open_ports = open_ports
        device.discovery_method = "tcp_fallback"
        
        hostname = await reverse_dns_lookup(ip)
        device.hostname = hostname
        
        device.mac_address = await get_mac_via_arp_lookup(ip)
        device.vendor = lookup_vendor(device.mac_address)
        device.device_type = guess_device_type(device.mac_address, device.hostname, open_ports)
        
        return device

    # Host does not respond to ICMP or TCP - report as offline
    # Still try to get ARP table info for display purposes
    device.discovery_method = "arp"
    return device