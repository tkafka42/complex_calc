# Unsure syntax / behaviour — please verify on a real device

Everything below was implemented from memory of the official reference guide
and the handheld menus, **not** from the device itself. Items here may differ
from the real handheld. If you check one, update the code and remove the entry.

Legend: **[menu]** menu numbering, **[syntax]** command syntax/argument order,
**[output]** display format, **[dev]** deliberate deviation of this app.

## Output format

- **[output]** `zInterval` / `tInterval` table: the first row is shown as
  `"Title" "z Interval"`, then a combined row `"CLower, CUpper" {lo,hi}`, then
  `"x̄"`, `"ME"`, (`"sx"` data input only), `"n"`, `"σ"` (z) or
  `"df"`, `"sx"`, `"n"` (t). Not sure whether the device shows CLower/CUpper as
  one combined row or as two rows.
- **[output]** Default display is Float 6, and an approximate integer is shown
  with a trailing dot (`3.`). Very small/large numbers are shown as `1.2E-5`.
  The exact switch point to scientific notation may differ.
- **[output]** Order of solutions: `cSolve(x^2+4x+13=0,x)` shows
  `x=-2-3·i or x=-2+3·i`. The device may list `+` first.
- **[output]** Periodic solutions: `solve(sin(x)=0,x)` gives
  `x=2·π·n1 or x=2·π·n1+π`. The device simplifies this to `x=n1·π`.
- **[output]** Inequalities: `solve(x^2≤4,x)` shows `-2≤x≤2`. The device may
  show `x≥-2 and x≤2`.
- **[output]** `log(2)` (exact) is shown as `ln(2)/ln(10)`, not as `log₁₀(2)`.
- **[output]** Distribution functions (`normCdf`, `binomPdf`, …) always return
  decimals, even in Exact mode.
- **[output]** `LinRegMx` table rows: `RegEqn "m*x+b"`, `m`, `b`, `r²`, `r`,
  `Resid`. `QuadReg` uses capital `R²`. `ExpReg` shows `RegEqn "a*(b)^x"`.
- **[output]** `ExpReg`: `r²`/`r` are computed for the linearised data
  (ln y vs x). `Resid` uses the original y values. The device might use the
  linearised residuals.
- **[output]** `SinReg`: the amplitude `a` is made positive and `c` is reduced
  to (-π, π]. The device may return an equivalent but different `a`/`c` pair.
  `Iterations` is accepted but ignored (the fit always runs to convergence).
- **[output]** `OneVar` row labels (`"sx := sn-1x"`, `"σx := σnx"`, `"Q₁X"`,
  `"SSX := Σ(x-x̄)²"`).

## Syntax

- **[syntax]** `factor(expr, var)` also splits off irrational real factors:
  `factor(x^2-2,x)` → `(x-√(2))·(x+√(2))`, while `factor(x^2-2)` stays
  `x^2-2`. This is believed to match the device.
- **[syntax]** `invNorm(Area[,μ[,σ]])`: newer OS versions may also take a
  *Tail* argument (Left/Center/Right). It is not implemented here.
- **[syntax]** `zInterval`/`tInterval`: a CLevel above 1 (e.g. `95`) is read
  as a percentage. The device may reject it.
- **[syntax]** Derivative: on the handheld it is a template (`d/dx`). Here you
  type `derivative(Expr,Var[,Order])`. Integral: `∫(` or `integral(`.
- **[syntax]** `nDeriv(Expr,Var=Value[,H])` uses the central difference with
  H = 0.001 by default.
- **[syntax]** Inverse trig functions: `sin⁻¹(`, also `arcsin(` / `asin(`.

## Deliberate deviations [dev]

- On the handheld, `e` and `i` typed as letters are ordinary variables, and
  Euler's number/the imaginary unit are the special keys `ℯ` and `ⅈ`. Here
  `e` and `i` **are** Euler's number and the imaginary unit (easier on a PC
  keyboard). `ℯ`, `ⅈ` and `@i` work too.
- An undefined name followed by `(` is implicit multiplication (`a(x+1)` =
  `a·(x+1)`). On the handheld it may be treated as a call to an undefined
  function.
- `x:=5` shows `5`, `Define x=5` shows `Done`, `Define f(x)=…` shows `Done`.
- Error messages are written by this app and do not copy the handheld texts.

## Menu numbering [menu]

Paths marked `[?]` in `:menu` (REPL) or with "?" in the GUI. Main uncertain
areas:

- Menu 1 *Actions* items 2–8.
- Menu 2 *Number*: complete numbering, *Number Tools* and
  *Complex Number Tools* submenus.
- Menu 3 *Algebra*: items 5–C (Complete the Square, Numerical Solve, Solve
  System, Polynomial Tools, Fraction Tools, Convert Expression, Trigonometry,
  Complex). Inside *Complex*: 1 Solve, 2 Factor, 3 Zeros.
- Menu 4 *Calculus*: items 2 and 5–F, and *Numerical Calculations*
  (1 Numerical Derivative at a Point, 2 Numerical Integral).
- Distributions (Menu 5 → 5 and Menu 6 → 5): items 1–C are believed correct.
  The letters **D–K** (Binomial Pdf = D, Binomial Cdf = E, Inverse Binomial = F,
  Inverse Binomial w.r.t. N = G, Poisson Pdf = H, Poisson Cdf = I,
  Geometric Pdf = J, Geometric Cdf = K) are unsure, because OS versions added
  entries over time.

Paths believed correct: `6 → 5 → 2` Normal Cdf, `6 → 6 → 1` z Interval,
`6 → 6 → 2` t Interval, `6 → 1 → 3` Linear Regression (mx+b),
`6 → 1 → 6` Quadratic, `6 → 1 → A` Exponential, `6 → 1 → C` Sinusoidal,
`6 → 3 → …` List Math, `3 → 1/2/3/4` Solve/Factor/Expand/Zeros.

## Wizard fields

Field labels and their order come from memory, e.g. *Normal Cdf*: Lower Bound,
Upper Bound, μ, σ. *Binomial Cdf*: Num Trials n, Prob Success p, Lower Bound,
Upper Bound. *z Interval (Stats)*: σ, x̄, n, C Level. *t Interval (Stats)*:
x̄, sx, n, C Level. Regressions: X List, Y List, Save RegEqn to,
Frequency List, Category List, Include Categories. Category fields are shown
but disabled. Default values (e.g. -∞/∞ for the bounds) may differ.
