"""Main application window."""
from __future__ import annotations

import asyncio

from PySide6.QtWidgets import (
    QMainWindow, QSplitter,
    QStatusBar, QMessageBox,
    QLabel,
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, QTimer, QThread, Signal

from ..config import get_config
from ..database.models import Device, ScanHistory
from ..database.database import session_scope
from ..core.monitoring import MonitorController
from ..utils.logger import get_logger
from ..utils.privileges import is_admin
from ..utils.dependencies import get_optional_dependencies
from .. import __version__
from .dashboard import DashboardWidget
from .device_table import DeviceTableWidget
from .themes import apply_theme
from .tools.ping_tool import PingToolWidget

log = get_logger(__name__)


class DependencyChecker(QThread):
    """Check optional dependencies in background to avoid UI freeze."""
    finished = Signal(dict)
    _running = False

    def run(self):
        DependencyChecker._running = True
        try:
            self.finished.emit(get_optional_dependencies())
        finally:
            DependencyChecker._running = False


class MonitorThread(QThread):
    """Drive MonitorController in a dedicated asyncio event loop."""
    alert = Signal(str, str, object)  # severity, message, device_id

    def __init__(self, controller: MonitorController):
        super().__init__()
        self._ctl = controller

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._ctl.alert_callback = lambda sev, msg, did: self.alert.emit(sev, msg, did)
        try:
            self._ctl.run_forever(loop)
        finally:
            try:
                loop.close()
            except RuntimeError:
                pass


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"NetOps Commander v{__version__}")
        self.setMinimumSize(1400, 900)
        self._deps: dict = {}
        self._monitor_ctl = MonitorController()
        self._monitor_thread: MonitorThread | None = None
        self._build_ui()
        self._start_status_refresh()
        self._start_monitoring()
        self._refresh_dashboard()

    def _build_ui(self):
        central = QSplitter(Qt.Orientation.Horizontal)
        self.dashboard = DashboardWidget()
        self.device_table = DeviceTableWidget()
        central.addWidget(self.dashboard)
        central.addWidget(self.device_table)
        central.setSizes([400, 1000])
        self.setCentralWidget(central)

        # Connect signals
        self.device_table.inventory_changed.connect(self._refresh_dashboard)
        self.device_table.monitor_toggled.connect(self._on_monitor_toggled)

        menu = self.menuBar()
        file_menu = menu.addMenu("File")
        export_menu = file_menu.addMenu("Export")
        for fmt in ("csv", "json", "html"):
            act = QAction(f"Export as {fmt.upper()}", self)
            act.triggered.connect(lambda checked, f=fmt: self.device_table.export_devices(f))
            export_menu.addAction(act)
        file_menu.addSeparator()
        exit_act = QAction("Exit", self)
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)

        view_menu = menu.addMenu("View")
        cfg = get_config()
        current_theme = cfg.get("app.theme", "dark")
        self._theme_act = QAction(
            f"Switch to {'Light' if current_theme == 'dark' else 'Dark'} Theme", self
        )
        self._theme_act.triggered.connect(self._toggle_theme)
        view_menu.addAction(self._theme_act)

        tools_menu = menu.addMenu("Tools")
        ping_act = QAction("Ping Tool", self)
        ping_act.triggered.connect(self._open_ping_tool)
        tools_menu.addAction(ping_act)
        deps_action = QAction("Dependencies", self)
        deps_action.triggered.connect(self._show_dependencies)
        tools_menu.addAction(deps_action)

        help_menu = menu.addMenu("Help")
        about_act = QAction("About", self)
        about_act.triggered.connect(self._show_about)
        help_menu.addAction(about_act)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.lbl_priv = QLabel()
        self.lbl_deps = QLabel()
        self.lbl_monitor = QLabel()
        self.status_bar.addWidget(self.lbl_priv)
        self.status_bar.addWidget(self.lbl_deps)
        self.status_bar.addPermanentWidget(self.lbl_monitor)

        # Apply theme
        apply_theme(self, current_theme)

    # ---- Theme ----
    def _toggle_theme(self):
        cfg = get_config()
        current = cfg.get("app.theme", "dark")
        new_theme = "light" if current == "dark" else "dark"
        cfg["app"]["theme"] = new_theme
        apply_theme(self, new_theme)
        self._theme_act.setText(f"Switch to {'Light' if new_theme == 'dark' else 'Dark'} Theme")

    # ---- Monitoring ----
    def _start_monitoring(self):
        count = self._monitor_ctl.load_from_db()
        if count > 0 and self._monitor_ctl.running is False:
            self._monitor_thread = MonitorThread(self._monitor_ctl)
            self._monitor_thread.alert.connect(self._on_monitor_alert)
            self._monitor_thread.start()
        self.lbl_monitor.setText(f"Monitoring: {count} devices")

    def _on_monitor_toggled(self, device_id: int, ip: str, monitored: bool):
        self._monitor_ctl.sync_device(device_id, ip, monitored)
        count = len(self._monitor_ctl.devices)
        self.lbl_monitor.setText(f"Monitoring: {count} devices")
        # Start monitoring loop if we now have devices
        if count > 0 and (self._monitor_thread is None or not self._monitor_thread.isRunning()):
            self._monitor_thread = MonitorThread(self._monitor_ctl)
            self._monitor_thread.alert.connect(self._on_monitor_alert)
            self._monitor_thread.start()
        elif count == 0 and self._monitor_thread and self._monitor_thread.isRunning():
            self._monitor_ctl.stop()
            self._monitor_thread.wait(2000)

    def _on_monitor_alert(self, severity: str, message: str, device_id):
        self.dashboard.add_alert_from_db()
        self._refresh_dashboard()

    # ---- Dashboard refresh ----
    def _refresh_dashboard(self):
        with session_scope() as session:
            total = session.query(Device).count()
            online = session.query(Device).filter(Device.online.is_(True)).count()
            offline = total - online
            scans = session.query(ScanHistory).count()
        self.dashboard.update_stats(online, offline, total, scans)
        self.dashboard.reload_alerts()

    # ---- Status bar ----
    def _start_status_refresh(self):
        self._refresh_status()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_status)
        self._timer.start(30_000)

    def _refresh_status(self):
        if is_admin():
            self.lbl_priv.setText("✓ Running as Administrator")
        else:
            self.lbl_priv.setText("⚠ Standard user — some features limited")

        if not self._deps:
            self._deps = get_optional_dependencies()
            self._update_deps_label()
        elif not DependencyChecker._running:
            checker = DependencyChecker()
            checker.finished.connect(self._on_deps_checked)
            checker.start()

    def _on_deps_checked(self, deps):
        self._deps = deps
        self._update_deps_label()

    def _update_deps_label(self):
        count = sum(1 for v in self._deps.values() if v)
        self.lbl_deps.setText(f"Optional deps: {count}/{len(self._deps)}")

    def _show_dependencies(self):
        deps = self._deps or get_optional_dependencies()
        lines = [f"  {'✓' if v else '✗'} {k}" for k, v in deps.items()]
        QMessageBox.information(self, "Dependencies", "\n".join(lines))

    def _open_ping_tool(self):
        widget = PingToolWidget()
        widget.setWindowModality(Qt.WindowModality.ApplicationModal)
        widget.exec()

    def _show_about(self):
        QMessageBox.about(
            self, "About NetOps Commander",
            f"NetOps Commander v{__version__}\n\n"
            "Professional network administration tool.\n"
            "For authorized use only.\n"
            "Licensed under GPL-3.0.",
        )

    def closeEvent(self, event):
        """Stop monitoring on exit."""
        if self._monitor_thread and self._monitor_thread.isRunning():
            self._monitor_ctl.stop()
            self._monitor_thread.wait(3000)
        event.accept()
