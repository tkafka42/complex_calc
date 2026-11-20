# Unsure syntax / behaviour — please verify on a real device

## What is verified

- **Command names, argument order and optional arguments** follow the official
  *TI-Nspire™ CX CAS Reference Guide* (v6.4). All commands in its alphabetical
  listing are implemented except those listed under "Not implemented" below.
- **Keyboard shortcuts** (`@e`, `@i`, `@>`, `@t`, `=>`, `<=>`, `=:`,
  `derivative(`, `integral(`, `sumSeq(`, `deltaList(` …) and the **order of
  evaluation (EOS™)** follow the guide's chapters "Shortcuts for Entering Math
  Expressions" and "EOS Hierarchy". This includes:
  - `a(b+c)` is a function call. Write `a*(b+c)` to multiply. If `a` already
    holds a value, it is a multiplication.
  - The letters `e` and `i` are ordinary variables. Euler's number is `ℯ` or
    `@e`, the imaginary unit is `ⅈ` or `@i`. The setting "Typed e and i are
    constants" switches this off (this is not available on the handheld).
  - In Real mode (the default), `√(-4)` gives "Non-real result".
- **stat.* output variables** of all statistics commands follow the guide.
- **Submenu order** of *Distributions*, *Confidence Intervals*, *Stat Tests*
  and *Stat Calculations* follows the official TI-Nspire eGuide.
  `Menu → 5 Probability → 5 Distributions → 2 Normal Cdf` (and `3` Inverse
  Normal) is confirmed by official TI teacher notes.

## Menu numbering [menu]

Menu items marked `[?]` (REPL `:menu`) or `(?)` (GUI) are reconstructed from
memory:

- The top-level menus 1–9 (Actions, Number, Algebra, Calculus, Probability,
  Statistics, Matrix & Vector, Finance, Functions & Programs) are believed
  correct.
- Unsure are:
  - all items of *Actions*, *Number*, *Matrix & Vector*, *Finance*,
    *Functions & Programs*
  - *Algebra* items 5 and above
  - *Calculus* items 2 and 5 and above
  - *Probability → Random*
  - *Statistics → Stat Results / List Math / List Operations*
- **Changed in this version:** the earlier letters for the distributions were
  wrong. According to the eGuide, the order is:

  | Key | Item | Key | Item |
  |---|---|---|---|
  | 9 | F Pdf | E | Inverse Binomial w.r.t. N |
  | A | F Cdf | F | Poisson Pdf |
  | B | Binomial Pdf | G | Poisson Cdf |
  | C | Binomial Cdf | H | Geometric Pdf |
  | D | Inverse Binomial | I | Geometric Cdf |

  The eGuide lists neither Inverse χ² nor Inverse F in this menu.

## Wizard fields [wizard]

- The eGuide shows the *Normal Pdf* dialog (Lists & Spreadsheet) with the
  fields "X Value", "Mean", "Standard Deviation" and a "Draw" check box. This
  app uses "X Value", "μ", "σ", the way the Calculator dialog is remembered.
  Please check which labels your handheld shows.
- The regression dialogs use "X List", "Y List", "Save RegEqn To" (from the
  eGuide), then "Frequency List", "Category List" and "Include Categories".
- The Stat Test and Interval dialog labels (e.g. "μ0", "σ", "x̄", "n",
  "Alternate Hyp", "C Level", "Pooled") are not documented in the eGuide.
- The "Draw"/"Shade Area" check boxes are not implemented.

## Output format [output]

- **Result tables:** shown as `"Title" "z Interval"`, then
  `"CLower, CUpper" {lo,hi}` and the other stat variables. Stat Tests also
  show an `"Alternate Hyp"` row. The exact labels in the table are not given in
  the guide.
- **Number display:** Float 6 by default, and an approximate integer keeps its
  dot (`3.`). The switch point to scientific notation may differ.
- **Matrices** are shown as `[[1,2][3,4]]` and row vectors as `[1,2,3]`.
- **Complex solutions:** order such as `x=-2-3·ⅈ or x=-2+3·ⅈ` may differ.
- **Periodic solutions** are shown as `x=2·π·n1+π/6 or x=2·π·n1+5·π/6`. The
  device may combine them.
- **Inequalities** are shown as `-2≤x≤2`. The device may write
  `x≥-2 and x≤2`.
- **Exact `log(2)`** is shown as `ln(2)/ln(10)`, not `log₁₀(2)`.
- **Distribution functions** always return decimals.
- **`piecewise`/`when`** results are shown as `piecewise(…)`.
- **`propFrac(7/3)`** is shown as `1/3+2` (the value is correct, the term
  order is not).
- **`SinReg`:** a > 0 and c in (-π,π]. `Iterations` is ignored.
- **`ExpReg`/`PowerReg`:** r² and r refer to the linearised data.
- **`sin(Matrix)`, `ln(Matrix)` …** work element by element here. On the
  device they are matrix functions (`exp(Matrix)` is a real matrix
  exponential).

## Behaviour [dev]

- **`invBinomN`:** implemented as the smallest N with
  `binomCdf(N,p,0,NumSuccess) ≤ CumulativeProb`. Please check against the
  netball example in the guide.
- **`fMax`/`fMin`** return the global extremum candidates. For more
  complicated functions the device may return other forms.
- **`domain`, `dominantTerm`, `impDif`, `deSolve`** use SymPy. The output
  form can differ, for example `y=c1·sin(x)+c2·cos(x)`.
- **Draw commands:**
  - dotted/dashed pens are drawn solid
  - `UseBuffer`/`PaintBuffer` have no effect, because the drawing is shown
    after the program ends
  - `getKey()` always returns `""`
- **`Wait`** really pauses (max. 100 s).
- **Error messages** are this app's own wording. Error codes for `errCode`
  are approximate.

## Not implemented

- Libraries are plain text files in `~/.local/share/complex_calc/MyLib/*.txt`.
  They are not .tns documents.
- `RefreshProbeVars` (Vernier sensors).
- Hub commands (`Send`, `Get`, `GetStr`, `eval`).
- The Unit System setting (SI/Eng-US), Vector Format display, and the
  remaining entries of the units catalog. Common units and all constants from
  the guide are there.
- Apps not built: Geometry, Data & Statistics, Notes, Vernier DataQuest,
  Question and Python. Documents (.tns files) are not supported either.
- **Graphs app:**
  - the menu numbering is from memory
  - missing: equation, sequence, differential equation and inequality plots,
    Zoom – Box/User, and Geometry tools
- **Lists & Spreadsheet app:**
  - missing: Insert menu, Data Capture, and the Table menu
  - statistics results are written as text columns
