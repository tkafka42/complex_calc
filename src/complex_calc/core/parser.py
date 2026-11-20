"""Recursive-descent parser that turns tokens into a small AST.

Grammar (lowest to highest precedence)::

    program    := statement (":" statement)*
    statement  := "Define" target "=" expr
                | "DelVar" name ("," name)*
                | "CopyVar" name "," name
                | name ":=" expr | name "(" params ")" ":=" expr
                | command arg ("," arg)*          (zInterval 15,100,25)
                | expr ("→" name)?
    expr       := or ("|" or)*                    (the "with" operator)
    or         := and (("or"|"xor") and)*
    and        := not ("and" not)*
    not        := "not" not | relation
    relation   := additive (relop additive)?
    additive   := term (("+"|"-") term)*
    term       := unary (("*"|"/") unary | <implicit> power)*
    unary      := ("-"|"+") unary | power
    power      := postfix ("^" unary)?
    postfix    := primary ("!" | "°")*
    primary    := number | name | call | "(" expr ")" | "{" list "}"
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .errors import CalcSyntaxError
from .tokenizer import EOF, IDENT, NUM, OP, Token, tokenize

# ---------------------------------------------------------------- AST nodes


@dataclass
class Node:
    pos: int = field(default=0, kw_only=True)


@dataclass
class Num(Node):
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
    op: str  # + - * / ^
    left: Node
    right: Node


@dataclass
class Neg(Node):
    operand: Node


@dataclass
class Postfix(Node):
    op: str  # ! °
    operand: Node


@dataclass
class Relation(Node):
    op: str  # = ≠ < > ≤ ≥
    left: Node
    right: Node


@dataclass
class Logic(Node):
    op: str  # and / or / xor
    items: list[Node]


@dataclass
class Not(Node):
    operand: Node


@dataclass
class With(Node):
    expr: Node
    condition: Node


@dataclass
class ListLit(Node):
    items: list[Node]


# ---------------------------------------------------------------- statements


@dataclass
class ExprStmt(Node):
    expr: Node
    store_to: str | None = None


@dataclass
class DefineStmt(Node):
    name: str
    params: list[str] | None  # None for a plain variable
    body: Node
    show_value: bool = False  # "a:=5" shows 5, "Define a=5" shows Done


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


KEYWORDS = {"and", "or", "xor", "not"}


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
            raise CalcSyntaxError(f"Expected '{value}' but found '{found}'", self.tok.pos)
        return self.advance()

    def expect_name(self) -> Token:
        if self.tok.kind != IDENT:
            raise CalcSyntaxError("Variable name expected", self.tok.pos)
        return self.advance()

    def is_keyword(self, token: Token, word: str) -> bool:
        return token.kind == IDENT and token.value.lower() == word

    def at_statement_end(self) -> bool:
        return self.tok.kind == EOF or self.tok.is_op(":")

    # ------------------------------------------------------------ program
    def parse_program(self) -> list[Node]:
        statements: list[Node] = []
        while True:
            if self.tok.kind == EOF:
                break
            if self.tok.is_op(":"):
                self.advance()
                continue
            statements.append(self.parse_statement())
            if not self.at_statement_end():
                raise CalcSyntaxError(f"Unexpected '{self.tok.value}'", self.tok.pos)
        if not statements:
            raise CalcSyntaxError("Empty input", 0)
        return statements

    def parse_statement(self) -> Node:
        tok = self.tok
        if tok.kind == IDENT:
            lower = tok.value.lower()
            if lower == "define":
                return self.parse_define()
            if lower == "delvar":
                self.advance()
                names = [self.expect_name().value]
                while self.tok.is_op(","):
                    self.advance()
                    names.append(self.expect_name().value)
                return DelVarStmt(names, pos=tok.pos)
            if lower == "copyvar":
                self.advance()
                source = self.expect_name().value
                self.expect_op(",")
                target = self.expect_name().value
                return CopyVarStmt(source, target, pos=tok.pos)
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
            store_to = self.expect_name().value
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

    def parse_define(self) -> Node:
        start = self.advance()
        name = self.expect_name().value
        params = None
        if self.tok.is_op("("):
            params = self.parse_params()
        self.expect_op("=")
        body = self.parse_expr()
        return DefineStmt(name, params, body, pos=start.pos)

    def parse_command(self) -> Node:
        start = self.advance()
        args: list[Node] = []
        # Accept an optional pair of parentheses around the whole argument list.
        if self.tok.is_op("("):
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
        if not self.at_statement_end():
            args.append(self.parse_expr())
            while self.tok.is_op(","):
                self.advance()
                args.append(self.parse_expr())
        return CommandStmt(start.value, args, pos=start.pos)

    def parse_arg_list(self, closing: str) -> list[Node]:
        args: list[Node] = []
        if self.tok.is_op(closing):
            return args
        args.append(self.parse_expr())
        while self.tok.is_op(","):
            self.advance()
            args.append(self.parse_expr())
        return args

    # ------------------------------------------------------------ expressions
    def parse_expr(self) -> Node:
        node = self.parse_or()
        while self.tok.is_op("|"):
            pos = self.advance().pos
            node = With(node, self.parse_or(), pos=pos)
        return node

    def parse_or(self) -> Node:
        node = self.parse_and()
        while self.is_keyword(self.tok, "or") or self.is_keyword(self.tok, "xor"):
            op = self.advance().value.lower()
            right = self.parse_and()
            if isinstance(node, Logic) and node.op == op:
                node.items.append(right)
            else:
                node = Logic(op, [node, right], pos=node.pos)
        return node

    def parse_and(self) -> Node:
        node = self.parse_not()
        while self.is_keyword(self.tok, "and"):
            self.advance()
            right = self.parse_not()
            if isinstance(node, Logic) and node.op == "and":
                node.items.append(right)
            else:
                node = Logic("and", [node, right], pos=node.pos)
        return node

    def parse_not(self) -> Node:
        if self.is_keyword(self.tok, "not"):
            pos = self.advance().pos
            return Not(self.parse_not(), pos=pos)
        return self.parse_relation()

    def parse_relation(self) -> Node:
        left = self.parse_additive()
        if self.tok.kind == OP and self.tok.value in ("=", "≠", "<", ">", "≤", "≥"):
            op_tok = self.advance()
            right = self.parse_additive()
            return Relation(op_tok.value, left, right, pos=op_tok.pos)
        return left

    def parse_additive(self) -> Node:
        node = self.parse_term()
        while self.tok.is_op("+", "-"):
            op_tok = self.advance()
            node = BinOp(op_tok.value, node, self.parse_term(), pos=op_tok.pos)
        return node

    def _starts_primary(self, token: Token) -> bool:
        if token.kind == NUM:
            return True
        if token.kind == IDENT:
            return token.value.lower() not in KEYWORDS
        return token.is_op("(", "{")

    def parse_term(self) -> Node:
        node = self.parse_unary()
        while True:
            if self.tok.is_op("*", "/"):
                op_tok = self.advance()
                node = BinOp(op_tok.value, node, self.parse_unary(), pos=op_tok.pos)
            elif self._starts_primary(self.tok):
                # implicit multiplication: 2x, 3(x+1), (a+b)(a-b), 2π
                if isinstance(node, Num) and self.tok.kind == NUM:
                    raise CalcSyntaxError("Missing operator between numbers", self.tok.pos)
                node = BinOp("*", node, self.parse_power(), pos=self.tok.pos)
            else:
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
        if self.tok.is_op("^"):
            pos = self.advance().pos
            exponent = self.parse_unary()  # right-associative, allows 2^-1
            return BinOp("^", base, exponent, pos=pos)
        return base

    def parse_postfix(self) -> Node:
        node = self.parse_primary()
        while self.tok.is_op("!", "°"):
            op_tok = self.advance()
            node = Postfix(op_tok.value, node, pos=op_tok.pos)
        return node

    def parse_primary(self) -> Node:
        tok = self.tok
        if tok.kind == NUM:
            self.advance()
            return Num(tok.value, pos=tok.pos)

        if tok.kind == IDENT:
            if tok.value.lower() in KEYWORDS:
                raise CalcSyntaxError(f"Unexpected '{tok.value}'", tok.pos)
            self.advance()
            if tok.value == "√" and not self.tok.is_op("("):
                return Call("√", [self.parse_power()], pos=tok.pos)
            if self.is_function(tok.value):
                if not self.tok.is_op("("):
                    raise CalcSyntaxError(f"Missing '(' after {tok.value}", self.tok.pos)
                self.advance()
                args = self.parse_arg_list(")")
                self.expect_op(")")
                return Call(tok.value, args, pos=tok.pos)
            return Name(tok.value, pos=tok.pos)

        if tok.is_op("("):
            self.advance()
            node = self.parse_expr()
            self.expect_op(")")
            return node

        if tok.is_op("{"):
            self.advance()
            items = self.parse_arg_list("}")
            self.expect_op("}")
            return ListLit(items, pos=tok.pos)

        if tok.kind == EOF:
            raise CalcSyntaxError("Unexpected end of input", tok.pos)
        raise CalcSyntaxError(f"Unexpected '{tok.value}'", tok.pos)


def parse(
    source: str,
    is_function: Callable[[str], bool] = lambda name: False,
    is_command: Callable[[str], bool] = lambda name: False,
) -> list[Node]:
    return Parser(source, is_function, is_command).parse_program()
