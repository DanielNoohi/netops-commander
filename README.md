# NetOps Commander

A desktop application for network inventory, monitoring, and diagnostics.
Built with Python 3.11+, PySide6, SQLAlchemy, and async I/O.
**Authorized use only** — never scan networks you do not own or have
written permission to test.

## Version 1.4.0 (Current)

- **GUI**: scan dialog (estimate + local subnet), ping latency sparkline,
  HTTP/RDP/SSH launchers, Wi‑Fi card, recent activity, empty-state inventory,
  keyboard shortcuts, device dialog latency history
- **Tests**: monitor alert edges, tools utils, network/wifi parsing, headless
  GUI smoke (`QT_QPA_PLATFORM=offscreen`) in CI with PySide6

## Version 1.3.4

- **Settings** dialog (File → Settings): theme, scan timeout/concurrency,
  `require_arp`, monitor interval/max, history retention
- History retention purge on startup; delete devices from inventory
- Alert acknowledge + severity colors; HTML export escapes cell content
- Unit tests for ARP/ghost rules, inventory reconcile, export escaping

## Version 1.3.3

- **Inventory cleanup**: purge ghost rows (no MAC) on startup; after a scan,
  reconcile the CIDR so the table and dashboard match found hosts only
  (not stale “254 online” from older buggy scans).

## Version 1.3.2

- **Ghost-host filter**: require a real ARP MAC (not gateway proxy-ARP) before
  marking a host online. Stops `/24` scans reporting 254 fake “online” devices
  when the LAN answers ICMP/TCP for empty addresses.
- Config: `app.require_arp: true` (default).

## Version 1.3.1

- **Scan fix**: reverse-DNS / NetBIOS timeouts no longer discard online hosts.
- Stricter ICMP reply matching; modest Windows scan concurrency; ARP cache reuse.

## Version 1.3.0

- Full **Tools suite**: Ping, DNS, Traceroute, Subnet Calculator, TLS check,
  Wake-on-LAN, Route/ARP viewers — toolbar + Tools menu + device context menu
- Packaging: `pyproject.toml`, `python -m netops_commander`, `netops-commander` script
- Broader unit tests (validators, subnet, WOL, config, ports, monitor stop)

## Features

### Network Discovery & Inventory
- CIDR scan (ICMP / ARP / TCP fallback), strict online detection
- Hostname, MAC + OUI vendor enrichment, device type classification
- Sortable/searchable inventory; notes/tags (double-click or context menu)
- Scan history recorded in SQLite

### Dashboard
- Interface / IP / subnet / gateway / DNS / public IP / Wi‑Fi
- Online/offline/total/monitored counts and recent activity
- Alerts feed (offline / recovery / high latency) with acknowledge
- File → Settings; shortcuts: Ctrl+R scan, Ctrl+F search, F5 refresh

### Monitoring
- Opt-in per-device monitoring with clean start/stop
- Edge-triggered high-latency alerts (no spam)

### Tools
| Tool | Where |
|------|--------|
| Continuous Ping | Tools / toolbar |
| DNS (A/AAAA/PTR + MX/TXT/NS via nslookup) | Tools / context menu |
| Traceroute | Tools / context menu |
| TCP Port Scan | Context menu |
| Subnet Calculator | Tools / toolbar |
| TLS certificate check | Tools / context menu |
| Wake-on-LAN | Tools / context menu |
| Route + ARP tables | Tools menu |
| HTTP / HTTPS / RDP / SSH launchers | Context menu / device dialog |
| Live ping latency sparkline | Ping tool |
| Dark/light theme | View / toolbar (persisted) |

### Data
- SQLite for devices, history, monitor results, alerts
- Export CSV / JSON / HTML
- Preferences in `config.yaml`

### Planned
- Multi-probe packet-loss alerts
- Deep nmap/SNMP integration in the scan pipeline

## Requirements

- Python 3.11+ (3.12 recommended)
- Windows 10/11, Linux, macOS
- Admin/root recommended for some discovery features

## Installation

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python main.py
# or: python -m netops_commander
```

Optional extras:

```bash
pip install -r requirements-optional.txt
# or: pip install -e ".[optional]"
```

## Configuration

Defaults in `config.yaml` (auto-created). Theme and other keys are updated via
`ConfigManager.set()` at runtime. SQLite `settings` is used for schema versioning.

## Usage

1. **Scan** — toolbar **Scan** or device-table Scan button → CIDR → Start  
2. **Inspect** — double-click a row to edit notes/tags  
3. **Monitor** — right-click → Toggle Monitoring  
4. **Tools** — toolbar / Tools menu / device context menu  
5. **Export** — File → Export  

## Security

- Authorized networks only  
- Validated CIDR/IP/ports; rate-limited scans  
- No `shell=True`; subprocess uses argument lists only  

## Project Structure

See `PROJECT_STRUCTURE.md`.

## Changelog

### 1.4.0 — GUI polish + test depth
- Scan dialog, latency sparkline, launchers, Wi‑Fi + activity dashboard
- Shortcuts; empty inventory state; device latency history
- Broad unit suite + offscreen GUI smoke tests in CI
- Version 1.3.4 → 1.4.0

### 1.3.4 — Settings, retention, harden exports/tests
- File → Settings for key scan/monitor preferences
- Startup history retention; device delete; alert acknowledge UI
- HTML export XSS-safe escaping; tests for discovery ARP + inventory
- Version 1.3.3 → 1.3.4

### 1.3.3 — Inventory matches scan results
- Startup purge of ghost ICMP inventory rows (no real MAC)
- Post-scan reconcile deletes/marks offline CIDR hosts not found this pass
- Version 1.3.2 → 1.3.3

### 1.3.2 — Reject ghost ICMP/TCP hosts
- Online requires ARP/L2 confirmation (or local IP); proxy-ARP and “all ports
  open” sinkholes are dropped
- `require_arp` config flag (default true)
- Version 1.3.1 → 1.3.2

### 1.3.1 — Scan finds devices again
- Hostname enrichment timeouts no longer abort `discover_host` after a successful ping
- Ping success requires a real reply marker; Windows concurrency capped
- Brief ARP table cache during scan waves
- Version 1.3.0 → 1.3.1

### 1.3.0 — Tools suite & packaging
- Added DNS, Traceroute, Subnet Calculator, TLS check, WOL, Route/ARP tools
- Main toolbar; richer device context menu
- `pyproject.toml` + `netops_commander.app` entry points
- Unit tests for validators, subnet, WOL
- Version 1.2.1 → 1.3.0

### 1.2.1 — Remaining bugfixes
- Theme persistence, deps-thread retain, ScanHistory, edge-triggered latency alerts,
  double-click edit, doc honesty, GPL named

### 1.2.0 — Monitoring stop & docs honesty
- Clean monitor stop; real Ping Tool; requirements split; honest README

### 1.1.x — Scan pipeline & discovery
- Strict discovery, OUI enrichment, scan cancel/progress fixes

## License

**GNU GPL v3.0** — see `LICENSE`.

Authorized network administration use only.
