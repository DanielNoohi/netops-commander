"""Logger setup."""
import logging
from ..config import get_config

def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

def setup_logging() -> None:
    cfg = get_config()
    level = cfg.get("app.log_level", "INFO")
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    root = logging.getLogger()
    root.setLevel(getattr(logging, level))
    from logging.handlers import RotatingFileHandler
    fh = RotatingFileHandler("netops_commander.log", maxBytes=cfg.get("app.log_max_bytes", 5242880), backupCount=cfg.get("app.log_backup_count", 3))
    fh.setFormatter(formatter)
    ch = logging.StreamHandler()
    ch.setFormatter(formatter)
    root.handlers.clear()
    root.addHandler(fh)
    root.addHandler(ch)