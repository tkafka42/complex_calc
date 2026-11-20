"""Elementary functions: ln, log, trig (Rad/Deg aware), √, abs, nCr, ..."""

from __future__ import annotations

import sympy as sp

from ..core.errors import DomainError
from .registry import builtin, to_int

ALL = (0, 1, 2)


def _to_radians(ctx, x):
    return x * sp.pi / 180 if ctx.settings.angle == "deg" else x


def _from_radians(ctx, x):
    return x * 180 / sp.pi if ctx.settings.angle == "deg" else x


@builtin("sin", "sin(Expr)", 1, listable=(0,), summary="Sine (uses the angle mode)")
def sin_(ctx, x):
    return sp.sin(_to_radians(ctx, x))


@builtin("cos", "cos(Expr)", 1, listable=(0,), summary="Cosine (uses the angle mode)")
def cos_(ctx, x):
    return sp.cos(_to_radians(ctx, x))


@builtin("tan", "tan(Expr)", 1, listable=(0,), summary="Tangent (uses the angle mode)")
def tan_(ctx, x):
    return sp.tan(_to_radians(ctx, x))


@builtin("sin⁻¹", "sin⁻¹(Expr)", 1, aliases=("arcsin", "asin"), listable=(0,), summary="Inverse sine")
def arcsin_(ctx, x):
    return _from_radians(ctx, sp.asin(x))


@builtin("cos⁻¹", "cos⁻¹(Expr)", 1, aliases=("arccos", "acos"), listable=(0,), summary="Inverse cosine")
def arccos_(ctx, x):
    return _from_radians(ctx, sp.acos(x))


@builtin("tan⁻¹", "tan⁻¹(Expr)", 1, aliases=("arctan", "atan"), listable=(0,), summary="Inverse tangent")
def arctan_(ctx, x):
    return _from_radians(ctx, sp.atan(x))


@builtin("ln", "ln(Expr)", 1, listable=(0,), summary="Natural logarithm")
def ln_(ctx, x):
    if x == 0:
        raise DomainError("ln(0) is undefined")
    return sp.log(x)


@builtin("log", "log(Expr[,Base])", 1, 2, listable=(0, 1), summary="Logarithm, base 10 by default")
def log_(ctx, x, base=10):
    if x == 0:
        raise DomainError("log(0) is undefined")
    if base in (0, 1):
        raise DomainError("Base must not be 0 or 1")
    result = sp.log(x, base)
    simplified = sp.simplify(result)
    return simplified if simplified.is_Rational else result


@builtin("√", "√(Expr)", 1, aliases=("sqrt",), listable=(0,), summary="Square root")
def sqrt_(ctx, x):
    return sp.sqrt(x)


@builtin("root", "root(Expr[,n])", 1, 2, listable=(0, 1), summary="n-th root")
def root_(ctx, x, n=3):
    n = sp.sympify(n)
    if x.is_real and x.is_negative and n.is_integer and n.is_odd:
        return -sp.root(-x, n)  # real root of a negative number, e.g. root(-8,3) = -2
    return sp.root(x, n)


@builtin("abs", "abs(Expr)", 1, listable=(0,), summary="Absolute value")
def abs_(ctx, x):
    return sp.Abs(x)


@builtin("nCr", "nCr(n,r)", 2, listable=ALL, summary="Combinations")
def ncr_(ctx, n, r):
    return sp.binomial(n, r)


@builtin("nPr", "nPr(n,r)", 2, listable=ALL, summary="Permutations")
def npr_(ctx, n, r):
    return sp.ff(n, r)


@builtin("round", "round(Expr[,digits])", 1, 2, listable=ALL, approx=True, summary="Round to digits after the decimal point")
def round_(ctx, x, digits=12):
    d = to_int(digits, "digits")
    return sp.Float(round(float(sp.N(x)), d))


@builtin("floor", "floor(Expr)", 1, listable=(0,), summary="Greatest integer ≤ Expr")
def floor_(ctx, x):
    return sp.floor(x)


@builtin("ceiling", "ceiling(Expr)", 1, listable=(0,), summary="Smallest integer ≥ Expr")
def ceiling_(ctx, x):
    return sp.ceiling(x)


@builtin("iPart", "iPart(Number)", 1, listable=(0,), summary="Integer part")
def ipart_(ctx, x):
    return sp.sign(x) * sp.floor(sp.Abs(x))


@builtin("fPart", "fPart(Number)", 1, listable=(0,), summary="Fractional part")
def fpart_(ctx, x):
    return x - sp.sign(x) * sp.floor(sp.Abs(x))


@builtin("mod", "mod(Number1,Number2)", 2, listable=ALL, summary="Remainder (sign of divisor)")
def mod_(ctx, a, b):
    if b == 0:
        return a
    return sp.Mod(a, b)


@builtin("gcd", "gcd(Number1,Number2)", 2, listable=ALL, summary="Greatest common divisor")
def gcd_(ctx, a, b):
    return sp.gcd(a, b)


@builtin("lcm", "lcm(Number1,Number2)", 2, listable=ALL, summary="Least common multiple")
def lcm_(ctx, a, b):
    return sp.lcm(a, b)


@builtin("real", "real(Expr)", 1, listable=(0,), summary="Real part")
def real_(ctx, x):
    return sp.re(x)


@builtin("imag", "imag(Expr)", 1, listable=(0,), summary="Imaginary part")
def imag_(ctx, x):
    return sp.im(x)


@builtin("conj", "conj(Expr)", 1, listable=(0,), summary="Complex conjugate")
def conj_(ctx, x):
    return sp.conjugate(x)


@builtin("remain", "remain(Number1,Number2)", 2, listable=ALL, summary="Remainder (sign of dividend)")
def remain_(ctx, a, b):
    if b == 0:
        return a
    quotient = a / b
    return a - b * (sp.sign(quotient) * sp.floor(sp.Abs(quotient)))


@builtin("sign", "sign(Expr)", 1, listable=(0,), summary="Sign: -1, 0 or 1")
def sign_(ctx, x):
    return sp.sign(x)


# ------------------------------------------------------------------ more trig / hyperbolic


def _trig(name: str, func, summary: str, aliases: tuple[str, ...] = ()):
    @builtin(name, f"{name}(Expr)", 1, listable=(0,), aliases=aliases, summary=summary)
    def wrapper(ctx, x):
        return func(_to_radians(ctx, x))

    return wrapper


def _inverse(name: str, func, summary: str, aliases: tuple[str, ...]):
    @builtin(name, f"{name}(Expr)", 1, listable=(0,), aliases=aliases, summary=summary)
    def wrapper(ctx, x):
        return _from_radians(ctx, func(x))

    return wrapper


def _plain(name: str, func, summary: str, aliases: tuple[str, ...] = ()):
    @builtin(name, f"{name}(Expr)", 1, listable=(0,), aliases=aliases, summary=summary)
    def wrapper(ctx, x):
        return func(x)

    return wrapper


_trig("sec", sp.sec, "Secant")
_trig("csc", sp.csc, "Cosecant")
_trig("cot", sp.cot, "Cotangent")
_inverse("sec⁻¹", sp.asec, "Inverse secant", ("arcsec",))
_inverse("csc⁻¹", sp.acsc, "Inverse cosecant", ("arccsc",))
_inverse("cot⁻¹", sp.acot, "Inverse cotangent", ("arccot",))
_plain("sinh", sp.sinh, "Hyperbolic sine")
_plain("cosh", sp.cosh, "Hyperbolic cosine")
_plain("tanh", sp.tanh, "Hyperbolic tangent")
_plain("sech", sp.sech, "Hyperbolic secant")
_plain("csch", sp.csch, "Hyperbolic cosecant")
_plain("coth", sp.coth, "Hyperbolic cotangent")
_plain("sinh⁻¹", sp.asinh, "Inverse hyperbolic sine", ("arcsinh",))
_plain("cosh⁻¹", sp.acosh, "Inverse hyperbolic cosine", ("arccosh",))
_plain("tanh⁻¹", sp.atanh, "Inverse hyperbolic tangent", ("arctanh",))
_plain("sech⁻¹", sp.asech, "Inverse hyperbolic secant", ("arcsech",))
_plain("csch⁻¹", sp.acsch, "Inverse hyperbolic cosecant", ("arccsch",))
_plain("coth⁻¹", sp.acoth, "Inverse hyperbolic cotangent", ("arccoth",))


@builtin("exp", "exp(Expr)", 1, listable=(0,), matrix_aware=True, summary="ℯ raised to Expr")
def exp_(ctx, x):
    if hasattr(x, "is_square") and x.is_square:
        return sp.ImmutableMatrix(x.exp())
    return sp.exp(x)


@builtin("int", "int(Expr)", 1, listable=(0,), summary="Greatest integer ≤ Expr (same as floor)")
def int_(ctx, x):
    return sp.floor(x)


@builtin("intDiv", "intDiv(Number1,Number2)", 2, listable=ALL, summary="Signed integer part of Number1/Number2")
def int_div(ctx, a, b):
    if b == 0:
        raise DomainError("Division by zero")
    q = a / b
    return sp.sign(q) * sp.floor(sp.Abs(q))


@builtin("isPrime", "isPrime(Number)", 1, listable=(0,), summary="true if Number is a prime ≥ 2")
def is_prime(ctx, n):
    if not (isinstance(n, sp.Integer) or (n.is_number and float(n).is_integer())):
        raise DomainError("isPrime needs a whole number")
    return sp.true if sp.isprime(int(n)) else sp.false


@builtin("angle", "angle(Expr)", 1, listable=(0,), summary="Polar angle of a complex number")
def angle_(ctx, x):
    return _from_radians(ctx, sp.arg(x))


@builtin("approxRational", "approxRational(Expr[,Tol])", 1, 2, listable=(0,), exact=True,
         summary="Fraction approximating Expr within Tol (default 5E-14)")
def approx_rational(ctx, x, tol=None):
    from .conversions import simplest_fraction

    tolerance = float(tol) if tol is not None else 5e-14
    return simplest_fraction(x, tolerance)


@builtin("getNum", "getNum(Expr)", 1, listable=(0,), summary="Numerator after combining fractions")
def get_num(ctx, x):
    return sp.fraction(sp.cancel(sp.together(x)))[0]


@builtin("getDenom", "getDenom(Expr)", 1, listable=(0,), summary="Denominator after combining fractions")
def get_denom(ctx, x):
    return sp.fraction(sp.cancel(sp.together(x)))[1]


@builtin("comDenom", "comDenom(Expr[,Var])", 1, 2, hold=(1,), listable=(0,), summary="Common denominator form")
def com_denom(ctx, x, var=None):
    num, den = sp.fraction(sp.cancel(sp.together(x)))
    return sp.Mul(sp.expand(num), sp.Pow(sp.expand(den), -1), evaluate=False) if den != 1 else sp.expand(num)


@builtin("propFrac", "propFrac(Expr[,Var])", 1, 2, hold=(1,), listable=(0,), summary="Proper fraction expansion")
def prop_frac(ctx, x, var=None):
    if isinstance(x, sp.Rational) and not isinstance(x, sp.Integer):
        whole = sp.sign(x) * (abs(x.p) // x.q)
        rest = x - whole
        return sp.Add(whole, rest, evaluate=False) if whole != 0 else rest
    symbol = var if isinstance(var, sp.Symbol) else None
    if symbol is None:
        symbols = sorted(x.free_symbols, key=lambda s: s.name)
        symbol = symbols[0] if symbols else None
    if symbol is None:
        return x
    num, den = sp.fraction(sp.together(x))
    quotient, remainder = sp.div(sp.Poly(num, symbol), sp.Poly(den, symbol))
    return quotient.as_expr() + remainder.as_expr() / den


@builtin("tExpand", "tExpand(Expr)", 1, listable=(0,), summary="Expand trig of sums/multiples")
def t_expand(ctx, x):
    return sp.expand_trig(x)


@builtin("tCollect", "tCollect(Expr)", 1, listable=(0,), summary="Collect trig products/powers into multiple angles")
def t_collect(ctx, x):
    return sp.simplify(sp.fu(x, measure=lambda e: e.count_ops()))


# ------------------------------------------------------------------ functions of square matrices
# The reference guide defines sin(squareMatrix), ln(squareMatrix), √(squareMatrix) …
# as matrix functions (not element by element). Lists are still mapped element-wise.

def _matrix_function(spec_name: str, scalar):
    from .registry import REGISTRY

    spec = REGISTRY[spec_name.lower()]
    original = spec.func

    def func(ctx, x, *rest):
        if hasattr(x, "is_square") and hasattr(x, "analytic_func"):
            if not x.is_square:
                raise DomainError("Dimension error: square matrix required")
            t = sp.Dummy("t")
            try:
                result = x.analytic_func(scalar(ctx, t, *rest), t)
            except (ValueError, NotImplementedError, ZeroDivisionError) as exc:
                raise DomainError(f"Matrix function not defined: {exc}")
            return sp.ImmutableMatrix(result.applyfunc(sp.simplify))
        return original(ctx, x, *rest)

    spec.func = func
    spec.matrix_aware = True


for _name, _scalar in {
    "sin": lambda ctx, t: sp.sin(_to_radians(ctx, t)),
    "cos": lambda ctx, t: sp.cos(_to_radians(ctx, t)),
    "tan": lambda ctx, t: sp.tan(_to_radians(ctx, t)),
    "sin⁻¹": lambda ctx, t: _from_radians(ctx, sp.asin(t)),
    "cos⁻¹": lambda ctx, t: _from_radians(ctx, sp.acos(t)),
    "tan⁻¹": lambda ctx, t: _from_radians(ctx, sp.atan(t)),
    "sinh": lambda ctx, t: sp.sinh(t),
    "cosh": lambda ctx, t: sp.cosh(t),
    "tanh": lambda ctx, t: sp.tanh(t),
    "sinh⁻¹": lambda ctx, t: sp.asinh(t),
    "cosh⁻¹": lambda ctx, t: sp.acosh(t),
    "tanh⁻¹": lambda ctx, t: sp.atanh(t),
    "ln": lambda ctx, t: sp.log(t),
    "log": lambda ctx, t, base=10: sp.log(t, base),
    "√": lambda ctx, t: sp.sqrt(t),
    "exp": lambda ctx, t: sp.exp(t),
}.items():
    _matrix_function(_name, _scalar)
