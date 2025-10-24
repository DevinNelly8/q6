"""Utility math helpers used across the lightweight analysis modules.

The project originally relied on :mod:`numpy` for most numeric operations.
Because the execution environment in this kata does not provide third-party
packages we instead implement the tiny subset of functionality that is needed
by the rewritten modules.  The helpers intentionally operate on standard
Python sequences so they stay dependency free and easy to audit.
"""

from __future__ import annotations

from math import cos, factorial, pi, sqrt
from typing import Iterable, Sequence, Tuple
import cmath


Vector = Sequence[float]


def vector_sub(a: Vector, b: Vector) -> Tuple[float, float, float]:
    """Return the component-wise difference ``a - b`` for three component vectors."""

    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def vector_norm(vec: Vector) -> float:
    """Euclidean norm of a 3D vector."""

    return sqrt(vec[0] * vec[0] + vec[1] * vec[1] + vec[2] * vec[2])


def mean(values: Iterable[float]) -> float:
    """Return the arithmetic mean of *values* or ``0.0`` when empty."""

    values = list(values)
    if not values:
        return 0.0
    return sum(values) / len(values)


def clip(value: float, min_value: float, max_value: float) -> float:
    """Clamp *value* to the inclusive interval ``[min_value, max_value]``."""

    if value < min_value:
        return min_value
    if value > max_value:
        return max_value
    return value


def spherical_harmonic(l: int, m: int, theta: float, phi: float) -> complex:
    """Compute the complex spherical harmonic :math:`Y_l^m(\theta, \phi)`.

    Only small degrees (``l = 4`` and ``l = 6``) are used in the analysis which
    keeps the recursion manageable.  The implementation follows the definition
    based on the associated Legendre polynomials.
    """

    if abs(m) > l:
        return 0j

    # Compute the associated Legendre polynomial P_l^m(cos(theta)) using the
    # stable recurrence relations.
    x = cos(theta)
    abs_m = abs(m)

    # Initial value P_m^m(x)
    p_mm = (-1) ** abs_m * double_factorial(2 * abs_m - 1) * (1 - x * x) ** (abs_m / 2.0)

    if l == abs_m:
        p_lm = p_mm
    else:
        p_m1m = x * (2 * abs_m + 1) * p_mm
        if l == abs_m + 1:
            p_lm = p_m1m
        else:
            p_lm_prev_prev = p_mm
            p_lm_prev = p_m1m
            for ell in range(abs_m + 2, l + 1):
                p_lm = ((2 * ell - 1) * x * p_lm_prev - (ell + abs_m - 1) * p_lm_prev_prev) / (ell - abs_m)
                p_lm_prev_prev, p_lm_prev = p_lm_prev, p_lm
    if m < 0:
        # Use the Condon-Shortley phase relation.
        p_lm = (-1) ** abs_m * factorial(l - abs_m) / factorial(l + abs_m) * p_lm

    normalization = sqrt((2 * l + 1) / (4 * pi) * factorial(l - abs_m) / factorial(l + abs_m))
    result = normalization * p_lm * cmath.exp(1j * m * phi)
    return result


def double_factorial(n: int) -> int:
    """Return the double factorial ``n!!``."""

    if n <= 0:
        return 1
    result = 1
    for value in range(n, 0, -2):
        result *= value
    return result


__all__ = [
    "clip",
    "mean",
    "spherical_harmonic",
    "vector_norm",
    "vector_sub",
]
