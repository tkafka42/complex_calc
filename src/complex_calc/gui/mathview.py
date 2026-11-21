"""Render LaTeX (matplotlib mathtext) into QPixmaps for 2D math display."""

from __future__ import annotations

import io
from functools import lru_cache

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication, QPixmap
from PySide6.QtWidgets import QLabel


@lru_cache(maxsize=512)
def _png(tex: str, color: str, size: float, dpi: int) -> bytes | None:
    from matplotlib.figure import Figure
    from matplotlib.font_manager import FontProperties

    buffer = io.BytesIO()
    try:
        figure = Figure(figsize=(0.01, 0.01))
        figure.text(0, 0, f"${tex}$", fontproperties=FontProperties(size=size), color=color)
        figure.savefig(buffer, dpi=dpi, format="png", bbox_inches="tight", pad_inches=0.03, transparent=True)
    except Exception:  # noqa: BLE001 - caller falls back to plain text
        return None
    return buffer.getvalue()


def math_pixmap(tex: str, color: str, size: float = 13.0) -> QPixmap | None:
    ratio = QGuiApplication.primaryScreen().devicePixelRatio() if QGuiApplication.primaryScreen() else 1.0
    data = _png(tex, color, size, int(100 * ratio))
    if data is None:
        return None
    pixmap = QPixmap()
    pixmap.loadFromData(data, "PNG")
    pixmap.setDevicePixelRatio(ratio)
    return pixmap


class MathLabel(QLabel):
    """Shows `tex` in 2D (or `fallback` as text); click emits `payload`."""

    clicked = Signal(str)

    def __init__(self, tex: str | None, fallback: str, payload: str, color: str, object_name: str,
                 size: float = 13.0, tooltip: str = ""):
        super().__init__()
        self.payload = payload
        self.setObjectName(object_name)
        pixmap = math_pixmap(tex, color, size) if tex else None
        if pixmap is not None:
            self.setPixmap(pixmap)
        else:
            self.setTextFormat(Qt.PlainText)
            self.setText(fallback)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(tooltip or fallback)

    def mousePressEvent(self, event):  # noqa: N802
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.payload)
        super().mousePressEvent(event)
