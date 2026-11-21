"""Numbered Calculator menu tree and wizard (assistant dialog) definitions.

The numbering mirrors the menu of a handheld CAS calculator's Calculator page,
so learned key paths such as  Menu → 5 → 5 → 2  (Normal Cdf) work the same.
Items that this app does not implement are kept as disabled placeholders so
that the numbering of the following items stays correct.

Sources: the order of the Distributions, Confidence Intervals, Stat Tests and
Stat Calculations submenus follows the official TI-Nspire eGuide (Lists &
Spreadsheet chapter). "Menu → 5 Probability → 5 Distributions → 2 Normal Cdf"
is confirmed by official TI teacher notes. Everything marked ``unsure=True``
is reconstructed from memory (see UNSURE_SYNTAX.md).

This module is GUI-independent: the REPL prints it with ``:menu`` and the GUI
builds its menus and dialogs from it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable


@dataclass
class WizardField:
    label: str
    key: str
    default: str = ""
    optional: bool = False
    enabled: bool = True  # disabled fields are shown greyed out (not supported)
    choices: list[tuple[str, str]] | None = None  # drop-down: (label, value)


@dataclass
class WizardVariant:
    fields: list[WizardField]
    build: Callable[[dict[str, str]], str]


@dataclass
class Wizard:
    title: str
    # One variant, or several selectable "Data Input Method"s (e.g. Stats / Data)
    variants: dict[str, WizardVariant]

    @property
    def needs_method_choice(self) -> bool:
        return len(self.variants) > 1


@dataclass
class MenuItem:
    key: str  # "1".."9", "A".."K"
    label: str
    insert: str | None = None  # text inserted into the entry line
    wizard: Wizard | None = None
    action: str | None = None  # special app action (clear history, program editor, ...)
    children: list["MenuItem"] = field(default_factory=list)
    enabled: bool = True
    unsure: bool = False

    @property
    def is_submenu(self) -> bool:
        return bool(self.children)


# ------------------------------------------------------------------ builders


def _args(values: dict[str, str], keys: tuple[str, ...]) -> list[str]:
    args = [values.get(k, "").strip() for k in keys]
    while args and not args[-1]:
        args.pop()
    return args


def _call(name: str, *keys: str) -> Callable[[dict[str, str]], str]:
    """Build name(a,b,c), dropping empty trailing optional arguments."""

    def build(values: dict[str, str]) -> str:
        return f"{name}({','.join(_args(values, keys))})"

    return build


def _command(name: str, *keys: str) -> Callable[[dict[str, str]], str]:
    def build(values: dict[str, str]) -> str:
        return f"{name} {','.join(_args(values, keys))}"

    return build


def _regression(name: str, *keys: str) -> Callable[[dict[str, str]], str]:
    base = _command(name, *keys)

    def build(values: dict[str, str]) -> str:
        text = base(values)
        target = values.get("save", "").strip()
        if target:
            text += f": CopyVar stat.RegEqn,{target}"
        return text

    return build


def _wizard(title: str, fields: list["WizardField"], build) -> Wizard:
    return Wizard(title, {"": WizardVariant(fields, build)})


F = WizardField


def _hyp(symbol: str, null: str) -> WizardField:
    return F("Alternate Hyp", "hyp", "0", choices=[
        (f"Ha: {symbol} ≠ {null}", "0"), (f"Ha: {symbol} < {null}", "-1"), (f"Ha: {symbol} > {null}", "1")])


POOLED = F("Pooled", "pooled", "0", choices=[("No", "0"), ("Yes", "1")])
CLEVEL = F("C Level", "c", "0.95")
FREQ = F("Frequency List", "freq", "1")
FREQ1 = F("Frequency List 1", "freq1", "1")
FREQ2 = F("Frequency List 2", "freq2", "1")


def _stats_data(title: str, stats: tuple[list, Callable], data: tuple[list, Callable]) -> Wizard:
    return Wizard(title, {"Stats": WizardVariant(*stats), "Data": WizardVariant(*data)})


# ------------------------------------------------------------------ distribution wizards

NORMAL_PDF = _wizard("Normal Pdf", [F("X Value", "x"), F("μ", "mu", "0"), F("σ", "sigma", "1")],
                     _call("normPdf", "x", "mu", "sigma"))
NORMAL_CDF = _wizard("Normal Cdf", [F("Lower Bound", "lo", "-∞"), F("Upper Bound", "hi", "∞"),
                                    F("μ", "mu", "0"), F("σ", "sigma", "1")],
                     _call("normCdf", "lo", "hi", "mu", "sigma"))
INVERSE_NORMAL = _wizard("Inverse Normal", [F("Area", "area"), F("μ", "mu", "0"), F("σ", "sigma", "1")],
                         _call("invNorm", "area", "mu", "sigma"))
T_PDF = _wizard("t Pdf", [F("X Value", "x"), F("Deg of Freedom, df", "df")], _call("tPdf", "x", "df"))
T_CDF = _wizard("t Cdf", [F("Lower Bound", "lo", "-∞"), F("Upper Bound", "hi", "∞"), F("Deg of Freedom, df", "df")],
                _call("tCdf", "lo", "hi", "df"))
INVERSE_T = _wizard("Inverse t", [F("Area", "area"), F("Deg of Freedom, df", "df")], _call("invt", "area", "df"))
CHI2_PDF = _wizard("χ² Pdf", [F("X Value", "x"), F("Deg of Freedom, df", "df")], _call("χ²Pdf", "x", "df"))
CHI2_CDF = _wizard("χ² Cdf", [F("Lower Bound", "lo", "0"), F("Upper Bound", "hi", "∞"), F("Deg of Freedom, df", "df")],
                   _call("χ²Cdf", "lo", "hi", "df"))
F_PDF = _wizard("F Pdf", [F("X Value", "x"), F("Numerator df", "d1"), F("Denominator df", "d2")],
                _call("FPdf", "x", "d1", "d2"))
F_CDF = _wizard("F Cdf", [F("Lower Bound", "lo", "0"), F("Upper Bound", "hi", "∞"), F("Numerator df", "d1"),
                          F("Denominator df", "d2")], _call("FCdf", "lo", "hi", "d1", "d2"))
BINOMIAL_PDF = _wizard("Binomial Pdf", [F("Num Trials, n", "n"), F("Prob Success, p", "p"),
                                        F("X Value", "x", optional=True)],
                       _call("binomPdf", "n", "p", "x"))
BINOMIAL_CDF = _wizard("Binomial Cdf", [F("Num Trials, n", "n"), F("Prob Success, p", "p"),
                                        F("Lower Bound", "lo", "0"), F("Upper Bound", "hi")],
                       _call("binomCdf", "n", "p", "lo", "hi"))
INVERSE_BINOMIAL = _wizard("Inverse Binomial", [F("Cumulative Probability", "c"), F("Num Trials, n", "n"),
                                                F("Prob Success, p", "p")],
                           _call("invBinom", "c", "n", "p"))
INVERSE_BINOMIAL_N = _wizard("Inverse Binomial with respect to N",
                             [F("Cumulative Probability", "c"), F("Prob Success, p", "p"),
                              F("Num Success, k", "k")], _call("invBinomN", "c", "p", "k"))
POISSON_PDF = _wizard("Poisson Pdf", [F("λ", "lam"), F("X Value", "x")], _call("poissPdf", "lam", "x"))
POISSON_CDF = _wizard("Poisson Cdf", [F("λ", "lam"), F("Lower Bound", "lo", "0"), F("Upper Bound", "hi")],
                      _call("poissCdf", "lam", "lo", "hi"))
GEOMETRIC_PDF = _wizard("Geometric Pdf", [F("Prob Success, p", "p"), F("X Value", "x")], _call("geomPdf", "p", "x"))
GEOMETRIC_CDF = _wizard("Geometric Cdf", [F("Prob Success, p", "p"), F("Lower Bound", "lo", "1"),
                                          F("Upper Bound", "hi")],
                        _call("geomCdf", "p", "lo", "hi"))

# ------------------------------------------------------------------ interval wizards

Z_INTERVAL = _stats_data(
    "z Interval",
    ([F("σ", "sigma"), F("x̄", "mean"), F("n", "n"), CLEVEL], _command("zInterval", "sigma", "mean", "n", "c")),
    ([F("σ", "sigma"), F("List", "list"), FREQ, CLEVEL], _command("zInterval", "sigma", "list", "freq", "c")))
T_INTERVAL = _stats_data(
    "t Interval",
    ([F("x̄", "mean"), F("sx", "sx"), F("n", "n"), CLEVEL], _command("tInterval", "mean", "sx", "n", "c")),
    ([F("List", "list"), FREQ, CLEVEL], _command("tInterval", "list", "freq", "c")))
Z_INTERVAL_2SAMP = _stats_data(
    "2-Sample z Interval",
    ([F("σ1", "s1"), F("σ2", "s2"), F("x̄1", "m1"), F("n1", "n1"), F("x̄2", "m2"), F("n2", "n2"), CLEVEL],
     _command("zInterval_2Samp", "s1", "s2", "m1", "n1", "m2", "n2", "c")),
    ([F("σ1", "s1"), F("σ2", "s2"), F("List 1", "l1"), F("List 2", "l2"), FREQ1, FREQ2, CLEVEL],
     _command("zInterval_2Samp", "s1", "s2", "l1", "l2", "freq1", "freq2", "c")))
T_INTERVAL_2SAMP = _stats_data(
    "2-Sample t Interval",
    ([F("x̄1", "m1"), F("sx1", "sx1"), F("n1", "n1"), F("x̄2", "m2"), F("sx2", "sx2"), F("n2", "n2"), CLEVEL, POOLED],
     _command("tInterval_2Samp", "m1", "sx1", "n1", "m2", "sx2", "n2", "c", "pooled")),
    ([F("List 1", "l1"), F("List 2", "l2"), FREQ1, FREQ2, CLEVEL, POOLED],
     _command("tInterval_2Samp", "l1", "l2", "freq1", "freq2", "c", "pooled")))
Z_INTERVAL_1PROP = _wizard("1-Prop z Interval", [F("Successes, x", "x"), F("n", "n"), CLEVEL],
                           _command("zInterval_1Prop", "x", "n", "c"))
Z_INTERVAL_2PROP = _wizard("2-Prop z Interval", [F("Successes, x1", "x1"), F("n1", "n1"), F("Successes, x2", "x2"),
                                                 F("n2", "n2"), CLEVEL],
                           _command("zInterval_2Prop", "x1", "n1", "x2", "n2", "c"))
LINREG_T_INTERVALS = _wizard(
    "Linear Reg t Intervals",
    [F("X List", "x"), F("Y List", "y"), FREQ,
     F("Interval", "kind", "0", choices=[("Slope", "0"), ("Response", "1")]),
     F("X Value (Response only)", "xv", optional=True), CLEVEL],
    lambda v: (f"LinRegtIntervals {v.get('x','')},{v.get('y','')},{v.get('freq','1') or '1'},"
               + (f"1,{v.get('xv','')},{v.get('c','0.95')}" if v.get("kind") == "1" else f"0,{v.get('c','0.95')}")))

# ------------------------------------------------------------------ test wizards

Z_TEST = _stats_data(
    "z Test",
    ([F("μ0", "mu0"), F("σ", "sigma"), F("x̄", "mean"), F("n", "n"), _hyp("μ", "μ0")],
     _command("zTest", "mu0", "sigma", "mean", "n", "hyp")),
    ([F("μ0", "mu0"), F("σ", "sigma"), F("List", "list"), FREQ, _hyp("μ", "μ0")],
     _command("zTest", "mu0", "sigma", "list", "freq", "hyp")))
T_TEST = _stats_data(
    "t Test",
    ([F("μ0", "mu0"), F("x̄", "mean"), F("sx", "sx"), F("n", "n"), _hyp("μ", "μ0")],
     _command("tTest", "mu0", "mean", "sx", "n", "hyp")),
    ([F("μ0", "mu0"), F("List", "list"), FREQ, _hyp("μ", "μ0")], _command("tTest", "mu0", "list", "freq", "hyp")))
Z_TEST_2SAMP = _stats_data(
    "2-Sample z Test",
    ([F("σ1", "s1"), F("σ2", "s2"), F("x̄1", "m1"), F("n1", "n1"), F("x̄2", "m2"), F("n2", "n2"), _hyp("μ1", "μ2")],
     _command("zTest_2Samp", "s1", "s2", "m1", "n1", "m2", "n2", "hyp")),
    ([F("σ1", "s1"), F("σ2", "s2"), F("List 1", "l1"), F("List 2", "l2"), FREQ1, FREQ2, _hyp("μ1", "μ2")],
     _command("zTest_2Samp", "s1", "s2", "l1", "l2", "freq1", "freq2", "hyp")))
T_TEST_2SAMP = _stats_data(
    "2-Sample t Test",
    ([F("x̄1", "m1"), F("sx1", "sx1"), F("n1", "n1"), F("x̄2", "m2"), F("sx2", "sx2"), F("n2", "n2"),
      _hyp("μ1", "μ2"), POOLED],
     _command("tTest_2Samp", "m1", "sx1", "n1", "m2", "sx2", "n2", "hyp", "pooled")),
    ([F("List 1", "l1"), F("List 2", "l2"), FREQ1, FREQ2, _hyp("μ1", "μ2"), POOLED],
     _command("tTest_2Samp", "l1", "l2", "freq1", "freq2", "hyp", "pooled")))
Z_TEST_1PROP = _wizard("1-Prop z Test", [F("p0", "p0"), F("Successes, x", "x"), F("n", "n"), _hyp("p", "p0")],
                       _command("zTest_1Prop", "p0", "x", "n", "hyp"))
Z_TEST_2PROP = _wizard("2-Prop z Test", [F("Successes, x1", "x1"), F("n1", "n1"), F("Successes, x2", "x2"),
                                         F("n2", "n2"), _hyp("p1", "p2")],
                       _command("zTest_2Prop", "x1", "n1", "x2", "n2", "hyp"))
CHI2_GOF = _wizard("χ² GOF", [F("Observed List", "obs"), F("Expected List", "exp"), F("Deg of Freedom, df", "df")],
                   _command("χ²GOF", "obs", "exp", "df"))
CHI2_2WAY = _wizard("χ² 2-way Test", [F("Observed Matrix", "m")], _command("χ²2way", "m"))
F_TEST_2SAMP = _stats_data(
    "2-Sample F Test",
    ([F("sx1", "sx1"), F("n1", "n1"), F("sx2", "sx2"), F("n2", "n2"), _hyp("σ1", "σ2")],
     _command("FTest_2Samp", "sx1", "n1", "sx2", "n2", "hyp")),
    ([F("List 1", "l1"), F("List 2", "l2"), FREQ1, FREQ2, _hyp("σ1", "σ2")],
     _command("FTest_2Samp", "l1", "l2", "freq1", "freq2", "hyp")))
LINREG_T_TEST = _wizard("Linear Reg t Test", [F("X List", "x"), F("Y List", "y"), FREQ, _hyp("β & ρ", "0")],
                        _command("LinRegtTest", "x", "y", "freq", "hyp"))
ANOVA_WIZARD = _wizard("ANOVA", [F("List 1", "l1"), F("List 2", "l2"), F("List 3", "l3", optional=True),
                                 F("List 4", "l4", optional=True), F("List 5", "l5", optional=True)],
                       _command("ANOVA", "l1", "l2", "l3", "l4", "l5"))

# ------------------------------------------------------------------ stat calculation wizards

ONE_VAR = _wizard("One-Variable Statistics", [F("X1 List", "list"), FREQ,
                                               F("Category List", "cat", enabled=False),
                                               F("Include Categories", "inc", enabled=False)],
                  _command("OneVar", "list", "freq"))
TWO_VAR = _wizard("Two-Variable Statistics", [F("X List", "x"), F("Y List", "y"), FREQ,
                                               F("Category List", "cat", enabled=False),
                                               F("Include Categories", "inc", enabled=False)],
                  _command("TwoVar", "x", "y", "freq"))


def _reg_wizard(title: str, command: str) -> Wizard:
    return _wizard(title, [F("X List", "x"), F("Y List", "y"), F("Save RegEqn To", "save", "f1"), FREQ,
                           F("Category List", "cat", enabled=False),
                           F("Include Categories", "inc", enabled=False)],
                   _regression(command, "x", "y", "freq"))


SIN_REG = _wizard("Sinusoidal Regression", [F("X List", "x"), F("Y List", "y"), F("Iterations", "iter", "8"),
                                            F("Period", "period", optional=True),
                                            F("Save RegEqn To", "save", "f1"),
                                            F("Category List", "cat", enabled=False),
                                            F("Include Categories", "inc", enabled=False)],
                  _regression("SinReg", "x", "y", "iter", "period"))
MULT_REG = _wizard("Multiple Linear Regression", [F("Y List", "y"), F("X1 List", "x1"), F("X2 List", "x2", optional=True),
                                                  F("X3 List", "x3", optional=True)],
                   _command("MultReg", "y", "x1", "x2", "x3"))

# ------------------------------------------------------------------ finance wizards

TVM_FIELDS = ["N", "I", "PV", "Pmt", "FV"]


def _finance_solver(values: dict[str, str]) -> str:
    target = values.get("solve", "FV")
    args = {k: values.get(k.lower(), "").strip() or "0" for k in TVM_FIELDS}
    ppy, cpy = values.get("ppy", "1") or "1", values.get("cpy", "1") or "1"
    at = values.get("at", "0") or "0"
    order = {"N": ["I", "PV", "Pmt", "FV"], "I": ["N", "PV", "Pmt", "FV"], "PV": ["N", "I", "Pmt", "FV"],
             "Pmt": ["N", "I", "PV", "FV"], "FV": ["N", "I", "PV", "Pmt"]}[target]
    return f"tvm{target}({','.join(args[k] for k in order)},{ppy},{cpy},{at})"


FINANCE_SOLVER = _wizard("Finance Solver", [
    F("Solve for", "solve", "FV", choices=[(k, k) for k in TVM_FIELDS]),
    F("N", "n", "0"), F("I(%)", "i", "0"), F("PV", "pv", "0"), F("Pmt", "pmt", "0"), F("FV", "fv", "0"),
    F("PpY", "ppy", "1"), F("CpY", "cpy", "1"),
    F("Payment at", "at", "0", choices=[("END", "0"), ("BEGIN", "1")])], _finance_solver)

# ------------------------------------------------------------------ menu tree

M = MenuItem


def _off(key: str, label: str, unsure: bool = False, children: list[MenuItem] | None = None) -> MenuItem:
    return MenuItem(key, label, enabled=False, unsure=unsure, children=children or [])


def _distributions() -> list[MenuItem]:
    # order from the official eGuide (Statistics > Distributions)
    return [
        M("1", "Normal Pdf", wizard=NORMAL_PDF),
        M("2", "Normal Cdf", wizard=NORMAL_CDF),
        M("3", "Inverse Normal", wizard=INVERSE_NORMAL),
        M("4", "t Pdf", wizard=T_PDF),
        M("5", "t Cdf", wizard=T_CDF),
        M("6", "Inverse t", wizard=INVERSE_T),
        M("7", "χ² Pdf", wizard=CHI2_PDF),
        M("8", "χ² Cdf", wizard=CHI2_CDF),
        M("9", "F Pdf", wizard=F_PDF),
        M("A", "F Cdf", wizard=F_CDF),
        M("B", "Binomial Pdf", wizard=BINOMIAL_PDF),
        M("C", "Binomial Cdf", wizard=BINOMIAL_CDF),
        M("D", "Inverse Binomial", wizard=INVERSE_BINOMIAL),
        M("E", "Inverse Binomial with respect to N", wizard=INVERSE_BINOMIAL_N),
        M("F", "Poisson Pdf", wizard=POISSON_PDF),
        M("G", "Poisson Cdf", wizard=POISSON_CDF),
        M("H", "Geometric Pdf", wizard=GEOMETRIC_PDF),
        M("I", "Geometric Cdf", wizard=GEOMETRIC_CDF),
    ]


MENU: list[MenuItem] = [
    M("1", "Actions", unsure=True, children=[
        M("1", "Define", insert="Define "),
        M("2", "Recall Definition", action="recall_definition"),
        M("3", "Delete Variable", insert="DelVar "),
        M("4", "Clear a-z...", action="clear_az"),
        M("5", "Clear History", action="clear_history"),
        M("6", "Insert Comment", insert="©"),
        M("7", "Library", children=[
            M("1", "Refresh Libraries", action="refresh_libraries"),
            M("2", "Open Library Folder", action="open_library_folder"),
            M("3", "Create Shortcuts", insert="libShortcut("),
            M("4", "Define LibPub", insert="Define LibPub "),
            M("5", "Define LibPriv", insert="Define LibPriv "),
        ]),
        M("8", "Lock", children=[
            M("1", "Lock Variable", insert="Lock "),
            M("2", "Unlock Variable", insert="unLock "),
            M("3", "Get Lock Info", insert="getLockInfo("),
        ]),
    ]),
    M("2", "Number", unsure=True, children=[
        M("1", "Convert to Decimal", insert="►Decimal"),
        M("2", "Approximate to Fraction", insert="►approxFraction()"),
        M("3", "Factor", insert="factor("),
        M("4", "Least Common Multiple", insert="lcm("),
        M("5", "Greatest Common Divisor", insert="gcd("),
        M("6", "Remainder", insert="remain("),
        M("7", "Fraction Tools", children=[
            M("1", "Proper Fraction", insert="propFrac("),
            M("2", "Get Numerator", insert="getNum("),
            M("3", "Get Denominator", insert="getDenom("),
        ]),
        M("8", "Number Tools", children=[
            M("1", "Round", insert="round("),
            M("2", "Integer Part", insert="iPart("),
            M("3", "Fractional Part", insert="fPart("),
            M("4", "Sign", insert="sign("),
            M("5", "Modulo", insert="mod("),
            M("6", "Floor", insert="floor("),
            M("7", "Ceiling", insert="ceiling("),
        ]),
        M("9", "Complex Number Tools", children=[
            M("1", "Complex Conjugate", insert="conj("),
            M("2", "Real Part", insert="real("),
            M("3", "Imaginary Part", insert="imag("),
            M("4", "Polar Angle", insert="angle("),
            M("5", "Magnitude", insert="abs("),
            M("6", "Convert to Polar", insert="►Polar"),
            M("7", "Convert to Rectangular", insert="►Rect"),
        ]),
        M("A", "Prime Number Test", insert="isPrime("),
    ]),
    M("3", "Algebra", children=[
        M("1", "Solve", insert="solve("),
        M("2", "Factor", insert="factor("),
        M("3", "Expand", insert="expand("),
        M("4", "Zeros", insert="zeros("),
        M("5", "Complete the Square", insert="completeSquare(", unsure=True),
        M("6", "Numerical Solve", insert="nSolve(", unsure=True),
        M("7", "Solve System of Equations", unsure=True, children=[
            M("1", "Solve System of Equations", insert="solve( and ,{x,y})"),
            M("2", "Solve System of Linear Equations", insert="linSolve( and ,{x,y})"),
        ]),
        M("8", "Polynomial Tools", unsure=True, children=[
            M("1", "Find Roots of Polynomial", insert="polyRoots("),
            M("2", "Real Roots of Polynomial", insert="polyRoots("),
            M("3", "Complex Roots of Polynomial", insert="cPolyRoots("),
            M("4", "Remainder of Polynomial", insert="polyRemainder("),
            M("5", "Quotient of Polynomial", insert="polyQuotient("),
            M("6", "GCD of Polynomials", insert="polyGcd("),
            M("7", "Coefficients of Polynomial", insert="polyCoeffs("),
            M("8", "Degree of Polynomial", insert="polyDegree("),
        ]),
        M("9", "Fraction Tools", unsure=True, children=[
            M("1", "Proper Fraction", insert="propFrac("),
            M("2", "Get Numerator", insert="getNum("),
            M("3", "Get Denominator", insert="getDenom("),
            M("4", "Common Denominator", insert="comDenom("),
        ]),
        M("A", "Convert Expression", unsure=True, children=[
            M("1", "Convert to ln", insert="►ln"),
            M("2", "Convert to logbase", insert="►logbase("),
            M("3", "Convert to exp", insert="►exp"),
            M("4", "Convert to sin", insert="►sin"),
            M("5", "Convert to cos", insert="►cos"),
        ]),
        M("B", "Trigonometry", unsure=True, children=[
            M("1", "Expand", insert="tExpand("),
            M("2", "Collect", insert="tCollect("),
        ]),
        M("C", "Complex", unsure=True, children=[
            M("1", "Solve", insert="cSolve("),
            M("2", "Factor", insert="cFactor("),
            M("3", "Zeros", insert="cZeros("),
        ]),
        M("D", "Extract", unsure=True, children=[
            M("1", "Left", insert="left("),
            M("2", "Right", insert="right("),
        ]),
        M("E", "Piecewise Function", insert="piecewise(", unsure=True),
    ]),
    M("4", "Calculus", children=[
        M("1", "Derivative", insert="d("),
        M("2", "Derivative at a Point", insert="d(", unsure=True),
        M("3", "Integral", insert="∫("),
        M("4", "Limit", insert="limit("),
        M("5", "Sum", insert="Σ(", unsure=True),
        M("6", "Product", insert="Π(", unsure=True),
        M("7", "Function Minimum", insert="fMin(", unsure=True),
        M("8", "Function Maximum", insert="fMax(", unsure=True),
        M("9", "Tangent Line", insert="tangentLine(", unsure=True),
        M("A", "Normal Line", insert="normalLine(", unsure=True),
        M("B", "Arc Length", insert="arcLen(", unsure=True),
        M("C", "Series", unsure=True, children=[
            M("1", "Taylor Polynomial", insert="taylor("),
            M("2", "Generalized Series", insert="series("),
            M("3", "Dominant Term", insert="dominantTerm("),
        ]),
        M("D", "Differential Equation Solver", insert="deSolve(", unsure=True),
        M("E", "Implicit Differentiation", insert="impDif(", unsure=True),
        M("F", "Numerical Calculations", unsure=True, children=[
            M("1", "Numerical Derivative at a Point", insert="nDerivative("),
            M("2", "Numerical Integral", insert="nInt("),
            M("3", "Numerical Function Minimum", insert="nfMin("),
            M("4", "Numerical Function Maximum", insert="nfMax("),
            M("5", "Central Difference Quotient", insert="centralDiff("),
            M("6", "Average Rate of Change", insert="avgRC("),
        ]),
    ]),
    M("5", "Probability", children=[
        M("1", "Factorial (!)", insert="!"),
        M("2", "Permutations", insert="nPr("),
        M("3", "Combinations", insert="nCr("),
        M("4", "Random", unsure=True, children=[
            M("1", "Number", insert="rand("),
            M("2", "Integer", insert="randInt("),
            M("3", "Binomial", insert="randBin("),
            M("4", "Normal", insert="randNorm("),
            M("5", "Sample", insert="randSamp("),
            M("6", "Seed", insert="RandSeed "),
        ]),
        M("5", "Distributions", children=_distributions()),
    ]),
    M("6", "Statistics", children=[
        M("1", "Stat Calculations", children=[
            M("1", "One-Variable Statistics", wizard=ONE_VAR),
            M("2", "Two-Variable Statistics", wizard=TWO_VAR),
            M("3", "Linear Regression (mx+b)", wizard=_reg_wizard("Linear Regression (mx+b)", "LinRegMx")),
            M("4", "Linear Regression (a+bx)", wizard=_reg_wizard("Linear Regression (a+bx)", "LinRegBx")),
            M("5", "Median-Median Line", wizard=_reg_wizard("Median-Median Line", "MedMed")),
            M("6", "Quadratic Regression", wizard=_reg_wizard("Quadratic Regression", "QuadReg")),
            M("7", "Cubic Regression", wizard=_reg_wizard("Cubic Regression", "CubicReg")),
            M("8", "Quartic Regression", wizard=_reg_wizard("Quartic Regression", "QuartReg")),
            M("9", "Power Regression", wizard=_reg_wizard("Power Regression", "PowerReg")),
            M("A", "Exponential Regression", wizard=_reg_wizard("Exponential Regression", "ExpReg")),
            M("B", "Logarithmic Regression", wizard=_reg_wizard("Logarithmic Regression", "LnReg")),
            M("C", "Sinusoidal Regression", wizard=SIN_REG),
            M("D", "Logistic Regression (d=0)", wizard=_reg_wizard("Logistic Regression (d=0)", "Logistic")),
            M("E", "Logistic Regression (d≠0)", wizard=_reg_wizard("Logistic Regression (d≠0)", "LogisticD")),
            M("F", "Multiple Linear Regression", wizard=MULT_REG),
        ]),
        M("2", "Stat Results", insert="stat.results", unsure=True),
        M("3", "List Math", unsure=True, children=[
            M("1", "Minimum", insert="min("),
            M("2", "Maximum", insert="max("),
            M("3", "Mean", insert="mean("),
            M("4", "Median", insert="median("),
            M("5", "Sum of Elements", insert="sum("),
            M("6", "Product of Elements", insert="product("),
            M("7", "Sample Standard Deviation", insert="stDevSamp("),
            M("8", "Sample Variance", insert="varSamp("),
            M("9", "Population Standard Deviation", insert="stDevPop("),
            M("A", "Population Variance", insert="varPop("),
        ]),
        M("4", "List Operations", unsure=True, children=[
            M("1", "Sort Ascending", insert="SortA "),
            M("2", "Sort Descending", insert="SortD "),
            M("3", "Cumulative Sum List", insert="cumulativeSum("),
            M("4", "Fill", insert="Fill "),
            M("5", "Frequency", insert="frequency("),
            M("6", "Difference List", insert="ΔList("),
            M("7", "Delete Void Elements", insert="delVoid("),
            M("8", "Augment", insert="augment("),
            M("9", "Create List", insert="newList("),
            M("A", "Sequence", insert="seq("),
        ]),
        M("5", "Distributions", unsure=True, children=_distributions()),
        M("6", "Confidence Intervals", children=[
            M("1", "z Interval", wizard=Z_INTERVAL),
            M("2", "t Interval", wizard=T_INTERVAL),
            M("3", "2-Sample z Interval", wizard=Z_INTERVAL_2SAMP),
            M("4", "2-Sample t Interval", wizard=T_INTERVAL_2SAMP),
            M("5", "1-Prop z Interval", wizard=Z_INTERVAL_1PROP),
            M("6", "2-Prop z Interval", wizard=Z_INTERVAL_2PROP),
            M("7", "Linear Reg t Intervals", wizard=LINREG_T_INTERVALS),
            M("8", "Multiple Reg Intervals", insert="MultRegIntervals "),
        ]),
        M("7", "Stat Tests", children=[
            M("1", "z Test", wizard=Z_TEST),
            M("2", "t Test", wizard=T_TEST),
            M("3", "2-Sample z Test", wizard=Z_TEST_2SAMP),
            M("4", "2-Sample t Test", wizard=T_TEST_2SAMP),
            M("5", "1-Prop z Test", wizard=Z_TEST_1PROP),
            M("6", "2-Prop z Test", wizard=Z_TEST_2PROP),
            M("7", "χ² GOF", wizard=CHI2_GOF),
            M("8", "χ² 2-way Test", wizard=CHI2_2WAY),
            M("9", "2-Sample F Test", wizard=F_TEST_2SAMP),
            M("A", "Linear Reg t Test", wizard=LINREG_T_TEST),
            M("B", "Multiple Reg Tests", insert="MultRegTests "),
            M("C", "ANOVA", wizard=ANOVA_WIZARD),
            M("D", "ANOVA 2-Way", insert="ANOVA2way "),
        ]),
    ]),
    M("7", "Matrix & Vector", unsure=True, children=[
        M("1", "Create", children=[
            M("1", "Matrix", insert="[ , ; , ]"),
            M("2", "Zero Matrix", insert="newMat("),
            M("3", "Identity", insert="identity("),
            M("4", "Diagonal", insert="diag("),
            M("5", "Random Matrix", insert="randMat("),
            M("6", "Fill", insert="Fill "),
            M("7", "Construct Matrix", insert="constructMat("),
            M("8", "Submatrix", insert="subMat("),
            M("9", "Augment", insert="augment("),
            M("A", "Column Augment", insert="colAugment("),
        ]),
        M("2", "Transpose", insert="ᵀ"),
        M("3", "Determinant", insert="det("),
        M("4", "Row-Echelon Form", insert="ref("),
        M("5", "Reduced Row-Echelon Form", insert="rref("),
        M("6", "Simultaneous", insert="simult("),
        M("7", "Norms", children=[
            M("1", "Norm", insert="norm("),
            M("2", "Row Norm", insert="rowNorm("),
            M("3", "Column Norm", insert="colNorm("),
        ]),
        M("8", "Dimensions", children=[
            M("1", "Dimension", insert="dim("),
            M("2", "Row Dimension", insert="rowDim("),
            M("3", "Column Dimension", insert="colDim("),
        ]),
        M("9", "Row Operations", children=[
            M("1", "Swap Rows", insert="rowSwap("),
            M("2", "Add Row to Another", insert="rowAdd("),
            M("3", "Multiply Row", insert="mRow("),
            M("4", "Multiply Row & Add", insert="mRowAdd("),
        ]),
        M("A", "Element Operations", children=[
            M("1", "Dot Add", insert=".+"),
            M("2", "Dot Subtract", insert=".-"),
            M("3", "Dot Multiply", insert=".*"),
            M("4", "Dot Divide", insert="./"),
            M("5", "Dot Power", insert=".^"),
        ]),
        M("B", "Advanced", children=[
            M("1", "Trace", insert="trace("),
            M("2", "Characteristic Polynomial", insert="charPoly("),
            M("3", "Eigenvalues", insert="eigVl("),
            M("4", "Eigenvectors", insert="eigVc("),
            M("5", "LU Decomposition", insert="LU "),
            M("6", "QR Decomposition", insert="QR "),
        ]),
        M("C", "Vector", children=[
            M("1", "Unit Vector", insert="unitV("),
            M("2", "Cross Product", insert="crossP("),
            M("3", "Dot Product", insert="dotP("),
        ]),
    ]),
    M("8", "Finance", unsure=True, children=[
        M("1", "Finance Solver...", wizard=FINANCE_SOLVER),
        M("2", "TVM Functions", children=[
            M("1", "Number of Payments", insert="tvmN("),
            M("2", "Interest Rate", insert="tvmI("),
            M("3", "Present Value", insert="tvmPV("),
            M("4", "Payment Amount", insert="tvmPmt("),
            M("5", "Future Value", insert="tvmFV("),
        ]),
        M("3", "Amortization", children=[
            M("1", "Amortization Table", insert="amortTbl("),
            M("2", "Balance", insert="bal("),
            M("3", "Interest Sum", insert="ΣInt("),
            M("4", "Principal Sum", insert="ΣPrn("),
        ]),
        M("4", "Cash Flows", children=[
            M("1", "Net Present Value", insert="npv("),
            M("2", "Internal Rate of Return", insert="irr("),
            M("3", "Modified Internal Rate of Return", insert="mirr("),
        ]),
        M("5", "Interest Conversion", children=[
            M("1", "Nominal Interest Rate", insert="nom("),
            M("2", "Effective Interest Rate", insert="eff("),
        ]),
        M("6", "Days between Dates", insert="dbd("),
    ]),
    M("9", "Functions & Programs", unsure=True, children=[
        M("1", "Program Editor", action="program_editor"),
        M("2", "Define", insert="Define "),
        M("3", "Control", children=[
            M("1", "If…Then…EndIf", insert="If  Then\n\nEndIf"),
            M("2", "For…EndFor", insert="For i,1,10\n\nEndFor"),
            M("3", "While…EndWhile", insert="While \n\nEndWhile"),
            M("4", "Loop…EndLoop", insert="Loop\n\nEndLoop"),
            M("5", "Try…Else…EndTry", insert="Try\n\nElse\n\nEndTry"),
        ]),
        M("4", "I/O", children=[
            M("1", "Disp", insert="Disp "),
            M("2", "Request", insert="Request "),
            M("3", "RequestStr", insert="RequestStr "),
            M("4", "Text", insert="Text "),
        ]),
        M("5", "Mode", children=[
            M("1", "Get Mode", insert="getMode("),
            M("2", "Set Mode", insert="setMode("),
        ]),
    ]),
]


def iter_paths(items: list[MenuItem] | None = None, prefix: tuple[str, ...] = ()):
    """Yield (path labels, item) for every menu entry."""
    for item in MENU if items is None else items:
        path = prefix + (f"{item.key}: {item.label}",)
        yield path, item
        yield from iter_paths(item.children, path)


def find_path(*keys: str) -> MenuItem:
    """find_path("5", "5", "2") → Normal Cdf."""
    items = MENU
    item = None
    for key in keys:
        item = next((i for i in items if i.key.upper() == key.upper()), None)
        if item is None:
            raise KeyError("/".join(keys))
        items = item.children
    assert item is not None
    return item


def render_tree(items: list[MenuItem] | None = None, indent: int = 0, max_depth: int = 9) -> str:
    from .i18n import tr

    lines: list[str] = []
    for item in MENU if items is None else items:
        marks = ""
        if not item.enabled:
            marks += "  (not available)"
        if item.unsure:
            marks += "  [?]"
        target = ""
        if item.wizard:
            target = "  → wizard"
        elif item.insert:
            target = f"  → {item.insert.splitlines()[0]}"
        lines.append(f"{'    ' * indent}{item.key}: {tr(item.label)}{target}{marks}")
        if item.children and indent + 1 < max_depth:
            lines.append(render_tree(item.children, indent + 1, max_depth))
    return "\n".join(lines)


# ------------------------------------------------------------------ Graphs page menu
# Numbering of the Graphs application menu is reconstructed from memory (unsure).

GRAPHS_MENU: list[MenuItem] = [
    M("1", "Actions", unsure=True, children=[
        M("1", "Delete All Functions", action="g_clear"),
        M("2", "Hide/Show Function List", action="g_toggle_list"),
    ]),
    M("2", "View", unsure=True, children=[
        M("1", "Hide/Show Entry Line", action="g_toggle_entry"),
        M("2", "Show/Hide Grid", action="g_toggle_grid"),
        M("3", "Show/Hide Axes", action="g_toggle_axes"),
    ]),
    M("3", "Graph Entry/Edit", unsure=True, children=[
        M("1", "Function", action="g_entry_function"),
        _off("2", "Equation"),
        M("3", "Parametric", action="g_entry_parametric"),
        M("4", "Polar", action="g_entry_polar"),
        M("5", "Scatter Plot", action="g_entry_scatter"),
        _off("6", "Sequence"),
        _off("7", "Diff Eq"),
    ]),
    M("4", "Window/Zoom", unsure=True, children=[
        M("1", "Window Settings...", action="g_window"),
        _off("2", "Zoom – Box"),
        M("3", "Zoom – In", action="g_zoom_in"),
        M("4", "Zoom – Out", action="g_zoom_out"),
        M("5", "Zoom – Standard", action="g_zoom_standard"),
        M("6", "Zoom – Quadrant 1", action="g_zoom_quadrant1"),
        _off("7", "Zoom – User"),
        M("8", "Zoom – Trig", action="g_zoom_trig"),
        M("9", "Zoom – Data", action="g_zoom_data"),
        M("A", "Zoom – Fit", action="g_zoom_fit"),
        M("B", "Zoom – Square", action="g_zoom_square"),
    ]),
    M("5", "Trace", unsure=True, children=[
        M("1", "Graph Trace", action="g_trace"),
    ]),
    M("6", "Analyze Graph", unsure=True, children=[
        M("1", "Zero", action="g_zero"),
        M("2", "Minimum", action="g_minimum"),
        M("3", "Maximum", action="g_maximum"),
        M("4", "Intersection", action="g_intersection"),
        M("5", "Inflection", action="g_inflection"),
        M("6", "dy/dx", action="g_dydx"),
        M("7", "Integral", action="g_integral"),
    ]),
    M("7", "Table", unsure=True, children=[
        M("1", "Split-screen Table", action="g_table"),
        M("2", "Remove Table", action="g_table_remove"),
        M("3", "Edit Table Settings...", action="g_table_settings"),
    ]),
    _off("8", "Geometry", unsure=True),
    M("9", "Settings", unsure=True, children=[
        M("1", "Axes: linear", action="g_scale_linear"),
        M("2", "Axes: semi-log (y logarithmic)", action="g_scale_semilogy"),
        M("3", "Axes: semi-log (x logarithmic)", action="g_scale_semilogx"),
        M("4", "Axes: log-log", action="g_scale_loglog"),
    ]),
]


# ------------------------------------------------------------------ Lists & Spreadsheet page menu
# Statistics submenu order (Stat Calculations, Distributions, Confidence Intervals,
# Stat Tests) follows the eGuide's Lists & Spreadsheet chapter; other numbers are unsure.

def _lists_menu() -> list[MenuItem]:
    statistics = find_path("6")
    return [
        M("1", "Actions", unsure=True, children=[
            M("1", "Clear Column Data", action="l_clear_column"),
            M("2", "Delete Column Name", action="l_delete_name"),
        ]),
        _off("2", "Insert", unsure=True),
        M("3", "Data", unsure=True, children=[
            M("1", "Generate Sequence", action="l_sequence"),
            _off("2", "Data Capture"),
            M("3", "Fill", action="l_fill"),
            M("4", "Quick Graph", action="l_quick_graph"),
            M("5", "Sort", children=[
                M("1", "Ascending", action="l_sort_asc"),
                M("2", "Descending", action="l_sort_desc"),
            ]),
        ]),
        M("4", "Statistics", children=[
            M("1", "Stat Calculations", children=find_path("6", "1").children),
            M("2", "Distributions", children=find_path("6", "5").children),
            M("3", "Confidence Intervals", children=find_path("6", "6").children),
            M("4", "Stat Tests", children=find_path("6", "7").children),
        ]) if statistics else _off("4", "Statistics"),
        _off("5", "Table", unsure=True),
    ]


LISTS_MENU: list[MenuItem] = _lists_menu()
