"""Subnet calculator helpers (stdlib ipaddress)."""
from __future__ import annotations

import ipaddress
from typing import Any, Dict, Union


Network = Union[ipaddress.IPv4Network, ipaddress.IPv6Network]


def parse_network(cidr: str) -> Network:
    """Parse CIDR or address/prefix into a network (non-strict)."""
    return ipaddress.ip_network(cidr.strip(), strict=False)


def describe_network(cidr: str) -> Dict[str, Any]:
    """Return human-readable subnet details for a CIDR string."""
    net = parse_network(cidr)
    hosts = list(net.hosts())
    first = str(hosts[0]) if hosts else None
    last = str(hosts[-1]) if hosts else None
    return {
        "network": str(net.network_address),
        "broadcast": str(getattr(net, "broadcast_address", "")) or None,
        "netmask": str(net.netmask),
        "wildcard": str(getattr(net, "hostmask", "")),
        "prefixlen": net.prefixlen,
        "num_addresses": net.num_addresses,
        "usable_hosts": max(net.num_addresses - 2, 0) if net.version == 4 and net.prefixlen < 31 else len(hosts),
        "first_usable": first,
        "last_usable": last,
        "is_private": net.is_private,
        "version": net.version,
        "cidr": str(net),
    }
