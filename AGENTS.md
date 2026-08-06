# AGENTS.md — NetOps Commander

## Current state (v1.4.0)

Desktop NetOps MVP with:

- CIDR discovery with ARP/L2 confirmation (rejects ghost ICMP / proxy-ARP)
- Inventory reconcile after scan + startup ghost purge
- Monitoring + edge alerts with acknowledge UI
- Tools: Ping (live latency sparkline), DNS, Traceroute, Port Scan, Subnet, TLS, WOL, Route/ARP
- Launchers: HTTP/HTTPS/RDP/SSH from context menu + device dialog
- Scan dialog (host estimate, local subnet, require_arp), empty inventory state
- Dashboard: Wi‑Fi summary, recent activity, monitored count
- Settings dialog; history retention; keyboard shortcuts (Ctrl+R scan, Ctrl+F search, F5)
- Headless GUI smoke tests (`QT_QPA_PLATFORM=offscreen`) + broad unit suite
- Packaging (`pyproject.toml`, `python -m netops_commander`), CI with PySide6 + pyflakes

Still Planned: multi-probe packet-loss alerts, deep nmap/SNMP in scan path.

## Versioning

Bump on every user-visible batch. Sync `__init__.py`, `constants.py`,
`config.yaml`, `config.py`, `pyproject.toml`, README changelog.

| Change | Bump |
|--------|------|
| Bug fix | PATCH |
| New tool/capability | MINOR |
| Breaking | MAJOR |

## Patterns

- `QThread` + asyncio / subprocess for network
- `session_scope()` for DB; `reset_engine()` only in tests
- `get_logger(__name__)`, relative imports
- No `shell=True`; validate inputs via `utils.validators`
- Online host = local IP **or** ping/TCP **plus** real ARP MAC (when `require_arp`)
- GUI tests: set `QT_QPA_PLATFORM=offscreen` before importing Qt

## Verify

```bash
set QT_QPA_PLATFORM=offscreen
python tests/test_scan_pipeline.py
python tests/test_monitor_stop.py
python tests/test_ports.py
python tests/test_config.py
python tests/test_validators.py
python tests/test_subnet.py
python tests/test_wol.py
python tests/test_export.py
python tests/test_discovery_arp.py
python tests/test_inventory.py
python tests/test_alerts.py
python tests/test_monitor_alerts.py
python tests/test_tools_utils.py
python tests/test_network_parse.py
python tests/test_gui_smoke.py
python -m pyflakes main.py netops_commander tests
```
