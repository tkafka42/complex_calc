"""User-interface languages: English (default text in the code) and German.

    from complex_calc.i18n import tr, set_language
    tr("Statistics")  →  "Statistik" when German is active

Command names (normCdf, solve, …) are the same in every language, as on the
handheld. The German menu labels were translated for this app and have not
been compared with a German handheld OS (see UNSURE_SYNTAX.md).
"""

from __future__ import annotations

import locale
import os

LANGUAGES = {"en": "English", "de": "Deutsch"}
_current = "en"

DE: dict[str, str] = {
    # ---------------------------------------------------------- top-level menus
    "Actions": "Aktionen", "Number": "Zahl", "Algebra": "Algebra", "Calculus": "Analysis",
    "Probability": "Wahrscheinlichkeit", "Statistics": "Statistik", "Matrix & Vector": "Matrix & Vektor",
    "Finance": "Finanzen", "Functions & Programs": "Funktionen & Programme",
    # Actions
    "Define": "Definieren", "Recall Definition": "Definition abrufen", "Delete Variable": "Variable löschen",
    "Clear a-z...": "a-z löschen...", "Clear History": "Protokoll löschen", "Insert Comment": "Kommentar einfügen",
    "Library": "Bibliothek", "Refresh Libraries": "Bibliotheken aktualisieren",
    "Open Library Folder": "Bibliotheksordner öffnen", "Create Shortcuts": "Kurznamen erstellen",
    "Define LibPub": "Define LibPub", "Define LibPriv": "Define LibPriv", "Lock": "Sperren",
    "Lock Variable": "Variable sperren", "Unlock Variable": "Variable entsperren",
    "Get Lock Info": "Sperrstatus abfragen",
    # Number
    "Convert to Decimal": "In Dezimalzahl umwandeln", "Approximate to Fraction": "In Bruch approximieren",
    "Factor": "Faktorisieren", "Least Common Multiple": "Kleinstes gemeinsames Vielfaches",
    "Greatest Common Divisor": "Größter gemeinsamer Teiler", "Remainder": "Rest",
    "Fraction Tools": "Bruch-Werkzeuge", "Proper Fraction": "Echter Bruch", "Get Numerator": "Zähler",
    "Get Denominator": "Nenner", "Common Denominator": "Gemeinsamer Nenner", "Number Tools": "Zahlen-Werkzeuge",
    "Round": "Runden", "Integer Part": "Ganzzahliger Teil", "Fractional Part": "Nachkommateil",
    "Sign": "Vorzeichen", "Modulo": "Modulo", "Floor": "Abrunden (floor)", "Ceiling": "Aufrunden (ceiling)",
    "Complex Number Tools": "Werkzeuge für komplexe Zahlen", "Complex Conjugate": "Konjugiert komplex",
    "Real Part": "Realteil", "Imaginary Part": "Imaginärteil", "Polar Angle": "Polarwinkel",
    "Magnitude": "Betrag", "Convert to Polar": "In Polarform umwandeln",
    "Convert to Rectangular": "In kartesische Form umwandeln", "Prime Number Test": "Primzahltest",
    # Algebra
    "Solve": "Lösen", "Expand": "Ausmultiplizieren", "Zeros": "Nullstellen",
    "Complete the Square": "Quadratische Ergänzung", "Numerical Solve": "Numerisch lösen",
    "Solve System of Equations": "Gleichungssystem lösen",
    "Solve System of Linear Equations": "Lineares Gleichungssystem lösen",
    "Polynomial Tools": "Polynom-Werkzeuge", "Find Roots of Polynomial": "Nullstellen des Polynoms",
    "Real Roots of Polynomial": "Reelle Nullstellen", "Complex Roots of Polynomial": "Komplexe Nullstellen",
    "Remainder of Polynomial": "Rest der Polynomdivision", "Quotient of Polynomial": "Quotient der Polynomdivision",
    "GCD of Polynomials": "ggT von Polynomen", "Coefficients of Polynomial": "Koeffizienten des Polynoms",
    "Degree of Polynomial": "Grad des Polynoms", "Convert Expression": "Ausdruck umwandeln",
    "Convert to ln": "In ln umwandeln", "Convert to logbase": "In logbase umwandeln",
    "Convert to exp": "In exp umwandeln", "Convert to sin": "In sin umwandeln", "Convert to cos": "In cos umwandeln",
    "Trigonometry": "Trigonometrie", "Collect": "Zusammenfassen", "Complex": "Komplex", "Extract": "Extrahieren",
    "Left": "Links", "Right": "Rechts", "Piecewise Function": "Abschnittsweise Funktion",
    # Calculus
    "Derivative": "Ableitung", "Derivative at a Point": "Ableitung an einer Stelle", "Integral": "Integral",
    "Limit": "Grenzwert", "Sum": "Summe", "Product": "Produkt", "Function Minimum": "Funktionsminimum",
    "Function Maximum": "Funktionsmaximum", "Tangent Line": "Tangente", "Normal Line": "Normale",
    "Arc Length": "Bogenlänge", "Series": "Reihen", "Taylor Polynomial": "Taylorpolynom",
    "Generalized Series": "Verallgemeinerte Reihe", "Dominant Term": "Dominanter Term",
    "Differential Equation Solver": "Differentialgleichung lösen",
    "Implicit Differentiation": "Implizites Differenzieren", "Numerical Calculations": "Numerische Berechnungen",
    "Numerical Derivative at a Point": "Numerische Ableitung an einer Stelle",
    "Numerical Integral": "Numerisches Integral", "Numerical Function Minimum": "Numerisches Funktionsminimum",
    "Numerical Function Maximum": "Numerisches Funktionsmaximum",
    "Central Difference Quotient": "Zentraler Differenzenquotient",
    "Average Rate of Change": "Mittlere Änderungsrate",
    # Probability
    "Factorial (!)": "Fakultät (!)", "Permutations": "Permutationen", "Combinations": "Kombinationen",
    "Random": "Zufall", "Integer": "Ganzzahl", "Binomial": "Binomial", "Normal": "Normal",
    "Sample": "Stichprobe", "Seed": "Startwert", "Distributions": "Verteilungen",
    "Inverse Normal": "Inverse Normal", "Inverse t": "Inverse t", "Inverse Binomial": "Inverse Binomial",
    "Inverse Binomial with respect to N": "Inverse Binomial bzgl. N",
    # Statistics
    "Stat Calculations": "Statistische Berechnungen", "One-Variable Statistics": "Statistik mit einer Variablen",
    "Two-Variable Statistics": "Statistik mit zwei Variablen",
    "Linear Regression (mx+b)": "Lineare Regression (mx+b)", "Linear Regression (a+bx)": "Lineare Regression (a+bx)",
    "Median-Median Line": "Median-Median-Gerade", "Quadratic Regression": "Quadratische Regression",
    "Cubic Regression": "Kubische Regression", "Quartic Regression": "Regression 4. Grades",
    "Power Regression": "Potenzregression", "Exponential Regression": "Exponentielle Regression",
    "Logarithmic Regression": "Logarithmische Regression", "Sinusoidal Regression": "Sinusregression",
    "Logistic Regression (d=0)": "Logistische Regression (d=0)",
    "Logistic Regression (d≠0)": "Logistische Regression (d≠0)",
    "Multiple Linear Regression": "Multiple lineare Regression", "Stat Results": "Statistik-Ergebnisse",
    "List Math": "Listen-Mathematik", "Minimum": "Minimum", "Maximum": "Maximum", "Mean": "Mittelwert",
    "Median": "Median", "Sum of Elements": "Summe der Elemente", "Product of Elements": "Produkt der Elemente",
    "Sample Standard Deviation": "Stichproben-Standardabweichung", "Sample Variance": "Stichproben-Varianz",
    "Population Standard Deviation": "Populations-Standardabweichung", "Population Variance": "Populations-Varianz",
    "List Operations": "Listenoperationen", "Sort Ascending": "Aufsteigend sortieren",
    "Sort Descending": "Absteigend sortieren", "Cumulative Sum List": "Kumulierte Summenliste",
    "Fill": "Füllen", "Frequency": "Häufigkeit", "Difference List": "Differenzenliste",
    "Delete Void Elements": "Leere Elemente löschen", "Augment": "Verketten", "Create List": "Liste erstellen",
    "Sequence": "Folge", "Confidence Intervals": "Konfidenzintervalle", "Stat Tests": "Statistische Tests",
    "2-Sample z Interval": "2-Stichproben z-Intervall", "2-Sample t Interval": "2-Stichproben t-Intervall",
    "1-Prop z Interval": "1-Anteil z-Intervall", "2-Prop z Interval": "2-Anteile z-Intervall",
    "Linear Reg t Intervals": "Lineare Reg. t-Intervalle", "Multiple Reg Intervals": "Multiple Reg. Intervalle",
    "z Interval": "z-Intervall", "t Interval": "t-Intervall", "z Test": "z-Test", "t Test": "t-Test",
    "2-Sample z Test": "2-Stichproben z-Test", "2-Sample t Test": "2-Stichproben t-Test",
    "1-Prop z Test": "1-Anteil z-Test", "2-Prop z Test": "2-Anteile z-Test", "χ² GOF": "χ²-Anpassungstest",
    "χ² 2-way Test": "χ²-Unabhängigkeitstest", "2-Sample F Test": "2-Stichproben F-Test",
    "Linear Reg t Test": "Lineare Reg. t-Test", "Multiple Reg Tests": "Multiple Reg. Tests",
    "ANOVA": "ANOVA", "ANOVA 2-Way": "ANOVA zweifach",
    # Matrix & Vector
    "Create": "Erstellen", "Matrix": "Matrix", "Zero Matrix": "Nullmatrix", "Identity": "Einheitsmatrix",
    "Diagonal": "Diagonalmatrix", "Random Matrix": "Zufallsmatrix", "Construct Matrix": "Matrix konstruieren",
    "Submatrix": "Untermatrix", "Column Augment": "Spaltenweise verketten", "Transpose": "Transponieren",
    "Determinant": "Determinante", "Row-Echelon Form": "Zeilenstufenform",
    "Reduced Row-Echelon Form": "Reduzierte Zeilenstufenform", "Simultaneous": "Lineares System (simult)",
    "Norms": "Normen", "Norm": "Norm", "Row Norm": "Zeilennorm", "Column Norm": "Spaltennorm",
    "Dimensions": "Dimensionen", "Dimension": "Dimension", "Row Dimension": "Zeilenanzahl",
    "Column Dimension": "Spaltenanzahl", "Row Operations": "Zeilenoperationen", "Swap Rows": "Zeilen tauschen",
    "Add Row to Another": "Zeile zu anderer addieren", "Multiply Row": "Zeile multiplizieren",
    "Multiply Row & Add": "Zeile multiplizieren & addieren", "Element Operations": "Elementweise Operationen",
    "Dot Add": "Punkt-Addition", "Dot Subtract": "Punkt-Subtraktion", "Dot Multiply": "Punkt-Multiplikation",
    "Dot Divide": "Punkt-Division", "Dot Power": "Punkt-Potenz", "Advanced": "Erweitert", "Trace": "Spur",
    "Characteristic Polynomial": "Charakteristisches Polynom", "Eigenvalues": "Eigenwerte",
    "Eigenvectors": "Eigenvektoren", "LU Decomposition": "LU-Zerlegung", "QR Decomposition": "QR-Zerlegung",
    "Vector": "Vektor", "Unit Vector": "Einheitsvektor", "Cross Product": "Kreuzprodukt",
    "Dot Product": "Skalarprodukt",
    # Finance
    "Finance Solver...": "Finanzlöser...", "Finance Solver": "Finanzlöser", "TVM Functions": "TVM-Funktionen",
    "Number of Payments": "Anzahl der Zahlungen", "Interest Rate": "Zinssatz", "Present Value": "Barwert",
    "Payment Amount": "Ratenbetrag", "Future Value": "Endwert", "Amortization": "Tilgung",
    "Amortization Table": "Tilgungsplan", "Balance": "Restschuld", "Interest Sum": "Zinssumme",
    "Principal Sum": "Tilgungssumme", "Cash Flows": "Zahlungsströme", "Net Present Value": "Kapitalwert",
    "Internal Rate of Return": "Interner Zinsfuß", "Modified Internal Rate of Return": "Modifizierter interner Zinsfuß",
    "Interest Conversion": "Zinsumrechnung", "Nominal Interest Rate": "Nominalzins",
    "Effective Interest Rate": "Effektivzins", "Days between Dates": "Tage zwischen Daten",
    # Functions & Programs
    "Program Editor": "Programmeditor", "Control": "Steuerung", "I/O": "Ein-/Ausgabe", "Mode": "Modus",
    "Get Mode": "Modus abfragen", "Set Mode": "Modus setzen",
    # Graphs page
    "Delete All Functions": "Alle Funktionen löschen", "Hide/Show Function List": "Funktionsliste ein/aus",
    "View": "Ansicht", "Hide/Show Entry Line": "Eingabezeile ein/aus", "Show/Hide Grid": "Gitter ein/aus",
    "Show/Hide Axes": "Achsen ein/aus", "Graph Entry/Edit": "Graph-Eingabe/Bearbeitung", "Function": "Funktion",
    "Equation": "Gleichung", "Parametric": "Parameterdarstellung", "Polar": "Polar",
    "Scatter Plot": "Streudiagramm", "Diff Eq": "Differentialgleichung", "Window/Zoom": "Fenster/Zoom",
    "Window Settings...": "Fenstereinstellungen...", "Window Settings": "Fenstereinstellungen",
    "Zoom – Box": "Zoom – Rechteck", "Zoom – In": "Zoom – Vergrößern", "Zoom – Out": "Zoom – Verkleinern",
    "Zoom – Standard": "Zoom – Standard", "Zoom – Quadrant 1": "Zoom – Quadrant 1",
    "Zoom – User": "Zoom – Benutzer", "Zoom – Trig": "Zoom – Trigonometrie", "Zoom – Data": "Zoom – Daten",
    "Zoom – Fit": "Zoom – Anpassen", "Zoom – Square": "Zoom – Quadratisch", "Graph Trace": "Graph-Spur",
    "Analyze Graph": "Graph analysieren", "Zero": "Nullstelle", "Intersection": "Schnittpunkt",
    "Inflection": "Wendepunkt", "dy/dx": "dy/dx", "Table": "Tabelle", "Split-screen Table": "Geteilte Tabelle",
    "Remove Table": "Tabelle entfernen", "Edit Table Settings...": "Tabelleneinstellungen...",
    "Geometry": "Geometrie", "Settings": "Einstellungen", "Axes: linear": "Achsen: linear",
    "Axes: semi-log (y logarithmic)": "Achsen: einfach-logarithmisch (y)",
    "Axes: semi-log (x logarithmic)": "Achsen: einfach-logarithmisch (x)",
    "Axes: log-log": "Achsen: doppelt-logarithmisch",
    # Lists page
    "Clear Column Data": "Spaltendaten löschen", "Delete Column Name": "Spaltenname löschen",
    "Insert": "Einfügen", "Data": "Daten", "Generate Sequence": "Folge erzeugen", "Data Capture": "Datenerfassung",
    "Quick Graph": "Schnellgraph", "Sort": "Sortieren", "Ascending": "Aufsteigend", "Descending": "Absteigend",
    # ---------------------------------------------------------- wizard fields
    "Stats": "Statistikwerte", "Data Input Method": "Dateneingabemethode", "Lower Bound": "Untere Grenze",
    "Upper Bound": "Obere Grenze", "X Value": "X-Wert", "Area": "Fläche", "Deg of Freedom, df": "Freiheitsgrade, df",
    "Numerator df": "Zähler-df", "Denominator df": "Nenner-df", "Num Trials, n": "Anzahl Versuche, n",
    "Prob Success, p": "Erfolgswahrsch., p", "Cumulative Probability": "Kumulierte Wahrscheinlichkeit",
    "Num Success, k": "Anzahl Erfolge, k", "C Level": "C-Niveau", "List": "Liste", "List 1": "Liste 1",
    "List 2": "Liste 2", "List 3": "Liste 3", "List 4": "Liste 4", "List 5": "Liste 5",
    "Frequency List": "Häufigkeitsliste", "Frequency List 1": "Häufigkeitsliste 1",
    "Frequency List 2": "Häufigkeitsliste 2", "Category List": "Kategorieliste",
    "Include Categories": "Kategorien einschließen", "Alternate Hyp": "Alternativhypothese", "Pooled": "Gepoolt",
    "No": "Nein", "Yes": "Ja", "Successes, x": "Erfolge, x", "Successes, x1": "Erfolge, x1",
    "Successes, x2": "Erfolge, x2", "Observed List": "Beobachtete Liste", "Expected List": "Erwartete Liste",
    "Observed Matrix": "Beobachtete Matrix", "X List": "X-Liste", "Y List": "Y-Liste", "X1 List": "X1-Liste",
    "X2 List": "X2-Liste", "X3 List": "X3-Liste", "Save RegEqn To": "RegEqn speichern unter",
    "Iterations": "Iterationen", "Period": "Periode", "Interval": "Intervall", "Slope": "Steigung",
    "Response": "Antwortwert", "X Value (Response only)": "X-Wert (nur Antwortwert)", "Solve for": "Lösen nach",
    "Payment at": "Zahlung am", "END": "ENDE", "BEGIN": "ANFANG",
    # ---------------------------------------------------------- application UI
    "Calculator": "Calculator", "Graphs": "Graphs", "Lists & Spreadsheet": "Lists & Spreadsheet",
    "Menu": "Menü", "Enter": "Enter", "Catalog": "Katalog", "Templates": "Vorlagen", "File": "Datei",
    "Help": "Hilfe", "Quit": "Beenden", "Program Editor…": "Programmeditor…", "Keyboard Shortcuts": "Tastenkürzel",
    "About": "Über", "Language": "Sprache", "Display Digits": "Angezeigte Ziffern", "Angle": "Winkel",
    "Radian": "Bogenmaß", "Degree": "Grad", "Gradian": "Neugrad", "Exponential Format": "Exponentialformat",
    "Scientific": "Wissenschaftlich", "Engineering": "Technisch", "Real or Complex Format": "Reell oder komplex",
    "Real": "Reell", "Rectangular": "Kartesisch", "Calculation Mode": "Berechnungsmodus", "Auto": "Auto",
    "Exact": "Exakt", "Approximate": "Approximiert", "Base": "Basis", "Decimal": "Dezimal", "Hex": "Hex",
    "Binary": "Binär", "Typed e and i are constants (not on the handheld)":
        "Getipptes e und i sind Konstanten (nicht wie am Gerät)",
    "Insert Page": "Seite einfügen", "New Calculator page": "Neue Calculator-Seite",
    "New Graphs page": "Neue Graphs-Seite", "New Lists & Spreadsheet page": "Neue Lists & Spreadsheet-Seite",
    "Close Page": "Seite schließen",
    "Enter an expression (Ctrl+M: menu, Ctrl+K: catalog)": "Ausdruck eingeben (Strg+M: Menü, Strg+K: Katalog)",
    "Evaluate approximately (Ctrl+Enter)": "Näherungsweise berechnen (Strg+Enter)",
    "Numbered command menu (Ctrl+M)": "Nummeriertes Befehlsmenü (Strg+M)",
    "Click to paste into the entry line": "Klicken, um in die Eingabezeile einzufügen",
    "Ctrl+M opens the menu · Ctrl+K catalog · Ctrl+Enter gives a decimal result":
        "Strg+M Menü · Strg+K Katalog · Strg+Enter liefert eine Dezimalzahl",
    "Search": "Suchen", "Insert into entry line": "In Eingabezeile einfügen", "Close": "Schließen",
    "Restart to apply the language completely?": "Neu starten, um die Sprache vollständig zu übernehmen?",
    "Restart now": "Jetzt neu starten", "Later": "Später",
    "Functions & plots": "Funktionen & Plots",
    "Type a function and press Enter. Menu (Ctrl+M) → 6 Analyze Graph.":
        "Funktion eingeben und Enter drücken. Menü (Strg+M) → 6 Graph analysieren.",
    "e.g. x^2-3   or   sin(x)   (Enter graphs the function)":
        "z. B. x^2-3   oder   sin(x)   (Enter zeichnet die Funktion)",
    "Click the lower bound": "Untere Grenze anklicken", "Click the upper bound.": "Obere Grenze anklicken.",
    "Click the point": "Punkt anklicken", "(on the graph).": "(auf dem Graphen).",
    "Please graph a function first.": "Bitte zuerst eine Funktion zeichnen.", "Select graph:": "Graph wählen:",
    "Second graph": "Zweiter Graph",
    "Row 'name': list name (shared with the Calculator).  Row '◆': column formula, e.g. =seq(n^2,n,1,10).  Cells: values or =a1*2.":
        "Zeile 'name': Listenname (mit dem Calculator geteilt).  Zeile '◆': Spaltenformel, z. B. =seq(n^2,n,1,10).  Zellen: Werte oder =a1*2.",
    "Lists: {1,2,3} or a list variable name.": "Listen: {1,2,3} oder ein Listenname.",
    "∞ may be typed as inf.": "∞ kann als infinity eingegeben werden.",
    "not supported": "nicht unterstützt", "optional": "optional",
    "Name": "Name", "Type": "Typ", "Parameters": "Parameter", "Function (Func)": "Funktion (Func)",
    "Program (Prgm)": "Programm (Prgm)", "Check Syntax & Store": "Syntax prüfen && speichern",
    "Ctrl+B: Check Syntax & Store": "Strg+B: Syntax prüfen & speichern", "Please enter a name.": "Bitte einen Namen eingeben.",
    "Variable or function name:": "Variablen- oder Funktionsname:",
    "Finished — press any key or close the window": "Fertig – beliebige Taste drücken oder Fenster schließen",
    "Graphics": "Grafik",
    # ---------------------------------------------------------- error kinds
    "Syntax error": "Syntaxfehler", "Argument error": "Argumentfehler", "Domain error": "Bereichsfehler",
    "Undefined": "Nicht definiert", "Error": "Fehler",
}


def detect_language() -> str:
    for key in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(key, "")
        if value:
            return "de" if value.lower().startswith("de") else "en"
    try:
        code = locale.getlocale()[0] or ""
    except ValueError:
        code = ""
    return "de" if code.lower().startswith("de") else "en"


def set_language(code: str) -> None:
    global _current
    _current = code if code in LANGUAGES else "en"


def language() -> str:
    return _current


def tr(text: str) -> str:
    if _current == "de":
        return DE.get(text, text)
    return text


def tr_error(message: str) -> str:
    """Translate the 'Kind:' prefix of an error message."""
    if _current != "de":
        return message
    head, sep, rest = message.partition(":")
    return tr(head) + sep + rest if sep and head in DE else message
