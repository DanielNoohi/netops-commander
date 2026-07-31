netops_commander/
├── main.py                      # Entry point
├── requirements.txt
├── README.md
├── config.yaml                  # Sample configuration
├── netops_commander/
│   ├── __init__.py
│   ├── config.py                # Configuration management
│   ├── constants.py             # Constants and enums
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── database.py          # Database session and initialization
│   │   └── migrations.py        # Schema migrations
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── scanner.py           # Network scanner core logic
│   │   ├── discovery.py         # Device discovery methods
│   │   ├── workers.py           # Async background workers
│   │   ├── monitoring.py        # Continuous monitoring
│   │   └── alerts.py            # Alert system
│   │
│   ├── gui/
│   │   ├── __init__.py
│   │   ├── main_window.py       # Main application window
│   │   ├── dashboard.py         # Dashboard widget
│   │   ├── device_table.py      # Device table with sorting/filtering
│   │   ├── device_dialog.py     # Device detail/edit dialog
│   │   ├── themes.py            # Dark/light theme management
│   │   ├── widgets/
│   │   │   ├── __init__.py
│   │   │   ├── progress_overlay.py
│   │   │   ├── log_viewer.py
│   │   │   └── status_bar.py
│   │   └── tools/
│   │       ├── __init__.py
│   │       ├── ping_tool.py
│   │       ├── traceroute_tool.py
│   │       ├── dns_tool.py
│   │       ├── port_scanner_tool.py
│   │       ├── http_tls_tool.py
│   │       ├── subnet_calculator.py
│   │       ├── route_table_tool.py
│   │       ├── arp_table_tool.py
│   │       ├── interface_tool.py
│   │       ├── wifi_tool.py
│   │       ├── wol_tool.py
│   │       ├── duplicate_ip_tool.py
│   │       ├── connectivity_tool.py
│   │       └── launch_tools.py
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── network.py           # Network utilities
│   │   ├── validators.py        # Input validation
│   │   ├── export.py            # CSV/JSON/HTML export
│   │   ├── logger.py            # Logging setup
│   │   ├── privileges.py        # Privilege detection
│   │   ├── dependencies.py      # Optional dependency detection
│   │   └── helpers.py           # General helpers
│   │
│   └── tests/
│       ├── __init__.py
│       ├── test_network_utils.py
│       ├── test_validators.py
│       └── test_export.py