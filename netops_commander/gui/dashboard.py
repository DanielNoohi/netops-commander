"""Dashboard widget."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QGroupBox, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt, QTimer
from ..utils.network import get_active_interface, get_public_ip, get_dns_servers, get_local_subnet
from ..utils.logger import get_logger

log = get_logger(__name__)


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
            h.addWidget(w)
        grp.setLayout(h)
        self.layout().addWidget(grp)

    def _build_alerts_table(self):
        grp = QGroupBox("Recent Alerts")
        v = QVBoxLayout()
        self.alerts_table = QTableWidget(0, 3)
        self.alerts_table.setHorizontalHeaderLabels(["Time", "Severity", "Message"])
        self.alerts_table.horizontalHeader().setStretchLastSection(True)
        v.addWidget(self.alerts_table)
        grp.setLayout(v)
        self.layout().addWidget(grp)

    def _refresh_network(self):
        info = get_active_interface()
        self.lbl_iface.setText(f"Interface: {info.get('name', 'Unknown')}")
        self.lbl_local_ip.setText(f"Local IP: {info.get('ip', 'N/A')}")
        self.lbl_subnet.setText(f"Subnet: {get_local_subnet()}")
        self.lbl_gateway.setText(f"Gateway: {info.get('gateway', 'N/A')}")
        self.lbl_dns.setText(f"DNS: {', '.join(get_dns_servers())}")
        pub = get_public_ip(timeout=3)
        self.lbl_public_ip.setText(f"Public IP: {pub or 'N/A'}")

    def update_stats(self, online: int, offline: int, total: int, recent_scans: int):
        self.lbl_online.setText(f"Online: {online}")
        self.lbl_offline.setText(f"Offline: {offline}")
        self.lbl_total.setText(f"Total: {total}")
        self.lbl_scans.setText(f"Recent: {recent_scans}")

    def add_alert(self, timestamp: str, severity: str, message: str):
        row = self.alerts_table.rowCount()
        self.alerts_table.insertRow(row)
        self.alerts_table.setItem(row, 0, QTableWidgetItem(timestamp))
        self.alerts_table.setItem(row, 1, QTableWidgetItem(severity))
        self.alerts_table.setItem(row, 2, QTableWidgetItem(message))

    def _start_refresh(self):
        self._refresh_network()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._refresh_network)
        self.timer.start(10000)