"""Command-line REPL: ``complex-calc``.

Type expressions as on the handheld, e.g. ``normCdf(-∞,520,500,10)``.
Lines starting with ``:`` are REPL commands (``:help``).
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from .. import __version__
from ..core.session import Session
from ..functions.registry import REGISTRY, canonical_names, lookup_builtin
from ..menus import MENU, find_path, render_tree

HELP = """\
Complex Calc — commands
  <expression>           evaluate, e.g. solve(x^2-4=0,x)  or  zInterval 15,100,25,0.95
  ~<expression>          evaluate approximately (like Ctrl+Enter in the GUI)
  :help [name]           this help, or the syntax of a function (e.g. :help normCdf)
  :list                  all functions and commands
  :menu [keys]           show the numbered menu, e.g. :menu 6 5
  :mode auto|exact|approx
  :angle rad|deg|grad
  :complex real|rectangular|polar
  :digits N              display digits (Float N), default 6
  :vars                  show defined variables
  :clear                 delete all variables
  :refreshlib            Refresh Libraries (MyLib folder, use lib\\name(...))
  :quit                  exit (also Ctrl+D)

Keyboard shortcuts (as in the reference guide): sqrt( → √(  pi → π  @e → ℯ
@i → ⅈ  infinity → ∞  <= >= /= → ≤ ≥ ≠  =: → →  => → ⇒  @> → ►  @t → ᵀ
derivative( → d(  integral( → ∫(  sumSeq( → Σ(  deltaList( → ΔList(
Note: like on the handheld, the letters e and i are ordinary variables.
Programs: separate statements with ":" e.g.
  Define f(n)=Func:If n≤1 Then:Return 1:Else:Return n*f(n-1):EndIf:EndFunc
"""


def _history_file() -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return base / "complex_calc" / "history"


def _setup_readline():
    try:
        import readline
    except ImportError:  # pragma: no cover
        return None
    words = sorted({spec.name for spec in REGISTRY.values()} | {"Define", "DelVar", "CopyVar"})

    def complete(text: str, state: int):
        matches = [w + ("(" if (s := lookup_builtin(w)) and not s.command else " ") for w in words
                   if w.lower().startswith(text.lower())]
        return matches[state] if state < len(matches) else None

    readline.set_completer_delims(" \t\n,(){}+-*/^=<>|:")
    readline.set_completer(complete)
    readline.parse_and_bind("tab: complete")
    path = _history_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            readline.read_history_file(path)
    except OSError:
        pass
    return readline, path


def _settings_line(session: Session) -> str:
    s = session.settings
    digits = f"Fix {s.fix}" if s.fix is not None else f"Float {s.digits}"
    return f"mode={s.mode}  angle={s.angle}  complex={s.complex_format}  digits={digits}"


def handle_command(session: Session, line: str) -> str | None:
    """Handle a ':' command. Returns text to print, or None to quit."""
    parts = line[1:].split()
    if not parts:
        return HELP
    cmd, args = parts[0].lower(), parts[1:]
    if cmd in ("q", "quit", "exit"):
        return None
    if cmd in ("h", "help", "?"):
        if not args:
            return HELP
        spec = lookup_builtin(args[0])
        if spec is None:
            return f"Unknown function '{args[0]}'"
        text = f"{spec.signature}\n  {spec.summary}"
        if spec.aliases:
            text += f"\n  also: {', '.join(spec.aliases)}"
        return text
    if cmd == "list":
        return "  ".join(canonical_names())
    if cmd == "menu":
        if not args:
            return render_tree(max_depth=1) + "\n(:menu 6 shows a submenu)"
        try:
            item = find_path(*args)
        except KeyError:
            return "No such menu path"
        if not item.children:
            return render_tree([item])
        return render_tree(item.children, max_depth=2)
    if cmd == "mode":
        if args and args[0].lower() in ("auto", "exact", "approx", "approximate"):
            session.settings.mode = "approx" if args[0].lower().startswith("approx") else args[0].lower()
        return _settings_line(session)
    if cmd == "angle":
        if args and args[0].lower() in ("rad", "deg", "grad", "radian", "degree", "gradian"):
            session.settings.angle = {"r": "rad", "d": "deg", "g": "grad"}[args[0].lower()[0]]
        return _settings_line(session)
    if cmd == "complex":
        if args and args[0].lower() in ("real", "rectangular", "polar"):
            session.settings.complex_format = args[0].lower()
        return _settings_line(session)
    if cmd == "digits":
        if args and args[0].isdigit() and 1 <= int(args[0]) <= 12:
            session.settings.digits = int(args[0])
        return _settings_line(session)
    if cmd == "vars":
        if not session.variables:
            return "(no variables)"
        return "\n".join(f"{name} = {session.format(value)}" for name, value in sorted(session.variables.items())
                         if "\n" not in session.format(value))
    if cmd in ("refreshlib", "refreshlibs"):
        from ..library import library_folder, refresh_libraries

        return "\n".join([f"Library folder: {library_folder()}", *refresh_libraries(session)])
    if cmd == "clear":
        session.clear_variables()
        return "Done"
    return f"Unknown command :{cmd}  (type :help)"


def process_line(session: Session, line: str) -> str | None:
    line = line.strip()
    if not line:
        return ""
    if line.startswith(":") and not line.startswith(":="):
        return handle_command(session, line)
    force_approx = False
    if line.startswith("~"):
        force_approx, line = True, line[1:].strip()
    entry = session.run(line, force_approx=force_approx)
    lines = [*entry.output]
    if entry.drawing:
        import tempfile

        from ..functions.draw import render

        path = tempfile.NamedTemporaryFile(prefix="complex_calc_drawing_", suffix=".png", delete=False).name
        render(entry.drawing).save(path)
        lines.append(f"(graphics saved to {path})")
    lines.append(entry.text)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="complex-calc", description="CAS calculator REPL")
    parser.add_argument("-c", "--command", action="append", help="evaluate and exit (repeatable)")
    parser.add_argument("--deg", action="store_true", help="start in degree mode")
    parser.add_argument("--version", action="version", version=f"complex_calc {__version__}")
    options = parser.parse_args(argv)

    session = Session()

    def ask(prompt: str, as_string):
        if as_string is None:  # Text
            print("  " + prompt)
            return ""
        try:
            return input(f"  {prompt} ")
        except EOFError:
            return None

    session.input_provider = ask
    from ..library import refresh_libraries

    refresh_libraries(session)
    if options.deg:
        session.settings.angle = "deg"

    if options.command:
        for command in options.command:
            print(process_line(session, command))
        return 0

    if not sys.stdin.isatty():
        for line in sys.stdin:
            out = process_line(session, line)
            if out is None:
                break
            if out:
                print(out)
        return 0

    rl = _setup_readline()
    print(f"Complex Calc {__version__} — type :help for help, :quit to exit")
    print(_settings_line(session))
    try:
        while True:
            try:
                line = input("› ")
            except EOFError:
                print()
                break
            except KeyboardInterrupt:
                print()
                continue
            out = process_line(session, line)
            if out is None:
                break
            if out:
                print("  " + out.replace("\n", "\n  "))
    finally:
        if rl is not None:
            readline, path = rl
            try:
                readline.set_history_length(1000)
                readline.write_history_file(path)
            except OSError:
                pass
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
