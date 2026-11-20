# Complex Calc

An open-source CAS calculator for Linux, made for practising school maths
(statistics, equation solving, calculus) on a PC.

Complex Calc **uses command syntax similar to the TI-Nspire™ CX CAS**: the same
command names and argument orders (`normCdf(lowBound,upBound,μ,σ)`,
`binomCdf(n,p,lower,upper)`, `zInterval σ,x̄,n,CLevel`, `solve(…,x)`, …) and a
numbered menu with the same paths (e.g. *Menu → 6 Statistics →
5 Distributions → 2 Normal Cdf*). The design is the project's own.

> **Disclaimer:** This project is not affiliated with, endorsed by or sponsored
> by Texas Instruments. TI-Nspire is a trademark of Texas Instruments
> Incorporated. No TI firmware, OS files, ROMs, graphics, icons or fonts are
> used or included.

## Features

- **Calculator page** with entry line and history. Click an entry or result
  to reuse it. Results can be exact (CAS) or decimal: switch between
  Auto/Exact/Approximate, or press Ctrl+Enter for one decimal result.
- **Statistics:** `normPdf`, `normCdf` (with ±∞), `invNorm`, `tPdf`, `tCdf`,
  `invt`, `binomPdf`, `binomCdf`, `invBinom`, `poissPdf`, `poissCdf`,
  `geomPdf`, `geomCdf`, `χ²Pdf`, `χ²Cdf`, `zInterval`, `tInterval`, `OneVar`,
  `mean`, `median`, `stDevSamp`, `stDevPop`, `varSamp`, `varPop`.
- **Regression:** `LinRegMx`, `LinRegBx`, `QuadReg`, `ExpReg`, `SinReg`.
  The results are kept in `stat.RegEqn`, `stat.m`, … like on the handheld.
- **CAS:** `solve`, `cSolve`, `nSolve`, `zeros`, `cZeros`, `factor`, `cFactor`,
  `expand`, `approx`, `exact`, `derivative`, `∫`/`integral`, `nDeriv`, `nInt`,
  `limit`.
- `Define f(x)=…`, `a:=5`, `5→a`, `DelVar`, the "with" operator
  `x^2|x=3`, Rad/Deg, lists `{1,2,3}`.
- **Numbered menu** (Ctrl+M) with assistant dialogs (wizards).
- **REPL** for the terminal.
- Planned: Graphs page (M4), Lists & Spreadsheet page (M5).

Command names are case-insensitive (`NORMCDF` = `normCdf`).
[`UNSURE_SYNTAX.md`](UNSURE_SYNTAX.md) lists every place where the
syntax, output format or menu numbering could not be verified against a real
device.

## Installation

Requirements: Python ≥ 3.11 and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/<you>/complex_calc.git
cd complex_calc
uv sync
uv run complex-calc        # terminal REPL
uv run complex-calc-gui    # GUI (native Wayland, falls back to X11)
```

Without uv:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e .
complex-calc
```

Optional desktop launcher:

```bash
uv tool install .   # puts complex-calc and complex-calc-gui on your PATH
install -Dm644 data/complex_calc.desktop ~/.local/share/applications/complex_calc.desktop
install -Dm644 data/complex_calc.svg ~/.local/share/icons/hicolor/scalable/apps/complex_calc.svg
```

## Usage examples

```
› normCdf(-∞,520,500,10)
  0.97725
› binomCdf(20,0.1,0,3)
  0.867047
› cSolve(x^2+4x+13=0,x)
  x=-2-3·i or x=-2+3·i
› zInterval 15,100,25,0.95
  "Title"           "z Interval"
  "CLower, CUpper"  {94.1201,105.88}
  "x̄"               100.
  "ME"              5.87989
  "n"               25
  "σ"               15.
› Define f(x)=x^3-3x
  Done
› solve(f(x)=0,x)
  x=-√(3) or x=0 or x=√(3)
```

REPL commands: `:help [name]`, `:menu [6 5]`, `:mode auto|exact|approx`,
`:angle rad|deg`, `:digits N`, `:vars`, `:clear`, `:quit`. Start a line with `~`
to get a decimal result.

Keyboard alternatives for special characters: `sqrt(` → `√(`, `pi` → `π`,
`e^(` → `ℯ^(`, `i` → `ⅈ`, `inf`/`infinity` → `∞`, `<=` `>=` `/=` → `≤ ≥ ≠`,
`->` or `=:` → `→`.

## Development

```bash
uv run pytest
```

Project layout:

```
src/complex_calc/
  core/        tokenizer, parser, session (evaluator), formatting
  functions/   built-in functions (registry, stats, intervals, regression, cas, elementary)
  menus.py     numbered menu tree + wizard definitions (shared by GUI and REPL)
  cli/         REPL
  gui/         PySide6 GUI
tests/         pytest suite with reference values
```

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
