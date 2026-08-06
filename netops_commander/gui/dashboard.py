"""Dashboard widget with live stats, Wi-Fi, history, and alerts."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton,
)
from PySide6.QtCore import QTimer, QThread, Signal, Qt
from PySide6.QtGui import QColor

from ..database.database import session_scope
from ..database.models import Alert, Device, MonitorResult, ScanHistory
from ..utils.network import get_active_interface, get_public_ip, get_dns_servers, get_local_subnet
from ..utils.wifi import get_wifi_info, format_wifi_summary
from ..utils.logger import get_logger

log = get_logger(__name__)


class NetworkInfoWorker(QThread):
    """Fetch network info in background to avoid UI freeze."""
    finished = Signal(dict)

    def run(self):
        info = get_active_interface()
        info["public_ip"] = get_public_ip(timeout=3)
        info["dns"] = get_dns_servers()
        info["subnet"] = get_local_subnet()
        info["wifi"] = format_wifi_summary(get_wifi_info())
        self.finished.emit(info)


class DashboardWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayout(QVBoxLayout())
        self.layout().setSpacing(10)
        self._build_network_card()
        self._build_stats_card()
        self._build_activity_card()
        self._build_alerts_table()
        self._start_refresh()

    def _build_network_card(self):
        grp = QGroupBox("Network Interface")
        gl = QGridLayout()
        self.lbl_iface = QLabel("Interface: ...")
        self.lbl_local_ip = QLabel("Local IP: ...")
        self.lbl_subnet = QLabel("Subnet: ...")
        self.lbl_gateway = QLabel("Gateway: ...")
        self.lbl_dns = QLabel("DNS: ...")
        self.lbl_public_ip = QLabel("Public IP: ...")
        self.lbl_wifi = QLabel("Wi-Fi: ...")
        gl.addWidget(self.lbl_iface, 0, 0)
        gl.addWidget(self.lbl_local_ip, 0, 1)
        gl.addWidget(self.lbl_subnet, 1, 0)
        gl.addWidget(self.lbl_gateway, 1, 1)
        gl.addWidget(self.lbl_dns, 2, 0)
        gl.addWidget(self.lbl_public_ip, 2, 1)
        gl.addWidget(self.lbl_wifi, 3, 0, 1, 2)
        grp.setLayout(gl)
        self.layout().addWidget(grp)

    def _build_stats_card(self):
        grp = QGroupBox("Inventory Overview")
        h = QHBoxLayout()
        self.lbl_online = QLabel("Online: 0")
        self.lbl_offline = QLabel("Offline: 0")
        self.lbl_total = QLabel("Total: 0")
        self.lbl_scans = QLabel("Scans: 0")
        self.lbl_monitored = QLabel("Monitored: 0")
        for w in (
            self.lbl_online, self.lbl_offline, self.lbl_total,
            self.lbl_scans, self.lbl_monitored,
        ):
            w.setStyleSheet("font-size: 13px; font-weight: bold;")
            h.addWidget(w)
        grp.setLayout(h)
        self.layout().addWidget(grp)

    def _build_activity_card(self):
        grp = QGroupBox("Recent Activity")
        layout = QVBoxLayout()
        self.activity_table = QTableWidget(0, 3)
        self.activity_table.setHorizontalHeaderLabels(["Time", "Kind", "Detail"])
        self.activity_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.activity_table.setMaximumHeight(140)
        self.activity_table.setAlternatingRowColors(True)
        layout.addWidget(self.activity_table)
        grp.setLayout(layout)
        self.layout().addWidget(grp)

    def _build_alerts_table(self):
        grp = QGroupBox("Recent Alerts")
        layout = QVBoxLayout()
        self.alerts_table = QTableWidget(0, 4)
        self.alerts_table.setHorizontalHeaderLabels(["Time", "Severity", "Type", "Message"])
        self.alerts_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.alerts_table.setMaximumHeight(200)
        self.alerts_table.setAlternatingRowColors(True)
        self.alerts_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        btn_row = QHBoxLayout()
        self.btn_ack = QPushButton("Acknowledge selected")
        self.btn_ack.clicked.connect(self._acknowledge_selected)
        self.btn_ack_all = QPushButton("Acknowledge all")
        self.btn_ack_all.clicked.connect(self._acknowledge_all)
        btn_row.addWidget(self.btn_ack)
        btn_row.addWidget(self.btn_ack_all)
        btn_row.addStretch(1)
        layout.addWidget(self.alerts_table)
        layout.addLayout(btn_row)
        grp.setLayout(layout)
        self.layout().addWidget(grp)

    def _start_refresh(self):
        self._refresh_network()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_network)
        self._timer.start(60_000)

    def _refresh_network(self):
        self._worker = NetworkInfoWorker()
        self._worker.finished.connect(self._on_network_info)
        self._worker.start()

    def _on_network_info(self, info):
        self.lbl_iface.setText(f"Interface: {info.get('name', 'Unknown')}")
        self.lbl_local_ip.setText(f"Local IP: {info.get('ip', 'Unknown')}")
        self.lbl_subnet.setText(f"Subnet: {info.get('subnet', 'Unknown')}")
        gw = info.get("gateway")
        self.lbl_gateway.setText(f"Gateway: {gw or 'Unknown'}")
        dns = info.get("dns", [])
        self.lbl_dns.setText(f"DNS: {', '.join(dns[:3]) if dns else 'Unknown'}")
        self.lbl_public_ip.setText(f"Public IP: {info.get('public_ip', 'Unknown')}")
        self.lbl_wifi.setText(f"Wi-Fi: {info.get('wifi', 'N/A')}")

    def update_stats(
        self,
        online: int,
        offline: int,
        total: int,
        scans: int = 0,
        monitored: int = 0,
    ):
        self.lbl_online.setText(f"Online: {online}")
        self.lbl_offline.setText(f"Offline: {offline}")
        self.lbl_total.setText(f"Total: {total}")
        self.lbl_scans.setText(f"Scans: {scans}")
        self.lbl_monitored.setText(f"Monitored: {monitored}")

    def reload_activity(self, limit: int = 8):
        """Show recent scan history + monitor samples."""
        try:
            rows: list[tuple] = []
            with session_scope() as session:
                for sh in (
                    session.query(ScanHistory)
                    .order_by(ScanHistory.timestamp.desc())
                    .limit(limit)
                    .all()
                ):
                    ip = ""
                    if sh.device_id:
                        dev = session.get(Device, sh.device_id)
                        ip = dev.ip_address if dev else ""
                    ts = sh.timestamp.strftime("%H:%M:%S") if sh.timestamp else ""
                    detail = f"{ip} {sh.scan_type} {'up' if sh.online else 'down'}"
                    if sh.latency_ms is not None:
                        detail += f" {sh.latency_ms:.0f}ms"
                    rows.append((ts, "scan", detail))
                for mr in (
                    session.query(MonitorResult)
                    .order_by(MonitorResult.timestamp.desc())
                    .limit(limit)
                    .all()
                ):
                    ip = ""
                    if mr.device_id:
                        dev = session.get(Device, mr.device_id)
                        ip = dev.ip_address if dev else ""
                    ts = mr.timestamp.strftime("%H:%M:%S") if mr.timestamp else ""
                    lat = f"{mr.latency_ms:.0f}ms" if mr.latency_ms is not None else "—"
                    detail = f"{ip} {'up' if mr.online else 'down'} {lat}"
                    rows.append((ts, "monitor", detail))
            # Keep freshest-looking order as listed (already desc per source)
            rows = rows[:limit]
            self.activity_table.setRowCount(len(rows))
            for i, (ts, kind, detail) in enumerate(rows):
                self.activity_table.setItem(i, 0, QTableWidgetItem(ts))
                self.activity_table.setItem(i, 1, QTableWidgetItem(kind))
                self.activity_table.setItem(i, 2, QTableWidgetItem(detail))
        except Exception as e:
            log.debug("reload_activity error: %s", e)

    def reload_alerts(self, limit: int = 20):
        """Load recent unacknowledged alerts into the table."""
        try:
            with session_scope() as session:
                rows = (
                    session.query(Alert)
                    .filter(Alert.acknowledged.is_(False))
                    .order_by(Alert.timestamp.desc())
                    .limit(limit)
                    .all()
                )
                color_map = {
                    "critical": QColor("#ef4444"),
                    "warning": QColor("#f59e0b"),
                    "info": QColor("#22c55e"),
                }
                self.alerts_table.setRowCount(len(rows))
                for i, a in enumerate(rows):
                    ts = a.timestamp.strftime("%Y-%m-%d %H:%M") if a.timestamp else ""
                    severity = (a.severity or "info").lower()
                    alert_type = a.alert_type or ""
                    message = a.message or ""
                    time_item = QTableWidgetItem(ts)
                    time_item.setData(Qt.ItemDataRole.UserRole, a.id)
                    self.alerts_table.setItem(i, 0, time_item)
                    sev_item = QTableWidgetItem(severity)
                    if severity in color_map:
                        sev_item.setForeground(color_map[severity])
                    self.alerts_table.setItem(i, 1, sev_item)
                    self.alerts_table.setItem(i, 2, QTableWidgetItem(alert_type))
                    self.alerts_table.setItem(i, 3, QTableWidgetItem(message))
        except Exception as e:
            log.debug(f"reload_alerts error: {e}")

    def _selected_alert_ids(self) -> list[int]:
        ids: list[int] = []
        for idx in self.alerts_table.selectionModel().selectedRows():
            item = self.alerts_table.item(idx.row(), 0)
            if item is None:
                continue
            alert_id = item.data(Qt.ItemDataRole.UserRole)
            if alert_id is not None:
                ids.append(int(alert_id))
        return ids

    def _acknowledge_selected(self):
        ids = self._selected_alert_ids()
        if not ids:
            return
        with session_scope() as session:
            for alert_id in ids:
                alert = session.get(Alert, alert_id)
                if alert:
                    alert.acknowledged = True
        self.reload_alerts()

    def _acknowledge_all(self):
        with session_scope() as session:
            session.query(Alert).filter(Alert.acknowledged.is_(False)).update(
                {Alert.acknowledged: True},
                synchronize_session=False,
            )
        self.reload_alerts()

    def add_alert_from_db(self):
        """Convenience: reload alerts after a new alert is created."""
        self.reload_alerts()
        self.reload_activity()
