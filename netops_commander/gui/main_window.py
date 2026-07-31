"""Main application window."""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QToolBar, QStatusBar, QMenuBar, QFileDialog, QMessageBox,
    QProgressBar, QLabel
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QIcon

from ..config import get_config
from ..database.database import init_database
from ..utils.logger import get_logger, setup_logging
from ..utils.privileges import is_admin, privilege_guidance
from ..utils.dependencies import get_optional_dependencies
from .dashboard import DashboardWidget
from .device_table import DeviceTableWidget

log = get_logger(__name__)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NetOps Commander v1.1.0")
        self.setMinimumSize(1400, 900)
        self._setup_logging()
        self._build_ui()
        self._start_status_refresh()

    def _setup_logging(self):
        setup_logging()

    def _build_ui(self):
        central = QSplitter(Qt.Orientation.Horizontal)
        self.dashboard = DashboardWidget()
        self.device_table = DeviceTableWidget()
        central.addWidget(self.dashboard)
        central.addWidget(self.device_table)
        central.setSizes([400, 1000])
        self.setCentralWidget(central)

        menu = self.menuBar()
        file_menu = menu.addMenu("File")
        export_menu = file_menu.addMenu("Export")
        for fmt in ("csv", "json", "html"):
            act = QAction(f"Export as {fmt.upper()}", self)
            act.triggered.connect(lambda checked, f=fmt: self.device_table.export_devices(f))
            export_menu.addAction(act)
        exit_act = QAction("Exit", self)
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)

        tools_menu = menu.addMenu("Tools")
        help_menu = menu.addMenu("Help")
        about_act = QAction("About", self)
        about_act.triggered.connect(self._show_about)
        help_menu.addAction(about_act)

        tb = QToolBar()
        self.addToolBar(tb)
        scan_act = QAction("Scan", self)
        scan_act.triggered.connect(self.device_table.start_scan_dialog)
        tb.addAction(scan_act)
        mon_act = QAction("Monitor", self)
        mon_act.triggered.connect(self.device_table.monitor_selected)
        tb.addAction(mon_act)
        refresh_act = QAction("Refresh", self)
        refresh_act.triggered.connect(self.device_table.reload_data)
        tb.addAction(refresh_act)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status_label = QLabel(privilege_guidance())
        self.progress = QProgressBar()
        self.progress.setMaximumWidth(300)
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setVisible(False)
        self.status.addWidget(self.status_label, 1)
        self.status.addWidget(self.progress)

        self._set_theme()

    def _set_theme(self):
        theme = get_config().get("app.theme", "dark")
        if theme == "dark":
            self.setStyleSheet(self._dark_stylesheet())
        else:
            self.setStyleSheet(self._light_stylesheet())

    def _dark_stylesheet(self) -> str:
        return """
        QMainWindow { background-color: #121212; }
        QMenuBar, QToolBar { background-color: #1a1a1a; }
        QTableWidget { background-color: #1a1a1a; gridline-color: #333; }
        QHeaderView::section { background-color: #333; color: #eee; }
        QPushButton { background-color: #2563eb; color: white; border-radius: 4px; padding: 4px 8px; }
        QPushButton:hover { background-color: #1d4ed8; }
        QLineEdit, QComboBox, QTextEdit { background-color: #444; color: #eee; border: 1px solid #555; border-radius: 4px; padding: 4px; }
        """

    def _light_stylesheet(self) -> str:
        return """
        QMainWindow { background-color: #f3f4f6; }
        QMenuBar, QToolBar { background-color: #e5e7eb; }
        QTableWidget { background-color: #fff; gridline-color: #d1d5db; }
        QHeaderView::section { background-color: #e5e7eb; color: #111; }
        QPushButton { background-color: #2563eb; color: white; border-radius: 4px; padding: 4px 8px; }
        QPushButton:hover { background-color: #1d4ed8; }
        QLineEdit, QComboBox, QTextEdit { background-color: #fff; color: #111; border: 1px solid #d1d5db; border-radius: 4px; padding: 4px; }
        """

    def _start_status_refresh(self):
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_status)
        self.timer.start(5000)
        self._update_status()

    def _update_status(self):
        deps = get_optional_dependencies()
        admin = is_admin()
        text = f"Admin: {'Yes' if admin else 'No'} | nmap: {'OK' if deps['nmap'] else 'N/A'} | scapy: {'OK' if deps['scapy'] else 'N/A'} | SNMP: {'OK' if deps['pysnmp'] else 'N/A'}"
        self.status_label.setText(text)

    def _show_about(self):
        QMessageBox.information(self, "About", "NetOps Commander v1.1.0\nProfessional network administration tool.\nAuthorized use only.")