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
from ..i18n import LANGUAGES, language, tr
from .calculator_page import CalculatorPage

APP_NAME = "Complex Calc"

ABOUT = f"""<h3>{APP_NAME} {__version__}</h3>
<p>Open-source CAS calculator for Linux.<br>
Uses command syntax similar to the TI-Nspire&trade; CX CAS.</p>
<p><small>This project is not affiliated with, endorsed by or sponsored by Texas Instruments.
TI-Nspire is a trademark of Texas Instruments Incorporated.</small></p>
<p>License: GPL-3.0-or-later</p>"""

SHORTCUTS = {
    "en": """<table>
<tr><td><b>Enter</b></td><td>evaluate</td></tr>
<tr><td><b>Ctrl+Enter</b></td><td>evaluate approximately (≈)</td></tr>
<tr><td><b>Ctrl+M</b></td><td>open the numbered menu; then type the numbers, e.g. 5 5 2</td></tr>
<tr><td><b>Ctrl+K</b></td><td>catalog of all commands with syntax help</td></tr>
<tr><td><b>Ctrl+T</b></td><td>templates (fraction, root, integral, matrix …)</td></tr>
<tr><td><b>Ctrl+I</b></td><td>insert a page (Calculator, Graphs, Lists &amp; Spreadsheet)</td></tr>
<tr><td><b>Ctrl+Tab</b></td><td>next page</td></tr>
<tr><td><b>↑ / ↓</b></td><td>recall previous inputs</td></tr>
<tr><td><b>Click</b></td><td>an input or result in the history to paste it</td></tr>
<tr><td><b>Ctrl+L</b></td><td>clear history</td></tr>
<tr><td><b>Ctrl+E</b></td><td>Program Editor (Func/Prgm); Ctrl+B stores</td></tr>
<tr><td><b>@e @i @&gt; @t</b></td><td>type ℯ, ⅈ, ►, ᵀ (as on the handheld's computer keyboard)</td></tr>
</table>""",
    "de": """<table>
<tr><td><b>Enter</b></td><td>berechnen</td></tr>
<tr><td><b>Strg+Enter</b></td><td>näherungsweise berechnen (≈)</td></tr>
<tr><td><b>Strg+M</b></td><td>nummeriertes Menü öffnen, dann Ziffern tippen, z. B. 5 5 2</td></tr>
<tr><td><b>Strg+K</b></td><td>Katalog aller Befehle mit Syntaxhilfe</td></tr>
<tr><td><b>Strg+T</b></td><td>Vorlagen (Bruch, Wurzel, Integral, Matrix …)</td></tr>
<tr><td><b>Strg+I</b></td><td>Seite einfügen (Calculator, Graphs, Lists &amp; Spreadsheet)</td></tr>
<tr><td><b>Strg+Tab</b></td><td>nächste Seite</td></tr>
<tr><td><b>↑ / ↓</b></td><td>frühere Eingaben zurückholen</td></tr>
<tr><td><b>Klick</b></td><td>auf Eingabe oder Ergebnis im Verlauf fügt sie ein</td></tr>
<tr><td><b>Strg+L</b></td><td>Verlauf löschen</td></tr>
<tr><td><b>Strg+E</b></td><td>Programmeditor (Func/Prgm); Strg+B speichert</td></tr>
<tr><td><b>@e @i @&gt; @t</b></td><td>tippt ℯ, ⅈ, ►, ᵀ (wie an der Computertastatur des Geräts)</td></tr>
</table>""",
}


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

        # pages of problem 1 ("1.1", "1.2", …) share variables, like in a handheld document
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_page)
        self.calculator = self.add_page("calculator")
        self.graphs = self.add_page("graphs")
        self.lists = self.add_page("lists")
        self.tabs.setCurrentIndex(0)
        self.setCentralWidget(self.tabs)

        self._build_menu_bar()
        self._build_status_bar()
        geometry = self.store.value("geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)

    # ------------------------------------------------------------ pages
    def add_page(self, kind: str):
        if kind == "calculator":
            page = CalculatorPage(self.session)
        elif kind == "graphs":
            from .graphs_page import GraphsPage

            page = GraphsPage(self.session)
        else:
            from .lists_page import ListsPage

            graphs = next((self.tabs.widget(k) for k in range(self.tabs.count())
                           if type(self.tabs.widget(k)).__name__ == "GraphsPage"), None)
            page = ListsPage(self.session, graphs)
        page.kind = kind
        self.tabs.addTab(page, "")
        self.tabs.setCurrentWidget(page)
        self._renumber()
        return page

    def _renumber(self):
        names = {"calculator": "Calculator", "graphs": "Graphs", "lists": "Lists & Spreadsheet"}
        for k in range(self.tabs.count()):
            page = self.tabs.widget(k)
            self.tabs.setTabText(k, f"1.{k + 1}  {tr(names[page.kind]).replace('&', '&&')}")

    def close_page(self, index: int):
        if self.tabs.count() <= 1:
            return
        page = self.tabs.widget(index)
        self.tabs.removeTab(index)
        page.deleteLater()
        self._renumber()

    def insert_page_dialog(self):
        from PySide6.QtWidgets import QInputDialog

        options = [tr("New Calculator page"), tr("New Graphs page"), tr("New Lists & Spreadsheet page")]
        choice, ok = QInputDialog.getItem(self, tr("Insert Page"), tr("Insert Page"), options, 0, False)
        if ok:
            self.add_page(["calculator", "graphs", "lists"][options.index(choice)])

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
        file_menu = bar.addMenu("&" + tr("File"))
        file_menu.addAction(QAction(tr("Insert Page") + "…", self, shortcut=QKeySequence("Ctrl+I"),
                                    triggered=self.insert_page_dialog))
        file_menu.addAction(QAction(tr("Close Page"), self, shortcut=QKeySequence("Ctrl+W"),
                                    triggered=lambda: self.close_page(self.tabs.currentIndex())))
        file_menu.addAction(QAction(tr("Program Editor…"), self, shortcut=QKeySequence("Ctrl+E"),
                                    triggered=lambda: self.calculator.open_program_editor()))
        file_menu.addSeparator()
        file_menu.addAction(QAction(tr("Quit"), self, shortcut=QKeySequence.Quit, triggered=self.close))
        next_page = QAction(self, shortcut=QKeySequence("Ctrl+Tab"),
                            triggered=lambda: self.tabs.setCurrentIndex((self.tabs.currentIndex() + 1) % self.tabs.count()))
        self.addAction(next_page)

        settings = bar.addMenu("&" + tr("Settings"))  # order as in the handheld's Document Settings
        self.groups: dict[str, dict] = {}
        self.groups["display"] = self._radio_group(
            settings, tr("Display Digits"),
            [("Float", "Float")] + [(f"Float {d}", f"Float{d}") for d in range(1, 13)]
            + [(f"Fix {d}", f"Fix{d}") for d in range(0, 13)], "display")
        self.groups["angle"] = self._radio_group(settings, tr("Angle"), [
            (tr("Radian"), "rad"), (tr("Degree"), "deg"), (tr("Gradian"), "grad")], "angle")
        self.groups["exp_format"] = self._radio_group(settings, tr("Exponential Format"), [
            (tr("Normal"), "normal"), (tr("Scientific"), "scientific"), (tr("Engineering"), "engineering")],
            "exp_format")
        self.groups["complex_format"] = self._radio_group(settings, tr("Real or Complex Format"), [
            (tr("Real"), "real"), (tr("Rectangular"), "rectangular"), (tr("Polar"), "polar")], "complex_format")
        self.groups["mode"] = self._radio_group(settings, tr("Calculation Mode"), [
            (tr("Auto"), "auto"), (tr("Exact"), "exact"), (tr("Approximate"), "approx")], "mode")
        self.groups["base"] = self._radio_group(settings, tr("Base"), [
            (tr("Decimal"), "dec"), (tr("Hex"), "hex"), (tr("Binary"), "bin")], "base")
        settings.addSeparator()
        language_menu = settings.addMenu(tr("Language"))
        language_group = QActionGroup(self)
        for code, label in LANGUAGES.items():
            action = QAction(label, self, checkable=True)
            action.setChecked(language() == code)
            action.triggered.connect(lambda checked=False, c=code: self.change_language(c))
            language_group.addAction(action)
            language_menu.addAction(action)
        letters = QAction(tr("Typed e and i are constants (not on the handheld)"), self, checkable=True)
        letters.setChecked(self.session.settings.letters_are_constants)
        letters.toggled.connect(lambda on: self.set_setting("letters_are_constants", on))
        settings.addAction(letters)

        help_menu = bar.addMenu("&" + tr("Help"))
        help_menu.addAction(QAction(tr("Keyboard Shortcuts"), self, triggered=lambda: QMessageBox.information(
            self, tr("Keyboard Shortcuts"), SHORTCUTS[language()])))
        help_menu.addAction(QAction(tr("Catalog") + "…", self, triggered=lambda: self.calculator.open_catalog()))
        help_menu.addAction(QAction(tr("About"), self, triggered=lambda: QMessageBox.about(
            self, f"{tr('About')} {APP_NAME}", ABOUT)))

    def change_language(self, code: str):
        self.store.setValue("language", code)
        answer = QMessageBox.question(self, tr("Language"), tr("Restart to apply the language completely?"))
        if answer == QMessageBox.Yes:
            import os
            import sys

            self.close()
            os.execv(sys.executable, [sys.executable, "-m", "complex_calc", "--gui"])

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
        bar.showMessage(tr("Ctrl+M opens the menu · Ctrl+K catalog · Ctrl+Enter gives a decimal result"))
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
