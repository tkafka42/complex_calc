"""Confidence intervals and one-variable statistics (commands, no parentheses).

    zInterval σ,List[,Freq[,CLevel]]        (data input)
    zInterval σ,x̄,n[,CLevel]                 (stats input)
    tInterval List[,Freq[,CLevel]]          (data input)
    tInterval x̄,sx,n[,CLevel]                (stats input)
    OneVar List[,freqList]
"""

from __future__ import annotations

import math

import sympy as sp
from scipy import stats as sps

from ..core.errors import ArgumentError, DomainError
from ..core.values import ListValue, StatResults
from .registry import builtin, check_positive, to_float, to_float_list, to_int
from .stats import quartiles


def _f(x: float) -> sp.Float:
    return sp.Float(x, 15)


def _clevel(value) -> float:
    c = to_float(value, "CLevel")
    if 1 < c < 100:  # also accept 95 for 95 %
        c /= 100
    if not 0 < c < 1:
        raise DomainError("CLevel must be between 0 and 1 (e.g. 0.95)")
    return c


def _data_with_freq(values, freq) -> tuple[list[float], list[float]]:
    data = to_float_list(values, "List")
    if freq is None or (isinstance(freq, sp.Basic) and freq == 1):
        weights = [1.0] * len(data)
    elif isinstance(freq, ListValue):
        weights = to_float_list(freq, "Freq")
        if len(weights) != len(data):
            raise ArgumentError("Dimension mismatch: List and Freq must have the same length")
    else:
        weights = [to_float(freq, "Freq")] * len(data)
    return data, weights


def _mean_sx(data: list[float], weights: list[float]) -> tuple[float, float, float]:
    n = sum(weights)
    if n < 2:
        raise DomainError("At least 2 data points are required")
    mean = sum(x * w for x, w in zip(data, weights)) / n
    ss = sum(w * (x - mean) ** 2 for x, w in zip(data, weights))
    return mean, math.sqrt(ss / (n - 1)), n


def _pair(lo: float, hi: float) -> ListValue:
    return ListValue([_f(lo), _f(hi)])


@builtin("zInterval", "zInterval σ,x̄,n[,CLevel]  |  zInterval σ,List[,Freq[,CLevel]]", 2, 4,
         command=True, approx=True, summary="z confidence interval for μ (σ known)")
def z_interval(ctx, sigma, second, third=None, fourth=None):
    s = to_float(sigma, "σ")
    check_positive(s, "σ")
    if isinstance(second, ListValue):  # data input
        data, weights = _data_with_freq(second, third)
        c = _clevel(fourth if fourth is not None else 0.95)
        mean, sx, n = _mean_sx(data, weights)
    else:  # stats input
        if third is None:
            raise ArgumentError("Too few arguments: zInterval σ,x̄,n[,CLevel]")
        mean = to_float(second, "x̄")
        n = to_int(third, "n")
        check_positive(n, "n")
        c = _clevel(fourth if fourth is not None else 0.95)
        sx = None
    me = sps.norm.ppf((1 + c) / 2) * s / math.sqrt(n)
    rows = [
        ("CLower, CUpper", _pair(mean - me, mean + me)),
        ("x̄", _f(mean)),
        ("ME", _f(me)),
    ]
    if sx is not None:
        rows.append(("sx", _f(sx)))
    rows += [("n", sp.Integer(int(n)) if float(n).is_integer() else _f(n)), ("σ", _f(s))]
    variables = {"CLower": _f(mean - me), "CUpper": _f(mean + me), "x̄": _f(mean), "ME": _f(me),
                 "n": rows[-2][1], "σ": _f(s)}
    if sx is not None:
        variables["sx"] = _f(sx)
    return StatResults("z Interval", rows, variables)


@builtin("tInterval", "tInterval x̄,sx,n[,CLevel]  |  tInterval List[,Freq[,CLevel]]", 1, 4,
         command=True, approx=True, summary="t confidence interval for μ (σ unknown)")
def t_interval(ctx, first, second=None, third=None, fourth=None):
    if isinstance(first, ListValue):  # data input
        if fourth is not None:
            raise ArgumentError("Too many arguments: tInterval List[,Freq[,CLevel]]")
        data, weights = _data_with_freq(first, second)
        c = _clevel(third if third is not None else 0.95)
        mean, sx, n = _mean_sx(data, weights)
    else:
        if second is None or third is None:
            raise ArgumentError("Too few arguments: tInterval x̄,sx,n[,CLevel]")
        mean = to_float(first, "x̄")
        sx = to_float(second, "sx")
        check_positive(sx, "sx")
        n = to_int(third, "n")
        if n < 2:
            raise DomainError("n must be ≥ 2")
        c = _clevel(fourth if fourth is not None else 0.95)
    df = n - 1
    me = sps.t.ppf((1 + c) / 2, df) * sx / math.sqrt(n)
    n_value = sp.Integer(int(n)) if float(n).is_integer() else _f(n)
    df_value = sp.Integer(int(df)) if float(df).is_integer() else _f(df)
    rows = [
        ("CLower, CUpper", _pair(mean - me, mean + me)),
        ("x̄", _f(mean)),
        ("ME", _f(me)),
        ("df", df_value),
        ("sx", _f(sx)),
        ("n", n_value),
    ]
    variables = {"CLower": _f(mean - me), "CUpper": _f(mean + me), "x̄": _f(mean), "ME": _f(me),
                 "df": df_value, "sx": _f(sx), "n": n_value}
    return StatResults("t Interval", rows, variables)


@builtin("OneVar", "OneVar List[,freqList]", 1, 2, command=True, approx=True,
         summary="One-variable statistics")
def one_var(ctx, values, freq=None):
    data, weights = _data_with_freq(values, freq)
    n = sum(weights)
    if n < 1:
        raise DomainError("List is empty")
    mean = sum(x * w for x, w in zip(data, weights)) / n
    sum_x = sum(x * w for x, w in zip(data, weights))
    sum_x2 = sum(x * x * w for x, w in zip(data, weights))
    ssx = sum(w * (x - mean) ** 2 for x, w in zip(data, weights))
    sx = math.sqrt(ssx / (n - 1)) if n > 1 else float("nan")
    sigma_x = math.sqrt(ssx / n)
    expanded: list[float] = []
    for x, w in zip(data, weights):
        expanded.extend([x] * int(round(w)))
    expanded.sort()
    q1, q3 = quartiles(expanded)
    mid = len(expanded) // 2
    median = expanded[mid] if len(expanded) % 2 else (expanded[mid - 1] + expanded[mid]) / 2
    n_value = sp.Integer(int(n)) if float(n).is_integer() else _f(n)
    rows = [
        ("x̄", _f(mean)),
        ("Σx", _f(sum_x)),
        ("Σx²", _f(sum_x2)),
        ("sx := sn-1x", _f(sx) if not math.isnan(sx) else sp.nan),
        ("σx := σnx", _f(sigma_x)),
        ("n", n_value),
        ("MinX", _f(expanded[0])),
        ("Q₁X", _f(q1)),
        ("MedianX", _f(median)),
        ("Q₃X", _f(q3)),
        ("MaxX", _f(expanded[-1])),
        ("SSX := Σ(x-x̄)²", _f(ssx)),
    ]
    variables = {"x̄": _f(mean), "Σx": _f(sum_x), "Σx²": _f(sum_x2), "sx": rows[3][1],
                 "σx": _f(sigma_x), "n": n_value, "MinX": _f(expanded[0]), "Q₁X": _f(q1),
                 "MedianX": _f(median), "Q₃X": _f(q3), "MaxX": _f(expanded[-1]), "SSX": _f(ssx)}
    return StatResults("One-Variable Statistics", rows, variables)
