# AGENTS.md — NetOps Commander

## Current state (v1.3.4)

Desktop NetOps MVP with:

- CIDR discovery with ARP/L2 confirmation (rejects ghost ICMP / proxy-ARP)
- Inventory reconcile after scan + startup ghost purge
- Monitoring + edge alerts (offline / recovery / high latency) with acknowledge UI
- Tools: Ping, DNS, Traceroute, Port Scan, Subnet, TLS, WOL, Route/ARP
- Settings dialog (theme, scan, ARP, monitor, retention)
- History retention purge on startup; HTML export escapes user content
- Themes, toolbar, packaging (`pyproject.toml`, `python -m netops_commander`)
- Unit tests + CI (compile, tests, version sync, hard pyflakes)

Still Planned: live ping graph, Wi‑Fi UI, launchers, deep nmap/SNMP in scan path,
multi-probe loss alerts.

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

## Verify

```bash
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
python -m pyflakes main.py netops_commander tests
```
