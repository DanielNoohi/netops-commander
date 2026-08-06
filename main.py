#!/usr/bin/env python3
"""
NetOps Commander - Main entry point
"""

import sys

from PySide6.QtWidgets import QApplication

from netops_commander import __version__
from netops_commander.database.database import init_database
from netops_commander.utils.logger import setup_logging
from netops_commander.gui.main_window import MainWindow


def main():
    """Application entry point."""
    app = QApplication(sys.argv)
    app.setApplicationName("NetOps Commander")
    app.setApplicationVersion(__version__)

    # Initialize database (create tables + run migrations)
    init_database()

    # Setup logging (RotatingFileHandler + stdout)
    setup_logging()

    import logging
    logging.info("Starting NetOps Commander v%s", __version__)

    # Create and show main window (theme applied inside MainWindow)
    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
