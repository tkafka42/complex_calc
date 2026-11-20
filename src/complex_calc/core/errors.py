"""Error types with user-facing messages.

Message texts follow the style of handheld CAS calculators
("Syntax error", "Too few arguments", "Domain error", ...) so that
the feedback feels familiar while practising.
"""

from __future__ import annotations


class CalcError(Exception):
    """Base class for all errors shown to the user."""

    kind = "Error"

    def __init__(self, message: str, position: int | None = None):
        super().__init__(message)
        self.message = message
        self.position = position

    def user_message(self, source: str | None = None) -> str:
        text = f"{self.kind}: {self.message}"
        if source is not None and self.position is not None:
            pointer = " " * min(self.position, len(source)) + "^"
            text += f"\n  {source}\n  {pointer}"
        return text


class CalcSyntaxError(CalcError):
    kind = "Syntax error"


class ArgumentError(CalcError):
    kind = "Argument error"


class DomainError(CalcError):
    kind = "Domain error"


class UndefinedError(CalcError):
    kind = "Undefined"


class EvaluationError(CalcError):
    kind = "Error"
