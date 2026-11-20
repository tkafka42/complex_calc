"""Regression commands (no parentheses), e.g. ``LinRegMx {1,2,3},{2,4,7}``.

Each command returns a stat.results table and stores stat.RegEqn as a
callable function, so ``stat.RegEqn(5)`` works afterwards.
"""

from __future__ import annotations

import math

import numpy as np
import sympy as sp
from scipy.optimize import curve_fit

from ..core.errors import ArgumentError, DomainError
from ..core.values import ListValue, StatResults, TextValue, UserFunction
from .registry import builtin, to_float, to_float_list, to_int

X = sp.Symbol("x")


def _f(x: float) -> sp.Float:
    x = float(x)
    return sp.Float(0.0 if abs(x) < 1e-11 else x, 15)  # hide floating-point noise


def _xy(xs, ys, freq, minimum: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    x = np.array(to_float_list(xs, "X List"))
    y = np.array(to_float_list(ys, "Y List"))
    if len(x) != len(y):
        raise ArgumentError("Dimension mismatch: X List and Y List must have the same length")
    if freq is None or (isinstance(freq, sp.Basic) and freq == 1):
        w = np.ones_like(x)
    elif isinstance(freq, ListValue):
        w = np.array(to_float_list(freq, "Freq"))
        if len(w) != len(x):
            raise ArgumentError("Dimension mismatch: Freq must have the same length as X List")
    else:
        w = np.full_like(x, to_float(freq, "Freq"))
    mask = w > 0
    x, y, w = x[mask], y[mask], w[mask]
    if len(x) < minimum:
        raise DomainError(f"At least {minimum} data points are required")
    return x, y, w


def _linear_fit(x, y, w) -> tuple[float, float, float]:
    """Weighted least squares y = m*x + b; returns m, b, r."""
    n = w.sum()
    mx, my = (w * x).sum() / n, (w * y).sum() / n
    sxx = (w * (x - mx) ** 2).sum()
    syy = (w * (y - my) ** 2).sum()
    sxy = (w * (x - mx) * (y - my)).sum()
    if sxx == 0:
        raise DomainError("All x values are equal")
    m = sxy / sxx
    b = my - m * mx
    r = sxy / math.sqrt(sxx * syy) if syy > 0 else 1.0
    return m, b, r


def _resid(y, model) -> ListValue:
    return ListValue(_f(v) for v in (y - model))


def _results(ctx, title: str, eqn_text: str, eqn: sp.Expr, rows: list, resid: ListValue,
             data=None, resid_trans: ListValue | None = None) -> StatResults:
    all_rows = [("RegEqn", TextValue(eqn_text)), *rows, ("Resid", resid)]
    if resid_trans is not None:
        all_rows.append(("ResidTrans", resid_trans))
    variables = {name: value for name, value in rows}
    variables["Resid"] = resid
    if resid_trans is not None:
        variables["ResidTrans"] = resid_trans
    variables["RegEqn"] = UserFunction("stat.RegEqn", [X], eqn)
    if data is not None:
        x, y, w = data
        variables["XReg"] = ListValue(_f(v) for v in x)
        variables["YReg"] = ListValue(_f(v) for v in y)
        variables["FreqReg"] = ListValue(_f(v) for v in w)
    return StatResults(title, all_rows, variables)


@builtin("LinRegMx", "LinRegMx X,Y[,Freq]", 2, 3, command=True, approx=True,
         summary="Linear regression y = m·x + b")
def lin_reg_mx(ctx, xs, ys, freq=None):
    x, y, w = _xy(xs, ys, freq, 2)
    m, b, r = _linear_fit(x, y, w)
    rows = [("m", _f(m)), ("b", _f(b)), ("r²", _f(r * r)), ("r", _f(r))]
    return _results(ctx, "Linear Regression (mx+b)", "m*x+b", _f(m) * X + _f(b), rows, _resid(y, m * x + b),
                    (x, y, w))


@builtin("LinRegBx", "LinRegBx X,Y[,Freq]", 2, 3, command=True, approx=True,
         summary="Linear regression y = a + b·x")
def lin_reg_bx(ctx, xs, ys, freq=None):
    x, y, w = _xy(xs, ys, freq, 2)
    m, b, r = _linear_fit(x, y, w)
    rows = [("a", _f(b)), ("b", _f(m)), ("r²", _f(r * r)), ("r", _f(r))]
    return _results(ctx, "Linear Regression (a+bx)", "a+b*x", _f(b) + _f(m) * X, rows, _resid(y, m * x + b),
                    (x, y, w))


@builtin("QuadReg", "QuadReg X,Y[,Freq]", 2, 3, command=True, approx=True,
         summary="Quadratic regression y = a·x² + b·x + c")
def quad_reg(ctx, xs, ys, freq=None):
    x, y, w = _xy(xs, ys, freq, 3)
    a, b, c = np.polyfit(x, y, 2, w=np.sqrt(w))
    model = a * x**2 + b * x + c
    my = (w * y).sum() / w.sum()
    ss_tot = (w * (y - my) ** 2).sum()
    r2 = 1 - (w * (y - model) ** 2).sum() / ss_tot if ss_tot > 0 else 1.0
    rows = [("a", _f(a)), ("b", _f(b)), ("c", _f(c)), ("R²", _f(r2))]
    eqn = _f(a) * X**2 + _f(b) * X + _f(c)
    return _results(ctx, "Quadratic Regression", "a*x^2+b*x+c", eqn, rows, _resid(y, model), (x, y, w))


@builtin("ExpReg", "ExpReg X,Y[,Freq]", 2, 3, command=True, approx=True,
         summary="Exponential regression y = a·bˣ")
def exp_reg(ctx, xs, ys, freq=None):
    x, y, w = _xy(xs, ys, freq, 2)
    if np.any(y <= 0):
        raise DomainError("ExpReg needs all y values > 0")
    m, intercept, r = _linear_fit(x, np.log(y), w)
    a, b = math.exp(intercept), math.exp(m)
    rows = [("a", _f(a)), ("b", _f(b)), ("r²", _f(r * r)), ("r", _f(r))]
    trans = ListValue(_f(v) for v in np.log(y) - (intercept + m * x))
    return _results(ctx, "Exponential Regression", "a*(b)^x", _f(a) * _f(b) ** X, rows, _resid(y, a * b**x),
                    (x, y, w), trans)


@builtin("SinReg", "SinReg X,Y[,Iterations][,Period]", 2, 4, command=True, approx=True,
         summary="Sinusoidal regression y = a·sin(b·x + c) + d")
def sin_reg(ctx, xs, ys, iterations=None, period=None):
    x, y, _ = _xy(xs, ys, None, 4)
    if iterations is not None:
        to_int(iterations, "Iterations")  # accepted for compatibility, fit runs to convergence

    def design(b: float) -> np.ndarray:
        return np.column_stack([np.sin(b * x), np.cos(b * x), np.ones_like(x)])

    def solve_linear(b: float) -> tuple[np.ndarray, float]:
        coef, *_ = np.linalg.lstsq(design(b), y, rcond=None)
        sse = float(((design(b) @ coef - y) ** 2).sum())
        return coef, sse

    if period is not None:
        p = to_float(period, "Period")
        if p <= 0:
            raise DomainError("Period must be > 0")
        candidates = [2 * math.pi / p]
    else:
        span = float(x.max() - x.min())
        if span == 0:
            raise DomainError("All x values are equal")
        diffs = np.diff(np.unique(x))
        nyquist = math.pi / float(diffs.min())
        candidates = np.linspace(math.pi / span, nyquist, 4000)

    best_b, (best_coef, best_sse) = None, (None, math.inf)
    for b in candidates:
        coef, sse = solve_linear(float(b))
        if sse < best_sse:
            best_b, best_coef, best_sse = float(b), coef, sse

    s_coef, c_coef, d0 = best_coef
    a0, c0 = math.hypot(s_coef, c_coef), math.atan2(c_coef, s_coef)

    def model(t, a, b, c, d):
        return a * np.sin(b * t + c) + d

    try:
        params, _ = curve_fit(model, x, y, p0=[a0, best_b, c0, d0], maxfev=20000)
    except RuntimeError:
        params = np.array([a0, best_b, c0, d0])
    a, b, c, d = (float(v) for v in params)
    if a < 0:  # normalise: amplitude positive
        a, c = -a, c + math.pi
    if b < 0:
        b, c = -b, math.pi - c
    c = math.remainder(c, 2 * math.pi)
    rows = [("a", _f(a)), ("b", _f(b)), ("c", _f(c)), ("d", _f(d))]
    eqn = _f(a) * sp.sin(_f(b) * X + _f(c)) + _f(d)
    return _results(ctx, "Sinusoidal Regression", "a*sin(b*x+c)+d", eqn, rows, _resid(y, model(x, a, b, c, d)),
                    (x, y, np.ones_like(x)))


def _poly_reg(ctx, xs, ys, freq, degree: int, title: str, eqn_text: str):
    x, y, w = _xy(xs, ys, freq, degree + 1)
    coeffs = np.polyfit(x, y, degree, w=np.sqrt(w))
    model = np.polyval(coeffs, x)
    my = (w * y).sum() / w.sum()
    ss_tot = (w * (y - my) ** 2).sum()
    r2 = 1 - (w * (y - model) ** 2).sum() / ss_tot if ss_tot > 0 else 1.0
    names = "abcde"[: degree + 1]
    rows = [(names[k], _f(c)) for k, c in enumerate(coeffs)] + [("R²", _f(r2))]
    eqn = sum(_f(c) * X ** (degree - k) for k, c in enumerate(coeffs))
    return _results(ctx, title, eqn_text, eqn, rows, _resid(y, model), (x, y, w))


@builtin("CubicReg", "CubicReg X,Y[,Freq]", 2, 3, command=True, approx=True,
         summary="Cubic regression y = a·x³ + b·x² + c·x + d")
def cubic_reg(ctx, xs, ys, freq=None):
    return _poly_reg(ctx, xs, ys, freq, 3, "Cubic Regression", "a*x^3+b*x^2+c*x+d")


@builtin("QuartReg", "QuartReg X,Y[,Freq]", 2, 3, command=True, approx=True,
         summary="Quartic regression y = a·x⁴ + b·x³ + c·x² + d·x + e")
def quart_reg(ctx, xs, ys, freq=None):
    return _poly_reg(ctx, xs, ys, freq, 4, "Quartic Regression", "a*x^4+b*x^3+c*x^2+d*x+e")


@builtin("PowerReg", "PowerReg X,Y[,Freq]", 2, 3, command=True, approx=True, summary="Power regression y = a·x^b")
def power_reg(ctx, xs, ys, freq=None):
    x, y, w = _xy(xs, ys, freq, 2)
    if np.any(x <= 0) or np.any(y <= 0):
        raise DomainError("PowerReg needs all x and y values > 0")
    b, ln_a, r = _linear_fit(np.log(x), np.log(y), w)
    a = math.exp(ln_a)
    rows = [("a", _f(a)), ("b", _f(b)), ("r²", _f(r * r)), ("r", _f(r))]
    trans = ListValue(_f(v) for v in np.log(y) - (ln_a + b * np.log(x)))
    return _results(ctx, "Power Regression", "a*x^b", _f(a) * X ** _f(b), rows, _resid(y, a * x**b), (x, y, w), trans)


@builtin("LnReg", "LnReg X,Y[,Freq]", 2, 3, command=True, approx=True, summary="Logarithmic regression y = a + b·ln(x)")
def ln_reg(ctx, xs, ys, freq=None):
    x, y, w = _xy(xs, ys, freq, 2)
    if np.any(x <= 0):
        raise DomainError("LnReg needs all x values > 0")
    b, a, r = _linear_fit(np.log(x), y, w)
    rows = [("a", _f(a)), ("b", _f(b)), ("r²", _f(r * r)), ("r", _f(r))]
    model = a + b * np.log(x)
    return _results(ctx, "Logarithmic Regression", "a+b*ln(x)", _f(a) + _f(b) * sp.log(X), rows,
                    _resid(y, model), (x, y, w), _resid(y, model))


def _logistic_fit(x, y, with_d: bool):
    def model(t, a, b, c, *d):
        with np.errstate(over="ignore"):
            return c / (1 + a * np.exp(-b * t)) + (d[0] if d else 0)

    c0 = float(y.max()) * 1.1 if not with_d else float(y.max() - y.min()) * 1.1
    d0 = float(y.min()) if with_d else 0.0
    p0 = [max((c0 / max(float(y[0]) - d0, 1e-9)) - 1, 1e-3), 1.0, c0] + ([d0] if with_d else [])
    import warnings

    best = None
    for b0 in (0.01, 0.1, 0.5, 1.0, 2.0, 5.0):
        try:
            p0[1] = b0
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                params, _ = curve_fit(model, x, y, p0=p0, maxfev=20000)
            sse = float(((model(x, *params) - y) ** 2).sum())
            if best is None or sse < best[1]:
                best = (params, sse)
        except (RuntimeError, ValueError):
            continue
    if best is None:
        raise DomainError("Logistic fit did not converge")
    return best[0], model


@builtin("Logistic", "Logistic X,Y[,Freq]", 2, 3, command=True, approx=True,
         summary="Logistic regression y = c/(1+a·e^(-b·x))")
def logistic_reg(ctx, xs, ys, freq=None):
    x, y, w = _xy(xs, ys, freq, 3)
    (a, b, c), model = _logistic_fit(x, y, False)
    rows = [("a", _f(a)), ("b", _f(b)), ("c", _f(c))]
    eqn = _f(c) / (1 + _f(a) * sp.exp(-_f(b) * X))
    return _results(ctx, "Logistic Regression (d=0)", "c/(1+a*e^(-b*x))", eqn, rows, _resid(y, model(x, a, b, c)),
                    (x, y, w))


@builtin("LogisticD", "LogisticD X,Y[,[Iterations],[Freq]]", 2, 4, command=True, approx=True,
         summary="Logistic regression y = c/(1+a·e^(-b·x))+d")
def logistic_d_reg(ctx, xs, ys, iterations=None, freq=None):
    x, y, w = _xy(xs, ys, freq, 4)
    (a, b, c, d), model = _logistic_fit(x, y, True)
    rows = [("a", _f(a)), ("b", _f(b)), ("c", _f(c)), ("d", _f(d))]
    eqn = _f(c) / (1 + _f(a) * sp.exp(-_f(b) * X)) + _f(d)
    return _results(ctx, "Logistic Regression (d≠0)", "c/(1+a*e^(-b*x))+d", eqn, rows,
                    _resid(y, model(x, a, b, c, d)), (x, y, w))


@builtin("MedMed", "MedMed X,Y[,Freq]", 2, 3, command=True, approx=True, summary="Median-median line y = m·x + b")
def med_med(ctx, xs, ys, freq=None):
    x, y, w = _xy(xs, ys, freq, 3)
    order = np.argsort(x, kind="stable")
    xe = np.repeat(x[order], w[order].astype(int))
    ye = np.repeat(y[order], w[order].astype(int))
    n = len(xe)
    size = [n // 3 + (1 if n % 3 == 2 else 0), n // 3 + (1 if n % 3 == 1 else 0), n // 3 + (1 if n % 3 == 2 else 0)]
    g1, g2 = slice(0, size[0]), slice(size[0], size[0] + size[1])
    g3 = slice(size[0] + size[1], n)
    mx = [float(np.median(xe[g])) for g in (g1, g2, g3)]
    my = [float(np.median(ye[g])) for g in (g1, g2, g3)]
    m = (my[2] - my[0]) / (mx[2] - mx[0])
    b = (sum(my) - m * sum(mx)) / 3
    rows = [("m", _f(m)), ("b", _f(b))]
    return _results(ctx, "Median-Median Line", "m*x+b", _f(m) * X + _f(b), rows, _resid(y, m * x + b), (x, y, w))


@builtin("MultReg", "MultReg Y,X1[,X2[,X3,…[,X10]]]", 2, 11, command=True, approx=True,
         summary="Multiple linear regression y = b0 + b1·x1 + …")
def mult_reg(ctx, ys, *xs_lists):
    y = np.array(to_float_list(ys, "Y"))
    columns = [np.array(to_float_list(v, "X")) for v in xs_lists]
    if any(len(c) != len(y) for c in columns):
        raise ArgumentError("Dimension mismatch")
    design = np.column_stack([np.ones_like(y), *columns])
    coeffs, *_ = np.linalg.lstsq(design, y, rcond=None)
    model = design @ coeffs
    ss_tot = ((y - y.mean()) ** 2).sum()
    r2 = 1 - ((y - model) ** 2).sum() / ss_tot if ss_tot > 0 else 1.0
    names = [sp.Symbol(f"x{k + 1}") for k in range(len(columns))]
    eqn = _f(coeffs[0]) + sum(_f(c) * s for c, s in zip(coeffs[1:], names))
    rows = [("RegEqn", TextValue("b0+b1*x1" + "".join(f"+b{k}*x{k}" for k in range(2, len(columns) + 1)))),
            *[(f"b{k}", _f(c)) for k, c in enumerate(coeffs)], ("R²", _f(r2)),
            ("yList", ListValue(_f(v) for v in model)), ("Resid", ListValue(_f(v) for v in y - model))]
    variables = {label: value for label, value in rows if label != "RegEqn"}
    variables["RegEqn"] = UserFunction("stat.RegEqn", names, eqn)
    return StatResults("Multiple Linear Regression", rows, variables)
