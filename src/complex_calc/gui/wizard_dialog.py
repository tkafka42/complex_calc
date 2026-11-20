"""Assistant dialogs generated from complex_calc.menus.Wizard definitions."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QVBoxLayout,
    QWidget,
)

from ..menus import Wizard, WizardVariant


class MethodDialog(QDialog):
    """First step for wizards with several data input methods (Stats / Data)."""

    def __init__(self, wizard: Wizard, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(wizard.title)
        layout = QFormLayout(self)
        self.combo = QComboBox()
        self.combo.addItems(list(wizard.variants))
        layout.addRow("Data Input Method", self.combo)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def method(self) -> str:
        return self.combo.currentText()


class WizardDialog(QDialog):
    def __init__(self, title: str, variant: WizardVariant, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.variant = variant
        self.edits: dict[str, QLineEdit] = {}

        outer = QVBoxLayout(self)
        form = QFormLayout()
        outer.addLayout(form)
        for field in variant.fields:
            edit = QLineEdit(field.default)
            edit.setMinimumWidth(260)
            if not field.enabled:
                edit.setEnabled(False)
                edit.setPlaceholderText("not supported")
            elif field.optional:
                edit.setPlaceholderText("optional")
            form.addRow(field.label, edit)
            self.edits[field.key] = edit

        has_lists = any("List" in f.label for f in variant.fields)
        hint = QLabel("Lists: {1,2,3} or a list variable name." if has_lists else "∞ may be typed as inf.")
        hint.setObjectName("Hint")
        outer.addWidget(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)

        first = next((e for e in self.edits.values() if e.isEnabled()), None)
        if first is not None:
            first.setFocus()
            first.selectAll()

    def command(self) -> str:
        values = {key: edit.text() for key, edit in self.edits.items() if edit.isEnabled()}
        return self.variant.build(values)


def run_wizard(wizard: Wizard, parent: QWidget | None = None) -> str | None:
    """Show the wizard (and method chooser); return the command text or None."""
    if wizard.needs_method_choice:
        chooser = MethodDialog(wizard, parent)
        if chooser.exec() != QDialog.Accepted:
            return None
        variant = wizard.variants[chooser.method()]
    else:
        variant = next(iter(wizard.variants.values()))
    dialog = WizardDialog(wizard.title, variant, parent)
    if dialog.exec() != QDialog.Accepted:
        return None
    return dialog.command()
