# NetOps Commander — Project Structure

```
netops_commander/
├── main.py                              # Entry point: QApplication + DB init + MainWindow
├── requirements.txt                     # Core runtime dependencies
├── requirements-optional.txt            # Optional deps (nmap, scapy, pysnmp)
├── README.md                            # User-facing docs (features, install, changelog)
├── config.yaml                          # Sample/default configuration
├── netops_commander/
│   ├── __init__.py                      # Package metadata: __version__ (mirrors constants)
│   ├── config.py                        # ConfigManager: YAML load/save + DEFAULT_CONFIG
│   ├── constants.py                     # APP_VERSION, ports, timeouts, limits, ICON_PATHS
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py                    # SQLAlchemy models (Device, ScanHistory, MonitorResult, Alert)
│   │   ├── database.py                  # Engine, session_scope, init_database (migrations + VACUUM)
│   │   └── migrations.py                # Schema migrations (versioned)
│   ├── core/
│   │   ├── __init__.py
│   │   ├── scanner.py                   # CancellableScan, scan_cidr, background_scan, persist_device
│   │   ├── discovery.py                 # async_ping, async_tcp_connect, discover_host, OUI vendors
│   │   ├── monitoring.py                # MonitorController (poll loop, alerts, clean stop)
│   │   └── alerts.py                    # Alert severity mapping + create_alert
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── main_window.py               # MainWindow, MonitorThread, menu bar, status bar
│   │   ├── dashboard.py                 # Network info, stats, alerts table (auto-refresh)
│   │   ├── device_table.py              # Inventory table, context menu, PingWorker, PortScanWorker
│   │   ├── device_dialog.py             # Add/Edit device dialog
│   │   ├── themes.py                    # Dark/light QSS themes + apply_theme
│   │   └── tools/
│   │       ├── __init__.py
│   │       └── ping_tool.py             # Standalone Ping Tool dialog (continuous ping)
│   └── utils/
│       ├── __init__.py
│       ├── network.py                   # Local interface info, gateway, DNS, public IP
│       ├── validators.py                # CIDR/IP/host/port validation, target limits
│       ├── ports.py                     # parse_open_ports / format_open_ports (JSON text ↔ list)
│       ├── export.py                    # export_csv / export_json / export_html
│       ├── logger.py                    # RotatingFileHandler + stdout setup
│       ├── privileges.py                # Admin/root detection
│       └── dependencies.py              # Optional dependency detection (nmap, scapy, ...)
└── tests/
    ├── test_scan_pipeline.py            # Scan pipeline: scan_cidr, background_scan, cancel
    ├── test_monitor_stop.py             # Monitor stop/cancel from another thread
    └── test_ports.py                    # parse_open_ports / format_open_ports unit tests
```

## Notes

- `__version__` in `netops_commander/__init__.py` must always match
  `APP_VERSION` in `netops_commander/constants.py` (enforced by CI).
- GUI modules import with relative imports (`from ..core.discovery import ...`).
- No `shell=True` anywhere — subprocess calls use explicit argument lists.
