"""Calculator page: entry line, scrollable history, numbered menu and wizards."""

from __future__ import annotations

from PySide6.QtCore import QPoint, QStringListModel, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCompleter,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ..core.formatting import stat_table
from ..core.session import Entry, Session
from ..core.values import StatResults
from ..functions.registry import REGISTRY
from ..menus import MENU, MenuItem
from .wizard_dialog import run_wizard

SYMBOLS = ["√(", "π", "ℯ^(", "ⅈ", "∞", "^", "²", "≤", "≥", "≠", "→", "|", "°", "∫(", "x̄", "σ", "μ", "{", "}"]


class ClickableLabel(QLabel):
    clicked = Signal(str)

    def __init__(self, text: str, payload: str, object_name: str):
        super().__init__(text)
        self.payload = payload
        self.setObjectName(object_name)
        self.setTextFormat(Qt.PlainText)
        self.setCursor(Qt.PointingHandCursor)
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        self.setToolTip("Click to paste into the entry line")

    def mousePressEvent(self, event):  # noqa: N802 (Qt naming)
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.payload)
        super().mousePressEvent(event)


class HistoryItem(QFrame):
    paste_requested = Signal(str)

    def __init__(self, entry: Entry, session: Session):
        super().__init__()
        self.setObjectName("HistoryItem")
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(4)

        source = ClickableLabel(entry.source, entry.source, "InputText")
        source.clicked.connect(self.paste_requested)
        layout.addWidget(source, alignment=Qt.AlignLeft)

        if entry.error:
            error = QLabel(entry.text)
            error.setObjectName("ErrorText")
            error.setTextFormat(Qt.PlainText)
            error.setTextInteractionFlags(Qt.TextSelectableByMouse)
            layout.addWidget(error, alignment=Qt.AlignRight)
        elif isinstance(entry.value, StatResults):
            layout.addWidget(self._table(entry.value, session), alignment=Qt.AlignRight)
        else:
            result = ClickableLabel(entry.text, entry.text, "ResultText")
            result.clicked.connect(self.paste_requested)
            layout.addWidget(result, alignment=Qt.AlignRight)

    def _table(self, results: StatResults, session: Session) -> QWidget:
        box = QWidget()
        grid = QGridLayout(box)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(2)
        for row, (label, value) in enumerate(stat_table(results, session.settings.digits)):
            name = QLabel(label)
            name.setTextFormat(Qt.PlainText)
            name.setObjectName("TableLabel")
            grid.addWidget(name, row, 0)
            cell = ClickableLabel(value, value.strip('"'), "TableValue")
            cell.clicked.connect(self.paste_requested)
            grid.addWidget(cell, row, 1)
        return box


class EntryLine(QLineEdit):
    """Entry with history recall (↑/↓), Ctrl+Enter for approximate results
    and word completion of function names."""

    submitted = Signal(str, bool)  # text, approximate

    def __init__(self):
        super().__init__()
        self.setPlaceholderText("Enter an expression, e.g. normCdf(-∞,520,500,10)   (Ctrl+M: menu)")
        self.recall: list[str] = []
        self.recall_index = 0
        names = sorted({spec.name for spec in REGISTRY.values()} | {"Define", "DelVar", "CopyVar"}, key=str.lower)
        self.completer = QCompleter(QStringListModel(names), self)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.completer.setWidget(self)
        self.completer.activated.connect(self._insert_completion)
        self.textEdited.connect(self._update_completion)

    # --- completion of the word left of the cursor
    def _current_word(self) -> str:
        text = self.text()[: self.cursorPosition()]
        start = len(text)
        while start > 0 and (text[start - 1].isalnum() or text[start - 1] in "_.²⁻¹χ"):
            start -= 1
        return text[start:]

    def _update_completion(self):
        word = self._current_word()
        if len(word) < 2 or word[0].isdigit():
            self.completer.popup().hide()
            return
        self.completer.setCompletionPrefix(word)
        if self.completer.completionCount() == 0:
            self.completer.popup().hide()
            return
        self.completer.complete()

    def _insert_completion(self, name: str):
        word = self._current_word()
        pos = self.cursorPosition()
        spec = REGISTRY.get(name.lower())
        suffix = "(" if spec is not None and not spec.command else " "
        text = self.text()
        self.setText(text[: pos - len(word)] + name + suffix + text[pos:])
        self.setCursorPosition(pos - len(word) + len(name) + len(suffix))

    # --- keys
    def keyPressEvent(self, event):  # noqa: N802
        popup_visible = self.completer.popup().isVisible()
        key = event.key()
        if popup_visible and key in (Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab, Qt.Key_Escape, Qt.Key_Up, Qt.Key_Down):
            event.ignore()
            return
        if key in (Qt.Key_Return, Qt.Key_Enter):
            text = self.text().strip()
            if text:
                self.recall.append(text)
                self.recall_index = len(self.recall)
                self.submitted.emit(text, bool(event.modifiers() & Qt.ControlModifier))
            return
        if key == Qt.Key_Up and self.recall:
            self.recall_index = max(0, self.recall_index - 1)
            self.setText(self.recall[self.recall_index])
            return
        if key == Qt.Key_Down and self.recall:
            self.recall_index = min(len(self.recall), self.recall_index + 1)
            self.setText(self.recall[self.recall_index] if self.recall_index < len(self.recall) else "")
            return
        super().keyPressEvent(event)

    def insert_text(self, text: str):
        self.insert(text)
        self.setFocus()


def build_menu(parent: QWidget, items: list[MenuItem], on_select) -> QMenu:
    """Build a QMenu whose keys 1–9/A–K work as mnemonics, like on a handheld."""
    menu = QMenu(parent)
    for item in items:
        label = f"&{item.key}: {item.label.replace('&', '&&')}"
        if item.unsure:
            label += "  (?)"
        if item.children:
            submenu = build_menu(parent, item.children, on_select)
            submenu.setTitle(label)
            submenu.setEnabled(item.enabled)
            menu.addMenu(submenu)
        else:
            action = QAction(label, menu)
            action.setEnabled(item.enabled)
            action.triggered.connect(lambda checked=False, it=item: on_select(it))
            menu.addAction(action)
    return menu


class CalculatorPage(QWidget):
    settings_changed = Signal()

    def __init__(self, session: Session):
        super().__init__()
        self.setObjectName("Page")
        self.session = session

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(10)

        # history
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.history_box = QWidget()
        self.history_layout = QVBoxLayout(self.history_box)
        self.history_layout.setSpacing(8)
        self.history_layout.addStretch(1)
        self.scroll.setWidget(self.history_box)
        layout.addWidget(self.scroll, 1)

        # symbol bar
        symbols = QHBoxLayout()
        symbols.setSpacing(4)
        for symbol in SYMBOLS:
            button = QPushButton(symbol)
            button.setObjectName("Symbol")
            button.setFocusPolicy(Qt.NoFocus)
            button.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
            button.clicked.connect(lambda checked=False, s=symbol: self.entry.insert_text(s))
            symbols.addWidget(button)
        symbols.addStretch(1)
        layout.addLayout(symbols)

        # entry row
        row = QHBoxLayout()
        self.menu_button = QPushButton("Menu")
        self.menu_button.setObjectName("Primary")
        self.menu_button.setToolTip("Numbered command menu (Ctrl+M)")
        self.menu_button.setFocusPolicy(Qt.NoFocus)
        self.menu_button.clicked.connect(self.open_menu)
        row.addWidget(self.menu_button)

        self.entry = EntryLine()
        self.entry.submitted.connect(self.submit)
        row.addWidget(self.entry, 1)

        approx_button = QPushButton("≈")
        approx_button.setToolTip("Evaluate approximately (Ctrl+Enter)")
        approx_button.setFocusPolicy(Qt.NoFocus)
        approx_button.clicked.connect(lambda: self._submit_from_button(True))
        row.addWidget(approx_button)

        enter_button = QPushButton("Enter")
        enter_button.setObjectName("Primary")
        enter_button.setFocusPolicy(Qt.NoFocus)
        enter_button.clicked.connect(lambda: self._submit_from_button(False))
        row.addWidget(enter_button)
        layout.addLayout(row)

        self.menu = build_menu(self, MENU, self.on_menu_item)
        QShortcut(QKeySequence("Ctrl+M"), self, activated=self.open_menu)
        QShortcut(QKeySequence("Ctrl+L"), self, activated=self.clear_history)
        self.entry.setFocus()

    # ------------------------------------------------------------ actions
    def _submit_from_button(self, approximate: bool):
        text = self.entry.text().strip()
        if text:
            self.entry.recall.append(text)
            self.entry.recall_index = len(self.entry.recall)
            self.submit(text, approximate)

    def submit(self, text: str, approximate: bool = False):
        entry = self.session.run(text, force_approx=approximate)
        self.add_history_item(entry)
        if not entry.error:
            self.entry.clear()
        else:
            self.entry.selectAll()
        self.entry.setFocus()

    def add_history_item(self, entry: Entry):
        item = HistoryItem(entry, self.session)
        item.paste_requested.connect(self.entry.insert_text)
        self.history_layout.insertWidget(self.history_layout.count() - 1, item)
        QTimer.singleShot(0, lambda: self.scroll.verticalScrollBar().setValue(
            self.scroll.verticalScrollBar().maximum()))

    def clear_history(self):
        while self.history_layout.count() > 1:
            widget = self.history_layout.takeAt(0).widget()
            if widget is not None:
                widget.deleteLater()
        self.session.history.clear()

    def open_menu(self):
        top_left = self.menu_button.mapToGlobal(QPoint(0, 0))
        self.menu.popup(top_left - QPoint(0, self.menu.sizeHint().height()))

    def on_menu_item(self, item: MenuItem):
        if item.wizard is not None:
            command = run_wizard(item.wizard, self)
            if command:
                self.submit(command)
            return
        if item.action == "clear_history":
            self.clear_history()
        elif item.action == "clear_az":
            self.session.clear_variables()
            self.add_history_item(Entry("Clear a-z", "Done"))
        elif item.insert:
            self.entry.insert_text(item.insert)
        self.entry.setFocus()
