"""Main application window."""
from __future__ import annotations

import asyncio

from PySide6.QtWidgets import (
    QMainWindow, QSplitter, QToolBar,
    QStatusBar, QMessageBox,
    QLabel, QApplication,
)
from PySide6.QtGui import QAction
from PySide6.QtCore import Qt, QTimer, QThread, Signal

from ..config import get_config
from ..database.models import Device, ScanHistory
from ..database.database import session_scope
from ..core.monitoring import MonitorController
from ..core.scanner import purge_ghost_devices
from ..utils.logger import get_logger
from ..utils.privileges import is_admin
from ..utils.dependencies import get_optional_dependencies
from ..utils.network import get_local_subnet
from .. import __version__
from .dashboard import DashboardWidget
from .device_table import DeviceTableWidget
from .themes import apply_theme
from .tools import (
    PingToolWidget,
    DnsToolDialog,
    TracerouteToolDialog,
    SubnetToolDialog,
    WolToolDialog,
    TlsToolDialog,
    RouteArpToolDialog,
)

log = get_logger(__name__)


class DependencyChecker(QThread):
    """Check optional dependencies in background to avoid UI freeze."""
    finished = Signal(dict)

    def run(self):
        self.finished.emit(get_optional_dependencies())


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
        self._deps_checker: DependencyChecker | None = None
        self._monitor_ctl = MonitorController()
        self._monitor_thread: MonitorThread | None = None
        # Drop leftover ghost ICMP rows from older buggy scans
        try:
            n = purge_ghost_devices()
            if n:
                log.info("Startup inventory cleanup removed %s ghost devices", n)
        except Exception as e:
            log.debug("ghost purge skipped: %s", e)
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

        self.device_table.inventory_changed.connect(self._refresh_dashboard)
        self.device_table.monitor_toggled.connect(self._on_monitor_toggled)

        self._build_menus()
        self._build_toolbar()

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.lbl_priv = QLabel()
        self.lbl_deps = QLabel()
        self.lbl_monitor = QLabel()
        self.lbl_ready = QLabel(f"Ready · v{__version__}")
        self.status_bar.addWidget(self.lbl_priv)
        self.status_bar.addWidget(self.lbl_deps)
        self.status_bar.addWidget(self.lbl_ready)
        self.status_bar.addPermanentWidget(self.lbl_monitor)

        cfg = get_config()
        apply_theme(QApplication.instance(), cfg.get("app.theme", "dark"))

    def _build_menus(self):
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
        tool_actions = [
            ("Scan Network…", self._toolbar_scan),
            ("Ping Tool", self._open_ping_tool),
            ("DNS Lookup", self._open_dns_tool),
            ("Traceroute", self._open_traceroute_tool),
            ("Subnet Calculator", self._open_subnet_tool),
            ("TLS Certificate Check", self._open_tls_tool),
            ("Wake-on-LAN", self._open_wol_tool),
            ("Route / ARP Tables", self._open_route_arp_tool),
        ]
        for label, slot in tool_actions:
            act = QAction(label, self)
            act.triggered.connect(slot)
            tools_menu.addAction(act)
        tools_menu.addSeparator()
        deps_action = QAction("Dependencies", self)
        deps_action.triggered.connect(self._show_dependencies)
        tools_menu.addAction(deps_action)

        help_menu = menu.addMenu("Help")
        about_act = QAction("About", self)
        about_act.triggered.connect(self._show_about)
        help_menu.addAction(about_act)

    def _build_toolbar(self):
        tb = QToolBar("Main")
        tb.setMovable(False)
        self.addToolBar(tb)
        actions = [
            ("Scan", self._toolbar_scan),
            ("Ping", self._open_ping_tool),
            ("DNS", self._open_dns_tool),
            ("Trace", self._open_traceroute_tool),
            ("Subnet", self._open_subnet_tool),
            ("TLS", self._open_tls_tool),
            ("WOL", self._open_wol_tool),
            ("Theme", self._toggle_theme),
        ]
        for label, slot in actions:
            act = QAction(label, self)
            act.triggered.connect(slot)
            tb.addAction(act)

    # ---- Theme ----
    def _toggle_theme(self):
        cfg = get_config()
        current = cfg.get("app.theme", "dark")
        new_theme = "light" if current == "dark" else "dark"
        cfg.set("app.theme", new_theme)
        apply_theme(QApplication.instance(), new_theme)
        self._theme_act.setText(
            f"Switch to {'Light' if new_theme == 'dark' else 'Dark'} Theme"
        )
        self.lbl_ready.setText(f"Theme → {new_theme}")

    # ---- Tools ----
    def _toolbar_scan(self):
        self.device_table.start_scan_dialog()

    def _open_ping_tool(self):
        PingToolWidget(self).exec()

    def _open_dns_tool(self):
        DnsToolDialog(self).exec()

    def _open_traceroute_tool(self):
        TracerouteToolDialog(self).exec()

    def _open_subnet_tool(self):
        SubnetToolDialog(self, initial_cidr=get_local_subnet() or "").exec()

    def _open_tls_tool(self):
        TlsToolDialog(self).exec()

    def _open_wol_tool(self):
        WolToolDialog(self).exec()

    def _open_route_arp_tool(self):
        RouteArpToolDialog(self).exec()

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
        self.lbl_ready.setText(f"Alert: {message}")

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
            return

        if self._deps_checker is not None and self._deps_checker.isRunning():
            return

        self._deps_checker = DependencyChecker()
        self._deps_checker.finished.connect(self._on_deps_checked)
        self._deps_checker.start()

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

    def _show_about(self):
        QMessageBox.about(
            self, "About NetOps Commander",
            f"NetOps Commander v{__version__}\n\n"
            "Network inventory, monitoring, and diagnostics.\n"
            "For authorized use only.\n"
            "Licensed under GPL-3.0.",
        )

    def closeEvent(self, event):
        if self._monitor_thread and self._monitor_thread.isRunning():
            self._monitor_ctl.stop()
            self._monitor_thread.wait(3000)
        event.accept()
