"""Tokenizer for the calculator input language.

Accepts both the special characters of handheld CAS calculators
(√ π ℯ ⅈ ∞ → ≤ ≥ ≠ ° ² ∫ x̄ σ μ ...) and plain-keyboard alternatives
(sqrt pi e i infinity -> =: <= >= /= ...).
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from .errors import CalcSyntaxError

NUM = "NUM"
IDENT = "IDENT"
OP = "OP"
EOF = "EOF"

# Multi-character operators, longest first.
_MULTI_OPS = [
    (":=", ":="),
    ("=:", "→"),
    ("->", "→"),
    ("=>", "→"),
    ("<=", "≤"),
    (">=", "≥"),
    ("/=", "≠"),
    ("!=", "≠"),
    ("<>", "≠"),
    ("**", "^"),
]

_SINGLE_OPS = {
    "+": "+",
    "-": "-",
    "−": "-",  # unicode minus
    "‐": "-",
    "*": "*",
    "·": "*",
    "×": "*",
    "/": "/",
    "÷": "/",
    "^": "^",
    "(": "(",
    ")": ")",
    "{": "{",
    "}": "}",
    "[": "[",
    "]": "]",
    ",": ",",
    "=": "=",
    "<": "<",
    ">": ">",
    "≤": "≤",
    "≥": "≥",
    "≠": "≠",
    "→": "→",
    "|": "|",
    "!": "!",
    "°": "°",
    ":": ":",
}

# Characters that are turned into identifiers on their own.
_SYMBOL_IDENTS = {
    "π": "π",
    "ℯ": "ℯ",
    "ⅈ": "ⅈ",
    "∞": "∞",
    "√": "√",
    "∫": "∫",
    "Σ": "Σ",
}

_SUPERSCRIPTS = {"²": "2", "³": "3"}


@dataclass
class Token:
    kind: str
    value: str
    pos: int

    def is_op(self, *values: str) -> bool:
        return self.kind == OP and self.value in values

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Token({self.kind},{self.value!r}@{self.pos})"


def _is_ident_start(ch: str) -> bool:
    return ch == "_" or unicodedata.category(ch).startswith("L")


def _is_ident_part(ch: str) -> bool:
    if ch == "_":
        return True
    cat = unicodedata.category(ch)
    return cat[0] in ("L", "M", "N") and ch not in _SUPERSCRIPTS and ch not in "⁻¹"


def tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    n = len(source)
    while i < n:
        ch = source[i]
        if ch.isspace():
            i += 1
            continue

        # Numbers: 12, 1.5, .5, 2E3, 1.2ᴇ-4
        if ch.isdigit() or (ch == "." and i + 1 < n and source[i + 1].isdigit()):
            start = i
            while i < n and source[i].isdigit():
                i += 1
            if i < n and source[i] == ".":
                i += 1
                while i < n and source[i].isdigit():
                    i += 1
            if i < n and source[i] in ("E", "ᴇ"):
                j = i + 1
                if j < n and source[j] in "+-−":
                    j += 1
                if j < n and source[j].isdigit():
                    while j < n and source[j].isdigit():
                        j += 1
                    i = j
            text = source[start:i].replace("ᴇ", "E").replace("−", "-")
            tokens.append(Token(NUM, text, start))
            continue

        # Multi-character operators
        matched = False
        for text, value in _MULTI_OPS:
            if source.startswith(text, i):
                tokens.append(Token(OP, value, i))
                i += len(text)
                matched = True
                break
        if matched:
            continue

        if ch in _SUPERSCRIPTS:
            tokens.append(Token(OP, "^", i))
            tokens.append(Token(NUM, _SUPERSCRIPTS[ch], i))
            i += 1
            continue

        if ch in _SYMBOL_IDENTS:
            tokens.append(Token(IDENT, _SYMBOL_IDENTS[ch], i))
            i += 1
            continue

        if ch in _SINGLE_OPS:
            tokens.append(Token(OP, _SINGLE_OPS[ch], i))
            i += 1
            continue

        if ch == "@" and source.startswith("@i", i):
            tokens.append(Token(IDENT, "ⅈ", i))
            i += 2
            continue

        if _is_ident_start(ch):
            start = i
            i += 1
            while i < n:
                c = source[i]
                if _is_ident_part(c):
                    i += 1
                elif c == "." and i + 1 < n and _is_ident_start(source[i + 1]):
                    i += 1  # dotted names such as stat.RegEqn
                else:
                    break
            if source[i - 1] == "χ" and source.startswith("²", i):  # χ²Pdf, χ²Cdf
                i += 1
                while i < n and _is_ident_part(source[i]):
                    i += 1
            name = source[start:i]
            if source.startswith("⁻¹", i):  # sin⁻¹ etc.
                name += "⁻¹"
                i += 2
            tokens.append(Token(IDENT, name, start))
            continue

        raise CalcSyntaxError(f"Unexpected character '{ch}'", i)

    tokens.append(Token(EOF, "", n))
    return tokens
