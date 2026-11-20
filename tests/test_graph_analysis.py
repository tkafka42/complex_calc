import math

import pytest
import sympy as sp

from complex_calc.analysis import graph_analysis as ga

x = ga.X


def test_zero():
    assert ga.zero(x**2 - 2, 0, 3).x == pytest.approx(math.sqrt(2))
    assert ga.zero(x**2, -1, 1).x == pytest.approx(0, abs=1e-6)       # touching zero
    with pytest.raises(ga.AnalysisError):
        ga.zero(x**2 + 1, -5, 5)


def test_extrema():
    p = ga.extremum(-(x - 1) ** 2 + 3, -5, 5, maximum=True)
    assert (p.x, p.y) == (pytest.approx(1, abs=1e-6), pytest.approx(3))
    p = ga.extremum(x**3 - 3 * x, 0, 3, maximum=False)
    assert p.x == pytest.approx(1, abs=1e-6) and p.y == pytest.approx(-2)


def test_intersection():
    p = ga.intersection(x**2, x + 2, 0, 5)
    assert (p.x, p.y) == (pytest.approx(2), pytest.approx(4))


def test_inflection():
    assert ga.inflection(x**3 - 3 * x**2, -5, 5).x == pytest.approx(1)


def test_derivative_and_integral():
    assert ga.derivative_at(x**3, 2) == pytest.approx(12)
    assert ga.integral(x**2, 0, 3) == pytest.approx(9)
    assert ga.integral(sp.exp(-x**2), -3, 3) == pytest.approx(1.7724146, rel=1e-6)


def test_numeric_domain():
    f = ga.numeric(sp.sqrt(x))
    values = f([-1, 4])
    assert math.isnan(values[0]) and values[1] == pytest.approx(2)
