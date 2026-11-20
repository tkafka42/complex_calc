"""Units (names starting with "_"), physical constants and temperature conversion.

    3_m►_ft         5_km/_h►_m/_s        _c          tmpCnv(100_°C,_°F)
"""

from __future__ import annotations

from typing import Any

import sympy as sp

from ..core.errors import ArgumentError
from ..core.values import ListValue
from .registry import builtin

_BASE = {name: sp.Symbol(name) for name in ("_m", "_kg", "_s", "_A", "_K", "_mol", "_cd")}
m, kg, s, A, K, mol, cd = (_BASE[n] for n in ("_m", "_kg", "_s", "_A", "_K", "_mol", "_cd"))
N = kg * m / s**2
J = N * m
W = J / s
Pa = N / m**2
C = A * s
V = W / A
ohm = V / A

UNITS: dict[str, sp.Expr] = {
    # length
    "_m": m, "_km": 1000 * m, "_cm": m / 100, "_mm": m / 1000, "_μm": m / 10**6, "_nm": m / 10**9,
    "_Ang": m / 10**10, "_ft": sp.Rational(3048, 10000) * m, "_in": sp.Rational(254, 10000) * m,
    "_yd": sp.Rational(9144, 10000) * m, "_mi": sp.Rational(1609344, 1000) * m,
    "_nmi": 1852 * m, "_ltyr": sp.Rational(9460730472580800) * m, "_au": 149597870700 * m,
    # area / volume
    "_acre": sp.Rational(40468564224, 10**7) * m**2, "_ha": 10000 * m**2,
    "_l": m**3 / 1000, "_ml": m**3 / 10**6, "_gal": sp.Rational(3785411784, 10**12) * m**3,
    # time
    "_s": s, "_ms": s / 1000, "_μs": s / 10**6, "_ns": s / 10**9, "_min": 60 * s, "_hr": 3600 * s,
    "_h": 3600 * s, "_day": 86400 * s, "_week": 604800 * s, "_yr": sp.Rational(31556925974678, 10**6) * s,
    # mass
    "_kg": kg, "_g": kg / 1000, "_mg": kg / 10**6, "_mton": 1000 * kg, "_lb": sp.Rational(45359237, 10**8) * kg,
    "_oz": sp.Rational(45359237, 16 * 10**8) * kg, "_ton": 2000 * sp.Rational(45359237, 10**8) * kg,
    # speed
    "_knot": sp.Rational(1852, 3600) * m / s, "_mph": sp.Rational(1609344, 3600000) * m / s,
    "_kph": sp.Rational(1000, 3600) * m / s,
    # force / energy / power / pressure
    "_N": N, "_kN": 1000 * N, "_dyne": N / 10**5, "_lbf": sp.Rational(44482216152605, 10**13) * N,
    "_J": J, "_kJ": 1000 * J, "_cal": sp.Rational(4184, 1000) * J, "_kcal": 4184 * J,
    "_eV": sp.Rational(1602176634, 10**28) * J, "_Wh": 3600 * J, "_kWh": 3600000 * J,
    "_W": W, "_kW": 1000 * W, "_MW": 10**6 * W, "_hp": sp.Rational(7456998715822702, 10**13) * W,
    "_Pa": Pa, "_kPa": 1000 * Pa, "_bar": 10**5 * Pa, "_atm": 101325 * Pa, "_mmHg": sp.Rational(101325, 760) * Pa,
    "_psi": sp.Rational(689475729316836, 10**11) * Pa,
    # electricity
    "_A": A, "_mA": A / 1000, "_coul": C, "_V": V, "_mV": V / 1000, "_kV": 1000 * V, "_ohm": ohm,
    "_Ω": ohm, "_F": C / V, "_H": V * s / A, "_T": V * s / m**2, "_Wb": V * s, "_S": 1 / ohm,
    # other base units
    "_K": K, "_°K": K, "_mol": mol, "_cd": cd,
}

CONSTANTS: dict[str, sp.Expr] = {
    "_c": 299792458 * m / s,
    "_Cc": sp.Float("8987551792.261") * m / (C / V),
    "_Fc": sp.Float("96485.33212") * C / mol,
    "_g": sp.Float("9.80665") * m / s**2,
    "_Gc": sp.Float("6.6743E-11") * m**3 / kg / s**2,
    "_h": sp.Float("6.62607015E-34") * J * s,
    "_k": sp.Float("1.380649E-23") * J / K,
    "_m0": sp.Float("1.25663706127E-6") * N / A**2,
    "_mb": sp.Float("9.274009994E-24") * J * m**2 / (V * s),
    "_Me": sp.Float("9.10938371390E-31") * kg,
    "_Mm": sp.Float("1.883531627E-28") * kg,
    "_Mn": sp.Float("1.67492750058E-27") * kg,
    "_Mp": sp.Float("1.67262192595E-27") * kg,
    "_Na": sp.Float("6.02214076E23") / mol,
    "_q": sp.Float("1.602176634E-19") * C,
    "_Rb": sp.Float("5.29177210544E-11") * m,
    "_Rc": sp.Float("8.314462618") * J / mol / K,
    "_Rdb": sp.Float("10973731.568157") / m,
    "_Vm": sp.Float("0.022413969545") * m**3 / mol,
    "_ε0": sp.Float("8.8541878188E-12") * C / V / m,
    "_σ": sp.Float("5.670374419E-8") * W / m**2 / K**4,
    "_φ0": sp.Float("2.067833848E-15") * V * s,
}

# lower-case lookup (names are case-insensitive except where they would collide)
_LOOKUP = {**{k: v for k, v in UNITS.items()}, **CONSTANTS}
_LOWER = {k.lower(): k for k in _LOOKUP}


def unit_value(name: str) -> sp.Expr | None:
    """Value of _unit or _constant in SI base units, or None."""
    if name in CONSTANTS:
        return CONSTANTS[name]
    if name in UNITS:
        return sp.Symbol(name)  # keep the unit symbol until conversion
    real = _LOWER.get(name.lower())
    if real is None:
        return None
    return CONSTANTS.get(real, sp.Symbol(real) if real in UNITS else None)


def to_base(expr: Any) -> Any:
    mapping = {sp.Symbol(name): value for name, value in UNITS.items()}
    return sp.sympify(expr).subs(mapping)


def convert_units(ctx, value: Any, target_expr: Any) -> Any:
    if isinstance(value, ListValue):
        return ListValue(convert_units(ctx, v, target_expr) for v in value)
    ratio = sp.simplify(to_base(value) / to_base(target_expr))
    if ratio.free_symbols & set(_BASE.values()):
        raise ArgumentError("Incompatible units")
    return sp.Mul(ratio.evalf(15), target_expr, evaluate=False)


_TEMPS = {"_°c": "C", "_°f": "F", "_°k": "K", "_°r": "R", "_k": "K"}


def _temp_unit(expr: Any) -> tuple[Any, str]:
    for sym in sp.sympify(expr).free_symbols:
        kind = _TEMPS.get(sym.name.lower())
        if kind:
            return sp.sympify(expr).subs(sym, 1), kind
    raise ArgumentError("Temperature unit expected, e.g. 100_°C")


def _to_kelvin(value, kind, delta=False):
    if kind == "K":
        return value
    if kind == "C":
        return value if delta else value + sp.Rational(27315, 100)
    if kind == "F":
        return value * sp.Rational(5, 9) if delta else (value + sp.Rational(45967, 100)) * sp.Rational(5, 9)
    return value * sp.Rational(5, 9)  # Rankine


def _from_kelvin(value, kind, delta=False):
    if kind == "K":
        return value
    if kind == "C":
        return value if delta else value - sp.Rational(27315, 100)
    if kind == "F":
        return value * sp.Rational(9, 5) if delta else value * sp.Rational(9, 5) - sp.Rational(45967, 100)
    return value * sp.Rational(9, 5)


@builtin("tmpCnv", "tmpCnv(Expr_°tempUnit, _°tempUnit2)", 2, summary="Convert a temperature")
def tmp_cnv(ctx, value, unit):
    number, source = _temp_unit(value)
    _, target = _temp_unit(unit)
    return sp.Mul(_from_kelvin(_to_kelvin(number, source), target), unit, evaluate=False)


@builtin("ΔtmpCnv", "ΔtmpCnv(Expr_°tempUnit, _°tempUnit2)", 2, summary="Convert a temperature difference")
def delta_tmp_cnv(ctx, value, unit):
    number, source = _temp_unit(value)
    _, target = _temp_unit(unit)
    return sp.Mul(_from_kelvin(_to_kelvin(number, source, True), target, True), unit, evaluate=False)
