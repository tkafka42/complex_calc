"""Reference values checked against published tables / scipy."""

import math

import pytest

from complex_calc.core.errors import DomainError, ArgumentError


@pytest.mark.parametrize("expr, expected", [
    ("normCdf(-∞,520,500,10)", 0.97725),
    ("normCdf(-infinity,520,500,10)", 0.97725),
    ("normCdf(-1,1)", 0.682689),
    ("normCdf(1.96,∞)", 0.0249979),
    ("normPdf(0)", 0.398942),
    ("normPdf(500,500,10)", 0.0398942),
    ("invNorm(0.975)", 1.95996),
    ("invNorm(0.9,100,15)", 119.223),
    ("binomCdf(20,0.1,0,3)", 0.86705),
    ("binomCdf(20,0.1,3)", 0.86705),            # single upper bound: P(X≤3)
    ("binomPdf(10,0.5,5)", 0.246094),
    ("binomPdf(20,0.1,0)", 0.121577),
    ("tPdf(0,1)", 1 / math.pi),
    ("tCdf(-∞,2.228,10)", 0.975),
    ("tCdf(-2.0639,2.0639,24)", 0.95),
    ("invt(0.975,10)", 2.22814),
    ("invt(0.95,24)", 1.71088),
    ("poissPdf(3,2)", 0.224042),
    ("poissCdf(3,0,2)", 0.42319),
    ("χ²Cdf(0,3.841,1)", 0.95),
])
def test_reference_values(num, expr, expected):
    assert num(expr) == pytest.approx(expected, rel=2e-4)


def test_binom_pdf_list(session):
    values = session.evaluate("binomPdf(3,0.5)")
    assert [float(v) for v in values] == pytest.approx([0.125, 0.375, 0.375, 0.125])


def test_binom_pdf_listable(session):
    values = session.evaluate("binomPdf(10,0.5,{0,1,2})")
    assert len(values) == 3
    assert float(values[2]) == pytest.approx(0.0439453, rel=1e-5)


def test_case_insensitive(num):
    assert num("NORMCDF(-1,1)") == pytest.approx(num("normcdf(-1,1)"))
    assert num("BinomCdf(20,0.1,0,3)") == pytest.approx(0.86705, rel=1e-4)


def test_display_float6(calc):
    assert calc("normCdf(-∞,520,500,10)") == "0.97725"
    assert calc("binomCdf(20,0.1,0,3)") == "0.867047"


@pytest.mark.parametrize("expr, error", [
    ("binomPdf(10,2,1)", DomainError),
    ("normCdf(0,1,0,-1)", DomainError),
    ("invNorm(1.5)", DomainError),
    ("normCdf(0)", ArgumentError),
    ("tCdf(0,1,2,3)", ArgumentError),
])
def test_errors(session, expr, error):
    with pytest.raises(error):
        session.evaluate(expr)
