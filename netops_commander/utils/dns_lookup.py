"""DNS lookup helpers (stdlib + optional system resolver tools)."""
from __future__ import annotations

import re
import socket
import subprocess
from typing import Dict, List, Tuple


def lookup_a_aaaa(name: str) -> Dict[str, List[str]]:
    """Resolve A and AAAA via getaddrinfo."""
    out: Dict[str, List[str]] = {"A": [], "AAAA": []}
    try:
        infos = socket.getaddrinfo(name, None)
    except socket.gaierror as e:
        raise ValueError(f"Resolution failed: {e}") from e
    for info in infos:
        family, _, _, _, sockaddr = info
        addr = sockaddr[0]
        if family == socket.AF_INET and addr not in out["A"]:
            out["A"].append(addr)
        elif family == socket.AF_INET6 and addr not in out["AAAA"]:
            out["AAAA"].append(addr)
    return out


def lookup_ptr(ip: str) -> str:
    """Reverse DNS (PTR)."""
    try:
        host, _, _ = socket.gethostbyaddr(ip)
        return host
    except (socket.herror, socket.gaierror, OSError) as e:
        raise ValueError(f"PTR lookup failed: {e}") from e


def _run_resolver(args: List[str], timeout: float = 8.0) -> str:
    proc = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    text = (proc.stdout or "") + (proc.stderr or "")
    if not text.strip():
        raise ValueError("Resolver returned empty output")
    return text


def lookup_with_nslookup(name: str, rtype: str) -> str:
    """Best-effort MX/TXT/NS/CNAME/SOA via nslookup (cross-platform)."""
    rtype = rtype.upper()
    return _run_resolver(["nslookup", f"-type={rtype}", name])


def lookup_records(name: str, rtype: str) -> Tuple[str, List[str]]:
    """
    Lookup DNS records.

    Returns (source, lines) where source is 'stdlib' or 'nslookup'.
    """
    name = name.strip()
    rtype = rtype.upper().strip()
    if not name:
        raise ValueError("Empty name")

    if rtype in ("A", "AAAA"):
        data = lookup_a_aaaa(name)
        lines = [f"{rtype}: {addr}" for addr in data.get(rtype, [])]
        if not lines and rtype == "A":
            # also show AAAA if A empty? keep strict
            pass
        if not lines:
            # try both and show requested emptily with note
            other = "AAAA" if rtype == "A" else "A"
            alt = data.get(other, [])
            if alt:
                lines = [f"(no {rtype}) {other}: {a}" for a in alt]
            else:
                raise ValueError(f"No {rtype} records for {name}")
        return "stdlib", lines

    if rtype == "PTR":
        host = lookup_ptr(name)
        return "stdlib", [f"PTR: {host}"]

    # Extended types via nslookup
    try:
        raw = lookup_with_nslookup(name, rtype)
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError, OSError) as e:
        raise ValueError(
            f"{rtype} lookup requires nslookup on PATH ({e})"
        ) from e

    lines = []
    for line in raw.splitlines():
        s = line.strip()
        if not s:
            continue
        # Keep useful answer-ish lines
        if re.search(rtype, s, re.I) or "mail exchanger" in s.lower() or "text =" in s.lower():
            lines.append(s)
        elif s.startswith("Name:") or s.startswith("Address") or "nameserver" in s.lower():
            lines.append(s)
    if not lines:
        lines = [ln for ln in raw.splitlines() if ln.strip()][-20:]
    return "nslookup", lines
