"""Constants and enums for NetOps Commander."""

APP_NAME = "NetOps Commander"
APP_VERSION = "1.4.0"
ORG_NAME = "NetOps"
ORG_DOMAIN = "netops.local"
DEFAULT_THEME = "dark"

SUPPORTED_EXPORT_FORMATS = ("csv", "json", "html")

# Alert types currently emitted by MonitorController
ALERT_TYPES = {
    "offline": "Device Offline",
    "recovery": "Device Recovered",
    "high_latency": "High Latency",
}

MONITOR_INTERVALS = (30, 60, 120, 300, 600)

# Methods used / recorded by the active discovery path (nmap/snmp planned)
SCAN_METHODS = ("ping", "arp", "tcp")

DISCOVERY_METHODS = ("icmp", "icmp+arp", "tcp_fallback", "local", "none")

DEFAULT_PORTS = [
    21, 22, 23, 25, 53, 80, 110, 135, 139, 143, 443, 445,
    993, 995, 1433, 3306, 3389, 5432, 5900, 8080, 8443,
]

DEFAULT_SCAN_TIMEOUT = 2.0
DEFAULT_SCAN_CONCURRENCY = 128
DEFAULT_PORT_SCAN_TIMEOUT = 0.8
DEFAULT_MONITOR_INTERVAL = 60
DEFAULT_MONITOR_MAX_DEVICES = 25
DEFAULT_HISTORY_RETENTION_DAYS = 30

# Timeouts (seconds)
TCP_CONNECT_TIMEOUT = 1.0
HTTP_TIMEOUT = 5.0
DNS_TIMEOUT = 3.0
TRACEROUTE_TIMEOUT = 2.0

# Port scan safety
PORT_SCAN_MAX_PORTS = 1024
PORT_SCAN_MAX_TARGETS = 256

# WOL
WOL_UDP_PORT = 9
WOL_BROADCAST = "255.255.255.255"

# Vendor database URL (IEEE OUI)
OUI_DATABASE_URL = "https://api.macvendors.com/"
