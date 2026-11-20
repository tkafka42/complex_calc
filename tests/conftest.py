import pytest

from complex_calc.core.session import Session


@pytest.fixture
def session() -> Session:
    return Session()


@pytest.fixture
def calc(session):
    """calc("expr") → formatted result text; raises on error."""

    def run(source: str) -> str:
        return session.format(session.evaluate(source))

    return run


@pytest.fixture
def num(session):
    """num("expr") → float value of the result."""

    def run(source: str) -> float:
        return float(session.evaluate(source))

    return run
