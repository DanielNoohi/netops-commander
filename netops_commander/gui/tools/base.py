"""Shared helpers for Tools menu dialogs."""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QLabel,
)


class LineWorker(QThread):
    """Generic worker that emits text lines then finishes."""

    line = Signal(str)
    finished_ok = Signal()

    def __init__(self, runner: Callable[["LineWorker"], None]):
        super().__init__()
        self._runner = runner
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    @property
    def stopped(self) -> bool:
        return self._stop

    def run(self) -> None:
        try:
            self._runner(self)
        finally:
            self.finished_ok.emit()


class ToolDialog(QDialog):
    """Dialog with a log pane + Run/Stop/Close controls."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(560, 420)
        self._worker: Optional[LineWorker] = None

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.run_btn = QPushButton("Run")
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setEnabled(False)
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        self.stop_btn.clicked.connect(self._stop)

        self.header = QVBoxLayout()
        btn_row = QHBoxLayout()
        btn_row.addWidget(self.run_btn)
        btn_row.addWidget(self.stop_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(self.close_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(self.header)
        layout.addWidget(self.log, 1)
        layout.addLayout(btn_row)

    def add_header_row(self, label: str, widget) -> None:
        row = QHBoxLayout()
        row.addWidget(QLabel(label))
        row.addWidget(widget, 1)
        self.header.addLayout(row)

    def start_worker(self, runner: Callable[[LineWorker], None]) -> None:
        if self._worker and self._worker.isRunning():
            self.log.append("Already running — press Stop first.")
            return
        self.log.clear()
        self._worker = LineWorker(runner)
        self._worker.line.connect(self.log.append)
        self._worker.finished_ok.connect(self._on_finished)
        self.run_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._worker.start()

    def _stop(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.stop()

    def _on_finished(self) -> None:
        self.run_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

    def closeEvent(self, event):
        if self._worker and self._worker.isRunning():
            self._worker.stop()
            self._worker.wait(3000)
        event.accept()
