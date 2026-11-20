"""Central registry of built-in functions and commands.

Lookup is case-insensitive, like on the handheld (NORMCDF == normCdf).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

import sympy as sp

from ..core.errors import ArgumentError, DomainError
from ..core.values import ListValue


class Settings(Protocol):  # pragma: no cover - typing only
    angle: str  # "rad" | "deg"
    mode: str  # "auto" | "exact" | "approx"
    digits: int


@dataclass
class Context:
    settings: Any
    store: Callable[[str, Any], None]
    lookup: Callable[[str], Any]
    session: Any = None
    evaluator: Any = None


@dataclass
class Builtin:
    name: str  # canonical spelling shown in help and menus
    func: Callable[..., Any]
    min_args: int
    max_args: int | None
    signature: str  # e.g. "normCdf(lowBound,upBound[,μ[,σ]])"
    hold: tuple[int, ...] = ()  # argument positions that name variables
    command: bool = False  # called without parentheses: zInterval 15,100,25
    approx: bool = False  # result is always numeric
    listable: tuple[int, ...] = ()  # applied element-wise when a list is passed
    aliases: tuple[str, ...] = ()
    summary: str = ""
    exact: bool = False  # result is exact even if the input contained decimals
    raw: tuple[int, ...] = ()  # argument positions passed unevaluated (AST nodes)
    complex: bool = False  # complex results allowed in Real mode (cSolve, cZeros, ...)
    matrix_aware: bool = False  # receives matrices itself instead of element-wise mapping


REGISTRY: dict[str, Builtin] = {}


def builtin(
    name: str,
    signature: str,
    min_args: int,
    max_args: int | None = None,
    *,
    aliases: tuple[str, ...] = (),
    hold: tuple[int, ...] = (),
    command: bool = False,
    approx: bool = False,
    listable: tuple[int, ...] = (),
    summary: str = "",
    exact: bool = False,
    raw: tuple[int, ...] = (),
    complex: bool = False,
    matrix_aware: bool = False,
):
    """Decorator registering `func(ctx, *args)` as a built-in."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        spec = Builtin(
            name=name,
            func=func,
            min_args=min_args,
            max_args=min_args if max_args is None else max_args,
            signature=signature,
            hold=hold,
            command=command,
            approx=approx,
            listable=listable,
            aliases=aliases,
            summary=summary,
            exact=exact,
            raw=raw,
            complex=complex,
            matrix_aware=matrix_aware,
        )
        for key in (name, *aliases):
            REGISTRY[key.lower()] = spec
        return func

    return decorator


def lookup_builtin(name: str) -> Builtin | None:
    return REGISTRY.get(name.lower())


def canonical_names() -> list[str]:
    seen: dict[str, None] = {}
    for spec in REGISTRY.values():
        seen.setdefault(spec.name, None)
    return sorted(seen, key=str.lower)


# ------------------------------------------------------------------ helpers


def to_float(value: Any, label: str) -> float:
    """Convert an argument to a real float (∞ allowed)."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, sp.Basic):
        if value == sp.oo:
            return math.inf
        if value == -sp.oo:
            return -math.inf
        try:
            number = sp.N(value, 17)
        except (TypeError, ValueError):
            number = None
        if number is not None and number.is_number:
            re_part, im_part = number.as_real_imag()
            if abs(float(im_part)) < 1e-12:
                return float(re_part)
            raise DomainError(f"{label} must be a real number")
    raise ArgumentError(f"{label} must be a number")


def to_int(value: Any, label: str) -> int:
    number = to_float(value, label)
    if math.isinf(number):
        return int(math.copysign(10**18, number))
    if abs(number - round(number)) > 1e-9:
        raise DomainError(f"{label} must be an integer")
    return int(round(number))


def to_list(value: Any, label: str) -> list[Any]:
    if isinstance(value, ListValue):
        return list(value)
    raise ArgumentError(f"{label} must be a list, e.g. {{1,2,3}}")


def to_float_list(value: Any, label: str) -> list[float]:
    return [to_float(item, f"element of {label}") for item in to_list(value, label)]


def check_probability(p: float, label: str = "p") -> None:
    if not 0 <= p <= 1:
        raise DomainError(f"{label} must be between 0 and 1")


def check_positive(x: float, label: str) -> None:
    if not x > 0:
        raise DomainError(f"{label} must be > 0")
