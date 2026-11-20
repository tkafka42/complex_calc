import math

import pytest


def rows(result):
    return dict(result.rows)


def test_linreg(session):
    r = rows(session.evaluate("LinRegMx {1,2,3,4},{2,4,6,8}"))
    assert float(r["m"]) == pytest.approx(2)
    assert float(r["b"]) == pytest.approx(0, abs=1e-12)
    assert float(r["r"]) == pytest.approx(1)
    assert r["RegEqn"].text == "m*x+b"
    assert float(session.evaluate("stat.RegEqn(10)")) == pytest.approx(20)


def test_linreg_reference(session):
    # textbook example
    r = rows(session.evaluate("LinRegMx {1,2,3,4,5},{2,4,5,4,5}"))
    assert float(r["m"]) == pytest.approx(0.6)
    assert float(r["b"]) == pytest.approx(2.2)
    assert float(r["r²"]) == pytest.approx(0.6)


def test_quadreg(session):
    r = rows(session.evaluate("QuadReg {0,1,2,3,4},{1,2,5,10,17}"))
    assert float(r["a"]) == pytest.approx(1)
    assert float(r["b"]) == pytest.approx(0, abs=1e-9)
    assert float(r["c"]) == pytest.approx(1)
    assert float(r["R²"]) == pytest.approx(1)


def test_expreg(session):
    r = rows(session.evaluate("ExpReg {0,1,2,3},{3,6,12,24}"))
    assert float(r["a"]) == pytest.approx(3)
    assert float(r["b"]) == pytest.approx(2)
    assert r["RegEqn"].text == "a*(b)^x"


def test_sinreg(session):
    xs = [i * 0.5 for i in range(20)]
    ys = [2 * math.sin(1.3 * x + 0.4) + 1 for x in xs]
    lx = "{" + ",".join(f"{x:.6f}" for x in xs) + "}"
    ly = "{" + ",".join(f"{y:.6f}" for y in ys) + "}"
    r = rows(session.evaluate(f"SinReg {lx},{ly}"))
    assert float(r["a"]) == pytest.approx(2, rel=1e-3)
    assert float(r["b"]) == pytest.approx(1.3, rel=1e-3)
    assert float(r["c"]) == pytest.approx(0.4, abs=1e-2)
    assert float(r["d"]) == pytest.approx(1, rel=1e-3)


def test_regression_wizard_copyvar(session):
    session.evaluate("LinRegMx {1,2,3},{3,5,7},1: CopyVar stat.RegEqn,f1")
    assert float(session.evaluate("f1(10)")) == pytest.approx(21)
