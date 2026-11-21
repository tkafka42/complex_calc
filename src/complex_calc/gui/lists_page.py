"""Lists & Spreadsheet page: named columns are list variables shared with the
Calculator, column formulas (=seq(…)), cell formulas (=a1+b1), statistics
wizards writing their results into the sheet, sort and Quick Graph."""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QBrush, QColor, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..core.session import Session
from ..core.values import ListValue, StatResults, StringValue
from ..core.formatting import stat_table
from ..i18n import tr
from ..menus import LISTS_MENU, MenuItem
from ..spreadsheet import COLUMNS, Sheet
from .calculator_page import build_menu
from .wizard_dialog import run_wizard

HEADER_ROWS = 2  # row 0: list name, row 1: column formula (◆)


class ListsPage(QWidget):
    def __init__(self, session: Session, graphs_page=None, rows: int = 200):
        super().__init__()
        self.setObjectName("Page")
        self.session = session
        self.graphs_page = graphs_page
        self.sheet = Sheet(session, rows)
        self._updating = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        self.table = QTableWidget(rows + HEADER_ROWS, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(list(COLUMNS))
        self.table.setVerticalHeaderLabels(["name", "◆"] + [str(k) for k in range(1, rows + 1)])
        self.table.itemChanged.connect(self._on_item_changed)
        self.table.currentCellChanged.connect(self._on_current)
        layout.addWidget(self.table, 1)

        bottom = QHBoxLayout()
        self.menu_button = QPushButton(tr("Menu"))
        self.menu_button.setObjectName("Primary")
        self.menu_button.setFocusPolicy(Qt.NoFocus)
        self.menu_button.clicked.connect(self.open_menu)
        bottom.addWidget(self.menu_button)
        self.status = QLabel(tr("Row 'name': list name (shared with the Calculator).  Row '◆': column formula, "
                                "e.g. =seq(n^2,n,1,10).  Cells: values or =a1*2."))
        self.status.setObjectName("Hint")
        self.status.setWordWrap(True)
        bottom.addWidget(self.status, 1)
        layout.addLayout(bottom)

        self.menu = build_menu(self, LISTS_MENU, self.on_menu_item)
        shortcut = QShortcut(QKeySequence("Ctrl+M"), self, activated=self.open_menu)
        shortcut.setContext(Qt.WidgetWithChildrenShortcut)
        self.refresh()

    # ------------------------------------------------------------ view
    def refresh(self):
        self._updating = True
        sheet = self.sheet
        muted = QBrush(QColor("#64748b"))
        error = QBrush(QColor("#c2410c"))
        for col in range(len(COLUMNS)):
            name_item = QTableWidgetItem(sheet.names.get(col, ""))
            name_item.setBackground(QBrush(QColor(0, 0, 0, 18)))
            self.table.setItem(0, col, name_item)
            formula_item = QTableWidgetItem(sheet.formulas.get(col, ""))
            formula_item.setForeground(error if col in sheet.formula_errors else muted)
            if col in sheet.formula_errors:
                formula_item.setToolTip(sheet.formula_errors[col])
            self.table.setItem(1, col, formula_item)
        for row in range(sheet.rows):
            for col in range(len(COLUMNS)):
                key = (row, col)
                if key not in sheet.values and key not in sheet.cells:
                    if self.table.item(row + HEADER_ROWS, col) is not None:
                        self.table.setItem(row + HEADER_ROWS, col, None)
                    continue
                value = sheet.values.get(key)
                if key in sheet.errors:
                    text = "Error"
                elif isinstance(value, StringValue):
                    text = str(value)
                else:
                    text = "" if value is None else self.session.format(value)
                item = QTableWidgetItem(text)
                if key in sheet.errors:
                    item.setForeground(error)
                    item.setToolTip(sheet.errors[key])
                elif sheet.cells.get(key, "").startswith("="):
                    item.setToolTip(sheet.cells[key])
                if col in sheet.formulas:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    item.setForeground(muted)
                self.table.setItem(row + HEADER_ROWS, col, item)
        self._updating = False

    def showEvent(self, event):  # noqa: N802 - pull lists changed in the Calculator
        if self.sheet.pull_from_session():
            self.refresh()
        super().showEvent(event)

    def _on_current(self, row, col, *_):
        if row >= HEADER_ROWS:
            raw = self.sheet.cells.get((row - HEADER_ROWS, col))
            if raw and raw.startswith("="):
                self.status.setText(f"{COLUMNS[col]}{row - HEADER_ROWS + 1}: {raw}")

    def _on_item_changed(self, item: QTableWidgetItem):
        if self._updating:
            return
        row, col, text = item.row(), item.column(), item.text()
        try:
            if row == 0:
                self.sheet.set_name(col, text)
            elif row == 1:
                self.sheet.set_formula(col, text)
            else:
                raw = self.sheet.cells.get((row - HEADER_ROWS, col), "")
                if text != self.session.format(self.sheet.values.get((row - HEADER_ROWS, col))) or not raw:
                    self.sheet.set_cell(row - HEADER_ROWS, col, text)
        except ValueError as exc:
            self.status.setText(str(exc))
        self.refresh()

    # ------------------------------------------------------------ menu
    def open_menu(self):
        top_left = self.menu_button.mapToGlobal(QPoint(0, 0))
        self.menu.popup(top_left - QPoint(0, self.menu.sizeHint().height()))

    def _current_column(self) -> int:
        return max(self.table.currentColumn(), 0)

    def on_menu_item(self, item: MenuItem):
        if item.wizard is not None:
            command = run_wizard(item.wizard, self)
            if command:
                self.run_statistics(command)
            return
        handler = getattr(self, f"action_{item.action}", None)
        if handler is not None:
            handler()

    def run_statistics(self, command: str):
        entry = self.session.run(command)
        if entry.error:
            QMessageBox.warning(self, "Statistics", entry.text)
            return
        try:
            col = self.sheet.first_empty_column()
        except ValueError:
            QMessageBox.information(self, "Statistics", entry.text)
            return
        value = entry.value
        if isinstance(value, StatResults):  # results go into two columns, like on the handheld
            rows = stat_table(value, self.session.settings)
            self.sheet.write_column(col, [StringValue(label.strip('"')) for label, _ in rows])
            self.sheet.formulas[col + 1] = "=stat.results"
            values = []
            for _, text in rows:
                values.append(StringValue(text.strip('"')) if text.startswith('"') else text)
            self.sheet.formulas.pop(col + 1, None)
            for r, text in enumerate(values):
                self.sheet.cells[(r, col + 1)] = f'"{text}"' if isinstance(text, StringValue) else text
            self.sheet.recalc()
        else:
            self.sheet.cells[(0, col)] = command if isinstance(value, ListValue) else self.session.format(value)
            self.sheet.recalc()
        self.refresh()
        self.status.setText(f"{command.splitlines()[0]} → column {COLUMNS[col]}")

    def action_l_clear_column(self):
        self.sheet.clear_column(self._current_column())
        self.refresh()

    def action_l_delete_name(self):
        self.sheet.set_name(self._current_column(), "")
        self.refresh()

    def action_l_sequence(self):
        col = self._current_column()
        formula, ok = QInputDialog.getText(self, "Generate Sequence", "Formula u(n)=", text="n^2")
        if not ok:
            return
        n0, ok = QInputDialog.getInt(self, "Generate Sequence", "n0:", 1, -10**6, 10**6)
        if not ok:
            return
        n_max, ok = QInputDialog.getInt(self, "Generate Sequence", "nMax:", 10, -10**6, 10**6)
        if not ok:
            return
        self.sheet.set_formula(col, f"=seq({formula},n,{n0},{n_max})")
        self.refresh()

    def action_l_fill(self):
        col = self._current_column()
        value, ok = QInputDialog.getText(self, "Fill", "Value or expression for the selected column:")
        if not ok:
            return
        count = max(len(self.sheet.column_values(col)), 1)
        for row in range(count):
            self.sheet.cells[(row, col)] = value
        self.sheet.recalc()
        self.refresh()

    def _sort(self, descending: bool):
        try:
            self.sheet.sort(self._current_column(), descending)
        except ValueError as exc:
            self.status.setText(str(exc))
        self.refresh()

    def action_l_sort_asc(self):
        self._sort(False)

    def action_l_sort_desc(self):
        self._sort(True)

    def action_l_quick_graph(self):
        named = [(c, n) for c, n in sorted(self.sheet.names.items())]
        if len(named) < 2 or self.graphs_page is None:
            self.status.setText("Quick Graph needs two named columns (x and y).")
            return
        labels = [f"{COLUMNS[c]}: {n}" for c, n in named]
        x_label, ok = QInputDialog.getItem(self, "Quick Graph", "x list:", labels, 0, False)
        if not ok:
            return
        y_label, ok = QInputDialog.getItem(self, "Quick Graph", "y list:", labels, 1, False)
        if not ok:
            return
        (xc, xn), (yc, yn) = named[labels.index(x_label)], named[labels.index(y_label)]
        import sympy as sp

        try:
            xs = [float(sp.N(v)) for v in self.sheet.column_values(xc)]
            ys = [float(sp.N(v)) for v in self.sheet.column_values(yc)]
        except TypeError:
            self.status.setText("Quick Graph needs numeric columns.")
            return
        n = min(len(xs), len(ys))
        self.graphs_page.add_scatter(xn, yn, xs[:n], ys[:n])
        tabs = self.parent()
        while tabs is not None and not hasattr(tabs, "setCurrentWidget"):
            tabs = tabs.parent()
        if tabs is not None:
            tabs.setCurrentWidget(self.graphs_page)
