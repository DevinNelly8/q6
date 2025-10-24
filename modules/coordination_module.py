#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""配位数和GCN计算模块 v6.2.3"""

from __future__ import annotations

from math import exp
from typing import Iterable, Sequence

from .config import COORDINATION, GCN
from .math_utils import mean, vector_norm, vector_sub


def plumed_switch(distances: Iterable[float], R0: float, NN: float, MM: float, D0: float, Dmax: float):
    """PLUMED风格的平滑切换函数"""

    values = []
    for dist in distances:
        x = (dist - D0) / R0
        num = 1 - x ** NN
        den = 1 - x ** MM
        if abs(den) < 1e-8:
            den = 1e-8
        sw = num / den
        if dist > Dmax or sw < 0:
            sw = 0.0
        values.append(sw)
    return values


def calc_cn_smooth(dists: Sequence[float], bond_type='pt_pt'):
    """使用PLUMED平滑函数计算配位数"""
    params = COORDINATION['plumed'][bond_type]

    sw_values = plumed_switch(
        dists,
        params['R0'],
        params['NN'],
        params['MM'],
        params['D0'],
        params['Dmax']
    )

    return float(sum(value for value in sw_values if not _is_nan(value)))


def calc_bond_specific_cn_smooth(central_pos, central_element, pt_positions, sn_positions, box=None):
    """计算键型特异性配位数（平滑版本）"""

    result = {
        'cn_center_center': 0.0,
        'cn_center_other': 0.0,
        'cn_total': 0.0,
        'avg_dist_center_center': 0.0,
        'avg_dist_center_other': 0.0,
        'central_element': central_element
    }

    pt_dists = [_distance(central_pos, pos) for pos in pt_positions]
    sn_dists = [_distance(central_pos, pos) for pos in sn_positions]

    if central_element == 'Pt':
        valid_pt = [d for d in pt_dists if d > 0.1]
        if valid_pt:
            result['cn_center_center'] = calc_cn_smooth(valid_pt, 'pt_pt')
            cutoff = COORDINATION['rcut_pt_pt'] * 1.5
            near_pt = [d for d in valid_pt if d < cutoff]
            if near_pt:
                result['avg_dist_center_center'] = mean(near_pt)

        if sn_dists:
            result['cn_center_other'] = calc_cn_smooth(sn_dists, 'pt_sn')
            cutoff = COORDINATION['rcut_pt_sn'] * 1.5
            near_sn = [d for d in sn_dists if d < cutoff]
            if near_sn:
                result['avg_dist_center_other'] = mean(near_sn)

        result['cn_total'] = result['cn_center_center'] + result['cn_center_other']

    elif central_element == 'Sn':
        if pt_dists:
            result['cn_center_other'] = calc_cn_smooth(pt_dists, 'pt_sn')
            cutoff = COORDINATION['rcut_pt_sn'] * 1.5
            near_pt = [d for d in pt_dists if d < cutoff]
            if near_pt:
                result['avg_dist_center_other'] = mean(near_pt)

        valid_sn = [d for d in sn_dists if d > 0.1]
        if valid_sn:
            result['cn_center_center'] = calc_cn_smooth(valid_sn, 'sn_sn')
            cutoff = COORDINATION['rcut_sn_sn'] * 1.5
            near_sn = [d for d in valid_sn if d < cutoff]
            if near_sn:
                result['avg_dist_center_center'] = mean(near_sn)

        result['cn_total'] = result['cn_center_other'] + result['cn_center_center']

    return result


def calc_gcn_descriptors(central_pos, pt_positions, sn_positions, box=None):
    """计算所有GCN变体"""

    if not GCN['enable']:
        return {
            'gcn_loc': 0.0,
            'w_gcn_loc': 0.0,
            'sn_w_gcn_loc': 0.0,
            'shell_gcn_loc': 0.0
        }

    pt_dists = [_distance(central_pos, pos) for pos in pt_positions]
    sn_dists = [_distance(central_pos, pos) for pos in sn_positions]
    pt_dists = [d for d in pt_dists if d > 0.1]
    sn_dists = [d for d in sn_dists if d > 0.1]

    # 1. 标准GCN
    params = GCN['standard']
    all_dists = pt_dists + sn_dists
    gcn_weights = [exp(-dist / params['r0']) if dist <= params['cutoff'] else 0.0 for dist in all_dists]
    gcn_loc = float(sum(gcn_weights))

    # 2. 加权GCN (wGCN)
    params = GCN['weighted']
    pt_weights = [params['pt_weight'] * exp(-dist / params['r0']) if dist <= params['cutoff'] else 0.0 for dist in pt_dists]
    sn_weights = [params['sn_weight'] * exp(-dist / params['r0']) if dist <= params['cutoff'] else 0.0 for dist in sn_dists]
    w_gcn_loc = float(sum(pt_weights) + sum(sn_weights))

    # 3. Sn加权GCN
    params = GCN['sn_weighted']
    pt_mask = [params['r_min'] <= dist <= params['r_max'] for dist in pt_dists]
    sn_mask = [params['r_min'] <= dist <= params['r_max'] for dist in sn_dists]
    sn_w_gcn_loc = float(
        params['pt_weight'] * sum(1 for flag in pt_mask if flag) +
        params['sn_weight'] * sum(1 for flag in sn_mask if flag)
    )

    # 4. 壳层GCN
    shells = GCN['shell']['shells']
    shell_gcn_loc = 0.0
    for shell in shells:
        pt_count = sum(1 for dist in pt_dists if shell['r_min'] <= dist <= shell['r_max'])
        sn_count = sum(1 for dist in sn_dists if shell['r_min'] <= dist <= shell['r_max'])
        shell_gcn_loc += shell['pt_weight'] * pt_count + shell['sn_weight'] * sn_count

    return {
        'gcn_loc': gcn_loc,
        'w_gcn_loc': w_gcn_loc,
        'sn_w_gcn_loc': sn_w_gcn_loc,
        'shell_gcn_loc': float(shell_gcn_loc)
    }


def _distance(a, b):
    return vector_norm(vector_sub(a, b))


def _is_nan(value: float) -> bool:
    return value != value


__all__ = [
    'calc_bond_specific_cn_smooth',
    'calc_gcn_descriptors',
]
