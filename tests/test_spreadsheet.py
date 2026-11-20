import pytest

from complex_calc.spreadsheet import Sheet


@pytest.fixture
def sheet(session):
    return Sheet(session, rows=50)


def test_named_column_is_list(sheet, calc):
    sheet.set_name(0, "a")
    for row, value in enumerate(["1", "2", "3"]):
        sheet.set_cell(row, 0, value)
    assert calc("a") == "{1,2,3}"
    assert calc("mean(a)") == "2"


def test_column_formula(sheet, calc):
    sheet.set_name(0, "a")
    sheet.set_formula(0, "=seq(n^2,n,1,4)")
    sheet.set_name(1, "b")
    sheet.set_formula(1, "a*2")
    assert calc("b") == "{2,8,18,32}"


def test_cell_formula(sheet):
    sheet.set_cell(0, 0, "5")
    sheet.set_cell(1, 0, "=a1*2+1")
    assert str(sheet.values[(1, 0)]) == "11"


def test_pull_from_calculator(sheet, calc):
    sheet.set_name(2, "data")
    calc("data:={4,5,6}")
    assert sheet.pull_from_session()
    assert [int(v) for v in sheet.column_values(2)] == [4, 5, 6]


def test_regression_from_columns(sheet, session):
    sheet.set_name(0, "xs")
    sheet.set_name(1, "ys")
    for row, (x, y) in enumerate([(1, 2), (2, 4), (3, 6)]):
        sheet.set_cell(row, 0, str(x))
        sheet.set_cell(row, 1, str(y))
    result = session.evaluate("LinRegMx xs,ys")
    assert float(dict(result.rows)["m"]) == pytest.approx(2)


def test_sort_and_errors(sheet):
    for row, value in enumerate(["3", "1", "2"]):
        sheet.set_cell(row, 0, value)
    sheet.sort(0)
    assert [int(v) for v in sheet.column_values(0)] == [1, 2, 3]
    sheet.set_cell(3, 0, "2+")
    assert (3, 0) in sheet.errors
