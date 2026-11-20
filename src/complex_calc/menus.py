"""Numbered Calculator menu tree and wizard (assistant dialog) definitions.

The numbering mirrors the menu of a handheld CAS calculator's Calculator page,
so learned key paths such as  Menu → 6 → 5 → 2  (Normal Cdf) work the same.
Items that this app does not implement are kept as disabled placeholders so
that the numbering of the following items stays correct.

Entries marked ``unsure=True`` were reconstructed from memory and are listed
in UNSURE_SYNTAX.md; please verify them on a real device.

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
    action: str | None = None  # special app action (clear history, ...)
    children: list["MenuItem"] = field(default_factory=list)
    enabled: bool = True
    unsure: bool = False

    @property
    def is_submenu(self) -> bool:
        return bool(self.children)


# ------------------------------------------------------------------ builders


def _call(name: str, *keys: str) -> Callable[[dict[str, str]], str]:
    """Build name(a,b,c), dropping empty trailing optional arguments."""

    def build(values: dict[str, str]) -> str:
        args = [values.get(k, "").strip() for k in keys]
        while args and not args[-1]:
            args.pop()
        return f"{name}({','.join(args)})"

    return build


def _command(name: str, *keys: str) -> Callable[[dict[str, str]], str]:
    def build(values: dict[str, str]) -> str:
        args = [values.get(k, "").strip() for k in keys]
        while args and not args[-1]:
            args.pop()
        return f"{name} {','.join(args)}"

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


def _wizard(title: str, fields: list[WizardField], build) -> Wizard:
    return Wizard(title, {"": WizardVariant(fields, build)})


F = WizardField

# ------------------------------------------------------------------ wizards

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
BINOMIAL_PDF = _wizard("Binomial Pdf", [F("Num Trials, n", "n"), F("Prob Success, p", "p"),
                                        F("X Value", "x", optional=True)],
                       _call("binomPdf", "n", "p", "x"))
BINOMIAL_CDF = _wizard("Binomial Cdf", [F("Num Trials, n", "n"), F("Prob Success, p", "p"),
                                        F("Lower Bound", "lo", "0"), F("Upper Bound", "hi")],
                       _call("binomCdf", "n", "p", "lo", "hi"))
INVERSE_BINOMIAL = _wizard("Inverse Binomial", [F("Cumulative Probability", "c"), F("Num Trials, n", "n"),
                                                F("Prob Success, p", "p")],
                           _call("invBinom", "c", "n", "p"))
POISSON_PDF = _wizard("Poisson Pdf", [F("λ", "lam"), F("X Value", "x")], _call("poissPdf", "lam", "x"))
POISSON_CDF = _wizard("Poisson Cdf", [F("λ", "lam"), F("Lower Bound", "lo", "0"), F("Upper Bound", "hi")],
                      _call("poissCdf", "lam", "lo", "hi"))
GEOMETRIC_PDF = _wizard("Geometric Pdf", [F("Prob Success, p", "p"), F("X Value", "x")], _call("geomPdf", "p", "x"))
GEOMETRIC_CDF = _wizard("Geometric Cdf", [F("Prob Success, p", "p"), F("Lower Bound", "lo", "1"),
                                          F("Upper Bound", "hi")],
                        _call("geomCdf", "p", "lo", "hi"))

Z_INTERVAL = Wizard("z Interval", {
    "Stats": WizardVariant([F("σ", "sigma"), F("x̄", "mean"), F("n", "n"), F("C Level", "c", "0.95")],
                           _command("zInterval", "sigma", "mean", "n", "c")),
    "Data": WizardVariant([F("σ", "sigma"), F("List", "list"), F("Frequency List", "freq", "1"),
                           F("C Level", "c", "0.95")],
                          _command("zInterval", "sigma", "list", "freq", "c")),
})
T_INTERVAL = Wizard("t Interval", {
    "Stats": WizardVariant([F("x̄", "mean"), F("sx", "sx"), F("n", "n"), F("C Level", "c", "0.95")],
                           _command("tInterval", "mean", "sx", "n", "c")),
    "Data": WizardVariant([F("List", "list"), F("Frequency List", "freq", "1"), F("C Level", "c", "0.95")],
                          _command("tInterval", "list", "freq", "c")),
})

ONE_VAR = _wizard("One-Variable Statistics", [F("X1 List", "list"), F("Frequency List", "freq", "1"),
                                               F("Category List", "cat", enabled=False),
                                               F("Include Categories", "inc", enabled=False)],
                  _command("OneVar", "list", "freq"))


def _reg_wizard(title: str, command: str) -> Wizard:
    return _wizard(title, [F("X List", "x"), F("Y List", "y"), F("Save RegEqn to", "save", "f1"),
                           F("Frequency List", "freq", "1"), F("Category List", "cat", enabled=False),
                           F("Include Categories", "inc", enabled=False)],
                   _regression(command, "x", "y", "freq"))


SIN_REG = _wizard("Sinusoidal Regression", [F("X List", "x"), F("Y List", "y"), F("Iterations", "iter", "8"),
                                            F("Period", "period", optional=True),
                                            F("Save RegEqn to", "save", "f1"),
                                            F("Category List", "cat", enabled=False),
                                            F("Include Categories", "inc", enabled=False)],
                  _regression("SinReg", "x", "y", "iter", "period"))

# ------------------------------------------------------------------ menu tree

M = MenuItem


def _off(key: str, label: str, unsure: bool = False, children: list[MenuItem] | None = None) -> MenuItem:
    return MenuItem(key, label, enabled=False, unsure=unsure, children=children or [])


def _distributions() -> list[MenuItem]:
    return [
        M("1", "Normal Pdf", wizard=NORMAL_PDF),
        M("2", "Normal Cdf", wizard=NORMAL_CDF),
        M("3", "Inverse Normal", wizard=INVERSE_NORMAL),
        M("4", "t Pdf", wizard=T_PDF),
        M("5", "t Cdf", wizard=T_CDF),
        M("6", "Inverse t", wizard=INVERSE_T),
        M("7", "χ² Pdf", wizard=CHI2_PDF),
        M("8", "χ² Cdf", wizard=CHI2_CDF),
        _off("9", "Inverse χ²"),
        _off("A", "F Pdf"),
        _off("B", "F Cdf"),
        _off("C", "Inverse F"),
        M("D", "Binomial Pdf", wizard=BINOMIAL_PDF, unsure=True),
        M("E", "Binomial Cdf", wizard=BINOMIAL_CDF, unsure=True),
        M("F", "Inverse Binomial", wizard=INVERSE_BINOMIAL, unsure=True),
        _off("G", "Inverse Binomial with respect to N", unsure=True),
        M("H", "Poisson Pdf", wizard=POISSON_PDF, unsure=True),
        M("I", "Poisson Cdf", wizard=POISSON_CDF, unsure=True),
        M("J", "Geometric Pdf", wizard=GEOMETRIC_PDF, unsure=True),
        M("K", "Geometric Cdf", wizard=GEOMETRIC_CDF, unsure=True),
    ]


MENU: list[MenuItem] = [
    M("1", "Actions", unsure=True, children=[
        M("1", "Define", insert="Define "),
        _off("2", "Recall Definition"),
        M("3", "Delete Variable", insert="DelVar "),
        M("4", "Clear a-z...", action="clear_az"),
        M("5", "Clear History", action="clear_history"),
        _off("6", "Insert Comment"),
        _off("7", "Library"),
        _off("8", "Lock"),
    ]),
    M("2", "Number", unsure=True, children=[
        M("1", "Convert to Decimal", insert="approx("),
        M("2", "Approximate to Fraction", insert="exact("),
        M("3", "Factor", insert="factor("),
        M("4", "Least Common Multiple", insert="lcm("),
        M("5", "Greatest Common Divisor", insert="gcd("),
        M("6", "Remainder", insert="remain("),
        _off("7", "Fraction Tools"),
        M("8", "Number Tools", unsure=True, children=[
            M("1", "Round", insert="round("),
            M("2", "Integer Part", insert="iPart("),
            M("3", "Fractional Part", insert="fPart("),
            M("4", "Sign", insert="sign("),
            M("5", "Modulo", insert="mod("),
            M("6", "Floor", insert="floor("),
            M("7", "Ceiling", insert="ceiling("),
        ]),
        M("9", "Complex Number Tools", unsure=True, children=[
            M("1", "Complex Conjugate", insert="conj("),
            M("2", "Real Part", insert="real("),
            M("3", "Imaginary Part", insert="imag("),
            _off("4", "Polar Angle"),
            M("5", "Magnitude", insert="abs("),
        ]),
    ]),
    M("3", "Algebra", children=[
        M("1", "Solve", insert="solve("),
        M("2", "Factor", insert="factor("),
        M("3", "Expand", insert="expand("),
        M("4", "Zeros", insert="zeros("),
        _off("5", "Complete the Square", unsure=True),
        M("6", "Numerical Solve", insert="nSolve(", unsure=True),
        M("7", "Solve System of Equations", insert="solve( and ,{x,y})", unsure=True),
        _off("8", "Polynomial Tools", unsure=True),
        _off("9", "Fraction Tools", unsure=True),
        _off("A", "Convert Expression", unsure=True),
        _off("B", "Trigonometry", unsure=True),
        M("C", "Complex", unsure=True, children=[
            M("1", "Solve", insert="cSolve("),
            M("2", "Factor", insert="cFactor("),
            M("3", "Zeros", insert="cZeros("),
        ]),
    ]),
    M("4", "Calculus", children=[
        M("1", "Derivative", insert="derivative("),
        M("2", "Derivative at a Point", insert="derivative(", unsure=True),
        M("3", "Integral", insert="∫("),
        M("4", "Limit", insert="limit("),
        _off("5", "Sum", unsure=True),
        _off("6", "Product", unsure=True),
        _off("7", "Function Minimum", unsure=True),
        _off("8", "Function Maximum", unsure=True),
        _off("9", "Tangent Line", unsure=True),
        _off("A", "Normal Line", unsure=True),
        _off("B", "Arc Length", unsure=True),
        _off("C", "Series", unsure=True),
        _off("D", "Differential Equation Solver", unsure=True),
        _off("E", "Implicit Differentiation", unsure=True),
        M("F", "Numerical Calculations", unsure=True, children=[
            M("1", "Numerical Derivative at a Point", insert="nDeriv("),
            M("2", "Numerical Integral", insert="nInt("),
        ]),
    ]),
    M("5", "Probability", children=[
        M("1", "Factorial (!)", insert="!"),
        M("2", "Permutations", insert="nPr("),
        M("3", "Combinations", insert="nCr("),
        _off("4", "Random"),
        M("5", "Distributions", children=_distributions()),
    ]),
    M("6", "Statistics", children=[
        M("1", "Stat Calculations", children=[
            M("1", "One-Variable Statistics", wizard=ONE_VAR),
            _off("2", "Two-Variable Statistics"),
            M("3", "Linear Regression (mx+b)", wizard=_reg_wizard("Linear Regression (mx+b)", "LinRegMx")),
            M("4", "Linear Regression (a+bx)", wizard=_reg_wizard("Linear Regression (a+bx)", "LinRegBx")),
            _off("5", "Median-Median Line"),
            M("6", "Quadratic Regression", wizard=_reg_wizard("Quadratic Regression", "QuadReg")),
            _off("7", "Cubic Regression"),
            _off("8", "Quartic Regression"),
            _off("9", "Power Regression"),
            M("A", "Exponential Regression", wizard=_reg_wizard("Exponential Regression", "ExpReg")),
            _off("B", "Logarithmic Regression"),
            M("C", "Sinusoidal Regression", wizard=SIN_REG),
            _off("D", "Logistic Regression (d=0)"),
            _off("E", "Logistic Regression (d≠0)"),
            _off("F", "Multiple Linear Regression"),
        ]),
        _off("2", "Stat Results"),
        M("3", "List Math", children=[
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
        _off("4", "List Operations"),
        M("5", "Distributions", children=_distributions()),
        M("6", "Confidence Intervals", children=[
            M("1", "z Interval", wizard=Z_INTERVAL),
            M("2", "t Interval", wizard=T_INTERVAL),
            _off("3", "2-Sample z Interval"),
            _off("4", "2-Sample t Interval"),
            _off("5", "1-Prop z Interval"),
            _off("6", "2-Prop z Interval"),
            _off("7", "Linear Reg t Intervals"),
            _off("8", "Multiple Reg Intervals"),
        ]),
        _off("7", "Stat Tests"),
    ]),
    _off("7", "Matrix & Vector"),
    _off("8", "Finance"),
    _off("9", "Functions & Programs"),
]


def iter_paths(items: list[MenuItem] | None = None, prefix: tuple[str, ...] = ()):
    """Yield (path keys, path labels, item) for every menu entry."""
    for item in MENU if items is None else items:
        path = prefix + (f"{item.key}: {item.label}",)
        yield path, item
        yield from iter_paths(item.children, path)


def find_path(*keys: str) -> MenuItem:
    """find_path("6", "5", "2") → Normal Cdf."""
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
            target = f"  → {item.insert}"
        lines.append(f"{'    ' * indent}{item.key}: {item.label}{target}{marks}")
        if item.children and indent + 1 < max_depth:
            lines.append(render_tree(item.children, indent + 1, max_depth))
    return "\n".join(lines)
