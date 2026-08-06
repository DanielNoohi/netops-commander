"""DNS lookup tool dialog."""
from __future__ import annotations

from PySide6.QtWidgets import QLineEdit, QComboBox

from ...utils.dns_lookup import lookup_records
from ...utils.validators import is_valid_host
from .base import ToolDialog, LineWorker


class DnsToolDialog(ToolDialog):
    def __init__(self, parent=None, initial_host: str = ""):
        super().__init__("DNS Lookup", parent)
        self.host = QLineEdit(initial_host)
        self.host.setPlaceholderText("hostname or IP (for PTR)")
        self.rtype = QComboBox()
        self.rtype.addItems(["A", "AAAA", "PTR", "MX", "TXT", "NS", "CNAME", "SOA"])
        self.add_header_row("Name:", self.host)
        self.add_header_row("Type:", self.rtype)
        self.run_btn.clicked.connect(self._run)
        self.host.returnPressed.connect(self._run)

    def _run(self):
        name = self.host.text().strip()
        rtype = self.rtype.currentText()
        if not name:
            self.log.append("Enter a name or IP.")
            return
        if rtype != "PTR" and not is_valid_host(name):
            self.log.append(f"Invalid host: {name!r}")
            return

        def runner(worker: LineWorker):
            try:
                source, lines = lookup_records(name, rtype)
                worker.line.emit(f"Lookup {rtype} {name} via {source}")
                for ln in lines:
                    if worker.stopped:
                        break
                    worker.line.emit(ln)
            except Exception as e:
                worker.line.emit(f"Error: {e}")

        self.start_worker(runner)
