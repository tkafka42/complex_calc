"""More CAS functions: polynomial tools, completeSquare, piecewise/when/ifFn,
extrema, tangent/normal lines, series, differential equations, Σ and Π."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import sympy as sp
from scipy.optimize import minimize_scalar

from ..core.errors import ArgumentError, DomainError, EvaluationError
from ..core.values import ListValue, SolveResult, is_matrix
from .registry import builtin, to_float, to_int


def _var(value: Any) -> tuple[sp.Symbol, Any]:
    if isinstance(value, sp.Symbol):
        return value, None
    if isinstance(value, sp.Equality) and isinstance(value.lhs, sp.Symbol):
        return value.lhs, value.rhs
    raise ArgumentError("Variable name expected")


def _main_var(expr: sp.Expr, var: Any = None) -> sp.Symbol:
    if isinstance(var, sp.Symbol):
        return var
    symbols = sorted(expr.free_symbols, key=lambda s: s.name)
    if not symbols:
        return sp.Symbol("x")
    return symbols[-1] if sp.Symbol("x") not in symbols else sp.Symbol("x")


def _poly(expr: Any, var: Any = None) -> sp.Poly:
    if not isinstance(expr, sp.Expr):
        raise ArgumentError("Polynomial expected")
    symbol = _main_var(expr, var)
    try:
        return sp.Poly(sp.expand(expr), symbol)
    except sp.PolynomialError:
        raise ArgumentError("Polynomial expected")


def _coeff_poly(value: Any, var: Any = None) -> sp.Poly:
    if isinstance(value, ListValue):
        return sp.Poly(list(value), sp.Symbol("x"))
    return _poly(value, var)


# ------------------------------------------------------------------ polynomial tools


@builtin("polyCoeffs", "polyCoeffs(Poly[,Var])", 1, 2, hold=(1,), summary="List of coefficients (highest first)")
def poly_coeffs(ctx, poly, var=None):
    return ListValue(_poly(poly, var).all_coeffs())


@builtin("polyDegree", "polyDegree(Poly[,Var])", 1, 2, hold=(1,), summary="Degree of a polynomial")
def poly_degree(ctx, poly, var=None):
    if isinstance(poly, sp.Expr) and poly.is_number:
        return sp.Integer(0) if poly != 0 else sp.nan
    return sp.Integer(_poly(poly, var).degree())


@builtin("polyEval", "polyEval(List,Expr)  |  polyEval(List1,List2)", 2, summary="Evaluate a polynomial given by coefficients")
def poly_eval(ctx, coeffs, value):
    if not isinstance(coeffs, ListValue):
        raise ArgumentError("polyEval needs a list of coefficients")
    def evaluate(x):
        result = sp.Integer(0)
        for c in coeffs:
            result = result * x + c
        return sp.expand(result)
    if isinstance(value, ListValue):
        return ListValue(evaluate(v) for v in value)
    return evaluate(value)


@builtin("polyGcd", "polyGcd(Expr1,Expr2)", 2, summary="Greatest common divisor of two polynomials")
def poly_gcd(ctx, a, b):
    return sp.gcd(a, b)


@builtin("polyQuotient", "polyQuotient(Poly1,Poly2[,Var])", 2, 3, hold=(2,), summary="Quotient of polynomial division")
def poly_quotient(ctx, a, b, var=None):
    symbol = _main_var(a + b, var)
    return sp.div(a, b, symbol)[0]


@builtin("polyRemainder", "polyRemainder(Poly1,Poly2[,Var])", 2, 3, hold=(2,), summary="Remainder of polynomial division")
def poly_remainder(ctx, a, b, var=None):
    symbol = _main_var(a + b, var)
    return sp.div(a, b, symbol)[1]


def _roots(poly: sp.Poly, complex_: bool) -> ListValue:
    values = []
    roots = sp.roots(poly)
    if sum(roots.values()) != poly.degree():
        roots = {r: 1 for r in sp.Poly(poly).nroots()}
    for value, multiplicity in roots.items():
        if complex_ or value.is_real is not False:
            values += [value] * multiplicity
    return ListValue(sorted(values, key=lambda v: (float(sp.re(sp.N(v))), float(sp.im(sp.N(v))))))


@builtin("polyRoots", "polyRoots(Poly,Var)  |  polyRoots(ListOfCoeffs)", 1, 2, hold=(1,), summary="Real roots")
def poly_roots(ctx, poly, var=None):
    return _roots(_coeff_poly(poly, var), False)


@builtin("cPolyRoots", "cPolyRoots(Poly,Var)  |  cPolyRoots(ListOfCoeffs)", 1, 2, hold=(1,), complex=True,
         summary="Complex roots")
def c_poly_roots(ctx, poly, var=None):
    return _roots(_coeff_poly(poly, var), True)


@builtin("completeSquare", "completeSquare(ExprOrEqn,Var)", 2, hold=(1,), summary="Complete the square")
def complete_square(ctx, value, var):
    symbol = var if isinstance(var, sp.Symbol) else _var(var)[0]

    def complete(expr):
        poly = sp.Poly(sp.expand(expr), symbol)
        if poly.degree() != 2:
            raise ArgumentError("completeSquare needs a quadratic in Var")
        a, b, c = poly.all_coeffs()
        h = b / (2 * a)
        k = c - b**2 / (4 * a)
        square = sp.Pow(symbol + h, 2, evaluate=False) if h != 0 else symbol**2
        return sp.Add(sp.Mul(a, square, evaluate=False) if a != 1 else square, k, evaluate=False) if k != 0 \
            else (sp.Mul(a, square, evaluate=False) if a != 1 else square)

    if isinstance(value, sp.Equality):
        left_has = value.lhs.has(symbol)
        return sp.Eq(complete(value.lhs) if left_has else value.lhs,
                     complete(value.rhs) if not left_has else value.rhs, evaluate=False)
    return complete(value)


@builtin("linSolve", "linSolve(LinearEqn1 and LinearEqn2 …,{Var1,Var2,…})", 2, 9, hold=tuple(range(1, 9)),
         summary="Solution list of a linear system")
def lin_solve(ctx, system, *variables):
    if len(variables) == 1 and isinstance(variables[0], ListValue):
        symbols = [_var(v)[0] for v in variables[0]]
    else:
        symbols = [_var(v)[0] for v in variables]
    equations = list(system.args) if isinstance(system, sp.And) else list(system) if isinstance(system, ListValue) \
        else [system]
    exprs = [e.lhs - e.rhs if isinstance(e, sp.Equality) else e for e in equations]
    try:
        solution = sp.linsolve(exprs, symbols)
    except sp.PolynomialError:
        raise ArgumentError("linSolve needs linear equations")
    if solution is sp.S.EmptySet:
        return sp.false
    return ListValue(list(solution.args[0]))


@builtin("system", "system(Eqn1,Eqn2[,…])", 1, 20, summary="System of equations (same as Eqn1 and Eqn2)")
def system_(ctx, *equations):
    return sp.And(*equations) if len(equations) > 1 else equations[0]


# ------------------------------------------------------------------ piecewise / when / ifFn


@builtin("piecewise", "piecewise(Expr1[,Cond1[,Expr2[,Cond2[,…]]]])", 1, 40, summary="Piecewise function")
def piecewise_(ctx, *args):
    pieces = []
    items = list(args)
    while items:
        expr = items.pop(0)
        cond = items.pop(0) if items else sp.true
        pieces.append((expr, cond))
    if pieces[-1][1] is not sp.true:
        pieces.append((sp.nan, sp.true))
    return sp.Piecewise(*pieces)


@builtin("when", "when(Condition,trueResult[,falseResult][,unknownResult])", 2, 4, summary="Conditional value")
def when_(ctx, cond, true_value, false_value=None, unknown_value=None):
    if cond is sp.true:
        return true_value
    if cond is sp.false:
        return false_value if false_value is not None else sp.nan
    if unknown_value is not None:
        return unknown_value
    pieces = [(true_value, cond)]
    pieces.append((false_value if false_value is not None else sp.nan, True))
    return sp.Piecewise(*pieces)


@builtin("ifFn", "ifFn(BooleanExpr,Value_If_true[,Value_If_false[,Value_If_unknown]])", 2, 4,
         summary="Element-wise conditional value")
def if_fn(ctx, cond, true_value, false_value=sp.nan, unknown_value=None):
    def pick(c, k):
        def item(v):
            return v[k] if isinstance(v, ListValue) else v
        if c is sp.true:
            return item(true_value)
        if c is sp.false:
            return item(false_value)
        return item(unknown_value) if unknown_value is not None else sp.nan
    if isinstance(cond, ListValue):
        return ListValue(pick(c, k) for k, c in enumerate(cond))
    return pick(cond, 0)


# ------------------------------------------------------------------ calculus extras


def _real_bounds(ctx, symbol, low, high) -> tuple[float, float]:
    lo = to_float(low, "lowBound") if low is not None else -math.inf
    hi = to_float(high, "upBound") if high is not None else math.inf
    for cond in ctx.evaluator.active_constraints() if ctx.evaluator else []:
        parts = cond.args if isinstance(cond, sp.And) else (cond,)
        for rel in parts:
            if isinstance(rel, sp.core.relational.Relational):
                if rel.lhs == symbol and rel.rhs.is_number:
                    if rel.rel_op in (">", ">="):
                        lo = max(lo, float(rel.rhs))
                    elif rel.rel_op in ("<", "<="):
                        hi = min(hi, float(rel.rhs))
                elif rel.rhs == symbol and rel.lhs.is_number:
                    if rel.rel_op in ("<", "<="):
                        lo = max(lo, float(rel.lhs))
                    elif rel.rel_op in (">", ">="):
                        hi = min(hi, float(rel.lhs))
    return lo, hi


def _numeric_extremum(ctx, expr, symbol, low, high, maximize: bool) -> float:
    lo, hi = _real_bounds(ctx, symbol, low, high)
    f = sp.lambdify(symbol, -expr if maximize else expr, modules=["numpy"])

    def safe(t):
        try:
            v = complex(f(t))
            return v.real if abs(v.imag) < 1e-9 else math.inf
        except (ZeroDivisionError, ValueError, OverflowError):
            return math.inf

    a = lo if math.isfinite(lo) else -100.0 if not math.isfinite(hi) else hi - 200
    b = hi if math.isfinite(hi) else 100.0 if not math.isfinite(lo) else lo + 200
    xs = np.linspace(a, b, 4001)
    ys = [safe(float(t)) for t in xs]
    k = int(np.argmin(ys))
    left, right = xs[max(k - 1, 0)], xs[min(k + 1, len(xs) - 1)]
    if right > left:
        result = minimize_scalar(safe, bounds=(float(left), float(right)), method="bounded",
                                 options={"xatol": 1e-12})
        return float(result.x)
    return float(xs[k])


@builtin("nfMax", "nfMax(Expr,Var[,lowBound[,upBound]])", 2, 4, hold=(1,), approx=True,
         summary="x where Expr has a local maximum (numeric)")
def nf_max(ctx, expr, var, low=None, high=None):
    symbol = _var(var)[0]
    return sp.Float(_numeric_extremum(ctx, expr, symbol, low, high, True), 15)


@builtin("nfMin", "nfMin(Expr,Var[,lowBound[,upBound]])", 2, 4, hold=(1,), approx=True,
         summary="x where Expr has a local minimum (numeric)")
def nf_min(ctx, expr, var, low=None, high=None):
    symbol = _var(var)[0]
    return sp.Float(_numeric_extremum(ctx, expr, symbol, low, high, False), 15)


def _f_extremum(ctx, expr, var, low, high, maximize: bool) -> SolveResult:
    symbol = _var(var)[0]
    lo, hi = _real_bounds(ctx, symbol, low, high)
    candidates: list[sp.Expr] = []
    try:
        critical = sp.solveset(sp.diff(expr, symbol), symbol, sp.Interval(lo, hi) if (math.isfinite(lo) or
                                                                                    math.isfinite(hi))
                               else sp.S.Reals)
        if isinstance(critical, sp.FiniteSet):
            candidates += list(critical)
    except (NotImplementedError, ValueError, TypeError):
        pass
    for bound in (lo, hi):
        if math.isfinite(bound):
            candidates.append(sp.nsimplify(bound))
    if not candidates:
        value = _numeric_extremum(ctx, expr, symbol, low, high, maximize)
        return SolveResult(alternatives=[[(symbol, sp.Float(value, 15))]])
    values = [(c, sp.N(expr.subs(symbol, c))) for c in candidates]
    values = [(c, v) for c, v in values if v.is_real]
    if not values:
        raise EvaluationError("No extremum found")
    best = max(v for _, v in values) if maximize else min(v for _, v in values)
    # check whether the function exceeds best towards ±∞ (no global extremum)
    for limit_point, ok in ((sp.oo, not math.isfinite(hi)), (-sp.oo, not math.isfinite(lo))):
        if ok:
            limit = sp.limit(expr, symbol, limit_point)
            if (maximize and (limit == sp.oo or (limit.is_number and limit > best))) or \
                    (not maximize and (limit == -sp.oo or (limit.is_number and limit < best))):
                return SolveResult(alternatives=[[(symbol, limit_point)]])
    winners = [c for c, v in values if abs(v - best) < 1e-12 * max(1, abs(best))]
    return SolveResult(alternatives=[[(symbol, w)] for w in sorted(set(winners), key=lambda c: float(c))])


@builtin("fMax", "fMax(Expr,Var[,lowBound[,upBound]])", 2, 4, hold=(1,), summary="Candidate x values of the maximum")
def f_max(ctx, expr, var, low=None, high=None):
    return _f_extremum(ctx, expr, var, low, high, True)


@builtin("fMin", "fMin(Expr,Var[,lowBound[,upBound]])", 2, 4, hold=(1,), summary="Candidate x values of the minimum")
def f_min(ctx, expr, var, low=None, high=None):
    return _f_extremum(ctx, expr, var, low, high, False)


def _point(var, point):
    symbol, at = _var(var)
    if at is None:
        if point is None:
            raise ArgumentError("Point expected")
        at = point
    return symbol, at


@builtin("tangentLine", "tangentLine(Expr,Var,Point)  |  tangentLine(Expr,Var=Point)", 2, 3, hold=(1,),
         summary="Tangent line at Point")
def tangent_line(ctx, expr, var, point=None):
    symbol, at = _point(var, point)
    slope = sp.diff(expr, symbol).subs(symbol, at)
    return sp.expand(slope * (symbol - at) + expr.subs(symbol, at))


@builtin("normalLine", "normalLine(Expr,Var,Point)  |  normalLine(Expr,Var=Point)", 2, 3, hold=(1,),
         summary="Normal line at Point")
def normal_line(ctx, expr, var, point=None):
    symbol, at = _point(var, point)
    slope = sp.diff(expr, symbol).subs(symbol, at)
    if slope == 0:
        return sp.Eq(symbol, at)
    return sp.expand(-1 / slope * (symbol - at) + expr.subs(symbol, at))


@builtin("arcLen", "arcLen(Expr,Var,Start,End)", 4, hold=(1,), listable=(0,), summary="Arc length")
def arc_len(ctx, expr, var, start, end):
    symbol = _var(var)[0]
    integrand = sp.sqrt(1 + sp.diff(expr, symbol) ** 2)
    result = sp.integrate(integrand, (symbol, start, end))
    if result.has(sp.Integral):
        from .cas import _numeric_integral

        return _numeric_integral(integrand, symbol, start, end)
    return sp.simplify(result)


@builtin("series", "series(Expr,Var,Order[,Point])", 3, 4, hold=(1,), summary="Power series up to Order")
def series_(ctx, expr, var, order, point=0):
    symbol = _var(var)[0]
    n = to_int(order, "Order")
    return sp.series(expr, symbol, point, n + 1).removeO()


@builtin("taylor", "taylor(Expr,Var,Order[,Point])", 3, 4, hold=(1,), summary="Taylor polynomial")
def taylor_(ctx, expr, var, order, point=0):
    symbol = _var(var)[0]
    n = to_int(order, "Order")
    terms = [sp.diff(expr, symbol, k).subs(symbol, point) / sp.factorial(k) * (symbol - point) ** k
             for k in range(n + 1)]
    return sp.Add(*terms)


@builtin("dominantTerm", "dominantTerm(Expr,Var[,Point])", 2, 3, hold=(1,), summary="Dominant term of the series")
def dominant_term(ctx, expr, var, point=0):
    symbol = _var(var)[0]
    if point in (sp.oo, -sp.oo):
        return sp.series(expr, symbol, point, n=1).removeO().as_leading_term(symbol)
    return sp.series(expr, symbol, point, n=3).removeO().as_leading_term(symbol)


@builtin("domain", "domain(Expr,Var)", 2, hold=(1,), summary="Real domain of Expr")
def domain_(ctx, expr, var):
    from sympy.calculus.util import continuous_domain

    symbol = _var(var)[0]
    region = continuous_domain(expr, symbol, sp.S.Reals)
    from .cas import _from_set

    result = _from_set(region, None, symbol, False)
    return result


@builtin("impDif", "impDif(Equation,Var,dependVar[,Ord])", 3, 4, hold=(1, 2), summary="Implicit derivative")
def imp_dif(ctx, equation, var, dep, order=1):
    expr = equation.lhs - equation.rhs if isinstance(equation, sp.Equality) else equation
    result = sp.idiff(expr, dep, var, to_int(order, "Ord"))
    return sp.simplify(result)


@builtin("Σ", "Σ(Expr,Var,Low,High)", 4, aliases=("sumSeq",), hold=(1,), summary="Sum")
def sum_seq(ctx, expr, var, low, high):
    symbol = _var(var)[0]
    return sp.summation(expr, (symbol, low, high))


@builtin("Π", "Π(Expr,Var,Low,High)", 4, aliases=("prodSeq",), hold=(1,), summary="Product")
def prod_seq(ctx, expr, var, low, high):
    symbol = _var(var)[0]
    return sp.product(expr, (symbol, low, high))


# ------------------------------------------------------------------ differential equations


def _ode(equation, x: sp.Symbol, y_name: str):
    y = sp.Function(y_name)(x)
    expr = equation.lhs - equation.rhs if isinstance(equation, sp.Equality) else equation
    mapping = {}
    for sym in expr.free_symbols:
        if sym.name == y_name + "''":
            mapping[sym] = y.diff(x, 2)
        elif sym.name == y_name + "'":
            mapping[sym] = y.diff(x)
        elif sym.name == y_name:
            mapping[sym] = y
    return expr.subs(mapping), y


def _to_conditions(conditions: Any, x: sp.Symbol, y, y_name: str) -> dict:
    ics = {}
    items = list(conditions.args) if isinstance(conditions, sp.And) else [conditions]
    for cond in items:
        if not isinstance(cond, sp.Equality):
            continue
        lhs = cond.lhs
        if isinstance(lhs, sp.core.function.AppliedUndef) and lhs.func.__name__ == y_name:
            ics[y.subs(x, lhs.args[0])] = cond.rhs
        elif isinstance(lhs, sp.Symbol) and lhs.name.startswith(y_name + "'"):
            pass
    return ics


@builtin("deSolve", "deSolve(1stOr2ndOrderODE,Var,depVar)  |  deSolve(ODE and initCond,Var,depVar)", 3,
         hold=(1, 2), summary="Solve an ODE (use y' and y'' for derivatives)")
def de_solve(ctx, equation, var, dep):
    x = _var(var)[0]
    y_name = dep.name if isinstance(dep, sp.Symbol) else str(dep.func)
    conditions = []
    ode = equation
    if isinstance(equation, sp.And):
        ode = next(e for e in equation.args if any(s.name.endswith("'") for s in e.free_symbols))
        conditions = [e for e in equation.args if e is not ode]
    expr, y = _ode(ode, x, y_name)
    ics = {}
    for cond in conditions:
        lhs = cond.lhs
        if isinstance(lhs, sp.core.function.AppliedUndef) and lhs.func.__name__ == y_name:
            ics[y.subs(x, lhs.args[0])] = cond.rhs
        elif isinstance(lhs, sp.core.function.AppliedUndef) and lhs.func.__name__ == y_name + "'":
            ics[y.diff(x).subs(x, lhs.args[0])] = cond.rhs
    try:
        solution = sp.dsolve(expr, y, ics=ics or None)
    except (NotImplementedError, ValueError) as exc:
        raise EvaluationError(f"deSolve: {exc}")
    sols = solution if isinstance(solution, list) else [solution]
    # constants C1, C2 → c1, c2 as on the handheld; y(x) → y
    out = []
    for s in sols:
        renamed = s.subs({sp.Symbol(f"C{k}"): sp.Symbol(f"c{k}") for k in range(1, 6)})
        out.append(sp.Eq(sp.Symbol(y_name), renamed.rhs))
    return out[0] if len(out) == 1 else sp.Or(*out)


def _ode_system(exprs, x, deps):
    funcs = [sp.lambdify((x, *deps), e, modules=["numpy"]) for e in exprs]

    def rhs(t, values):
        return [float(f(t, *values)) for f in funcs]

    return rhs


@builtin("euler", "euler(Expr,Var,depVar,{Var0,VarMax},depVar0,VarStep[,eulerStep])", 6, 7, hold=(1, 2),
         approx=True, summary="Euler method for an ODE y'=Expr")
def euler_(ctx, expr, var, dep, bounds, y0, step, euler_step=sp.Integer(1)):
    x = _var(var)[0]
    deps = list(dep) if isinstance(dep, ListValue) else [dep]
    exprs = list(expr) if isinstance(expr, ListValue) else [expr]
    values = [to_float(v, "depVar0") for v in (y0 if isinstance(y0, ListValue) else [y0])]
    x0, x_max = (to_float(b, "bound") for b in bounds)
    h = to_float(step, "VarStep")
    sub = to_int(euler_step, "eulerStep")
    rhs = _ode_system(exprs, x, deps)
    xs, rows = [x0], [[v] for v in values]
    t = x0
    current = values[:]
    while t + h <= x_max + 1e-12:
        for _ in range(sub):
            derivative = rhs(t, current)
            current = [c + h / sub * d for c, d in zip(current, derivative)]
            t += h / sub
        xs.append(t)
        for row, value in zip(rows, current):
            row.append(value)
    return sp.ImmutableMatrix([xs, *rows])


@builtin("rk23", "rk23(Expr,Var,depVar,{Var0,VarMax},depVar0,VarStep[,diftol])", 6, 7, hold=(1, 2),
         approx=True, summary="Runge-Kutta method for an ODE y'=Expr")
def rk23_(ctx, expr, var, dep, bounds, y0, step, diftol=None):
    from scipy.integrate import solve_ivp

    x = _var(var)[0]
    deps = list(dep) if isinstance(dep, ListValue) else [dep]
    exprs = list(expr) if isinstance(expr, ListValue) else [expr]
    values = [to_float(v, "depVar0") for v in (y0 if isinstance(y0, ListValue) else [y0])]
    x0, x_max = (to_float(b, "bound") for b in bounds)
    h = to_float(step, "VarStep")
    points = list(np.arange(x0, x_max + h / 2, h))
    tol = to_float(diftol, "diftol") if diftol is not None else 1e-6
    sol = solve_ivp(_ode_system(exprs, x, deps), (x0, points[-1]), values, method="RK23", t_eval=points,
                    rtol=tol, atol=tol * 1e-3)
    return sp.ImmutableMatrix([list(sol.t), *[list(row) for row in sol.y]])
