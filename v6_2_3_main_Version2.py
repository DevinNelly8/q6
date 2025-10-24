#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Coordination Analysis v6.2.3 - 主脚本
==============================================

使用方法:
    python main.py --auto --output-dir ./results

作者: DevinNelly8
日期: 2025-10-24
版本: 6.2.3
"""

import sys
import os
import argparse
import numpy as np
import pandas as pd
import time
from pathlib import Path

# 添加模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules'))

from modules.config import PREPROCESS, COORDINATION, GCN, Q6_Q4, ELEMENTS, OUTPUT, DEBUG
from modules.coordination_module import calc_bond_specific_cn_smooth, calc_gcn_descriptors
from modules.q6_module import calc_q6_fast, calc_q4_fast, classify_structure_advanced
from modules.global_q6_module import calc_cluster_analysis
from modules.geometry_module import calc_geometry_statistics


# ==================== XYZ文件读取 ====================

def read_xyz_fast(xyz_file):
    """快速读取XYZ文件"""
    frames = []
    
    with open(xyz_file, 'r') as f:
        lines = f.readlines()
    
    i = 0
    while i < len(lines):
        try:
            n_atoms = int(lines[i].strip())
        except:
            i += 1
            continue
        
        if i + n_atoms + 1 >= len(lines):
            break
        
        # 跳过注释行
        i += 2
        
        elements = []
        positions = []
        
        for j in range(n_atoms):
            parts = lines[i + j].strip().split()
            if len(parts) >= 4:
                elements.append(parts[0])
                positions.append([float(parts[1]), float(parts[2]), float(parts[3])])
        
        frames.append({
            'elements': np.array(elements),
            'positions': np.array(positions, dtype=np.float64)
        })
        
        i += n_atoms
    
    return frames


def detect_elements(frames, target_elements):
    """检测轨迹中的元素"""
    all_elements = set()
    for frame in frames:
        all_elements.update(frame['elements'])
    
    detected = [e for e in target_elements if e in all_elements]
    
    element_counts = {}
    if len(frames) > 0:
        first_frame = frames[0]
        for elem in detected:
            element_counts[elem] = int(np.sum(first_frame['elements'] == elem))
    
    return detected, element_counts


# ==================== 主分析函数 ====================

def analyze_trajectory(xyz_file, output_dir=None, dt_ps=1.0, sample_interval=10):
    """
    主分析函数 v6.2.3
    
    Parameters:
    -----------
    xyz_file : str
        XYZ轨迹文件路径
    output_dir : str, optional
        输出目录
    dt_ps : float
        时间步长（ps）
    sample_interval : int
        采样间隔
    
    Returns:
    --------
    pd.DataFrame : 分析结果
    """
    print(f"⏳ 读取轨迹文件: {xyz_file}")
    start_time = time.time()
    
    frames = read_xyz_fast(xyz_file)
    if len(frames) == 0:
        print("❌ ERROR: 未读取到任何帧")
        return None
    
    print(f"✅ 读取完成: {len(frames)}帧 ({time.time()-start_time:.2f}s)")
    
    if output_dir is None:
        output_dir = os.getcwd()
    os.makedirs(output_dir, exist_ok=True)
    
    # 检测元素
    detected_elements, element_counts = detect_elements(frames, ELEMENTS['target_elements'])
    target_elements = [e for e in detected_elements if e in ELEMENTS['metal_elements']]
    
    if len(target_elements) == 0:
        print(f"❌ ERROR: 未检测到金属元素")
        return None
    
    print(f"✅ 检测到元素: {detected_elements}")
    print(f"✅ 金属元素: {target_elements}")
    for elem, count in element_counts.items():
        print(f"   {elem}: {count}个")
    
    # 统一的时间序列字典
    unified_time_series = {
        'frame': [],
        'time_ps': []
    }
    
    # 为每个元素添加列
    for elem in target_elements:
        unified_time_series[f'{elem}_cn_total'] = []
        unified_time_series[f'{elem}_cn_{elem}_{elem}'] = []
        
        if elem == 'Pt':
            unified_time_series[f'{elem}_cn_Pt_Sn'] = []
        elif elem == 'Sn':
            unified_time_series[f'{elem}_cn_Sn_Pt'] = []
        
        # ⭐ v6.2.3新增：GCN描述符
        if GCN['enable']:
            unified_time_series[f'{elem}_gcn_loc'] = []
            unified_time_series[f'{elem}_w_gcn_loc'] = []
            unified_time_series[f'{elem}_sn_w_gcn_loc'] = []
            unified_time_series[f'{elem}_shell_gcn_loc'] = []
        
        unified_time_series[f'{elem}_q6'] = []
        unified_time_series[f'{elem}_q4'] = []
        unified_time_series[f'{elem}_structure'] = []
    
    # 全局Q6时间序列
    global_q6_series = {
        'frame': [],
        'time_ps': [],
        'cluster_all_q6_global': [],      # ⭐ v6.2.3: PtSnO全局Q6
        'cluster_metal_q6_global': [],
        'pt_q6_global': [],
        'sn_q6_global': []
    }
    
    # 几何统计时间序列
    geometry_series = {
        'frame': [],
        'time_ps': [],
        'sn_avg_dist_to_center': [],
        'pt_avg_dist_to_center': [],
        'gyration_radius': []
    }
    
    # 逐帧分析
    print("\n⏳ 开始逐帧分析...")
    for frame_idx, frame in enumerate(frames):
        if (frame_idx + 1) % DEBUG['progress_interval'] == 0:
            print(f"  进度: {frame_idx+1}/{len(frames)}")
        
        elements = frame['elements']
        positions = frame['positions']
        
        pt_mask = elements == 'Pt'
        sn_mask = elements == 'Sn'
        
        pt_positions = positions[pt_mask]
        sn_positions = positions[sn_mask]
        
        # 计算全局Q6
        try:
            q6_result = calc_cluster_analysis(positions, elements, cutoff=Q6_Q4['q6_cutoff'])
            
            global_q6_series['frame'].append(frame_idx * sample_interval)
            global_q6_series['time_ps'].append(frame_idx * sample_interval * dt_ps)
            global_q6_series['cluster_all_q6_global'].append(q6_result['cluster']['q6_global'])
            global_q6_series['cluster_metal_q6_global'].append(q6_result.get('metal', {}).get('q6_global', 0.0))
            global_q6_series['pt_q6_global'].append(q6_result['Pt']['q6_global'])
            global_q6_series['sn_q6_global'].append(q6_result['Sn']['q6_global'])
        except Exception as e:
            if DEBUG['verbose']:
                print(f"  ⚠️  全局Q6计算失败（帧{frame_idx}）: {e}")
        
        # 计算几何统计
        try:
            geo_stats = calc_geometry_statistics(positions, elements)
            geometry_series['frame'].append(frame_idx * sample_interval)
            geometry_series['time_ps'].append(frame_idx * sample_interval * dt_ps)
            geometry_series['sn_avg_dist_to_center'].append(geo_stats['sn_avg_dist_to_center'])
            geometry_series['pt_avg_dist_to_center'].append(geo_stats['pt_avg_dist_to_center'])
            geometry_series['gyration_radius'].append(geo_stats['gyration_radius'])
        except:
            pass
        
        # 计算每个元素的配位数、GCN和局域Q6
        frame_data = {
            'frame': frame_idx * sample_interval, 
            'time_ps': frame_idx * sample_interval * dt_ps
        }
        
        for target_atom in target_elements:
            target_mask = elements == target_atom
            target_indices = np.where(target_mask)[0]
            
            if len(target_indices) == 0:
                continue
            
            frame_accumulator = {
                'cn_total': [],
                'cn_center_center': [],
                'cn_center_other': [],
                'gcn_loc': [],
                'w_gcn_loc': [],
                'sn_w_gcn_loc': [],
                'shell_gcn_loc': [],
                'q6': [],
                'q4': []
            }
            
            for target_idx in target_indices:
                central_pos = positions[target_idx]
                
                # ⭐ 配位数（平滑版本）
                bond_cn = calc_bond_specific_cn_smooth(
                    central_pos, target_atom, pt_positions, sn_positions
                )
                
                # ⭐ GCN描述符
                if GCN['enable']:
                    gcn_descriptors = calc_gcn_descriptors(
                        central_pos, pt_positions, sn_positions
                    )
                    frame_accumulator['gcn_loc'].append(gcn_descriptors['gcn_loc'])
                    frame_accumulator['w_gcn_loc'].append(gcn_descriptors['w_gcn_loc'])
                    frame_accumulator['sn_w_gcn_loc'].append(gcn_descriptors['sn_w_gcn_loc'])
                    frame_accumulator['shell_gcn_loc'].append(gcn_descriptors['shell_gcn_loc'])
                
                # 局域Q6/Q4
                q6 = calc_q6_fast(central_pos, positions, elements, cutoff=Q6_Q4['q6_cutoff'])
                q4 = calc_q4_fast(central_pos, positions, elements, cutoff=Q6_Q4['q6_cutoff'])
                
                frame_accumulator['cn_total'].append(bond_cn['cn_total'])
                frame_accumulator['cn_center_center'].append(bond_cn['cn_center_center'])
                frame_accumulator['cn_center_other'].append(bond_cn['cn_center_other'])
                frame_accumulator['q6'].append(q6)
                frame_accumulator['q4'].append(q4)
            
            if len(frame_accumulator['cn_total']) > 0:
                frame_data[f'{target_atom}_cn_total'] = np.mean(frame_accumulator['cn_total'])
                frame_data[f'{target_atom}_cn_{target_atom}_{target_atom}'] = np.mean(frame_accumulator['cn_center_center'])
                
                if target_atom == 'Pt':
                    frame_data[f'{target_atom}_cn_Pt_Sn'] = np.mean(frame_accumulator['cn_center_other'])
                elif target_atom == 'Sn':
                    frame_data[f'{target_atom}_cn_Sn_Pt'] = np.mean(frame_accumulator['cn_center_other'])
                
                # ⭐ GCN平均值
                if GCN['enable']:
                    frame_data[f'{target_atom}_gcn_loc'] = np.mean(frame_accumulator['gcn_loc'])
                    frame_data[f'{target_atom}_w_gcn_loc'] = np.mean(frame_accumulator['w_gcn_loc'])
                    frame_data[f'{target_atom}_sn_w_gcn_loc'] = np.mean(frame_accumulator['sn_w_gcn_loc'])
                    frame_data[f'{target_atom}_shell_gcn_loc'] = np.mean(frame_accumulator['shell_gcn_loc'])
                
                frame_data[f'{target_atom}_q6'] = np.mean(frame_accumulator['q6'])
                frame_data[f'{target_atom}_q4'] = np.mean(frame_accumulator['q4'])
                
                avg_q4 = np.mean(frame_accumulator['q4'])
                avg_q6 = np.mean(frame_accumulator['q6'])
                frame_data[f'{target_atom}_structure'] = classify_structure_advanced(avg_q4, avg_q6)
        
        # 添加到统一时间序列
        for key in unified_time_series.keys():
            if key in frame_data:
                unified_time_series[key].append(frame_data[key])
            elif key in ['frame', 'time_ps']:
                unified_time_series[key].append(frame_data[key])
            else:
                unified_time_series[key].append(np.nan)
    
    # ⭐ 保存到CSV文件
    print("\n⏳ 保存结果...")
    
    ts_df = pd.DataFrame(unified_time_series)
    ts_df.to_csv(os.path.join(output_dir, 'coordination_time_series.csv'), index=False)
    
    if len(global_q6_series['frame']) > 0:
        global_q6_df = pd.DataFrame(global_q6_series)
        global_q6_df.to_csv(
            os.path.join(output_dir, 'cluster_global_q6_time_series.csv'), index=False
        )
        
        print(f"\n✅ 全局Q6数据已保存")
        print(f"   PtSnO Q6: {global_q6_df['cluster_all_q6_global'].mean():.4f}")
        print(f"   Metal Q6: {global_q6_df['cluster_metal_q6_global'].mean():.4f}")
    
    if len(geometry_series['frame']) > 0:
        pd.DataFrame(geometry_series).to_csv(
            os.path.join(output_dir, 'cluster_geometry_time_series.csv'), index=False
        )
    
    # 生成元素对比表
    comparison_data = []
    for elem in target_elements:
        row = {'Element': elem}
        row['CN_total'] = ts_df[f'{elem}_cn_total'].mean()
        
        if GCN['enable']:
            row['wGCN'] = ts_df[f'{elem}_w_gcn_loc'].mean()
        
        row['Q6'] = ts_df[f'{elem}_q6'].mean()
        row['Q4'] = ts_df[f'{elem}_q4'].mean()
        
        comparison_data.append(row)
    
    pd.DataFrame(comparison_data).to_csv(
        os.path.join(output_dir, 'element_comparison.csv'), index=False
    )
    
    # 保存检测信息
    with open(os.path.join(output_dir, 'detection_info.txt'), 'w') as f:
        f.write(f"元素检测结果 v6.2.3\n")
        f.write(f"=====================\n")
        f.write(f"检测到的元素: {', '.join(detected_elements)}\n")
        f.write(f"金属元素: {', '.join(target_elements)}\n\n")
        f.write(f"各元素原子数:\n")
        for elem, count in element_counts.items():
            f.write(f"  {elem}: {count}\n")
        f.write(f"\n总帧数: {len(frames)}\n")
        f.write(f"\n关键改进 (v6.2.3):\n")
        f.write(f"  ✅ PLUMED平滑配位数\n")
        f.write(f"  ✅ 4种GCN描述符\n")
        f.write(f"  ✅ 全局Q6包含所有原子\n")
    
    total_time = time.time() - start_time
    print(f"\n✅ 分析完成: {total_time:.2f}s")
    print(f"✅ 结果保存至: {output_dir}")
    
    return ts_df


# ==================== 命令行接口 ====================

def main():
    """主程序入口"""
    parser = argparse.ArgumentParser(
        description='Enhanced Coordination Analysis v6.2.3',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python main.py --auto
  python main.py --auto --output-dir ./results
  python main.py sampling.xyz -o ./output --dt-ps 2.0
        """
    )
    
    parser.add_argument('xyz_file', nargs='?', default='sampling-simply_ase_unwrapped.xyz',
                        help='XYZ轨迹文件')
    parser.add_argument('--auto', action='store_true', help='自动模式')
    parser.add_argument('--output-dir', '-o', type=str, default=None, help='输出目录')
    parser.add_argument('--dt-ps', type=float, default=1.0, help='时间步长（ps）')
    parser.add_argument('--sample-interval', type=int, default=10, help='采样间隔')
    
    parser.add_argument('--rcut-pt-pt', type=float, default=COORDINATION['rcut_pt_pt'], 
                        help='Pt-Pt截断(Å)')
    parser.add_argument('--rcut-pt-sn', type=float, default=COORDINATION['rcut_pt_sn'],
                        help='Pt-Sn截断(Å)')
    parser.add_argument('--rcut-sn-sn', type=float, default=COORDINATION['rcut_sn_sn'],
                        help='Sn-Sn截断(Å)')
    parser.add_argument('--q6-cutoff', type=float, default=Q6_Q4['q6_cutoff'],
                        help='Q6/Q4截断(Å)')
    
    parser.add_argument('--disable-gcn', action='store_true', help='禁用GCN计算')
    parser.add_argument('--version', action='version', version='v6.2.3')
    
    args = parser.parse_args()
    
    print("="*70)
    print("Enhanced Coordination Analysis v6.2.3")
    print("="*70)
    print("✅ PLUMED平滑配位数")
    print("✅ 4种GCN描述符（标准、加权、Sn加权、壳层）")
    print("✅ 全局Q6包含所有原子（PtSnO）")
    print("="*70)
    
    # 更新配置
    COORDINATION['rcut_pt_pt'] = args.rcut_pt_pt
    COORDINATION['rcut_pt_sn'] = args.rcut_pt_sn
    COORDINATION['rcut_sn_sn'] = args.rcut_sn_sn
    Q6_Q4['q6_cutoff'] = args.q6_cutoff
    
    if args.disable_gcn:
        GCN['enable'] = False
        print("⚠️  GCN计算已禁用")
    
    # 查找XYZ文件
    xyz_file = args.xyz_file
    if args.auto:
        candidates = [
            'sampling-simply_ase_unwrapped.xyz',
            'sampling-simply.xyz'
        ]
        for candidate in candidates:
            if os.path.exists(candidate):
                xyz_file = candidate
                break
    
    if not os.path.exists(xyz_file):
        print(f"❌ ERROR: 文件不存在: {xyz_file}")
        sys.exit(1)
    
    print(f"\n✅ 使用文件: {xyz_file}")
    
    # 运行分析
    results = analyze_trajectory(
        xyz_file,
        args.output_dir,
        args.dt_ps,
        args.sample_interval
    )
    
    if results is None:
        print("❌ ERROR: 分析失败")
        sys.exit(1)
    
    print("\n" + "="*70)
    print("✅ SUCCESS")
    print("="*70)


if __name__ == '__main__':
    main()