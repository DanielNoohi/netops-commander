"""Simple latency sparkline (no external charting deps)."""
from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath
from PySide6.QtWidgets import QWidget


class LatencySparkline(QWidget):
    """Paint a polyline of recent latency samples (ms)."""

    def __init__(self, parent=None, max_points: int = 60):
        super().__init__(parent)
        self._samples: List[Optional[float]] = []
        self._max_points = max_points
        self.setMinimumHeight(72)
        self.setMinimumWidth(200)
        self._line = QColor("#38bdf8")
        self._fill = QColor(56, 189, 248, 40)
        self._grid = QColor("#374151")
        self._muted = QColor("#9ca3af")
        self._timeout_color = QColor("#ef4444")

    def clear(self) -> None:
        self._samples.clear()
        self.update()

    def add_sample(self, latency_ms: Optional[float]) -> None:
        """None means timeout / missed reply."""
        self._samples.append(latency_ms)
        if len(self._samples) > self._max_points:
            self._samples = self._samples[-self._max_points :]
        self.update()

    def set_samples(self, samples: List[Optional[float]]) -> None:
        self._samples = list(samples[-self._max_points :])
        self.update()

    @property
    def samples(self) -> List[Optional[float]]:
        return list(self._samples)

    def paintEvent(self, event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(8, 8, -8, -8)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))

        if not self._samples:
            painter.setPen(self._muted)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "Latency graph — start ping")
            return

        # Grid
        painter.setPen(QPen(self._grid, 1))
        for i in range(1, 4):
            y = rect.top() + rect.height() * i / 4
            painter.drawLine(rect.left(), int(y), rect.right(), int(y))

        vals = [v for v in self._samples if v is not None]
        ymax = max(vals) if vals else 1.0
        ymax = max(ymax, 1.0) * 1.15
        n = len(self._samples)
        if n < 2:
            painter.setPen(self._muted)
            last = self._samples[-1]
            label = "timeout" if last is None else f"{last:.1f} ms"
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)
            return

        path = QPainterPath()
        fill = QPainterPath()
        started = False
        for i, v in enumerate(self._samples):
            x = rect.left() + (rect.width() * i / (n - 1))
            if v is None:
                # Break the path on timeouts
                started = False
                # Mark timeout tick
                painter.setPen(QPen(self._timeout_color, 2))
                painter.drawLine(int(x), rect.top() + 4, int(x), rect.bottom() - 4)
                continue
            y = rect.bottom() - (rect.height() * (v / ymax))
            if not started:
                path.moveTo(x, y)
                fill.moveTo(x, rect.bottom())
                fill.lineTo(x, y)
                started = True
            else:
                path.lineTo(x, y)
                fill.lineTo(x, y)
        if started:
            fill.lineTo(rect.right(), rect.bottom())
            fill.closeSubpath()
            painter.fillPath(fill, self._fill)
            painter.setPen(QPen(self._line, 2))
            painter.drawPath(path)

        # Stats overlay
        last = next((v for v in reversed(self._samples) if v is not None), None)
        avg = (sum(vals) / len(vals)) if vals else None
        bits = []
        if last is not None:
            bits.append(f"last {last:.1f} ms")
        if avg is not None:
            bits.append(f"avg {avg:.1f} ms")
        bits.append(f"n={len(self._samples)}")
        painter.setPen(self._muted)
        painter.drawText(
            QRectF(rect),
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight,
            "  ·  ".join(bits),
        )
