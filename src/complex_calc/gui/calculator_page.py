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
from ..core.latex import input_latex, value_latex
from ..core.session import Entry, Session
from ..core.values import StatResults, is_matrix
from ..functions.registry import REGISTRY
from ..i18n import tr, tr_error
from ..menus import MENU, MenuItem
from .mathview import MathLabel
from .theme import current_palette
from .wizard_dialog import run_wizard

SYMBOLS = ["π", "ℯ", "ⅈ", "∞", "√(", "^", "²", "≤", "≥", "≠", "→", "|", "°", "∠", "►",
           "[", "]", "{", "}", "θ", "x̄", "σ", "μ", "λ", "χ²"]


class ClickableLabel(QLabel):
    clicked = Signal(str)

    def __init__(self, text: str, payload: str, object_name: str):
        super().__init__(text)
        self.payload = payload
        self.setObjectName(object_name)
        self.setTextFormat(Qt.PlainText)
        self.setCursor(Qt.PointingHandCursor)
        self.setTextInteractionFlags(Qt.NoTextInteraction)
        self.setToolTip(tr("Click to paste into the entry line"))

    def mousePressEvent(self, event):  # noqa: N802 (Qt naming)
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.payload)
        super().mousePressEvent(event)


def _matrix_widget(matrix, session: Session, color: str, on_click) -> QWidget:
    """A matrix shown as a grid between brackets."""
    box = QWidget()
    outer = QHBoxLayout(box)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(2)
    left, right = QLabel("["), QLabel("]")
    for bracket in (left, right):
        bracket.setObjectName("Bracket")
    grid_box = QWidget()
    grid = QGridLayout(grid_box)
    grid.setContentsMargins(4, 0, 4, 0)
    grid.setHorizontalSpacing(14)
    grid.setVerticalSpacing(2)
    for r in range(matrix.rows):
        for c in range(matrix.cols):
            cell = matrix[r, c]
            label = MathLabel(value_latex(cell, session.settings), session.format(cell), session.format(cell),
                              color, "ResultText")
            label.clicked.connect(on_click)
            grid.addWidget(label, r, c, alignment=Qt.AlignCenter)
    size = int(14 + 15 * matrix.rows)
    for bracket in (left, right):
        bracket.setStyleSheet(f"font-size: {size}px; font-weight: 200;")
    outer.addWidget(left)
    outer.addWidget(grid_box)
    outer.addWidget(right)
    return box


class HistoryItem(QFrame):
    paste_requested = Signal(str)

    def __init__(self, entry: Entry, session: Session):
        super().__init__()
        self.setObjectName("HistoryItem")
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        palette = current_palette()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(2)

        first_line = entry.source.splitlines()[0] if entry.source else ""
        shown = first_line + (" …" if "\n" in entry.source else "")
        source = MathLabel(input_latex(entry.source, session), shown, entry.source, palette.text, "InputText",
                           tooltip=entry.source)
        source.clicked.connect(self.paste_requested)
        layout.addWidget(source, alignment=Qt.AlignLeft)

        for line in entry.output:  # Disp / Text output of programs
            out = QLabel(line)
            out.setObjectName("TableLabel")
            out.setTextFormat(Qt.PlainText)
            out.setTextInteractionFlags(Qt.TextSelectableByMouse)
            layout.addWidget(out, alignment=Qt.AlignLeft)

        if entry.error:
            error = QLabel(tr_error(entry.text))
            error.setObjectName("ErrorText")
            error.setTextFormat(Qt.PlainText)
            error.setTextInteractionFlags(Qt.TextSelectableByMouse)
            layout.addWidget(error, alignment=Qt.AlignRight)
        elif isinstance(entry.value, StatResults):
            layout.addWidget(self._table(entry.value, session), alignment=Qt.AlignRight)
        elif is_matrix(entry.value):
            layout.addWidget(_matrix_widget(entry.value, session, palette.result,
                                            lambda _=None: self.paste_requested.emit(entry.text)),
                             alignment=Qt.AlignRight)
        else:
            result = MathLabel(value_latex(entry.value, session.settings), entry.text, entry.text, palette.result,
                               "ResultText", size=13.5)
            result.clicked.connect(self.paste_requested)
            layout.addWidget(result, alignment=Qt.AlignRight)

    def _table(self, results: StatResults, session: Session) -> QWidget:
        box = QWidget()
        grid = QGridLayout(box)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(18)
        grid.setVerticalSpacing(2)
        for row, (label, value) in enumerate(stat_table(results, session.settings)):
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
        self.setPlaceholderText(tr("Enter an expression (Ctrl+M: menu, Ctrl+K: catalog)"))
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

    def insert_template(self, text: str, offset: int):
        position = self.cursorPosition()
        self.insert(text)
        self.setCursorPosition(position + offset)
        self.setFocus()

    def current_function(self) -> str | None:
        """Name of the function whose parentheses contain the cursor (for the syntax help)."""
        text = self.text()[: self.cursorPosition()]
        depth = 0
        for k in range(len(text) - 1, -1, -1):
            ch = text[k]
            if ch == ")":
                depth += 1
            elif ch == "(":
                if depth == 0:
                    end = k
                    start = end
                    while start > 0 and (text[start - 1].isalnum() or text[start - 1] in "_.²⁻¹χΔΣΠ√∫►"):
                        start -= 1
                    return text[start:end] or None
                depth -= 1
        words = text.split()
        return words[0] if words else None


def build_menu(parent: QWidget, items: list[MenuItem], on_select) -> QMenu:
    """Build a QMenu whose keys 1–9/A–K work as mnemonics, like on a handheld."""
    menu = QMenu(parent)
    menu.setAttribute(Qt.WA_TranslucentBackground, False)
    menu.setAutoFillBackground(True)
    for item in items:
        label = f"&{item.key}: {tr(item.label).replace('&', '&&')}"
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
        self.history_box.setObjectName("HistoryBox")
        self.history_layout = QVBoxLayout(self.history_box)
        self.history_layout.setSpacing(0)
        self.history_layout.addStretch(1)
        self.scroll.setWidget(self.history_box)
        layout.addWidget(self.scroll, 1)

        # symbol bar
        symbols = QHBoxLayout()
        symbols.setSpacing(3)
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
        self.menu_button = QPushButton(tr("Menu"))
        self.menu_button.setObjectName("Primary")
        self.menu_button.setToolTip(tr("Numbered command menu (Ctrl+M)"))
        self.menu_button.setFocusPolicy(Qt.NoFocus)
        self.menu_button.clicked.connect(self.open_menu)
        row.addWidget(self.menu_button)

        self.template_button = QPushButton("□/□")
        self.template_button.setToolTip(tr("Templates") + " (Ctrl+T)")
        self.template_button.setFocusPolicy(Qt.NoFocus)
        self.template_button.clicked.connect(self.open_templates)
        row.addWidget(self.template_button)

        self.catalog_button = QPushButton("📖")
        self.catalog_button.setToolTip(tr("Catalog") + " (Ctrl+K)")
        self.catalog_button.setFocusPolicy(Qt.NoFocus)
        self.catalog_button.clicked.connect(self.open_catalog)
        row.addWidget(self.catalog_button)

        self.entry = EntryLine()
        self.entry.submitted.connect(self.submit)
        self.entry.cursorPositionChanged.connect(self.update_help)
        self.entry.textChanged.connect(self.update_help)
        row.addWidget(self.entry, 1)

        approx_button = QPushButton("≈")
        approx_button.setToolTip(tr("Evaluate approximately (Ctrl+Enter)"))
        approx_button.setFocusPolicy(Qt.NoFocus)
        approx_button.clicked.connect(lambda: self._submit_from_button(True))
        row.addWidget(approx_button)

        enter_button = QPushButton(tr("Enter"))
        enter_button.setObjectName("Primary")
        enter_button.setFocusPolicy(Qt.NoFocus)
        enter_button.clicked.connect(lambda: self._submit_from_button(False))
        row.addWidget(enter_button)
        layout.addLayout(row)

        self.help_line = QLabel(" ")
        self.help_line.setObjectName("HelpLine")
        self.help_line.setTextFormat(Qt.PlainText)
        layout.addWidget(self.help_line)

        self.menu = build_menu(self, MENU, self.on_menu_item)
        self.session.input_provider = self.ask_input
        for keys, slot in (("Ctrl+M", self.open_menu), ("Ctrl+L", self.clear_history),
                           ("Ctrl+K", self.open_catalog), ("Ctrl+T", self.open_templates)):
            shortcut = QShortcut(QKeySequence(keys), self, activated=slot)
            shortcut.setContext(Qt.WidgetWithChildrenShortcut)
        self.entry.setFocus()

    # ------------------------------------------------------------ catalog, templates, help
    def open_catalog(self):
        from .catalog import CatalogDialog

        dialog = CatalogDialog(self)
        dialog.inserted.connect(self.entry.insert_text)
        dialog.exec()

    def open_templates(self):
        from .catalog import TemplatePalette

        palette = TemplatePalette(self)
        palette.chosen.connect(self.entry.insert_template)
        palette.move(self.template_button.mapToGlobal(QPoint(0, -palette.sizeHint().height() - 4)))
        palette.show()

    def update_help(self, *_):
        name = self.entry.current_function()
        spec = REGISTRY.get(name.lower()) if name else None
        self.help_line.setText(f"{spec.signature}   —   {spec.summary}" if spec else " ")

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
        if entry.drawing:
            self.show_drawing(entry.drawing)
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

    def show_drawing(self, ops):
        """Graphics screen of a program (CX II Draw commands), 318×212 px."""
        from PySide6.QtGui import QImage, QPixmap
        from PySide6.QtWidgets import QDialog, QVBoxLayout as VBox

        from ..functions.draw import render

        image = render(ops, scale=2)
        data = image.tobytes("raw", "RGB")
        qimage = QImage(data, image.width, image.height, image.width * 3, QImage.Format_RGB888).copy()
        dialog = QDialog(self)
        dialog.setWindowTitle(tr("Graphics"))
        box = VBox(dialog)
        label = QLabel()
        label.setPixmap(QPixmap.fromImage(qimage))
        box.addWidget(label)
        hint = QLabel(tr("Finished — press any key or close the window"))
        hint.setObjectName("Hint")
        box.addWidget(hint)
        dialog.keyPressEvent = lambda event: dialog.accept()
        dialog.exec()

    def open_program_editor(self, name: str = ""):
        from .program_editor import ProgramEditor

        editor = ProgramEditor(self.session, self, name)
        if editor.exec():
            self.add_history_item(self.session.history[-1])

    def recall_definition(self):
        from PySide6.QtWidgets import QInputDialog

        from ..core.session import normalize_name
        from ..core.values import UserFunction, UserProgram

        name, ok = QInputDialog.getText(self, tr("Recall Definition"), tr("Variable or function name:"))
        if not ok or not name.strip():
            return
        value = self.session.variables.get(normalize_name(name.strip()))
        if isinstance(value, UserProgram):
            self.open_program_editor(name.strip())
        elif isinstance(value, UserFunction):
            params = ",".join(p.name for p in value.params)
            from ..core.formatting import format_expr

            self.entry.setText(f"Define {name.strip()}({params})={format_expr(value.body, self.session.settings)}")
        elif value is not None:
            self.entry.setText(f"{name.strip()}:={self.session.format(value)}")

    def ask_input(self, prompt: str, as_string):
        """Input provider for Request / RequestStr / Text."""
        from PySide6.QtWidgets import QInputDialog, QMessageBox

        if as_string is None:  # Text
            QMessageBox.information(self, "Text", prompt)
            return ""
        text, ok = QInputDialog.getText(self, "Request", prompt)
        return text if ok else None

    def on_menu_item(self, item: MenuItem):
        if item.wizard is not None:
            command = run_wizard(item.wizard, self)
            if command:
                self.submit(command)
            return
        if item.action == "clear_history":
            self.clear_history()
        elif item.action == "clear_az":
            self.submit("ClearAZ")
        elif item.action == "program_editor":
            self.open_program_editor()
        elif item.action == "recall_definition":
            self.recall_definition()
        elif item.action == "refresh_libraries":
            from ..library import refresh_libraries

            messages = refresh_libraries(self.session)
            self.add_history_item(Entry("Refresh Libraries", "\n".join(messages) or "Done"))
        elif item.action == "open_library_folder":
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices

            from ..library import library_folder

            folder = library_folder()
            folder.mkdir(parents=True, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
        elif item.insert:
            self.entry.insert_text(item.insert)
        self.entry.setFocus()
