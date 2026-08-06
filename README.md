# NetOps Commander

A desktop application for network inventory, monitoring, and diagnostics.
Built with Python 3.11+, PySide6, SQLAlchemy, and modern async I/O.
**Authorized use only** — never scan networks you do not own or have
written permission to test.

## Version 1.2.0 (Current)

- Monitoring loop now stops cleanly (fixed: `stop()` cancelled a task that was
  never created when driven from the `MonitorThread`, so exit/toggle-off hung).
- Real standalone Ping Tool (Tools → Ping Tool) — continuous ICMP ping with
  live output and stop control. The old placeholder widget was replaced.
- Docs now match reality: README features and `PROJECT_STRUCTURE.md` reflect
  only what actually exists; fantasy features are marked **Planned**.
- Requirements split into core (`requirements.txt`) and optional
  (`requirements-optional.txt`); unused packages (`asyncio-mqtt`, etc.) removed.

## Features

### Network Discovery & Inventory (working)
- Scan a local subnet or user-entered CIDR range (ICMP ping, ARP, TCP fallback)
- Strict discovery — only hosts that actually respond are reported online
- Hostname lookup, MAC address + IEEE OUI vendor enrichment (120+ prefixes)
- Device type classification (router, switch, printer, VM, etc.)
- Sortable, searchable, filterable device table
- Per-device notes and tags (double-click a row → Edit Device)

### Dashboard (working)
- Current interface, local IP, subnet, gateway, DNS servers
- Public IP detection (multiple fallback endpoints)
- Online/offline/total device counts, recent scan count
- Alerts feed (last 20)

### Monitoring & Alerts (working)
- Watch selected devices on an interval (opt-in per device, default off)
- Alerts on offline / recovery / high latency / packet loss
- Alert history stored in SQLite
- Monitoring starts and stops cleanly (window close, or un-toggle the last
  monitored device)

### Tools (working)
- Context-menu **Ping** (4 probes with loss/avg stats)
- Context-menu **TCP Port Scan** (rate-limited, validated port ranges)
- Standalone **Ping Tool** (Tools menu) — continuous ping until Stop
- Dark/light theme toggle (View menu)

### Data & Export (working)
- SQLite storage (scans, devices, notes, monitoring history, alerts, settings)
- Export: CSV, JSON, HTML (File → Export)

### UX
- Progress bar + cancel for long scans
- Context menus on the device table
- Input validation, timeouts, rate limiting
- Comprehensive logging to file
- Privilege detection (admin/root) with guidance
- Optional dependency detection (nmap, scapy, pysnmp, PuTTY, WinSCP)

### Planned (not yet implemented)
- Traceroute (ICMP/TCP)
- DNS lookup tool (A, AAAA, MX, TXT, CNAME, NS, SOA, PTR)
- TLS certificate diagnostics
- Subnet calculator (VLSM)
- Route/ARP table viewers
- Wi-Fi information
- Wake-on-LAN
- Live ping graph
- App launchers (RDP, SSH, browser, …)

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
|-----------|----------|--------|
| Nmap | Deep port scanning | `pip install -r requirements-optional.txt` (or `python-nmap` + nmap binary) |
| scapy | ARP discovery (more reliable than netsh) | `pip install -r requirements-optional.txt` |
| pysnmp | SNMP device interrogation | `pip install -r requirements-optional.txt` |

## Configuration

All settings stored in SQLite (table: `settings`). Config file `config.yaml`
provides defaults applied on first run:

```yaml
app:
  name: NetOps Commander
  version: 1.2.0
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
2. **Inspect** — double-click a device row to edit notes/tags.
3. **Monitor** — right-click a device → "Toggle Monitoring". Alerts appear
   in the Dashboard. Un-toggle the last device to stop monitoring.
4. **Ping / Port Scan** — right-click a device → Ping or Port Scan.
   Or Tools → Ping Tool for continuous ping.
5. **Export** — File → Export → CSV/JSON/HTML.

## Security Notes

- **Never** run scans against networks you do not own or are not authorized
  to test.
- Port scanning can trip IDS/IPS systems — use rate limiting (built-in).
- All user-entered IPs/CIDRs are validated; no `shell=True` is used anywhere;
  subprocess calls use explicit argument lists only.

## Project Structure

See `PROJECT_STRUCTURE.md` for the full annotated tree.

## Changelog

### 1.2.0 — Monitoring Fixes & Docs Honesty
- **Fixed**: monitoring now stops cleanly. `MonitorController.stop()` cancels
  the active loop task scheduler-safely even when driven by `MonitorThread`
  (previously it cancelled a `None` task, so exit / toggle-off hung).
- **Ping Tool**: real continuous ping (Tools → Ping Tool) replacing the
  placeholder stub; context-menu Ping/Port Scan unchanged.
- **Docs**: README features and `PROJECT_STRUCTURE.md` rewritten to match the
  actual code; removed fantasy features (marked as Planned instead).
- **Requirements**: split core vs optional; dropped unused `asyncio-mqtt`.
- **Version**: bumped to 1.2.0 everywhere (`__init__`, `constants`,
  `config.py` default, `config.yaml`, README).

### 1.1.1 — Scan & Monitoring Bugfix Release
- **Fixed broken `monitor.add_device()` call** in `scan_cidr` — was passing a
  single IP string to a method expecting `(device_id, ip)`, which would crash
  monitoring during scans.
- **Fixed `background_scan` cancellation** — now accepts an external
  `CancellableScan` instance so cancellation actually propagates to the
  running scan.
- **`persist_device()` enrichment** — new devices now get `first_seen`,
  `last_check`, `is_monitored=True`, and `monitor_interval` from config;
  updates preserve existing monitoring state.
- **`ScanThread.run()` in GUI** — updated to the new
  `background_scan(cidr, scan_mgr, done_callback, error_callback)` API so the
  scan button works correctly.
- **CSV export** — now includes `notes`, `tags`, `first_seen` (was dropping
  them).
- **Version bumped** to 1.1.1 across all files.

### 1.1.0 — Strict Discovery & Enrichment Release
- **Strict device discovery** — only hosts that actively respond to ICMP ping
  or TCP connect are reported as online. Eliminates false positives from
  stale ARP entries.
- **Vendor enrichment** — 120+ MAC OUI prefixes mapped to vendors (Apple,
  Dell, Ubiquiti, VMware, Raspberry Pi, Cisco, HP, Lenovo, Intel, etc.)
- **Smart device type classification** — infers device role from hostname,
  open ports, and vendor: Router, Switch, Access Point, Computer, Mobile,
  Virtual Machine, NAS, Smart Home, IoT, Printer, Camera, etc.
- **DB persistence fix** — offline devices are no longer persisted, keeping
  inventory clean.

## License

Authorized network administration use only. The operator is responsible for
ensuring they have permission to scan any network they use this tool on.
