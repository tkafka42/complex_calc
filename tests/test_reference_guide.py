"""Tests for commands added from the reference guide (matrices, lists, strings,
algebra, calculus, statistics tests, regressions, finance, programs, units)."""

import pytest

from complex_calc.core.errors import CalcError, DomainError


def rows(result):
    return dict(result.rows)


# ------------------------------------------------------------------ syntax (EOS)


@pytest.mark.parametrize("expr, expected", [
    ("2^3^2", "512"),                  # right to left
    ("-3^2", "-9"),                    # negation after power
    ("4^3!", "4096"),                  # post operator before power
    ("5%", "1/20"),
    ("0b101+0hF", "20"),
    ("2.5E2", "250."),
    ("\"ab\"&\"cd\"", "\"abcd\""),
    ("5 xor 3", "6"),
    ("2>1 ⇒ 1>2", "false"),
    ("2>1 => 1>2", "false"),
    ("true <=> true", "true"),
    ("not 2>3", "true"),
])
def test_eos(calc, expr, expected):
    assert calc(expr) == expected


def test_function_call_vs_multiplication(calc):
    # reference guide: a(b+c) is the function a, not a·(b+c)
    assert calc("a(b+c)") == "a(b+c)"
    assert calc("a*(b+c)") == "a·(b+c)"
    calc("k:=3")
    assert calc("k(2)") == "6"        # defined value → multiplication


def test_e_and_i_letters(session, calc):
    assert calc("e") == "e"           # the letter e is a variable
    assert calc("@e") == "ℯ"
    assert calc("ℯ^(1)") == "ℯ"
    assert calc("@i^2") == "-1"
    session.settings.letters_are_constants = True
    assert calc("ln(e)") == "1"


def test_real_mode(session, calc):
    with pytest.raises(DomainError):
        session.evaluate("√(-4)")
    assert calc("√(-4)+0@i") == "2·ⅈ"
    session.settings.complex_format = "rectangular"
    assert calc("√(-4)") == "2·ⅈ"


def test_void_arguments(num):
    assert num("bal(3,60,10,5000,,,12,12)") == pytest.approx(4804.67)


# ------------------------------------------------------------------ matrices


@pytest.mark.parametrize("expr, expected", [
    ("[1,2;3,4]", "[[1,2][3,4]]"),
    ("[[1,2][3,4]]", "[[1,2][3,4]]"),
    ("[1,2,3]", "[1,2,3]"),
    ("[1,2;3,4]^-1", "[[-2,1][3/2,-1/2]]"),
    ("det([1,2;3,4])", "-2"),
    ("[1,2;3,4]*[5;6]", "[[17][39]]"),
    ("[1,2;3,4]ᵀ", "[[1,3][2,4]]"),
    ("[1,2;3,4]@t", "[[1,3][2,4]]"),
    ("5+[1,2;3,4]", "[[6,2][3,9]]"),        # adds to the diagonal
    ("5 .+[1,2;3,4]", "[[6,7][8,9]]"),       # every element
    ("[1,2;3,4].*[1,2;3,4]", "[[1,4][9,16]]"),
    ("rref([1,2,3;4,5,6])", "[[1,0,-1][0,1,2]]"),
    ("identity(2)", "[[1,0][0,1]]"),
    ("dotP({1,2,3},{4,5,6})", "32"),
    ("crossP([1,0,0],[0,1,0])", "[0,0,1]"),
    ("simult([1,2;3,4],[1;-1])", "[[-3][2]]"),
    ("trace([1,2;3,4])", "5"),
    ("dim([1,2,3;4,5,6])", "{2,3}"),
    ("charPoly([1,2;3,4],x)", "x^2-5·x-2"),
    ("rowSwap([1,2;3,4],1,2)", "[[3,4][1,2]]"),
    ("subMat([1,2,3;4,5,6;7,8,9],2,2)", "[[5,6][8,9]]"),
    ("diag({1,2})", "[[1,0][0,2]]"),
    ("constructMat(i+j,i,j,2,2)", "[[2,3][3,4]]"),
    ("augment([1;2],[3;4])", "[[1,3][2,4]]"),
    ("colAugment([1,2],[3,4])", "[[1,2][3,4]]"),
    ("list►mat({1,2,3,4},2)", "[[1,2][3,4]]"),
    ("mat►list([1,2;3,4])", "{1,2,3,4}"),
])
def test_matrices(calc, expr, expected):
    assert calc(expr) == expected


def test_matrix_subscripts(calc):
    calc("m:=[1,2;3,4]")
    assert calc("m[2,1]") == "3"
    calc("9→m[1,2]")
    assert calc("m") == "[[1,9][3,4]]"


def test_eigenvalues(session):
    values = sorted(float(v) for v in session.evaluate("eigVl([2,0;0,3])"))
    assert values == pytest.approx([2, 3])


# ------------------------------------------------------------------ lists & strings


@pytest.mark.parametrize("expr, expected", [
    ("seq(n^2,n,1,5)", "{1,4,9,16,25}"),
    ("seq(n,n,10,1,-3)", "{10,7,4,1}"),
    ("cumulativeSum({1,2,3})", "{1,3,6}"),
    ("ΔList({1,4,9,16})", "{3,5,7}"),
    ("deltaList({1,4,9,16})", "{3,5,7}"),
    ("augment({1,2},{3})", "{1,2,3}"),
    ("countIf({1,3,5,7,9},?<5)", "2"),
    ("countIf({1,3,3,7},3)", "2"),
    ("sumIf({1,2,3,4},?>2)", "7"),
    ("frequency({1,2,3,4,5,6},{2,4})", "{2,2,2}"),
    ("left({1,2,3,4},2)", "{1,2}"),
    ("right(x=3)", "3"),
    ("mid({1,2,3,4,5},2,3)", "{2,3,4}"),
    ("shift({1,2,3},1)", "{2,3,undef}"),
    ("rotate({1,2,3},1)", "{2,3,1}"),
    ("newList(3)", "{0,0,0}"),
    ("seqGen(u(n-1)*2,n,u,{1,5},{1})", "{1,2,4,8,16}"),
    ("dim(\"hello\")", "5"),
    ("left(\"hello\",2)", "\"he\""),
    ("right(\"hello\",3)", "\"llo\""),
    ("mid(\"hello\",2,3)", "\"ell\""),
    ("string(1/3)", "\"1/3\""),
    ("expr(\"2+3\")", "5"),
    ("inString(\"hello\",\"ll\")", "3"),
    ("char(65)", "\"A\""),
    ("ord(\"A\")", "65"),
    ("format(3.14159,\"F2\")", "\"3.14\""),
    ("format(1234.5,\"S2\")", "\"1.23E3\""),
    ("shift(\"abc\",1)", "\"bc \""),
    ("rotate(\"abcd\",-1)", "\"dabc\""),
])
def test_lists_and_strings(calc, expr, expected):
    assert calc(expr) == expected


def test_sort_commands(calc):
    calc("a:={3,1,2}")
    calc("b:={30,10,20}")
    calc("SortA a,b")
    assert calc("a") == "{1,2,3}"
    assert calc("b") == "{10,20,30}"
    calc("SortD a")
    assert calc("a") == "{3,2,1}"
    calc("Fill 7,a")
    assert calc("a") == "{7,7,7}"


# ------------------------------------------------------------------ algebra & calculus


@pytest.mark.parametrize("expr, expected", [
    ("polyCoeffs(3x^2+2x+1,x)", "{3,2,1}"),
    ("polyDegree(x^3+x,x)", "3"),
    ("polyRoots(x^2-5x+6,x)", "{2,3}"),
    ("polyRoots({1,-5,6})", "{2,3}"),
    ("cPolyRoots({1,0,1})", "{-ⅈ,ⅈ}"),
    ("polyEval({1,2,3},2)", "11"),
    ("polyQuotient(x^2-1,x-1,x)", "x+1"),
    ("polyRemainder(x^2+1,x-1,x)", "2"),
    ("polyGcd(x^2-1,x^2+2x+1)", "x+1"),
    ("completeSquare(x^2+6x+5,x)", "(x+3)^2-4"),
    ("linSolve(x+y=3 and x-y=1,{x,y})", "{2,1}"),
    ("fMax(-x^2+4x,x)", "x=2"),
    ("fMin(x^2-4x,x)", "x=2"),
    ("tangentLine(x^2,x,1)", "2·x-1"),
    ("taylor(ℯ^(x),x,3)", "x^3/6+x^2/2+x+1"),
    ("Σ(k,k,1,100)", "5050"),
    ("sumSeq(1/k^2,k,1,∞)", "π^2/6"),
    ("Π(k,k,1,5)", "120"),
    ("d(x^3,x,2)", "6·x"),
    ("derivative(sin(x),x)", "cos(x)"),
    ("deSolve(y'=y,x,y)", "y=c1·ℯ^x"),
    ("deSolve(y'=y and y(0)=2,x,y)", "y=2·ℯ^x"),
    ("deSolve(y''+y=0 and y(0)=1 and y'(0)=0,x,y)", "y=cos(x)"),
    ("impDif(x^2+y^2=1,x,y)", "-x/y"),
    ("domain(1/x,x)", "x<0 or x>0"),
    ("isPrime(17)", "true"),
    ("intDiv(-7,2)", "-3"),
    ("getNum((x+1)/(x-1)+1)", "2·x"),
    ("getDenom(1/x+1/y)", "x·y"),
    ("approxRational(0.333333333)", "333333333/1000000000"),
    ("approxRational(0.333333333,1E-6)", "1/3"),
    ("sec(0)", "1"),
    ("cosh(0)", "1"),
    ("int(-2.5)", "-3."),
    ("int(-5/2)", "-3"),
])
def test_algebra(calc, expr, expected):
    assert calc(expr) == expected


def test_numeric_extrema(num):
    assert num("nfMin(x^2-4x,x)") == pytest.approx(2, abs=1e-6)
    assert num("nfMax(sin(x),x,0,3)") == pytest.approx(1.5707963, abs=1e-6)
    assert num("arcLen(x^2,x,0,1)") == pytest.approx(1.4789429, rel=1e-6)


def test_solve_with_interval(calc):
    assert calc("solve(sin(x)=1/2,x)|0≤x≤2π") == "x=π/6 or x=5·π/6"


def test_euler(session):
    result = session.evaluate("euler(y,x,y,{0,1},1,0.5)")
    assert [float(v) for v in result.row(1)] == pytest.approx([1, 1.5, 2.25])


# ------------------------------------------------------------------ conversions ►


@pytest.mark.parametrize("expr, expected", [
    ("1/3►Decimal", "0.333333"),
    ("1/3@>Decimal", "0.333333"),
    ("0.25►approxFraction()", "1/4"),
    ("25►Base2", "0b11001"),
    ("255►Base16", "0hFF"),
    ("0b11001►Base10", "25"),
    ("(1∠π/2)", "ⅈ"),
])
def test_conversions(calc, expr, expected):
    assert calc(expr) == expected


def test_dms(session, calc):
    session.settings.angle = "deg"
    assert calc("30°15'") == "121/4"
    assert calc("30.5►DMS") == "30°30'0″"
    assert calc("30°30'►DD") == "30.5"


def test_units(num, calc):
    assert calc("3_m►_ft") == "9.84252·_ft"
    assert calc("100_km/_hr►_m/_s") == "27.7778·(_m/_s)"
    assert calc("tmpCnv(100_°C,_°F)") == "212·_°f"


# ------------------------------------------------------------------ statistics


def test_z_test(session):
    r = rows(session.evaluate("zTest 100,15,105,30,1"))
    assert float(r["z"]) == pytest.approx(1.82574, rel=1e-5)
    assert float(r["PVal"]) == pytest.approx(0.0339446, rel=1e-4)


def test_t_test(session):
    r = rows(session.evaluate("tTest 100,105,15,30,1"))
    assert float(r["t"]) == pytest.approx(1.82574, rel=1e-5)
    assert int(r["df"]) == 29


def test_one_prop(session):
    r = rows(session.evaluate("zTest_1Prop 0.5,60,100"))
    assert float(r["z"]) == pytest.approx(2.0)
    r = rows(session.evaluate("zInterval_1Prop 60,100"))
    lo, hi = (float(v) for v in r["CLower, CUpper"])
    assert lo == pytest.approx(0.503982, rel=1e-5)
    assert hi == pytest.approx(0.696018, rel=1e-5)


def test_chi2_and_anova(session):
    assert float(rows(session.evaluate("χ²GOF {10,20,30},{20,20,20},2"))["χ²"]) == pytest.approx(10)
    assert float(rows(session.evaluate("chi22way [10,20;30,40]"))["χ²"]) == pytest.approx(0.793651, rel=1e-5)
    assert float(rows(session.evaluate("ANOVA {1,2,3},{2,3,4},{5,6,7}"))["F"]) == pytest.approx(13)


def test_more_regressions(session):
    r = rows(session.evaluate("CubicReg {0,1,2,3,4},{1,2,9,28,65}"))
    assert [float(r[k]) for k in "abcd"] == pytest.approx([1, 0, 0, 1], abs=1e-9)
    r = rows(session.evaluate("PowerReg {1,2,3,4},{2,8,18,32}"))
    assert float(r["a"]) == pytest.approx(2) and float(r["b"]) == pytest.approx(2)
    r = rows(session.evaluate("MedMed {1,2,3,4,5,6,7,8,9},{2,4,6,8,10,12,14,16,18}"))
    assert float(r["m"]) == pytest.approx(2)
    r = rows(session.evaluate("LinRegtTest {1,2,3,4,5},{2,4,5,4,5}"))
    assert float(r["t"]) == pytest.approx(2.12132, rel=1e-5)


@pytest.mark.parametrize("expr, expected", [
    ("FPdf(1,2,3)", 0.278855),
    ("FCdf(0,2,3,4)", 0.743613),
    ("invF(0.95,2,10)", 4.10282),
    ("invχ²(0.95,1)", 3.84146),
    ("invChi2(0.95,1)", 3.84146),
    ("invBinom(0.77,30,1/6)", 6),
])
def test_more_distributions(num, expr, expected):
    assert num(expr) == pytest.approx(expected, rel=1e-5)


# ------------------------------------------------------------------ finance


@pytest.mark.parametrize("expr, expected", [
    ("tvmPmt(60,10,5000,0,12,12)", -106.235),
    ("tvmFV(10,5,-1000,0)", 1628.89),
    ("tvmPV(10,5,0,1628.89)", -1000.0),
    ("tvmN(5,-1000,0,2000)", 14.2067),
    ("tvmI(10,-1000,0,2000)", 7.17735),
    ("npv(10,-1000,{300,400,500})", -21.0368),
    ("irr(-1000,{300,400,500})", 8.89634),
    ("eff(10,12)", 10.4713),
    ("nom(10.471307,12)", 10.0),
    ("dbd(12.3121,1.0122)", 1),
])
def test_finance(num, expr, expected):
    assert num(expr) == pytest.approx(expected, rel=1e-5)


def test_amortization(session):
    table = session.evaluate("amortTbl(3,60,10,5000,,,12,12)")
    assert [float(v) for v in table.row(0)] == pytest.approx([1, -41.67, -64.57, 4935.43])


# ------------------------------------------------------------------ programs


def test_recursive_func(calc):
    calc("Define f(n)=Func:If n≤1 Then:Return 1:Else:Return n*f(n-1):EndIf:EndFunc")
    assert calc("f(5)") == "120"


def test_multiline_func_with_local_and_while(calc):
    calc("Define g(x)=Func\nLocal s\ns:=0\nWhile x>0\ns:=s+x\nx:=x-1\nEndWhile\nReturn s\nEndFunc")
    assert calc("g(4)") == "10"


def test_program_disp(session):
    session.evaluate("Define p()=Prgm:For i,1,3:Disp i^2:EndFor:EndPrgm")
    entry = session.run("p()")
    assert entry.output == ["1", "4", "9"]
    assert entry.text == "Done"


def test_func_cannot_modify_globals(session):
    session.evaluate("Define bad()=Func:zz:=1:Return zz:EndFunc")
    with pytest.raises(CalcError):
        session.evaluate("bad()")


def test_try_else(session, calc):
    calc("Define h(v)=Func:Try:Return ln(v):Else:Return \"err\":EndTry:EndFunc")
    assert calc("h(0)") == "\"err\""


def test_loop_exit_cycle(calc):
    calc("Define q()=Func:Local s,k:s:=0:For k,1,10:If k=3:Cycle:If k>5:Exit:s:=s+k:EndFor:Return s:EndFunc")
    assert calc("q()") == "12"   # 1+2+4+5


def test_request(session):
    session.input_provider = lambda prompt, is_string: "42"
    session.evaluate("Define r()=Prgm:Request \"n?\",nn:Disp nn*2:EndPrgm")
    entry = session.run("r()")
    assert entry.output[-1] == "84"


def test_modes(calc):
    assert calc("getMode(2)") == "1"
    assert calc("setMode(2,2)") == "1"
    assert calc("sin(30)") == "1/2"
    assert calc("getType(undefinedvar)") == "\"NONE\""
    calc("v:=\"text\"")
    assert calc("getType(v)") == "\"STR\""


# ------------------------------------------------------------------ CX II draw commands & extras


def test_draw_commands(session):
    session.evaluate("Define art()=Prgm:SetColor 255,0,0:FillCircle 159,106,50:SetWindow 0,10,0,10:"
                     "DrawLine 0,0,10,10:PlotXY 5,5,1:DrawText 1,1,\"hi\":EndPrgm")
    entry = session.run("art()")
    kinds = [op[0] for op in entry.drawing]
    assert kinds == ["ellipse", "line", "point", "text"]
    assert entry.drawing[0][1] == (255, 0, 0)
    (x1, y1), (x2, y2) = entry.drawing[1][4]
    assert (x1, y1, x2, y2) == (0, 212, 318, 0)   # window origin bottom left
    from complex_calc.functions.draw import render
    assert render(entry.drawing).size == (636, 424)


@pytest.mark.parametrize("expr, expected", [
    ("P►Rx(2,π/3)", "1"),
    ("R►Pθ(1,1)", "π/4"),
    ("R@>Pr(3,4)", "5"),
    ("freqTable►list({1,2},{2,3})", "{1,1,2,2,2}"),
    ("interpolate(1.5,{1,2},{1,4},{2,4})", "2.25"),
])
def test_extras(calc, expr, expected):
    assert calc(expr) == expected


def test_anova_2way_and_mult_reg(session):
    r = rows(session.evaluate("ANOVA2way {1,2,3,4},{2,3,4,6},{5,6,7,8}"))
    assert float(r["F"]) == pytest.approx(201)
    r = rows(session.evaluate("MultRegTests {3,5,7,9,12},{1,2,3,4,5},{0,1,0,1,1}"))
    assert float(r["R²"]) == pytest.approx(0.991803, rel=1e-5)
    r = rows(session.evaluate("MultRegIntervals {3,5,7,9,12},{1,2,3,4,5},{0,1,0,1,1},{3,1}"))
    assert float(r["ŷ"]) == pytest.approx(7.2, rel=1e-6)


def test_matrix_functions(calc):
    assert calc("exp([0,1;0,0])") == "[[1,1][0,1]]"
    assert calc("√([4,0;0,9])") == "[[2,0][0,3]]"
    assert calc("sin({0,π/2})") == "{0,1}"   # lists stay element-wise


def test_library(tmp_path, session, calc):
    from complex_calc.library import refresh_libraries

    (tmp_path / "linalg.txt").write_text(
        "Define LibPub sq(x)=x^2\nDefine LibPriv helper(x)=x+1\n"
        "Define LibPub twice(x)=Func\nReturn 2*helper(x)\nEndFunc\n", encoding="utf-8")
    refresh_libraries(session, tmp_path)
    assert calc("linalg\\sq(5)") == "25"
    assert calc("linalg\\twice(3)") == "8"
    assert calc('libShortcut("linalg","la")') == "{la.sq,la.twice}"
    assert calc("la.sq(4)") == "16"


def test_hardware_commands(session):
    with pytest.raises(CalcError):
        session.evaluate('Send "SET LIGHT ON"')


def test_dashed_pen(session):
    from complex_calc.functions.draw import render

    session.evaluate("Define dash()=Prgm:SetPen 2,3:DrawLine 0,100,300,100:SetPen 1,2:DrawCircle 150,100,50:EndPrgm")
    entry = session.run("dash()")
    image = render(entry.drawing, scale=1)
    row = [image.getpixel((x, 100)) for x in range(0, 300)]
    assert (255, 255, 255) in row and (0, 0, 0) in row      # gaps in the dashed line
