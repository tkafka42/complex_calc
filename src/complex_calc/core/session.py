"""Session: variables, settings and evaluation of parsed input.

Used by both the CLI REPL and the GUI.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable

import sympy as sp

from .. import functions  # noqa: F401  (registers all built-ins)
from ..functions.conversions import convert
from ..functions.registry import Builtin, Context, lookup_builtin
from . import parser as ast
from .errors import ArgumentError, CalcError, DomainError, EvaluationError, UndefinedError
from .formatting import format_value
from .values import (
    ListValue,
    SolveResult,
    StatResults,
    StringValue,
    TextValue,
    UserFunction,
    UserProgram,
    is_matrix,
)

FIXED_CONSTANTS: dict[str, Any] = {
    "π": sp.pi,
    "ℯ": sp.E,
    "ⅈ": sp.I,
    "∞": sp.oo,
    "true": sp.true,
    "false": sp.false,
    "undef": sp.nan,
}
LETTER_CONSTANTS: dict[str, Any] = {"e": sp.E, "i": sp.I}

RESERVED = set(FIXED_CONSTANTS) | {"ans"}


def normalize_name(name: str) -> str:
    """Variable names are case-insensitive (ASCII letters only, so Σ ≠ σ)."""
    return "".join(c.lower() if c.isascii() else c for c in name)


@dataclass
class Settings:
    angle: str = "rad"  # "rad" | "deg" | "grad"
    mode: str = "auto"  # "auto" | "exact" | "approx"
    digits: int = 6  # Float 6
    complex_format: str = "real"  # "real" | "rectangular" | "polar"
    # On the handheld the letters e and i are ordinary variables; ℯ (@e) and ⅈ (@i)
    # are the constants. Set to True to treat typed e / i as the constants.
    letters_are_constants: bool = False
    fix: int | None = None  # Display Digits "Fix n" (None = Float)
    float_full: bool = False  # Display Digits "Float" (12 significant digits)
    exp_format: str = "normal"  # "normal" | "scientific" | "engineering"
    vector_format: str = "rectangular"
    base: str = "dec"  # "dec" | "hex" | "bin"


@dataclass
class Entry:
    source: str
    text: str
    value: Any = None
    error: bool = False
    output: list[str] = field(default_factory=list)  # Disp output of programs
    drawing: list[tuple] = field(default_factory=list)  # Draw commands (CX II graphics)


# --------------------------------------------------------------- control flow


class _Flow(Exception):
    pass


class _Return(_Flow):
    def __init__(self, value: Any):
        super().__init__()
        self.value = value


class _Exit(_Flow):
    pass


class _Cycle(_Flow):
    pass


class _Stop(_Flow):
    pass


class _Goto(_Flow):
    def __init__(self, label: str):
        super().__init__()
        self.label = label


DONE = TextValue("Done", quoted=False)


@dataclass
class Session:
    settings: Settings = field(default_factory=Settings)
    variables: dict[str, Any] = field(default_factory=dict)
    history: list[Entry] = field(default_factory=list)
    # Called by Request/RequestStr: (prompt, is_string) -> text or None (cancel)
    input_provider: Callable[[str, bool], str | None] | None = None
    # Called by Disp/Text/DispAt with each output line (in addition to Entry.output)
    output_listener: Callable[[str], None] | None = None
    locked: set[str] = field(default_factory=set)
    _output: list[str] = field(default_factory=list)
    canvas: Any = None

    # ------------------------------------------------------------ parser hooks
    def constant(self, name: str) -> Any | None:
        if name in FIXED_CONSTANTS:
            return FIXED_CONSTANTS[name]
        key = normalize_name(name)
        if key in FIXED_CONSTANTS:
            return FIXED_CONSTANTS[key]
        if self.settings.letters_are_constants and key in LETTER_CONSTANTS and key not in self.variables:
            return LETTER_CONSTANTS[key]
        return None

    def is_function(self, name: str) -> bool:
        """A name followed by "(" is a call unless it holds a value."""
        if self.constant(name) is not None:
            return False
        spec = lookup_builtin(name)
        if spec is not None:
            return not spec.command
        value = self.variables.get(normalize_name(name))
        return value is None or isinstance(value, (UserFunction, UserProgram))

    def is_command(self, name: str) -> bool:
        spec = lookup_builtin(name)
        return spec is not None and spec.command

    # ------------------------------------------------------------ public API
    def evaluate(self, source: str, force_approx: bool = False) -> Any:
        """Parse and evaluate `source`; raises CalcError on failure."""
        statements = ast.parse(source, self.is_function, self.is_command)
        evaluator = Evaluator(self, force_approx)
        try:
            result = evaluator.exec_block(statements, top_level=True)
        except _Stop:
            result = DONE
        except _Return as ret:
            result = ret.value
        except (_Exit, _Cycle):
            raise EvaluationError("Exit/Cycle used outside of a loop")
        except _Goto as goto:
            raise EvaluationError(f"Label {goto.label} not found")
        return result

    def run(self, source: str, force_approx: bool = False) -> Entry:
        """Evaluate and record in the history; never raises CalcError."""
        self._output = []
        self.canvas = None
        try:
            value = self.evaluate(source, force_approx)
            entry = Entry(source, self.format(value), value)
        except CalcError as exc:
            entry = Entry(source, exc.user_message(source), None, error=True)
        except RecursionError:
            entry = Entry(source, "Error: Expression too deeply nested", None, error=True)
        except (TypeError, ValueError, ZeroDivisionError, NotImplementedError, AttributeError,
                IndexError, KeyError, OverflowError) as exc:
            entry = Entry(source, f"Error: {exc}", None, error=True)
        entry.output = list(self._output)
        if self.canvas is not None:
            entry.drawing = list(self.canvas.ops)
        self.history.append(entry)
        return entry

    def format(self, value: Any) -> str:
        return format_value(value, self.settings)

    def emit(self, text: str) -> None:
        self._output.append(text)
        if self.output_listener is not None:
            self.output_listener(text)

    def store(self, name: str, value: Any) -> None:
        key = normalize_name(name)
        if key in RESERVED or (lookup_builtin(key) is not None and not key.startswith("stat.")):
            raise ArgumentError(f"'{name}' is a reserved name")
        if key in self.locked:
            raise EvaluationError(f"Variable {name} is locked")
        if isinstance(value, UserFunction):
            value = UserFunction(name, value.params, value.body)
        self.variables[key] = value

    def delete(self, name: str) -> None:
        key = normalize_name(name)
        if key in self.locked:
            raise EvaluationError(f"Variable {name} is locked")
        self.variables.pop(key, None)

    def clear_variables(self) -> None:
        """ClearAZ: delete all single-letter variables (and everything else here)."""
        for key in list(self.variables):
            if key not in self.locked:
                del self.variables[key]


class Evaluator:
    def __init__(self, session: Session, force_approx: bool = False):
        self.session = session
        self.settings = session.settings
        self.force_approx = force_approx
        self.saw_decimal = False
        self.saw_imaginary = False
        self.scopes: list[dict[str, Any]] = []  # local variables of running programs
        self.in_func: list[bool] = []
        self.ctx = Context(settings=self.settings, store=self.store, lookup=self.lookup_variable,
                           session=session, evaluator=self)

    # ------------------------------------------------------------ variables
    def lookup_variable(self, name: str) -> Any:
        key = normalize_name(name)
        for scope in reversed(self.scopes):
            if key in scope:
                return scope[key]
        return self.session.variables.get(key)

    def store(self, name: str, value: Any) -> None:
        key = normalize_name(name)
        if self.scopes and key in self.scopes[-1]:
            self.scopes[-1][key] = value
            return
        if self.in_func and self.in_func[-1]:
            raise EvaluationError(f"A function cannot modify the global variable {name}; use Local {name}")
        self.session.store(name, value)

    # ------------------------------------------------------------ statements
    def exec_block(self, statements: list[ast.Node], top_level: bool = False) -> Any:
        result: Any = DONE
        index = 0
        while index < len(statements):
            statement = statements[index]
            try:
                result = self.exec_statement(statement, top_level)
            except _Goto as goto:
                target = next((i for i, s in enumerate(statements)
                               if isinstance(s, ast.LblStmt) and s.label == goto.label), None)
                if target is None:
                    raise
                index = target + 1
                continue
            index += 1
        return result

    def exec_statement(self, node: ast.Node, top_level: bool = False) -> Any:
        if isinstance(node, ast.ExprStmt):
            self.saw_decimal = False
            self.saw_imaginary = False
            value = self.finalize(self.eval(node.expr, frozenset()))
            if isinstance(value, StatResults):
                return value
            if node.store_to is not None:
                self.assign(node.store_to, value)
            if top_level and not self.scopes:
                self.session.variables["ans"] = value
            return value

        if isinstance(node, ast.DefineStmt):
            return self.exec_define(node)

        if isinstance(node, ast.DelVarStmt):
            for name in node.names:
                self.session.delete(name)
            return DONE

        if isinstance(node, ast.CopyVarStmt):
            value = self.lookup_variable(node.source)
            if value is None:
                raise UndefinedError(f"Variable '{node.source}' is not defined")
            if isinstance(value, UserFunction):
                value = UserFunction(node.target, value.params, value.body)
            self.store(node.target, value)
            return DONE

        if isinstance(node, ast.CommandStmt):
            spec = lookup_builtin(node.name)
            assert spec is not None
            self.saw_decimal = False
            result = self.call_builtin(spec, node.args, frozenset())
            if isinstance(result, StatResults):
                for key, value in result.variables.items():
                    self.session.variables[normalize_name(f"stat.{key}")] = value
                self.session.variables["stat.results"] = result
                return result
            return DONE if result is None else result

        if isinstance(node, ast.IfStmt):
            for condition, block in node.branches:
                if self.truth(condition):
                    return self.exec_block(block)
            if node.else_block is not None:
                return self.exec_block(node.else_block)
            return DONE

        if isinstance(node, ast.ForStmt):
            return self.exec_for(node)

        if isinstance(node, ast.WhileStmt):
            iterations = 0
            while self.truth(node.condition):
                iterations += 1
                if iterations > 1_000_000:
                    raise EvaluationError("Loop limit reached")
                try:
                    self.exec_block(node.body)
                except _Cycle:
                    continue
                except _Exit:
                    break
            return DONE

        if isinstance(node, ast.LoopStmt):
            iterations = 0
            while True:
                iterations += 1
                if iterations > 1_000_000:
                    raise EvaluationError("Loop limit reached")
                try:
                    self.exec_block(node.body)
                except _Cycle:
                    continue
                except _Exit:
                    break
            return DONE

        if isinstance(node, ast.TryStmt):
            try:
                return self.exec_block(node.body)
            except CalcError as exc:
                self.session.variables["errcode"] = sp.Integer(_error_code(exc))
                self._last_error = exc
                if node.handler is not None:
                    return self.exec_block(node.handler)
                return DONE

        if isinstance(node, ast.ReturnStmt):
            value = self.finalize(self.eval(node.value, frozenset())) if node.value is not None else DONE
            raise _Return(value)

        if isinstance(node, ast.SimpleStmt):
            if node.word == "exit":
                raise _Exit()
            if node.word == "cycle":
                raise _Cycle()
            if node.word == "stop":
                raise _Stop()
            if node.word == "clrerr":
                self.session.variables.pop("errcode", None)
                return DONE
            if node.word == "passerr":
                exc = getattr(self, "_last_error", None)
                if exc is not None:
                    raise exc
                return DONE

        if isinstance(node, ast.LocalStmt):
            if not self.scopes:
                raise EvaluationError("Local can only be used inside Func or Prgm")
            for name in node.names:
                self.scopes[-1][normalize_name(name)] = sp.Symbol(normalize_name(name))
            return DONE

        if isinstance(node, ast.LblStmt):
            return DONE

        if isinstance(node, ast.GotoStmt):
            raise _Goto(node.label)

        raise EvaluationError("Unknown statement")

    def exec_define(self, node: ast.DefineStmt) -> Any:
        if node.kind in ("func", "prgm"):
            program = UserProgram(node.name, [normalize_name(p) for p in node.params], node.block or [],
                                  node.kind)
            self.store(node.name, program)
            return DONE
        self.saw_decimal = False
        if node.params is None:
            value = self.finalize(self.eval(node.body, frozenset()))
            self.store(node.name, value)
            return value if node.show_value else DONE
        params = [normalize_name(p) for p in node.params]
        body = self.finalize(self.eval(node.body, frozenset(params)))
        self.store(node.name, UserFunction(node.name, [sp.Symbol(p) for p in params], body))
        return DONE

    def exec_for(self, node: ast.ForStmt) -> Any:
        start = self.eval(node.start, frozenset())
        end = self.eval(node.end, frozenset())
        step = self.eval(node.step, frozenset()) if node.step is not None else sp.Integer(1)
        try:
            step_f = float(step)
            end_f = float(end)
        except TypeError:
            raise ArgumentError("For needs numeric bounds")
        if step_f == 0:
            raise DomainError("Step must not be 0")
        value = start
        iterations = 0
        while (float(value) <= end_f + 1e-12) if step_f > 0 else (float(value) >= end_f - 1e-12):
            iterations += 1
            if iterations > 1_000_000:
                raise EvaluationError("Loop limit reached")
            self.store_loop_var(node.var, value)
            try:
                self.exec_block(node.body)
            except _Cycle:
                pass
            except _Exit:
                break
            current = self.lookup_variable(node.var)
            value = (current if current is not None else value) + step
        return DONE

    def store_loop_var(self, name: str, value: Any) -> None:
        key = normalize_name(name)
        if self.scopes and (key in self.scopes[-1] or (self.in_func and self.in_func[-1])):
            self.scopes[-1][key] = value
        else:
            self.session.store(name, value)

    def assign(self, target: ast.Node, value: Any) -> None:
        if isinstance(target, ast.Name):
            self.store(target.name, value)
            return
        if isinstance(target, ast.Subscript) and isinstance(target.operand, ast.Name):
            container = self.lookup_variable(target.operand.name)
            indices = [self._index(self.eval(i, frozenset())) for i in target.indices]
            if isinstance(container, ListValue) and len(indices) == 1:
                items = list(container)
                k = indices[0]
                if k == len(items) + 1:
                    items.append(value)
                elif 1 <= k <= len(items):
                    items[k - 1] = value
                else:
                    raise DomainError("Invalid list index")
                self.store(target.operand.name, ListValue(items))
                return
            if container is None and len(indices) == 1 and indices[0] == 1:
                self.store(target.operand.name, ListValue([value]))
                return
            if is_matrix(container) and len(indices) == 2:
                matrix = sp.Matrix(container)
                matrix[indices[0] - 1, indices[1] - 1] = value
                self.store(target.operand.name, sp.ImmutableMatrix(matrix))
                return
        raise ArgumentError("Invalid store target")

    def truth(self, condition: ast.Node) -> bool:
        value = self.eval(condition, frozenset())
        if value is sp.true or value is True:
            return True
        if value is sp.false or value is False:
            return False
        raise EvaluationError("A conditional statement did not resolve to TRUE or FALSE")

    # ------------------------------------------------------------ results
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
        if is_matrix(value):
            return sp.ImmutableMatrix(value.applyfunc(lambda e: self.numeric(e)))
        if isinstance(value, sp.Basic) and not isinstance(value, sp.logic.boolalg.BooleanAtom):
            try:
                return value.evalf(15, chop=True)
            except (TypeError, ValueError, AttributeError):
                return value
        return value

    def finalize(self, value: Any) -> Any:
        mode = self.settings.mode
        if self.force_approx or mode == "approx" or (mode == "auto" and self.saw_decimal):
            value = self.numeric(value)
        if self.settings.complex_format == "real" and not self.saw_imaginary and _has_nonreal(value):
            raise DomainError("Non-real result")
        if self.settings.complex_format == "polar" and isinstance(value, sp.Expr) and value.is_number \
                and not value.is_real:
            return convert(self.ctx, value, "Polar", [])
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

    def eval_Void(self, node: ast.Void, exclude) -> Any:
        return None

    def eval_Str(self, node: ast.Str, exclude) -> Any:
        return StringValue(node.text)

    def eval_Name(self, node: ast.Name, exclude) -> Any:
        key = normalize_name(node.name)
        if key in exclude:
            return sp.Symbol(key)
        fixed = FIXED_CONSTANTS.get(node.name) or FIXED_CONSTANTS.get(key)
        if fixed is not None:
            if fixed is sp.I:
                self.saw_imaginary = True
            return fixed
        value = self.lookup_variable(key)
        if value is not None:
            if isinstance(value, (UserFunction, UserProgram)):
                raise ArgumentError(f"{node.name} is a function; call it like {node.name}(x)")
            if isinstance(value, StatResults):
                return value
            return value
        if key.startswith("_"):
            from ..functions.units import unit_value

            unit = unit_value(node.name)
            if unit is not None:
                return unit
        constant = self.session.constant(node.name)
        if constant is not None:
            if constant is sp.I:
                self.saw_imaginary = True
            return constant
        if key == "ans":
            raise UndefinedError("No previous answer")
        if lookup_builtin(key) is not None:
            raise ArgumentError(f"Missing '(' after {node.name}")
        if key.startswith("stat."):
            raise UndefinedError(f"{node.name} is not defined (run a statistics command first)")
        return sp.Symbol(key)

    def eval_ListLit(self, node: ast.ListLit, exclude) -> Any:
        return ListValue(self.eval(item, exclude) for item in node.items)

    def eval_MatrixLit(self, node: ast.MatrixLit, exclude) -> Any:
        rows = [[self.eval(item, exclude) for item in row] for row in node.rows]
        for row in rows:
            for item in row:
                if isinstance(item, (ListValue, StringValue)) or is_matrix(item):
                    raise ArgumentError("Matrix elements must be expressions")
        return sp.ImmutableMatrix(rows)

    def eval_Neg(self, node: ast.Neg, exclude) -> Any:
        return self.arith("*", sp.Integer(-1), self.eval(node.operand, exclude))

    def eval_BinOp(self, node: ast.BinOp, exclude) -> Any:
        left, right = self.eval(node.left, exclude), self.eval(node.right, exclude)
        if node.op == "&":
            if isinstance(left, StringValue) and isinstance(right, StringValue):
                return StringValue(left + right)
            raise ArgumentError("& joins two strings")
        return self.arith(node.op, left, right)

    def arith(self, op: str, a: Any, b: Any) -> Any:
        if isinstance(a, StringValue) or isinstance(b, StringValue):
            raise ArgumentError("Data type error: use & to join strings")
        if isinstance(a, ListValue) or isinstance(b, ListValue):
            if is_matrix(a) or is_matrix(b):
                raise ArgumentError("Data type: cannot combine a list and a matrix")
            base = op[1:] if op.startswith(".") else op
            if isinstance(a, ListValue) and isinstance(b, ListValue):
                if len(a) != len(b):
                    raise ArgumentError("Dimension mismatch")
                return ListValue(self.arith(base, x, y) for x, y in zip(a, b))
            if isinstance(a, ListValue):
                return ListValue(self.arith(base, x, b) for x in a)
            return ListValue(self.arith(base, a, y) for y in b)
        if is_matrix(a) or is_matrix(b):
            return _matrix_arith(op, a, b)
        for operand in (a, b):
            if not isinstance(operand, sp.Expr):
                raise ArgumentError("Arithmetic is only possible with numbers and expressions")
        op = op[1:] if op.startswith(".") else op
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
        if node.op == "'" and isinstance(node.operand, (ast.Name, ast.Postfix)):
            name = _prime_name(node)
            if name is not None:
                return sp.Symbol(name)  # y' / y'' (used by deSolve)
        value = self.eval(node.operand, exclude)
        if isinstance(value, ListValue):
            return ListValue(self._postfix(node.op, v) for v in value)
        return self._postfix(node.op, value)

    def _angle_unit(self) -> sp.Expr:
        """Size of one degree in the current angle unit."""
        return {"deg": sp.Integer(1), "rad": sp.pi / 180, "grad": sp.Rational(10, 9)}[self.settings.angle]

    def _postfix(self, op: str, value: Any) -> Any:
        if op == "ᵀ":
            if not is_matrix(value):
                raise ArgumentError("Transpose needs a matrix")
            return value.T
        if is_matrix(value) and op not in ("!", "%"):
            return value.applyfunc(lambda e: self._postfix(op, e))
        if is_matrix(value):
            return value.applyfunc(lambda e: self._postfix(op, e))
        if op == "!":
            if value.is_number and value.is_negative and value.is_integer:
                raise DomainError("Factorial of a negative integer is undefined")
            return sp.factorial(value)
        if op == "%":
            return value / 100
        if op == "°":
            return value * self._angle_unit()
        if op == "'":
            return value * self._angle_unit() / 60
        if op == "″":
            return value * self._angle_unit() / 3600
        if op == "ʳ":
            return value * self._angle_unit() * 180 / sp.pi
        if op == "ᵍ":
            return value * self._angle_unit() * sp.Rational(9, 10)
        raise EvaluationError(f"Unknown operator {op}")

    def eval_Subscript(self, node: ast.Subscript, exclude) -> Any:
        container = self.eval(node.operand, exclude)
        indices = [self._index(self.eval(i, exclude)) for i in node.indices]
        if isinstance(container, (ListValue, StringValue)) and len(indices) == 1:
            k = indices[0]
            if not 1 <= k <= len(container):
                raise DomainError("Invalid list index")
            item = container[k - 1]
            return StringValue(item) if isinstance(container, StringValue) else item
        if is_matrix(container):
            if len(indices) == 1:
                if not 1 <= indices[0] <= container.rows:
                    raise DomainError("Invalid row index")
                return container[indices[0] - 1, :]
            if len(indices) == 2:
                r, c = indices
                if not (1 <= r <= container.rows and 1 <= c <= container.cols):
                    raise DomainError("Invalid matrix index")
                return container[r - 1, c - 1]
        raise ArgumentError("Subscripts need a list, string or matrix")

    def _index(self, value: Any) -> int:
        if isinstance(value, sp.Integer) or (isinstance(value, sp.Expr) and value.is_integer):
            return int(value)
        if isinstance(value, sp.Float) and float(value).is_integer():
            return int(value)
        raise ArgumentError("Index must be an integer")

    def eval_Indirection(self, node: ast.Indirection, exclude) -> Any:
        target = self.eval(node.operand, exclude)
        if not isinstance(target, StringValue):
            raise ArgumentError("# needs a string with a variable name")
        return self.eval(ast.Name(str(target), pos=node.pos), exclude)

    def eval_Polar(self, node: ast.Polar, exclude) -> Any:
        r = self.eval(node.magnitude, exclude)
        theta = self.eval(node.angle, exclude) * (sp.pi / 180 / self._angle_unit())
        self.saw_imaginary = True
        return sp.expand_complex(r * sp.exp(sp.I * theta))

    def eval_Convert(self, node: ast.Convert, exclude) -> Any:
        value = self.eval(node.operand, exclude)
        if node.target_node is not None:
            from ..functions.units import convert_units

            return convert_units(self.ctx, value, self.eval(node.target_node, exclude))
        args = [self.eval(a, exclude) for a in node.args]
        result = convert(self.ctx, value, node.target, args)
        target = node.target.lower()
        if target == "decimal":
            self.saw_decimal = True
        elif target == "approxfraction":
            self.saw_decimal = False
        return result

    def eval_Relation(self, node: ast.Relation, exclude) -> Any:
        left, right = self.eval(node.left, exclude), self.eval(node.right, exclude)
        return self.relation(node.op, left, right)

    def relation(self, op: str, left: Any, right: Any) -> Any:
        if isinstance(left, ListValue) or isinstance(right, ListValue):
            if isinstance(left, ListValue) and isinstance(right, ListValue):
                if len(left) != len(right):
                    raise ArgumentError("Dimension mismatch")
                return ListValue(self.relation(op, a, b) for a, b in zip(left, right))
            if isinstance(left, ListValue):
                return ListValue(self.relation(op, a, right) for a in left)
            return ListValue(self.relation(op, left, b) for b in right)
        if isinstance(left, StringValue) or isinstance(right, StringValue):
            equal = isinstance(left, StringValue) and isinstance(right, StringValue) and left == right
            if op == "=":
                return sp.true if equal else sp.false
            if op == "≠":
                return sp.false if equal else sp.true
            raise ArgumentError("Strings can only be compared with = or ≠")
        if is_matrix(left) or is_matrix(right):
            if op in ("=", "≠") and is_matrix(left) and is_matrix(right):
                same = left.shape == right.shape and sp.simplify(left - right) == sp.zeros(*left.shape)
                return sp.true if same == (op == "=") else sp.false
            raise ArgumentError("Matrices can only be compared with = or ≠")
        builders = {"=": sp.Eq, "≠": sp.Ne, "<": sp.Lt, ">": sp.Gt, "≤": sp.Le, "≥": sp.Ge}
        try:
            return builders[op](left, right)
        except TypeError as exc:
            raise EvaluationError(f"Invalid comparison: {exc}")

    def eval_Logic(self, node: ast.Logic, exclude) -> Any:
        items = [self.eval(item, exclude) for item in node.items]
        if all(isinstance(i, sp.Integer) for i in items):
            return _bitwise(node.op, [int(i) for i in items])
        if any(isinstance(i, ListValue) for i in items):
            size = max(len(i) for i in items if isinstance(i, ListValue))
            columns = [[i[k] if isinstance(i, ListValue) else i for i in items] for k in range(size)]
            return ListValue(_logic(node.op, col) for col in columns)
        return _logic(node.op, items)

    def eval_Not(self, node: ast.Not, exclude) -> Any:
        value = self.eval(node.operand, exclude)
        if isinstance(value, sp.Integer):
            return sp.Integer(~int(value))
        if isinstance(value, ListValue):
            return ListValue(sp.Not(v) for v in value)
        try:
            return sp.Not(value)
        except TypeError:
            raise ArgumentError("not needs a condition")

    # ------------------------------------------------------------ "with" operator |
    def eval_With(self, node: ast.With, exclude) -> Any:
        conditions = _flatten_and(node.condition)
        substitutions: dict[str, Any] = {}
        filters: list[ast.Node] = []
        for cond in conditions:
            if isinstance(cond, ast.Relation) and cond.op == "=" and isinstance(cond.left, ast.Name):
                substitutions[normalize_name(cond.left.name)] = self.eval(cond.right, exclude)
            else:
                filters.append(cond)
        filter_names = frozenset(n for f in filters for n in _names_in(f))
        inner_exclude = exclude | frozenset(substitutions) | filter_names
        self._constraints = getattr(self, "_constraints", [])
        filter_exprs = [self.eval(f, exclude | filter_names) for f in filters]
        self._constraints.append(filter_exprs)
        try:
            value = self.eval(node.expr, inner_exclude)
        finally:
            self._constraints.pop()
        mapping = {sp.Symbol(k): v for k, v in substitutions.items()}
        return self._apply_with(value, mapping, filter_exprs)

    def active_constraints(self) -> list:
        """Conditions of enclosing "|" operators (used by fMax, nfMin, nSolve, ...)."""
        return [c for group in getattr(self, "_constraints", []) for c in group]

    def _apply_with(self, value: Any, mapping: dict, filters: list) -> Any:
        if isinstance(value, ListValue):
            return ListValue(self._apply_with(v, mapping, filters) for v in value)
        if isinstance(value, SolveResult):
            return _filter_solutions(value, mapping, filters)
        if is_matrix(value):
            return value.subs(mapping) if mapping else value
        if isinstance(value, (StringValue, StatResults, TextValue)):
            return value
        if isinstance(value, sp.Basic):
            result = value.subs(mapping) if mapping else value
            return result.doit() if hasattr(result, "doit") else result
        raise ArgumentError("'|' cannot be applied to this result")

    # ------------------------------------------------------------ calls
    def eval_Call(self, node: ast.Call, exclude) -> Any:
        key = normalize_name(node.name)
        user = self.lookup_variable(key) if key not in exclude else None
        if isinstance(user, UserFunction):
            args = [self.eval(a, exclude) for a in node.args]
            if len(args) == 1 and isinstance(args[0], ListValue) and len(user.params) == 1:
                return ListValue(user.call([v]) for v in args[0])
            return user.call(args)
        if isinstance(user, UserProgram):
            args = [self.eval(a, exclude) for a in node.args]
            return self.call_program(user, args)
        spec = lookup_builtin(node.name)
        if spec is None:
            # undefined function: stays symbolic, e.g. f(x)
            args = [self.eval(a, exclude) for a in node.args]
            if any(not isinstance(a, sp.Basic) for a in args):
                raise UndefinedError(f"Function {node.name} is not defined")
            return sp.Function(key)(*args)
        if spec.command:
            raise ArgumentError(f"{spec.name} is a command without parentheses: {spec.signature}")
        return self.call_builtin(spec, node.args, exclude)

    def call_program(self, program: UserProgram, args: list[Any]) -> Any:
        if len(args) != len(program.params):
            raise ArgumentError("Too few arguments" if len(args) < len(program.params) else "Too many arguments")
        if len(self.scopes) > 200:
            raise EvaluationError("Too many nested calls")
        self.scopes.append(dict(zip(program.params, args)))
        self.in_func.append(program.kind == "func")
        try:
            result = self.exec_block(program.block)
            if program.kind == "prgm":
                return DONE
            return result
        except _Return as ret:
            return ret.value if program.kind == "func" else DONE
        except (_Exit, _Cycle):
            raise EvaluationError("Exit/Cycle used outside of a loop")
        finally:
            self.scopes.pop()
            self.in_func.pop()

    def call_value(self, function: Any, args: list[Any]) -> Any:
        """Call a user function/program value (used by built-ins)."""
        if isinstance(function, UserFunction):
            return function.call(args)
        if isinstance(function, UserProgram):
            return self.call_program(function, args)
        raise ArgumentError("Function expected")

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
            elif index in spec.raw:
                args.append(node)
            else:
                args.append(self.eval(node, inner_exclude))

        if spec.complex:
            self.saw_imaginary = True
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
        matrix_positions = [i for i in spec.listable if i < len(args) and is_matrix(args[i])
                            and not spec.matrix_aware]
        if matrix_positions:
            shape = args[matrix_positions[0]].shape
            if any(args[i].shape != shape for i in matrix_positions):
                raise ArgumentError("Dimension mismatch")
            cells = []
            for r in range(shape[0]):
                for c in range(shape[1]):
                    call_args = [a[r, c] if i in matrix_positions else a for i, a in enumerate(args)]
                    cells.append(self._apply(spec, call_args))
            return sp.ImmutableMatrix(shape[0], shape[1], cells)
        try:
            return spec.func(self.ctx, *args)
        except (CalcError, _Flow):
            raise
        except (TypeError, ValueError, NotImplementedError, ZeroDivisionError, AttributeError, IndexError) as exc:
            raise EvaluationError(f"{spec.name}: {exc}")

    def eval_held(self, node: ast.Node, exclude: frozenset[str]) -> Any:
        if isinstance(node, ast.Name):
            return sp.Symbol(normalize_name(node.name))
        if isinstance(node, ast.Relation) and node.op == "=" and isinstance(node.left, ast.Name):
            return sp.Eq(sp.Symbol(normalize_name(node.left.name)), self.eval(node.right, exclude), evaluate=False)
        if isinstance(node, ast.ListLit):
            return ListValue(self.eval_held(item, exclude) for item in node.items)
        if isinstance(node, ast.BinOp) and node.op == "^" and isinstance(node.left, ast.Name):
            return sp.Pow(sp.Symbol(normalize_name(node.left.name)), self.eval(node.right, exclude),
                          evaluate=False)
        if isinstance(node, ast.Call):  # e.g. deSolve(..., x, y) with y(x)
            return self.eval(node, exclude)
        raise ArgumentError("Variable name expected here")


# ------------------------------------------------------------------ helpers


def _prime_name(node: ast.Node) -> str | None:
    primes = 0
    while isinstance(node, ast.Postfix) and node.op == "'":
        primes += 1
        node = node.operand
    if isinstance(node, ast.Name):
        return normalize_name(node.name) + "'" * primes
    return None


def _has_nonreal(value: Any) -> bool:
    if isinstance(value, ListValue):
        return any(_has_nonreal(v) for v in value)
    if is_matrix(value):
        return any(_has_nonreal(v) for v in value)
    if isinstance(value, sp.Expr) and value.is_number:
        if value.has(sp.zoo, sp.nan):
            return False
        try:
            return abs(complex(value).imag) > 1e-14
        except (TypeError, ValueError):
            return False
    return False


def _matrix_arith(op: str, a: Any, b: Any) -> Any:
    dot = op.startswith(".")
    base = op[1:] if dot else op
    both = is_matrix(a) and is_matrix(b)
    if dot:
        if both:
            if a.shape != b.shape:
                raise ArgumentError("Dimension error")
            cells = [_scalar_op(base, x, y) for x, y in zip(a, b)]
            return sp.ImmutableMatrix(a.rows, a.cols, cells)
        matrix, scalar, left = (a, b, False) if is_matrix(a) else (b, a, True)
        cells = [_scalar_op(base, scalar, x) if left else _scalar_op(base, x, scalar) for x in matrix]
        return sp.ImmutableMatrix(matrix.rows, matrix.cols, cells)
    if base in ("+", "-"):
        if both:
            if a.shape != b.shape:
                raise ArgumentError("Dimension error")
            return a + b if base == "+" else a - b
        # Expr + Matrix adds Expr to the diagonal (square matrices only)
        matrix = a if is_matrix(a) else b
        if not matrix.is_square:
            raise ArgumentError("Dimension error: matrix must be square (use .+ for every element)")
        scalar_matrix = (b if is_matrix(a) else a) * sp.eye(matrix.rows)
        if base == "+":
            return sp.ImmutableMatrix(matrix + scalar_matrix)
        return sp.ImmutableMatrix(a - scalar_matrix if is_matrix(a) else scalar_matrix - b)
    if base == "*":
        if both:
            if a.cols != b.rows:
                raise ArgumentError("Dimension error")
            return sp.ImmutableMatrix(a * b)
        return sp.ImmutableMatrix(a * b)
    if base == "/":
        if is_matrix(b):
            raise ArgumentError("Division by a matrix is not defined; use ^-1")
        return sp.ImmutableMatrix(a / b)
    if base == "^":
        if not is_matrix(a) or is_matrix(b):
            raise ArgumentError("Data type error")
        if not a.is_square:
            raise ArgumentError("Dimension error: matrix must be square")
        if not (isinstance(b, sp.Integer) or (b.is_number and float(b).is_integer())):
            raise ArgumentError("Matrix power must be an integer")
        if int(b) < 0 and a.det() == 0:
            raise DomainError("Singular matrix")
        return sp.ImmutableMatrix(a ** int(b))
    raise EvaluationError(f"Unknown operator {op}")


def _scalar_op(op: str, x: Any, y: Any) -> Any:
    return {"+": lambda: x + y, "-": lambda: x - y, "*": lambda: x * y,
            "/": lambda: x / y, "^": lambda: x**y}[op]()


def _bitwise(op: str, items: list[int]) -> sp.Integer:
    result = items[0]
    for value in items[1:]:
        if op == "and":
            result &= value
        elif op == "or":
            result |= value
        elif op == "xor":
            result ^= value
        elif op == "nor":
            result = ~(result | value)
        elif op == "nand":
            result = ~(result & value)
        elif op == "⇒":
            result = (~result) | value
        elif op == "⇔":
            result = ~(result ^ value)
    return sp.Integer(result)


def _logic(op: str, items: list[Any]) -> Any:
    try:
        if op == "and":
            return sp.And(*items)
        if op == "or":
            return sp.Or(*items)
        if op == "xor":
            return sp.Xor(*items)
        if op == "nor":
            return sp.Nor(*items)
        if op == "nand":
            return sp.Nand(*items)
        if op == "⇒":
            return sp.Implies(*items)
        if op == "⇔":
            return sp.Equivalent(*items)
    except TypeError:
        pass
    raise ArgumentError(f"'{op}' needs conditions such as x>1 or x=2")


def _flatten_and(node: ast.Node) -> list[ast.Node]:
    if isinstance(node, ast.Logic) and node.op == "and":
        out: list[ast.Node] = []
        for item in node.items:
            out += _flatten_and(item)
        return out
    return [node]


def _held_names(node: ast.Node) -> set[str]:
    if isinstance(node, ast.Name):
        return {normalize_name(node.name)}
    if isinstance(node, ast.Relation) and isinstance(node.left, ast.Name):
        return {normalize_name(node.left.name)}
    if isinstance(node, ast.BinOp) and node.op == "^" and isinstance(node.left, ast.Name):
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
    return names - {"π", "ℯ", "ⅈ", "∞", "true", "false"}


def _error_code(exc: CalcError) -> int:
    from .errors import ArgumentError as AE, CalcSyntaxError, DomainError as DE, UndefinedError as UE

    if isinstance(exc, CalcSyntaxError):
        return 170
    if isinstance(exc, DE):
        return 960
    if isinstance(exc, AE):
        return 210
    if isinstance(exc, UE):
        return 140
    return 40


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
    general = result.general
    if filters and general:
        general = []  # periodic families with interval constraints: list members instead
        for var, family in result.general:
            bounds = _bounds_for(var, filters)
            if bounds is None:
                general.append((var, family))
                continue
            lo, hi = bounds
            n1 = sp.Symbol("n1")
            for k in range(-200, 201):
                value = family.subs(n1, k)
                try:
                    v = float(value)
                except TypeError:
                    continue
                if lo - 1e-12 <= v <= hi + 1e-12:
                    alternatives.append([(var, value)])
        alternatives.sort(key=lambda alt: float(alt[0][1]) if alt and alt[0][1].is_number else 0)
    return SolveResult(alternatives=alternatives, intervals=intervals or None,
                       always_true=result.always_true and not filters, general=general)


def _bounds_for(var: sp.Symbol, filters: list) -> tuple[float, float] | None:
    lo, hi = -math.inf, math.inf
    found = False
    for f in filters:
        parts = f.args if isinstance(f, sp.And) else (f,)
        for rel in parts:
            if not isinstance(rel, sp.core.relational.Relational):
                continue
            if rel.lhs == var and rel.rhs.is_number:
                bound, side = float(rel.rhs), rel.rel_op
            elif rel.rhs == var and rel.lhs.is_number:
                bound, side = float(rel.lhs), {"<": ">", "<=": ">=", ">": "<", ">=": "<="}.get(rel.rel_op, "")
            else:
                continue
            found = True
            if side in (">", ">="):
                lo = max(lo, bound)
            elif side in ("<", "<="):
                hi = min(hi, bound)
    return (lo, hi) if found and not (math.isinf(lo) or math.isinf(hi)) else None
