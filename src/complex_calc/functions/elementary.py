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
