"""Device detail / edit dialog."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit,
    QTextEdit, QDialogButtonBox, QMessageBox
)

from ..database.database import session_scope
from ..database.models import Device


class DeviceDialog(QDialog):
    def __init__(self, device_id: int, parent=None):
        super().__init__(parent)
        self.device_id = device_id
        self.setWindowTitle("Device Details")
        self.setMinimumSize(500, 400)
        layout = QVBoxLayout()
        self.setLayout(layout)

        self.lbl_ip = QLabel("IP: ...")
        self.lbl_vendor = QLabel("Vendor: ...")
        self.lbl_mac = QLabel("MAC: ...")
        self.lbl_type = QLabel("Type: ...")
        self.edit_hostname = QLineEdit()
        self.edit_tags = QLineEdit()
        self.edit_notes = QTextEdit()

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

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._load_device()

    def _load_device(self):
        """Load device data from the database."""
        with session_scope() as session:
            device = session.get(Device, self.device_id)
            if not device:
                self.lbl_ip.setText("IP: (not found)")
                return
            self.lbl_ip.setText(f"IP: {device.ip_address}")
            self.lbl_vendor.setText(f"Vendor: {device.vendor or 'Unknown'}")
            self.lbl_mac.setText(f"MAC: {device.mac_address or 'Unknown'}")
            self.lbl_type.setText(f"Type: {device.device_type or 'Unknown'}")
            self.edit_hostname.setText(device.hostname or "")
            self.edit_tags.setText(device.tags or "")
            self.edit_notes.setPlainText(device.notes or "")

    def _save(self):
        """Save changes back to the database."""
        with session_scope() as session:
            device = session.get(Device, self.device_id)
            if device:
                device.hostname = self.edit_hostname.text() or None
                device.tags = self.edit_tags.text() or None
                device.notes = self.edit_notes.toPlainText() or None
        self.accept()
