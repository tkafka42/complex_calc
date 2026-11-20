"""Tokenizer for the calculator input language.

Accepts the special characters of the handheld (√ π ℯ ⅈ ∞ → ≤ ≥ ≠ ° ² ∫ Σ Π ►
∠ ᵀ ⇒ ⇔ x̄ σ μ ...) as well as the official keyboard shortcuts from the
reference guide ("Shortcuts for Entering Math Expressions"):

    pi → π      theta → θ     infinity → ∞     <= → ≤     >= → ≥     /= → ≠
    => → ⇒      <=> → ⇔       =: → →           @i → ⅈ     @e → ℯ     @E → ᴇ
    @t → ᵀ      @r → ʳ        @d → °           @g → ᵍ     @< → ∠     @> → ►
    @n1 → n1    @c1 → c1      sqrt( → √(       derivative( → d(   integral( → ∫(
    sumSeq( → Σ(   prodSeq( → Π(   deltaList( → ΔList(   arcsin( → sin⁻¹(
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from .errors import CalcSyntaxError

NUM = "NUM"
IDENT = "IDENT"
OP = "OP"
STR = "STR"
EOF = "EOF"

# Multi-character operators, longest first.
_MULTI_OPS = [
    ("<=>", "⇔"),
    (":=", ":="),
    ("=:", "→"),
    ("->", "→"),
    ("=>", "⇒"),
    ("<=", "≤"),
    (">=", "≥"),
    ("/=", "≠"),
    ("!=", "≠"),
    ("<>", "≠"),
    ("**", "^"),
    ("''", "″"),
    ("@>", "►"),
    ("@<", "∠"),
    ("@t", "ᵀ"),
    ("@r", "ʳ"),
    ("@d", "°"),
    ("@g", "ᵍ"),
]

_SINGLE_OPS = {
    "+": "+", "-": "-", "−": "-", "‐": "-", "⁻": "-",
    "*": "*", "·": "*", "•": "*", "×": "*",
    "/": "/", "÷": "/", "⁄": "/",
    "^": "^", "(": "(", ")": ")", "{": "{", "}": "}", "[": "[", "]": "]",
    ",": ",", ";": ";", "=": "=", "<": "<", ">": ">",
    "≤": "≤", "≥": "≥", "≠": "≠", "→": "→", "|": "|", "!": "!", "%": "%",
    "°": "°", ":": ":", "&": "&", "#": "#", "►": "►", "∠": "∠",
    "ᵀ": "ᵀ", "ʳ": "ʳ", "ᵍ": "ᵍ", "'": "'", "″": "″", "⇒": "⇒", "⇔": "⇔",
}

# Characters that become identifiers on their own.
_SYMBOL_IDENTS = {"π": "π", "ℯ": "ℯ", "ⅈ": "ⅈ", "∞": "∞", "√": "√", "∫": "∫"}
# Only when directly followed by "(": Σ( and Π( (otherwise they are letters, e.g. stat.Σx)
_CALL_SYMBOLS = {"Σ": "Σ", "Π": "Π", "∏": "Π", "∑": "Σ"}

_SUPERSCRIPTS = {"²": "2", "³": "3"}

_KEYBOARD_NAMES = {
    "sqrt": "√",
    "derivative": "d",
    "integral": "∫",
    "sumseq": "Σ",
    "prodseq": "Π",
    "deltalist": "ΔList",
    "deltatmpcnv": "ΔtmpCnv",
    "pi": "π",
    "theta": "θ",
    "infinity": "∞",
}


@dataclass
class Token:
    kind: str
    value: str
    pos: int
    space_before: bool = False

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
    return cat[0] in ("L", "M", "N") and ch not in _SUPERSCRIPTS and ch not in "⁻¹ᵀʳᵍ" \
        and ch not in _SYMBOL_IDENTS and ch not in "∑∏"


def tokenize(source: str) -> list[Token]:
    tokens: list[Token] = []
    i = 0
    n = len(source)
    space = False

    def add(kind: str, value: str, pos: int) -> None:
        nonlocal space
        tokens.append(Token(kind, value, pos, space))
        space = False

    while i < n:
        ch = source[i]
        if ch == "\n":  # a new line separates statements like ":"
            add(OP, ":", i)
            i += 1
            continue
        if ch == "©":  # comment until the end of the line
            while i < n and source[i] != "\n":
                i += 1
            continue
        if ch.isspace():
            space = True
            i += 1
            continue

        # strings "..." (also typographic quotes)
        if ch in "\"“”":
            start = i
            i += 1
            chars = []
            while i < n and source[i] not in "\"“”":
                chars.append(source[i])
                i += 1
            if i >= n:
                raise CalcSyntaxError('Missing closing "', start)
            i += 1
            add(STR, "".join(chars), start)
            continue

        # numbers: 12, 1.5, .5, 2E3, 1.2ᴇ-4, 2@E3, 0b101, 0hFF
        if ch.isdigit() or (ch == "." and i + 1 < n and source[i + 1].isdigit()):
            start = i
            if ch == "0" and i + 1 < n and source[i + 1] in "bBhH":
                j = i + 2
                digits = "01" if source[i + 1] in "bB" else "0123456789abcdefABCDEF"
                while j < n and source[j] in digits:
                    j += 1
                if j > i + 2:
                    base = 2 if source[i + 1] in "bB" else 16
                    add(NUM, str(int(source[i + 2:j], base)), start)
                    i = j
                    continue
            while i < n and source[i].isdigit():
                i += 1
            if i < n and source[i] == ".":
                i += 1
                while i < n and source[i].isdigit():
                    i += 1
            exp_marker = None
            if i < n and source[i] in ("E", "ᴇ"):
                exp_marker = 1
            elif source.startswith("@E", i):
                exp_marker = 2
            if exp_marker:
                j = i + exp_marker
                if j < n and source[j] in "+-−⁻":
                    j += 1
                if j < n and source[j].isdigit():
                    while j < n and source[j].isdigit():
                        j += 1
                    i = j
            text = source[start:i].replace("@E", "E").replace("ᴇ", "E").replace("−", "-").replace("⁻", "-")
            add(NUM, text, start)
            continue

        # @-shortcuts for constants: @i @e @n1 @c1
        if ch == "@":
            if source.startswith("@i", i) and not (i + 2 < n and _is_ident_part(source[i + 2])):
                add(IDENT, "ⅈ", i)
                i += 2
                continue
            if source.startswith("@e", i) and not (i + 2 < n and _is_ident_part(source[i + 2])):
                add(IDENT, "ℯ", i)
                i += 2
                continue
            if i + 2 < n and source[i + 1] in "nc" and source[i + 2].isdigit():
                j = i + 2
                while j < n and source[j].isdigit():
                    j += 1
                add(IDENT, source[i + 1:j], i)
                i = j
                continue

        # dot operators .+ .- .* ./ .^ (not after a digit, where "." is a decimal point)
        if ch == "." and i + 1 < n and source[i + 1] in "+-*/^•⁄" and not (i > 0 and source[i - 1].isdigit()):
            op = source[i + 1].replace("•", "*").replace("⁄", "/")
            add(OP, "." + op, i)
            i += 2
            continue

        matched = False
        for text, value in _MULTI_OPS:
            if source.startswith(text, i):
                if text.startswith("@") and i + len(text) < n and _is_ident_part(source[i + len(text)]) \
                        and text != "@>":
                    continue
                add(OP, value, i)
                i += len(text)
                matched = True
                break
        if matched:
            continue

        if ch in _SUPERSCRIPTS:
            add(OP, "^", i)
            add(NUM, _SUPERSCRIPTS[ch], i)
            i += 1
            continue

        if source.startswith("⁻¹", i):  # A⁻¹ (reciprocal / inverse)
            add(OP, "^", i)
            add(OP, "-", i)
            add(NUM, "1", i)
            i += 2
            continue

        if ch in _SYMBOL_IDENTS:
            add(IDENT, _SYMBOL_IDENTS[ch], i)
            i += 1
            continue

        if ch in _CALL_SYMBOLS:
            j = i + 1
            while j < n and source[j].isspace():
                j += 1
            if j < n and source[j] == "(":
                add(IDENT, _CALL_SYMBOLS[ch], i)
                i += 1
                continue

        if ch == "?":  # placeholder in countIf/sumIf criteria
            add(IDENT, "?", i)
            i += 1
            continue

        if ch in _SINGLE_OPS:
            add(OP, _SINGLE_OPS[ch], i)
            i += 1
            continue

        if _is_ident_start(ch) or ch in _CALL_SYMBOLS:
            start = i
            i += 1
            while i < n:
                c = source[i]
                if _is_ident_part(c):
                    i += 1
                elif c == "." and i + 1 < n and _is_ident_start(source[i + 1]):
                    i += 1  # dotted names such as stat.RegEqn
                elif c == "\\" and i + 1 < n and _is_ident_start(source[i + 1]):
                    i += 1  # library objects such as linalg\\gauss
                elif c == "°" and source[i - 1] == "_":  # temperature units _°C
                    i += 1
                elif c == "χ" or (source[i - 1] == "χ" and c in "²2"):
                    i += 1
                else:
                    break
            if source[i - 1] == "χ" and source.startswith("²", i):  # χ²Pdf, χ²Cdf
                i += 1
                while i < n and _is_ident_part(source[i]):
                    i += 1
            name = source[start:i]
            # exp►list, list►mat, mat►list, freqTable►list (keyboard: exp@>list)
            for arrow in ("►", "@>"):
                rest = source[i + len(arrow):]
                polar = name in ("P", "R") and rest[:2] in ("Rx", "Ry", "Pr", "Pθ") or \
                    (name == "R" and rest.startswith("Ptheta"))
                if (name.lower() in ("exp", "list", "mat", "freqtable") or polar) and source.startswith(arrow, i) \
                        and i + len(arrow) < n and _is_ident_start(source[i + len(arrow)]):
                    j = i + len(arrow)
                    while j < n and _is_ident_part(source[j]):
                        j += 1
                    name = name + "►" + source[i + len(arrow):j]
                    i = j
                    break
            if source.startswith("⁻¹", i):  # sin⁻¹ etc.
                name += "⁻¹"
                i += 2
            elif source.startswith("-1(", i) and name.lower() in _INVERSE_CAPABLE:
                name += "⁻¹"  # sin-1( as written in the reference guide
                i += 2
            name = _KEYBOARD_NAMES.get(name.lower(), name)
            add(IDENT, name, start)
            continue

        raise CalcSyntaxError(f"Unexpected character '{ch}'", i)

    tokens.append(Token(EOF, "", n, space))
    return tokens


_INVERSE_CAPABLE = {"sin", "cos", "tan", "sec", "csc", "cot", "sinh", "cosh", "tanh", "sech", "csch", "coth"}
