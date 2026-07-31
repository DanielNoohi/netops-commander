# NetOps Commander

A professional, cross-platform desktop application for network administration,
inventory, monitoring, and diagnostics. Built with Python 3.11+, PySide6,
SQLAlchemy, and modern async I/O. **Authorized use only.**

## Version 1.1.0 (Current)

**Major improvements in discovery and enrichment:**
- **Strict device discovery** — only hosts that actively respond to ICMP ping or TCP connect are reported as online. Eliminates false positives from stale ARP entries.
- **Vendor enrichment** — 120+ MAC OUI prefixes mapped to vendors (Apple, Dell, Ubiquiti, VMware, Raspberry Pi, Cisco, HP, Lenovo, Intel, etc.)
- **Smart device type classification** — infers device role from hostname, open ports, and vendor: Router, Switch, Access Point, Computer, Mobile, Virtual Machine, NAS, Smart Home, IoT, Printer, Camera, etc.
- **DB persistence fix** — offline devices are no longer persisted, keeping inventory clean.

---

## Features

### Network Discovery & Inventory
- Scan local network or user-entered CIDR ranges
- Device discovery via ICMP ping, ARP table, TCP fallback
- Hostname lookup (NetBIOS + reverse DNS)
- MAC address + IEEE OUI vendor lookup
- Device type classification (router, switch, printer, etc.)
- Optional integration: Nmap (port scan), SNMP (device interrogation)
- Sortable, searchable, filterable device table
- Per-device notes, tags, custom fields

### Dashboard
- Current interface, local IP, subnet, gateway, DNS servers
- Public IP detection (multiple fallback endpoints)
- Online/offline device counts
- Recent scans, alerts feed
- Network health indicators (latency, loss, jitter)

### Practical Tools
- Continuous ping with live graph + packet loss stats
- Traceroute (ICMP + TCP modes)
- DNS lookup (A, AAAA, MX, TXT, CNAME, NS, SOA, PTR)
- TCP port tester (individual)
- Safe port scanner (rate-limited, validated ranges)
- HTTP/HTTPS + TLS certificate diagnostics (expiry, issuer, chain)
- Subnet calculator (VLSM, usable hosts, broadcast)
- Route table viewer, ARP table viewer
- Interface information, Wi-Fi information
- Wake-on-LAN (WOL magic packet)
- Duplicate IP detection
- Gateway/internet connectivity tests
- Launchers: RDP, SSH, browser, PowerShell, PuTTY, WinSCP, Computer Management

### Monitoring & Alerts
- Watch selected devices periodically
- Alerts: offline, recovery, high latency, packet loss, new device,
  IP change, MAC change, certificate expiry
- Alert history stored in SQLite

### Data & Export
- SQLite storage (scans, devices, notes, monitoring, settings, alerts)
- Export: CSV, JSON, HTML

### UX
- Dark + light themes
- Progress bars + cancellation for long operations
- Context menus everywhere relevant
- Input validation, timeouts, rate limiting
- Comprehensive logging to file
- Graceful error handling everywhere
- Privilege detection (admin/root) with guidance
- Optional dependency detection (nmap, snmp, scapy)

---

## Requirements

- Python 3.11+ (3.12 recommended)
- Windows 10/11, Linux, macOS
- Administrator/root privileges recommended for ARP/SNMP/raw socket features

## Installation

```bash
# 1. Create virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run
python main.py
```

### Optional Dependencies (auto-detected, not required)
| Dependency | Provides | Install |
|-----------|----------|---------|
| Nmap | Deep port scanning | https://nmap.org/download.html |
| scapy | ARP discovery (more reliable than netsh) | `pip install scapy` |
| pysnmp | SNMP device interrogation | `pip install pysnmp` |

## Configuration

All settings stored in SQLite (tables: `settings`). Config file `config.yaml`
provides defaults applied on first run:

```yaml
app:
  name: NetOps Commander
  version: 1.1.0
  theme: dark
  scan_timeout: 2.0
  scan_concurrency: 128
  port_scan_timeout: 1.0
  ...
```

## Usage

1. **Scan** — click "Scan" on toolbar or Dashboard → choose CIDR (defaults
   to local subnet), pick discovery method, click Start. Progress bar shows
   live progress; Cancel aborts safely.
2. **Inspect** — double-click a device row to edit notes/tags or run tools
   against it (ping, ports, RDP, SSH...).
3. **Monitor** — select devices → right-click → "Monitor Device" → set
   interval. Alerts appear in Dashboard and Log.
4. **Export** — File → Export → CSV/JSON/HTML.

## Security Notes

- **Never** run scans against networks you do not own or are not authorized
  to test.
- Port scanning can trip IDS/IPS systems — use rate limiting (built-in).
- TLS certificate diagnostics connect to the target host — expect
  connection logs on the remote side.
- All user-entered IPs/CIDRs are validated; no shell=True is used anywhere;
  subprocess calls use explicit argument lists only.

## Project Structure

```
netops_commander/
├── main.py
├── requirements.txt
├── README.md
├── config.yaml
├── netops_commander/
│   ├── config.py
│   ├── constants.py
│   ├── database/
│   │   ├── models.py
│   │   ├── database.py
│   │   └── migrations.py
│   ├── core/
│   │   ├── scanner.py
│   │   ├── discovery.py
│   │   ├── workers.py
│   │   ├── monitoring.py
│   │   └── alerts.py
│   ├── gui/
│   │   ├── main_window.py
│   │   ├── dashboard.py
│   │   ├── device_table.py
│   │   ├── device_dialog.py
│   │   ├── themes.py
│   │   ├── widgets/...
│   │   └── tools/...
│   ├── utils/
│   │   ├── network.py
│   │   ├── validators.py
│   │   ├── export.py
│   │   ├── logger.py
│   │   ├── privileges.py
│   │   ├── dependencies.py
│   │   └── helpers.py
│   └── tests/
└── ...
```

## License

Authorized network administration use only. The operator is responsible for
ensuring they have permission to scan any network they use this tool on.

## Changelog

### 1.1.0 — Strict Discovery & Enrichment Release
- **Strict device discovery** — only hosts that actively respond to ICMP ping or TCP connect are reported as online. Eliminates false positives from stale ARP entries.
- **Vendor enrichment** — 120+ MAC OUI prefixes mapped to vendors (Apple, Dell, Ubiquiti, VMware, Raspberry Pi, Cisco, HP, Lenovo, Intel, Microsoft, Samsung, Sony, Huawei, Xiaomi, Synology, QNAP, Philips Hue, LIFX, Google, Amazon, Roku, Mikrotik, etc.).
- **Smart device type classification** — infers device role from hostname, open ports, and vendor: Router, Switch, Access Point, Computer, Mobile, Virtual Machine, NAS, Smart Home, IoT, Printer, Camera, Web Server, SSH Server, etc.
- **DB persistence fix** — offline devices are no longer persisted; returns bool to indicate whether a device was saved.
- **Logger import paths corrected** — modules now use `..utils.logger` correctly.
- **psutil 7.x compatibility** — `net_if_gateways()` wrapped in try/except.
- **sys.executable** — `platform.executable` deprecated in 3.11+, replaced with `sys.executable`.
- **QAction import** — moved to `QtGui` per PySide6 6.11+ convention.
- **README updated** — Version section, this changelog.

### 1.0.0 — Initial release
- Full device discovery, inventory, tools suite, monitoring, alerts, exports
- Async architecture: GUI never blocks
