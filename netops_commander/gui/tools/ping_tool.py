"""Ping tool UI placeholder."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTextEdit
from ...utils.logger import get_logger

log = get_logger(__name__)

class PingToolWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setLayout(QVBoxLayout())
        self.host = QLineEdit()
        self.host.setPlaceholderText("Target IP / hostname")
        self.start_btn = QPushButton("Start Ping")
        self.start_btn.clicked.connect(self._start)
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.clicked.connect(self._stop)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        tb = QHBoxLayout()
        tb.addWidget(self.host)
        tb.addWidget(self.start_btn)
        tb.addWidget(self.stop_btn)
        self.layout().addLayout(tb)
        self.layout().addWidget(self.log)

    def _start(self):
        self.log.append(f"Pinging {self.host.text()}...")

    def _stop(self):
        self.log.append("Stopped.")
