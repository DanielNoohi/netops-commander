"""Configuration management module."""

import copy
import yaml
from pathlib import Path
from typing import Any, Dict
from .constants import (
    DEFAULT_THEME,
    DEFAULT_SCAN_TIMEOUT,
    DEFAULT_SCAN_CONCURRENCY,
    DEFAULT_PORT_SCAN_TIMEOUT,
    DEFAULT_MONITOR_INTERVAL,
    DEFAULT_MONITOR_MAX_DEVICES,
    DEFAULT_HISTORY_RETENTION_DAYS,
)

DEFAULT_CONFIG: Dict[str, Any] = {
    "app": {
        "name": "NetOps Commander",
        "version": "1.3.0",
        "theme": DEFAULT_THEME,
        "scan_timeout": DEFAULT_SCAN_TIMEOUT,
        "scan_concurrency": DEFAULT_SCAN_CONCURRENCY,
        "tcp_connect_timeout": 1.0,
        "port_scan_concurrency": 64,
        "port_scan_timeout": DEFAULT_PORT_SCAN_TIMEOUT,
        "port_scan_ports": "21,22,23,25,53,80,110,135,139,143,443,445,993,995,1433,3306,3389,5432,5900,8080,8443",
        "monitoring_interval": DEFAULT_MONITOR_INTERVAL,
        "monitor_max_devices": DEFAULT_MONITOR_MAX_DEVICES,
        "history_retention_days": DEFAULT_HISTORY_RETENTION_DAYS,
        "public_ip_endpoints": [
            "https://api.ipify.org",
            "https://ifconfig.me/ip",
            "https://icanhazip.com",
        ],
        "vendor_cache_enabled": True,
        "log_level": "INFO",
        "log_max_bytes": 5242880,
        "log_backup_count": 3,
        "database_path": "netops_commander.db",
    }
}


class ConfigManager:
    """Manages application configuration from YAML file or defaults."""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        # Deep copy so nested mutations never alter DEFAULT_CONFIG
        self._config = copy.deepcopy(DEFAULT_CONFIG)
        self.load()

    def load(self) -> None:
        """Load configuration from file if exists, otherwise write defaults."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    file_cfg = yaml.safe_load(f)
                    if file_cfg and isinstance(file_cfg, dict):
                        self._update_deep(self._config, file_cfg)
            except Exception as e:
                print(f"[ConfigManager] Failed to load {self.config_path}: {e}")
        else:
            self.save()

    def save(self) -> None:
        """Save current configuration to file."""
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(self._config, f, default_flow_style=False)
        except Exception as e:
            print(f"[ConfigManager] Failed to save {self.config_path}: {e}")

    def get(self, key_path: str, default: Any = None) -> Any:
        """Retrieve config value by dot-separated path (e.g. 'app.theme')."""
        keys = key_path.split(".")
        val = self._config
        for k in keys:
            if isinstance(val, dict) and k in val:
                val = val[k]
            else:
                return default
        return val

    def set(self, key_path: str, value: Any) -> None:
        """Set config value by dot-separated path and save."""
        keys = key_path.split(".")
        d = self._config
        for k in keys[:-1]:
            if k not in d or not isinstance(d[k], dict):
                d[k] = {}
            d = d[k]
        d[keys[-1]] = value
        self.save()

    def _update_deep(self, target: dict, source: dict) -> None:
        """Deep update target dict with source dict."""
        for k, v in source.items():
            if k in target and isinstance(target[k], dict) and isinstance(v, dict):
                self._update_deep(target[k], v)
            else:
                target[k] = v


_global_config: ConfigManager | None = None


def get_config() -> ConfigManager:
    """Singleton getter for ConfigManager."""
    global _global_config
    if _global_config is None:
        _global_config = ConfigManager()
    return _global_config
