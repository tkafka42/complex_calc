"""2D ("pretty print") math as LaTeX for matplotlib's mathtext.

- input_latex(source, session): the typed input, from the parsed AST
  (so 1/2 is shown as a stacked fraction, √(x) with a root sign, …)
- value_latex(value, settings): a result value

Returns None when something cannot be shown in 2D; callers then fall back to
the linear text.
"""

from __future__ import annotations

import re
from typing import Any

import sympy as sp
from sympy.printing.latex import LatexPrinter

from . import parser as ast
from .formatting import format_float
from .values import ListValue, SolveResult, StringValue, TextValue, UserFunction, is_matrix

GREEK = {"π": r"\pi", "∞": r"\infty", "ℯ": r"\mathit{e}", "ⅈ": r"\mathit{i}", "θ": r"\theta"}
REL = {"=": "=", "≠": r"\neq", "<": "<", ">": ">", "≤": r"\leq", "≥": r"\geq"}
LOGIC = {"and": r"\ \mathrm{and}\ ", "or": r"\ \mathrm{or}\ ", "xor": r"\ \mathrm{xor}\ ",
         "nor": r"\ \mathrm{nor}\ ", "nand": r"\ \mathrm{nand}\ ", "⇒": r"\Rightarrow", "⇔": r"\Leftrightarrow"}
_SAFE_TEXT = re.compile(r"[^\w.\-]")


def _text(name: str) -> str:
    if name in GREEK:
        return GREEK[name]
    escaped = name.replace("_", r"\_").replace("\\", r"\backslash ").replace("#", r"\#").replace("%", r"\%")
    if len(name) == 1:
        return escaped
    return r"\mathrm{" + escaped + "}"


# ------------------------------------------------------------------ input (AST)

_PREC = {"+": 1, "-": 1, ".+": 1, ".-": 1, "*": 2, "/": 2, ".*": 2, "./": 2, "&": 3, "^": 5, ".^": 5}


def _prec(node: ast.Node) -> int:
    if isinstance(node, ast.BinOp):
        return _PREC.get(node.op, 4)
    if isinstance(node, ast.Neg):
        return 1
    if isinstance(node, (ast.Relation, ast.Logic, ast.With, ast.Not, ast.Convert)):
        return 0
    return 9


def _wrap(node: ast.Node, minimum: int) -> str:
    inner = node_latex(node)
    return r"\left(" + inner + r"\right)" if _prec(node) < minimum else inner


def _args(nodes: list[ast.Node]) -> str:
    return ",".join(node_latex(a) for a in nodes)


def node_latex(node: ast.Node) -> str:
    if isinstance(node, ast.Num):
        text = node.text
        if "E" in text:
            mantissa, exponent = text.split("E")
            return f"{mantissa}" + r"\cdot 10^{" + exponent + "}"
        return text
    if isinstance(node, ast.Str):
        raise ValueError("strings are shown linear")
    if isinstance(node, ast.Name):
        return _text(node.name)
    if isinstance(node, ast.Void):
        return ""
    if isinstance(node, ast.Neg):
        return "-" + _wrap(node.operand, 2)
    if isinstance(node, ast.BinOp):
        op = node.op
        if op in ("/", "./") and op == "/":
            return r"\frac{" + node_latex(node.left) + "}{" + node_latex(node.right) + "}"
        if op in ("^", ".^"):
            base = _wrap(node.left, 6)
            return base + ("" if op == "^" else r"\!.") + "^{" + node_latex(node.right) + "}"
        p = _PREC[op]
        symbol = {"*": r"\cdot ", ".*": r".\!\cdot ", "./": "./", "&": r"\&", "+": "+", "-": "-",
                  ".+": ".+", ".-": ".-"}[op]
        right_min = p + 1 if op in ("-", "/", ".-") else p
        return _wrap(node.left, p) + symbol + _wrap(node.right, right_min)
    if isinstance(node, ast.Postfix):
        symbol = {"!": "!", "%": r"\%", "°": r"^{\circ}", "'": "'", "″": "''", "ʳ": "^{r}", "ᵍ": "^{g}",
                  "ᵀ": "^{T}", "∠": r"\angle "}[node.op]
        if node.op == "∠":
            return symbol + node_latex(node.operand)
        return _wrap(node.operand, 9) + symbol
    if isinstance(node, ast.Subscript):
        return _wrap(node.operand, 9) + r"\left[" + _args(node.indices) + r"\right]"
    if isinstance(node, ast.Indirection):
        return r"\#" + _wrap(node.operand, 9)
    if isinstance(node, ast.Relation):
        return node_latex(node.left) + REL[node.op] + node_latex(node.right)
    if isinstance(node, ast.Logic):
        return LOGIC[node.op].join(node_latex(i) for i in node.items)
    if isinstance(node, ast.Not):
        return r"\mathrm{not}\ " + node_latex(node.operand)
    if isinstance(node, ast.With):
        return node_latex(node.expr) + r"\ \mid\ " + node_latex(node.condition)
    if isinstance(node, ast.Convert):
        target = node_latex(node.target_node) if node.target_node is not None else _text(node.target)
        args = r"\left(" + _args(node.args) + r"\right)" if node.args else ""
        return node_latex(node.operand) + r"\blacktriangleright " + target + args
    if isinstance(node, ast.Polar):
        return r"\left(" + node_latex(node.magnitude) + r"\angle " + node_latex(node.angle) + r"\right)"
    if isinstance(node, ast.ListLit):
        return r"\left\{" + _args(node.items) + r"\right\}"
    if isinstance(node, ast.MatrixLit):
        return r"\left[" + ";".join(_args(row) for row in node.rows) + r"\right]"
    if isinstance(node, ast.Call):
        return _call_latex(node)
    raise ValueError("no 2D form")


def _call_latex(node: ast.Call) -> str:
    name, args = node.name, node.args
    lower = name.lower()
    if name == "√" and len(args) == 1:
        return r"\sqrt{" + node_latex(args[0]) + "}"
    if lower == "root" and len(args) == 2:
        return r"\sqrt[" + node_latex(args[1]) + "]{" + node_latex(args[0]) + "}"
    if lower == "abs" and len(args) == 1:
        return r"\left|" + node_latex(args[0]) + r"\right|"
    if lower == "log" and len(args) == 2:
        return r"\log_{" + node_latex(args[1]) + r"}\left(" + node_latex(args[0]) + r"\right)"
    if lower == "log" and len(args) == 1:
        return r"\log_{10}\left(" + node_latex(args[0]) + r"\right)"
    if name == "∫" and len(args) in (2, 4):
        var = node_latex(args[1])
        limits = "_{" + node_latex(args[2]) + "}^{" + node_latex(args[3]) + "}" if len(args) == 4 else ""
        return r"\int" + limits + " " + _wrap(args[0], 2) + r"\,d" + var
    if lower == "d" and len(args) in (2, 3):
        var = node_latex(args[1])
        order = "^{" + node_latex(args[2]) + "}" if len(args) == 3 else ""
        return r"\frac{d" + order + "}{d" + var + order + r"}\left(" + node_latex(args[0]) + r"\right)"
    if name in ("Σ", "Π") and len(args) == 4:
        big = r"\sum" if name == "Σ" else r"\prod"
        return big + "_{" + node_latex(args[1]) + "=" + node_latex(args[2]) + "}^{" + node_latex(args[3]) + "}" \
            + _wrap(args[0], 2)
    if lower == "limit" and len(args) in (3, 4):
        return r"\lim_{" + node_latex(args[1]) + r"\to " + node_latex(args[2]) + "}" + _wrap(args[0], 2)
    return _text(name) + r"\left(" + _args(args) + r"\right)"


def statement_latex(node: ast.Node) -> str:
    if isinstance(node, ast.ExprStmt):
        text = node_latex(node.expr)
        if node.store_to is not None:
            text += r"\rightarrow " + node_latex(node.store_to)
        return text
    if isinstance(node, ast.DefineStmt) and node.body is not None:
        head = _text(node.name)
        if node.params is not None:
            head += r"\left(" + ",".join(_text(p) for p in node.params) + r"\right)"
        if node.show_value:
            return head + ":=" + node_latex(node.body)
        return r"\mathrm{Define}\ " + head + "=" + node_latex(node.body)
    if isinstance(node, ast.CommandStmt):
        return _text(node.name) + r"\ " + _args(node.args)
    if isinstance(node, ast.DelVarStmt):
        return r"\mathrm{DelVar}\ " + ",".join(_text(n) for n in node.names)
    raise ValueError("no 2D form")


def input_latex(source: str, session) -> str | None:
    if "\n" in source or len(source) > 160:
        return None
    try:
        statements = ast.parse(source, session.is_function, session.is_command)
        if len(statements) != 1:
            return None
        return statement_latex(statements[0])
    except Exception:  # noqa: BLE001 - fall back to linear text
        return None


# ------------------------------------------------------------------ results


class _Printer(LatexPrinter):
    def __init__(self, digits):
        super().__init__({"imaginary_unit": "i", "mul_symbol": "dot", "inv_trig_style": "power",
                          "ln_notation": True})
        self.digits = digits

    def _print_Float(self, expr):
        text = format_float(float(expr), self.digits)
        if "E" in text:
            mantissa, exponent = text.split("E")
            return mantissa + r"\cdot 10^{" + exponent + "}"
        return text

    def _print_ImaginaryUnit(self, expr):
        return r"\mathit{i}"

    def _print_Exp1(self, expr):
        return r"\mathit{e}"

    def _print_exp(self, expr, exp=None):
        tex = r"\mathit{e}^{" + self._print(expr.args[0]) + "}"
        return tex if exp is None else r"\left(" + tex + r"\right)^{" + exp + "}"

    def _print_Symbol(self, expr, style="plain"):
        return _text(expr.name)

    def _print_NaN(self, expr):
        return r"\mathrm{undef}"

    def _print_ComplexInfinity(self, expr):
        return r"\mathrm{undef}"

    def _print_BooleanTrue(self, expr):
        return r"\mathrm{true}"

    def _print_BooleanFalse(self, expr):
        return r"\mathrm{false}"


def _clean(tex: str) -> str:
    tex = tex.replace(r"\limits", "").replace(r"\operatorname", r"\mathrm")
    tex = tex.replace(r"\left[\begin{matrix}", "").replace(r"\end{matrix}\right]", "")
    return tex


def expr_latex(expr: Any, digits) -> str:
    return _clean(_Printer(digits).doprint(expr))


def value_latex(value: Any, digits) -> str | None:
    try:
        if isinstance(value, (TextValue, StringValue, UserFunction)) or value is None or is_matrix(value):
            return None
        if isinstance(value, ListValue):
            parts = [value_latex(v, digits) for v in value]
            if any(p is None for p in parts) or len(value) > 12:
                return None
            return r"\left\{" + ",".join(parts) + r"\right\}"
        if isinstance(value, SolveResult):
            if value.intervals or value.always_true:
                return None
            pieces = [r"\ \mathrm{and}\ ".join(f"{expr_latex(v, digits)}={expr_latex(x, digits)}" for v, x in alt)
                      for alt in value.alternatives]
            pieces += [f"{expr_latex(v, digits)}={expr_latex(x, digits)}" for v, x in value.general]
            return r"\ \mathrm{or}\ ".join(pieces) if pieces else r"\mathrm{false}"
        if isinstance(value, sp.Basic):
            tex = expr_latex(value, digits)
            return tex if len(tex) < 400 else None
    except Exception:  # noqa: BLE001
        return None
    return None
