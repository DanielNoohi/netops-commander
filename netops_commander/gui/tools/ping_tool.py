"""Ping tool: continuous ICMP ping with live output and stop control."""
import asyncio

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton,
    QTextEdit, QLabel,
)

from ...core.discovery import async_ping
from ...utils.validators import is_valid_host


class PingToolWorker(QThread):
    """Continuous ping loop in a worker thread (non-blocking UI)."""

    line = Signal(str)
    finished_ok = Signal()

    def __init__(self, host: str, timeout: float = 2.0, interval: float = 1.0):
        super().__init__()
        self.host = host
        self.timeout = timeout
        self.interval = interval
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._run(loop))
        finally:
            loop.close()
            self.finished_ok.emit()

    async def _run(self, loop) -> None:
        sent = 0
        received = 0
        latencies = []
        self.line.emit(f"Pinging {self.host} (Ctrl+Stop to end)...")
        while not self._stop:
            sent += 1
            online, latency = await async_ping(self.host, timeout=self.timeout)
            if online:
                received += 1
                latencies.append(latency or 0.0)
                if latency is not None:
                    self.line.emit(f"  reply from {self.host}: time={latency:.1f} ms")
                else:
                    self.line.emit(f"  reply from {self.host}")
            else:
                self.line.emit(f"  request timed out ({sent})")
            if not self._stop:
                await asyncio.sleep(self.interval)
        loss = 100.0 * (sent - received) / sent if sent else 0.0
        avg = (sum(latencies) / len(latencies)) if latencies else None
        avg_s = f"{avg:.1f} ms" if avg is not None else "n/a"
        self.line.emit(
            f"Stopped. sent={sent} recv={received} loss={loss:.0f}% avg={avg_s}"
        )


class PingToolWidget(QDialog):
    """Standalone ping tool opened from the Tools menu."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ping Tool")
        self.setMinimumSize(520, 380)
        self._worker: PingToolWorker | None = None

        self.host = QLineEdit()
        self.host.setPlaceholderText("Target IP / hostname")
        self.host.returnPressed.connect(self._start)

        self.start_btn = QPushButton("Start Ping")
        self.start_btn.clicked.connect(self._start)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop)

        self.log = QTextEdit()
        self.log.setReadOnly(True)

        tb = QHBoxLayout()
        tb.addWidget(QLabel("Host:"))
        tb.addWidget(self.host, 1)
        tb.addWidget(self.start_btn)
        tb.addWidget(self.stop_btn)

        layout = QVBoxLayout()
        layout.addLayout(tb)
        layout.addWidget(self.log)
        self.setLayout(layout)

    def _start(self):
        host = self.host.text().strip()
        if not host:
            self.log.append("Enter a target IP or hostname first.")
            return
        if not is_valid_host(host):
            self.log.append(f"Invalid host: {host!r}")
            return
        if self._worker and self._worker.isRunning():
            self.log.append("Ping already running — press Stop first.")
            return
        self.log.clear()
        self._worker = PingToolWorker(host)
        self._worker.line.connect(self.log.append)
        self._worker.finished_ok.connect(self._on_finished)
        self._worker.start()
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

    def _stop(self):
        if self._worker and self._worker.isRunning():
            self._worker.stop()

    def _on_finished(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def closeEvent(self, event):
        """Ensure the worker thread is stopped before closing the window."""
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(2000)
        event.accept()
