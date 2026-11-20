"""Remaining reference-guide functions: polar/rectangular coordinates,
freqTable►list, interpolate, warnCodes, ANOVA2way, MultRegTests, MultRegIntervals."""

from __future__ import annotations

import math

import numpy as np
import sympy as sp
from scipy import stats as sps

from ..core.errors import ArgumentError, DomainError
from ..core.values import ListValue, StatResults, TextValue, UserFunction
from .intervals import _clevel
from .registry import builtin, to_float, to_float_list, to_int


def _f(x: float) -> sp.Float:
    x = float(x)
    return sp.Float(0.0 if abs(x) < 1e-13 else x, 15)


def _to_rad(ctx, angle):
    return {"rad": angle, "deg": angle * sp.pi / 180, "grad": angle * sp.pi / 200}[ctx.settings.angle]


def _from_rad(ctx, angle):
    return {"rad": angle, "deg": angle * 180 / sp.pi, "grad": angle * 200 / sp.pi}[ctx.settings.angle]


@builtin("P►Rx", "P►Rx(rExpr,θExpr)", 2, aliases=("P@>Rx",), listable=(0, 1), summary="x from polar (r,θ)")
def p_to_rx(ctx, r, theta):
    return sp.simplify(r * sp.cos(_to_rad(ctx, theta)))


@builtin("P►Ry", "P►Ry(rExpr,θExpr)", 2, aliases=("P@>Ry",), listable=(0, 1), summary="y from polar (r,θ)")
def p_to_ry(ctx, r, theta):
    return sp.simplify(r * sp.sin(_to_rad(ctx, theta)))


@builtin("R►Pr", "R►Pr(xExpr,yExpr)", 2, aliases=("R@>Pr",), listable=(0, 1), summary="r from rectangular (x,y)")
def r_to_pr(ctx, x, y):
    return sp.sqrt(x**2 + y**2)


@builtin("R►Pθ", "R►Pθ(xExpr,yExpr)", 2, aliases=("R@>Ptheta", "R►Ptheta"), listable=(0, 1),
         summary="θ from rectangular (x,y)")
def r_to_ptheta(ctx, x, y):
    return _from_rad(ctx, sp.atan2(y, x))


@builtin("freqTable►list", "freqTable►list(List1,freqIntegerList)", 2, aliases=("freqTable@>list",),
         summary="Expand a list by frequencies")
def freq_table_to_list(ctx, values, freq):
    if not isinstance(values, ListValue) or not isinstance(freq, ListValue) or len(values) != len(freq):
        raise ArgumentError("Two lists of equal length expected")
    out = []
    for value, count in zip(values, freq):
        out += [value] * to_int(count, "frequency")
    return ListValue(out)


@builtin("interpolate", "interpolate(xValue,xList,yList,yPrimeList)", 4, listable=(0,),
         summary="Cubic Hermite interpolation")
def interpolate_(ctx, x_value, xs, ys, dys):
    x = to_float_list(xs, "xList")
    y = to_float_list(ys, "yList")
    d = to_float_list(dys, "yPrimeList")
    if not (len(x) == len(y) == len(d)) or len(x) < 2:
        raise ArgumentError("Lists must have equal dimension ≥ 2")
    t = to_float(x_value, "xValue")
    for k in range(len(x) - 1):
        a, b = sorted((x[k], x[k + 1]))
        if a <= t <= b:
            h = x[k + 1] - x[k]
            s = (t - x[k]) / h
            h00, h10 = 2 * s**3 - 3 * s**2 + 1, s**3 - 2 * s**2 + s
            h01, h11 = -2 * s**3 + 3 * s**2, s**3 - s**2
            return _f(h00 * y[k] + h10 * h * d[k] + h01 * y[k + 1] + h11 * h * d[k + 1])
    return sp.nan


@builtin("warnCodes", "warnCodes(Expr1,StatusVar)", 2, hold=(1,), summary="Evaluate and store warning codes")
def warn_codes(ctx, value, status):
    ctx.store(status.name, ListValue())
    return value


# ------------------------------------------------------------------ ANOVA2way


@builtin("ANOVA2way", "ANOVA2way List1,List2[,List3,…,List10][,levRow]", 2, 11, command=True, approx=True,
         summary="Two-way analysis of variance (block design or two factor)")
def anova_2way(ctx, *args):
    lists = [a for a in args if isinstance(a, ListValue)]
    rest = [a for a in args if not isinstance(a, ListValue)]
    lev_row = to_int(rest[0], "levRow") if rest else 0
    data = np.array([to_float_list(lst, "List") for lst in lists]).T  # rows × columns
    n_rows, n_cols = data.shape
    grand = data.mean()
    if lev_row == 0:  # randomized block design
        ss_col = n_rows * ((data.mean(axis=0) - grand) ** 2).sum()
        ss_block = n_cols * ((data.mean(axis=1) - grand) ** 2).sum()
        ss_total = ((data - grand) ** 2).sum()
        ss_error = ss_total - ss_col - ss_block
        df_col, df_block = n_cols - 1, n_rows - 1
        df_error = df_col * df_block
        ms_col, ms_block, ms_error = ss_col / df_col, ss_block / df_block, ss_error / df_error
        f_col, f_block = ms_col / ms_error, ms_block / ms_error
        rows = [("F", _f(f_col)), ("PVal", _f(sps.f.sf(f_col, df_col, df_error))), ("df", sp.Integer(df_col)),
                ("SS", _f(ss_col)), ("MS", _f(ms_col)), ("FBlock", _f(f_block)),
                ("PValBlock", _f(sps.f.sf(f_block, df_block, df_error))), ("dfBlock", sp.Integer(df_block)),
                ("SSBlock", _f(ss_block)), ("MSBlock", _f(ms_block)), ("dfError", sp.Integer(df_error)),
                ("SSError", _f(ss_error)), ("MSError", _f(ms_error)), ("s", _f(math.sqrt(ms_error)))]
        return StatResults("ANOVA 2-Way (Block Design)", rows, dict(rows))
    if n_rows % lev_row or n_rows // lev_row < 2:
        raise DomainError("Length/levRow must be an integer ≥ 2")
    reps = n_rows // lev_row
    cells = data.reshape(lev_row, reps, n_cols)  # row level × replicate × column level
    cell_means = cells.mean(axis=1)
    row_means, col_means = cell_means.mean(axis=1), cell_means.mean(axis=0)
    ss_row = reps * n_cols * ((row_means - grand) ** 2).sum()
    ss_col = reps * lev_row * ((col_means - grand) ** 2).sum()
    ss_cells = reps * ((cell_means - grand) ** 2).sum()
    ss_inter = ss_cells - ss_row - ss_col
    ss_error = ((cells - cell_means[:, None, :]) ** 2).sum()
    df_row, df_col = lev_row - 1, n_cols - 1
    df_inter, df_error = df_row * df_col, lev_row * n_cols * (reps - 1)
    ms_error = ss_error / df_error

    def factor(ss, df):
        ms = ss / df
        f = ms / ms_error
        return f, sps.f.sf(f, df, df_error), df, ss, ms

    f_c, p_c, d_c, s_c, m_c = factor(ss_col, df_col)
    f_r, p_r, d_r, s_r, m_r = factor(ss_row, df_row)
    f_i, p_i, d_i, s_i, m_i = factor(ss_inter, df_inter)
    rows = [("Fcol", _f(f_c)), ("PValCol", _f(p_c)), ("dfCol", sp.Integer(d_c)), ("SSCol", _f(s_c)),
            ("MSCol", _f(m_c)), ("FRow", _f(f_r)), ("PValRow", _f(p_r)), ("dfRow", sp.Integer(d_r)),
            ("SSRow", _f(s_r)), ("MSRow", _f(m_r)), ("FInteract", _f(f_i)), ("PValInteract", _f(p_i)),
            ("dfInteract", sp.Integer(d_i)), ("SSInteract", _f(s_i)), ("MSInteract", _f(m_i)),
            ("dfError", sp.Integer(df_error)), ("SSError", _f(ss_error)), ("MSError", _f(ms_error)),
            ("s", _f(math.sqrt(ms_error)))]
    return StatResults("ANOVA 2-Way (Two Factor)", rows, dict(rows))


# ------------------------------------------------------------------ multiple regression tests / intervals


def _mult_fit(ys, xs_lists):
    y = np.array(to_float_list(ys, "Y"))
    columns = [np.array(to_float_list(v, "X")) for v in xs_lists]
    if any(len(c) != len(y) for c in columns):
        raise ArgumentError("Dimension mismatch")
    design = np.column_stack([np.ones_like(y), *columns])
    n, p = design.shape
    if n <= p:
        raise DomainError("Not enough data points")
    coeffs, *_ = np.linalg.lstsq(design, y, rcond=None)
    fitted = design @ coeffs
    resid = y - fitted
    df_error = n - p
    sse = float((resid**2).sum())
    mse = sse / df_error
    xtx_inv = np.linalg.inv(design.T @ design)
    return y, design, coeffs, fitted, resid, df_error, sse, mse, xtx_inv


def _regeqn(coeffs, count):
    names = [sp.Symbol(f"x{k + 1}") for k in range(count)]
    eqn = _f(coeffs[0]) + sum(_f(c) * s for c, s in zip(coeffs[1:], names))
    return UserFunction("stat.RegEqn", names, eqn)


@builtin("MultRegTests", "MultRegTests Y,X1[,X2[,X3,…[,X10]]]", 2, 11, command=True, approx=True,
         summary="Multiple linear regression tests")
def mult_reg_tests(ctx, ys, *xs_lists):
    y, design, coeffs, fitted, resid, df_error, sse, mse, xtx_inv = _mult_fit(ys, xs_lists)
    n, p = design.shape
    df_reg = p - 1
    ssr = float(((fitted - y.mean()) ** 2).sum())
    msr = ssr / df_reg
    f = msr / mse
    r2 = ssr / (ssr + sse)
    adj = 1 - (1 - r2) * (n - 1) / df_error
    se = np.sqrt(np.diag(xtx_inv) * mse)
    t = coeffs / se
    pvals = 2 * sps.t.sf(np.abs(t), df_error)
    leverage = np.einsum("ij,jk,ik->i", design, xtx_inv, design)
    s = math.sqrt(mse)
    s_resid = resid / (s * np.sqrt(1 - leverage))
    cook = (resid**2 / (p * mse)) * leverage / (1 - leverage) ** 2
    dw = float((np.diff(resid) ** 2).sum() / (resid**2).sum())
    lst = lambda arr: ListValue(_f(v) for v in arr)  # noqa: E731
    rows = [("RegEqn", TextValue("b0+b1*x1+…")), ("F", _f(f)), ("PVal", _f(sps.f.sf(f, df_reg, df_error))),
            ("R²", _f(r2)), ("AdjR²", _f(adj)), ("s", _f(s)), ("DW", _f(dw)), ("dfReg", sp.Integer(df_reg)),
            ("SSReg", _f(ssr)), ("MSReg", _f(msr)), ("dfError", sp.Integer(df_error)), ("SSError", _f(sse)),
            ("MSError", _f(mse)), ("bList", lst(coeffs)), ("tList", lst(t)), ("PList", lst(pvals)),
            ("SEList", lst(se)), ("yList", lst(fitted)), ("Resid", lst(resid)), ("sResid", lst(s_resid)),
            ("CookDist", lst(cook)), ("Leverage", lst(leverage))]
    variables = {k: v for k, v in rows if k != "RegEqn"}
    variables["RegEqn"] = _regeqn(coeffs, p - 1)
    return StatResults("Multiple Reg Tests", rows, variables)


@builtin("MultRegIntervals", "MultRegIntervals Y,X1[,X2[,…[,X10]]],XValList[,CLevel]", 3, 13, command=True,
         approx=True, summary="Confidence and prediction interval for multiple regression")
def mult_reg_intervals(ctx, ys, *rest):
    rest = list(rest)
    clevel = 0.95
    if rest and not isinstance(rest[-1], ListValue):
        clevel = _clevel(rest.pop())
    if len(rest) < 2:
        raise ArgumentError("MultRegIntervals needs X lists and an XValList")
    x_values = to_float_list(rest.pop(), "XValList")
    y, design, coeffs, fitted, resid, df_error, sse, mse, xtx_inv = _mult_fit(ys, rest)
    if len(x_values) != design.shape[1] - 1:
        raise ArgumentError("XValList needs one value per X list")
    x0 = np.array([1.0, *x_values])
    y_hat = float(x0 @ coeffs)
    se = math.sqrt(mse * float(x0 @ xtx_inv @ x0))
    se_pred = math.sqrt(mse + se**2)
    t_crit = sps.t.ppf((1 + clevel) / 2, df_error)
    me, me_pred = t_crit * se, t_crit * se_pred
    rows = [("RegEqn", TextValue("b0+b1*x1+…")), ("ŷ", _f(y_hat)), ("dfError", sp.Integer(df_error)),
            ("CLower, CUpper", ListValue([_f(y_hat - me), _f(y_hat + me)])), ("ME", _f(me)), ("SE", _f(se)),
            ("LowerPred", _f(y_hat - me_pred)), ("UpperPred", _f(y_hat + me_pred)), ("MEPred", _f(me_pred)),
            ("SEPred", _f(se_pred)), ("bList", ListValue(_f(v) for v in coeffs)),
            ("Resid", ListValue(_f(v) for v in resid))]
    variables = {k: v for k, v in rows if k not in ("RegEqn", "CLower, CUpper")}
    variables["CLower"], variables["CUpper"] = _f(y_hat - me), _f(y_hat + me)
    variables["RegEqn"] = _regeqn(coeffs, design.shape[1] - 1)
    return StatResults("Multiple Reg Intervals", rows, variables)
