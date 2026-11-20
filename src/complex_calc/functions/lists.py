"""List, sequence and string functions."""

from __future__ import annotations

import math
from typing import Any

import sympy as sp

from ..core.errors import ArgumentError, DomainError
from ..core.values import ListValue, StringValue, is_matrix
from .registry import builtin, to_float, to_int, to_list

UNDEF = sp.nan


def _as_list(value: Any, label: str = "List") -> list:
    if isinstance(value, ListValue):
        return list(value)
    if is_matrix(value):
        return list(value)
    raise ArgumentError(f"{label} must be a list")


# ------------------------------------------------------------------ sequences


@builtin("seq", "seq(Expr,Var,Low,High[,Step])", 4, 5, hold=(1,), summary="List of Expr for Var=Low..High")
def seq_(ctx, expr, var, low, high, step=sp.Integer(1)):
    if step == 0:
        raise DomainError("Step must not be 0")
    values = []
    k = low
    count = 0
    while (k <= high) if step > 0 else (k >= high):
        values.append(expr.subs(var, k) if isinstance(expr, sp.Basic) else expr)
        k += step
        count += 1
        if count > 100000:
            raise DomainError("Too many elements")
    return ListValue(values)


def _recursive(expr, var, depvar_name: str, start: int, stop: int, init: list, step: int = 1, ceiling=None):
    """u(n)=Expr with u(n-1), u(n-2) … referring to earlier terms."""
    values: dict[int, Any] = {}
    u = sp.Function(depvar_name)
    for offset, value in enumerate(init):
        values[start + offset * step] = value
    out = []
    k = start
    while k <= stop:
        if k not in values:
            def replace(call):
                index = int(call.args[0].subs(var, k))
                if index not in values:
                    raise DomainError(f"Missing initial term for {depvar_name}({index})")
                return values[index]

            term = expr.replace(lambda e: isinstance(e, sp.core.function.AppliedUndef) and e.func == u,
                                lambda e: replace(e))
            values[k] = sp.simplify(term.subs(var, k))
        if ceiling is not None and values[k].is_number and abs(float(values[k])) > float(ceiling):
            break
        out.append(values[k])
        k += step
    return out


@builtin("seqGen", "seqGen(Expr,Var,depVar,{Var0,VarMax}[,ListOfInitTerms[,VarStep[,CeilingValue]]])", 4, 7,
         hold=(1, 2), summary="Terms of a (recursive) sequence")
def seq_gen(ctx, expr, var, depvar, bounds, init=None, step=sp.Integer(1), ceiling=None):
    lo, hi = (to_int(b, "bound") for b in to_list(bounds, "{Var0,VarMax}"))
    initial = list(init) if isinstance(init, ListValue) else ([] if init is None else [init])
    return ListValue(_recursive(expr, var, depvar.name, lo, hi, initial, to_int(step, "VarStep"), ceiling))


@builtin("seqn", "seqn(Expr(u,n)[,ListOfInitTerms[,nMax[,CeilingValue]]])", 1, 4,
         summary="Terms u(1), u(2), … of a sequence in n (and u)")
def seqn_(ctx, expr, init=None, nmax=None, ceiling=None):
    n = sp.Symbol("n")
    if isinstance(init, ListValue) or nmax is not None:
        initial = list(init) if isinstance(init, ListValue) else []
        stop = to_int(nmax, "nMax") if nmax is not None else 2500
    else:
        initial = []
        stop = to_int(init, "nMax") if init is not None else 2500
    if stop == 0:
        stop = 2500
    return ListValue(_recursive(expr, n, "u", 1, stop, initial, 1, ceiling))


@builtin("augment", "augment(List1,List2)  |  augment(Matrix1,Matrix2)", 2, matrix_aware=True,
         summary="Join two lists, or matrices side by side")
def augment(ctx, a, b):
    if is_matrix(a) and is_matrix(b):
        if a.rows != b.rows:
            raise ArgumentError("Dimension error")
        return sp.ImmutableMatrix(a.row_join(b))
    return ListValue(_as_list(a, "List1") + _as_list(b, "List2"))


@builtin("cumulativeSum", "cumulativeSum(List)", 1, matrix_aware=True, summary="Running totals")
def cumulative_sum(ctx, values):
    if is_matrix(values):
        m = sp.Matrix(values)
        for r in range(1, m.rows):
            m[r, :] = m[r, :] + m[r - 1, :]
        return sp.ImmutableMatrix(m)
    total, out = sp.Integer(0), []
    for v in _as_list(values):
        total = total + v
        out.append(total)
    return ListValue(out)


@builtin("ΔList", "ΔList(List)", 1, aliases=("deltaList",), summary="Differences of consecutive elements")
def delta_list(ctx, values):
    data = _as_list(values)
    return ListValue(b - a for a, b in zip(data, data[1:]))


def _criteria_match(ctx, criteria, element) -> bool:
    from ..core import parser as ast

    if isinstance(criteria, ast.Node):
        evaluator = ctx.evaluator
        evaluator.scopes.append({"?": element})
        evaluator.in_func.append(False)
        try:
            value = evaluator.eval(criteria, frozenset())
        finally:
            evaluator.scopes.pop()
            evaluator.in_func.pop()
        if value is sp.true:
            return True
        if value is sp.false:
            return False
        if isinstance(value, StringValue) or isinstance(element, StringValue):
            return value == element
        try:
            return sp.simplify(value - element) == 0
        except TypeError:
            return False
    return False


@builtin("countIf", "countIf(List,Criteria)", 2, raw=(1,), summary="Count elements meeting Criteria (use ? as placeholder)")
def count_if(ctx, values, criteria):
    return sp.Integer(sum(1 for v in _as_list(values) if v is not UNDEF and _criteria_match(ctx, criteria, v)))


@builtin("sumIf", "sumIf(List,Criteria[,SumList])", 2, 3, raw=(1,), summary="Sum of elements meeting Criteria")
def sum_if(ctx, values, criteria, sum_list=None):
    data = _as_list(values)
    targets = _as_list(sum_list, "SumList") if sum_list is not None else data
    if len(targets) != len(data):
        raise ArgumentError("Dimension mismatch")
    return sp.Add(*[t for v, t in zip(data, targets) if _criteria_match(ctx, criteria, v)])


@builtin("count", "count(Value1orList1[,Value2orList2[,...]])", 1, 99, summary="Number of numeric elements")
def count_(ctx, *values):
    total = 0
    for value in values:
        items = list(value) if isinstance(value, ListValue) or is_matrix(value) else [value]
        for item in items:
            if isinstance(item, ListValue):
                total += int(count_(ctx, item))
            elif isinstance(item, sp.Expr) and item is not UNDEF:
                total += 1
    return sp.Integer(total)


@builtin("frequency", "frequency(List1,binsList)", 2, summary="Counts of List1 elements per bin")
def frequency_(ctx, values, bins):
    data = [to_float(v, "List1") for v in _as_list(values, "List1")]
    edges = [to_float(b, "binsList") for b in _as_list(bins, "binsList")]
    counts = [0] * (len(edges) + 1)
    for v in data:
        for k, edge in enumerate(edges):
            if v <= edge and (k == 0 or v > edges[k - 1]):
                counts[k] += 1
                break
        else:
            counts[-1] += 1
    return ListValue(sp.Integer(c) for c in counts)


@builtin("delVoid", "delVoid(List)", 1, summary="Remove empty (void) elements")
def del_void(ctx, values):
    return ListValue(v for v in _as_list(values) if v is not UNDEF)


@builtin("isVoid", "isVoid(Expr)", 1, listable=(0,), summary="true if the element is empty (void)")
def is_void(ctx, value):
    return sp.true if value is UNDEF else sp.false


@builtin("newList", "newList(numElements)", 1, summary="List of zeros")
def new_list(ctx, n):
    return ListValue([sp.Integer(0)] * to_int(n, "numElements"))


def _left_right(ctx, value, num, from_left: bool):
    if isinstance(value, sp.core.relational.Relational):
        return value.lhs if from_left else value.rhs
    if isinstance(value, StringValue):
        k = len(value) if num is None else to_int(num, "Num")
        return StringValue(value[:k] if from_left else (value[-k:] if k else ""))
    data = _as_list(value)
    k = len(data) if num is None else to_int(num, "Num")
    return ListValue(data[:k] if from_left else (data[-k:] if k else []))


@builtin("left", "left(sourceString[,Num])  |  left(List[,Num])  |  left(Comparison)", 1, 2,
         summary="First Num characters/elements, or left side of an equation")
def left_(ctx, value, num=None):
    return _left_right(ctx, value, num, True)


@builtin("right", "right(sourceString[,Num])  |  right(List[,Num])  |  right(Comparison)", 1, 2,
         summary="Last Num characters/elements, or right side of an equation")
def right_(ctx, value, num=None):
    return _left_right(ctx, value, num, False)


@builtin("mid", "mid(sourceString,Start[,Count])  |  mid(List,Start[,Count])", 2, 3,
         summary="Part of a string or list")
def mid_(ctx, value, start, count=None):
    s = to_int(start, "Start") - 1
    if isinstance(value, StringValue):
        e = len(value) if count is None else s + to_int(count, "Count")
        return StringValue(value[s:e])
    data = _as_list(value)
    e = len(data) if count is None else s + to_int(count, "Count")
    return ListValue(data[s:e])


def _shift_seq(items: list, k: int, filler) -> list:
    n = len(items)
    if k >= 0:
        return items[k:] + [filler] * min(k, n) if k < n else [filler] * n
    k = -k
    return [filler] * min(k, n) + items[:n - k] if k < n else [filler] * n


@builtin("shift", "shift(Integer[,#ofShifts])  |  shift(List[,#ofShifts])  |  shift(String[,#ofShifts])", 1, 2,
         summary="Shift bits/elements/characters (positive = left, default -1)")
def shift_(ctx, value, count=sp.Integer(-1)):
    k = to_int(count, "#ofShifts")
    if isinstance(value, StringValue):
        return StringValue("".join(_shift_seq(list(value), k, " ")))
    if isinstance(value, ListValue):
        return ListValue(_shift_seq(list(value), k, UNDEF))
    n = to_int(value, "Integer") & ((1 << 64) - 1)
    n = (n << k) if k >= 0 else (n >> -k) | (((1 << -k) - 1) << (64 + k) if n >> 63 else 0)
    n &= (1 << 64) - 1
    return sp.Integer(n - (1 << 64) if n >> 63 else n)


@builtin("rotate", "rotate(Integer[,#ofRotations])  |  rotate(List[,#ofRotations])  |  rotate(String[,#ofRotations])",
         1, 2, summary="Rotate bits/elements/characters (positive = left, default -1)")
def rotate_(ctx, value, count=sp.Integer(-1)):
    k = to_int(count, "#ofRotations")
    if isinstance(value, (StringValue, ListValue)):
        items = list(value)
        if items:
            k %= len(items)
            items = items[k:] + items[:k]
        return StringValue("".join(items)) if isinstance(value, StringValue) else ListValue(items)
    n = to_int(value, "Integer") & ((1 << 64) - 1)
    k %= 64
    n = ((n << k) | (n >> (64 - k))) & ((1 << 64) - 1)
    return sp.Integer(n - (1 << 64) if n >> 63 else n)


@builtin("exp►list", "exp►list(Expr,Var)", 2, hold=(1,), aliases=("exp@>list",),
         summary="List of the right sides of an 'or' of equations (e.g. from solve)")
def exp_to_list(ctx, value, var):
    from ..core.values import SolveResult

    if isinstance(value, SolveResult):
        return ListValue(v for alt in value.alternatives for s, v in alt if s == var)
    if isinstance(value, sp.Equality):
        return ListValue([value.rhs])
    if isinstance(value, sp.Or):
        return ListValue(a.rhs for a in value.args if isinstance(a, sp.Equality))
    raise ArgumentError("exp►list needs equations joined by 'or'")


@builtin("list►mat", "list►mat(List[,elementsPerRow])", 1, 2, aliases=("list@>mat",), summary="List to matrix")
def list_to_mat(ctx, values, per_row=None):
    data = _as_list(values)
    k = len(data) if per_row is None else to_int(per_row, "elementsPerRow")
    rows = [data[i:i + k] for i in range(0, len(data), k)]
    if rows and len(rows[-1]) < k:
        rows[-1] = rows[-1] + [sp.Integer(0)] * (k - len(rows[-1]))
    return sp.ImmutableMatrix(rows)


@builtin("mat►list", "mat►list(Matrix)", 1, aliases=("mat@>list",), matrix_aware=True, summary="Matrix to list (row by row)")
def mat_to_list(ctx, matrix):
    if not is_matrix(matrix):
        raise ArgumentError("Matrix expected")
    return ListValue(list(matrix))


# ------------------------------------------------------------------ list commands (modify variables)


def _sort_command(ctx, names, descending: bool):
    first = ctx.lookup(names[0].name)
    if not isinstance(first, ListValue):
        raise ArgumentError("SortA/SortD need list variables")
    order = sorted(range(len(first)), key=lambda i: float(sp.N(first[i])), reverse=descending)
    for symbol in names:
        values = ctx.lookup(symbol.name)
        if not isinstance(values, ListValue) or len(values) != len(first):
            raise ArgumentError("Dimension mismatch")
        ctx.store(symbol.name, ListValue(values[i] for i in order))
    return None


@builtin("SortA", "SortA List1[,List2][,List3]...", 1, 20, command=True, hold=tuple(range(20)),
         summary="Sort list variable(s) ascending")
def sort_a(ctx, *names):
    return _sort_command(ctx, names, False)


@builtin("SortD", "SortD List1[,List2][,List3]...", 1, 20, command=True, hold=tuple(range(20)),
         summary="Sort list variable(s) descending")
def sort_d(ctx, *names):
    return _sort_command(ctx, names, True)


@builtin("Fill", "Fill Expr,listVar  |  Fill Expr,matrixVar", 2, command=True, hold=(1,),
         summary="Replace every element of a list/matrix variable")
def fill_(ctx, value, var):
    current = ctx.lookup(var.name)
    if isinstance(current, ListValue):
        ctx.store(var.name, ListValue([value] * len(current)))
    elif is_matrix(current):
        ctx.store(var.name, sp.ImmutableMatrix(current.rows, current.cols, [value] * len(current)))
    else:
        raise ArgumentError("Fill needs a list or matrix variable")
    return None


# ------------------------------------------------------------------ strings


@builtin("char", "char(Integer)", 1, listable=(0,), summary="Character with this code")
def char_(ctx, code):
    return StringValue(chr(to_int(code, "Integer")))


@builtin("ord", "ord(String)", 1, listable=(0,), summary="Code of the first character")
def ord_(ctx, text):
    if not isinstance(text, StringValue) or not text:
        raise ArgumentError("ord needs a non-empty string")
    return sp.Integer(ord(text[0]))


@builtin("string", "string(Expr)", 1, summary="Expression as a string")
def string_(ctx, value):
    from ..core.formatting import format_value

    if isinstance(value, StringValue):
        return value
    return StringValue(format_value(value, ctx.settings.digits))


@builtin("expr", "expr(String)", 1, summary="Evaluate a string as an expression")
def expr_(ctx, text):
    from ..core.parser import parse

    if not isinstance(text, StringValue):
        raise ArgumentError("expr needs a string")
    session = ctx.session
    statements = parse(str(text), session.is_function, session.is_command)
    result = None
    for statement in statements:
        result = ctx.evaluator.exec_statement(statement)
    return result


@builtin("inString", "inString(srcString,subString[,Start])", 2, 3, summary="Position of subString (0 if absent)")
def in_string(ctx, source, sub, start=sp.Integer(1)):
    if not isinstance(source, StringValue) or not isinstance(sub, StringValue):
        raise ArgumentError("inString needs strings")
    return sp.Integer(source.find(sub, to_int(start, "Start") - 1) + 1)


@builtin("format", 'format(Expr[,formatString])  formatString: "F[n]" "S[n]" "E[n]" "G[n][c]"', 1, 2,
         summary="Number as a formatted string")
def format_(ctx, value, spec=None):
    x = to_float(value, "Expr")
    if spec is None:
        from ..core.formatting import format_float

        return StringValue(format_float(x, ctx.settings.digits))
    text = str(spec).strip().upper()
    kind, rest = text[:1], text[1:]
    sep = None
    if kind == "G" and rest and not rest[-1].isdigit():
        sep, rest = rest[-1], rest[:-1]
    n = int(rest) if rest else 12
    if kind == "F":
        return StringValue(f"{x:.{n}f}")
    if kind == "S":
        mantissa, exponent = f"{x:.{n}e}".split("e")
        return StringValue(f"{mantissa}E{int(exponent)}")
    if kind == "E":
        if x == 0:
            return StringValue(f"{0:.{n}f}E0")
        exponent = int(math.floor(math.log10(abs(x)) / 3) * 3)
        mantissa = x / 10**exponent
        return StringValue(f"{mantissa:.{n}f}E{exponent}")
    if kind == "G":
        out = f"{x:,.{n}f}"
        if sep is not None:
            out = out.replace(",", "\0").replace(".", sep if sep != "," else ".").replace("\0", sep if sep == "," else ",")
        return StringValue(out)
    raise ArgumentError('formatString must be "F[n]", "S[n]", "E[n]" or "G[n][c]"')


@builtin("dim", "dim(List)  |  dim(Matrix)  |  dim(String)", 1, matrix_aware=True,
         summary="Number of elements / {rows,cols} / string length")
def dim_(ctx, value):
    if is_matrix(value):
        return ListValue([sp.Integer(value.rows), sp.Integer(value.cols)])
    if isinstance(value, (ListValue, StringValue)):
        return sp.Integer(len(value))
    raise ArgumentError("dim needs a list, matrix or string")
