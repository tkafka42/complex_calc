"""python -m complex_calc  → REPL;  python -m complex_calc --gui  → GUI."""

import sys


def main() -> int:
    if "--gui" in sys.argv[1:]:
        sys.argv.remove("--gui")
        from .gui.app import main as gui_main

        return gui_main()
    from .cli.repl import main as repl_main

    return repl_main()


if __name__ == "__main__":
    sys.exit(main())
