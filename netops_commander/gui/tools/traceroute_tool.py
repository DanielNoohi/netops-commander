"""Traceroute tool dialog."""
from __future__ import annotations

from PySide6.QtWidgets import QLineEdit, QSpinBox

from ...utils.traceroute import run_traceroute
from ...utils.validators import is_valid_host
from .base import ToolDialog, LineWorker


class TracerouteToolDialog(ToolDialog):
    def __init__(self, parent=None, initial_host: str = ""):
        super().__init__("Traceroute", parent)
        self.host = QLineEdit(initial_host)
        self.host.setPlaceholderText("Target IP / hostname")
        self.hops = QSpinBox()
        self.hops.setRange(1, 64)
        self.hops.setValue(30)
        self.add_header_row("Host:", self.host)
        self.add_header_row("Max hops:", self.hops)
        self.run_btn.clicked.connect(self._run)
        self.host.returnPressed.connect(self._run)

    def _run(self):
        host = self.host.text().strip()
        if not is_valid_host(host):
            self.log.append(f"Invalid host: {host!r}")
            return

        max_hops = self.hops.value()

        def runner(worker: LineWorker):
            worker.line.emit(f"Tracing route to {host} (max {max_hops} hops)...")
            code = run_traceroute(
                host,
                max_hops=max_hops,
                line_callback=lambda s: worker.line.emit(s),
                should_stop=lambda: worker.stopped,
            )
            worker.line.emit(f"Done (exit {code}).")

        self.start_worker(runner)
