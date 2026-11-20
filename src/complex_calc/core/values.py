"""Value types that are not plain SymPy expressions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import sympy as sp


class ListValue(list):
    """A list literal such as {1,2,3}."""


@dataclass
class UserFunction:
    """A function created with Define f(x)=... (or f(x):=...)."""

    name: str
    params: list[sp.Symbol]
    body: Any

    def call(self, args: list[Any]) -> Any:
        from .errors import ArgumentError

        if len(args) != len(self.params):
            raise ArgumentError(
                "Too few arguments" if len(args) < len(self.params) else "Too many arguments"
            )
        mapping = dict(zip(self.params, args))
        if isinstance(self.body, sp.Basic):
            return self.body.subs(mapping, simultaneous=True)
        return self.body


@dataclass
class SolveResult:
    """Result of solve/cSolve.

    `alternatives` is a list of solutions; each solution is a list of
    (variable, value) pairs joined by "and". Alternatives are joined by "or".
    `relational` is used instead for inequality solutions (already a list of
    preformatted pieces built from SymPy intervals).
    """

    alternatives: list[list[tuple[sp.Symbol, Any]]] = field(default_factory=list)
    intervals: list[tuple[sp.Symbol, sp.Interval]] | None = None
    always_true: bool = False
    general: list[tuple[sp.Symbol, Any]] = field(default_factory=list)  # periodic families


@dataclass
class StatResults:
    """Two-column result table like stat.results (zInterval, LinRegMx, ...)."""

    title: str
    rows: list[tuple[str, Any]]
    # Values stored as stat.<name> variables after the command ran.
    variables: dict[str, Any] = field(default_factory=dict)


@dataclass
class TextValue:
    """A plain text result: quoted ("m*x+b") or raw (Done, 0b101, 30°15'0″)."""

    text: str
    quoted: bool = True


class StringValue(str):
    """A string such as "hello"."""


@dataclass
class UserProgram:
    """Define name(params)=Func ... EndFunc  or  =Prgm ... EndPrgm."""

    name: str
    params: list[str]
    block: list[Any]
    kind: str  # "func" | "prgm"
    source: str = ""
    library: str | None = None  # library document the program belongs to


def is_matrix(value: Any) -> bool:
    return isinstance(value, sp.MatrixBase)
