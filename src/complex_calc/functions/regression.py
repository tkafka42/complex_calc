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


def _results(ctx, title: str, eqn_text: str, eqn: sp.Expr, rows: list, resid: ListValue) -> StatResults:
    all_rows = [("RegEqn", TextValue(eqn_text)), *rows, ("Resid", resid)]
    variables = {name: value for name, value in rows}
    variables["Resid"] = resid
    variables["RegEqn"] = UserFunction("stat.RegEqn", [X], eqn)
    return StatResults(title, all_rows, variables)


@builtin("LinRegMx", "LinRegMx X,Y[,Freq]", 2, 3, command=True, approx=True,
         summary="Linear regression y = m·x + b")
def lin_reg_mx(ctx, xs, ys, freq=None):
    x, y, w = _xy(xs, ys, freq, 2)
    m, b, r = _linear_fit(x, y, w)
    rows = [("m", _f(m)), ("b", _f(b)), ("r²", _f(r * r)), ("r", _f(r))]
    return _results(ctx, "Linear Regression (mx+b)", "m*x+b", _f(m) * X + _f(b), rows, _resid(y, m * x + b))


@builtin("LinRegBx", "LinRegBx X,Y[,Freq]", 2, 3, command=True, approx=True,
         summary="Linear regression y = a + b·x")
def lin_reg_bx(ctx, xs, ys, freq=None):
    x, y, w = _xy(xs, ys, freq, 2)
    m, b, r = _linear_fit(x, y, w)
    rows = [("a", _f(b)), ("b", _f(m)), ("r²", _f(r * r)), ("r", _f(r))]
    return _results(ctx, "Linear Regression (a+bx)", "a+b*x", _f(b) + _f(m) * X, rows, _resid(y, m * x + b))


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
    return _results(ctx, "Quadratic Regression", "a*x^2+b*x+c", eqn, rows, _resid(y, model))


@builtin("ExpReg", "ExpReg X,Y[,Freq]", 2, 3, command=True, approx=True,
         summary="Exponential regression y = a·bˣ")
def exp_reg(ctx, xs, ys, freq=None):
    x, y, w = _xy(xs, ys, freq, 2)
    if np.any(y <= 0):
        raise DomainError("ExpReg needs all y values > 0")
    m, intercept, r = _linear_fit(x, np.log(y), w)
    a, b = math.exp(intercept), math.exp(m)
    rows = [("a", _f(a)), ("b", _f(b)), ("r²", _f(r * r)), ("r", _f(r))]
    return _results(ctx, "Exponential Regression", "a*(b)^x", _f(a) * _f(b) ** X, rows, _resid(y, a * b**x))


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
    return _results(ctx, "Sinusoidal Regression", "a*sin(b*x+c)+d", eqn, rows, _resid(y, model(x, a, b, c, d)))
