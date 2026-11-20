"""Spreadsheet model for the Lists & Spreadsheet page (GUI-independent).

- 26 columns A…Z. A column may have a name: it is then a list variable shared
  with the Calculator (e.g. column "a" ↔ variable a = {1,2,3}).
- A column formula (e.g. =seq(n^2,n,1,10) or =a*2) fills the whole column.
- A cell may hold a value/expression or a cell formula such as =a1+b2
  (cell references: column letter + row number).
"""

from __future__ import annotations

import re
import string
from typing import Any

import sympy as sp

from .core.errors import CalcError
from .core.session import Session, normalize_name
from .core.values import ListValue, StringValue

COLUMNS = string.ascii_uppercase
CELL_REF = re.compile(r"\b([A-Za-z])(\d{1,4})\b")


class Sheet:
    def __init__(self, session: Session, rows: int = 200):
        self.session = session
        self.rows = rows
        self.names: dict[int, str] = {}
        self.formulas: dict[int, str] = {}
        self.cells: dict[tuple[int, int], str] = {}  # (row, col) → raw text, row starts at 0
        self.values: dict[tuple[int, int], Any] = {}
        self.errors: dict[tuple[int, int], str] = {}
        self.formula_errors: dict[int, str] = {}

    # ------------------------------------------------------------ editing
    def set_name(self, col: int, name: str) -> None:
        name = name.strip()
        old = self.names.get(col)
        if old and old != name:
            self.session.variables.pop(normalize_name(old), None)
        if name:
            if not re.fullmatch(r"[A-Za-zα-ωΑ-Ω_][\w.]*", name):
                raise ValueError("Invalid list name")
            if any(n.lower() == name.lower() and c != col for c, n in self.names.items()):
                raise ValueError(f"Name {name} is already used")
            self.names[col] = name
            existing = self.session.variables.get(normalize_name(name))
            if isinstance(existing, ListValue) and not self._column_has_data(col):
                self.load_list(col, existing)
        else:
            self.names.pop(col, None)
        self.recalc()

    def set_formula(self, col: int, formula: str) -> None:
        formula = formula.strip()
        if formula and not formula.startswith("="):
            formula = "=" + formula
        if formula:
            self.formulas[col] = formula
        else:
            self.formulas.pop(col, None)
            self.formula_errors.pop(col, None)
        self.recalc()

    def set_cell(self, row: int, col: int, text: str) -> None:
        text = text.strip()
        if col in self.formulas:
            raise ValueError("This column is defined by a column formula")
        if text:
            self.cells[(row, col)] = text
        else:
            self.cells.pop((row, col), None)
        self.recalc()

    def load_list(self, col: int, values: ListValue) -> None:
        for row in range(self.rows):
            self.cells.pop((row, col), None)
        for row, value in enumerate(values):
            self.cells[(row, col)] = self.session.format(value) if not isinstance(value, StringValue) \
                else f'"{value}"'

    def clear_column(self, col: int) -> None:
        for row in range(self.rows):
            self.cells.pop((row, col), None)
        self.formulas.pop(col, None)
        self.recalc()

    def _column_has_data(self, col: int) -> bool:
        return any(c == col for _, c in self.cells) or col in self.formulas

    # ------------------------------------------------------------ evaluation
    def column_values(self, col: int) -> list[Any]:
        out = []
        for row in range(self.rows):
            if (row, col) not in self.values:
                break
            out.append(self.values[(row, col)])
        return out

    def _replace_refs(self, text: str) -> str:
        def repl(match: re.Match) -> str:
            col = COLUMNS.index(match.group(1).upper())
            row = int(match.group(2)) - 1
            value = self.values.get((row, col))
            if value is None:
                return "0"
            return f"({self.session.format(value)})"

        return CELL_REF.sub(repl, text)

    def recalc(self) -> None:
        for _ in range(3):  # a few passes resolve dependencies between columns
            self.values.clear()
            self.errors.clear()
            for (row, col), text in sorted(self.cells.items()):
                if col in self.formulas:
                    continue
                source = self._replace_refs(text[1:]) if text.startswith("=") else text
                try:
                    self.values[(row, col)] = self.session.evaluate(source)
                except CalcError as exc:
                    self.errors[(row, col)] = exc.message
                    self.values[(row, col)] = sp.nan
            self._publish(skip=set(self.formulas))
            for col, formula in self.formulas.items():
                try:
                    result = self.session.evaluate(formula[1:])
                    items = list(result) if isinstance(result, ListValue) else [result]
                    for row, value in enumerate(items[: self.rows]):
                        self.values[(row, col)] = value
                    self.formula_errors.pop(col, None)
                    self._publish()
                except CalcError as exc:
                    self.formula_errors[col] = exc.message
            self._publish()

    def _publish(self, skip: set[int] | None = None) -> None:
        """Named columns become list variables in the session."""
        for col, name in self.names.items():
            if skip and col in skip:
                continue
            self.session.variables[normalize_name(name)] = ListValue(self.column_values(col))

    def pull_from_session(self) -> bool:
        """Copy named lists changed elsewhere (e.g. in the Calculator) into the sheet."""
        changed = False
        for col, name in self.names.items():
            if col in self.formulas:
                continue
            value = self.session.variables.get(normalize_name(name))
            if isinstance(value, ListValue) and list(value) != self.column_values(col):
                self.load_list(col, value)
                changed = True
        if changed:
            self.recalc()
        return changed

    def first_empty_column(self) -> int:
        for col in range(len(COLUMNS)):
            if col not in self.names and not self._column_has_data(col):
                return col
        raise ValueError("No empty column")

    def write_column(self, col: int, values: list[Any], name: str | None = None) -> None:
        for row in range(self.rows):
            self.cells.pop((row, col), None)
        for row, value in enumerate(values):
            if isinstance(value, StringValue):
                self.cells[(row, col)] = f'"{value}"'
            else:
                self.cells[(row, col)] = self.session.format(value)
        if name:
            self.names[col] = name
        self.recalc()

    def sort(self, col: int, descending: bool = False) -> None:
        values = self.column_values(col)
        try:
            order = sorted(range(len(values)), key=lambda k: float(sp.N(values[k])), reverse=descending)
        except TypeError:
            raise ValueError("Only numeric columns can be sorted")
        texts = [self.cells.get((k, col), "") for k in range(len(values))]
        for new_row, old_row in enumerate(order):
            self.cells[(new_row, col)] = texts[old_row]
        self.recalc()
