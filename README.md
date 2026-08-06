# NetOps Commander

**Local network inventory, monitoring, and diagnostics** — a desktop toolkit for
operators who need a clear picture of what’s on the LAN, without cloud accounts
or agent sprawl.

| | |
|---|---|
| **Version** | 1.4.0 |
| **Stack** | Python 3.11+ · PySide6 · SQLAlchemy · asyncio |
| **Platforms** | Windows · Linux · macOS |
| **License** | GPL-3.0 |

> **Authorized use only.** Scan and probe only networks you own or have
> written permission to test.

---

## Highlights

- **Strict discovery** — ICMP + ARP/L2 confirmation rejects ghost subnet replies
  and proxy-ARP sinkholes (`require_arp`)
- **Living inventory** — post-scan reconcile keeps the table aligned with what
  was actually found; ghost rows purged on startup
- **Opt-in monitoring** — edge-triggered offline / recovery / high-latency alerts
- **Ops toolbox** — ping (live latency graph), DNS, traceroute, port scan,
  subnet calc, TLS check, WOL, route/ARP, HTTP·RDP·SSH launchers
- **Desktop UX** — dashboard (iface, Wi‑Fi, activity), settings, themes,
  shortcuts, CSV/JSON/HTML export
- **Solid engineering** — no `shell=True`, validated inputs, CI + unit +
  headless GUI smoke tests

---

## Quick start

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Unix:     source .venv/bin/activate

pip install -r requirements.txt
python main.py
# or:  python -m netops_commander
# or:  netops-commander   (after pip install -e .)
```

Optional extras (nmap / scapy / pysnmp — not required for core scans):

```bash
pip install -r requirements-optional.txt
# or:  pip install -e ".[optional]"
```

Admin/root is recommended for full ICMP/ARP fidelity on some platforms.

---

## Everyday workflow

| Step | Action |
|------|--------|
| 1 | **Scan** — toolbar or `Ctrl+R` → choose CIDR → Start |
| 2 | **Inspect** — double-click a row (notes, tags, latency history, launchers) |
| 3 | **Monitor** — right-click → Toggle Monitoring |
| 4 | **Diagnose** — Ping / DNS / Trace / Ports / TLS / WOL from context menu |
| 5 | **Export** — File → Export (CSV, JSON, HTML) |
| 6 | **Tune** — File → Settings (`Ctrl+,`) or edit `config.yaml` |

**Shortcuts:** `Ctrl+R` scan · `Ctrl+F` search · `F5` refresh · `Ctrl+,` settings · `Ctrl+E` export CSV

---

## Features

### Discovery & inventory
CIDR scan with ICMP, ARP confirmation, and TCP fallback; hostname / MAC / OUI
vendor enrichment; device-type guess; searchable sortable table; notes & tags;
SQLite-backed history.

### Dashboard & monitoring
Active interface, gateway, DNS, public IP, Wi‑Fi summary; online / offline /
monitored counts; recent activity; acknowledgeable alerts.

### Tools

| Tool | Entry points |
|------|----------------|
| Continuous ping + latency sparkline | Toolbar · Tools · context |
| DNS (A/AAAA/PTR; MX/TXT/NS via nslookup) | Tools · context |
| Traceroute | Tools · context |
| TCP port scan | Context |
| Subnet calculator | Toolbar · Tools |
| TLS certificate check | Tools · context |
| Wake-on-LAN | Tools · context |
| Route / ARP tables | Tools |
| Open HTTP · HTTPS · RDP · SSH | Context · device dialog |

### Data & config
SQLite (`devices`, `scan_history`, `monitor_results`, `alerts`); preferences in
`config.yaml` (theme, timeouts, concurrency, `require_arp`, retention).

### Roadmap
Multi-probe packet-loss alerts · deeper nmap/SNMP in the scan path.

---

## Configuration

`config.yaml` is created with defaults on first run. Notable keys under `app:`:

| Key | Role |
|-----|------|
| `require_arp` | Require real ARP MAC before marking online (default `true`) |
| `scan_concurrency` | Parallel hosts per scan wave |
| `scan_timeout` | Per-host ping timeout (seconds) |
| `monitoring_interval` | Seconds between monitor passes |
| `history_retention_days` | Startup purge of old history (`0` = keep forever) |
| `theme` | `dark` \| `light` |

Runtime changes from **Settings** are persisted back to the file.

---

## Security posture

- Authorized networks only — enforce this yourself
- CIDR capped at `/16`; ports and hosts validated before tools run
- Subprocess calls use argument lists only (never `shell=True`)
- HTML export escapes cell content
- No telemetry, no remote accounts — data stays in local SQLite

---

## Development

```bash
# Unit + GUI smoke (headless)
set QT_QPA_PLATFORM=offscreen          # Windows
# export QT_QPA_PLATFORM=offscreen     # Unix

python tests/test_gui_smoke.py
python -m pyflakes main.py netops_commander tests
```

CI runs compile, the full test suite (including offscreen GUI smoke), version
sync, and hard pyflakes on Python 3.11 and 3.12.

Layout: see [`PROJECT_STRUCTURE.md`](PROJECT_STRUCTURE.md).  
Agent notes: see [`AGENTS.md`](AGENTS.md).

---

## Changelog

### 1.4.0
Scan dialog, ping latency sparkline, HTTP/RDP/SSH launchers, Wi‑Fi + activity
dashboard, shortcuts, empty inventory state, device latency history; broader
unit suite and offscreen GUI smoke tests in CI.

### 1.3.4
Settings dialog; history retention; device delete; alert acknowledge + severity
colors; HTML export escaping; ARP/inventory regression tests.

### 1.3.3
Startup ghost purge; post-scan inventory reconcile so UI matches found hosts.

### 1.3.2
Require ARP/L2 confirmation (`require_arp`) to reject ghost ICMP/TCP hosts.

### 1.3.1
Hostname enrichment timeouts no longer discard online hosts; tighter ICMP
matching; Windows concurrency cap; ARP cache reuse.

### 1.3.0
Full tools suite, toolbar, `pyproject.toml` packaging, expanded unit tests.

### 1.2.x
Clean monitor stop, real Ping tool, theme persistence, docs honesty.

### 1.1.x
Strict discovery pipeline, OUI enrichment, scan cancel/progress fixes.

---

## License

**GNU GPL v3.0** — see [`LICENSE`](LICENSE).

Built for people who run networks. Use it accordingly.
