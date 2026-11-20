"""Finance functions: TVM (tvmN, tvmI, tvmPV, tvmPmt, tvmFV), amortTbl, bal,
ΣInt, ΣPrn, npv, irr, mirr, eff, nom, dbd.

Sign convention as on the handheld: money received is positive, money paid
is negative. I is the annual interest rate in percent.
"""

from __future__ import annotations

import datetime as dt
import math

import sympy as sp
from scipy.optimize import brentq

from ..core.errors import ArgumentError, DomainError
from ..core.values import ListValue, is_matrix
from .registry import builtin, to_float, to_float_list, to_int


def _f(x: float) -> sp.Float:
    return sp.Float(float(x), 15)


def _opt(value, default):
    return default if value is None or (isinstance(value, sp.Basic) and value is sp.nan) else to_float(value, "argument")


def _rate(i_annual: float, ppy: float, cpy: float) -> float:
    return (1 + i_annual / 100 / cpy) ** (cpy / ppy) - 1


def _tvm_residual(n, i_annual, pv, pmt, fv, ppy, cpy, at) -> float:
    i = _rate(i_annual, ppy, cpy)
    if abs(i) < 1e-14:
        return pv + pmt * n + fv
    g = 1 + i * at
    growth = (1 + i) ** n
    return pv * growth + pmt * g * (growth - 1) / i + fv


def _common(ppy, cpy, at):
    p = _opt(ppy, 1.0)
    c = _opt(cpy, p)
    a = _opt(at, 0.0)
    return p, c, a


@builtin("tvmFV", "tvmFV(N,I,PV,Pmt,[PpY],[CpY],[PmtAt])", 4, 7, approx=True, summary="Future value")
def tvm_fv(ctx, n, i, pv, pmt, ppy=None, cpy=None, at=None):
    p, c, a = _common(ppy, cpy, at)
    return _f(-_tvm_residual(to_float(n, "N"), to_float(i, "I"), to_float(pv, "PV"), to_float(pmt, "Pmt"), 0, p, c, a))


@builtin("tvmPV", "tvmPV(N,I,Pmt,FV,[PpY],[CpY],[PmtAt])", 4, 7, approx=True, summary="Present value")
def tvm_pv(ctx, n, i, pmt, fv, ppy=None, cpy=None, at=None):
    p, c, a = _common(ppy, cpy, at)
    nn, ii = to_float(n, "N"), to_float(i, "I")
    rate = _rate(ii, p, c)
    rest = _tvm_residual(nn, ii, 0, to_float(pmt, "Pmt"), to_float(fv, "FV"), p, c, a)
    return _f(-rest / (1 + rate) ** nn)


@builtin("tvmPmt", "tvmPmt(N,I,PV,FV,[PpY],[CpY],[PmtAt])", 4, 7, approx=True, summary="Payment per period")
def tvm_pmt(ctx, n, i, pv, fv, ppy=None, cpy=None, at=None):
    p, c, a = _common(ppy, cpy, at)
    nn, ii, pvv, fvv = to_float(n, "N"), to_float(i, "I"), to_float(pv, "PV"), to_float(fv, "FV")
    base = _tvm_residual(nn, ii, pvv, 0, fvv, p, c, a)
    per_unit = _tvm_residual(nn, ii, 0, 1, 0, p, c, a)
    return _f(-base / per_unit)


@builtin("tvmN", "tvmN(I,PV,Pmt,FV,[PpY],[CpY],[PmtAt])", 4, 7, approx=True, summary="Number of payment periods")
def tvm_n(ctx, i, pv, pmt, fv, ppy=None, cpy=None, at=None):
    p, c, a = _common(ppy, cpy, at)
    ii, pvv, pmtv, fvv = to_float(i, "I"), to_float(pv, "PV"), to_float(pmt, "Pmt"), to_float(fv, "FV")
    rate = _rate(ii, p, c)
    if abs(rate) < 1e-14:
        if pmtv == 0:
            raise DomainError("No solution found")
        return _f(-(pvv + fvv) / pmtv)
    g = 1 + rate * a
    k = pmtv * g / rate
    if pvv + k == 0:
        raise DomainError("No solution found")
    value = (k - fvv) / (pvv + k)
    if value <= 0:
        raise DomainError("No solution found")
    return _f(math.log(value) / math.log(1 + rate))


@builtin("tvmI", "tvmI(N,PV,Pmt,FV,[PpY],[CpY],[PmtAt])", 4, 7, approx=True, summary="Annual interest rate in %")
def tvm_i(ctx, n, pv, pmt, fv, ppy=None, cpy=None, at=None):
    p, c, a = _common(ppy, cpy, at)
    nn, pvv, pmtv, fvv = to_float(n, "N"), to_float(pv, "PV"), to_float(pmt, "Pmt"), to_float(fv, "FV")

    def f(rate):
        return _tvm_residual(nn, rate, pvv, pmtv, fvv, p, c, a)

    grid = [-99.0, -50.0, -10.0, -1.0, 1e-9, 1.0, 5.0, 10.0, 20.0, 50.0, 100.0, 500.0, 1000.0]
    for lo, hi in zip(grid, grid[1:]):
        try:
            if f(lo) * f(hi) <= 0:
                return _f(brentq(f, lo, hi, xtol=1e-14))
        except (OverflowError, ZeroDivisionError, ValueError):
            continue
    raise DomainError("No solution found")


def _amort_rows(npmt, n, i, pv, pmt, fv, ppy, cpy, at, round_value):
    p, c, a = _common(ppy, cpy, at)
    nn, ii, pvv = to_float(n, "N"), to_float(i, "I"), to_float(pv, "PV")
    fvv = _opt(fv, 0.0)
    if pmt is None or pmt is sp.nan:
        pmtv = float(tvm_pmt(None, sp.Float(nn), sp.Float(ii), sp.Float(pvv), sp.Float(fvv), sp.Float(p),
                             sp.Float(c), sp.Float(a)))
    else:
        pmtv = to_float(pmt, "Pmt")
    digits = int(_opt(round_value, 2))
    pmtv = round(pmtv, digits)
    rate = _rate(ii, p, c)
    balance = pvv
    rows = []
    for k in range(1, to_int(npmt, "NPmt") + 1):
        interest = round(-balance * rate, digits) if a == 0 else round(-(balance + pmtv) * rate, digits)
        principal = round(pmtv - interest, digits)
        balance = round(balance + principal, digits)
        rows.append([k, interest, principal, balance])
    return rows


@builtin("amortTbl", "amortTbl(NPmt,N,I,PV,[Pmt],[FV],[PpY],[CpY],[PmtAt],[roundValue])", 4, 10, approx=True,
         summary="Amortization table: payment, interest, principal, balance")
def amort_tbl(ctx, npmt, n, i, pv, pmt=None, fv=None, ppy=None, cpy=None, at=None, round_value=None):
    rows = _amort_rows(npmt, n, i, pv, pmt, fv, ppy, cpy, at, round_value)
    return sp.ImmutableMatrix([[sp.Integer(r[0]), _f(r[1]), _f(r[2]), _f(r[3])] for r in rows])


def _table_or_args(first_args: list, rest: tuple, count: int):
    """bal(NPmt,amortTable) or bal(NPmt,N,I,PV,…); returns the rows."""
    if rest and is_matrix(rest[0]):
        table = rest[0]
        return [[float(table[r, c]) for c in range(4)] for r in range(table.rows)]
    if len(rest) < 3:
        raise ArgumentError("Too few arguments")
    padded = list(rest) + [None] * (9 - len(rest))
    return _amort_rows(count, *padded[:9])


@builtin("bal", "bal(NPmt,N,I,PV,[Pmt],[FV],[PpY],[CpY],[PmtAt],[roundValue])  |  bal(NPmt,amortTable)", 2, 10,
         approx=True, summary="Balance after NPmt payments")
def bal_(ctx, npmt, *rest):
    k = to_int(npmt, "NPmt")
    rows = _table_or_args([], rest, k)
    if not 1 <= k <= len(rows):
        raise DomainError("NPmt out of range")
    return _f(rows[k - 1][3])


@builtin("ΣInt", "ΣInt(NPmt1,NPmt2,N,I,PV,…)  |  ΣInt(NPmt1,NPmt2,amortTable)", 3, 11, aliases=("sumInt",),
         approx=True, summary="Sum of interest paid in payments NPmt1..NPmt2")
def sum_int(ctx, first, second, *rest):
    a, b = to_int(first, "NPmt1"), to_int(second, "NPmt2")
    rows = _table_or_args([], rest, b)
    return _f(sum(r[1] for r in rows[a - 1:b]))


@builtin("ΣPrn", "ΣPrn(NPmt1,NPmt2,N,I,PV,…)  |  ΣPrn(NPmt1,NPmt2,amortTable)", 3, 11, aliases=("sumPrn",),
         approx=True, summary="Sum of principal paid in payments NPmt1..NPmt2")
def sum_prn(ctx, first, second, *rest):
    a, b = to_int(first, "NPmt1"), to_int(second, "NPmt2")
    rows = _table_or_args([], rest, b)
    return _f(sum(r[2] for r in rows[a - 1:b]))


def _cash_flows(cf0, cf_list, freq) -> list[float]:
    flows = to_float_list(cf_list, "CFList") if isinstance(cf_list, ListValue) else [to_float(cf_list, "CFList")]
    counts = [int(v) for v in to_float_list(freq, "CFFreq")] if freq is not None else [1] * len(flows)
    out = [to_float(cf0, "CF0")]
    for value, count in zip(flows, counts):
        out += [value] * count
    return out


def _npv(rate: float, flows: list[float]) -> float:
    return sum(v / (1 + rate) ** k for k, v in enumerate(flows))


@builtin("npv", "npv(InterestRate,CFO,CFList[,CFFreq])", 3, 4, approx=True, summary="Net present value")
def npv_(ctx, rate, cf0, cf_list, freq=None):
    return _f(_npv(to_float(rate, "InterestRate") / 100, _cash_flows(cf0, cf_list, freq)))


@builtin("irr", "irr(CF0,CFList[,CFFreq])", 2, 3, approx=True, summary="Internal rate of return in %")
def irr_(ctx, cf0, cf_list, freq=None):
    flows = _cash_flows(cf0, cf_list, freq)
    grid = [-0.99, -0.5, -0.1, 0.0, 0.05, 0.1, 0.2, 0.5, 1.0, 5.0, 10.0]
    for lo, hi in zip(grid, grid[1:]):
        if _npv(lo, flows) * _npv(hi, flows) <= 0:
            return _f(brentq(lambda r: _npv(r, flows), lo, hi, xtol=1e-14) * 100)
    raise DomainError("No solution found")


@builtin("mirr", "mirr(financeRate,reinvestRate,CF0,CFList[,CFFreq])", 4, 5, approx=True,
         summary="Modified internal rate of return in %")
def mirr_(ctx, finance_rate, reinvest_rate, cf0, cf_list, freq=None):
    flows = _cash_flows(cf0, cf_list, freq)
    f, r = to_float(finance_rate, "financeRate") / 100, to_float(reinvest_rate, "reinvestRate") / 100
    n = len(flows) - 1
    future_positive = sum(v * (1 + r) ** (n - k) for k, v in enumerate(flows) if v > 0)
    present_negative = sum(v / (1 + f) ** k for k, v in enumerate(flows) if v < 0)
    if present_negative == 0 or n == 0:
        raise DomainError("No solution found")
    return _f(((future_positive / -present_negative) ** (1 / n) - 1) * 100)


@builtin("eff", "eff(nominalRate,CpY)", 2, approx=True, summary="Effective annual rate from nominal rate")
def eff_(ctx, nominal, cpy):
    c = to_float(cpy, "CpY")
    return _f(((1 + to_float(nominal, "nominalRate") / 100 / c) ** c - 1) * 100)


@builtin("nom", "nom(effectiveRate,CpY)", 2, approx=True, summary="Nominal rate from effective annual rate")
def nom_(ctx, effective, cpy):
    c = to_float(cpy, "CpY")
    return _f(((1 + to_float(effective, "effectiveRate") / 100) ** (1 / c) - 1) * c * 100)


def _parse_date(value) -> dt.date:
    text = f"{to_float(value, 'date'):.6f}".rstrip("0")
    whole, _, frac = text.partition(".")
    frac = (frac + "0000")[:4]
    if len(whole) <= 2:  # MM.DDYY
        month, day, year = int(whole), int(frac[:2]), int(frac[2:4])
    else:  # DDMM.YY
        whole = whole.zfill(4)
        day, month, year = int(whole[:2]), int(whole[2:4]), int(frac[:2])
    year += 1900 if year >= 50 else 2000
    return dt.date(year, month, day)


@builtin("dbd", "dbd(date1,date2)", 2, summary="Days between dates (MM.DDYY or DDMM.YY, years 1950–2049)")
def dbd_(ctx, date1, date2):
    try:
        return sp.Integer((_parse_date(date2) - _parse_date(date1)).days)
    except ValueError:
        raise DomainError("Invalid date")
