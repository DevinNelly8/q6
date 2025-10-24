#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配位数和GCN计算模块 v6.2.3
============================

包含：
1. PLUMED平滑切换函数
2. 平滑配位数计算
3. 4种GCN变体

作者: DevinNelly8
日期: 2025-10-24
"""

import numpy as np

try:
    from .config import COORDINATION, GCN
except ImportError:
    from config import COORDINATION, GCN


def plumed_switch(distances, R0, NN, MM, D0, Dmax):
    """
    PLUMED风格的平滑切换函数
    
    公式: sw(r) = (1 - ((r-D0)/R0)^NN) / (1 - ((r-D0)/R0)^MM)
    """
    x = (distances - D0) / R0
    num = 1 - x**NN
    den = 1 - x**MM
    
    den[den == 0] = 1e-8
    sw = num / den
    sw[distances > Dmax] = 0.0
    sw[sw < 0] = 0.0
    
    return sw


def calc_cn_smooth(dists, bond_type='pt_pt'):
    """使用PLUMED平滑函数计算配位数"""
    params = COORDINATION['plumed'][bond_type]
    
    sw = plumed_switch(
        dists, 
        params['R0'], 
        params['NN'], 
        params['MM'], 
        params['D0'], 
        params['Dmax']
    )
    
    return float(np.nansum(sw))


def calc_bond_specific_cn_smooth(central_pos, central_element, pt_positions, sn_positions, box=None):
    """
    计算键型特异性配位数（平滑版本）
    
    ⭐ v6.2.3关键改进：使用PLUMED平滑函数替代硬截断
    """
    result = {
        'cn_center_center': 0.0,
        'cn_center_other': 0.0,
        'cn_total': 0.0,
        'avg_dist_center_center': 0.0,
        'avg_dist_center_other': 0.0,
        'central_element': central_element
    }
    
    if central_element == 'Pt':
        # Pt-Pt配位
        if len(pt_positions) > 0:
            pt_dists = np.linalg.norm(pt_positions - central_pos, axis=1)
            pt_dists = pt_dists[pt_dists > 0.1]
            
            result['cn_center_center'] = calc_cn_smooth(pt_dists, 'pt_pt')
            
            cutoff = COORDINATION['rcut_pt_pt'] * 1.5
            valid_pt = pt_dists[pt_dists < cutoff]
            if len(valid_pt) > 0:
                result['avg_dist_center_center'] = float(np.mean(valid_pt))
        
        # Pt-Sn配位
        if len(sn_positions) > 0:
            sn_dists = np.linalg.norm(sn_positions - central_pos, axis=1)
            
            result['cn_center_other'] = calc_cn_smooth(sn_dists, 'pt_sn')
            
            cutoff = COORDINATION['rcut_pt_sn'] * 1.5
            valid_sn = sn_dists[sn_dists < cutoff]
            if len(valid_sn) > 0:
                result['avg_dist_center_other'] = float(np.mean(valid_sn))
        
        result['cn_total'] = result['cn_center_center'] + result['cn_center_other']
    
    elif central_element == 'Sn':
        # Sn-Pt配位
        if len(pt_positions) > 0:
            pt_dists = np.linalg.norm(pt_positions - central_pos, axis=1)
            
            result['cn_center_other'] = calc_cn_smooth(pt_dists, 'pt_sn')
            
            cutoff = COORDINATION['rcut_pt_sn'] * 1.5
            valid_pt = pt_dists[pt_dists < cutoff]
            if len(valid_pt) > 0:
                result['avg_dist_center_other'] = float(np.mean(valid_pt))
        
        # Sn-Sn配位
        if len(sn_positions) > 0:
            sn_dists = np.linalg.norm(sn_positions - central_pos, axis=1)
            sn_dists = sn_dists[sn_dists > 0.1]
            
            result['cn_center_center'] = calc_cn_smooth(sn_dists, 'sn_sn')
            
            cutoff = COORDINATION['rcut_sn_sn'] * 1.5
            valid_sn = sn_dists[sn_dists < cutoff]
            if len(valid_sn) > 0:
                result['avg_dist_center_center'] = float(np.mean(valid_sn))
        
        result['cn_total'] = result['cn_center_other'] + result['cn_center_center']
    
    return result


def calc_gcn_descriptors(central_pos, pt_positions, sn_positions, box=None):
    """
    计算所有GCN变体
    
    ⭐ v6.2.3新增：4种GCN描述符
    """
    if not GCN['enable']:
        return {
            'gcn_loc': 0.0,
            'w_gcn_loc': 0.0,
            'sn_w_gcn_loc': 0.0,
            'shell_gcn_loc': 0.0
        }
    
    # 计算距离
    pt_dists = np.linalg.norm(pt_positions - central_pos, axis=1)
    sn_dists = np.linalg.norm(sn_positions - central_pos, axis=1)
    pt_dists = pt_dists[pt_dists > 0.1]
    
    # 1. 标准GCN
    params = GCN['standard']
    all_dists = np.concatenate([pt_dists, sn_dists])
    gcn_weights = np.exp(-all_dists / params['r0'])
    gcn_weights[all_dists > params['cutoff']] = 0
    gcn_loc = float(np.sum(gcn_weights))
    
    # 2. 加权GCN (wGCN) - 最重要！
    params = GCN['weighted']
    pt_weights = params['pt_weight'] * np.exp(-pt_dists / params['r0'])
    sn_weights = params['sn_weight'] * np.exp(-sn_dists / params['r0'])
    pt_weights[pt_dists > params['cutoff']] = 0
    sn_weights[sn_dists > params['cutoff']] = 0
    w_gcn_loc = float(np.sum(pt_weights) + np.sum(sn_weights))
    
    # 3. Sn加权GCN
    params = GCN['sn_weighted']
    pt_mask = (pt_dists >= params['r_min']) & (pt_dists <= params['r_max'])
    sn_mask = (sn_dists >= params['r_min']) & (sn_dists <= params['r_max'])
    sn_w_gcn_loc = float(
        params['pt_weight'] * np.sum(pt_mask) +
        params['sn_weight'] * np.sum(sn_mask)
    )
    
    # 4. 壳层GCN
    shells = GCN['shell']['shells']
    shell_gcn_loc = 0.0
    for shell in shells:
        pt_count = np.sum((pt_dists >= shell['r_min']) & (pt_dists <= shell['r_max']))
        sn_count = np.sum((sn_dists >= shell['r_min']) & (sn_dists <= shell['r_max']))
        shell_gcn_loc += shell['pt_weight'] * pt_count + shell['sn_weight'] * sn_count
    shell_gcn_loc = float(shell_gcn_loc)
    
    return {
        'gcn_loc': gcn_loc,
        'w_gcn_loc': w_gcn_loc,
        'sn_w_gcn_loc': sn_w_gcn_loc,
        'shell_gcn_loc': shell_gcn_loc
    }


if __name__ == '__main__':
    print("配位数和GCN模块测试 v6.2.3")
    
    central_pt = np.array([0.0, 0.0, 0.0])
    pt_neighbors = np.array([[2.8, 0, 0], [0, 2.8, 0], [0, 0, 2.8]])
    sn_neighbors = np.array([[2.9, 0.5, 0], [0.5, 2.9, 0]])
    
    cn = calc_bond_specific_cn_smooth(central_pt, 'Pt', pt_neighbors, sn_neighbors)
    print(f"CN总计: {cn['cn_total']:.3f}")
    
    gcn = calc_gcn_descriptors(central_pt, pt_neighbors, sn_neighbors)
    print(f"wGCN: {gcn['w_gcn_loc']:.3f}")