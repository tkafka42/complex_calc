"""Turn results into linear text in handheld style.

Examples: ``x^2+4·x+13``, ``x=-2 or x=3``, ``{1,2,3}``, ``0.97725``, ``3.``
(an approximate integer keeps its trailing dot like on the handheld).
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

import sympy as sp
from sympy.printing.str import StrPrinter

from .values import ListValue, SolveResult, StatResults, TextValue, UserFunction


def display_width(text: str) -> int:
    """Length ignoring combining marks (x̄ is one column wide)."""
    return sum(1 for c in text if not unicodedata.combining(c))


def format_float(value: float, digits: int = 6) -> str:
    if value != value:  # NaN
        return "undef"
    if value in (float("inf"), float("-inf")):
        return "∞" if value > 0 else "-∞"
    if value == 0:
        return "0."
    text = f"{value:.{digits}g}"
    if "e" in text:
        mantissa, exponent = text.split("e")
        if "." not in mantissa:
            mantissa += "."
        return f"{mantissa}E{int(exponent)}"
    if "." not in text:
        text += "."
    return text


class CalcPrinter(StrPrinter):
    def __init__(self, digits: int = 6):
        super().__init__({"order": None})
        self.digits = digits

    def _print_Float(self, expr):
        return format_float(float(expr), self.digits)

    def _print_ImaginaryUnit(self, expr):
        return "i"

    def _print_Exp1(self, expr):
        return "e"

    def _print_Pi(self, expr):
        return "π"

    def _print_Infinity(self, expr):
        return "∞"

    def _print_NegativeInfinity(self, expr):
        return "-∞"

    def _print_ComplexInfinity(self, expr):
        return "undef"

    def _print_NaN(self, expr):
        return "undef"

    def _print_BooleanTrue(self, expr):
        return "true"

    def _print_BooleanFalse(self, expr):
        return "false"

    def _print_exp(self, expr):
        arg = self._print(expr.args[0])
        if re.fullmatch(r"[\w.]+", arg):
            return f"e^{arg}"
        return f"e^({arg})"

    def _print_log(self, expr):
        if len(expr.args) == 2:
            return f"log({self._print(expr.args[0])},{self._print(expr.args[1])})"
        return f"ln({self._print(expr.args[0])})"

    def _print_Abs(self, expr):
        return f"|{self._print(expr.args[0])}|"

    def _print_asin(self, expr):
        return f"sin⁻¹({self._print(expr.args[0])})"

    def _print_acos(self, expr):
        return f"cos⁻¹({self._print(expr.args[0])})"

    def _print_atan(self, expr):
        return f"tan⁻¹({self._print(expr.args[0])})"

    def _print_Pow(self, expr, rational=False):
        base, exponent = expr.args
        if exponent == sp.Rational(1, 2):
            return f"√({self._print(base)})"
        if exponent == sp.Rational(-1, 2):
            return f"1/√({self._print(base)})"
        return super()._print_Pow(expr, rational)

    def _print_Relational(self, expr):
        symbols = {"==": "=", "!=": "≠", "<": "<", ">": ">", "<=": "≤", ">=": "≥"}
        return f"{self._print(expr.lhs)}{symbols[expr.rel_op]}{self._print(expr.rhs)}"

    def _print_And(self, expr):
        return " and ".join(self._print(a) for a in expr.args)

    def _print_Or(self, expr):
        return " or ".join(self._print(a) for a in expr.args)

    def _print_Not(self, expr):
        return f"not {self._print(expr.args[0])}"

    def _print_factorial(self, expr):
        arg = self._print(expr.args[0])
        return f"{arg}!" if re.fullmatch(r"\w+", arg) else f"({arg})!"

    def _print_binomial(self, expr):
        return f"nCr({self._print(expr.args[0])},{self._print(expr.args[1])})"


def _tidy(text: str) -> str:
    text = text.replace("**", "^").replace("*", "·")
    text = text.replace(" + ", "+").replace(" - ", "-").replace(", ", ",")
    text = text.replace("+-", "-")
    return text


def format_expr(expr: Any, digits: int = 6) -> str:
    if isinstance(expr, bool):
        return "true" if expr else "false"
    if isinstance(expr, float):
        return format_float(expr, digits)
    if isinstance(expr, int):
        return str(expr)
    return _tidy(CalcPrinter(digits).doprint(expr))


def _format_interval(var: sp.Symbol, interval: sp.Interval, digits: int) -> str:
    name = format_expr(var, digits)
    lo, hi = interval.start, interval.end
    lo_text, hi_text = format_expr(lo, digits), format_expr(hi, digits)
    left = "<" if interval.left_open else "≤"
    right = "<" if interval.right_open else "≤"
    if lo == -sp.oo and hi == sp.oo:
        return "true"
    if lo == -sp.oo:
        return f"{name}{right}{hi_text}"
    if hi == sp.oo:
        return f"{name}{'>' if interval.left_open else '≥'}{lo_text}"
    return f"{lo_text}{left}{name}{right}{hi_text}"


def format_solve_result(result: SolveResult, digits: int = 6) -> str:
    if result.always_true:
        return "true"
    parts = [
        " and ".join(f"{format_expr(var, digits)}={format_expr(value, digits)}" for var, value in alt)
        for alt in result.alternatives
    ]
    parts += [f"{format_expr(var, digits)}={format_expr(value, digits)}" for var, value in result.general]
    parts += [_format_interval(var, iv, digits) for var, iv in (result.intervals or [])]
    if not parts:
        return "false"
    return " or ".join(parts)


def stat_table(results: StatResults, digits: int = 6) -> list[tuple[str, str]]:
    """Rows as shown in the handheld stat.results table (labels in quotes)."""
    rows = [('"Title"', f'"{results.title}"')]
    for label, value in results.rows:
        rows.append((f'"{label}"', format_value(value, digits)))
    return rows


def format_value(value: Any, digits: int = 6) -> str:
    if value is None:
        return ""
    if isinstance(value, TextValue):
        return f'"{value.text}"' if value.text not in ("Done",) else value.text
    if isinstance(value, ListValue):
        return "{" + ",".join(format_value(v, digits) for v in value) + "}"
    if isinstance(value, SolveResult):
        return format_solve_result(value, digits)
    if isinstance(value, StatResults):
        rows = stat_table(value, digits)
        width = max(display_width(label) for label, _ in rows)
        return "\n".join(f"{label}{' ' * (width - display_width(label))}  {text}" for label, text in rows)
    if isinstance(value, UserFunction):
        params = ",".join(p.name for p in value.params)
        return f"{value.name}({params})={format_expr(value.body, digits)}"
    return format_expr(value, digits)
