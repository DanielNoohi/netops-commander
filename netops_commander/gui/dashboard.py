"""Dashboard widget."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, QTimer, QThread, Signal
from ..utils.network import get_active_interface, get_public_ip, get_dns_servers, get_local_subnet
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
        self.finished.emit(info)


class DashboardWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayout(QVBoxLayout())
        self.layout().setSpacing(10)
        self._build_network_card()
        self._build_stats_card()
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
        gl.addWidget(self.lbl_iface, 0, 0)
        gl.addWidget(self.lbl_local_ip, 0, 1)
        gl.addWidget(self.lbl_subnet, 1, 0)
        gl.addWidget(self.lbl_gateway, 1, 1)
        gl.addWidget(self.lbl_dns, 2, 0)
        gl.addWidget(self.lbl_public_ip, 2, 1)
        grp.setLayout(gl)
        self.layout().addWidget(grp)

    def _build_stats_card(self):
        grp = QGroupBox("Inventory Overview")
        h = QHBoxLayout()
        self.lbl_online = QLabel("Online: 0")
        self.lbl_offline = QLabel("Offline: 0")
        self.lbl_total = QLabel("Total: 0")
        self.lbl_scans = QLabel("Recent 0")
        for w in (self.lbl_online, self.lbl_offline, self.lbl_total, self.lbl_scans):
            w.setStyleSheet("font-size: 14px; font-weight: bold;")
            h.addWidget(w)
        grp.setLayout(h)
        self.layout().addWidget(grp)

    def _build_alerts_table(self):
        grp = QGroupBox("Recent Alerts")
        layout = QVBoxLayout()
        self.alerts_table = QTableWidget(0, 3)
        self.alerts_table.setHorizontalHeaderLabels(["Time", "Device", "Message"])
        self.alerts_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.alerts_table.setMaximumHeight(200)
        layout.addWidget(self.alerts_table)
        grp.setLayout(layout)
        self.layout().addWidget(grp)

    def _start_refresh(self):
        self._refresh_network()
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_network)
        self._timer.start(60_000)  # Every 60s instead of 10s

    def _refresh_network(self):
        """Refresh network info in background thread."""
        self._worker = NetworkInfoWorker()
        self._worker.finished.connect(self._on_network_info)
        self._worker.start()

    def _on_network_info(self, info):
        """Update UI with network info from background thread."""
        self.lbl_iface.setText(f"Interface: {info.get('name', 'Unknown')}")
        self.lbl_local_ip.setText(f"Local IP: {info.get('ip', 'Unknown')}")
        self.lbl_subnet.setText(f"Subnet: {info.get('subnet', 'Unknown')}")
        gw = info.get('gateway')
        self.lbl_gateway.setText(f"Gateway: {gw or 'Unknown'}")
        dns = info.get('dns', [])
        self.lbl_dns.setText(f"DNS: {', '.join(dns[:3]) if dns else 'Unknown'}")
        self.lbl_public_ip.setText(f"Public IP: {info.get('public_ip', 'Unknown')}")

    def update_stats(self, online: int, offline: int, total: int, scans: int = 0):
        self.lbl_online.setText(f"Online: {online}")
        self.lbl_offline.setText(f"Offline: {offline}")
        self.lbl_total.setText(f"Total: {total}")
        self.lbl_scans.setText(f"Recent {scans}")

    def add_alert(self, time_str: str, device: str, message: str):
        row = self.alerts_table.rowCount()
        self.alerts_table.insertRow(row)
        self.alerts_table.setItem(row, 0, QTableWidgetItem(time_str))
        self.alerts_table.setItem(row, 1, QTableWidgetItem(device))
        self.alerts_table.setItem(row, 2, QTableWidgetItem(message))
