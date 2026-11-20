"""Probability distributions and list statistics.

Argument orders follow the handheld reference guide, e.g.
normCdf(lowBound,upBound[,μ[,σ]]) and binomCdf(n,p,lowBound,upBound).
"""

from __future__ import annotations

import math

import sympy as sp
from scipy import stats as sps

from ..core.errors import ArgumentError, DomainError
from ..core.values import ListValue
from .registry import (
    builtin,
    check_positive,
    check_probability,
    to_float,
    to_float_list,
    to_int,
    to_list,
)


def _num(x: float) -> sp.Float:
    return sp.Float(x, 15)


# ------------------------------------------------------------- normal


@builtin("normPdf", "normPdf(XVal[,μ[,σ]])", 1, 3, approx=True, listable=(0,),
         summary="Normal probability density")
def norm_pdf(ctx, x, mu=0, sigma=1):
    s = to_float(sigma, "σ")
    check_positive(s, "σ")
    return _num(sps.norm.pdf(to_float(x, "XVal"), to_float(mu, "μ"), s))


@builtin("normCdf", "normCdf(lowBound,upBound[,μ[,σ]])", 2, 4, approx=True, listable=(0, 1),
         summary="Normal cumulative probability between two bounds")
def norm_cdf(ctx, low, up, mu=0, sigma=1):
    s = to_float(sigma, "σ")
    check_positive(s, "σ")
    m = to_float(mu, "μ")
    lo, hi = to_float(low, "lowBound"), to_float(up, "upBound")
    return _num(sps.norm.cdf(hi, m, s) - sps.norm.cdf(lo, m, s))


@builtin("invNorm", "invNorm(Area[,μ[,σ]])", 1, 3, approx=True, listable=(0,),
         summary="Inverse cumulative normal (left tail)")
def inv_norm(ctx, area, mu=0, sigma=1):
    a = to_float(area, "Area")
    if not 0 < a < 1:
        raise DomainError("Area must be between 0 and 1")
    s = to_float(sigma, "σ")
    check_positive(s, "σ")
    return _num(sps.norm.ppf(a, to_float(mu, "μ"), s))


# ------------------------------------------------------------- Student t


def _df(value) -> float:
    df = to_float(value, "df")
    check_positive(df, "df")
    return df


@builtin("tPdf", "tPdf(XVal,df)", 2, approx=True, listable=(0,), summary="Student-t probability density")
def t_pdf(ctx, x, df):
    return _num(sps.t.pdf(to_float(x, "XVal"), _df(df)))


@builtin("tCdf", "tCdf(lowBound,upBound,df)", 3, approx=True, listable=(0, 1),
         summary="Student-t cumulative probability between two bounds")
def t_cdf(ctx, low, up, df):
    d = _df(df)
    lo, hi = to_float(low, "lowBound"), to_float(up, "upBound")
    return _num(sps.t.cdf(hi, d) - sps.t.cdf(lo, d))


@builtin("invt", "invt(Area,df)", 2, approx=True, listable=(0,), summary="Inverse cumulative Student-t")
def inv_t(ctx, area, df):
    a = to_float(area, "Area")
    if not 0 < a < 1:
        raise DomainError("Area must be between 0 and 1")
    return _num(sps.t.ppf(a, _df(df)))


# ------------------------------------------------------------- χ²


@builtin("χ²Pdf", "χ²Pdf(XVal,df)", 2, aliases=("chi2Pdf",), approx=True, listable=(0,),
         summary="χ² probability density")
def chi2_pdf(ctx, x, df):
    return _num(sps.chi2.pdf(to_float(x, "XVal"), _df(df)))


@builtin("χ²Cdf", "χ²Cdf(lowBound,upBound,df)", 3, aliases=("chi2Cdf",), approx=True, listable=(0, 1),
         summary="χ² cumulative probability between two bounds")
def chi2_cdf(ctx, low, up, df):
    d = _df(df)
    return _num(sps.chi2.cdf(to_float(up, "upBound"), d) - sps.chi2.cdf(to_float(low, "lowBound"), d))


# ------------------------------------------------------------- binomial


def _binom_params(n, p) -> tuple[int, float]:
    trials = to_int(n, "n")
    if trials < 0:
        raise DomainError("n must be ≥ 0")
    prob = to_float(p, "p")
    check_probability(prob)
    return trials, prob


@builtin("binomPdf", "binomPdf(n,p[,XVal])", 2, 3, approx=True, listable=(2,),
         summary="Binomial probability P(X = XVal); list of all if XVal omitted")
def binom_pdf(ctx, n, p, x=None):
    trials, prob = _binom_params(n, p)
    if x is None:
        return ListValue(_num(v) for v in sps.binom.pmf(range(trials + 1), trials, prob))
    k = to_float(x, "XVal")
    if k != int(k):
        return _num(0.0)
    return _num(sps.binom.pmf(int(k), trials, prob))


@builtin("binomCdf", "binomCdf(n,p[,lowBound],upBound)", 2, 4, approx=True, listable=(2, 3),
         summary="Binomial cumulative probability P(lowBound ≤ X ≤ upBound)")
def binom_cdf(ctx, n, p, *bounds):
    trials, prob = _binom_params(n, p)
    if not bounds:
        return ListValue(_num(v) for v in sps.binom.cdf(range(trials + 1), trials, prob))
    if len(bounds) == 1:
        lo, hi = -math.inf, to_float(bounds[0], "upBound")
    else:
        lo, hi = to_float(bounds[0], "lowBound"), to_float(bounds[1], "upBound")
    if lo > hi:
        return _num(0.0)
    lower_k = math.ceil(lo) if not math.isinf(lo) else 0
    upper_k = math.floor(hi) if not math.isinf(hi) else trials
    return _num(sps.binom.cdf(upper_k, trials, prob) - sps.binom.cdf(lower_k - 1, trials, prob))


@builtin("invBinom", "invBinom(CumulativeProb,NumTrials,Prob[,OutputForm])", 3, 4, approx=True,
         summary="Smallest k with binomCdf(n,p,0,k) ≥ CumulativeProb")
def inv_binom(ctx, cum, n, p, output_form=None):
    c = to_float(cum, "CumulativeProb")
    check_probability(c, "CumulativeProb")
    trials, prob = _binom_params(n, p)
    k = int(sps.binom.ppf(c, trials, prob))
    if output_form is not None and to_float(output_form, "OutputForm") == 1:
        return sp.ImmutableMatrix([[k - 1, _num(sps.binom.cdf(k - 1, trials, prob))],
                                   [k, _num(sps.binom.cdf(k, trials, prob))]])
    return sp.Integer(k)


# ------------------------------------------------------------- Poisson / geometric


def _lambda(value) -> float:
    lam = to_float(value, "λ")
    check_positive(lam, "λ")
    return lam


@builtin("poissPdf", "poissPdf(λ,XVal)", 2, approx=True, listable=(1,), summary="Poisson probability P(X = XVal)")
def poiss_pdf(ctx, lam, x):
    k = to_float(x, "XVal")
    if k != int(k) or k < 0:
        return _num(0.0)
    return _num(sps.poisson.pmf(int(k), _lambda(lam)))


@builtin("poissCdf", "poissCdf(λ,lowBound,upBound)", 2, 3, approx=True, listable=(1, 2),
         summary="Poisson cumulative probability P(lowBound ≤ X ≤ upBound)")
def poiss_cdf(ctx, lam, *bounds):
    mu = _lambda(lam)
    if len(bounds) == 1:
        lo, hi = -math.inf, to_float(bounds[0], "upBound")
    else:
        lo, hi = to_float(bounds[0], "lowBound"), to_float(bounds[1], "upBound")
    if lo > hi:
        return _num(0.0)
    lower_k = max(math.ceil(lo), 0) if not math.isinf(lo) else 0
    upper = sps.poisson.cdf(math.floor(hi), mu) if not math.isinf(hi) else 1.0
    return _num(upper - sps.poisson.cdf(lower_k - 1, mu))


@builtin("geomPdf", "geomPdf(p,XVal)", 2, approx=True, listable=(1,), summary="Geometric probability P(X = XVal)")
def geom_pdf(ctx, p, x):
    prob = to_float(p, "p")
    check_probability(prob)
    return _num(sps.geom.pmf(to_int(x, "XVal"), prob))


@builtin("geomCdf", "geomCdf(p,lowBound,upBound)", 2, 3, approx=True, summary="Geometric cumulative probability")
def geom_cdf(ctx, p, *bounds):
    prob = to_float(p, "p")
    check_probability(prob)
    if len(bounds) == 1:
        lo, hi = 1, to_int(bounds[0], "upBound")
    else:
        lo, hi = to_int(bounds[0], "lowBound"), to_int(bounds[1], "upBound")
    return _num(sps.geom.cdf(hi, prob) - sps.geom.cdf(lo - 1, prob))


# ------------------------------------------------------------- list statistics


def _weighted(values, freq) -> tuple[list, list]:
    data = to_list(values, "List")
    if freq is None:
        return data, [sp.Integer(1)] * len(data)
    weights = to_list(freq, "freqList")
    if len(weights) != len(data):
        raise ArgumentError("Dimension mismatch: List and freqList must have the same length")
    return data, weights


@builtin("mean", "mean(List[,freqList])", 1, 2, summary="Arithmetic mean")
def mean_(ctx, values, freq=None):
    data, w = _weighted(values, freq)
    total = sum(w)
    if total == 0:
        raise DomainError("List is empty")
    return sum(a * b for a, b in zip(data, w)) / total


def _variance(values, freq, sample: bool):
    data, w = _weighted(values, freq)
    n = sum(w)
    if n == 0 or (sample and n < 2):
        raise DomainError("Not enough data")
    m = sum(a * b for a, b in zip(data, w)) / n
    ss = sum(b * (a - m) ** 2 for a, b in zip(data, w))
    return sp.simplify(ss / (n - 1 if sample else n))


@builtin("varSamp", "varSamp(List[,freqList])", 1, 2, summary="Sample variance")
def var_samp(ctx, values, freq=None):
    return _variance(values, freq, True)


@builtin("varPop", "varPop(List[,freqList])", 1, 2, summary="Population variance")
def var_pop(ctx, values, freq=None):
    return _variance(values, freq, False)


@builtin("stDevSamp", "stDevSamp(List[,freqList])", 1, 2, summary="Sample standard deviation (sx)")
def stdev_samp(ctx, values, freq=None):
    return sp.sqrt(_variance(values, freq, True))


@builtin("stDevPop", "stDevPop(List[,freqList])", 1, 2, summary="Population standard deviation (σx)")
def stdev_pop(ctx, values, freq=None):
    return sp.sqrt(_variance(values, freq, False))


def _expand_freq(values, freq) -> list:
    data, w = _weighted(values, freq)
    out = []
    for value, weight in zip(data, w):
        out.extend([value] * to_int(weight, "frequency"))
    return out


def _median_of(sorted_values: list):
    n = len(sorted_values)
    if n == 0:
        raise DomainError("List is empty")
    mid = n // 2
    if n % 2:
        return sorted_values[mid]
    return (sorted_values[mid - 1] + sorted_values[mid]) / 2


def _sort_key(v):
    return float(sp.N(v))


@builtin("median", "median(List[,freqList])", 1, 2, summary="Median")
def median_(ctx, values, freq=None):
    return _median_of(sorted(_expand_freq(values, freq), key=_sort_key))


@builtin("sum", "sum(List[,Start[,End]])", 1, 3, summary="Sum of list elements")
def sum_(ctx, values, start=1, end=None):
    data = to_list(values, "List")
    s = to_int(start, "Start") - 1
    e = len(data) if end is None else to_int(end, "End")
    return sp.Add(*data[s:e])


@builtin("product", "product(List[,Start[,End]])", 1, 3, summary="Product of list elements")
def product_(ctx, values, start=1, end=None):
    data = to_list(values, "List")
    s = to_int(start, "Start") - 1
    e = len(data) if end is None else to_int(end, "End")
    return sp.Mul(*data[s:e])


@builtin("min", "min(List) or min(Expr1,Expr2)", 1, 2, summary="Minimum")
def min_(ctx, a, b=None):
    data = to_list(a, "List") if b is None else [a, b]
    return sp.Min(*data)


@builtin("max", "max(List) or max(Expr1,Expr2)", 1, 2, summary="Maximum")
def max_(ctx, a, b=None):
    data = to_list(a, "List") if b is None else [a, b]
    return sp.Max(*data)


# Shared with intervals / OneVar
def quartiles(sorted_values: list) -> tuple:
    """Q1/Q3 as median of the lower/upper half (median excluded for odd n)."""
    n = len(sorted_values)
    half = n // 2
    lower = sorted_values[:half]
    upper = sorted_values[half + (n % 2):]
    if not lower:
        return sorted_values[0], sorted_values[-1]
    return _median_of(lower), _median_of(upper)


def expand_with_freq(values, freq) -> list:
    return _expand_freq(values, freq)


def float_data(values, label="List") -> list[float]:
    return to_float_list(values, label)
