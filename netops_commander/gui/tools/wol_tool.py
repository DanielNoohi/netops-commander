"""Wake-on-LAN tool dialog."""
from __future__ import annotations

from PySide6.QtWidgets import QLineEdit

from ...constants import WOL_BROADCAST, WOL_UDP_PORT
from ...utils.wol import send_magic_packet, is_valid_mac
from .base import ToolDialog, LineWorker


class WolToolDialog(ToolDialog):
    def __init__(self, parent=None, initial_mac: str = ""):
        super().__init__("Wake-on-LAN", parent)
        self.mac = QLineEdit(initial_mac)
        self.mac.setPlaceholderText("AA:BB:CC:DD:EE:FF")
        self.broadcast = QLineEdit(WOL_BROADCAST)
        self.add_header_row("MAC:", self.mac)
        self.add_header_row("Broadcast:", self.broadcast)
        self.run_btn.setText("Send magic packet")
        self.stop_btn.setVisible(False)
        self.run_btn.clicked.connect(self._run)
        self.mac.returnPressed.connect(self._run)

    def _run(self):
        mac = self.mac.text().strip()
        bcast = self.broadcast.text().strip() or WOL_BROADCAST
        if not is_valid_mac(mac):
            self.log.append(f"Invalid MAC: {mac!r}")
            return

        def runner(worker: LineWorker):
            ok, msg = send_magic_packet(mac, broadcast=bcast, port=WOL_UDP_PORT)
            worker.line.emit(msg if ok else f"Error: {msg}")

        self.start_worker(runner)
