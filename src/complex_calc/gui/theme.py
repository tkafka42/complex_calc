"""Own visual style (light and dark), independent of any handheld design."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication


@dataclass(frozen=True)
class Palette:
    background: str
    surface: str
    surface_alt: str
    border: str
    text: str
    muted: str
    accent: str
    accent_text: str
    error: str
    result: str


LIGHT = Palette(
    background="#f6f7f9",
    surface="#ffffff",
    surface_alt="#eef2f6",
    border="#d5dbe3",
    text="#1c2430",
    muted="#667085",
    accent="#2563eb",
    accent_text="#ffffff",
    error="#c2410c",
    result="#0f5132",
)

DARK = Palette(
    background="#14171c",
    surface="#1c2027",
    surface_alt="#242a33",
    border="#323a46",
    text="#e6e9ef",
    muted="#98a2b3",
    accent="#5b8def",
    accent_text="#0b1020",
    error="#fb923c",
    result="#86efac",
)


_active: Palette | None = None


def current_palette() -> Palette:
    """The palette of the last applied stylesheet (or the system's light/dark scheme)."""
    if _active is not None:
        return _active
    hints = QGuiApplication.styleHints()
    try:
        if hints.colorScheme() == Qt.ColorScheme.Dark:
            return DARK
    except AttributeError:  # Qt < 6.5
        pass
    return LIGHT


def stylesheet(p: Palette) -> str:
    global _active
    _active = p
    return f"""
    QMainWindow, QDialog, QWidget#Page {{ background: {p.background}; color: {p.text}; }}
    QWidget {{ color: {p.text}; font-size: 11pt; }}
    QMenuBar {{ background: {p.surface}; color: {p.text}; border-bottom: 1px solid {p.border}; }}
    QMenuBar::item {{ background: transparent; padding: 4px 10px; }}
    QMenuBar::item:selected {{ background: {p.surface_alt}; border-radius: 4px; }}
    QTabWidget::pane {{ border: none; }}
    QTabBar::tab {{
        background: transparent; color: {p.muted}; padding: 8px 18px; border: none;
        border-bottom: 2px solid transparent; font-weight: 600;
    }}
    QTabBar::tab:selected {{ color: {p.text}; border-bottom: 2px solid {p.accent}; }}
    QScrollArea {{ border: none; background: {p.background}; }}
    QScrollArea > QWidget > QWidget#HistoryBox {{ background: {p.surface}; }}
    QFrame#HistoryItem {{
        background: transparent; border: none; border-bottom: 1px solid {p.border};
    }}
    QWidget#HistoryBox {{ background: {p.surface}; border: 1px solid {p.border}; border-radius: 10px; }}
    QLabel#HelpLine {{ color: {p.muted}; font-family: monospace; font-size: 9.5pt; padding: 0 4px; }}
    QLabel#Bracket {{ color: {p.result}; }}
    QTabBar::tab:first {{ margin-left: 8px; }}
    QLabel#InputText {{ color: {p.text}; font-family: monospace; }}
    QLabel#ResultText {{ color: {p.result}; font-family: monospace; font-weight: 600; }}
    QLabel#ErrorText {{ color: {p.error}; font-family: monospace; }}
    QLabel#TableLabel {{ color: {p.muted}; font-family: monospace; }}
    QLabel#TableValue {{ color: {p.result}; font-family: monospace; font-weight: 600; }}
    QLabel#Hint {{ color: {p.muted}; font-size: 9pt; }}
    QLabel:hover#InputText, QLabel:hover#ResultText, QLabel:hover#TableValue {{
        background: {p.surface_alt}; border-radius: 4px;
    }}
    QLineEdit {{
        background: {p.surface}; border: 1px solid {p.border}; border-radius: 8px;
        padding: 8px 10px; font-family: monospace; font-size: 13pt;
        selection-background-color: {p.accent}; selection-color: {p.accent_text};
    }}
    QLineEdit:focus {{ border: 1px solid {p.accent}; }}
    QLineEdit:disabled {{ color: {p.muted}; background: {p.surface_alt}; }}
    QPushButton {{
        background: {p.surface_alt}; border: 1px solid {p.border}; border-radius: 7px;
        padding: 5px 10px; min-width: 28px;
    }}
    QPushButton:hover {{ border-color: {p.accent}; }}
    QPushButton#Primary {{
        background: {p.accent}; color: {p.accent_text}; border: none; font-weight: 700; padding: 7px 16px;
    }}
    QPushButton#Symbol {{ font-size: 11pt; padding: 3px 2px; min-width: 22px; }}
    QMenu {{ background: {p.surface}; border: 1px solid {p.border}; padding: 4px; }}
    QMenu::item {{ padding: 5px 24px 5px 12px; border-radius: 4px; }}
    QMenu::item:selected {{ background: {p.accent}; color: {p.accent_text}; }}
    QMenu::item:disabled {{ color: {p.muted}; }}
    QStatusBar {{ background: {p.surface}; color: {p.muted}; border-top: 1px solid {p.border}; }}
    QStatusBar QPushButton {{ background: transparent; border: none; color: {p.muted}; font-weight: 600; }}
    QStatusBar QPushButton:hover {{ color: {p.accent}; }}
    QListWidget, QTableWidget, QPlainTextEdit {{
        background: {p.surface}; color: {p.text}; border: 1px solid {p.border}; border-radius: 6px;
        gridline-color: {p.border}; selection-background-color: {p.accent}; selection-color: {p.accent_text};
    }}
    QHeaderView::section {{ background: {p.surface_alt}; color: {p.muted}; border: none;
        border-right: 1px solid {p.border}; border-bottom: 1px solid {p.border}; padding: 3px 6px; }}
    QTableCornerButton::section {{ background: {p.surface_alt}; border: none; }}
    QDialog {{ background: {p.background}; }}
    QComboBox {{ background: {p.surface}; border: 1px solid {p.border}; border-radius: 6px; padding: 4px 8px; }}
    """
