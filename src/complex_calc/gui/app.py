"""GUI entry point: ``complex-calc-gui``."""

from __future__ import annotations

import os
import sys


def main() -> int:
    # Prefer native Wayland (e.g. niri), fall back to X11/XWayland.
    if os.environ.get("WAYLAND_DISPLAY") and not os.environ.get("QT_QPA_PLATFORM"):
        os.environ["QT_QPA_PLATFORM"] = "wayland;xcb"

    from PySide6.QtGui import QGuiApplication
    from PySide6.QtWidgets import QApplication

    from PySide6.QtCore import QSettings

    from ..i18n import detect_language, set_language
    from .main_window import APP_NAME, MainWindow

    set_language(str(QSettings("complex_calc", "complex_calc").value("language", detect_language())))
    from .theme import current_palette, stylesheet

    app = QApplication(sys.argv)
    app.setApplicationName("complex_calc")
    app.setApplicationDisplayName(APP_NAME)
    QGuiApplication.setDesktopFileName("complex_calc")  # matches data/complex_calc.desktop (Wayland app-id)

    def apply_theme(*_):
        app.setStyleSheet(stylesheet(current_palette()))

    apply_theme()
    try:
        app.styleHints().colorSchemeChanged.connect(apply_theme)
    except AttributeError:  # Qt < 6.5
        pass

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
