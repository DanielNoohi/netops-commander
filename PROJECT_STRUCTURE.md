# NetOps Commander — Project Structure

```
.
├── main.py                              # Thin entry → netops_commander.app.run
├── pyproject.toml                       # Packaging + console script
├── requirements.txt                     # Core deps
├── requirements-optional.txt            # nmap / scapy / pysnmp
├── config.yaml                          # Runtime defaults (theme, timeouts, …)
├── README.md
├── AGENTS.md
├── netops_commander/
│   ├── __init__.py                      # __version__
│   ├── __main__.py                      # python -m netops_commander
│   ├── app.py                           # QApplication bootstrap
│   ├── config.py                        # ConfigManager (YAML)
│   ├── constants.py                     # Version, ports, limits, alert types
│   ├── core/
│   │   ├── discovery.py                 # ping / ARP / TCP / OUI / type guess
│   │   ├── scanner.py                   # scan_cidr, persist_device + ScanHistory
│   │   ├── monitoring.py                # MonitorController (thread-safe stop)
│   │   └── alerts.py                    # severity_for()
│   ├── database/
│   │   ├── models.py
│   │   ├── database.py
│   │   └── migrations.py
│   ├── gui/
│   │   ├── main_window.py               # Menus, toolbar, monitor thread
│   │   ├── dashboard.py
│   │   ├── device_table.py              # Inventory + context tools
│   │   ├── device_dialog.py
│   │   ├── themes.py
│   │   └── tools/
│   │       ├── base.py                  # Shared ToolDialog / LineWorker
│   │       ├── ping_tool.py
│   │       ├── dns_tool.py
│   │       ├── traceroute_tool.py
│   │       ├── subnet_tool.py
│   │       ├── tls_tool.py
│   │       ├── wol_tool.py
│   │       └── route_arp_tool.py
│   └── utils/
│       ├── network.py
│       ├── validators.py
│       ├── ports.py
│       ├── export.py
│       ├── logger.py
│       ├── privileges.py
│       ├── dependencies.py
│       ├── subnet.py
│       ├── wol.py
│       ├── dns_lookup.py
│       ├── traceroute.py
│       ├── tls_check.py
│       └── route_arp.py
└── tests/
    ├── test_scan_pipeline.py
    ├── test_monitor_stop.py
    ├── test_ports.py
    ├── test_config.py
    ├── test_validators.py
    ├── test_subnet.py
    └── test_wol.py
```

## Notes

- Keep `__version__` == `APP_VERSION` (CI enforced).
- No `shell=True`; subprocess uses argv lists.
- GUI network work runs in `QThread` workers.
