# Complex Calc

A CAS calculator for Linux that feels like the TI-Nspire™ CX CAS, so you can
practise school maths on your PC when the real thing isn't around.

It **uses command syntax similar to the TI-Nspire™ CX CAS**: same command
names, same argument order, and even the same numbered menu paths. So
`normCdf(-∞,520,500,10)` just works, and *Menu → 5 → 5 → 2* still gets you to
Normal Cdf. The looks are its own, though.

> **Disclaimer:** Not affiliated with, endorsed by or sponsored by Texas
> Instruments. TI-Nspire is a trademark of Texas Instruments Incorporated. No TI
> firmware, OS files, ROMs, graphics, icons or fonts are used or included.

## Why this exists

I was studying for a maths exam, didn't have my calculator with me, and found
out there's no open-source option for Linux that works like the handheld.
That annoyed me, so I built one together with Claude (an AI assistant).

Full honesty: this is mostly vibe-coded. I set the direction, wrote the
requirements and tested it, but Claude wrote most of the code. If you spot
something that behaves differently from the real device, please open an issue
or a PR. That kind of feedback helps the most.

## What it can do

The command set follows the official *TI-Nspire™ CX CAS Reference Guide*
(v6.4). That's about 400 commands, and almost all of them are in. The few
gaps, plus everything that couldn't be checked against a real device, are
listed in [`UNSURE_SYNTAX.md`](UNSURE_SYNTAX.md).

- **Calculator:** exact (CAS) or decimal results, with 2D math display
  (fractions, roots, ∫, Σ, matrices). Also has a history, a catalog (Ctrl+K),
  templates (Ctrl+T) and syntax help while you type.
- **CAS:** `solve`, `cSolve`, `nSolve`, `factor`, `expand`, `d`, `∫`, `limit`,
  `taylor`, `deSolve`, `fMax`/`fMin`, and the `|` operator, e.g.
  `solve(sin(x)=1/2,x)|0≤x≤2π`.
- **Statistics:**
  - all distributions (normal, t, χ², F, binomial, Poisson, geometric)
  - all confidence intervals and tests (z, t, 2-sample, proportions, χ², F,
    ANOVA)
  - every regression (linear, quadratic, cubic, quartic, power, exponential,
    logarithmic, sinusoidal, logistic and more)
  - results land in `stat.*` variables
- **Matrices, lists, strings, finance (TVM, amortization), units.**
- **TI-Basic:** `Func`/`Prgm` with `If`, `For`, `While`, `Try`, `Local`,
  `Disp`, `Request` and friends. Comes with a program editor (Ctrl+E) and the
  CX II draw commands.
- **Graphs:**
  - function, parametric, polar and scatter plots
  - zoom and trace
  - Analyze Graph (zero, min, max, intersection, inflection, dy/dx, integral):
    click the bounds like on the device
  - value table
  - linear and logarithmic axes
- **Lists & Spreadsheet:** named columns are list variables shared with the
  Calculator. Supports column formulas like `=seq(n^2,n,1,10)`, statistics
  wizards, sorting and Quick Graph.
- **Pages:** "1.1 Calculator", "1.2 Graphs" … all share the same variables.
  Add a page with Ctrl+I.
- **Languages:** English and German (*Settings → Language*, or
  `complex-calc --lang de`).
- **Terminal REPL** for when you don't want a window.

Just like on the handheld, `e` and `i` are normal variables. Use `@e` / `@i`
(or the ℯ / ⅈ buttons) for Euler's number and the imaginary unit, or flip the
switch in the settings if that bugs you.

## Install & run

You need Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/tkafka42/complex_calc.git
cd complex_calc
uv run complex-calc-gui    # the app (Wayland native, X11 works too)
uv run complex-calc        # terminal version
```

Want it in your app launcher?

```bash
uv tool install .
install -Dm644 data/complex_calc.desktop ~/.local/share/applications/complex_calc.desktop
install -Dm644 data/complex_calc.svg ~/.local/share/icons/hicolor/scalable/apps/complex_calc.svg
```

After pulling updates, run `uv tool install --reinstall .` again.

## Quick taste

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

Handy shortcuts:

| Keys | What it does |
|---|---|
| Ctrl+M | numbered menu |
| Ctrl+K | catalog |
| Ctrl+T | templates |
| Ctrl+Enter | decimal result |
| Ctrl+I | new page |
| Ctrl+E | program editor |

The keyboard shortcuts from the reference guide work too: `@e`, `@i`, `@>`
(►), `=>`, `<=`, `infinity`, `sqrt(` and so on. In the REPL, `:help` shows
everything.

## Hacking on it

```bash
uv run pytest
```

- `src/complex_calc/core/`: parser, evaluator and formatting
- `src/complex_calc/functions/`: all the commands
- `src/complex_calc/gui/`: the PySide6 app
- `src/complex_calc/menus.py`: the numbered menus and wizards

PRs welcome. Corrections from people who own a real Nspire are especially
welcome.

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
