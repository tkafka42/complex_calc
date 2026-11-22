"""Catalog (Ctrl+K): every command and function A–Z with syntax help, and the
template palette (fraction, root, integral, matrix, …)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..functions.registry import REGISTRY
from ..i18n import tr

KEYWORDS = {
    "Define": "Define Var=Expr  |  Define Function(Param1,…)=Expr  |  …=Func … EndFunc  |  …=Prgm … EndPrgm",
    "DelVar": "DelVar Var1[,Var2]…", "CopyVar": "CopyVar Var1,Var2", "Local": "Local Var1[,Var2]…",
    "If": "If BooleanExpr Then … [ElseIf … Then …] [Else …] EndIf", "For": "For Var,Low,High[,Step] … EndFor",
    "While": "While Condition … EndWhile", "Loop": "Loop … EndLoop", "Try": "Try … Else … EndTry",
    "Return": "Return [Expr]", "Exit": "Exit", "Cycle": "Cycle", "Stop": "Stop", "Lbl": "Lbl labelName",
    "Goto": "Goto labelName", "ClrErr": "ClrErr", "PassErr": "PassErr", "Func": "Func … EndFunc",
    "Prgm": "Prgm … EndPrgm", "and": "BooleanExpr1 and BooleanExpr2", "or": "BooleanExpr1 or BooleanExpr2",
    "xor": "BooleanExpr1 xor BooleanExpr2", "not": "not BooleanExpr", "nand": "BooleanExpr1 nand BooleanExpr2",
    "nor": "BooleanExpr1 nor BooleanExpr2",
}


def catalog_entries() -> list[tuple[str, str, str, bool]]:
    """(name, signature, summary, is_command) sorted A–Z like the catalog."""
    seen = {}
    for spec in REGISTRY.values():
        seen[spec.name] = (spec.name, spec.signature, spec.summary, spec.command)
    for name, signature in KEYWORDS.items():
        seen.setdefault(name, (name, signature, "", True))
    return sorted(seen.values(), key=lambda e: e[0].lstrip("ΔΣΠχ►∫√").lower() or e[0])


class CatalogDialog(QDialog):
    inserted = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(tr("Catalog"))
        self.resize(520, 560)
        layout = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("Search"))
        self.search.textChanged.connect(self._filter)
        layout.addWidget(self.search)
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._show_help)
        self.list.itemActivated.connect(lambda item: self._insert())
        layout.addWidget(self.list, 1)
        self.help = QLabel()
        self.help.setWordWrap(True)
        self.help.setObjectName("Hint")
        self.help.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.help)
        buttons = QDialogButtonBox()
        insert = buttons.addButton(tr("Insert into entry line"), QDialogButtonBox.AcceptRole)
        insert.clicked.connect(self._insert)
        buttons.addButton(tr("Close"), QDialogButtonBox.RejectRole).clicked.connect(self.reject)
        layout.addWidget(buttons)
        self.entries = catalog_entries()
        self._filter("")
        self.search.setFocus()

    def _filter(self, text: str):
        self.list.clear()
        needle = text.strip().lower()
        entries = self.entries
        if needle:  # names starting with the search text first, as in the catalog
            entries = sorted((e for e in entries if needle in e[0].lower() or needle in e[2].lower()),
                             key=lambda e: (not e[0].lower().startswith(needle), needle not in e[0].lower(),
                                            e[0].lower()))
        for name, signature, summary, command in entries:
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, (name, signature, summary, command))
            self.list.addItem(item)
        if self.list.count():
            self.list.setCurrentRow(0)

    def _show_help(self, item, _previous=None):
        if item is None:
            self.help.setText("")
            return
        name, signature, summary, _ = item.data(Qt.UserRole)
        self.help.setText(f"<b>{signature}</b><br>{summary}")

    def keyPressEvent(self, event):  # noqa: N802 - arrow keys move in the list while typing
        if event.key() in (Qt.Key_Up, Qt.Key_Down):
            self.list.keyPressEvent(event)
            return
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._insert()
            return
        super().keyPressEvent(event)

    def _insert(self):
        item = self.list.currentItem()
        if item is None:
            return
        name, _, _, command = item.data(Qt.UserRole)
        self.inserted.emit(name + (" " if command else "("))
        self.accept()


# (label shown on the button, text inserted, cursor offset from the start)
TEMPLATES = [
    ("□/□", "()/()", 1), ("□^□", "^()", 2), ("√□", "√()", 2), ("ⁿ√□", "root(,)", 5),
    ("ℯ^□", "ℯ^()", 3), ("log□(□)", "log(,)", 4), ("|□|", "abs()", 4), ("{ □,□ }", "piecewise(,,,)", 10),
    ("{ = , = }", "system(,)", 7), ("[□ □;□ □]", "[,;,]", 1), ("[□ □]", "[,]", 1), ("[□;□]", "[;]", 1),
    ("Σ□", "Σ(,,,)", 2), ("Π□", "Π(,,,)", 2), ("d/d□", "d(,)", 2), ("d²/d□²", "d(,,2)", 2),
    ("∫□d□", "∫(,)", 2), ("∫ₐᵇ□d□", "∫(,,,)", 2), ("lim □", "limit(,,)", 6), ("□°□'□″", "°'″", 0),
]


class TemplatePalette(QDialog):
    chosen = Signal(str, int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent, Qt.Popup)
        self.setObjectName("TemplatePalette")
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAutoFillBackground(True)
        grid = QGridLayout(self)
        grid.setSpacing(4)
        for k, (label, text, offset) in enumerate(TEMPLATES):
            button = QPushButton(label)
            button.setObjectName("Symbol")
            button.setMinimumWidth(78)
            button.clicked.connect(lambda checked=False, t=text, o=offset: self._choose(t, o))
            grid.addWidget(button, k // 5, k % 5)

    def _choose(self, text: str, offset: int):
        self.chosen.emit(text, offset)
        self.close()
