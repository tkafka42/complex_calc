import io

import pytest
from matplotlib import mathtext

from complex_calc import i18n
from complex_calc.core.latex import input_latex, value_latex
from complex_calc.menus import GRAPHS_MENU, LISTS_MENU, MENU


@pytest.fixture(autouse=True)
def reset_language():
    yield
    i18n.set_language("en")


def test_translation_switch():
    assert i18n.tr("Statistics") == "Statistics"
    i18n.set_language("de")
    assert i18n.tr("Statistics") == "Statistik"
    assert i18n.tr("Distributions") == "Verteilungen"
    assert i18n.tr_error("Syntax error: Missing )") == "Syntaxfehler: Missing )"
    assert i18n.tr("normCdf") == "normCdf"          # command names never change


def test_all_menu_labels_translated():
    i18n.set_language("de")
    missing = set()

    def walk(items):
        for item in items:
            if i18n.tr(item.label) == item.label and not item.label[:1].isdigit() and item.label not in (
                    "Algebra", "ANOVA", "Integral", "Matrix", "Minimum", "Maximum", "Median", "Normal", "Polar",
                    "Modulo", "Binomial", "Norm", "Dimension", "Disp", "Request", "RequestStr", "Text", "Auto",
                    "dy/dx", "Define LibPub", "Define LibPriv", "Zoom – Standard", "Zoom – Quadrant 1") \
                    and not item.label.startswith(("Normal ", "t ", "χ²", "F ", "Binomial ", "Poisson ",
                                                   "Geometric ", "Inverse ", "z ", "If", "For", "While", "Loop", "Try")):
                missing.add(item.label)
            walk(item.children)

    walk(MENU)
    walk(GRAPHS_MENU)
    walk(LISTS_MENU)
    assert not missing


@pytest.mark.parametrize("source", ["1/2+3/4", "√(x^2+1)", "∫(x^2,x,0,3)", "d(x^3,x)", "Σ(k,k,1,n)",
                                    "limit(sin(x)/x,x,0)", "normCdf(-∞,520,500,10)", "Define f(x)=x^2/3",
                                    "x^2|x=3", "1/3►Decimal", "log(8,2)", "30°", "zInterval 15,100,25"])
def test_input_latex_renders(session, source):
    tex = input_latex(source, session)
    assert tex
    mathtext.math_to_image(f"${tex}$", io.BytesIO(), dpi=72, format="png")


@pytest.mark.parametrize("source", ["5/4", "√(8)", "solve(x^2-x-6=0,x)", "cSolve(x^2+4x+13=0,x)",
                                    "{1,2,3}*2", "@e^(2)", "normCdf(-∞,520,500,10)", "sumSeq(1/k^2,k,1,∞)"])
def test_value_latex_renders(session, source):
    tex = value_latex(session.evaluate(source), session.settings)
    assert tex
    mathtext.math_to_image(f"${tex}$", io.BytesIO(), dpi=72, format="png")
