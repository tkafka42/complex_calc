import pytest
import sympy as sp

from complex_calc.core.errors import CalcSyntaxError


def test_csolve_reference(calc):
    result = calc("cSolve(x^2+4x+13=0,x)")
    assert set(result.split(" or ")) == {"x=-2+3·i", "x=-2-3·i"}


def test_solve_real_only(calc):
    assert calc("solve(x^2+4x+13=0,x)") == "false"
    assert calc("solve(x^2-x-6=0,x)") == "x=-2 or x=3"


def test_solve_inequality(calc):
    assert calc("solve(x^2>4,x)") == "x<-2 or x>2"
    assert calc("solve(x^2≤4,x)") == "-2≤x≤2"


def test_solve_system(calc):
    assert calc("solve(x+y=3 and x-y=1,{x,y})") == "x=2 and y=1"


def test_solve_with_condition(calc):
    assert calc("solve(x^2=4,x)|x>0") == "x=2"


def test_solve_numeric_fallback(calc):
    assert calc("solve(cos(x)=x,x)") == "x=0.739085"


def test_solve_with_guess(calc):
    assert calc("solve(x^2=2,x=1)") == "x=1.41421"


def test_solve_parameters(calc):
    assert calc("solve(a*x+b=0,x)") == "x=-b/a"


def test_nsolve(num):
    assert num("nSolve(cos(x)=x,x)") == pytest.approx(0.739085, rel=1e-6)
    assert num("nSolve(x^2=2,x,0,10)") == pytest.approx(2 ** 0.5)
    assert num("nSolve(x^2=2,x=-5)") == pytest.approx(-(2 ** 0.5))


def test_zeros(calc):
    assert calc("zeros(x^3-x,x)") == "{-1,0,1}"
    assert set(calc("cZeros(x^2+1,x)")[1:-1].split(",")) == {"-i", "i"}


def test_factor_expand(calc):
    assert calc("factor(x^2-5x+6)") == "(x-3)·(x-2)"
    assert calc("factor(x^2-2)") == "x^2-2"
    assert calc("factor(x^2-2,x)") == "(x-√(2))·(x+√(2))"
    assert calc("factor(360)") == "2^3·3^2·5"
    assert calc("expand((x+1)^3)") == "x^3+3·x^2+3·x+1"
    assert calc("cFactor(x^2+1,x)") == "(x-i)·(x+i)"


def test_approx_exact(calc):
    assert calc("approx(√(2))") == "1.41421"
    assert calc("exact(0.25)") == "1/4"
    assert calc("1/3+1/6") == "1/2"
    assert calc("0.5+1/3") == "0.833333"


def test_logs_and_exp(calc):
    assert calc("ln(e)") == "1"
    assert calc("log(8,2)") == "3"
    assert calc("log(1000)") == "3"
    assert calc("e^(0)") == "1"
    assert calc("ℯ^(ln(5))") == "5"
    assert calc("√(8)") == "2·√(2)"
    assert calc("sqrt(16)") == "4"


def test_trig_angle_modes(session, calc):
    assert calc("sin(π/6)") == "1/2"
    session.settings.angle = "deg"
    assert calc("sin(30)") == "1/2"
    assert calc("cos(60)") == "1/2"
    assert calc("sin⁻¹(1/2)") == "30"
    assert calc("arcsin(1)") == "90"
    session.settings.angle = "rad"
    assert calc("cos(60°)") == "1/2"


def test_variables_and_define(calc):
    assert calc("a:=5") == "5"
    assert calc("3→b") == "3"
    assert calc("4=:c") == "4"
    assert calc("a*b+c") == "19"
    assert calc("Define f(x)=x^2+1") == "Done"
    assert calc("f(3)") == "10"
    assert calc("define g(x,y)=x*y") == "Done"
    assert calc("g(2,a)") == "10"
    assert calc("h(t):=2t") == "Done"
    assert calc("h(4)") == "8"
    assert calc("DelVar a") == "Done"
    assert calc("a") == "a"
    assert calc("A:=7") == "7"
    assert calc("a") == "7"          # names are case-insensitive


def test_with_operator(calc):
    assert calc("x^2+1|x=3") == "10"
    assert calc("x*y|x=2 and y=5") == "10"


def test_implicit_multiplication(calc):
    assert calc("2x+3x") == "5·x"
    assert calc("2(3+4)") == "14"
    assert calc("(1+2)(3+4)") == "21"
    assert calc("xy") == "xy"        # multi-letter names are single variables


def test_calculus(calc, num):
    assert calc("derivative(x^3,x)") == "3·x^2"
    assert calc("∫(x^2,x,0,3)") == "9"
    assert calc("integral(x^2,x)") == "x^3/3"
    assert num("nDeriv(x^3,x=2)") == pytest.approx(12.000001)
    assert num("nDeriv(x^3,x)|x=2") == pytest.approx(12.000001)
    assert num("nInt(e^(-x^2),x,-∞,∞)") == pytest.approx(3.14159265 ** 0.5)
    assert calc("limit(sin(x)/x,x,0)") == "1"


def test_list_stats(calc, num):
    assert calc("mean({1,2,3,4})") == "5/2"
    assert num("stDevSamp({2,4,4,4,5,5,7,9})") == pytest.approx(2.13809, rel=1e-5)
    assert calc("stDevPop({2,4,4,4,5,5,7,9})") == "2"
    assert calc("median({5,1,3,2})") == "5/2"
    assert calc("mean({1,2,3},{1,1,2})") == "9/4"


def test_misc(calc):
    assert calc("5!") == "120"
    assert calc("nCr(5,2)") == "10"
    assert calc("abs(-3)") == "3"
    assert calc("1/0") == "undef"
    assert calc("{1,2,3}*2") == "{2,4,6}"
    assert calc("approx(3)") == "3."


@pytest.mark.parametrize("source", ["2+", "sin x", "(1+2", "3 4", "solve(x^2=4", "#"])
def test_syntax_errors(session, source):
    with pytest.raises(CalcSyntaxError):
        session.evaluate(source)


def test_error_message_has_pointer(session):
    entry = session.run("2+*3")
    assert entry.error
    assert "Syntax error" in entry.text
    assert "^" in entry.text
