# AGENTS.md — NetOps Commander

## Current state (v1.3.0)

Desktop NetOps MVP with:

- CIDR discovery, inventory, export, monitoring + alerts
- Tools: Ping, DNS, Traceroute, Port Scan, Subnet, TLS, WOL, Route/ARP
- Themes, toolbar, packaging (`pyproject.toml`, `python -m netops_commander`)
- Unit tests + CI (compile, tests, version sync, hard pyflakes)

Still Planned: live ping graph, Wi‑Fi UI, launchers, deep nmap/SNMP in scan path,
multi-probe loss alerts, full SQLite settings UI.

## Versioning

Bump on every user-visible batch. Sync `__init__.py`, `constants.py`,
`config.yaml`, `config.py`, `pyproject.toml`, README changelog.

| Change | Bump |
|--------|------|
| Bugfix | PATCH |
| New tool/capability | MINOR |
| Breaking | MAJOR |

## Patterns

- `QThread` + asyncio / subprocess for network
- `session_scope()` for DB
- `get_logger(__name__)`, relative imports
- No `shell=True`; validate inputs via `utils.validators`

## Verify

```bash
python tests/test_scan_pipeline.py
python tests/test_monitor_stop.py
python tests/test_ports.py
python tests/test_config.py
python tests/test_validators.py
python tests/test_subnet.py
python tests/test_wol.py
python -m pyflakes main.py netops_commander tests
```
