"""Conversion operator ► (keyboard: @>), e.g. 1/3►Decimal, 25►Base2, 30.5►DMS.

Targets: Decimal, approxFraction([Tol]), Base2, Base10, Base16, DMS, DD, Rad,
Grad, Polar, Rect, Cylind, Sphere, exp, ln, sin, cos, logbase(b), and unit
conversions (3_m►_ft).
"""

from __future__ import annotations

from typing import Any

import sympy as sp

from ..core.errors import ArgumentError, DomainError
from ..core.values import ListValue, TextValue, is_matrix


def simplest_fraction(value: Any, tol: float) -> Any:
    """Fraction with the smallest denominator within tol (continued fractions)."""
    from fractions import Fraction

    if isinstance(value, sp.Rational):
        return value
    if not isinstance(value, sp.Expr) or not value.is_number or not value.is_real:
        return value
    exact = Fraction(sp.N(value, 15).__format__(".15g")) if isinstance(value, sp.Float) else \
        Fraction(str(sp.N(value, 17)))
    sign = -1 if exact < 0 else 1
    x = abs(exact)
    limit = Fraction(tol) * max(1, x)
    h0, h1, k0, k1 = 0, 1, 1, 0
    rest = x
    for _ in range(100):
        a = rest.numerator // rest.denominator
        h0, h1 = h1, a * h1 + h0
        k0, k1 = k1, a * k1 + k0
        if abs(x - Fraction(h1, k1)) <= limit or rest == a:
            break
        rest = 1 / (rest - a)
    return sp.Rational(sign * h1, k1)


def _map(value: Any, func):
    if isinstance(value, ListValue):
        return ListValue(_map(v, func) for v in value)
    if is_matrix(value):
        return value.applyfunc(func)
    return func(value)


def _degrees_per_unit(ctx) -> sp.Expr:
    return {"deg": sp.Integer(1), "rad": 180 / sp.pi, "grad": sp.Rational(9, 10)}[ctx.settings.angle]


def _base(value: Any, base: int) -> Any:
    if not (isinstance(value, sp.Integer) or (isinstance(value, sp.Expr) and value.is_integer)):
        raise DomainError("Base conversion needs an integer")
    n = int(value)
    if base == 10:
        return sp.Integer(n)
    if n < 0:  # two's complement, 64 bit
        n &= (1 << 64) - 1
    digits = format(n, "b" if base == 2 else "X")
    return TextValue(("0b" if base == 2 else "0h") + digits, quoted=False)


def _dms(ctx, value: Any) -> TextValue:
    degrees = float(sp.N(value * _degrees_per_unit(ctx)))
    sign = "-" if degrees < 0 else ""
    degrees = abs(degrees)
    d = int(degrees)
    minutes_total = (degrees - d) * 60
    m = int(minutes_total)
    s = round((minutes_total - m) * 60, 6)
    if s >= 60:
        s -= 60
        m += 1
    if m >= 60:
        m -= 60
        d += 1
    s_text = f"{s:.6g}"
    return TextValue(f"{sign}{d}°{m}'{s_text}″", quoted=False)


def _polar(ctx, value: Any) -> Any:
    if is_matrix(value):
        if len(value) != 2:
            raise ArgumentError("►Polar needs a vector of dimension 2")
        x, y = value[0], value[1]
        r = sp.sqrt(x**2 + y**2)
        theta = sp.atan2(y, x) * _degrees_per_unit(ctx) * (sp.pi / 180 if ctx.settings.angle == "rad" else 1)
        if ctx.settings.angle == "rad":
            theta = sp.atan2(y, x)
        from ..core.formatting import format_expr
        d = ctx.settings.digits
        return TextValue(f"[{format_expr(sp.simplify(r), d)},∠{format_expr(sp.simplify(theta), d)}]", quoted=False)
    if isinstance(value, sp.Expr) and value.is_number:
        r = sp.Abs(value)
        theta = sp.arg(value)
        if ctx.settings.angle != "rad":
            theta = theta * _degrees_per_unit(ctx)
        from ..core.formatting import format_expr
        d = ctx.settings.digits
        return TextValue(f"({format_expr(sp.simplify(r), d)}∠{format_expr(sp.simplify(theta), d)})", quoted=False)
    raise ArgumentError("►Polar needs a complex number or a 2-element vector")


def _rect(ctx, value: Any) -> Any:
    if isinstance(value, sp.Expr):
        return sp.expand_complex(value)
    if is_matrix(value):
        return value
    raise ArgumentError("►Rect needs a complex number or vector")


def convert(ctx, value: Any, target: str, args: list[Any]) -> Any:
    key = target.lower()
    if key == "decimal":
        return _map(value, lambda v: v.evalf(15, chop=True) if isinstance(v, sp.Basic) else v)
    if key == "approxfraction":
        tol = float(args[0]) if args else 5e-14
        return _map(value, lambda v: simplest_fraction(v, tol))
    if key == "base2":
        return _map(value, lambda v: _base(v, 2))
    if key == "base10":
        return _map(value, lambda v: _base(v, 10))
    if key == "base16":
        return _map(value, lambda v: _base(v, 16))
    if key == "dms":
        return _map(value, lambda v: _dms(ctx, v))
    if key == "dd":
        return _map(value, lambda v: (v * _degrees_per_unit(ctx)).evalf(15))
    if key == "rad":
        return _map(value, lambda v: (v * _degrees_per_unit(ctx) * sp.pi / 180).evalf(15))
    if key == "grad":
        return _map(value, lambda v: (v * _degrees_per_unit(ctx) * sp.Rational(10, 9)).evalf(15))
    if key == "polar":
        return _polar(ctx, value)
    if key == "rect":
        return _rect(ctx, value)
    if key in ("cylind", "sphere"):
        if not is_matrix(value) or len(value) != 3:
            raise ArgumentError(f"►{target} needs a 3-element vector")
        x, y, z = value
        r_xy = sp.sqrt(x**2 + y**2)
        from ..core.formatting import format_expr
        d = ctx.settings.digits
        theta = sp.atan2(y, x) if ctx.settings.angle == "rad" else sp.atan2(y, x) * _degrees_per_unit(ctx)
        if key == "cylind":
            return TextValue(f"[{format_expr(r_xy, d)},∠{format_expr(theta, d)},{format_expr(z, d)}]", quoted=False)
        rho = sp.sqrt(x**2 + y**2 + z**2)
        phi = sp.atan2(r_xy, z) if ctx.settings.angle == "rad" else sp.atan2(r_xy, z) * _degrees_per_unit(ctx)
        return TextValue(f"[{format_expr(rho, d)},∠{format_expr(theta, d)},∠{format_expr(phi, d)}]", quoted=False)
    if key == "exp":
        return _map(value, lambda v: sp.simplify(v.rewrite(sp.exp)))
    if key == "ln":
        return _map(value, lambda v: sp.expand_log(sp.logcombine(v.rewrite(sp.log), force=True), force=True))
    if key == "sin":
        return _map(value, lambda v: sp.simplify(v.rewrite(sp.sin)))
    if key == "cos":
        return _map(value, lambda v: sp.simplify(v.rewrite(sp.cos)))
    if key == "logbase":
        if not args:
            raise ArgumentError("►logbase needs a base, e.g. ►logbase(10)")
        base = args[0]
        return _map(value, lambda v: sp.Mul(sp.log(v) / sp.log(base), evaluate=True))
    raise ArgumentError(f"Unknown conversion ►{target}")
