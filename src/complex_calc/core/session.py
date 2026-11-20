"""Session: variables, settings and evaluation of parsed input.

Used by both the CLI REPL and the GUI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import sympy as sp

from .. import functions  # noqa: F401  (registers all built-ins)
from ..functions.registry import Builtin, Context, lookup_builtin
from . import parser as ast
from .errors import ArgumentError, CalcError, EvaluationError, UndefinedError
from .formatting import format_value
from .values import ListValue, SolveResult, StatResults, TextValue, UserFunction

CONSTANTS: dict[str, Any] = {
    "π": sp.pi,
    "pi": sp.pi,
    "ℯ": sp.E,
    "e": sp.E,
    "ⅈ": sp.I,
    "i": sp.I,
    "∞": sp.oo,
    "infinity": sp.oo,
    "inf": sp.oo,
    "true": sp.true,
    "false": sp.false,
    "undef": sp.nan,
}

RESERVED = {"π", "pi", "ℯ", "e", "ⅈ", "i", "∞", "infinity", "inf", "true", "false", "undef", "ans"}


def normalize_name(name: str) -> str:
    """Variable names are case-insensitive (ASCII letters only, so Σ ≠ σ)."""
    return "".join(c.lower() if c.isascii() else c for c in name)


@dataclass
class Settings:
    angle: str = "rad"  # "rad" | "deg"
    mode: str = "auto"  # "auto" | "exact" | "approx"
    digits: int = 6  # Float 6


@dataclass
class Entry:
    source: str
    text: str
    value: Any = None
    error: bool = False


@dataclass
class Session:
    settings: Settings = field(default_factory=Settings)
    variables: dict[str, Any] = field(default_factory=dict)
    history: list[Entry] = field(default_factory=list)

    # ------------------------------------------------------------ parser hooks
    def is_function(self, name: str) -> bool:
        spec = lookup_builtin(name)
        if spec is not None and not spec.command:
            return True
        return isinstance(self.variables.get(normalize_name(name)), UserFunction)

    def is_command(self, name: str) -> bool:
        spec = lookup_builtin(name)
        return spec is not None and spec.command

    # ------------------------------------------------------------ public API
    def evaluate(self, source: str, force_approx: bool = False) -> Any:
        """Parse and evaluate `source`; raises CalcError on failure."""
        statements = ast.parse(source, self.is_function, self.is_command)
        result = None
        for statement in statements:
            result = _Evaluator(self, force_approx).run_statement(statement)
        return result

    def run(self, source: str, force_approx: bool = False) -> Entry:
        """Evaluate and record in the history; never raises CalcError."""
        try:
            value = self.evaluate(source, force_approx)
            entry = Entry(source, self.format(value), value)
        except CalcError as exc:
            entry = Entry(source, exc.user_message(source), None, error=True)
        except RecursionError:
            entry = Entry(source, "Error: Expression too deeply nested", None, error=True)
        except (TypeError, ValueError, ZeroDivisionError, NotImplementedError, AttributeError) as exc:
            entry = Entry(source, f"Error: {exc}", None, error=True)
        self.history.append(entry)
        return entry

    def format(self, value: Any) -> str:
        return format_value(value, self.settings.digits)

    def store(self, name: str, value: Any) -> None:
        key = normalize_name(name)
        if key in RESERVED or (lookup_builtin(key) is not None and not key.startswith("stat.")):
            raise ArgumentError(f"'{name}' is a reserved name")
        if isinstance(value, UserFunction):
            value = UserFunction(name, value.params, value.body)
        self.variables[key] = value

    def delete(self, name: str) -> None:
        self.variables.pop(normalize_name(name), None)

    def clear_variables(self) -> None:
        self.variables.clear()


class _Evaluator:
    def __init__(self, session: Session, force_approx: bool):
        self.session = session
        self.settings = session.settings
        self.force_approx = force_approx
        self.saw_decimal = False
        self.ctx = Context(settings=self.settings, store=session.store, lookup=self.lookup_variable)

    # ------------------------------------------------------------ statements
    def run_statement(self, node: ast.Node) -> Any:
        if isinstance(node, ast.ExprStmt):
            value = self.finalize(self.eval(node.expr, frozenset()))
            if isinstance(value, StatResults):
                return value
            if node.store_to:
                self.session.store(node.store_to, value)
            self.session.variables["ans"] = value
            return value

        if isinstance(node, ast.DefineStmt):
            if node.params is None:
                value = self.finalize(self.eval(node.body, frozenset()))
                self.session.store(node.name, value)
                return value if node.show_value else TextValue("Done")
            params = [normalize_name(p) for p in node.params]
            body = self.finalize(self.eval(node.body, frozenset(params)))
            self.session.store(node.name, UserFunction(node.name, [sp.Symbol(p) for p in params], body))
            return TextValue("Done")

        if isinstance(node, ast.DelVarStmt):
            for name in node.names:
                self.session.delete(name)
            return TextValue("Done")

        if isinstance(node, ast.CopyVarStmt):
            value = self.lookup_variable(node.source)
            if value is None:
                raise UndefinedError(f"Variable '{node.source}' is not defined")
            self.session.store(node.target, value)
            return TextValue("Done")

        if isinstance(node, ast.CommandStmt):
            spec = lookup_builtin(node.name)
            assert spec is not None
            result = self.call_builtin(spec, node.args, frozenset())
            if isinstance(result, StatResults):
                for key, value in result.variables.items():
                    self.session.variables[normalize_name(f"stat.{key}")] = value
            return result

        raise EvaluationError("Unknown statement")

    # ------------------------------------------------------------ helpers
    def lookup_variable(self, name: str) -> Any:
        return self.session.variables.get(normalize_name(name))

    def numeric(self, value: Any) -> Any:
        if isinstance(value, ListValue):
            return ListValue(self.numeric(v) for v in value)
        if isinstance(value, SolveResult):
            return SolveResult(
                alternatives=[[(s, self.numeric(v)) for s, v in alt] for alt in value.alternatives],
                intervals=[(s, iv) for s, iv in value.intervals] if value.intervals else None,
                always_true=value.always_true,
                general=[(s, self.numeric(v)) for s, v in value.general],
            )
        if isinstance(value, UserFunction):
            return UserFunction(value.name, value.params, self.numeric(value.body))
        if isinstance(value, sp.Basic) and not isinstance(value, sp.logic.boolalg.BooleanAtom):
            try:
                return value.evalf(15, chop=True)
            except (TypeError, ValueError, AttributeError):
                return value
        return value

    def finalize(self, value: Any) -> Any:
        mode = self.settings.mode
        if self.force_approx or mode == "approx" or (mode == "auto" and self.saw_decimal):
            return self.numeric(value)
        return value

    # ------------------------------------------------------------ expressions
    def eval(self, node: ast.Node, exclude: frozenset[str]) -> Any:
        method = getattr(self, f"eval_{type(node).__name__}", None)
        if method is None:
            raise EvaluationError(f"Cannot evaluate {type(node).__name__}")
        try:
            return method(node, exclude)
        except CalcError as exc:
            if exc.position is None:
                exc.position = node.pos
            raise

    def eval_Num(self, node: ast.Num, exclude) -> Any:
        text = node.text
        if "." in text or "E" in text:
            if self.settings.mode == "exact":
                return sp.Rational(text)
            self.saw_decimal = True
            return sp.Float(text, 15)
        return sp.Integer(text)

    def eval_Name(self, node: ast.Name, exclude) -> Any:
        key = normalize_name(node.name)
        if key in exclude:
            return sp.Symbol(key)
        if node.name in ("π", "ℯ", "ⅈ", "∞"):
            return CONSTANTS[node.name]
        if key in self.session.variables:
            value = self.session.variables[key]
            if isinstance(value, UserFunction):
                raise ArgumentError(f"{node.name} is a function; call it like {node.name}(x)")
            return value
        if key in CONSTANTS:
            return CONSTANTS[key]
        if key == "ans":
            raise UndefinedError("No previous answer")
        if lookup_builtin(key) is not None:
            raise ArgumentError(f"Missing '(' after {node.name}")
        if key.startswith("stat."):
            raise UndefinedError(f"{node.name} is not defined (run a statistics command first)")
        return sp.Symbol(key)

    def eval_ListLit(self, node: ast.ListLit, exclude) -> Any:
        return ListValue(self.eval(item, exclude) for item in node.items)

    def eval_Neg(self, node: ast.Neg, exclude) -> Any:
        return self.arith("*", sp.Integer(-1), self.eval(node.operand, exclude))

    def eval_BinOp(self, node: ast.BinOp, exclude) -> Any:
        return self.arith(node.op, self.eval(node.left, exclude), self.eval(node.right, exclude))

    def arith(self, op: str, a: Any, b: Any) -> Any:
        if isinstance(a, ListValue) or isinstance(b, ListValue):
            if isinstance(a, ListValue) and isinstance(b, ListValue):
                if len(a) != len(b):
                    raise ArgumentError("Dimension mismatch")
                return ListValue(self.arith(op, x, y) for x, y in zip(a, b))
            if isinstance(a, ListValue):
                return ListValue(self.arith(op, x, b) for x in a)
            return ListValue(self.arith(op, a, y) for y in b)
        for operand in (a, b):
            if not isinstance(operand, sp.Basic) or isinstance(operand, sp.logic.boolalg.Boolean) and not isinstance(operand, sp.Expr):
                raise ArgumentError("Arithmetic is only possible with numbers and expressions")
        if op == "+":
            return a + b
        if op == "-":
            return a - b
        if op == "*":
            return a * b
        if op == "/":
            return a / b
        if op == "^":
            return a**b
        raise EvaluationError(f"Unknown operator {op}")

    def eval_Postfix(self, node: ast.Postfix, exclude) -> Any:
        value = self.eval(node.operand, exclude)
        if isinstance(value, ListValue):
            return ListValue(self._postfix(node.op, v) for v in value)
        return self._postfix(node.op, value)

    def _postfix(self, op: str, value: Any) -> Any:
        if op == "!":
            if value.is_number and (value.is_negative or not value.is_integer):
                if value.is_negative:
                    raise ArgumentError("Factorial needs a non-negative integer")
            return sp.factorial(value)
        # degree sign: value in degrees, converted to the current angle unit
        return value if self.settings.angle == "deg" else value * sp.pi / 180

    def eval_Relation(self, node: ast.Relation, exclude) -> Any:
        left, right = self.eval(node.left, exclude), self.eval(node.right, exclude)
        if isinstance(left, ListValue) or isinstance(right, ListValue):
            raise ArgumentError("Relations between lists are not supported")
        builders = {"=": sp.Eq, "≠": sp.Ne, "<": sp.Lt, ">": sp.Gt, "≤": sp.Le, "≥": sp.Ge}
        try:
            return builders[node.op](left, right)
        except TypeError as exc:
            raise EvaluationError(f"Invalid comparison: {exc}")

    def eval_Logic(self, node: ast.Logic, exclude) -> Any:
        items = [self.eval(item, exclude) for item in node.items]
        try:
            if node.op == "and":
                return sp.And(*items)
            if node.op == "or":
                return sp.Or(*items)
            return sp.Xor(*items)
        except TypeError:
            raise ArgumentError(f"'{node.op}' needs conditions such as x>1 or x=2")

    def eval_Not(self, node: ast.Not, exclude) -> Any:
        return sp.Not(self.eval(node.operand, exclude))

    # ------------------------------------------------------------ "with" operator |
    def eval_With(self, node: ast.With, exclude) -> Any:
        conditions = node.condition.items if isinstance(node.condition, ast.Logic) and node.condition.op == "and" \
            else [node.condition]
        substitutions: dict[str, Any] = {}
        filters: list[ast.Node] = []
        for cond in conditions:
            if isinstance(cond, ast.Relation) and cond.op == "=" and isinstance(cond.left, ast.Name):
                substitutions[normalize_name(cond.left.name)] = self.eval(cond.right, exclude)
            else:
                filters.append(cond)
        filter_names = frozenset(n for f in filters for n in _names_in(f))
        inner_exclude = exclude | frozenset(substitutions) | filter_names
        value = self.eval(node.expr, inner_exclude)
        mapping = {sp.Symbol(k): v for k, v in substitutions.items()}
        filter_exprs = [self.eval(f, exclude | filter_names) for f in filters]
        return self._apply_with(value, mapping, filter_exprs)

    def _apply_with(self, value: Any, mapping: dict, filters: list) -> Any:
        if isinstance(value, ListValue):
            return ListValue(self._apply_with(v, mapping, filters) for v in value)
        if isinstance(value, SolveResult):
            return _filter_solutions(value, mapping, filters)
        if isinstance(value, sp.Basic):
            result = value.subs(mapping) if mapping else value
            return result.doit() if hasattr(result, "doit") else result
        raise ArgumentError("'|' cannot be applied to this result")

    # ------------------------------------------------------------ calls
    def eval_Call(self, node: ast.Call, exclude) -> Any:
        key = normalize_name(node.name)
        user = self.session.variables.get(key)
        if isinstance(user, UserFunction):
            args = [self.eval(a, exclude) for a in node.args]
            if len(args) == 1 and isinstance(args[0], ListValue) and len(user.params) == 1:
                return ListValue(user.call([v]) for v in args[0])
            return user.call(args)
        spec = lookup_builtin(node.name)
        if spec is None:
            raise UndefinedError(f"Unknown function {node.name}")
        if spec.command:
            raise ArgumentError(f"{spec.name} is a command without parentheses: {spec.signature}")
        return self.call_builtin(spec, node.args, exclude)

    def call_builtin(self, spec: Builtin, arg_nodes: list[ast.Node], exclude: frozenset[str]) -> Any:
        count = len(arg_nodes)
        if count < spec.min_args:
            raise ArgumentError(f"Too few arguments. Syntax: {spec.signature}")
        if spec.max_args is not None and count > spec.max_args:
            raise ArgumentError(f"Too many arguments. Syntax: {spec.signature}")

        held: set[str] = set()
        for index in spec.hold:
            if index < count:
                held |= _held_names(arg_nodes[index])
        inner_exclude = exclude | frozenset(held)
        args = []
        for index, node in enumerate(arg_nodes):
            if index in spec.hold:
                args.append(self.eval_held(node, inner_exclude))
            else:
                args.append(self.eval(node, inner_exclude))

        decimal_before = self.saw_decimal
        result = self._apply(spec, args)
        if spec.approx:
            result = self.numeric(result)
        if spec.exact:
            self.saw_decimal = False
        return result

    def _apply(self, spec: Builtin, args: list[Any]) -> Any:
        list_positions = [i for i in spec.listable if i < len(args) and isinstance(args[i], ListValue)]
        if list_positions:
            lengths = {len(args[i]) for i in list_positions}
            if len(lengths) > 1:
                raise ArgumentError("Dimension mismatch")
            size = lengths.pop()
            results = []
            for k in range(size):
                call_args = [a[k] if i in list_positions else a for i, a in enumerate(args)]
                results.append(self._apply(spec, call_args))
            return ListValue(results)
        try:
            return spec.func(self.ctx, *args)
        except CalcError:
            raise
        except (TypeError, ValueError, NotImplementedError, ZeroDivisionError, AttributeError) as exc:
            raise EvaluationError(f"{spec.name}: {exc}")

    def eval_held(self, node: ast.Node, exclude: frozenset[str]) -> Any:
        if isinstance(node, ast.Name):
            return sp.Symbol(normalize_name(node.name))
        if isinstance(node, ast.Relation) and node.op == "=" and isinstance(node.left, ast.Name):
            return sp.Eq(sp.Symbol(normalize_name(node.left.name)), self.eval(node.right, exclude), evaluate=False)
        if isinstance(node, ast.ListLit):
            return ListValue(self.eval_held(item, exclude) for item in node.items)
        raise ArgumentError("Variable name expected here")


def _held_names(node: ast.Node) -> set[str]:
    if isinstance(node, ast.Name):
        return {normalize_name(node.name)}
    if isinstance(node, ast.Relation) and isinstance(node.left, ast.Name):
        return {normalize_name(node.left.name)}
    if isinstance(node, ast.ListLit):
        return set().union(*(_held_names(i) for i in node.items)) if node.items else set()
    return set()


def _names_in(node: ast.Node) -> set[str]:
    if isinstance(node, ast.Name):
        return {normalize_name(node.name)}
    names: set[str] = set()
    for value in vars(node).values():
        if isinstance(value, ast.Node):
            names |= _names_in(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, ast.Node):
                    names |= _names_in(item)
    return names - {"π", "ℯ", "ⅈ", "∞", "pi", "e", "i", "true", "false"}


def _filter_solutions(result: SolveResult, mapping: dict, filters: list) -> SolveResult:
    def accepted(alt) -> bool:
        values = {s: v for s, v in alt}
        for f in filters:
            check = f.subs(values).subs(mapping) if isinstance(f, sp.Basic) else f
            if check is sp.false or check is False:
                return False
            if isinstance(check, sp.Basic) and check.free_symbols:
                continue
            if check not in (sp.true, True):
                try:
                    if not bool(check):
                        return False
                except TypeError:
                    return False
        return True

    alternatives = [[(s, v.subs(mapping) if isinstance(v, sp.Basic) else v) for s, v in alt]
                    for alt in result.alternatives if accepted(alt)]
    intervals = None
    if result.intervals:
        intervals = []
        for var, interval in result.intervals:
            region: sp.Set = interval
            for f in filters:
                try:
                    region = region.intersect(sp.solveset(f, var, sp.S.Reals))
                except (NotImplementedError, ValueError, TypeError):
                    pass
            pieces = region.args if isinstance(region, sp.Union) else (region,)
            for piece in pieces:
                if isinstance(piece, sp.Interval):
                    intervals.append((var, piece))
                elif isinstance(piece, sp.FiniteSet):
                    alternatives += [[(var, p)] for p in piece.args]
    return SolveResult(alternatives=alternatives, intervals=intervals or None,
                       always_true=result.always_true and not filters, general=result.general)
