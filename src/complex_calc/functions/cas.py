"""CAS commands: solve, cSolve, nSolve, zeros, cZeros, factor, cFactor,
expand, approx, exact and calculus helpers (derivative, ∫, nDeriv, nInt, limit)."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import sympy as sp
from scipy import integrate as spi
from scipy.optimize import brentq

from ..core.errors import ArgumentError, DomainError, EvaluationError
from ..core.values import ListValue, SolveResult
from .registry import builtin, to_float

N1 = sp.Symbol("n1")  # integer parameter for periodic solution families


# ------------------------------------------------------------------ helpers


def _variables(arg: Any) -> list[tuple[sp.Symbol, Any]]:
    """Accept x, x=guess or {x,y} / {x=1,y=2}. Returns (symbol, guess|None)."""
    items = list(arg) if isinstance(arg, ListValue) else [arg]
    result = []
    for item in items:
        if isinstance(item, sp.Symbol):
            result.append((item, None))
        elif isinstance(item, sp.Equality) and isinstance(item.lhs, sp.Symbol):
            result.append((item.lhs, item.rhs))
        else:
            raise ArgumentError("Variable name expected, e.g. solve(x^2=4,x)")
    if not result:
        raise ArgumentError("Variable name expected")
    return result


def _as_expr(eq: Any) -> sp.Expr:
    """Equation lhs=rhs → lhs-rhs; plain expression → expression (=0)."""
    if isinstance(eq, sp.Equality):
        return eq.lhs - eq.rhs
    if isinstance(eq, sp.Expr):
        return eq
    raise ArgumentError("Equation expected, e.g. x^2-4=0")


def _is_real_value(value: sp.Expr) -> bool:
    if value.is_real:
        return True
    if value.is_real is False:
        return False
    try:
        number = complex(sp.N(value))
    except (TypeError, ValueError):
        return True  # symbolic: keep
    return abs(number.imag) < 1e-12


def _sort_key(value: sp.Expr):
    try:
        number = complex(sp.N(value))
        return (0, number.real, number.imag)
    except (TypeError, ValueError):
        return (1, 0.0, 0.0)


def _numeric_roots(f_expr: sp.Expr, var: sp.Symbol, low: float, high: float, samples: int = 4000) -> list[float]:
    """Find real roots of f on [low, high] via sign changes + Brent's method."""
    f = sp.lambdify(var, f_expr, modules=["numpy"])

    def safe(t: float) -> float:
        try:
            value = complex(f(t))
        except (ZeroDivisionError, ValueError, OverflowError, TypeError):
            return math.nan
        return value.real if abs(value.imag) < 1e-9 else math.nan

    xs = np.linspace(low, high, samples)
    ys = [safe(float(t)) for t in xs]
    roots: list[float] = []
    for i in range(len(xs) - 1):
        a, b, fa, fb = float(xs[i]), float(xs[i + 1]), ys[i], ys[i + 1]
        if math.isnan(fa) or math.isnan(fb):
            continue
        if fa == 0:
            roots.append(a)
        elif fa * fb < 0:
            try:
                root = brentq(safe, a, b, xtol=1e-14)
            except (ValueError, RuntimeError):
                continue
            # reject poles (sign change through infinity)
            if abs(safe(root)) < 1e-6 * max(1.0, abs(fa), abs(fb)):
                roots.append(root)
    if ys and not math.isnan(ys[-1]) and ys[-1] == 0:
        roots.append(float(xs[-1]))
    unique: list[float] = []
    for r in sorted(roots):
        if not unique or abs(r - unique[-1]) > 1e-9 * max(1.0, abs(r)):
            unique.append(r)
    return unique


def _numeric_solve(f_expr: sp.Expr, var: sp.Symbol, guess: float | None,
                   low: float | None = None, high: float | None = None) -> float:
    if low is not None and high is not None:
        roots = _numeric_roots(f_expr, var, low, high)
    else:
        roots = []
        start = 0.0 if guess is None else guess
        try:
            root = sp.nsolve(f_expr, var, start, prec=20, verify=True)
            root_c = complex(root)
            if abs(root_c.imag) < 1e-12:
                roots = [root_c.real]
        except (ValueError, TypeError, ZeroDivisionError):
            pass
        width = 10.0
        while not roots and width <= 1e6:
            roots = _numeric_roots(f_expr, var, start - width, start + width)
            width *= 10
    if not roots:
        raise EvaluationError("No solution found")
    target = guess if guess is not None else (0.0 if low is None else low)
    return min(roots, key=lambda r: abs(r - target))


def _families_from_imageset(imageset: sp.ImageSet) -> sp.Expr:
    lam = imageset.lamda
    return lam.expr.subs(lam.variables[0], N1)


def _solve_single(expr: sp.Expr, var: sp.Symbol, complex_: bool) -> SolveResult:
    result = SolveResult()
    other_symbols = expr.free_symbols - {var}
    if other_symbols:
        # symbolic parameters: generic solution like the handheld does
        try:
            sols = sp.solve(expr, var)
        except NotImplementedError:
            raise EvaluationError("Cannot solve this equation exactly; try nSolve")
        if not complex_:
            sols = [s for s in sols if _is_real_value(s)]
        result.alternatives = [[(var, s)] for s in sorted(sols, key=sp.default_sort_key)]
        return result

    domain = sp.S.Complexes if complex_ else sp.S.Reals
    try:
        solution_set = sp.solveset(expr, var, domain)
    except (NotImplementedError, ValueError, TypeError):
        solution_set = sp.ConditionSet(var, sp.Eq(expr, 0), domain)
    return _from_set(solution_set, expr, var, complex_)


def _from_set(solution_set: sp.Set, expr: sp.Expr | None, var: sp.Symbol, complex_: bool) -> SolveResult:
    result = SolveResult()
    if solution_set in (sp.S.Reals, sp.S.Complexes):
        result.always_true = True
        return result
    if solution_set is sp.S.EmptySet:
        return result
    pieces = solution_set.args if isinstance(solution_set, sp.Union) else (solution_set,)
    values: list[sp.Expr] = []
    intervals: list[sp.Interval] = []
    for piece in pieces:
        if isinstance(piece, sp.FiniteSet):
            values.extend(piece.args)
        elif isinstance(piece, sp.ImageSet):
            result.general.append((var, _families_from_imageset(piece)))
        elif isinstance(piece, sp.Interval):
            intervals.append(piece)
        elif expr is not None:
            # ConditionSet / Intersection: fall back to sympy.solve, then numerics
            fallback = _fallback(expr, var, complex_)
            values.extend(fallback)
        else:
            raise EvaluationError("Cannot solve this exactly; try nSolve")
    if not complex_:
        values = [v for v in values if _is_real_value(v)]
    unique: list[sp.Expr] = []
    for v in sorted(values, key=_sort_key):
        if not any(sp.simplify(v - u) == 0 for u in unique):
            unique.append(v)
    result.alternatives = [[(var, v)] for v in unique]
    if intervals:
        result.intervals = [(var, iv) for iv in intervals]
    return result


def _fallback(expr: sp.Expr, var: sp.Symbol, complex_: bool) -> list[sp.Expr]:
    try:
        sols = sp.solve(expr, var)
        if sols:
            return sols
    except (NotImplementedError, ValueError, TypeError):
        pass
    roots = _numeric_roots(expr, var, -100.0, 100.0, samples=20000)
    return [sp.Float(r, 15) for r in roots]


def _solve(eq: Any, var_arg: Any, complex_: bool) -> SolveResult:
    variables = _variables(var_arg)
    symbols = [v for v, _ in variables]

    if eq is sp.true or eq is True:
        return SolveResult(always_true=True)
    if eq is sp.false or eq is False:
        return SolveResult()

    # a guess was given: numeric solution
    if any(g is not None for _, g in variables):
        if len(variables) != 1:
            guesses = [g if g is not None else 0 for _, g in variables]
            if not isinstance(eq, sp.And):
                raise ArgumentError("Use 'and' to combine the equations of a system")
            exprs = [_as_expr(e) for e in eq.args]
            sol = sp.nsolve(exprs, symbols, guesses)
            return SolveResult(alternatives=[[(s, sp.Float(v, 15)) for s, v in zip(symbols, sol)]])
        var, guess = variables[0]
        root = _numeric_solve(_as_expr(eq), var, to_float(guess, "guess"))
        return SolveResult(alternatives=[[(var, sp.Float(root, 15))]])

    if isinstance(eq, sp.Or):
        combined = SolveResult()
        for part in eq.args:
            sub = _solve(part, var_arg, complex_)
            combined.alternatives += sub.alternatives
            combined.general += sub.general
            if sub.intervals:
                combined.intervals = (combined.intervals or []) + sub.intervals
            combined.always_true |= sub.always_true
        return combined

    if isinstance(eq, sp.And) and all(isinstance(e, sp.Equality) for e in eq.args):
        exprs = [_as_expr(e) for e in eq.args]
        try:
            sols = sp.solve(exprs, symbols, dict=True)
        except NotImplementedError:
            raise EvaluationError("Cannot solve this system exactly")
        alternatives = []
        for sol in sols:
            if not complex_ and not all(_is_real_value(v) for v in sol.values()):
                continue
            alternatives.append([(s, sol[s]) for s in symbols if s in sol])
        return SolveResult(alternatives=alternatives)

    if len(symbols) != 1:
        raise ArgumentError("Several variables need several equations joined with 'and'")
    var = symbols[0]

    if isinstance(eq, (sp.StrictLessThan, sp.StrictGreaterThan, sp.LessThan, sp.GreaterThan,
                       sp.Unequality, sp.And)):
        if complex_:
            raise DomainError("Inequalities can only be solved over the reals")
        try:
            solution_set = sp.solveset(eq, var, sp.S.Reals)
        except (NotImplementedError, ValueError, TypeError):
            raise EvaluationError("Cannot solve this inequality")
        return _from_set(solution_set, None, var, False)

    return _solve_single(_as_expr(eq), var, complex_)


# ------------------------------------------------------------------ solve family


@builtin("solve", "solve(Equation,Var[=Guess])  |  solve(Eqn1 and Eqn2,{Var1,Var2})", 2, hold=(1,),
         summary="Real solutions of an equation, inequality or system")
def solve_(ctx, eq, var):
    return _solve(eq, var, complex_=False)


@builtin("cSolve", "cSolve(Equation,Var[=Guess])  |  cSolve(Eqn1 and Eqn2,{Var1,Var2})", 2, hold=(1,), complex=True,
         summary="Complex solutions of an equation or system")
def csolve_(ctx, eq, var):
    return _solve(eq, var, complex_=True)


@builtin("nSolve", "nSolve(Equation,Var[=Guess][,lowBound,upBound])", 2, 4, hold=(1,), approx=True,
         summary="One numeric (real) solution")
def nsolve_(ctx, eq, var, low=None, up=None):
    variables = _variables(var)
    if len(variables) != 1:
        raise ArgumentError("nSolve takes exactly one variable")
    symbol, guess = variables[0]
    if (low is None) != (up is None):
        raise ArgumentError("nSolve needs both lowBound and upBound")
    guess_f = to_float(guess, "guess") if guess is not None else None
    lo = to_float(low, "lowBound") if low is not None else None
    hi = to_float(up, "upBound") if up is not None else None
    if lo is not None and (math.isinf(lo) or math.isinf(hi)):
        lo, hi = max(lo, -1e6), min(hi, 1e6)
    expr = _as_expr(eq)
    if expr.free_symbols - {symbol}:
        raise ArgumentError("nSolve: all other variables must have values")
    return sp.Float(_numeric_solve(expr, symbol, guess_f, lo, hi), 15)


def _zeros(expr, var, complex_: bool) -> ListValue:
    result = _solve(sp.Eq(_as_expr(expr), 0), var, complex_)
    if result.general or result.intervals or result.always_true:
        raise EvaluationError("Infinitely many zeros; use solve() instead")
    return ListValue(value for alt in result.alternatives for _, value in alt)


@builtin("zeros", "zeros(Expr,Var)", 2, hold=(1,), summary="List of real zeros")
def zeros_(ctx, expr, var):
    return _zeros(expr, var, False)


@builtin("cZeros", "cZeros(Expr,Var)", 2, hold=(1,), complex=True, summary="List of complex zeros")
def czeros_(ctx, expr, var):
    return _zeros(expr, var, True)


# ------------------------------------------------------------------ factor / expand


def _factor_integer(n: sp.Integer) -> sp.Expr:
    factors = sp.factorint(n)
    if len(factors) <= 1 and all(m == 1 for m in factors.values()):
        return n
    parts = [sp.Pow(p, m, evaluate=False) if m > 1 else p for p, m in sorted(factors.items())]
    return sp.Mul(*parts, evaluate=False)


def _factor_by_roots(expr: sp.Expr, var: sp.Symbol, complex_: bool) -> sp.Expr | None:
    try:
        poly = sp.Poly(expr, var)
    except sp.PolynomialError:
        return None
    if poly.degree() < 2 or poly.free_symbols - {var}:
        return None
    roots = sp.roots(poly)
    if sum(roots.values()) != poly.degree():
        return None
    if not complex_ and not all(_is_real_value(r) for r in roots):
        return None
    factors = [sp.Pow(var - r, m, evaluate=False) if m > 1 else (var - r) for r, m in roots.items()]
    return sp.Mul(poly.LC(), *factors)


@builtin("factor", "factor(Expr[,Var])", 1, 2, hold=(1,), summary="Factor (over the rationals; with Var also irrational real factors)")
def factor_(ctx, expr, var=None):
    if isinstance(expr, sp.Integer):
        return _factor_integer(expr)
    if isinstance(expr, sp.Rational) and not isinstance(expr, sp.Integer):
        return sp.Mul(_factor_integer(expr.p), sp.Pow(_factor_integer(expr.q), -1, evaluate=False), evaluate=False)
    if var is not None:
        symbol = _variables(var)[0][0]
        rational = sp.factor(expr, symbol)
        by_roots = _factor_by_roots(expr, symbol, complex_=False)
        if by_roots is not None and not all(r.is_Rational for r in sp.roots(sp.Poly(expr, symbol))):
            return by_roots  # irrational real roots, e.g. factor(x^2-2,x) → (x-√2)·(x+√2)
        return rational
    return sp.factor(expr)


@builtin("cFactor", "cFactor(Expr[,Var])", 1, 2, hold=(1,), complex=True, summary="Factor over the complex numbers")
def cfactor_(ctx, expr, var=None):
    if var is not None:
        symbol = _variables(var)[0][0]
    else:
        symbols = sorted(expr.free_symbols, key=lambda s: s.name) if isinstance(expr, sp.Basic) else []
        if len(symbols) != 1:
            return sp.factor(expr, gaussian=True)
        symbol = symbols[0]
    by_roots = _factor_by_roots(expr, symbol, complex_=True)
    return by_roots if by_roots is not None else sp.factor(expr, gaussian=True)


@builtin("expand", "expand(Expr[,Var])", 1, 2, hold=(1,), summary="Expand products and powers")
def expand_(ctx, expr, var=None):
    expanded = sp.expand(expr)
    if var is not None:
        symbol = _variables(var)[0][0]
        return sp.collect(expanded, symbol)
    return expanded


@builtin("approx", "approx(Expr)", 1, approx=True, summary="Decimal approximation")
def approx_(ctx, expr):
    return expr


def _exact_one(value: Any, tolerance: float | None) -> Any:
    if isinstance(value, ListValue):
        return ListValue(_exact_one(v, tolerance) for v in value)
    if isinstance(value, sp.Basic):
        if tolerance is None:
            return sp.nsimplify(value, rational=True)
        return sp.nsimplify(value, tolerance=tolerance, rational=True)
    return value


@builtin("exact", "exact(Expr[,Tol])", 1, 2, exact=True, summary="Exact (rational) form of a decimal value")
def exact_(ctx, expr, tol=None):
    return _exact_one(expr, to_float(tol, "Tol") if tol is not None else None)


# ------------------------------------------------------------------ calculus


def _single_var(var: Any) -> tuple[sp.Symbol, Any]:
    variables = _variables(var)
    if len(variables) != 1:
        raise ArgumentError("Exactly one variable expected")
    return variables[0]


@builtin("d", "d(Expr,Var[,Order])", 2, 3, aliases=("derivative",), hold=(1,),
         summary="Derivative d/dVar")
def derivative_(ctx, expr, var, order=1):
    symbol, at = _single_var(var)
    result = sp.diff(expr, symbol, int(order))
    return result.subs(symbol, at) if at is not None else result


@builtin("∫", "∫(Expr,Var[,Lower,Upper])", 2, 4, aliases=("integral",), hold=(1,),
         summary="Integral (indefinite or definite)")
def integral_(ctx, expr, var, lower=None, upper=None):
    symbol, _ = _single_var(var)
    if (lower is None) != (upper is None):
        raise ArgumentError("Definite integral needs both Lower and Upper")
    if lower is None:
        result = sp.integrate(expr, symbol)
        if result.has(sp.Integral):
            raise EvaluationError("No closed-form antiderivative found")
        return result
    try:
        result = sp.integrate(expr, (symbol, lower, upper))
    except (NotImplementedError, ValueError):
        result = None
    if result is None or result.has(sp.Integral) or result.has(sp.nan):
        return _numeric_integral(expr, symbol, lower, upper)
    return result


def _numeric_integral(expr, symbol, lower, upper) -> sp.Float:
    if expr.free_symbols - {symbol}:
        raise EvaluationError("Integral cannot be evaluated: other variables have no value")
    f = sp.lambdify(symbol, expr, modules=["numpy"])
    value, _ = spi.quad(lambda t: float(np.real(f(t))), to_float(lower, "Lower"), to_float(upper, "Upper"), limit=200)
    return sp.Float(value, 15)


@builtin("nInt", "nInt(Expr,Var,Lower,Upper)", 4, hold=(1,), approx=True, summary="Numeric integral")
def nint_(ctx, expr, var, lower, upper):
    symbol, _ = _single_var(var)
    return _numeric_integral(expr, symbol, lower, upper)


@builtin("centralDiff", "centralDiff(Expr1,Var[=Value][,Step])  |  centralDiff(Expr1,Var[,Step])|Var=Value",
         2, 3, hold=(1,), approx=True, summary="Numeric derivative with the central difference quotient (Step=0.001)")
def central_diff(ctx, expr, var, step=sp.Rational(1, 1000)):
    symbol, at = _single_var(var)
    steps = list(step) if isinstance(step, ListValue) else None
    if steps is not None:
        return ListValue(central_diff(ctx, expr, var, h) for h in steps)
    central = (expr.subs(symbol, symbol + step) - expr.subs(symbol, symbol - step)) / (2 * step)
    return central.subs(symbol, at) if at is not None else central


@builtin("avgRC", "avgRC(Expr1,Var[=Value][,Step])", 2, 3, hold=(1,),
         summary="Forward-difference quotient (average rate of change), Step=0.001")
def avg_rc(ctx, expr, var, step=sp.Rational(1, 1000)):
    symbol, at = _single_var(var)
    if isinstance(step, ListValue):
        return ListValue(avg_rc(ctx, expr, var, h) for h in step)
    quotient = (expr.subs(symbol, symbol + step) - expr) / step
    return quotient.subs(symbol, at) if at is not None else quotient


@builtin("nDerivative", "nDerivative(Expr1,Var=Value[,Order])  |  nDerivative(Expr1,Var[,Order])|Var=Value",
         2, 3, aliases=("nDeriv",), hold=(1,), approx=True, summary="Numeric derivative (order 1 or 2)")
def nderivative_(ctx, expr, var, order=1):
    symbol, at = _single_var(var)
    if int(order) not in (1, 2):
        raise DomainError("Order must be 1 or 2")
    result = sp.diff(expr, symbol, int(order))
    return result.subs(symbol, at) if at is not None else result


@builtin("limit", "limit(Expr,Var,Point[,Direction])", 3, 4, aliases=("lim",), hold=(1,),
         summary="Limit; Direction <0 from the left, >0 from the right")
def limit_(ctx, expr, var, point, direction=0):
    symbol, _ = _single_var(var)
    d = to_float(direction, "Direction")
    if d < 0:
        return sp.limit(expr, symbol, point, dir="-")
    if d > 0:
        return sp.limit(expr, symbol, point, dir="+")
    return sp.limit(expr, symbol, point, dir="+-")
