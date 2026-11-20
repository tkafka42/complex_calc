"""Main window with pages (Calculator, Graphs, Lists & Spreadsheet)."""

from __future__ import annotations

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from ..core.session import Session
from .calculator_page import CalculatorPage

APP_NAME = "Complex Calc"

ABOUT = f"""<h3>{APP_NAME} {__version__}</h3>
<p>Open-source CAS calculator for Linux.<br>
Uses command syntax similar to the TI-Nspire&trade; CX CAS.</p>
<p><small>This project is not affiliated with, endorsed by or sponsored by Texas Instruments.
TI-Nspire is a trademark of Texas Instruments Incorporated.</small></p>
<p>License: GPL-3.0-or-later</p>"""

SHORTCUTS = """<table>
<tr><td><b>Enter</b></td><td>evaluate</td></tr>
<tr><td><b>Ctrl+Enter</b></td><td>evaluate approximately (≈)</td></tr>
<tr><td><b>Ctrl+M</b></td><td>open the numbered menu; then type the numbers, e.g. 6 5 2</td></tr>
<tr><td><b>↑ / ↓</b></td><td>recall previous inputs</td></tr>
<tr><td><b>Click</b></td><td>an input or result in the history to paste it</td></tr>
<tr><td><b>Ctrl+L</b></td><td>clear history</td></tr>
</table>"""


def _placeholder(text: str) -> QWidget:
    page = QWidget()
    page.setObjectName("Page")
    layout = QVBoxLayout(page)
    label = QLabel(text)
    label.setAlignment(Qt.AlignCenter)
    label.setObjectName("Hint")
    layout.addWidget(label)
    return page


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(900, 700)
        self.store = QSettings("complex_calc", "complex_calc")
        self.session = Session()
        self._load_settings()

        self.tabs = QTabWidget()
        self.calculator = CalculatorPage(self.session)
        self.tabs.addTab(self.calculator, "Calculator")
        self.tabs.addTab(_placeholder("Graphs — coming in milestone M4"), "Graphs")
        self.tabs.addTab(_placeholder("Lists & Spreadsheet — coming in milestone M5"), "Lists && Spreadsheet")
        self.setCentralWidget(self.tabs)

        self._build_menu_bar()
        self._build_status_bar()
        geometry = self.store.value("geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)

    # ------------------------------------------------------------ settings
    def _load_settings(self):
        s = self.session.settings
        s.mode = str(self.store.value("mode", "auto"))
        s.angle = str(self.store.value("angle", "rad"))
        try:
            s.digits = int(self.store.value("digits", 6))
        except (TypeError, ValueError):
            s.digits = 6

    def _save_settings(self):
        s = self.session.settings
        self.store.setValue("mode", s.mode)
        self.store.setValue("angle", s.angle)
        self.store.setValue("digits", s.digits)

    def closeEvent(self, event):  # noqa: N802
        self._save_settings()
        self.store.setValue("geometry", self.saveGeometry())
        super().closeEvent(event)

    # ------------------------------------------------------------ menu bar
    def _build_menu_bar(self):
        bar = self.menuBar()
        file_menu = bar.addMenu("&File")
        quit_action = QAction("Quit", self, shortcut=QKeySequence.Quit, triggered=self.close)
        file_menu.addAction(quit_action)

        settings = bar.addMenu("&Settings")
        self.mode_actions = self._radio_group(settings, "Calculation Mode", [
            ("Auto", "auto"), ("Exact", "exact"), ("Approximate", "approx")], "mode")
        self.angle_actions = self._radio_group(settings, "Angle", [("Radian", "rad"), ("Degree", "deg")], "angle")
        self.digit_actions = self._radio_group(settings, "Display Digits",
                                               [(f"Float {d}", d) for d in (2, 3, 4, 5, 6, 8, 10, 12)], "digits")

        help_menu = bar.addMenu("&Help")
        help_menu.addAction(QAction("Keyboard Shortcuts", self, triggered=lambda: QMessageBox.information(
            self, "Keyboard Shortcuts", SHORTCUTS)))
        help_menu.addAction(QAction("About", self, triggered=lambda: QMessageBox.about(self, f"About {APP_NAME}", ABOUT)))

    def _radio_group(self, parent_menu, title: str, options, attribute: str) -> dict:
        submenu = parent_menu.addMenu(title)
        group = QActionGroup(self)
        actions = {}
        for label, value in options:
            action = QAction(label, self, checkable=True)
            action.setChecked(getattr(self.session.settings, attribute) == value)
            action.triggered.connect(lambda checked=False, v=value: self.set_setting(attribute, v))
            group.addAction(action)
            submenu.addAction(action)
            actions[value] = action
        return actions

    def set_setting(self, attribute: str, value):
        setattr(self.session.settings, attribute, value)
        for actions, attr in ((self.mode_actions, "mode"), (self.angle_actions, "angle"),
                              (self.digit_actions, "digits")):
            current = getattr(self.session.settings, attr)
            if current in actions:
                actions[current].setChecked(True)
        self._save_settings()
        self._update_status()

    # ------------------------------------------------------------ status bar
    def _build_status_bar(self):
        bar = self.statusBar()
        self.mode_button = QPushButton()
        self.mode_button.setToolTip("Calculation mode (click to cycle Auto → Exact → Approximate)")
        self.mode_button.clicked.connect(self._cycle_mode)
        self.angle_button = QPushButton()
        self.angle_button.setToolTip("Angle mode (click to toggle Radian / Degree)")
        self.angle_button.clicked.connect(self._toggle_angle)
        self.digits_label = QLabel()
        for widget in (self.mode_button, self.angle_button, self.digits_label):
            widget.setFocusPolicy(Qt.NoFocus)
            bar.addPermanentWidget(widget)
        bar.showMessage("Ctrl+M opens the menu · Ctrl+Enter gives a decimal result")
        self._update_status()

    def _update_status(self):
        s = self.session.settings
        self.mode_button.setText({"auto": "AUTO", "exact": "EXACT", "approx": "APPROX"}[s.mode])
        self.angle_button.setText("RAD" if s.angle == "rad" else "DEG")
        self.digits_label.setText(f"Float {s.digits}")

    def _cycle_mode(self):
        order = ["auto", "exact", "approx"]
        self.set_setting("mode", order[(order.index(self.session.settings.mode) + 1) % 3])

    def _toggle_angle(self):
        self.set_setting("angle", "deg" if self.session.settings.angle == "rad" else "rad")
