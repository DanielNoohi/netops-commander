"""Sortable/searchable device table."""
from __future__ import annotations
import asyncio

from typing import Optional, Callable

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QLineEdit, QPushButton, QProgressBar, QMessageBox,
    QMenu, QFileDialog, QInputDialog, QDialog,
    QTextEdit,
)
from PySide6.QtCore import Qt, QThread, Signal

from ..database.database import session_scope
from ..database.models import Device
from ..core.scanner import (
    background_scan,
    CancellableScan,
    persist_device,
    reconcile_scan_results,
)
from ..core.discovery import async_ping, async_tcp_connect
from ..utils.export import export_csv, export_json, export_html
from ..utils.validators import validate_cidr, validate_port_range
from ..utils.network import get_local_subnet
from ..utils.ports import parse_open_ports, format_open_ports
from ..utils.logger import get_logger
from ..config import get_config
from ..constants import DEFAULT_PORTS, PORT_SCAN_MAX_PORTS
from .device_dialog import DeviceDialog

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
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            def _done(devices):
                self.scan_finished.emit(devices)

            def _err(e):
                self.scan_error.emit(str(e))

            def _progress(ip, count, total):
                # QThread Signal is thread-safe
                self.progress.emit(ip, count + 1, total)

            loop.run_until_complete(
                background_scan(
                    self.cidr,
                    scan_mgr=self._mgr,
                    done_callback=_done,
                    error_callback=_err,
                    progress_callback=_progress,
                )
            )
            loop.close()
        except Exception as e:
            self.scan_error.emit(str(e))

    def cancel(self):
        if self._mgr:
            self._mgr.cancel()


class PingWorker(QThread):
    line = Signal(str)
    finished_ok = Signal()

    def __init__(self, host: str, count: int = 4, interval: float = 1.0):
        super().__init__()
        self.host = host
        self.count = count
        self.interval = interval
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._run(loop))
        finally:
            loop.close()
            self.finished_ok.emit()

    async def _run(self, loop):
        sent = 0
        received = 0
        latencies = []
        self.line.emit(f"Pinging {self.host} with {self.count} probes...")
        for i in range(self.count):
            if self._stop:
                self.line.emit("Stopped by user.")
                break
            sent += 1
            online, latency = await async_ping(self.host, timeout=2.0)
            if online:
                received += 1
                latencies.append(latency or 0.0)
                self.line.emit(
                    f"  reply from {self.host}: time={latency:.1f} ms"
                    if latency is not None
                    else f"  reply from {self.host}"
                )
            else:
                self.line.emit(f"  request timed out ({i + 1}/{self.count})")
            if i + 1 < self.count and not self._stop:
                await asyncio.sleep(self.interval)
        loss = 100.0 * (sent - received) / sent if sent else 0.0
        avg = (sum(latencies) / len(latencies)) if latencies else None
        avg_s = f"{avg:.1f} ms" if avg is not None else "n/a"
        self.line.emit(
            f"Stats: sent={sent} recv={received} loss={loss:.0f}% avg={avg_s}"
        )


class PortScanWorker(QThread):
    line = Signal(str)
    finished_ok = Signal(list)

    def __init__(self, host: str, ports: list[int], timeout: float = 0.8):
        super().__init__()
        self.host = host
        self.ports = ports[:PORT_SCAN_MAX_PORTS]
        self.timeout = timeout
        self._stop = False

    def stop(self):
        self._stop = True

    def run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        open_ports: list[int] = []
        try:
            open_ports = loop.run_until_complete(self._run())
        finally:
            loop.close()
            self.finished_ok.emit(open_ports)

    async def _run(self) -> list[int]:
        self.line.emit(f"TCP port scan {self.host} ({len(self.ports)} ports)...")
        sem = asyncio.Semaphore(32)
        open_ports: list[int] = []

        async def check(port: int):
            if self._stop:
                return
            async with sem:
                ok = await async_tcp_connect(self.host, port, timeout=self.timeout)
            if ok:
                open_ports.append(port)
                self.line.emit(f"  open: {port}")

        await asyncio.gather(*(check(p) for p in self.ports))
        open_ports.sort()
        self.line.emit(
            f"Done. Open: {', '.join(map(str, open_ports)) if open_ports else '(none)'}"
        )
        return open_ports


class ToolLogDialog(QDialog):
    """Simple log dialog for ping / port-scan workers."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(520, 360)
        layout = QVBoxLayout(self)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        layout.addWidget(self.log)
        self.btn_stop = QPushButton("Stop")
        self.btn_close = QPushButton("Close")
        self.btn_close.setEnabled(False)
        row = QHBoxLayout()
        row.addWidget(self.btn_stop)
        row.addWidget(self.btn_close)
        layout.addLayout(row)
        self.btn_close.clicked.connect(self.accept)
        self._worker = None

    def append(self, text: str):
        self.log.append(text)

    def attach_worker(self, worker: QThread, stop_fn: Callable):
        self._worker = worker
        self.btn_stop.clicked.connect(stop_fn)

        def _done(*_args):
            self.btn_stop.setEnabled(False)
            self.btn_close.setEnabled(True)

        if hasattr(worker, "finished_ok"):
            worker.finished_ok.connect(_done)
        worker.finished.connect(_done)


class DeviceTableWidget(QWidget):
    """Inventory table + scan/export/context actions."""

    # Emitted after scan/monitor toggle so MainWindow can refresh dashboard
    inventory_changed = Signal()
    monitor_toggled = Signal(int, str, bool)  # device_id, ip, monitored

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scan_thread: Optional[ScanThread] = None
        self._tool_workers: list[QThread] = []
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
            "First Seen", "Last Seen",
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._context_menu)
        self.table.doubleClicked.connect(lambda _idx: self._edit_device())
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

    def reload_data(self):
        with session_scope() as session:
            devices = session.query(Device).order_by(Device.ip_address).all()
            # Detach values while session open
            snapshot = []
            for d in devices:
                snapshot.append({
                    "id": d.id,
                    "ip_address": d.ip_address,
                    "mac_address": d.mac_address or "",
                    "hostname": d.hostname or "",
                    "vendor": d.vendor or "",
                    "device_type": d.device_type or "",
                    "online": bool(d.online),
                    "latency_ms": d.latency_ms,
                    "open_ports": d.open_ports,
                    "notes": d.notes or "",
                    "tags": d.tags or "",
                    "is_monitored": bool(d.is_monitored),
                    "first_seen": d.first_seen,
                    "last_seen": d.last_seen,
                })
        self._populate(snapshot)

    def _populate(self, devices):
        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(devices))
        for row, d in enumerate(devices):
            ports_str = format_open_ports(d.get("open_ports"))
            vals = [
                d["ip_address"],
                d["mac_address"],
                d["hostname"],
                d["vendor"],
                d["device_type"],
                "Yes" if d["online"] else "No",
                f"{d['latency_ms']:.1f}" if d.get("latency_ms") is not None else "",
                ports_str,
                d["notes"],
                d["tags"],
                "Yes" if d["is_monitored"] else "No",
                d["first_seen"].strftime("%Y-%m-%d %H:%M") if d.get("first_seen") else "",
                d["last_seen"].strftime("%Y-%m-%d %H:%M") if d.get("last_seen") else "",
            ]
            for col, val in enumerate(vals):
                item = QTableWidgetItem(str(val))
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                if col == 0:
                    item.setData(Qt.ItemDataRole.UserRole, d["id"])
                self.table.setItem(row, col, item)
        self.table.setSortingEnabled(True)

    def _apply_filter(self):
        text = self.search.text().lower()
        for row in range(self.table.rowCount()):
            visible = False if text else True
            if text:
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item and text in item.text().lower():
                        visible = True
                        break
            self.table.setRowHidden(row, not visible)

    def start_scan_dialog(self):
        cidr, ok = QInputDialog.getText(
            self,
            "Scan Network",
            "CIDR (e.g. 192.168.1.0/24):",
            text=get_local_subnet(),
        )
        if not ok or not cidr:
            return
        valid, msg = validate_cidr(cidr)
        if not valid:
            QMessageBox.warning(self, "Invalid CIDR", msg)
            return
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
        self.progress.setMaximum(max(total, 1))
        self.progress.setValue(min(count, total))
        self.progress.setFormat(f"{count}/{total}  {ip}")

    def _scan_done(self, devices):
        self.btn_scan.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress.setVisible(False)
        cidr = self._scan_thread.cidr if self._scan_thread else ""
        removed = 0
        if cidr:
            _saved, removed = reconcile_scan_results(cidr, devices)
        else:
            for d in devices:
                persist_device(d)
        self.reload_data()
        self.inventory_changed.emit()
        msg = f"Discovered {len(devices)} online devices."
        if removed:
            msg += f"\nRemoved {removed} stale/ghost entries from inventory."
        QMessageBox.information(self, "Scan Complete", msg)

    def _scan_error(self, msg):
        self.btn_scan.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress.setVisible(False)
        if msg and "Cancelled" not in msg:
            QMessageBox.critical(self, "Scan Error", msg)
        else:
            QMessageBox.information(self, "Scan", msg or "Cancelled.")

    def cancel_scan(self):
        if self._scan_thread and self._scan_thread.isRunning():
            self._scan_thread.cancel()
            self._scan_thread.wait(2000)
        self.btn_scan.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.progress.setVisible(False)
        QMessageBox.information(self, "Scan", "Cancelled by user.")

    def _selected_device_ids(self) -> list[int]:
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()})
        ids = []
        for row in rows:
            item = self.table.item(row, 0)
            if item:
                dev_id = item.data(Qt.ItemDataRole.UserRole)
                if dev_id is not None:
                    ids.append(int(dev_id))
        return ids

    def _context_menu(self, pos):
        menu = QMenu(self)
        monitor_act = menu.addAction("Toggle Monitoring")
        edit_act = menu.addAction("Edit Device")
        menu.addSeparator()
        ping_act = menu.addAction("Ping")
        ports_act = menu.addAction("Port Scan")
        dns_act = menu.addAction("DNS Lookup")
        trace_act = menu.addAction("Traceroute")
        tls_act = menu.addAction("TLS Check")
        wol_act = menu.addAction("Wake-on-LAN")
        action = menu.exec(self.table.viewport().mapToGlobal(pos))
        if action == monitor_act:
            self._toggle_monitor()
        elif action == edit_act:
            self._edit_device()
        elif action == ping_act:
            self._ping_selected()
        elif action == ports_act:
            self._portscan_selected()
        elif action == dns_act:
            self._dns_selected()
        elif action == trace_act:
            self._traceroute_selected()
        elif action == tls_act:
            self._tls_selected()
        elif action == wol_act:
            self._wol_selected()

    def _selected_host_mac(self):
        ids = self._selected_device_ids()
        if not ids:
            return None, None
        with session_scope() as session:
            dev = session.get(Device, ids[0])
            if not dev:
                return None, None
            return dev.ip_address, dev.mac_address or ""

    def _dns_selected(self):
        from .tools.dns_tool import DnsToolDialog
        host, _ = self._selected_host_mac()
        if not host:
            return
        DnsToolDialog(self, initial_host=host).exec()

    def _traceroute_selected(self):
        from .tools.traceroute_tool import TracerouteToolDialog
        host, _ = self._selected_host_mac()
        if not host:
            return
        TracerouteToolDialog(self, initial_host=host).exec()

    def _tls_selected(self):
        from .tools.tls_tool import TlsToolDialog
        host, _ = self._selected_host_mac()
        if not host:
            return
        TlsToolDialog(self, initial_host=host).exec()

    def _wol_selected(self):
        from .tools.wol_tool import WolToolDialog
        _, mac = self._selected_host_mac()
        WolToolDialog(self, initial_mac=mac or "").exec()

    def _toggle_monitor(self):
        ids = self._selected_device_ids()
        if not ids:
            return
        with session_scope() as session:
            for dev_id in ids:
                dev = session.get(Device, dev_id)
                if not dev:
                    continue
                dev.is_monitored = not bool(dev.is_monitored)
                self.monitor_toggled.emit(dev.id, dev.ip_address, bool(dev.is_monitored))
        self.reload_data()
        self.inventory_changed.emit()

    def _edit_device(self):
        ids = self._selected_device_ids()
        if not ids:
            return
        dlg = DeviceDialog(ids[0], self)
        if dlg.exec():
            self.reload_data()
            self.inventory_changed.emit()

    def _ping_selected(self):
        ids = self._selected_device_ids()
        if not ids:
            return
        with session_scope() as session:
            dev = session.get(Device, ids[0])
            if not dev:
                return
            host = dev.ip_address
        dlg = ToolLogDialog(f"Ping — {host}", self)
        worker = PingWorker(host, count=4)
        worker.line.connect(dlg.append)
        dlg.attach_worker(worker, worker.stop)
        self._tool_workers.append(worker)
        worker.start()
        dlg.exec()

    def _portscan_selected(self):
        ids = self._selected_device_ids()
        if not ids:
            return
        with session_scope() as session:
            dev = session.get(Device, ids[0])
            if not dev:
                return
            host = dev.ip_address
        cfg = get_config()
        port_spec = cfg.get(
            "app.port_scan_ports",
            ",".join(str(p) for p in DEFAULT_PORTS),
        )
        ok, msg, ports = validate_port_range(str(port_spec))
        if not ok:
            ports = list(DEFAULT_PORTS)
        timeout = float(cfg.get("app.port_scan_timeout", 0.8))
        dlg = ToolLogDialog(f"Port Scan — {host}", self)
        worker = PortScanWorker(host, ports, timeout=timeout)
        worker.line.connect(dlg.append)

        def _persist(open_ports: list):
            if not open_ports:
                return
            import json
            with session_scope() as session:
                d = session.get(Device, ids[0])
                if d:
                    # Merge with existing
                    existing = set(parse_open_ports(d.open_ports))
                    existing.update(open_ports)
                    d.open_ports = json.dumps(sorted(existing))
            self.reload_data()
            self.inventory_changed.emit()

        worker.finished_ok.connect(_persist)
        dlg.attach_worker(worker, worker.stop)
        self._tool_workers.append(worker)
        worker.start()
        dlg.exec()

    def _export_menu(self):
        path, selected = QFileDialog.getSaveFileName(
            self,
            "Export devices",
            "devices.csv",
            "CSV (*.csv);;JSON (*.json);;HTML (*.html)",
        )
        if not path:
            return
        fmt = "csv"
        if path.lower().endswith(".json") or "JSON" in selected:
            fmt = "json"
        elif path.lower().endswith(".html") or "HTML" in selected:
            fmt = "html"
        self.export_devices(fmt, path)

    def export_devices(self, fmt: str, path: Optional[str] = None):
        if path is None:
            filters = {
                "csv": "CSV (*.csv)",
                "json": "JSON (*.json)",
                "html": "HTML (*.html)",
            }
            path, _ = QFileDialog.getSaveFileName(
                self, f"Export as {fmt.upper()}", f"devices.{fmt}", filters.get(fmt, "All (*)")
            )
            if not path:
                return
        rows = []
        with session_scope() as session:
            for d in session.query(Device).order_by(Device.ip_address).all():
                rows.append({
                    "ip_address": d.ip_address,
                    "hostname": d.hostname or "",
                    "mac_address": d.mac_address or "",
                    "vendor": d.vendor or "",
                    "device_type": d.device_type or "",
                    "online": d.online,
                    "latency_ms": d.latency_ms,
                    "open_ports": format_open_ports(d.open_ports, sep="|"),
                    "notes": d.notes or "",
                    "tags": d.tags or "",
                    "is_monitored": d.is_monitored,
                    "first_seen": d.first_seen,
                    "last_seen": d.last_seen,
                })
        if fmt == "csv":
            export_csv(path, rows)
        elif fmt == "json":
            export_json(path, rows)
        else:
            export_html(path, "NetOps Commander — Devices", rows)
        QMessageBox.information(self, "Export", f"Exported {len(rows)} devices to:\n{path}")
