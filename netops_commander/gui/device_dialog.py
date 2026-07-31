"""Device detail / edit dialog."""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit,
    QTextEdit, QDialogButtonBox
)


class DeviceDialog(QDialog):
    def __init__(self, device_id: int, parent=None):
        super().__init__(parent)
        self.device_id = device_id
        self.setWindowTitle("Device Details")
        self.setMinimumSize(500, 400)
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.lbl_ip = QLabel("IP: ...")
        self.edit_hostname = QLineEdit()
        self.edit_tags = QLineEdit()
        self.edit_notes = QTextEdit()
        layout.addWidget(self.lbl_ip)
        layout.addWidget(QLabel("Hostname"))
        layout.addWidget(self.edit_hostname)
        layout.addWidget(QLabel("Tags (comma separated)"))
        layout.addWidget(self.edit_tags)
        layout.addWidget(QLabel("Notes"))
        layout.addWidget(self.edit_notes)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)