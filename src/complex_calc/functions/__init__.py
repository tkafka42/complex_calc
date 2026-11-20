"""Built-in functions. Importing this package registers all of them."""

from . import (  # noqa: F401
    algebra,
    cas,
    conversions,
    draw,
    elementary,
    extras,
    finance,
    intervals,
    lists,
    matrices,
    programming,
    randoms,
    regression,
    stats,
    stattests,
    units,
)
from .registry import REGISTRY, Builtin, lookup_builtin  # noqa: F401
