"""Random numbers: rand, randInt, randBin, randNorm, randMat, randPoly, randSamp, RandSeed."""

from __future__ import annotations

import random

import sympy as sp

from ..core.errors import DomainError
from ..core.values import ListValue
from .registry import builtin, check_probability, to_float, to_int, to_list

_rng = random.Random()


def _trials(count, make):
    if count is None:
        return make()
    return ListValue(make() for _ in range(to_int(count, "#Trials")))


@builtin("RandSeed", "RandSeed Number", 1, command=True, summary="Seed the random generator (0 = reset)")
def rand_seed(ctx, seed):
    _rng.seed(to_int(seed, "Number"))
    return None


@builtin("rand", "rand([#Trials])", 0, 1, approx=True, summary="Random number between 0 and 1")
def rand_(ctx, count=None):
    return _trials(count, lambda: sp.Float(_rng.random(), 15))


@builtin("randInt", "randInt(lowBound,upBound[,#Trials])", 2, 3, summary="Random integer(s)")
def rand_int(ctx, low, high, count=None):
    lo, hi = to_int(low, "lowBound"), to_int(high, "upBound")
    if lo > hi:
        lo, hi = hi, lo
    return _trials(count, lambda: sp.Integer(_rng.randint(lo, hi)))


@builtin("randBin", "randBin(n,p[,#Trials])", 2, 3, summary="Random binomial value(s)")
def rand_bin(ctx, n, p, count=None):
    trials, prob = to_int(n, "n"), to_float(p, "p")
    check_probability(prob)
    return _trials(count, lambda: sp.Integer(sum(_rng.random() < prob for _ in range(trials))))


@builtin("randNorm", "randNorm(μ,σ[,#Trials])", 2, 3, approx=True, summary="Random normal value(s)")
def rand_norm(ctx, mu, sigma, count=None):
    m, s = to_float(mu, "μ"), to_float(sigma, "σ")
    return _trials(count, lambda: sp.Float(_rng.gauss(m, s), 15))


@builtin("randMat", "randMat(numRows,numColumns)", 2, summary="Matrix of random integers -9..9")
def rand_mat(ctx, rows, cols):
    r, c = to_int(rows, "numRows"), to_int(cols, "numColumns")
    return sp.ImmutableMatrix(r, c, [sp.Integer(_rng.randint(-9, 9)) for _ in range(r * c)])


@builtin("randPoly", "randPoly(Var,Order)", 2, hold=(0,), summary="Random polynomial with coefficients -9..9")
def rand_poly(ctx, var, order):
    n = to_int(order, "Order")
    if not 0 <= n <= 99:
        raise DomainError("Order must be 0..99")
    coeffs = [_rng.randint(-9, 9) for _ in range(n + 1)]
    while coeffs[0] == 0:
        coeffs[0] = _rng.randint(-9, 9)
    return sp.Add(*[c * var ** (n - k) for k, c in enumerate(coeffs)])


@builtin("randSamp", "randSamp(List,#Trials[,noRepl])", 2, 3, summary="Random sample from a list")
def rand_samp(ctx, values, count, no_repl=None):
    data = to_list(values, "List")
    k = to_int(count, "#Trials")
    if no_repl is not None and to_float(no_repl, "noRepl") != 0:
        if k > len(data):
            raise DomainError("#Trials larger than the list")
        return ListValue(_rng.sample(data, k))
    return ListValue(_rng.choice(data) for _ in range(k))
