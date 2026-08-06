"""Theme definitions and stylesheet application."""
from __future__ import annotations

from typing import Dict

from PySide6.QtWidgets import QApplication

DARK: Dict[str, str] = {
    "bg": "#121212",
    "fg": "#e0e0e0",
    "card": "#1a1a1a",
    "accent": "#2563eb",
    "border": "#333333",
    "success": "#22c55e",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "muted": "#9ca3af",
    "input": "#1f2937",
}

LIGHT: Dict[str, str] = {
    "bg": "#f3f4f6",
    "fg": "#111827",
    "card": "#ffffff",
    "accent": "#2563eb",
    "border": "#d1d5db",
    "success": "#16a34a",
    "warning": "#d97706",
    "danger": "#dc2626",
    "muted": "#6b7280",
    "input": "#ffffff",
}


def theme_colors(name: str) -> Dict[str, str]:
    return DARK if str(name).lower() != "light" else LIGHT


def build_stylesheet(name: str) -> str:
    t = theme_colors(name)
    return f"""
    QWidget {{
        background-color: {t['bg']};
        color: {t['fg']};
        font-size: 13px;
    }}
    QMainWindow, QDialog {{
        background-color: {t['bg']};
    }}
    QGroupBox {{
        background-color: {t['card']};
        border: 1px solid {t['border']};
        border-radius: 6px;
        margin-top: 10px;
        padding: 8px;
        font-weight: bold;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 4px;
        color: {t['accent']};
    }}
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {{
        background-color: {t['input']};
        border: 1px solid {t['border']};
        border-radius: 4px;
        padding: 4px 6px;
        selection-background-color: {t['accent']};
    }}
    QPushButton {{
        background-color: {t['accent']};
        color: #ffffff;
        border: none;
        border-radius: 4px;
        padding: 6px 12px;
    }}
    QPushButton:disabled {{
        background-color: {t['border']};
        color: {t['muted']};
    }}
    QPushButton:hover {{
        background-color: {t['accent']};
    }}
    QTableWidget {{
        background-color: {t['card']};
        alternate-background-color: {t['bg']};
        gridline-color: {t['border']};
        border: 1px solid {t['border']};
    }}
    QHeaderView::section {{
        background-color: {t['input']};
        color: {t['fg']};
        border: 1px solid {t['border']};
        padding: 4px;
    }}
    QMenuBar, QMenu {{
        background-color: {t['card']};
        color: {t['fg']};
    }}
    QMenuBar::item:selected, QMenu::item:selected {{
        background-color: {t['accent']};
        color: #ffffff;
    }}
    QStatusBar {{
        background-color: {t['card']};
        color: {t['muted']};
    }}
    QProgressBar {{
        border: 1px solid {t['border']};
        border-radius: 4px;
        text-align: center;
        background-color: {t['input']};
    }}
    QProgressBar::chunk {{
        background-color: {t['accent']};
    }}
    QSplitter::handle {{
        background-color: {t['border']};
    }}
    QTabWidget::pane {{
        border: 1px solid {t['border']};
    }}
    QTabBar::tab {{
        background: {t['card']};
        color: {t['fg']};
        padding: 6px 12px;
        border: 1px solid {t['border']};
    }}
    QTabBar::tab:selected {{
        background: {t['accent']};
        color: #ffffff;
    }}
    """


def apply_theme(app: QApplication | None, name: str) -> None:
    """Apply dark/light stylesheet to the QApplication."""
    if app is None:
        app = QApplication.instance()
    if app is None:
        return
    app.setStyleSheet(build_stylesheet(name))
