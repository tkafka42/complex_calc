"""Recursive-descent parser following the EOS™ order of evaluation of the
reference guide (lowest priority first):

    18 store →            (statement level)
       conversion ►       (applied to the whole expression)
    17 constraint |
    16 ⇔ (xnor)
    15 ⇒
    14 xor, nor, nand
    13 or
    12 and
    11 not
    10 = ≠ < ≤ > ≥
     9 + - .+ .-
     8 * / .* ./  and implied multiplication
     7 & (string concatenation)
     6 negation
     5 ^ .^ (right to left)
     4 post operators: ° ' ″ ! % ʳ ᵍ ᵀ and subscripts [ ]
     3 function calls
     2 indirection #
     1 ( ) [ ] { }

Statements (separated by ":" or new lines) include TI-Basic control
structures for programs and functions: If/Then/ElseIf/Else/EndIf, For,
While, Loop, Try, Return, Exit, Cycle, Stop, Local, Lbl, Goto,
Define ... Func ... EndFunc / Prgm ... EndPrgm.

Note (reference guide): a name followed by "(" is a function call, not
implied multiplication: a(b+c) calls a. Write a*(b+c) to multiply.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .errors import CalcSyntaxError
from .tokenizer import EOF, IDENT, NUM, OP, STR, Token, tokenize

# ---------------------------------------------------------------- AST nodes


@dataclass
class Node:
    pos: int = field(default=0, kw_only=True)


@dataclass
class Num(Node):
    text: str


@dataclass
class Str(Node):
    text: str


@dataclass
class Name(Node):
    name: str


@dataclass
class Call(Node):
    name: str
    args: list[Node]


@dataclass
class BinOp(Node):
    op: str  # + - * / ^ & .+ .- .* ./ .^
    left: Node
    right: Node


@dataclass
class Neg(Node):
    operand: Node


@dataclass
class Postfix(Node):
    op: str  # ! % ° ' ″ ʳ ᵍ ᵀ
    operand: Node


@dataclass
class Subscript(Node):
    operand: Node
    indices: list[Node]


@dataclass
class Indirection(Node):
    operand: Node


@dataclass
class Relation(Node):
    op: str  # = ≠ < > ≤ ≥
    left: Node
    right: Node


@dataclass
class Logic(Node):
    op: str  # and / or / xor / nor / nand / ⇒ / ⇔
    items: list[Node]


@dataclass
class Not(Node):
    operand: Node


@dataclass
class With(Node):
    expr: Node
    condition: Node


@dataclass
class Convert(Node):
    operand: Node
    target: str
    args: list[Node]
    target_node: Node | None = None  # unit expression such as _m/_s


@dataclass
class Polar(Node):  # (r∠θ)
    magnitude: Node
    angle: Node


@dataclass
class Void(Node):
    """An omitted optional argument, e.g. amortTbl(12,60,10,5000,,,12,12)."""


@dataclass
class ListLit(Node):
    items: list[Node]


@dataclass
class MatrixLit(Node):
    rows: list[list[Node]]


# ---------------------------------------------------------------- statements


@dataclass
class ExprStmt(Node):
    expr: Node
    store_to: Node | None = None  # Name or Subscript


@dataclass
class DefineStmt(Node):
    name: str
    params: list[str] | None  # None for a plain variable
    body: Node | None
    show_value: bool = False  # "a:=5" shows 5, "Define a=5" shows Done
    block: list[Node] | None = None  # Func/Prgm body
    kind: str = "expr"  # "expr" | "func" | "prgm"
    library: str | None = None  # "LibPub" | "LibPriv"


@dataclass
class DelVarStmt(Node):
    names: list[str]


@dataclass
class CopyVarStmt(Node):
    source: str
    target: str


@dataclass
class CommandStmt(Node):
    name: str
    args: list[Node]


@dataclass
class IfStmt(Node):
    branches: list[tuple[Node, list[Node]]]
    else_block: list[Node] | None = None


@dataclass
class ForStmt(Node):
    var: str
    start: Node
    end: Node
    step: Node | None
    body: list[Node]


@dataclass
class WhileStmt(Node):
    condition: Node
    body: list[Node]


@dataclass
class LoopStmt(Node):
    body: list[Node]


@dataclass
class TryStmt(Node):
    body: list[Node]
    handler: list[Node] | None


@dataclass
class ReturnStmt(Node):
    value: Node | None


@dataclass
class SimpleStmt(Node):
    word: str  # exit / cycle / stop / clrerr / passerr


@dataclass
class LocalStmt(Node):
    names: list[str]


@dataclass
class LblStmt(Node):
    label: str


@dataclass
class GotoStmt(Node):
    label: str


LOGIC_WORDS = {"and", "or", "xor", "not", "nor", "nand"}
BLOCK_WORDS = {
    "then", "else", "elseif", "endif", "endfor", "endwhile", "endloop", "endtry",
    "endfunc", "endprgm", "func", "prgm",
}
KEYWORDS = LOGIC_WORDS | BLOCK_WORDS
STATEMENT_WORDS = {"if", "for", "while", "loop", "try", "return", "exit", "cycle", "stop", "local",
                   "lbl", "goto", "clrerr", "passerr", "define", "delvar", "copyvar"}


class Parser:
    def __init__(
        self,
        source: str,
        is_function: Callable[[str], bool],
        is_command: Callable[[str], bool],
    ):
        self.source = source
        self.tokens = tokenize(source)
        self.index = 0
        self.is_function = is_function
        self.is_command = is_command

    # ------------------------------------------------------------ helpers
    @property
    def tok(self) -> Token:
        return self.tokens[self.index]

    def peek(self, offset: int = 1) -> Token:
        return self.tokens[min(self.index + offset, len(self.tokens) - 1)]

    def advance(self) -> Token:
        token = self.tokens[self.index]
        if token.kind != EOF:
            self.index += 1
        return token

    def expect_op(self, value: str) -> Token:
        if not self.tok.is_op(value):
            found = self.tok.value or "end of input"
            raise CalcSyntaxError(f"Missing {value}" if self.tok.kind == EOF else
                                  f"Expected '{value}' but found '{found}'", self.tok.pos)
        return self.advance()

    def expect_name(self) -> Token:
        if self.tok.kind != IDENT or self.tok.value.lower() in KEYWORDS:
            raise CalcSyntaxError("Variable name expected", self.tok.pos)
        return self.advance()

    def word(self, token: Token | None = None) -> str:
        token = token or self.tok
        return token.value.lower() if token.kind == IDENT else ""

    def expect_word(self, word: str) -> Token:
        if self.word() != word:
            raise CalcSyntaxError(f"Expected {word.capitalize()}", self.tok.pos)
        return self.advance()

    def at_statement_end(self) -> bool:
        return self.tok.kind == EOF or self.tok.is_op(":")

    def skip_separators(self) -> None:
        while self.tok.is_op(":"):
            self.advance()

    # ------------------------------------------------------------ program
    def parse_program(self) -> list[Node]:
        statements = self.parse_block(set())
        if self.tok.kind != EOF:
            raise CalcSyntaxError(f"{self.tok.value} invalid outside of a block", self.tok.pos)
        if not statements:
            raise CalcSyntaxError("Empty input", 0)
        return statements

    def parse_block(self, terminators: set[str]) -> list[Node]:
        statements: list[Node] = []
        while True:
            self.skip_separators()
            if self.tok.kind == EOF or self.word() in terminators:
                return statements
            if self.word() in BLOCK_WORDS:
                raise CalcSyntaxError(f"{self.tok.value} invalid outside of its block", self.tok.pos)
            statements.append(self.parse_statement())
            if not self.at_statement_end() and self.word() not in terminators:
                raise CalcSyntaxError(f"Unexpected '{self.tok.value}'", self.tok.pos)

    def parse_statement(self) -> Node:
        tok = self.tok
        word = self.word()
        if tok.kind == IDENT:
            handler = getattr(self, f"stmt_{word}", None)
            if handler is not None and word in STATEMENT_WORDS:
                return handler()
            if self.peek().is_op(":="):
                self.advance()
                self.advance()
                return DefineStmt(tok.value, None, self.parse_expr(), show_value=True, pos=tok.pos)
            if self.peek().is_op("(") and self._function_assignment_ahead():
                self.advance()
                params = self.parse_params()
                self.expect_op(":=")
                return DefineStmt(tok.value, params, self.parse_expr(), pos=tok.pos)
            if self.is_command(tok.value):
                return self.parse_command()

        expr = self.parse_expr()
        store_to = None
        if self.tok.is_op("→"):
            self.advance()
            target_tok = self.expect_name()
            store_to: Node = Name(target_tok.value, pos=target_tok.pos)
            if self.tok.is_op("[") and not self.tok.space_before:
                store_to = Subscript(store_to, self.parse_index_list(), pos=target_tok.pos)
        return ExprStmt(expr, store_to, pos=tok.pos)

    def _function_assignment_ahead(self) -> bool:
        depth = 0
        for j in range(self.index + 1, len(self.tokens)):
            t = self.tokens[j]
            if t.is_op("("):
                depth += 1
            elif t.is_op(")"):
                depth -= 1
                if depth == 0:
                    return self.tokens[j + 1].is_op(":=")
            elif t.kind == EOF:
                return False
        return False

    def parse_params(self) -> list[str]:
        self.expect_op("(")
        params: list[str] = []
        if not self.tok.is_op(")"):
            params.append(self.expect_name().value)
            while self.tok.is_op(","):
                self.advance()
                params.append(self.expect_name().value)
        self.expect_op(")")
        return params

    def parse_name_list(self) -> list[str]:
        names = [self.expect_name().value]
        while self.tok.is_op(","):
            self.advance()
            names.append(self.expect_name().value)
        return names

    # ------------------------------------------------------------ statement keywords
    def stmt_define(self) -> Node:
        start = self.advance()
        library = None
        if self.word() in ("libpub", "libpriv"):
            library = "LibPub" if self.word() == "libpub" else "LibPriv"
            self.advance()
        name = self.expect_name().value
        params = None
        if self.tok.is_op("("):
            params = self.parse_params()
        self.expect_op("=")
        self.skip_separators()
        if self.word() in ("func", "prgm"):
            kind = self.word()
            self.advance()
            end = "endfunc" if kind == "func" else "endprgm"
            block = self.parse_block({end})
            self.expect_word(end)
            return DefineStmt(name, params or [], None, block=block, kind=kind, library=library, pos=start.pos)
        body = self.parse_expr()
        return DefineStmt(name, params, body, library=library, pos=start.pos)

    def stmt_delvar(self) -> Node:
        start = self.advance()
        return DelVarStmt(self.parse_name_list(), pos=start.pos)

    def stmt_copyvar(self) -> Node:
        start = self.advance()
        source = self.expect_name().value
        self.expect_op(",")
        return CopyVarStmt(source, self.expect_name().value, pos=start.pos)

    def stmt_if(self) -> Node:
        start = self.advance()
        condition = self.parse_expr()
        self.skip_separators()
        if self.word() != "then":
            # one-line If: applies to the next statement only
            return IfStmt([(condition, [self.parse_statement()])], None, pos=start.pos)
        self.advance()
        branches = [(condition, self.parse_block({"elseif", "else", "endif"}))]
        else_block = None
        while True:
            word = self.word()
            if word == "elseif":
                self.advance()
                cond = self.parse_expr()
                self.skip_separators()
                if self.word() != "then":
                    raise CalcSyntaxError("Then missing in block: ElseIf", self.tok.pos)
                self.advance()
                branches.append((cond, self.parse_block({"elseif", "else", "endif"})))
            elif word == "else":
                self.advance()
                else_block = self.parse_block({"endif"})
            elif word == "endif":
                self.advance()
                return IfStmt(branches, else_block, pos=start.pos)
            else:
                raise CalcSyntaxError("Missing EndIf", self.tok.pos)

    def stmt_for(self) -> Node:
        start = self.advance()
        var = self.expect_name().value
        self.expect_op(",")
        begin = self.parse_expr()
        self.expect_op(",")
        end = self.parse_expr()
        step = None
        if self.tok.is_op(","):
            self.advance()
            step = self.parse_expr()
        body = self.parse_block({"endfor"})
        self.expect_word("endfor")
        return ForStmt(var, begin, end, step, body, pos=start.pos)

    def stmt_while(self) -> Node:
        start = self.advance()
        condition = self.parse_expr()
        body = self.parse_block({"endwhile"})
        self.expect_word("endwhile")
        return WhileStmt(condition, body, pos=start.pos)

    def stmt_loop(self) -> Node:
        start = self.advance()
        body = self.parse_block({"endloop"})
        self.expect_word("endloop")
        return LoopStmt(body, pos=start.pos)

    def stmt_try(self) -> Node:
        start = self.advance()
        body = self.parse_block({"else", "endtry"})
        handler = None
        if self.word() == "else":
            self.advance()
            handler = self.parse_block({"endtry"})
        self.expect_word("endtry")
        return TryStmt(body, handler, pos=start.pos)

    def stmt_return(self) -> Node:
        start = self.advance()
        value = None if self.at_statement_end() or self.word() in BLOCK_WORDS else self.parse_expr()
        return ReturnStmt(value, pos=start.pos)

    def _simple(self) -> Node:
        tok = self.advance()
        return SimpleStmt(tok.value.lower(), pos=tok.pos)

    stmt_exit = stmt_cycle = stmt_stop = stmt_clrerr = stmt_passerr = _simple

    def stmt_local(self) -> Node:
        start = self.advance()
        return LocalStmt(self.parse_name_list(), pos=start.pos)

    def stmt_lbl(self) -> Node:
        start = self.advance()
        return LblStmt(self.expect_name().value.lower(), pos=start.pos)

    def stmt_goto(self) -> Node:
        start = self.advance()
        return GotoStmt(self.expect_name().value.lower(), pos=start.pos)

    def parse_command(self) -> Node:
        start = self.advance()
        args: list[Node] = []
        if self.tok.is_op("(") and not self.tok.space_before:
            saved = self.index
            try:
                self.advance()
                args = self.parse_arg_list(")")
                self.expect_op(")")
                if self.at_statement_end():
                    return CommandStmt(start.value, args, pos=start.pos)
            except CalcSyntaxError:
                pass
            self.index = saved
            args = []
        if not self.at_statement_end() and self.word() not in BLOCK_WORDS:
            args.append(self.parse_expr())
            while self.tok.is_op(","):
                self.advance()
                args.append(self.parse_expr())
        return CommandStmt(start.value, args, pos=start.pos)

    def parse_arg_list(self, closing: str) -> list[Node]:
        args: list[Node] = []
        if self.tok.is_op(closing):
            return args
        args.append(self._arg(closing))
        while self.tok.is_op(","):
            self.advance()
            args.append(self._arg(closing))
        return args

    def _arg(self, closing: str) -> Node:
        if closing == ")" and self.tok.is_op(",", ")"):
            return Void(pos=self.tok.pos)
        return self.parse_expr()

    def parse_index_list(self) -> list[Node]:
        self.expect_op("[")
        indices = self.parse_arg_list("]")
        self.expect_op("]")
        if not indices:
            raise CalcSyntaxError("Index expected", self.tok.pos)
        return indices

    # ------------------------------------------------------------ expressions
    def parse_expr(self) -> Node:
        node = self.parse_constraint()
        while self.tok.is_op("►"):
            pos = self.advance().pos
            target = self.tok
            if target.kind != IDENT:
                raise CalcSyntaxError("Conversion target expected after ►", target.pos)
            if target.value.startswith("_"):
                node = Convert(node, target.value, [], target_node=self.parse_term(), pos=pos)
                continue
            self.advance()
            args: list[Node] = []
            if self.tok.is_op("(") and not self.tok.space_before:
                self.advance()
                args = self.parse_arg_list(")")
                self.expect_op(")")
            node = Convert(node, target.value, args, pos=pos)
        return node

    def parse_constraint(self) -> Node:
        node = self.parse_xnor()
        while self.tok.is_op("|"):
            pos = self.advance().pos
            node = With(node, self.parse_xnor(), pos=pos)
        return node

    def _logic_level(self, ops: tuple[str, ...], next_level) -> Node:
        node = next_level()
        while (self.tok.kind == OP and self.tok.value in ops) or self.word() in ops:
            op_tok = self.advance()
            op = op_tok.value.lower() if op_tok.kind == IDENT else op_tok.value
            right = next_level()
            if isinstance(node, Logic) and node.op == op and op in ("and", "or"):
                node.items.append(right)
            else:
                node = Logic(op, [node, right], pos=op_tok.pos)
        return node

    def parse_xnor(self) -> Node:
        return self._logic_level(("⇔",), self.parse_implication)

    def parse_implication(self) -> Node:
        return self._logic_level(("⇒",), self.parse_xor)

    def parse_xor(self) -> Node:
        return self._logic_level(("xor", "nor", "nand"), self.parse_or)

    def parse_or(self) -> Node:
        return self._logic_level(("or",), self.parse_and)

    def parse_and(self) -> Node:
        return self._logic_level(("and",), self.parse_not)

    def parse_not(self) -> Node:
        if self.word() == "not":
            pos = self.advance().pos
            return Not(self.parse_not(), pos=pos)
        return self.parse_relation()

    def parse_relation(self) -> Node:
        left = self.parse_additive()
        if self.tok.kind == OP and self.tok.value in ("=", "≠", "<", ">", "≤", "≥"):
            op_tok = self.advance()
            right = self.parse_additive()
            node = Relation(op_tok.value, left, right, pos=op_tok.pos)
            # chained comparisons such as 1≤x≤3 (used with "|")
            if self.tok.kind == OP and self.tok.value in ("<", ">", "≤", "≥"):
                op2 = self.advance()
                third = self.parse_additive()
                node = Logic("and", [node, Relation(op2.value, right, third, pos=op2.pos)], pos=node.pos)
            return node
        return left

    def parse_additive(self) -> Node:
        node = self.parse_term()
        while self.tok.is_op("+", "-", ".+", ".-"):
            op_tok = self.advance()
            node = BinOp(op_tok.value, node, self.parse_term(), pos=op_tok.pos)
        return node

    def _starts_primary(self, token: Token) -> bool:
        if token.kind in (NUM, STR):
            return True
        if token.kind == IDENT:
            return token.value.lower() not in KEYWORDS
        return token.is_op("(", "{", "[", "#")

    def parse_term(self) -> Node:
        node = self.parse_concat()
        while True:
            if self.tok.is_op("*", "/", ".*", "./"):
                op_tok = self.advance()
                node = BinOp(op_tok.value, node, self.parse_concat(), pos=op_tok.pos)
            elif self._starts_primary(self.tok):
                # implied multiplication: 2x, 3(x+1), (a+b)(a-b), 2π
                if isinstance(node, Num) and self.tok.kind == NUM:
                    raise CalcSyntaxError("Missing operator between numbers", self.tok.pos)
                pos = self.tok.pos
                operand = self.parse_concat_operand()
                if _is_dms(node) and isinstance(operand, Postfix) and operand.op in ("'", "″"):
                    node = BinOp("+", node, operand, pos=pos)  # 30°15'20″
                else:
                    node = BinOp("*", node, operand, pos=pos)
            else:
                return node

    def parse_concat_operand(self) -> Node:
        node = self.parse_power()
        while self.tok.is_op("&"):
            pos = self.advance().pos
            node = BinOp("&", node, self.parse_unary(), pos=pos)
        return node

    def parse_concat(self) -> Node:
        node = self.parse_unary()
        while self.tok.is_op("&"):
            pos = self.advance().pos
            node = BinOp("&", node, self.parse_unary(), pos=pos)
        return node

    def parse_unary(self) -> Node:
        if self.tok.is_op("-"):
            pos = self.advance().pos
            return Neg(self.parse_unary(), pos=pos)
        if self.tok.is_op("+"):
            self.advance()
            return self.parse_unary()
        return self.parse_power()

    def parse_power(self) -> Node:
        base = self.parse_postfix()
        if self.tok.is_op("^", ".^"):
            op_tok = self.advance()
            exponent = self.parse_unary()  # right-associative, allows 2^-1
            return BinOp(op_tok.value, base, exponent, pos=op_tok.pos)
        return base

    def parse_postfix(self) -> Node:
        node = self.parse_primary()
        while True:
            if self.tok.is_op("!", "%", "°", "'", "″", "ʳ", "ᵍ", "ᵀ"):
                op_tok = self.advance()
                if op_tok.value == "″" and isinstance(node, Name):  # y'' (second derivative)
                    node = Postfix("'", Postfix("'", node, pos=op_tok.pos), pos=op_tok.pos)
                    op_tok = Token(op_tok.kind, "'", op_tok.pos)
                else:
                    node = Postfix(op_tok.value, node, pos=op_tok.pos)
                if op_tok.value == "'" and self.tok.is_op("(") and not self.tok.space_before:
                    # y'(0) in deSolve initial conditions
                    base, primes = node, 0
                    while isinstance(base, Postfix) and base.op == "'":
                        base, primes = base.operand, primes + 1
                    if isinstance(base, Name):
                        self.advance()
                        args = self.parse_arg_list(")")
                        self.expect_op(")")
                        node = Call(base.name + "'" * primes, args, pos=base.pos)
            elif self.tok.is_op("[") and not self.tok.space_before and \
                    isinstance(node, (Name, Call, ListLit, MatrixLit, Subscript)):
                node = Subscript(node, self.parse_index_list(), pos=node.pos)
            else:
                return node

    def parse_primary(self) -> Node:
        tok = self.tok
        if tok.kind == NUM:
            self.advance()
            return Num(tok.value, pos=tok.pos)

        if tok.kind == STR:
            self.advance()
            return Str(tok.value, pos=tok.pos)

        if tok.kind == IDENT:
            if tok.value.lower() in KEYWORDS:
                raise CalcSyntaxError(f"Unexpected '{tok.value}'", tok.pos)
            self.advance()
            if tok.value == "√" and not self.tok.is_op("("):
                return Call("√", [self.parse_power()], pos=tok.pos)
            if self.tok.is_op("(") and self.is_function(tok.value):
                self.advance()
                args = self.parse_arg_list(")")
                self.expect_op(")")
                return Call(tok.value, args, pos=tok.pos)
            return Name(tok.value, pos=tok.pos)

        if tok.is_op("#"):
            self.advance()
            return Indirection(self.parse_postfix(), pos=tok.pos)

        if tok.is_op("("):
            self.advance()
            node = self.parse_expr()
            if self.tok.is_op("∠"):  # (r∠θ) polar complex number
                self.advance()
                node = Polar(node, self.parse_expr(), pos=tok.pos)
            self.expect_op(")")
            return node

        if tok.is_op("{"):
            self.advance()
            items = self.parse_arg_list("}")
            self.expect_op("}")
            return ListLit(items, pos=tok.pos)

        if tok.is_op("["):
            return self.parse_matrix()

        if tok.kind == EOF:
            raise CalcSyntaxError("Unexpected end of input", tok.pos)
        raise CalcSyntaxError(f"Unexpected '{tok.value}'", tok.pos)

    def parse_matrix(self) -> Node:
        """[1,2;3,4]   [[1,2][3,4]]   [[1,2],[3,4]]   [1,2,3]   [r,∠θ] (polar vector)"""
        start = self.expect_op("[")
        rows: list[list[Node]] = []
        if self.tok.is_op("["):
            while self.tok.is_op("["):
                self.advance()
                rows.append(self.parse_arg_list("]"))
                self.expect_op("]")
                if self.tok.is_op(","):
                    self.advance()
            self.expect_op("]")
        else:
            row: list[Node] = []
            while True:
                if self.tok.is_op("∠"):
                    angle_pos = self.advance().pos
                    angle = self.parse_expr()
                    row.append(Postfix("∠", angle, pos=angle_pos))
                else:
                    row.append(self.parse_expr())
                if self.tok.is_op(","):
                    self.advance()
                elif self.tok.is_op(";"):
                    self.advance()
                    rows.append(row)
                    row = []
                else:
                    break
            rows.append(row)
            self.expect_op("]")
        widths = {len(r) for r in rows}
        if len(widths) != 1 or 0 in widths:
            raise CalcSyntaxError("Dimension error: all rows must have the same length", start.pos)
        return MatrixLit(rows, pos=start.pos)


def _is_dms(node: Node) -> bool:
    if isinstance(node, Postfix) and node.op in ("°", "'"):
        return isinstance(node.operand, Num)
    if isinstance(node, BinOp) and node.op == "+":
        return _is_dms(node.right)
    return False


def parse(
    source: str,
    is_function: Callable[[str], bool] = lambda name: True,
    is_command: Callable[[str], bool] = lambda name: False,
) -> list[Node]:
    return Parser(source, is_function, is_command).parse_program()
