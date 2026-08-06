"""Scan network dialog with CIDR validation and host estimate."""
from __future__ import annotations

import ipaddress

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QDialogButtonBox,
    QLineEdit, QLabel, QPushButton, QHBoxLayout, QCheckBox,
)

from ..config import get_config
from ..utils.network import get_local_subnet
from ..utils.validators import validate_cidr


class ScanDialog(QDialog):
    def __init__(self, parent=None, initial_cidr: str | None = None):
        super().__init__(parent)
        self.setWindowTitle("Scan Network")
        self.setMinimumWidth(460)
        self._cidr = ""

        self.cidr_edit = QLineEdit(initial_cidr or get_local_subnet() or "192.168.1.0/24")
        self.cidr_edit.setPlaceholderText("e.g. 192.168.1.0/24")
        self.cidr_edit.textChanged.connect(self._refresh_estimate)

        self.btn_local = QPushButton("Use local subnet")
        self.btn_local.clicked.connect(self._use_local)

        row = QHBoxLayout()
        row.addWidget(self.cidr_edit, 1)
        row.addWidget(self.btn_local)

        self.lbl_estimate = QLabel("")
        self.lbl_estimate.setWordWrap(True)
        self.require_arp = QCheckBox("Require ARP / L2 confirmation (recommended)")
        self.require_arp.setChecked(bool(get_config().get("app.require_arp", True)))

        form = QFormLayout()
        form.addRow("CIDR", row)
        form.addRow("", self.lbl_estimate)
        form.addRow(self.require_arp)

        hint = QLabel(
            "Only scan networks you own or have written permission to test. "
            "Large ranges take longer; /16 is the maximum allowed."
        )
        hint.setWordWrap(True)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)
        self._ok = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self._ok.setText("Start Scan")

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(hint)
        layout.addWidget(buttons)
        self._refresh_estimate()

    def _use_local(self):
        self.cidr_edit.setText(get_local_subnet() or "192.168.1.0/24")

    def _refresh_estimate(self):
        text = self.cidr_edit.text().strip()
        ok, msg = validate_cidr(text)
        if not ok:
            self.lbl_estimate.setText(f"⚠ {msg or 'Invalid CIDR'}")
            self._ok.setEnabled(False)
            return
        try:
            net = ipaddress.ip_network(text, strict=False)
            hosts = list(net.hosts()) or list(net)
            n = len(hosts)
            self.lbl_estimate.setText(
                f"Will probe ~{n} address(es) · prefix /{net.prefixlen}"
            )
            self._ok.setEnabled(True)
        except ValueError as e:
            self.lbl_estimate.setText(f"⚠ {e}")
            self._ok.setEnabled(False)

    def _accept(self):
        text = self.cidr_edit.text().strip()
        ok, msg = validate_cidr(text)
        if not ok:
            self.lbl_estimate.setText(f"⚠ {msg}")
            return
        # Persist ARP preference for this scan session / future scans
        get_config().set("app.require_arp", bool(self.require_arp.isChecked()))
        self._cidr = text
        self.accept()

    @property
    def cidr(self) -> str:
        return self._cidr
