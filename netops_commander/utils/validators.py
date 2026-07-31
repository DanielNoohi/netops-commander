"""Input validation helpers."""
import ipaddress
import re
from ..constants import PORT_SCAN_MAX_PORTS, PORT_SCAN_MAX_TARGETS

def validate_cidr(value: str) -> tuple:
    """Validate CIDR notation. Returns (ok, message)."""
    try:
        net = ipaddress.ip_network(value.strip(), strict=False)
        if net.prefixlen < 16:
            return False, "CIDR block too large (max /16 for safety)"
        if net.num_addresses > 65536:
            return False, "CIDR block exceeds 65,536 addresses"
        return True, ""
    except ValueError as e:
        return False, str(e)

def validate_ip(value: str) -> tuple:
    """Validate IP address. Returns (ok, message)."""
    try:
        ipaddress.ip_address(value.strip())
        return True, ""
    except ValueError as e:
        return False, str(e)

def validate_port_range(spec: str) -> tuple:
    """Validate port range spec like '22,80,443' or '8000-8100'. Returns (ok, message, ports)."""
    ports = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            try:
                a, b = map(int, part.split("-"))
                ports.update(range(a, b + 1))
            except ValueError:
                return False, f"Invalid port range: {part}", []
        else:
            try:
                ports.add(int(part))
            except ValueError:
                return False, f"Invalid port: {part}", []
    ports = sorted(p for p in ports if 1 <= p <= 65535)
    if not ports:
        return False, "No valid ports", []
    if len(ports) > PORT_SCAN_MAX_PORTS:
        return False, f"Too many ports (max {PORT_SCAN_MAX_PORTS})", ports
    return True, "", ports

def validate_targets(targets: list) -> tuple:
    if len(targets) > PORT_SCAN_MAX_TARGETS:
        return False, f"Too many targets (max {PORT_SCAN_MAX_TARGETS})"
    return True, ""