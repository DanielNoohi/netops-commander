"""Preferences dialog for key scan / monitor settings."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QApplication,
    QDialog, QVBoxLayout, QFormLayout, QDialogButtonBox,
    QDoubleSpinBox, QSpinBox, QCheckBox, QComboBox, QLabel, QMessageBox,
)

from ..config import get_config
from ..constants import MONITOR_INTERVALS
from .themes import apply_theme


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumWidth(420)
        cfg = get_config()

        form = QFormLayout()
        self.theme = QComboBox()
        self.theme.addItems(["dark", "light"])
        self.theme.setCurrentText(str(cfg.get("app.theme", "dark")))

        self.scan_timeout = QDoubleSpinBox()
        self.scan_timeout.setRange(0.5, 10.0)
        self.scan_timeout.setSingleStep(0.5)
        self.scan_timeout.setValue(float(cfg.get("app.scan_timeout", 2.0)))

        self.scan_concurrency = QSpinBox()
        self.scan_concurrency.setRange(4, 256)
        self.scan_concurrency.setValue(int(cfg.get("app.scan_concurrency", 32)))

        self.require_arp = QCheckBox("Require ARP / L2 confirmation (recommended)")
        self.require_arp.setChecked(bool(cfg.get("app.require_arp", True)))

        self.monitor_interval = QComboBox()
        for sec in MONITOR_INTERVALS:
            self.monitor_interval.addItem(f"{sec}s", sec)
        current_iv = int(cfg.get("app.monitoring_interval", 60))
        idx = self.monitor_interval.findData(current_iv)
        self.monitor_interval.setCurrentIndex(max(0, idx))

        self.monitor_max = QSpinBox()
        self.monitor_max.setRange(1, 200)
        self.monitor_max.setValue(int(cfg.get("app.monitor_max_devices", 25)))

        self.retention = QSpinBox()
        self.retention.setRange(0, 3650)
        self.retention.setSuffix(" days")
        self.retention.setSpecialValueText("Keep forever")
        self.retention.setValue(int(cfg.get("app.history_retention_days", 30)))

        form.addRow("Theme", self.theme)
        form.addRow("Scan timeout (s)", self.scan_timeout)
        form.addRow("Scan concurrency", self.scan_concurrency)
        form.addRow(self.require_arp)
        form.addRow("Monitor interval", self.monitor_interval)
        form.addRow("Max monitored devices", self.monitor_max)
        form.addRow("History retention", self.retention)

        hint = QLabel(
            "Changes apply to the next scan / monitor cycle. "
            "Retention cleanup runs on startup."
        )
        hint.setWordWrap(True)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(hint)
        layout.addWidget(buttons)

    def _save(self):
        cfg = get_config()
        theme = self.theme.currentText()
        cfg.set("app.theme", theme)
        cfg.set("app.scan_timeout", float(self.scan_timeout.value()))
        cfg.set("app.scan_concurrency", int(self.scan_concurrency.value()))
        cfg.set("app.require_arp", bool(self.require_arp.isChecked()))
        cfg.set("app.monitoring_interval", int(self.monitor_interval.currentData()))
        cfg.set("app.monitor_max_devices", int(self.monitor_max.value()))
        cfg.set("app.history_retention_days", int(self.retention.value()))
        app = QApplication.instance()
        if app is not None:
            apply_theme(app, theme)
        QMessageBox.information(self, "Settings", "Settings saved.")
        self.accept()
