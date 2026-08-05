"""Main application window."""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QToolBar, QStatusBar, QMenuBar, QFileDialog, QMessageBox,
    QProgressBar, QLabel
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal

from ..config import get_config
from ..database.database import init_database
from ..utils.logger import get_logger
from ..utils.privileges import is_admin, privilege_guidance
from ..utils.dependencies import get_optional_dependencies
from .. import __version__
from .dashboard import DashboardWidget
from .device_table import DeviceTableWidget

log = get_logger(__name__)


class DependencyChecker(QThread):
    """Check optional dependencies in background to avoid UI freeze."""
    finished = Signal(dict)

    def run(self):
        self.finished.emit(get_optional_dependencies())


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"NetOps Commander v{__version__}")
        self.setMinimumSize(1400, 900)
        self._deps = {}  # Cache dependency results
        self._build_ui()
        self._start_status_refresh()

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
        self.status_bar.addWidget(self.lbl_priv)
        self.status_bar.addPermanentWidget(self.lbl_deps)

    def _start_status_refresh(self):
        """Start periodic status refresh (deps cached, runs in background)."""
        self._refresh_status()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_status)
        self._timer.start(30_000)  # Every 30s instead of 5s

    def _refresh_status(self):
        """Refresh status bar — deps checked in background thread."""
        # Privilege check (fast, no subprocess)
        if is_admin():
            self.lbl_priv.setText("✓ Running as Administrator")
        else:
            self.lbl_priv.setText("⚠ Standard user — some features limited")

        # Dependency check (cached after first run, then background refresh)
        if not self._deps:
            # First run: check synchronously to populate UI immediately
            self._deps = get_optional_dependencies()
            self._update_deps_label()
        else:
            # Subsequent runs: check in background
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

    def _show_about(self):
        QMessageBox.about(
            self, "About NetOps Commander",
            f"NetOps Commander v{__version__}\n\n"
            "Professional network administration tool.\n"
            "For authorized use only."
        )
