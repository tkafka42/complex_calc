import pytest


def rows(result):
    return dict(result.rows)


def test_z_interval_stats(session):
    result = session.evaluate("zInterval 15,100,25,0.95")
    r = rows(result)
    assert result.title == "z Interval"
    lo, hi = (float(v) for v in r["CLower, CUpper"])
    assert lo == pytest.approx(94.1201, rel=1e-5)
    assert hi == pytest.approx(105.880, rel=1e-5)
    assert float(r["ME"]) == pytest.approx(5.87989, rel=1e-5)
    assert list(r) == ["CLower, CUpper", "x̄", "ME", "n", "σ"]


def test_z_interval_data(session):
    result = session.evaluate("zInterval 2,{1,2,3,4,5},1,0.9")
    r = rows(result)
    assert list(r) == ["CLower, CUpper", "x̄", "ME", "sx", "n", "σ"]
    assert float(r["ME"]) == pytest.approx(1.64485 * 2 / 5 ** 0.5, rel=1e-5)


def test_t_interval_stats(session):
    result = session.evaluate("tInterval 100,15,25,0.95")
    r = rows(result)
    assert result.title == "t Interval"
    assert list(r) == ["CLower, CUpper", "x̄", "ME", "df", "sx", "n"]
    lo, hi = (float(v) for v in r["CLower, CUpper"])
    assert lo == pytest.approx(93.8083, rel=1e-5)
    assert hi == pytest.approx(106.192, rel=1e-5)
    assert int(r["df"]) == 24


def test_t_interval_data_default_clevel(session):
    result = session.evaluate("tInterval {1,2,3,4,5}")
    r = rows(result)
    assert float(r["sx"]) == pytest.approx(1.58114, rel=1e-5)
    assert float(r["ME"]) == pytest.approx(1.96324, rel=1e-5)


def test_stat_variables_stored(session):
    session.evaluate("tInterval 100,15,25,0.95")
    assert float(session.evaluate("stat.CLower")) == pytest.approx(93.8083, rel=1e-5)
    assert float(session.evaluate("STAT.ME")) == pytest.approx(6.1917, rel=1e-4)


def test_clevel_percent(session):
    a = rows(session.evaluate("zInterval 15,100,25,95"))
    b = rows(session.evaluate("zInterval 15,100,25,0.95"))
    assert float(a["ME"]) == pytest.approx(float(b["ME"]))


def test_table_format(session):
    text = session.format(session.evaluate("zInterval 15,100,25,0.95"))
    assert text.splitlines()[0].startswith('"Title"')
    assert '"CLower, CUpper"  {94.1201,105.88}' in text


def test_one_var(session):
    r = rows(session.evaluate("OneVar {1,2,3,4,5}"))
    assert float(r["x̄"]) == 3
    assert float(r["Q₁X"]) == 1.5
    assert float(r["Q₃X"]) == 4.5
