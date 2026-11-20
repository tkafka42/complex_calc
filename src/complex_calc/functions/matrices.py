"""Matrix and vector functions."""

from __future__ import annotations

from typing import Any

import sympy as sp

from ..core.errors import ArgumentError, DomainError
from ..core.values import ListValue, is_matrix
from .registry import builtin, to_int


def _m(value: Any, label: str = "Matrix") -> sp.ImmutableMatrix:
    if is_matrix(value):
        return value
    if isinstance(value, ListValue):
        return sp.ImmutableMatrix([list(value)])
    raise ArgumentError(f"{label} must be a matrix")


def _square(value: Any) -> sp.ImmutableMatrix:
    matrix = _m(value, "squareMatrix")
    if not matrix.is_square:
        raise ArgumentError("Dimension error: square matrix required")
    return matrix


def _vec(value: Any) -> list:
    if isinstance(value, ListValue):
        return list(value)
    if is_matrix(value) and (value.rows == 1 or value.cols == 1):
        return list(value)
    raise ArgumentError("Vector or list expected")


def _like(original: Any, items: list) -> Any:
    if isinstance(original, ListValue):
        return ListValue(items)
    if is_matrix(original) and original.cols == 1:
        return sp.ImmutableMatrix(items)
    return sp.ImmutableMatrix([items])


M = dict(matrix_aware=True)


@builtin("identity", "identity(Integer)", 1, summary="Identity matrix")
def identity(ctx, n):
    return sp.ImmutableMatrix(sp.eye(to_int(n, "Integer")))


@builtin("newMat", "newMat(numRows,numColumns)", 2, summary="Matrix of zeros")
def new_mat(ctx, rows, cols):
    return sp.ImmutableMatrix(sp.zeros(to_int(rows, "numRows"), to_int(cols, "numColumns")))


@builtin("constructMat", "constructMat(Expr,Var1,Var2,numRows,numCols)", 5, hold=(1, 2),
         summary="Matrix with elements Expr(Var1=row, Var2=column)")
def construct_mat(ctx, expr, var1, var2, rows, cols):
    r, c = to_int(rows, "numRows"), to_int(cols, "numCols")
    return sp.ImmutableMatrix(r, c, lambda i, j: expr.subs({var1: i + 1, var2: j + 1}))


@builtin("det", "det(squareMatrix[,Tolerance])", 1, 2, **M, summary="Determinant")
def det_(ctx, matrix, tol=None):
    return sp.simplify(_square(matrix).det())


@builtin("trace", "trace(squareMatrix)", 1, **M, summary="Sum of the diagonal")
def trace_(ctx, matrix):
    return _square(matrix).trace()


@builtin("rref", "rref(Matrix[,Tol])", 1, 2, **M, summary="Reduced row echelon form")
def rref_(ctx, matrix, tol=None):
    return sp.ImmutableMatrix(_m(matrix).rref()[0].applyfunc(sp.simplify))


@builtin("ref", "ref(Matrix[,Tol])", 1, 2, **M, summary="Row echelon form (Gaussian elimination, leading 1s)")
def ref_(ctx, matrix, tol=None):
    m = sp.Matrix(_m(matrix))
    rows, cols = m.shape
    pivot_row = 0
    for col in range(cols):
        if pivot_row >= rows:
            break
        # partial pivoting: largest absolute value, as the handheld does
        candidates = [r for r in range(pivot_row, rows) if m[r, col] != 0]
        if not candidates:
            continue
        best = max(candidates, key=lambda r: abs(complex(sp.N(m[r, col]))) if m[r, col].is_number else 0)
        m.row_swap(pivot_row, best)
        m[pivot_row, :] = m[pivot_row, :] / m[pivot_row, col]
        for r in range(pivot_row + 1, rows):
            m[r, :] = m[r, :] - m[r, col] * m[pivot_row, :]
        pivot_row += 1
    return sp.ImmutableMatrix(m.applyfunc(sp.simplify))


@builtin("colDim", "colDim(Matrix)", 1, **M, summary="Number of columns")
def col_dim(ctx, matrix):
    return sp.Integer(_m(matrix).cols)


@builtin("rowDim", "rowDim(Matrix)", 1, **M, summary="Number of rows")
def row_dim(ctx, matrix):
    return sp.Integer(_m(matrix).rows)


@builtin("colNorm", "colNorm(Matrix)", 1, **M, summary="Maximum of the column sums of absolute values")
def col_norm(ctx, matrix):
    m = _m(matrix)
    return sp.Max(*[sum(sp.Abs(x) for x in m[:, j]) for j in range(m.cols)])


@builtin("rowNorm", "rowNorm(Matrix)", 1, **M, summary="Maximum of the row sums of absolute values")
def row_norm(ctx, matrix):
    m = _m(matrix)
    return sp.Max(*[sum(sp.Abs(x) for x in m[i, :]) for i in range(m.rows)])


@builtin("norm", "norm(Matrix)  |  norm(Vector)", 1, **M, summary="Frobenius norm")
def norm_(ctx, matrix):
    m = _m(matrix)
    return sp.sqrt(sum(sp.Abs(x) ** 2 for x in m)) if not all(x.is_real for x in m) else \
        sp.sqrt(sum(x**2 for x in m))


@builtin("dotP", "dotP(List1,List2)  |  dotP(Vector1,Vector2)", 2, **M, summary="Dot product")
def dot_p(ctx, a, b):
    u, v = _vec(a), _vec(b)
    if len(u) != len(v):
        raise ArgumentError("Dimension mismatch")
    return sp.expand(sum(x * y for x, y in zip(u, v)))


@builtin("crossP", "crossP(List1,List2)  |  crossP(Vector1,Vector2)", 2, **M, summary="Cross product")
def cross_p(ctx, a, b):
    u, v = _vec(a), _vec(b)
    if len(u) not in (2, 3) or len(v) != len(u):
        raise ArgumentError("crossP needs two vectors of dimension 2 or 3")
    if len(u) == 2:
        u, v = u + [0], v + [0]
    result = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
    return _like(a, [sp.expand(r) for r in result])


@builtin("unitV", "unitV(Vector)", 1, **M, summary="Unit vector")
def unit_v(ctx, a):
    u = _vec(a)
    length = sp.sqrt(sum(x**2 for x in u))
    if length == 0:
        raise DomainError("Zero vector has no direction")
    return _like(a, [sp.simplify(x / length) for x in u])


@builtin("colAugment", "colAugment(Matrix1,Matrix2)", 2, **M, summary="Stack Matrix2 below Matrix1")
def col_augment(ctx, a, b):
    a, b = _m(a), _m(b)
    if a.cols != b.cols:
        raise ArgumentError("Dimension error")
    return sp.ImmutableMatrix(a.col_join(b))


@builtin("subMat", "subMat(Matrix[,startRow][,startCol][,endRow][,endCol])", 1, 5, **M, summary="Part of a matrix")
def sub_mat(ctx, matrix, r1=1, c1=1, r2=None, c2=None):
    m = _m(matrix)
    r1, c1 = to_int(r1, "startRow"), to_int(c1, "startCol")
    r2 = m.rows if r2 is None else to_int(r2, "endRow")
    c2 = m.cols if c2 is None else to_int(c2, "endCol")
    return sp.ImmutableMatrix(m[r1 - 1:r2, c1 - 1:c2])


@builtin("diag", "diag(List)  |  diag(rowMatrix)  |  diag(columnMatrix)  |  diag(squareMatrix)", 1, **M,
         summary="Diagonal matrix from a list, or the diagonal of a square matrix")
def diag_(ctx, value):
    if is_matrix(value) and value.is_square and value.rows > 1:
        return sp.ImmutableMatrix([[value[i, i] for i in range(value.rows)]])
    return sp.ImmutableMatrix(sp.diag(*_vec(value)))


@builtin("eigVl", "eigVl(squareMatrix)", 1, **M, approx=True, summary="Eigenvalues")
def eig_vl(ctx, matrix):
    m = _square(matrix)
    values = []
    for value, multiplicity in m.evalf().eigenvals().items():
        values += [value] * multiplicity
    return ListValue(sorted(values, key=lambda v: (-abs(complex(v)), complex(v).imag)))


@builtin("eigVc", "eigVc(squareMatrix)", 1, **M, approx=True, summary="Eigenvectors (normalised columns)")
def eig_vc(ctx, matrix):
    m = _square(matrix).evalf()
    columns = []
    for value, multiplicity, vectors in sorted(m.eigenvects(), key=lambda t: -abs(complex(t[0]))):
        for vector in vectors:
            columns.append(vector / vector.norm())
    return sp.ImmutableMatrix(sp.Matrix.hstack(*columns))


@builtin("charPoly", "charPoly(squareMatrix,Var)", 2, hold=(1,), **M, summary="Characteristic polynomial det(Var·I-M)")
def char_poly(ctx, matrix, var):
    m = _square(matrix)
    return sp.expand((var * sp.eye(m.rows) - m).det())


@builtin("LU", "LU Matrix,lMatrix,uMatrix,pMatrix[,Tol]", 4, 5, command=True, hold=(1, 2, 3),
         summary="LU decomposition with partial pivoting: P·M = L·U")
def lu_(ctx, matrix, l_var, u_var, p_var, tol=None):
    m = sp.Matrix(_m(matrix))
    lower, upper, perm = m.LUdecomposition()
    p = sp.eye(m.rows).permute_rows(perm)
    ctx.store(l_var.name, sp.ImmutableMatrix(lower))
    ctx.store(u_var.name, sp.ImmutableMatrix(upper))
    ctx.store(p_var.name, sp.ImmutableMatrix(p))
    return None


@builtin("QR", "QR Matrix,qMatrix,rMatrix[,Tol]", 3, 4, command=True, hold=(1, 2),
         summary="QR factorisation: M = Q·R")
def qr_(ctx, matrix, q_var, r_var, tol=None):
    q, r = sp.Matrix(_m(matrix)).QRdecomposition()
    ctx.store(q_var.name, sp.ImmutableMatrix(q))
    ctx.store(r_var.name, sp.ImmutableMatrix(r))
    return None


@builtin("simult", "simult(coeffMatrix,constVector[,Tol])", 2, 3, **M, summary="Solve a linear system A·x=b")
def simult_(ctx, a, b, tol=None):
    a = _square(a)
    b = _m(b) if is_matrix(b) else sp.ImmutableMatrix(_vec(b))
    if a.det() == 0:
        raise DomainError("Singular matrix")
    return sp.ImmutableMatrix(a.LUsolve(b).applyfunc(sp.simplify))


@builtin("mRow", "mRow(Expr,Matrix,Index)", 3, **M, summary="Multiply a row by Expr")
def m_row(ctx, factor, matrix, index):
    m = sp.Matrix(_m(matrix))
    i = to_int(index, "Index") - 1
    m[i, :] = factor * m[i, :]
    return sp.ImmutableMatrix(m)


@builtin("mRowAdd", "mRowAdd(Expr,Matrix,Index1,Index2)", 4, **M, summary="Add Expr·row Index1 to row Index2")
def m_row_add(ctx, factor, matrix, i1, i2):
    m = sp.Matrix(_m(matrix))
    a, b = to_int(i1, "Index1") - 1, to_int(i2, "Index2") - 1
    m[b, :] = m[b, :] + factor * m[a, :]
    return sp.ImmutableMatrix(m)


@builtin("rowAdd", "rowAdd(Matrix,rIndex1,rIndex2)", 3, **M, summary="Add row rIndex1 to row rIndex2")
def row_add(ctx, matrix, i1, i2):
    return m_row_add(ctx, sp.Integer(1), matrix, i1, i2)


@builtin("rowSwap", "rowSwap(Matrix,rIndex1,rIndex2)", 3, **M, summary="Swap two rows")
def row_swap(ctx, matrix, i1, i2):
    m = sp.Matrix(_m(matrix))
    m.row_swap(to_int(i1, "rIndex1") - 1, to_int(i2, "rIndex2") - 1)
    return sp.ImmutableMatrix(m)


@builtin("corrMat", "corrMat(List1,List2[,…[,List20]])", 2, 20, approx=True, summary="Correlation matrix")
def corr_mat(ctx, *lists):
    import numpy as np

    data = np.array([[float(sp.N(v)) for v in _vec(lst)] for lst in lists])
    return sp.ImmutableMatrix(np.corrcoef(data).tolist())
