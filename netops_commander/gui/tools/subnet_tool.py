"""Subnet calculator dialog."""
from __future__ import annotations

from PySide6.QtWidgets import QLineEdit

from ...utils.subnet import describe_network
from .base import ToolDialog, LineWorker


class SubnetToolDialog(ToolDialog):
    def __init__(self, parent=None, initial_cidr: str = ""):
        super().__init__("Subnet Calculator", parent)
        self.cidr = QLineEdit(initial_cidr)
        self.cidr.setPlaceholderText("e.g. 192.168.1.0/24 or 10.0.0.5/28")
        self.add_header_row("CIDR:", self.cidr)
        self.run_btn.setText("Calculate")
        self.stop_btn.setVisible(False)
        self.run_btn.clicked.connect(self._run)
        self.cidr.returnPressed.connect(self._run)

    def _run(self):
        value = self.cidr.text().strip()
        if not value:
            self.log.append("Enter a CIDR / prefix.")
            return

        def runner(worker: LineWorker):
            try:
                info = describe_network(value)
                worker.line.emit(f"Network: {info['cidr']}")
                for key in (
                    "network", "netmask", "wildcard", "broadcast", "prefixlen",
                    "num_addresses", "usable_hosts", "first_usable", "last_usable",
                    "is_private", "version",
                ):
                    worker.line.emit(f"  {key}: {info.get(key)}")
            except Exception as e:
                worker.line.emit(f"Error: {e}")

        self.start_worker(runner)
