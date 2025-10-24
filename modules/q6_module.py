#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""局域Q6/Q4计算模块 v6.2.3"""

from __future__ import annotations

from math import acos, atan2, pi, sqrt
from typing import Sequence

from .config import Q6_Q4
from .math_utils import clip, spherical_harmonic, vector_norm, vector_sub


def _select_neighbors(positions: Sequence[Sequence[float]], elements: Sequence[str], metal_only: bool):
    if metal_only:
        return [pos for pos, elem in zip(positions, elements) if elem in {"Pt", "Sn"}]
    return list(positions)


def calc_q_local(central_pos, positions, elements, cutoff=3.5, l=6, metal_only=True):
    """计算局域Ql序参量"""

    neighbor_positions = _select_neighbors(positions, elements, metal_only)
    if not neighbor_positions:
        return 0.0

    vectors = []
    distances = []
    for pos in neighbor_positions:
        vec = vector_sub(pos, central_pos)
        dist = vector_norm(vec)
        if 0.1 < dist < cutoff:
            vectors.append(vec)
            distances.append(dist)

    if len(vectors) < 4:
        return 0.0

    qlm = [0j for _ in range(2 * l + 1)]

    for vec, r in zip(vectors, distances):
        theta = acos(clip(vec[2] / r, -1.0, 1.0))
        phi = atan2(vec[1], vec[0])
        for m in range(-l, l + 1):
            qlm[m + l] += spherical_harmonic(l, m, theta, phi)

    averaged = [value / len(vectors) for value in qlm]
    sum_sq = sum(abs(value) ** 2 for value in averaged)
    ql = sqrt(4 * pi / (2 * l + 1) * sum_sq)
    return float(ql)


def calc_q6_fast(central_pos, positions, elements, cutoff=None):
    """计算Q6"""
    if cutoff is None:
        cutoff = Q6_Q4['q6_cutoff']

    metal_only = not Q6_Q4['include_oxygen_in_local']
    return calc_q_local(central_pos, positions, elements, cutoff, l=6, metal_only=metal_only)


def calc_q4_fast(central_pos, positions, elements, cutoff=None):
    """计算Q4"""
    if cutoff is None:
        cutoff = Q6_Q4['q6_cutoff']

    metal_only = not Q6_Q4['include_oxygen_in_local']
    return calc_q_local(central_pos, positions, elements, cutoff, l=4, metal_only=metal_only)


def classify_structure_advanced(q4, q6):
    """基于(Q4, Q6)联合判据的结构分类"""

    if q6 > 0.60:
        if q4 > 0.15:
            return 'FCC-like'
        else:
            return 'ICO-like'
    elif q6 > 0.50:
        if q4 > 0.15:
            return 'FCC-like'
        elif q4 > 0.08:
            return 'HCP-like'
        else:
            return 'BCC-like'
    elif q6 > 0.35:
        return 'Partially-Ordered'
    elif q6 > 0.25:
        return 'Liquid-like'
    else:
        return 'Disordered'


__all__ = [
    "calc_q4_fast",
    "calc_q6_fast",
    "classify_structure_advanced",
]
