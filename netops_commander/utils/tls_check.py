"""TLS certificate diagnostics (stdlib ssl)."""
from __future__ import annotations

import socket
import ssl
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def check_tls(host: str, port: int = 443, timeout: float = 8.0) -> Dict[str, Any]:
    """
    Connect and return certificate summary.
    Raises ValueError / OSError on failure.
    """
    host = host.strip()
    if not host:
        raise ValueError("Empty host")
    ctx = ssl.create_default_context()
    with socket.create_connection((host, port), timeout=timeout) as sock:
        with ctx.wrap_socket(sock, server_hostname=host) as ssock:
            cert = ssock.getpeercert()
            cipher = ssock.cipher()
            version = ssock.version()

    if not cert:
        raise ValueError("No certificate presented (or binary form unavailable)")

    not_before = _parse_cert_time(cert.get("notBefore"))
    not_after = _parse_cert_time(cert.get("notAfter"))
    days_left: Optional[float] = None
    if not_after:
        days_left = (not_after - datetime.now(timezone.utc)).total_seconds() / 86400.0

    san = []
    for typ, val in cert.get("subjectAltName", ()) or ():
        san.append(f"{typ}:{val}")

    subject = _name_to_str(cert.get("subject"))
    issuer = _name_to_str(cert.get("issuer"))

    return {
        "host": host,
        "port": port,
        "tls_version": version,
        "cipher": cipher[0] if cipher else None,
        "subject": subject,
        "issuer": issuer,
        "not_before": not_before.isoformat() if not_before else None,
        "not_after": not_after.isoformat() if not_after else None,
        "days_remaining": round(days_left, 1) if days_left is not None else None,
        "san": san,
        "serial": cert.get("serialNumber"),
    }


def _name_to_str(name) -> str:
    if not name:
        return ""
    parts = []
    for rdn in name:
        for key, val in rdn:
            parts.append(f"{key}={val}")
    return ", ".join(parts)


def _parse_cert_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    # e.g. 'Aug  6 12:00:00 2026 GMT'
    for fmt in ("%b %d %H:%M:%S %Y %Z", "%b  %d %H:%M:%S %Y %Z"):
        try:
            dt = datetime.strptime(value, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None
