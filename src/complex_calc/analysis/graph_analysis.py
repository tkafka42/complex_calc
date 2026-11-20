"""Numeric graph analysis used by the Graphs page (Analyze Graph menu):
Zero, Minimum, Maximum, Intersection, Inflection, dy/dx, Integral.

All functions take SymPy expressions in one variable and a search interval
[lower, upper], like the handheld asks for a lower and an upper bound.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import sympy as sp
from scipy import integrate as spi
from scipy.optimize import brentq, minimize_scalar

X = sp.Symbol("x")


class AnalysisError(Exception):
    pass


@dataclass
class Point:
    x: float
    y: float


def numeric(expr: sp.Expr, var: sp.Symbol = X):
    """Fast, safe numpy function of one variable (NaN outside the real domain)."""
    f = sp.lambdify(var, expr, modules=["numpy"])

    def evaluate(values):
        with np.errstate(all="ignore"):
            try:
                result = f(np.asarray(values, dtype=float) + 0j)
            except (ZeroDivisionError, ValueError, TypeError, OverflowError):
                arr = np.asarray(values, dtype=float)
                out = np.full(arr.shape, np.nan)
                for k, v in np.ndenumerate(arr):
                    try:
                        c = complex(f(complex(v)))
                        out[k] = c.real if abs(c.imag) < 1e-9 else np.nan
                    except (ZeroDivisionError, ValueError, TypeError, OverflowError):
                        pass
                return out
            result = np.asarray(result, dtype=complex) * np.ones_like(np.asarray(values, dtype=float))
            real = result.real.copy()
            real[np.abs(result.imag) > 1e-9 * np.maximum(1, np.abs(result.real))] = np.nan
            return real

    return evaluate


def scalar(expr: sp.Expr, var: sp.Symbol = X):
    vec = numeric(expr, var)
    return lambda t: float(vec(np.array([t]))[0])


def _check(lower: float, upper: float) -> tuple[float, float]:
    if not (math.isfinite(lower) and math.isfinite(upper)):
        raise AnalysisError("Bounds must be finite")
    if lower > upper:
        lower, upper = upper, lower
    if lower == upper:
        raise AnalysisError("Lower and upper bound must differ")
    return lower, upper


def _roots(f, lower: float, upper: float, samples: int = 2000) -> list[float]:
    xs = np.linspace(lower, upper, samples)
    ys = np.array([f(x) for x in xs])
    found = []
    for k in range(samples - 1):
        a, b, fa, fb = xs[k], xs[k + 1], ys[k], ys[k + 1]
        if np.isnan(fa) or np.isnan(fb):
            continue
        if fa == 0:
            found.append(float(a))
        elif fa * fb < 0:
            try:
                root = brentq(f, a, b, xtol=1e-14)
            except ValueError:
                continue
            if abs(f(root)) < 1e-6 * max(1.0, abs(fa), abs(fb)):
                found.append(float(root))
    if ys.size and ys[-1] == 0:
        found.append(float(xs[-1]))
    return found


def zero(expr: sp.Expr, lower: float, upper: float) -> Point:
    """First zero in [lower, upper] (also touching zeros such as x² at 0)."""
    lower, upper = _check(lower, upper)
    f = scalar(expr)
    roots = _roots(f, lower, upper)
    if not roots:
        # touching zero: minimum of |f| close to 0
        result = minimize_scalar(lambda t: abs(f(t)) if not math.isnan(f(t)) else math.inf,
                                 bounds=(lower, upper), method="bounded", options={"xatol": 1e-12})
        if abs(f(result.x)) < 1e-8:
            return Point(float(result.x), 0.0)
        raise AnalysisError("No zero in this interval")
    return Point(roots[0], 0.0)


def extremum(expr: sp.Expr, lower: float, upper: float, maximum: bool) -> Point:
    lower, upper = _check(lower, upper)
    f = scalar(expr)
    sign = -1.0 if maximum else 1.0
    xs = np.linspace(lower, upper, 2001)
    ys = np.array([sign * f(x) for x in xs])
    if np.all(np.isnan(ys)):
        raise AnalysisError("Function is undefined in this interval")
    k = int(np.nanargmin(ys))
    a, b = xs[max(k - 1, 0)], xs[min(k + 1, len(xs) - 1)]
    result = minimize_scalar(lambda t: sign * f(t) if not math.isnan(f(t)) else math.inf,
                             bounds=(a, b), method="bounded", options={"xatol": 1e-12})
    x = float(result.x)
    return Point(x, f(x))


def intersection(expr1: sp.Expr, expr2: sp.Expr, lower: float, upper: float) -> Point:
    lower, upper = _check(lower, upper)
    difference = scalar(expr1 - expr2)
    roots = _roots(difference, lower, upper)
    if not roots:
        raise AnalysisError("No intersection in this interval")
    x = roots[0]
    return Point(x, scalar(expr1)(x))


def inflection(expr: sp.Expr, lower: float, upper: float) -> Point:
    lower, upper = _check(lower, upper)
    second = sp.diff(expr, X, 2)
    roots = _roots(scalar(second), lower, upper)
    f = scalar(expr)
    for root in roots:
        # sign change of the second derivative
        d2 = scalar(second)
        h = max(1e-6, (upper - lower) * 1e-6)
        if d2(root - h) * d2(root + h) < 0:
            return Point(root, f(root))
    raise AnalysisError("No inflection point in this interval")


def derivative_at(expr: sp.Expr, x: float) -> float:
    value = sp.diff(expr, X).subs(X, x)
    try:
        return float(sp.N(value))
    except TypeError:
        raise AnalysisError("Derivative is not defined here")


def integral(expr: sp.Expr, lower: float, upper: float) -> float:
    if not (math.isfinite(lower) and math.isfinite(upper)):
        raise AnalysisError("Bounds must be finite")
    exact = sp.integrate(expr, (X, lower, upper))
    if not exact.has(sp.Integral) and exact.is_number and exact.is_finite:
        return float(sp.N(exact))
    f = scalar(expr)
    value, _ = spi.quad(f, lower, upper, limit=200)
    return float(value)


def table(expr: sp.Expr, start: float, step: float, rows: int = 20) -> list[tuple[float, float]]:
    f = numeric(expr)
    xs = start + step * np.arange(rows)
    return list(zip(xs.tolist(), f(xs).tolist()))
