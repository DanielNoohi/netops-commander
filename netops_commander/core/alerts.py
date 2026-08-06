"""Alert definitions and severity helpers."""


def severity_for(alert_type: str) -> str:
    mapping = {
        "offline": "critical",
        "recovery": "info",
        "high_latency": "warning",
        "packet_loss": "warning",
        "new_device": "info",
        "ip_change": "warning",
        "mac_change": "warning",
        "cert_expiry": "warning",
    }
    return mapping.get(alert_type, "info")