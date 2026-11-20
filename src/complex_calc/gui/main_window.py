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
<tr><td><b>Ctrl+E</b></td><td>Program Editor (Func/Prgm); Ctrl+B stores</td></tr>
<tr><td><b>@e @i @&gt; @t</b></td><td>type ℯ, ⅈ, ►, ᵀ (as on the handheld's computer keyboard)</td></tr>
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
        from ..library import refresh_libraries

        refresh_libraries(self.session)

        self.tabs = QTabWidget()
        self.calculator = CalculatorPage(self.session)
        self.tabs.addTab(self.calculator, "Calculator")
        from .graphs_page import GraphsPage

        self.graphs = GraphsPage(self.session)
        self.tabs.addTab(self.graphs, "Graphs")
        from .lists_page import ListsPage

        self.lists = ListsPage(self.session, self.graphs)
        self.tabs.addTab(self.lists, "Lists && Spreadsheet")
        self.setCentralWidget(self.tabs)

        self._build_menu_bar()
        self._build_status_bar()
        geometry = self.store.value("geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)

    # ------------------------------------------------------------ settings
    SAVED = ("mode", "angle", "complex_format", "exp_format", "base", "display", "letters_are_constants")

    def _load_settings(self):
        for name in self.SAVED:
            value = self.store.value(name)
            if value is None:
                continue
            if name == "letters_are_constants":
                value = str(value).lower() == "true"
            self._apply(name, value)

    def _save_settings(self):
        for name in self.SAVED:
            self.store.setValue(name, self._current(name))

    def _current(self, name: str):
        s = self.session.settings
        if name == "display":
            if s.fix is not None:
                return f"Fix{s.fix}"
            return "Float" if s.float_full else f"Float{s.digits}"
        return getattr(s, name)

    def _apply(self, name: str, value) -> None:
        s = self.session.settings
        if name == "display":
            value = str(value)
            if value.startswith("Fix"):
                s.fix = int(value[3:])
            elif value == "Float":
                s.fix, s.float_full, s.digits = None, True, 12
            else:
                s.fix, s.float_full, s.digits = None, False, int(value[5:] or 6)
        else:
            setattr(s, name, value)

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

        file_menu.insertAction(quit_action, QAction("Program Editor…", self, shortcut=QKeySequence("Ctrl+E"),
                                                    triggered=lambda: self.calculator.open_program_editor()))
        file_menu.insertSeparator(quit_action)

        settings = bar.addMenu("&Settings")  # order as in the handheld's Document Settings
        self.groups: dict[str, dict] = {}
        self.groups["display"] = self._radio_group(
            settings, "Display Digits",
            [("Float", "Float")] + [(f"Float {d}", f"Float{d}") for d in range(1, 13)]
            + [(f"Fix {d}", f"Fix{d}") for d in range(0, 13)], "display")
        self.groups["angle"] = self._radio_group(settings, "Angle", [("Radian", "rad"), ("Degree", "deg"),
                                                                     ("Gradian", "grad")], "angle")
        self.groups["exp_format"] = self._radio_group(settings, "Exponential Format", [
            ("Normal", "normal"), ("Scientific", "scientific"), ("Engineering", "engineering")], "exp_format")
        self.groups["complex_format"] = self._radio_group(settings, "Real or Complex Format", [
            ("Real", "real"), ("Rectangular", "rectangular"), ("Polar", "polar")], "complex_format")
        self.groups["mode"] = self._radio_group(settings, "Calculation Mode", [
            ("Auto", "auto"), ("Exact", "exact"), ("Approximate", "approx")], "mode")
        self.groups["base"] = self._radio_group(settings, "Base", [
            ("Decimal", "dec"), ("Hex", "hex"), ("Binary", "bin")], "base")
        settings.addSeparator()
        letters = QAction("Typed e and i are constants (not on the handheld)", self, checkable=True)
        letters.setChecked(self.session.settings.letters_are_constants)
        letters.toggled.connect(lambda on: self.set_setting("letters_are_constants", on))
        settings.addAction(letters)

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
            action.setChecked(self._current(attribute) == value)
            action.triggered.connect(lambda checked=False, v=value: self.set_setting(attribute, v))
            group.addAction(action)
            submenu.addAction(action)
            actions[value] = action
        return actions

    def set_setting(self, attribute: str, value):
        self._apply(attribute, value)
        for name, actions in getattr(self, "groups", {}).items():
            current = self._current(name)
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
        self.angle_button.setText({"rad": "RAD", "deg": "DEG", "grad": "GRAD"}[s.angle])
        display = self._current("display")
        self.digits_label.setText(display.replace("Float", "Float ").replace("Fix", "Fix ").strip()
                                  + ("  ·  ℂ" if s.complex_format != "real" else "  ·  ℝ"))

    def _cycle_mode(self):
        order = ["auto", "exact", "approx"]
        self.set_setting("mode", order[(order.index(self.session.settings.mode) + 1) % 3])

    def _toggle_angle(self):
        order = ["rad", "deg", "grad"]
        self.set_setting("angle", order[(order.index(self.session.settings.angle) + 1) % 3])
