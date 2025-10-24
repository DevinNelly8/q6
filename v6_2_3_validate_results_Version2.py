#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
结果验证脚本 v6.2.3
====================

验证分析结果的正确性和完整性

作者: DevinNelly8
日期: 2025-10-24
"""

import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path


def validate_csv_file(filepath, expected_columns=None):
    """验证CSV文件"""
    if not os.path.exists(filepath):
        return False, f"文件不存在: {filepath}"
    
    try:
        df = pd.read_csv(filepath)
    except Exception as e:
        return False, f"读取失败: {e}"
    
    if len(df) == 0:
        return False, "文件为空"
    
    if expected_columns:
        missing = set(expected_columns) - set(df.columns)
        if missing:
            return False, f"缺少列: {missing}"
    
    return True, f"✓ {len(df)}行数据"


def validate_coordination_file(filepath):
    """验证配位数文件"""
    required_cols = ['frame', 'time_ps']
    
    valid, msg = validate_csv_file(filepath, required_cols)
    if not valid:
        return valid, msg
    
    df = pd.read_csv(filepath)
    
    # 检查GCN列（v6.2.3新增）
    gcn_cols = [col for col in df.columns if 'gcn' in col.lower()]
    
    # 统计信息
    stats = {
        'frames': len(df),
        'gcn_columns': len(gcn_cols),
        'has_wgcn': any('w_gcn_loc' in col for col in df.columns)
    }
    
    # 检查数据合理性
    for col in df.columns:
        if 'cn_' in col:
            cn_values = df[col].dropna()
            if len(cn_values) > 0:
                avg_cn = cn_values.mean()
                if avg_cn < 0 or avg_cn > 20:
                    return False, f"配位数异常: {col} 平均值={avg_cn:.2f}"
    
    info = f"✓ {stats['frames']}帧, {stats['gcn_columns']}个GCN列"
    if stats['has_wgcn']:
        info += " [✓ wGCN]"
    
    return True, info


def validate_global_q6_file(filepath):
    """验证全局Q6文件"""
    required_cols = ['frame', 'time_ps', 'cluster_all_q6_global']
    
    valid, msg = validate_csv_file(filepath, required_cols)
    if not valid:
        return valid, msg
    
    df = pd.read_csv(filepath)
    
    # 检查cluster_all列（v6.2.3新增）
    has_cluster_all = 'cluster_all_q6_global' in df.columns
    
    if has_cluster_all:
        avg_q6_all = df['cluster_all_q6_global'].mean()
        info = f"✓ {len(df)}帧, PtSnO Q6={avg_q6_all:.4f}"
    else:
        info = f"⚠ 缺少cluster_all_q6_global列"
    
    return True, info


def validate_directory(result_dir):
    """验证单个结果目录"""
    print(f"\n{'='*60}")
    print(f"验证目录: {result_dir}")
    print(f"{'='*60}")
    
    required_files = {
        'coordination_time_series.csv': validate_coordination_file,
        'cluster_global_q6_time_series.csv': validate_global_q6_file,
        'element_comparison.csv': validate_csv_file,
        'detection_info.txt': lambda f: (os.path.exists(f), "✓" if os.path.exists(f) else "✗")
    }
    
    all_valid = True
    
    for filename, validator in required_files.items():
        filepath = os.path.join(result_dir, filename)
        
        valid, msg = validator(filepath)
        
        status = "✓" if valid else "✗"
        print(f"{status} {filename:40s} {msg}")
        
        if not valid:
            all_valid = False
    
    return all_valid


def validate_batch_results(batch_root):
    """验证批量结果"""
    print(f"\n{'='*60}")
    print(f"批量验证: {batch_root}")
    print(f"{'='*60}")
    
    subdirs = [d for d in Path(batch_root).iterdir() if d.is_dir() and d.name != 'logs']
    
    if len(subdirs) == 0:
        print("✗ 未找到结果目录")
        return False
    
    print(f"\n找到 {len(subdirs)} 个结果目录\n")
    
    valid_count = 0
    invalid_count = 0
    
    for subdir in subdirs:
        if validate_directory(str(subdir)):
            valid_count += 1
        else:
            invalid_count += 1
    
    print(f"\n{'='*60}")
    print(f"验证完成")
    print(f"{'='*60}")
    print(f"总计: {len(subdirs)}")
    print(f"有效: {valid_count}")
    print(f"无效: {invalid_count}")
    
    return invalid_count == 0


def main():
    """主程序"""
    if len(sys.argv) < 2:
        print("用法: python validate_results.py <结果目录>")
        print("\n示例:")
        print("  python validate_results.py ./results")
        print("  python validate_results.py ./batch_results_20251024_055823")
        sys.exit(1)
    
    target_dir = sys.argv[1]
    
    if not os.path.exists(target_dir):
        print(f"✗ 目录不存在: {target_dir}")
        sys.exit(1)
    
    # 判断是单个目录还是批量目录
    if os.path.exists(os.path.join(target_dir, 'logs')):
        # 批量结果
        success = validate_batch_results(target_dir)
    else:
        # 单个结果
        success = validate_directory(target_dir)
    
    if success:
        print("\n✓ 所有验证通过！")
        sys.exit(0)
    else:
        print("\n✗ 验证失败")
        sys.exit(1)


if __name__ == '__main__':
    main()