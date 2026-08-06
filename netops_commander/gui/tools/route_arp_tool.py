"""Route table / ARP table viewer dialog."""
from __future__ import annotations

from PySide6.QtWidgets import QComboBox

from ...utils.route_arp import get_route_table, get_arp_table
from .base import ToolDialog, LineWorker


class RouteArpToolDialog(ToolDialog):
    def __init__(self, parent=None):
        super().__init__("Route / ARP Tables", parent)
        self.kind = QComboBox()
        self.kind.addItems(["Route table", "ARP / neighbor table"])
        self.add_header_row("View:", self.kind)
        self.run_btn.setText("Refresh")
        self.stop_btn.setVisible(False)
        self.run_btn.clicked.connect(self._run)

    def _run(self):
        kind = self.kind.currentText()

        def runner(worker: LineWorker):
            worker.line.emit(f"Loading {kind}...")
            try:
                text = get_route_table() if kind.startswith("Route") else get_arp_table()
                for ln in text.splitlines():
                    if worker.stopped:
                        break
                    worker.line.emit(ln)
            except Exception as e:
                worker.line.emit(f"Error: {e}")

        self.start_worker(runner)
