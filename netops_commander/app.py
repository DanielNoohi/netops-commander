"""Application bootstrap (shared by main.py and python -m netops_commander)."""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from netops_commander import __version__
from netops_commander.database.database import init_database
from netops_commander.utils.logger import setup_logging
from netops_commander.gui.main_window import MainWindow


def run() -> int:
    """Create QApplication, show MainWindow, return process exit code."""
    app = QApplication(sys.argv)
    app.setApplicationName("NetOps Commander")
    app.setApplicationVersion(__version__)

    init_database()
    setup_logging()

    import logging
    logging.info("Starting NetOps Commander v%s", __version__)

    window = MainWindow()
    window.show()
    return app.exec()


def main() -> None:
    """Console-script entry point."""
    raise SystemExit(run())
