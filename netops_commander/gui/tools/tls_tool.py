"""TLS certificate diagnostics dialog."""
from __future__ import annotations

from PySide6.QtWidgets import QLineEdit, QSpinBox

from ...utils.tls_check import check_tls
from ...utils.validators import is_valid_host
from .base import ToolDialog, LineWorker


class TlsToolDialog(ToolDialog):
    def __init__(self, parent=None, initial_host: str = ""):
        super().__init__("TLS Certificate Check", parent)
        self.host = QLineEdit(initial_host)
        self.host.setPlaceholderText("hostname (SNI)")
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(443)
        self.add_header_row("Host:", self.host)
        self.add_header_row("Port:", self.port)
        self.run_btn.clicked.connect(self._run)
        self.host.returnPressed.connect(self._run)
        self.stop_btn.setVisible(False)

    def _run(self):
        host = self.host.text().strip()
        if not is_valid_host(host):
            self.log.append(f"Invalid host: {host!r}")
            return
        port = self.port.value()

        def runner(worker: LineWorker):
            try:
                info = check_tls(host, port=port)
                worker.line.emit(f"TLS check {host}:{port}")
                for key in (
                    "tls_version", "cipher", "subject", "issuer",
                    "not_before", "not_after", "days_remaining", "serial",
                ):
                    worker.line.emit(f"  {key}: {info.get(key)}")
                sans = info.get("san") or []
                if sans:
                    worker.line.emit("  SAN:")
                    for s in sans[:30]:
                        worker.line.emit(f"    {s}")
                days = info.get("days_remaining")
                if days is not None and days < 30:
                    worker.line.emit(f"  WARNING: certificate expires in {days} days")
            except Exception as e:
                worker.line.emit(f"Error: {e}")

        self.start_worker(runner)
