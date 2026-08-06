"""Device detail / edit dialog with latency history sparkline."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit,
    QTextEdit, QDialogButtonBox, QHBoxLayout, QPushButton,
)

from ..database.database import session_scope
from ..database.models import Device, MonitorResult
from .widgets.sparkline import LatencySparkline


class DeviceDialog(QDialog):
    def __init__(self, device_id: int, parent=None):
        super().__init__(parent)
        self.device_id = device_id
        self.setWindowTitle("Device Details")
        self.setMinimumSize(520, 520)
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.lbl_ip = QLabel("IP: ...")
        self.lbl_vendor = QLabel("Vendor: ...")
        self.lbl_mac = QLabel("MAC: ...")
        self.lbl_type = QLabel("Type: ...")
        self.edit_hostname = QLineEdit()
        self.edit_tags = QLineEdit()
        self.edit_notes = QTextEdit()
        self.sparkline = LatencySparkline(max_points=40)
        self.lbl_history = QLabel("Recent monitor latency")

        layout.addWidget(self.lbl_ip)
        layout.addWidget(self.lbl_vendor)
        layout.addWidget(self.lbl_mac)
        layout.addWidget(self.lbl_type)
        layout.addWidget(QLabel("Hostname"))
        layout.addWidget(self.edit_hostname)
        layout.addWidget(QLabel("Tags (comma separated)"))
        layout.addWidget(self.edit_tags)
        layout.addWidget(QLabel("Notes"))
        layout.addWidget(self.edit_notes)
        layout.addWidget(self.lbl_history)
        layout.addWidget(self.sparkline)

        launch_row = QHBoxLayout()
        for label, slot in (
            ("HTTP", self._launch_http),
            ("HTTPS", self._launch_https),
            ("RDP", self._launch_rdp),
            ("SSH", self._launch_ssh),
        ):
            btn = QPushButton(label)
            btn.clicked.connect(slot)
            launch_row.addWidget(btn)
        launch_row.addStretch(1)
        layout.addLayout(launch_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._ip = ""
        self._load_device()

    def _load_device(self):
        """Load device data from the database."""
        with session_scope() as session:
            device = session.get(Device, self.device_id)
            if not device:
                self.lbl_ip.setText("IP: (not found)")
                return
            self._ip = device.ip_address
            self.lbl_ip.setText(f"IP: {device.ip_address}")
            self.lbl_vendor.setText(f"Vendor: {device.vendor or 'Unknown'}")
            self.lbl_mac.setText(f"MAC: {device.mac_address or 'Unknown'}")
            self.lbl_type.setText(f"Type: {device.device_type or 'Unknown'}")
            self.edit_hostname.setText(device.hostname or "")
            self.edit_tags.setText(device.tags or "")
            self.edit_notes.setPlainText(device.notes or "")

            rows = (
                session.query(MonitorResult)
                .filter(MonitorResult.device_id == self.device_id)
                .order_by(MonitorResult.timestamp.desc())
                .limit(40)
                .all()
            )
            samples = []
            for r in reversed(rows):
                if r.online and r.latency_ms is not None:
                    samples.append(float(r.latency_ms))
                else:
                    samples.append(None)
            self.sparkline.set_samples(samples)
            if not samples:
                self.lbl_history.setText("Recent monitor latency (no samples yet)")

    def _save(self):
        """Save changes back to the database."""
        with session_scope() as session:
            device = session.get(Device, self.device_id)
            if device:
                device.hostname = self.edit_hostname.text() or None
                device.tags = self.edit_tags.text() or None
                device.notes = self.edit_notes.toPlainText() or None
        self.accept()

    def _launch_http(self):
        from ..utils.launchers import open_http
        open_http(self._ip, https=False)

    def _launch_https(self):
        from ..utils.launchers import open_http
        open_http(self._ip, https=True)

    def _launch_rdp(self):
        from ..utils.launchers import open_rdp
        open_rdp(self._ip)

    def _launch_ssh(self):
        from ..utils.launchers import open_ssh
        open_ssh(self._ip)
