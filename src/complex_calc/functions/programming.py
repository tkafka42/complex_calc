"""Program I/O and system commands: Disp, Text, Request, RequestStr, DispAt,
Wait, getKey, ClearAZ, Lock, unLock, getLockInfo, getMode, setMode, getType,
getVarInfo, getLangInfo, getPlatform."""

from __future__ import annotations

import time

import sympy as sp

from ..core.errors import ArgumentError, DomainError, EvaluationError
from ..core.values import (
    ListValue,
    StatResults,
    StringValue,
    TextValue,
    UserFunction,
    UserProgram,
    is_matrix,
)
from .registry import builtin, to_float, to_int


def _text(ctx, value) -> str:
    from ..core.formatting import format_value

    if isinstance(value, StringValue):
        return str(value)
    return format_value(value, ctx.settings.digits)


@builtin("Disp", "Disp exprOrString1[,exprOrString2]…", 0, 99, command=True, summary="Show values in the history")
def disp(ctx, *values):
    ctx.session.emit(" ".join(_text(ctx, v) for v in values))
    return None


@builtin("DispAt", "DispAt lineNumber,exprOrString1[,exprOrString2]…", 2, 99, command=True,
         summary="Show values at a line of the output")
def disp_at(ctx, line, *values):
    ctx.session.emit(f"[{to_int(line, 'lineNumber')}] " + " ".join(_text(ctx, v) for v in values))
    return None


@builtin("Text", "Text promptString[,DispFlag]", 1, 2, command=True, summary="Show a message")
def text_(ctx, prompt, flag=None):
    if ctx.session.input_provider is not None:
        ctx.session.input_provider(_text(ctx, prompt), None)
    if flag is None or to_float(flag, "DispFlag") != 0:
        ctx.session.emit(_text(ctx, prompt))
    return None


def _request(ctx, prompt, var, as_string: bool, flag):
    provider = ctx.session.input_provider
    if provider is None:
        raise EvaluationError("Request needs interactive input")
    answer = provider(_text(ctx, prompt), as_string)
    if answer is None:
        raise EvaluationError("Request cancelled")
    if as_string:
        value = StringValue(answer)
    else:
        from ..core.parser import parse

        statements = parse(answer, ctx.session.is_function, ctx.session.is_command)
        value = ctx.evaluator.exec_statement(statements[0])
    if isinstance(var, sp.core.function.AppliedUndef):  # Request "f(x)=", f(x)
        params = [a for a in var.args if isinstance(a, sp.Symbol)]
        ctx.store(var.func.__name__, UserFunction(var.func.__name__, params, value))
    else:
        ctx.store(var.name, value)
    if flag is None or to_float(flag, "DispFlag") != 0:
        ctx.session.emit(f"{_text(ctx, prompt)} {answer}")
    return None


@builtin("Request", "Request promptString,var[,DispFlag]", 2, 3, command=True, hold=(1,),
         summary="Ask the user for a value")
def request(ctx, prompt, var, flag=None):
    return _request(ctx, prompt, var, False, flag)


@builtin("RequestStr", "RequestStr promptString,var[,DispFlag]", 2, 3, command=True, hold=(1,),
         summary="Ask the user for a string")
def request_str(ctx, prompt, var, flag=None):
    return _request(ctx, prompt, var, True, flag)


@builtin("Wait", "Wait timeInSeconds", 1, command=True, summary="Pause (max 100 s)")
def wait_(ctx, seconds):
    t = to_float(seconds, "timeInSeconds")
    if not 0 <= t <= 100:
        raise DomainError("timeInSeconds must be 0…100")
    time.sleep(min(t, 100))
    return None


@builtin("getKey", "getKey([0|1])", 0, 1, summary='Key pressed (always "" here)')
def get_key(ctx, flag=None):
    return StringValue("")


@builtin("ClearAZ", "ClearAZ", 0, command=True, summary="Delete all single-character variables")
def clear_az(ctx):
    for key in [k for k in ctx.session.variables if len(k) == 1 and k not in ctx.session.locked]:
        del ctx.session.variables[key]
    return None


@builtin("Lock", "Lock Var1[,Var2]…", 1, 20, command=True, hold=tuple(range(20)), summary="Lock variables")
def lock_(ctx, *names):
    for name in names:
        ctx.session.locked.add(name.name)
    return None


@builtin("unLock", "unLock Var1[,Var2]…", 1, 20, command=True, hold=tuple(range(20)), summary="Unlock variables")
def unlock_(ctx, *names):
    for name in names:
        ctx.session.locked.discard(name.name)
    return None


@builtin("getLockInfo", "getLockInfo(Var)", 1, hold=(0,), summary="1 if locked, 0 otherwise")
def get_lock_info(ctx, name):
    return sp.Integer(1 if name.name in ctx.session.locked else 0)


def _type_name(value) -> str:
    if value is None:
        return "NONE"
    if isinstance(value, StringValue):
        return "STR"
    if isinstance(value, ListValue):
        return "LIST"
    if is_matrix(value):
        return "MAT"
    if isinstance(value, UserFunction) or (isinstance(value, UserProgram) and value.kind == "func"):
        return "FUNC"
    if isinstance(value, UserProgram):
        return "PRGM"
    if isinstance(value, StatResults):
        return "OTHER"
    if isinstance(value, sp.Basic) and value.is_number:
        return "NUM"
    if isinstance(value, sp.Basic):
        return "EXPR"
    return "OTHER"


@builtin("getType", "getType(var)", 1, hold=(0,), summary='Type of a variable ("NUM", "EXPR", "LIST", "STR", …)')
def get_type(ctx, name):
    return StringValue(_type_name(ctx.lookup(name.name)))


@builtin("getVarInfo", "getVarInfo()", 0, 1, summary="Table of defined variables")
def get_var_info(ctx, library=None):
    variables = ctx.session.variables
    names = [k for k in sorted(variables) if not k.startswith("stat.") and k != "ans"]
    if not names:
        return StringValue("NONE")
    rows = [[StringValue_to_sym(k), StringValue_to_sym(_type_name(variables[k])), StringValue_to_sym("0"),
             StringValue_to_sym("LOCKED" if k in ctx.session.locked else "UNLOCKED")] for k in names]
    return sp.ImmutableMatrix(rows)


def StringValue_to_sym(text: str) -> sp.Symbol:  # noqa: N802 - matrices hold symbols, shown as text
    return sp.Symbol(f'"{text}"')


@builtin("getLangInfo", "getLangInfo()", 0, summary='Language abbreviation ("en")')
def get_lang_info(ctx):
    return StringValue("en")


@builtin("getPlatform", "getPlatform()", 0, summary='Platform ("dt" = desktop)')
def get_platform(ctx):
    return StringValue("dt")


# ------------------------------------------------------------------ modes

_ANGLES = {1: "rad", 2: "deg", 3: "grad"}
_COMPLEX = {1: "real", 2: "rectangular", 3: "polar"}
_AUTO = {1: "auto", 2: "approx", 3: "exact"}


def _digits_code(settings) -> int:
    if getattr(settings, "fix", None) is not None:
        return 14 + settings.fix
    return 1 if settings.digits >= 12 and getattr(settings, "float_full", False) else settings.digits + 1


def _get_mode(settings, mode: int) -> int:
    if mode == 1:
        return _digits_code(settings)
    if mode == 2:
        return {v: k for k, v in _ANGLES.items()}[settings.angle]
    if mode == 3:
        return {"normal": 1, "scientific": 2, "engineering": 3}[getattr(settings, "exp_format", "normal")]
    if mode == 4:
        return {v: k for k, v in _COMPLEX.items()}[settings.complex_format]
    if mode == 5:
        return {v: k for k, v in _AUTO.items()}[settings.mode]
    if mode == 6:
        return {"rectangular": 1, "cylindrical": 2, "spherical": 3}[getattr(settings, "vector_format", "rectangular")]
    if mode == 7:
        return {"dec": 1, "hex": 2, "bin": 3}[getattr(settings, "base", "dec")]
    if mode == 8:
        return 1
    raise DomainError("Invalid mode number")


def _set_mode(settings, mode: int, value: int) -> int:
    old = _get_mode(settings, mode)
    if mode == 1:
        if value == 1:
            settings.fix, settings.digits, settings.float_full = None, 12, True
        elif 2 <= value <= 13:
            settings.fix, settings.digits, settings.float_full = None, value - 1, False
        elif 14 <= value <= 26:
            settings.fix = value - 14
        else:
            raise DomainError("Invalid setting")
    elif mode == 2:
        settings.angle = _ANGLES[value]
    elif mode == 3:
        settings.exp_format = {1: "normal", 2: "scientific", 3: "engineering"}[value]
    elif mode == 4:
        settings.complex_format = _COMPLEX[value]
    elif mode == 5:
        settings.mode = _AUTO[value]
    elif mode == 6:
        settings.vector_format = {1: "rectangular", 2: "cylindrical", 3: "spherical"}[value]
    elif mode == 7:
        settings.base = {1: "dec", 2: "hex", 3: "bin"}[value]
    elif mode != 8:
        raise DomainError("Invalid mode number")
    return old


@builtin("getMode", "getMode(ModeNameInteger)  |  getMode(0)", 1, summary="Current mode setting")
def get_mode(ctx, mode):
    m = to_int(mode, "ModeNameInteger")
    if m == 0:
        return ListValue(sp.Integer(v) for k in range(1, 9) for v in (k, _get_mode(ctx.settings, k)))
    return sp.Integer(_get_mode(ctx.settings, m))


@builtin("setMode", "setMode(ModeNameInteger,SettingInteger)  |  setMode(list)", 1, 2,
         summary="Change a mode; returns the previous setting")
def set_mode(ctx, mode, value=None):
    try:
        if isinstance(mode, ListValue):
            items = [to_int(v, "mode") for v in mode]
            old = []
            for k in range(0, len(items), 2):
                old += [items[k], _set_mode(ctx.settings, items[k], items[k + 1])]
            return ListValue(sp.Integer(v) for v in old)
        if value is None:
            raise ArgumentError("Too few arguments")
        return sp.Integer(_set_mode(ctx.settings, to_int(mode, "mode"), to_int(value, "setting")))
    except KeyError:
        raise DomainError("Invalid setting")


# ------------------------------------------------------------------ libraries


@builtin("libShortcut", "libShortcut(LibNameString,ShortcutNameString[,LibPrivFlag])", 2, 3,
         summary="Create short.name references to the objects of a library")
def lib_shortcut(ctx, lib_name, short_name, priv_flag=None):
    if not isinstance(lib_name, StringValue) or not isinstance(short_name, StringValue):
        raise ArgumentError("libShortcut needs two strings")
    library = ctx.session.libraries.get(str(lib_name).lower())
    if library is None:
        raise EvaluationError(f'Library "{lib_name}" not found (put it in MyLib and refresh libraries)')
    include_private = priv_flag is not None and to_float(priv_flag, "LibPrivFlag") != 0
    names = []
    for obj, (value, public) in sorted(library.items()):
        if public or include_private:
            full = f"{short_name}.{obj}"
            ctx.session.variables[full.lower()] = value
            names.append(sp.Symbol(full))
    return ListValue(names)


# ------------------------------------------------------------------ hardware commands (not available on a PC)


def _hardware(name: str, signature: str, what: str):
    @builtin(name, signature, 0, 99, command=True, raw=tuple(range(99)), summary=f"{what} (needs hardware)")
    def command(ctx, *args):
        raise EvaluationError(f"{name}: {what} is not connected")

    return command


_hardware("Send", 'Send exprOrString1[,exprOrString2]…', "TI-Innovator™ Hub")
_hardware("Get", "Get [promptString,]var[,statusVar]", "TI-Innovator™ Hub")
_hardware("GetStr", "GetStr [promptString,]var[,statusVar]", "TI-Innovator™ Hub")
_hardware("RefreshProbeVars", "RefreshProbeVars", "Vernier DataQuest™ sensor")


@builtin("eval", "eval(Expr)", 1, summary="Expression as a string (for Hub commands)")
def eval_(ctx, value):
    return StringValue(_text(ctx, value))
