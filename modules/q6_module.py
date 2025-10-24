#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
局域Q6/Q4计算模块 v6.2.3
=========================

计算每个原子的局域Q6和Q4序参量

作者: DevinNelly8
日期: 2025-10-24
"""

import numpy as np
from scipy.special import sph_harm

try:
    from .config import Q6_Q4
except ImportError:
    from config import Q6_Q4


def calc_q_local(central_pos, positions, elements, cutoff=3.5, l=6, metal_only=True):
    """计算局域Ql序参量"""
    
    # 筛选邻居
    if metal_only:
        metal_mask = (elements == 'Pt') | (elements == 'Sn')
        neighbor_positions = positions[metal_mask]
    else:
        neighbor_positions = positions
    
    if len(neighbor_positions) == 0:
        return 0.0
    
    # 计算距离
    vectors = neighbor_positions - central_pos
    dists = np.linalg.norm(vectors, axis=1)
    
    valid_mask = (dists > 0.1) & (dists < cutoff)
    vectors = vectors[valid_mask]
    dists = dists[valid_mask]
    
    if len(vectors) < 4:
        return 0.0
    
    # 球坐标
    r = dists
    theta = np.arccos(np.clip(vectors[:, 2] / r, -1, 1))
    phi = np.arctan2(vectors[:, 1], vectors[:, 0])
    
    # 计算qlm
    qlm = np.zeros(2*l + 1, dtype=np.complex64)
    for m in range(-l, l+1):
        ylm = sph_harm(m, l, phi, theta)
        qlm[m + l] = np.mean(ylm)
    
    # 计算ql
    ql = np.sqrt(4 * np.pi / (2*l + 1) * np.sum(np.abs(qlm)**2))
    
    return float(np.real(ql))


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
    """
    基于(Q4, Q6)联合判据的结构分类
    
    可区分FCC/HCP/ICO/BCC等结构
    """
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