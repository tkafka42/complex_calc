"""Hypothesis tests, more confidence intervals, TwoVar, FiveNumSummary and
the remaining distributions (F, inverse χ², inverse binomial w.r.t. N).

Hypoth: <0 → Ha: μ<μ0, 0 (default) → Ha: μ≠μ0, >0 → Ha: μ>μ0
"""

from __future__ import annotations

import math

import numpy as np
import sympy as sp
from scipy import stats as sps

from ..core.errors import ArgumentError, DomainError
from ..core.values import ListValue, StatResults, TextValue, UserFunction, is_matrix
from .intervals import _clevel, _data_with_freq, _mean_sx
from .registry import builtin, check_positive, to_float, to_float_list, to_int
from .stats import quartiles


def _f(x: float) -> sp.Float:
    x = float(x)
    return sp.Float(0.0 if abs(x) < 1e-13 else x, 15)


def _n(x: float):
    return sp.Integer(int(x)) if float(x).is_integer() else _f(x)


def _hyp(value) -> int:
    if value is None:
        return 0
    h = to_float(value, "Hypoth")
    return 0 if h == 0 else (1 if h > 0 else -1)


def _p_value(stat: float, hyp: int, cdf, sf) -> float:
    if hyp < 0:
        return cdf(stat)
    if hyp > 0:
        return sf(stat)
    return 2 * min(cdf(stat), sf(stat))


def _alt(symbol: str, null: str, hyp: int) -> TextValue:
    op = {-1: "<", 0: "≠", 1: ">"}[hyp]
    return TextValue(f"{symbol} {op} {null}")


def _results(title: str, rows: list[tuple[str, object]], extra: dict | None = None) -> StatResults:
    variables = {}
    for label, value in rows:
        if label == "Alternate Hyp":
            continue
        if label == "CLower, CUpper":
            variables["CLower"], variables["CUpper"] = value[0], value[1]
        else:
            variables[label] = value
    if extra:
        variables.update(extra)
    return StatResults(title, rows, variables)


def _pair(lo: float, hi: float) -> ListValue:
    return ListValue([_f(lo), _f(hi)])


# ------------------------------------------------------------------ z / t tests


@builtin("zTest", "zTest μ0,σ,List[,Freq[,Hypoth]]  |  zTest μ0,σ,x̄,n[,Hypoth]", 3, 5, command=True,
         approx=True, summary="z test for one mean")
def z_test(ctx, mu0, sigma, third, fourth=None, fifth=None):
    m0, s = to_float(mu0, "μ0"), to_float(sigma, "σ")
    check_positive(s, "σ")
    if isinstance(third, ListValue):
        data, w = _data_with_freq(third, fourth)
        mean, sx, n = _mean_sx(data, w)
        hyp = _hyp(fifth)
    else:
        if fourth is None:
            raise ArgumentError("Too few arguments: zTest μ0,σ,x̄,n[,Hypoth]")
        mean, n, sx = to_float(third, "x̄"), to_int(fourth, "n"), None
        hyp = _hyp(fifth)
    z = (mean - m0) / (s / math.sqrt(n))
    p = _p_value(z, hyp, sps.norm.cdf, sps.norm.sf)
    rows = [("Alternate Hyp", _alt("μ", "μ0", hyp)), ("z", _f(z)), ("PVal", _f(p)), ("x̄", _f(mean))]
    if sx is not None:
        rows.append(("sx", _f(sx)))
    rows.append(("n", _n(n)))
    return _results("z Test", rows)


@builtin("tTest", "tTest μ0,List[,Freq[,Hypoth]]  |  tTest μ0,x̄,sx,n[,Hypoth]", 2, 5, command=True,
         approx=True, summary="t test for one mean")
def t_test(ctx, mu0, second, third=None, fourth=None, fifth=None):
    m0 = to_float(mu0, "μ0")
    if isinstance(second, ListValue):
        data, w = _data_with_freq(second, third)
        mean, sx, n = _mean_sx(data, w)
        hyp = _hyp(fourth)
    else:
        if third is None or fourth is None:
            raise ArgumentError("Too few arguments: tTest μ0,x̄,sx,n[,Hypoth]")
        mean, sx, n = to_float(second, "x̄"), to_float(third, "sx"), to_int(fourth, "n")
        hyp = _hyp(fifth)
    df = n - 1
    t = (mean - m0) / (sx / math.sqrt(n))
    p = _p_value(t, hyp, lambda v: sps.t.cdf(v, df), lambda v: sps.t.sf(v, df))
    rows = [("Alternate Hyp", _alt("μ", "μ0", hyp)), ("t", _f(t)), ("PVal", _f(p)), ("df", _n(df)),
            ("x̄", _f(mean)), ("sx", _f(sx)), ("n", _n(n))]
    return _results("t Test", rows)


def _two_samples(args, sigma_first: bool):
    """Returns (mean1, s1, n1, mean2, s2, n2, rest_args)."""
    if isinstance(args[0], ListValue):
        list1, list2 = args[0], args[1]
        freq1 = args[2] if len(args) > 2 else None
        freq2 = args[3] if len(args) > 3 else None
        d1, w1 = _data_with_freq(list1, freq1)
        d2, w2 = _data_with_freq(list2, freq2)
        m1, s1, n1 = _mean_sx(d1, w1)
        m2, s2, n2 = _mean_sx(d2, w2)
        return m1, s1, n1, m2, s2, n2, list(args[4:])
    if len(args) < 6:
        raise ArgumentError("Too few arguments")
    m1, s1, n1, m2, s2, n2 = (to_float(a, "argument") for a in args[:6])
    return m1, s1, n1, m2, s2, n2, list(args[6:])


@builtin("zTest_2Samp", "zTest_2Samp σ1,σ2,List1,List2[,Freq1[,Freq2[,Hypoth]]]  |  zTest_2Samp σ1,σ2,x̄1,n1,x̄2,n2[,Hypoth]",
         4, 7, command=True, approx=True, summary="z test for two means")
def z_test_2samp(ctx, sigma1, sigma2, *rest):
    s1, s2 = to_float(sigma1, "σ1"), to_float(sigma2, "σ2")
    if isinstance(rest[0], ListValue):
        m1, sx1, n1, m2, sx2, n2, extra = _two_samples(list(rest), True)
    else:
        if len(rest) < 4:
            raise ArgumentError("Too few arguments")
        m1, n1, m2, n2 = (to_float(a, "argument") for a in rest[:4])
        sx1 = sx2 = None
        extra = list(rest[4:])
    hyp = _hyp(extra[0] if extra else None)
    z = (m1 - m2) / math.sqrt(s1**2 / n1 + s2**2 / n2)
    p = _p_value(z, hyp, sps.norm.cdf, sps.norm.sf)
    rows = [("Alternate Hyp", _alt("μ1", "μ2", hyp)), ("z", _f(z)), ("PVal", _f(p)), ("x̄1", _f(m1)), ("x̄2", _f(m2))]
    if sx1 is not None:
        rows += [("sx1", _f(sx1)), ("sx2", _f(sx2))]
    rows += [("n1", _n(n1)), ("n2", _n(n2))]
    return _results("2-Sample z Test", rows)


def _pooled(s1, n1, s2, n2) -> float:
    return math.sqrt(((n1 - 1) * s1**2 + (n2 - 1) * s2**2) / (n1 + n2 - 2))


def _welch_df(s1, n1, s2, n2) -> float:
    a, b = s1**2 / n1, s2**2 / n2
    return (a + b) ** 2 / (a**2 / (n1 - 1) + b**2 / (n2 - 1))


@builtin("tTest_2Samp", "tTest_2Samp List1,List2[,Freq1[,Freq2[,Hypoth[,Pooled]]]]  |  tTest_2Samp x̄1,sx1,n1,x̄2,sx2,n2[,Hypoth[,Pooled]]",
         2, 8, command=True, approx=True, summary="t test for two means")
def t_test_2samp(ctx, *args):
    m1, s1, n1, m2, s2, n2, extra = _two_samples(list(args), False)
    hyp = _hyp(extra[0] if extra else None)
    pooled = len(extra) > 1 and to_float(extra[1], "Pooled") != 0
    if pooled:
        sp_ = _pooled(s1, n1, s2, n2)
        se = sp_ * math.sqrt(1 / n1 + 1 / n2)
        df = n1 + n2 - 2
    else:
        se = math.sqrt(s1**2 / n1 + s2**2 / n2)
        df = _welch_df(s1, n1, s2, n2)
        sp_ = None
    t = (m1 - m2) / se
    p = _p_value(t, hyp, lambda v: sps.t.cdf(v, df), lambda v: sps.t.sf(v, df))
    rows = [("Alternate Hyp", _alt("μ1", "μ2", hyp)), ("t", _f(t)), ("PVal", _f(p)), ("df", _n(df) if pooled else _f(df)),
            ("x̄1", _f(m1)), ("x̄2", _f(m2)), ("sx1", _f(s1)), ("sx2", _f(s2)), ("n1", _n(n1)), ("n2", _n(n2))]
    if sp_ is not None:
        rows.append(("sp", _f(sp_)))
    return _results("2-Sample t Test", rows)


@builtin("zTest_1Prop", "zTest_1Prop p0,x,n[,Hypoth]", 3, 4, command=True, approx=True,
         summary="z test for one proportion")
def z_test_1prop(ctx, p0, x, n, hypoth=None):
    p_0, successes, trials = to_float(p0, "p0"), to_float(x, "x"), to_int(n, "n")
    hyp = _hyp(hypoth)
    p_hat = successes / trials
    z = (p_hat - p_0) / math.sqrt(p_0 * (1 - p_0) / trials)
    p = _p_value(z, hyp, sps.norm.cdf, sps.norm.sf)
    rows = [("Alternate Hyp", _alt("p", "p0", hyp)), ("p0", _f(p_0)), ("z", _f(z)), ("PVal", _f(p)),
            ("p̂", _f(p_hat)), ("n", _n(trials))]
    return _results("1-Prop z Test", rows)


@builtin("zTest_2Prop", "zTest_2Prop x1,n1,x2,n2[,Hypoth]", 4, 5, command=True, approx=True,
         summary="z test for two proportions")
def z_test_2prop(ctx, x1, n1, x2, n2, hypoth=None):
    a, na, b, nb = (to_float(v, "argument") for v in (x1, n1, x2, n2))
    hyp = _hyp(hypoth)
    p1, p2, pooled = a / na, b / nb, (a + b) / (na + nb)
    z = (p1 - p2) / math.sqrt(pooled * (1 - pooled) * (1 / na + 1 / nb))
    p = _p_value(z, hyp, sps.norm.cdf, sps.norm.sf)
    rows = [("Alternate Hyp", _alt("p1", "p2", hyp)), ("z", _f(z)), ("PVal", _f(p)), ("p̂1", _f(p1)),
            ("p̂2", _f(p2)), ("p̂", _f(pooled)), ("n1", _n(na)), ("n2", _n(nb))]
    return _results("2-Prop z Test", rows)


# ------------------------------------------------------------------ intervals


@builtin("zInterval_1Prop", "zInterval_1Prop x,n[,CLevel]", 2, 3, command=True, approx=True,
         summary="z confidence interval for one proportion")
def z_interval_1prop(ctx, x, n, clevel=None):
    successes, trials = to_float(x, "x"), to_int(n, "n")
    c = _clevel(clevel if clevel is not None else 0.95)
    p_hat = successes / trials
    me = sps.norm.ppf((1 + c) / 2) * math.sqrt(p_hat * (1 - p_hat) / trials)
    rows = [("CLower, CUpper", _pair(p_hat - me, p_hat + me)), ("p̂", _f(p_hat)), ("ME", _f(me)), ("n", _n(trials))]
    return _results("1-Prop z Interval", rows)


@builtin("zInterval_2Prop", "zInterval_2Prop x1,n1,x2,n2[,CLevel]", 4, 5, command=True, approx=True,
         summary="z confidence interval for the difference of two proportions")
def z_interval_2prop(ctx, x1, n1, x2, n2, clevel=None):
    a, na, b, nb = (to_float(v, "argument") for v in (x1, n1, x2, n2))
    c = _clevel(clevel if clevel is not None else 0.95)
    p1, p2 = a / na, b / nb
    diff = p1 - p2
    me = sps.norm.ppf((1 + c) / 2) * math.sqrt(p1 * (1 - p1) / na + p2 * (1 - p2) / nb)
    rows = [("CLower, CUpper", _pair(diff - me, diff + me)), ("p̂ Diff", _f(diff)), ("ME", _f(me)),
            ("p̂1", _f(p1)), ("p̂2", _f(p2)), ("n1", _n(na)), ("n2", _n(nb))]
    return _results("2-Prop z Interval", rows)


@builtin("zInterval_2Samp", "zInterval_2Samp σ1,σ2,List1,List2[,Freq1[,Freq2[,CLevel]]]  |  zInterval_2Samp σ1,σ2,x̄1,n1,x̄2,n2[,CLevel]",
         4, 7, command=True, approx=True, summary="z confidence interval for the difference of two means")
def z_interval_2samp(ctx, sigma1, sigma2, *rest):
    s1, s2 = to_float(sigma1, "σ1"), to_float(sigma2, "σ2")
    if isinstance(rest[0], ListValue):
        m1, sx1, n1, m2, sx2, n2, extra = _two_samples(list(rest), True)
    else:
        m1, n1, m2, n2 = (to_float(a, "argument") for a in rest[:4])
        sx1 = sx2 = None
        extra = list(rest[4:])
    c = _clevel(extra[0] if extra else 0.95)
    diff = m1 - m2
    me = sps.norm.ppf((1 + c) / 2) * math.sqrt(s1**2 / n1 + s2**2 / n2)
    rows = [("CLower, CUpper", _pair(diff - me, diff + me)), ("x̄1-x̄2", _f(diff)), ("ME", _f(me)),
            ("x̄1", _f(m1)), ("x̄2", _f(m2))]
    if sx1 is not None:
        rows += [("sx1", _f(sx1)), ("sx2", _f(sx2))]
    rows += [("n1", _n(n1)), ("n2", _n(n2))]
    return _results("2-Sample z Interval", rows)


@builtin("tInterval_2Samp", "tInterval_2Samp List1,List2[,Freq1[,Freq2[,CLevel[,Pooled]]]]  |  tInterval_2Samp x̄1,sx1,n1,x̄2,sx2,n2[,CLevel[,Pooled]]",
         2, 8, command=True, approx=True, summary="t confidence interval for the difference of two means")
def t_interval_2samp(ctx, *args):
    m1, s1, n1, m2, s2, n2, extra = _two_samples(list(args), False)
    c = _clevel(extra[0] if extra else 0.95)
    pooled = len(extra) > 1 and to_float(extra[1], "Pooled") != 0
    if pooled:
        sp_ = _pooled(s1, n1, s2, n2)
        se, df = sp_ * math.sqrt(1 / n1 + 1 / n2), n1 + n2 - 2
    else:
        sp_ = None
        se, df = math.sqrt(s1**2 / n1 + s2**2 / n2), _welch_df(s1, n1, s2, n2)
    diff = m1 - m2
    me = sps.t.ppf((1 + c) / 2, df) * se
    rows = [("CLower, CUpper", _pair(diff - me, diff + me)), ("x̄1-x̄2", _f(diff)), ("ME", _f(me)),
            ("df", _n(df) if pooled else _f(df)), ("x̄1", _f(m1)), ("x̄2", _f(m2)), ("sx1", _f(s1)),
            ("sx2", _f(s2)), ("n1", _n(n1)), ("n2", _n(n2))]
    if sp_ is not None:
        rows.append(("sp", _f(sp_)))
    return _results("2-Sample t Interval", rows)


# ------------------------------------------------------------------ χ², F, ANOVA


@builtin("χ²GOF", "χ²GOF obsList,expList,df", 3, aliases=("chi2GOF",), command=True, approx=True,
         summary="χ² goodness-of-fit test")
def chi2_gof(ctx, obs, exp, df):
    o, e = np.array(to_float_list(obs, "obsList")), np.array(to_float_list(exp, "expList"))
    if len(o) != len(e):
        raise ArgumentError("Dimension mismatch")
    comp = (o - e) ** 2 / e
    chi2 = float(comp.sum())
    d = to_int(df, "df")
    rows = [("χ²", _f(chi2)), ("PVal", _f(sps.chi2.sf(chi2, d))), ("df", _n(d)),
            ("CompList", ListValue(_f(v) for v in comp))]
    return _results("χ² GOF", rows)


@builtin("χ²2way", "χ²2way obsMatrix", 1, aliases=("chi22way",), command=True, approx=True,
         summary="χ² test of independence (two-way table)")
def chi2_2way(ctx, observed):
    if not is_matrix(observed):
        raise ArgumentError("obsMatrix must be a matrix")
    o = np.array(observed.tolist(), dtype=float)
    chi2, p, df, expected = sps.chi2_contingency(o, correction=False)
    comp = (o - expected) ** 2 / expected
    rows = [("χ²", _f(chi2)), ("PVal", _f(p)), ("df", _n(df)),
            ("ExpMat", sp.ImmutableMatrix(expected.tolist()).applyfunc(_f)),
            ("CompMat", sp.ImmutableMatrix(comp.tolist()).applyfunc(_f))]
    return _results("χ² 2-way", rows)


@builtin("FTest_2Samp", "FTest_2Samp List1,List2[,Freq1[,Freq2[,Hypoth]]]  |  FTest_2Samp sx1,n1,sx2,n2[,Hypoth]",
         2, 5, command=True, approx=True, summary="F test for two standard deviations")
def f_test_2samp(ctx, *args):
    if isinstance(args[0], ListValue):
        m1, s1, n1, m2, s2, n2, extra = _two_samples(list(args), False)
        means = (m1, m2)
    else:
        if len(args) < 4:
            raise ArgumentError("Too few arguments")
        s1, n1, s2, n2 = (to_float(a, "argument") for a in args[:4])
        extra = list(args[4:])
        means = None
    hyp = _hyp(extra[0] if extra else None)
    f = s1**2 / s2**2
    d1, d2 = n1 - 1, n2 - 1
    p = _p_value(f, hyp, lambda v: sps.f.cdf(v, d1, d2), lambda v: sps.f.sf(v, d1, d2))
    rows = [("Alternate Hyp", _alt("σ1", "σ2", hyp)), ("F", _f(f)), ("PVal", _f(p)), ("dfNumer", _n(d1)),
            ("dfDenom", _n(d2)), ("sx1", _f(s1)), ("sx2", _f(s2))]
    if means is not None:
        rows += [("x̄1", _f(means[0])), ("x̄2", _f(means[1]))]
    rows += [("n1", _n(n1)), ("n2", _n(n2))]
    return _results("2-Sample F Test", rows)


@builtin("ANOVA", "ANOVA List1,List2[,List3,…,List20][,Flag]", 2, 21, command=True, approx=True,
         summary="One-way analysis of variance")
def anova(ctx, *args):
    groups = [np.array(to_float_list(a, "List")) for a in args if isinstance(a, ListValue)]
    if len(groups) < 2:
        raise ArgumentError("ANOVA needs at least two lists")
    k = len(groups)
    n_total = sum(len(g) for g in groups)
    grand = np.concatenate(groups).mean()
    ss_between = sum(len(g) * (g.mean() - grand) ** 2 for g in groups)
    ss_error = sum(((g - g.mean()) ** 2).sum() for g in groups)
    df_b, df_e = k - 1, n_total - k
    ms_b, ms_e = ss_between / df_b, ss_error / df_e
    f = ms_b / ms_e
    sp_ = math.sqrt(ms_e)
    t_crit = sps.t.ppf(0.975, df_e)
    lowers = [g.mean() - t_crit * sp_ / math.sqrt(len(g)) for g in groups]
    uppers = [g.mean() + t_crit * sp_ / math.sqrt(len(g)) for g in groups]
    rows = [("F", _f(f)), ("PVal", _f(sps.f.sf(f, df_b, df_e))), ("df", _n(df_b)), ("SS", _f(ss_between)),
            ("MS", _f(ms_b)), ("dfError", _n(df_e)), ("SSError", _f(ss_error)), ("MSError", _f(ms_e)),
            ("sp", _f(sp_)), ("xbarlist", ListValue(_f(g.mean()) for g in groups)),
            ("CLowerList", ListValue(_f(v) for v in lowers)), ("CUpperList", ListValue(_f(v) for v in uppers))]
    return _results("ANOVA", rows)


# ------------------------------------------------------------------ linear regression t test / intervals


def _lin_data(xs, ys, freq):
    from .regression import _xy, _linear_fit

    x, y, w = _xy(xs, ys, freq, 3)
    b, a, r = _linear_fit(x, y, w)
    n = w.sum()
    resid = y - (a + b * x)
    s = math.sqrt((w * resid**2).sum() / (n - 2))
    mx = (w * x).sum() / n
    sxx = (w * (x - mx) ** 2).sum()
    return x, y, w, a, b, r, n, s, mx, sxx, resid


def _lin_rows(a, b, r, n, resid):
    return [("RegEqn", TextValue("a+b*x")), ("a", _f(a)), ("b", _f(b))], \
        [("r²", _f(r * r)), ("r", _f(r)), ("Resid", ListValue(_f(v) for v in resid))]


def _with_regeqn(results: StatResults, a: float, b: float) -> StatResults:
    x = sp.Symbol("x")
    results.variables["RegEqn"] = UserFunction("stat.RegEqn", [x], _f(a) + _f(b) * x)
    return results


@builtin("LinRegtTest", "LinRegtTest X,Y[,Freq[,Hypoth]]", 2, 4, command=True, approx=True,
         summary="t test for the slope of a linear regression")
def lin_reg_t_test(ctx, xs, ys, freq=None, hypoth=None):
    x, y, w, a, b, r, n, s, mx, sxx, resid = _lin_data(xs, ys, freq)
    hyp = _hyp(hypoth)
    se_slope = s / math.sqrt(sxx)
    df = n - 2
    t = b / se_slope
    p = _p_value(t, hyp, lambda v: sps.t.cdf(v, df), lambda v: sps.t.sf(v, df))
    head, tail = _lin_rows(a, b, r, n, resid)
    rows = [("Alternate Hyp", _alt("β & ρ", "0", hyp)), head[0], ("t", _f(t)), ("PVal", _f(p)), ("df", _n(df)),
            head[1], head[2], ("s", _f(s)), ("SESlope", _f(se_slope)), *tail]
    return _with_regeqn(_results("Linear Reg t Test", rows), a, b)


@builtin("LinRegtIntervals", "LinRegtIntervals X,Y[,F[,0[,CLev]]]  |  LinRegtIntervals X,Y[,F[,1,Xval[,CLev]]]",
         2, 6, command=True, approx=True, summary="Confidence intervals for slope or response")
def lin_reg_t_intervals(ctx, xs, ys, freq=None, kind=None, fifth=None, sixth=None):
    x, y, w, a, b, r, n, s, mx, sxx, resid = _lin_data(xs, ys, freq)
    df = n - 2
    head, tail = _lin_rows(a, b, r, n, resid)
    response = kind is not None and to_float(kind, "type") == 1
    if response:
        if fifth is None:
            raise ArgumentError("Xval required for response intervals")
        xv = to_float(fifth, "Xval")
        c = _clevel(sixth if sixth is not None else 0.95)
        t_crit = sps.t.ppf((1 + c) / 2, df)
        y_hat = a + b * xv
        se = s * math.sqrt(1 / n + (xv - mx) ** 2 / sxx)
        se_pred = s * math.sqrt(1 + 1 / n + (xv - mx) ** 2 / sxx)
        me, me_pred = t_crit * se, t_crit * se_pred
        rows = [*head, ("df", _n(df)), *tail[:2], ("CLower, CUpper", _pair(y_hat - me, y_hat + me)),
                ("ME", _f(me)), ("SE", _f(se)), ("LowerPred", _f(y_hat - me_pred)), ("UpperPred", _f(y_hat + me_pred)),
                ("MEPred", _f(me_pred)), ("SEPred", _f(se_pred)), ("ŷ", _f(y_hat)), tail[2]]
        title = "Linear Reg t Intervals (Response)"
    else:
        c = _clevel(fifth if fifth is not None else 0.95)
        t_crit = sps.t.ppf((1 + c) / 2, df)
        se_slope = s / math.sqrt(sxx)
        me = t_crit * se_slope
        rows = [*head, ("df", _n(df)), *tail[:2], ("CLower, CUpper", _pair(b - me, b + me)), ("ME", _f(me)),
                ("SESlope", _f(se_slope)), ("s", _f(s)), tail[2]]
        title = "Linear Reg t Intervals (Slope)"
    return _with_regeqn(_results(title, rows), a, b)


# ------------------------------------------------------------------ TwoVar / FiveNumSummary


@builtin("TwoVar", "TwoVar X,Y[,Freq]", 2, 3, command=True, approx=True, summary="Two-variable statistics")
def two_var(ctx, xs, ys, freq=None):
    from .regression import _xy

    x, y, w = _xy(xs, ys, freq, 1)
    n = w.sum()
    mx, my = (w * x).sum() / n, (w * y).sum() / n
    ssx, ssy = (w * (x - mx) ** 2).sum(), (w * (y - my) ** 2).sum()
    sxy = (w * (x - mx) * (y - my)).sum()
    r = sxy / math.sqrt(ssx * ssy) if ssx > 0 and ssy > 0 else float("nan")
    ex = sorted(np.repeat(x, w.astype(int)).tolist())
    ey = sorted(np.repeat(y, w.astype(int)).tolist())
    qx, qy = quartiles(ex), quartiles(ey)

    def med(values):
        k = len(values) // 2
        return values[k] if len(values) % 2 else (values[k - 1] + values[k]) / 2

    rows = [("x̄", _f(mx)), ("Σx", _f((w * x).sum())), ("Σx²", _f((w * x * x).sum())),
            ("sx := sn-1x", _f(math.sqrt(ssx / (n - 1)))), ("σx := σnx", _f(math.sqrt(ssx / n))), ("n", _n(n)),
            ("ȳ", _f(my)), ("Σy", _f((w * y).sum())), ("Σy²", _f((w * y * y).sum())),
            ("sy := sn-1y", _f(math.sqrt(ssy / (n - 1)))), ("σy := σny", _f(math.sqrt(ssy / n))),
            ("Σxy", _f((w * x * y).sum())), ("r", _f(r)), ("MinX", _f(ex[0])), ("Q₁X", _f(qx[0])),
            ("MedianX", _f(med(ex))), ("Q₃X", _f(qx[1])), ("MaxX", _f(ex[-1])), ("MinY", _f(ey[0])),
            ("Q₁Y", _f(qy[0])), ("MedY", _f(med(ey))), ("Q₃Y", _f(qy[1])), ("MaxY", _f(ey[-1])),
            ("Σ(x-x̄)²", _f(ssx)), ("Σ(y-ȳ)²", _f(ssy))]
    return _results("Two-Variable Statistics", rows)


@builtin("FiveNumSummary", "FiveNumSummary X[,Freq]", 1, 2, command=True, approx=True,
         summary="Minimum, Q1, median, Q3, maximum")
def five_num(ctx, values, freq=None):
    data, w = _data_with_freq(values, freq)
    expanded = sorted(np.repeat(np.array(data), np.array(w).astype(int)).tolist())
    q1, q3 = quartiles(expanded)
    k = len(expanded) // 2
    median = expanded[k] if len(expanded) % 2 else (expanded[k - 1] + expanded[k]) / 2
    rows = [("MinX", _f(expanded[0])), ("Q₁X", _f(q1)), ("MedianX", _f(median)), ("Q₃X", _f(q3)),
            ("MaxX", _f(expanded[-1]))]
    return _results("Five Number Summary", rows)


# ------------------------------------------------------------------ remaining distributions


@builtin("FPdf", "FPdf(XVal,dfNumer,dfDenom)", 3, approx=True, listable=(0,), summary="F probability density")
def f_pdf(ctx, x, d1, d2):
    return _f(sps.f.pdf(to_float(x, "XVal"), to_float(d1, "dfNumer"), to_float(d2, "dfDenom")))


@builtin("FCdf", "FCdf(lowBound,upBound,dfNumer,dfDenom)", 4, approx=True, listable=(0, 1),
         summary="F cumulative probability between two bounds")
def f_cdf(ctx, lo, hi, d1, d2):
    a, b = to_float(d1, "dfNumer"), to_float(d2, "dfDenom")
    return _f(sps.f.cdf(to_float(hi, "upBound"), a, b) - sps.f.cdf(to_float(lo, "lowBound"), a, b))


@builtin("invF", "invF(Area,dfNumer,dfDenom)", 3, approx=True, listable=(0,), summary="Inverse cumulative F")
def inv_f(ctx, area, d1, d2):
    a = to_float(area, "Area")
    if not 0 < a < 1:
        raise DomainError("Area must be between 0 and 1")
    return _f(sps.f.ppf(a, to_float(d1, "dfNumer"), to_float(d2, "dfDenom")))


@builtin("invχ²", "invχ²(Area,df)", 2, aliases=("invChi2",), approx=True, listable=(0,), summary="Inverse cumulative χ²")
def inv_chi2(ctx, area, df):
    a = to_float(area, "Area")
    if not 0 < a < 1:
        raise DomainError("Area must be between 0 and 1")
    return _f(sps.chi2.ppf(a, to_float(df, "df")))


@builtin("invBinomN", "invBinomN(CumulativeProb,Prob,NumSuccess[,OutputForm])", 3, 4, approx=True,
         summary="Smallest number of trials N with binomCdf(N,Prob,0,NumSuccess) ≤ CumulativeProb")
def inv_binom_n(ctx, cum, prob, successes, output_form=None):
    c, p, k = to_float(cum, "CumulativeProb"), to_float(prob, "Prob"), to_int(successes, "NumSuccess")
    n = max(k, 0)
    while sps.binom.cdf(k, n, p) > c:
        n += 1
        if n > 10**6:
            raise DomainError("No solution found")
    if output_form is not None and to_float(output_form, "OutputForm") == 1:
        return sp.ImmutableMatrix([[n - 1, _f(sps.binom.cdf(k, n - 1, p))], [n, _f(sps.binom.cdf(k, n, p))]])
    return sp.Integer(n)
