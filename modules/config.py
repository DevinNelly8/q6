#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置参数模块 v6.2.3
===================

集中管理所有分析参数

作者: DevinNelly8
日期: 2025-10-24
"""

# ==================== 预处理参数 ====================
PREPROCESS = {
    'remove_bottom_n': 240,
    'default_sample_interval': 10,
    'source_filename': 'sampling-simply_ase_unwrapped.xyz',
    'n_frames_for_id': 1,
    'require_unwrapped': True,
}

# ==================== 配位数计算参数 ====================
COORDINATION = {
    'rcut_pt_pt': 3.0,
    'rcut_pt_sn': 3.2,
    'rcut_sn_sn': 3.4,
    
    # ⭐ PLUMED平滑函数参数
    'plumed': {
        'pt_pt': {'R0': 2.9, 'NN': 6, 'MM': 12, 'D0': 0.1, 'Dmax': 10.0},
        'pt_sn': {'R0': 3.1, 'NN': 6, 'MM': 12, 'D0': 0.1, 'Dmax': 10.0},
        'sn_sn': {'R0': 3.3, 'NN': 6, 'MM': 12, 'D0': 0.1, 'Dmax': 10.0},
    }
}

# ==================== GCN计算参数 ====================
GCN = {
    'enable': True,
    
    'standard': {
        'r0': 0.3,
        'cutoff': 3.0
    },
    
    'weighted': {
        'r0': 0.3,
        'pt_weight': 1.0,
        'sn_weight': 2.0,
        'cutoff': 3.0
    },
    
    'sn_weighted': {
        'r_min': 2.0,
        'r_max': 2.8,
        'pt_weight': 0.8,
        'sn_weight': 2.5
    },
    
    'shell': {
        'shells': [
            {'r_min': 2.0, 'r_max': 2.5, 'pt_weight': 1.0, 'sn_weight': 3.0},
            {'r_min': 2.5, 'r_max': 3.0, 'pt_weight': 0.8, 'sn_weight': 2.0},
            {'r_min': 3.0, 'r_max': 3.5, 'pt_weight': 0.2, 'sn_weight': 0.6}
        ]
    }
}

# ==================== Q6/Q4参数 ====================
Q6_Q4 = {
    'q6_cutoff': 3.5,
    'include_oxygen_in_local': False,
    'l_q6': 6,
    'l_q4': 4,
}

# ==================== 全局Q6参数 ====================
GLOBAL_Q6 = {
    'save_global_q6': True,
    'cutoff': 3.5,
    'calculate_surface_core': True,
}

# ==================== 几何分析参数 ====================
GEOMETRY = {
    'save_geometry': True,
    'calculate_gyration': True,
    'surface_percentile': 70,
}

# ==================== 元素配置 ====================
ELEMENTS = {
    'target_elements': ['Pt', 'Sn', 'O'],
    'metal_elements': ['Pt', 'Sn'],
}

# ==================== 输出配置 ====================
OUTPUT = {
    'save_npz': True,
    'save_csv': True,
    'output_dir': None,
}

# ==================== 调试选项 ====================
DEBUG = {
    'verbose': True,
    'validate_data': True,
    'progress_interval': 50,
}