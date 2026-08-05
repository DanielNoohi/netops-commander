"""Sortable/searchable device table."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QLineEdit, QPushButton, QProgressBar, QMessageBox,
    QMenu, QFileDialog, QInputDialog
)
from PySide6.QtCore import Qt, QThread, Signal

from ..database.database import session_scope
from ..database.models import Device
from ..core.scanner import background_scan, CancellableScan, persist_device, export_devices_csv, export_devices_json
from ..utils.export import export_csv, export_json, export_html
from ..utils.validators import validate_cidr
from ..utils.network import get_local_subnet
from ..utils.logger import get_logger

log = get_logger(__name__)


class ScanThread(QThread):
    scan_finished = Signal(list)
    scan_error = Signal(str)
    progress = Signal(str, int, int)

    def __init__(self, cidr: str):
        super().__init__()
        self.cidr = cidr
        self._mgr = CancellableScan()

    def run(self):
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            def _done(devices):
                self.scan_finished.emit(devices)

            def _err(e):
                self.scan_error.emit(str(e))

            loop.run_until_complete(
                background_scan(
                    self.cidr,
                    scan_mgr=self._mgr,
                    done_callback=_done,
                    error_callback=_err,
                )
            )
            loop.close()
        except Exception as e:
            self.scan_error.emit(str(e))

    def cancel(self):
        if self._mgr:
            self._mgr.cancel()


class DeviceTableWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._scan_thread = None
        self._setup_ui()
        self.reload_data()

    def _setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)

        tb = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search devices...")
        self.search.textChanged.connect(self._apply_filter)
        self.btn_scan = QPushButton("Scan")
        self.btn_scan.clicked.connect(self.start_scan_dialog)
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.cancel_scan)
        self.btn_cancel.setEnabled(False)
        self.btn_export = QPushButton("Export")
        self.btn_export.clicked.connect(self._export_menu)
        tb.addWidget(self.search)
        tb.addWidget(self.btn_scan)
        tb.addWidget(self.btn_cancel)
        tb.addWidget(self.btn_export)
        layout.addLayout(tb)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        self.table = QTableWidget(0, 13)
        self.table.setHorizontalHeaderLabels([
            "IP", "MAC", "Hostname", "Vendor", "Type", "Online",
            "Latency", "Ports", "Notes", "Tags", "Monitored",
            "First Seen", "Last Seen"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        layout.addWidget(self.table)

    def reload_data(self):
        with session_scope() as session:
            devices = session.query(Device).order_by(Device.ip_address).all()
        self._populate(devices)

    def _populate(self, devices):
        self.table.setRowCount(len(devices))
        for row, d in enumerate(devices):
            vals = [
                d.ip_address,
                d.mac_address or "",
                d.hostname or "",
                d.vendor or "",
                d.device_type or "",
                "Yes" if d.online else "No",
                f"{d.latency_ms:.1f}" if d.latency_ms else "",
                ", ".join(map(str, d.open_ports)) if d.open_ports else "",
                d.notes or "",
                d.tags or "",
                "Yes" if d.is_monitored else "No",
                d.first_seen.strftime("%Y-%m-%d %H:%M") if d.first_seen else "",
                d.last_seen.strftime("%Y-%m-%d %H:%M") if d.last_seen else "",
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(str(val))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, d.id)
                self.table.setItem(row, col, item)

    def _apply_filter(self):
        text = self.search.text().lower()
        for row in range(self.table.rowCount()):
            visible = False
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and text in item.text().lower():
                    visible = True
                    break
            self.table.setRowHidden(row, not visible)

    def start_scan_dialog(self):
        cidr, ok = QInputDialog.getText(self, "Scan Network", "CIDR (e.g. 192.168.1.0/24):", text=get_local_subnet())
        if not ok or not cidr:
            return
        valid, msg = validate_cidr(cidr)
        if not valid:
            QMessageBox.warning(self, "Invalid CIDR", msg)
            return
        # Guard against concurrent scans (leaks the previous thread)
        if self._scan_thread and self._scan_thread.isRunning():
            QMessageBox.information(self, "Scan in progress", "A scan is already running.")
            return
        self._scan_thread = ScanThread(cidr)
        self._scan_thread.progress.connect(self._on_scan_progress)
        self._scan_thread.scan_finished.connect(self._scan_done)
        self._scan_thread.scan_error.connect(self._scan_error)
        self.btn_scan.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.progress.setVisible(True)
        self.progress.setValue(0)
        self._scan_thread.start()

    def _on_scan_progress(self, ip: str, count: int, total: int):
        self.progress.setMaximum(total)
        self.progress.setValue(count)

    def _scan_done(self, devices):
        self.btn_scan.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress.setVisible(False)
        for d in devices:
            persist_device(d)
        self.reload_data()
        QMessageBox.information(self, "Scan Complete", f"Discovered {len(devices)} online devices.")

    def _scan_error(self, msg):
        self.btn_scan.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress.setVisible(False)
        QMessageBox.critical(self, "Scan Error", msg)

    def cancel_scan(self):
        if self._scan_thread and self._scan_thread.isRunning():
            self._scan_thread.cancel()
            self._scan_thread.wait(2000)
        self._scan_error("Cancelled by user.")

    def _context_menu(self, pos):
        menu = QMenu()
        monitor_act = menu.addAction("Toggle Monitoring")
        edit_act = menu.addAction("Edit Notes/Tags")
        ping_act = menu.addAction("Ping")
        ports_act = menu.addAction("Port Scan")
        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == monitor_act:
            self._toggle_monitor()
        elif action == edit_act:
            self._edit_device()
        elif action == ping_act:
            self._ping_selected()
        elif action == ports_act:
            self._portscan_selected()

    def _toggle_monitor(self):
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()})
        if not rows:
            return
        with session_scope() as session:
            for row in rows:
                dev_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
                dev = session.get(Device, dev_id)
                if dev:
                    dev.is_monitored = not dev.is_monitored
        self.reload_data()

    def _edit_device(self):
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()})
        if not rows:
            return
        row = rows[0]
        dev_id = self.table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        with session_scope() as session:
            dev = session.get(Device, dev_id)
            if dev:
                notes, ok = QInputDialog.getMultiLineText(self, "Notes", "Notes:", dev.notes or "")
                if ok:
                    dev.notes = notes
                tags, ok = QInputDialog.getText(self, "Tags", "Tags (comma separated):", text=dev.tags or "")
                if ok:
                    dev.tags = tags
        self.reload_data()

    def _ping_selected(self):
        QMessageBox.information(self, "Ping", "Ping tool - opens in Tools menu")

    def _portscan_selected(self):
        QMessageBox.information(self, "Port Scan", "Port scan tool - opens in Tools menu")

    def monitor_selected(self):
        self._toggle_monitor()

    def _export_menu(self):
        from PySide6.QtWidgets import QMenu
        menu = QMenu()
        for fmt in ("csv", "json", "html"):
            act = menu.addAction(f"Export as {fmt.upper()}")
            act.triggered.connect(lambda checked, f=fmt: self.export_devices(f))
        menu.exec(self.btn_export.mapToGlobal(self.btn_export.rect().bottomLeft()))

    def export_devices(self, fmt: str):
        with session_scope() as session:
            devices = session.query(Device).all()
        rows = []
        for d in devices:
            rows.append({
                "ip_address": d.ip_address,
                "mac_address": d.mac_address or "",
                "hostname": d.hostname or "",
                "vendor": d.vendor or "",
                "device_type": d.device_type or "",
                "online": d.online,
                "latency_ms": d.latency_ms or "",
                "open_ports": ", ".join(map(str, d.open_ports)) if d.open_ports else "",
                "notes": d.notes or "",
                "tags": d.tags or "",
                "is_monitored": d.is_monitored,
                "first_seen": d.first_seen.isoformat() if d.first_seen else "",
                "last_seen": d.last_seen.isoformat() if d.last_seen else "",
            })
        if not rows:
            QMessageBox.information(self, "Export", "No data to export")
            return
        fname, _ = QFileDialog.getSaveFileName(self, f"Export as {fmt.upper()}", f"devices.{fmt}")
        if not fname:
            return
        if fmt == "csv":
            export_csv(fname, rows)
        elif fmt == "json":
            export_json(fname, rows)
        elif fmt == "html":
            export_html(fname, "NetOps Commander - Device Export", rows)
        QMessageBox.information(self, "Export", f"Exported {len(rows)} devices to {fname}")