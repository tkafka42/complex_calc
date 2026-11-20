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

## Why this exists

I was studying for a maths exam without my calculator at hand, and I was
surprised to find no open-source alternative for Linux that works the way the
handheld does. So I decided to build one myself, together with Claude (an AI
assistant).

To be upfront: this project is largely AI-generated ("vibe-coded"). I steered
the direction, set the requirements and tested it, but most of the code was
written by Claude. Bug reports, corrections against the real device and pull
requests are very welcome.

## Features

The **command set** follows the official *TI-Nspire™ CX CAS Reference Guide*
(v6.4): command names, argument order, optional arguments, keyboard
shortcuts and the order of evaluation (EOS™). The guide's catalog has about
400 entries. Almost all of them are implemented; see
[`UNSURE_SYNTAX.md`](UNSURE_SYNTAX.md) for what is missing or unverified.

- **Calculator page:** entry line with history. Results are exact (CAS) or
  decimal (Ctrl+Enter or `►Decimal`). Settings follow the handheld's Document
  Settings: Float/Fix digits, Radian/Degree/Gradian,
  Normal/Scientific/Engineering, Real/Rectangular/Polar, Auto/Exact/Approximate,
  and Decimal/Hex/Binary base.
- **CAS:** `solve`, `cSolve`, `nSolve`, `zeros`, `factor`, `expand`,
  `completeSquare`, `propFrac`, `comDenom`, polynomial tools, `d`, `∫`, `limit`,
  `Σ`, `Π`, `taylor`, `series`, `tangentLine`, `fMax`/`fMin`, `deSolve`, `euler`,
  `rk23`, and more. The `|` operator works, e.g. `solve(sin(x)=1/2,x)|0≤x≤2π`.
- **Statistics:**
  - all distributions (normal, t, χ², F, binomial, Poisson, geometric, with
    their inverses)
  - all intervals and tests (z/t, 2-sample, proportions, χ² GOF/2-way, F, ANOVA,
    ANOVA2way, linear and multiple regression tests)
  - `OneVar`, `TwoVar`, and all regressions (linear, quadratic, cubic, quartic,
    power, exponential, logarithmic, sinusoidal, logistic, median-median,
    multiple)
  - results go into `stat.*` variables
- **Matrices & vectors:** `[1,2;3,4]`, `det`, `rref`, `^-1`, `ᵀ`, `eigVl`, `LU`,
  `QR`, `simult`, `dotP`, `crossP`, and more.
- **Lists & strings:** `seq`, `seqGen`, `countIf`, `sumIf`, `SortA`, `augment`,
  `left`/`mid`/`right`, `&`, `format`, `expr`, and more.
- **Finance:** `tvmN/I/PV/Pmt/FV`, `amortTbl`, `bal`, `ΣInt`, `ΣPrn`, `npv`,
  `irr`, `mirr`, `eff`, `nom`, `dbd`, plus a Finance Solver dialog.
- **Units & constants:** `3_m►_ft`, `_c`, `tmpCnv(100_°C,_°F)`.
- **Programming (TI-Basic):** `Define f(x)=Func … EndFunc` and `Prgm … EndPrgm`
  with `If`/`ElseIf`, `For`, `While`, `Loop`, `Try`, `Local`, `Return`,
  `Disp`, `Request`, `Text`, `Goto`/`Lbl`, `Lock`, and `getMode`/`setMode`.
  There is a Program Editor (Ctrl+E).
- **CX II graphics commands:** `DrawLine`, `DrawCircle`, `FillRect`,
  `PlotXY`, `SetColor`, `SetWindow`, and more, drawn on a 318×212 canvas.
- **Numbered menu** (Ctrl+M) with assistant dialogs. The submenu order of the
  statistics menus follows the official eGuide.
- **REPL** for the terminal.
- Planned: Graphs page (M4), Lists & Spreadsheet page (M5).

Command names and variable names are case-insensitive (`NORMCDF` = `normCdf`).
As on the handheld, the letters `e` and `i` are ordinary variables. Use `ℯ`
(`@e`) and `ⅈ` (`@i`), or turn on *Settings → Typed e and i are constants*.

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
  x=-2-3·ⅈ or x=-2+3·ⅈ
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

REPL commands: `:help [name]`, `:menu [5 5]`, `:mode auto|exact|approx`,
`:angle rad|deg|grad`, `:complex real|rectangular|polar`, `:digits N`, `:vars`,
`:clear`, `:quit`. Start a line with `~` to get a decimal result.

Keyboard shortcuts, as listed in the reference guide: `sqrt(` → `√(`,
`pi` → `π`, `@e` → `ℯ`, `@i` → `ⅈ`, `infinity` → `∞`, `<= >= /=` → `≤ ≥ ≠`,
`=:` → `→`, `=>` → `⇒`, `<=>` → `⇔`, `@>` → `►`, `@t` → `ᵀ`, `@d` → `°`,
`derivative(` → `d(`, `integral(` → `∫(`, `sumSeq(` → `Σ(`.

A small program:

```
Define fact(n)=Func:If n≤1 Then:Return 1:Else:Return n*fact(n-1):EndIf:EndFunc
fact(10)
```

## Development

```bash
uv run pytest
```

Project layout:

```
src/complex_calc/
  core/        tokenizer, parser (EOS hierarchy, TI-Basic), session (evaluator), formatting
  functions/   built-in functions: registry, elementary, cas, algebra, stats, stattests,
               intervals, regression, matrices, lists, finance, units, conversions,
               programming, draw, randoms, extras
  menus.py     numbered menu tree + wizard definitions (shared by GUI and REPL)
  cli/         REPL
  gui/         PySide6 GUI
tests/         pytest suite with reference values
```

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
