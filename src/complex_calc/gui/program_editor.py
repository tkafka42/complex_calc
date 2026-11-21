"""Program Editor: write multi-line TI-Basic functions and programs.

Builds  Define name(params)=Func … EndFunc  or  =Prgm … EndPrgm  and stores it
in the session ("Check Syntax & Store", Ctrl+B).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..core.session import Session, normalize_name
from ..core.values import UserProgram
from ..i18n import tr

TEMPLATE_HINT = (
    "Body (one statement per line), e.g.\n"
    "Local s\ns:=0\nFor i,1,n\n  s:=s+i\nEndFor\nReturn s"
)


class ProgramEditor(QDialog):
    def __init__(self, session: Session, parent: QWidget | None = None, name: str = ""):
        super().__init__(parent)
        self.session = session
        self.setWindowTitle(tr("Program Editor"))
        self.resize(560, 520)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name_edit = QLineEdit(name)
        self.name_edit.setPlaceholderText("e.g. fact")
        self.kind_combo = QComboBox()
        self.kind_combo.addItems([tr("Function (Func)"), tr("Program (Prgm)")])
        self.params_edit = QLineEdit()
        self.params_edit.setPlaceholderText("e.g. n   or   a,b")
        form.addRow(tr("Name"), self.name_edit)
        form.addRow(tr("Type"), self.kind_combo)
        form.addRow(tr("Parameters"), self.params_edit)
        layout.addLayout(form)

        self.body = QPlainTextEdit()
        self.body.setPlaceholderText(TEMPLATE_HINT)
        font = QFont("monospace")
        font.setStyleHint(QFont.Monospace)
        self.body.setFont(font)
        layout.addWidget(self.body, 1)

        self.status = QLabel(tr("Ctrl+B: Check Syntax & Store"))
        self.status.setObjectName("Hint")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        store_button = buttons.addButton(tr("Check Syntax && Store"), QDialogButtonBox.AcceptRole)
        store_button.clicked.connect(self.store)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        QShortcut(QKeySequence("Ctrl+B"), self, activated=self.store)

        if name:
            self.load(name)

    def load(self, name: str) -> None:
        value = self.session.variables.get(normalize_name(name))
        if isinstance(value, UserProgram):
            self.kind_combo.setCurrentIndex(0 if value.kind == "func" else 1)
            self.params_edit.setText(",".join(value.params))
            self.body.setPlainText(value.source)

    def definition(self) -> str:
        name = self.name_edit.text().strip()
        kind = "Func" if self.kind_combo.currentIndex() == 0 else "Prgm"
        params = self.params_edit.text().strip()
        body = self.body.toPlainText().strip("\n")
        return f"Define {name}({params})={kind}\n{body}\nEnd{kind}"

    def store(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self.status.setText(tr("Please enter a name."))
            return
        entry = self.session.run(self.definition())
        if entry.error:
            self.status.setText(entry.text)
            self.status.setStyleSheet("color: #c2410c;")
            return
        stored = self.session.variables.get(normalize_name(name))
        if isinstance(stored, UserProgram):
            stored.source = self.body.toPlainText().strip("\n")
        self.status.setStyleSheet("")
        self.status.setText(f"Stored {name}. Run it from the Calculator page, e.g. {name}("
                            f"{self.params_edit.text().strip()}).")
        self.accept()
