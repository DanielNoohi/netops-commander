#!/usr/bin/env python3
"""
NetOps Commander - Main entry point
"""

import sys
import logging
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon

from netops_commander.config import get_config
from netops_commander.database.database import init_database
from netops_commander.gui.main_window import MainWindow


def setup_logging():
    """Configure application logging."""
    config = get_config()
    log_level = config.get("app.log_level", "INFO")
    log_max_bytes = config.get("app.log_max_bytes", 5242880)
    log_backup_count = config.get("app.log_backup_count", 3)

    logging.basicConfig(
        level=getattr(logging, log_level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("netops_commander.log", mode="a"),
            logging.StreamHandler(sys.stdout)
        ]
    )


def main():
    """Application entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("NetOps Commander")
    app.setApplicationVersion("1.0.0")
    app.setWindowIcon(QIcon(":/icons/app.png"))  # Placeholder

    # Initialize database
    init_database()

    # Setup logging
    setup_logging()
    logging.info("Starting NetOps Commander")

    # Create and show main window
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()