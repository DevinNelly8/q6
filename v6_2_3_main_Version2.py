#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enhanced Coordination Analysis v6.2.3 - 主脚本
==============================================

使用方法:
    python v6_2_3_main_Version2.py --auto --output-dir ./results
"""

from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from pathlib import Path
from typing import Dict, List

# 添加模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'modules'))

from modules.config import GCN, Q6_Q4, ELEMENTS, DEBUG
from modules.coordination_module import calc_bond_specific_cn_smooth, calc_gcn_descriptors
from modules.q6_module import calc_q6_fast, calc_q4_fast, classify_structure_advanced
from modules.global_q6_module import calc_cluster_analysis
from modules.geometry_module import calc_geometry_statistics
from modules.math_utils import mean


# ==================== XYZ文件读取 ====================

def read_xyz_fast(xyz_file):
    """快速读取XYZ文件"""
    frames: List[Dict[str, List]] = []

    with open(xyz_file, 'r') as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):
        try:
            n_atoms = int(lines[i].strip())
        except ValueError:
            i += 1
            continue

        if i + n_atoms + 1 >= len(lines):
            break

        i += 2  # 跳过注释行

        elements: List[str] = []
        positions: List[List[float]] = []

        for j in range(n_atoms):
            parts = lines[i + j].strip().split()
            if len(parts) >= 4:
                elements.append(parts[0])
                positions.append([float(parts[1]), float(parts[2]), float(parts[3])])

        frames.append({
            'elements': elements,
            'positions': positions,
        })

        i += n_atoms

    return frames


def detect_elements(frames, target_elements):
    """检测轨迹中的元素"""
    all_elements = set()
    for frame in frames:
        all_elements.update(frame['elements'])

    detected = [e for e in target_elements if e in all_elements]

    element_counts: Dict[str, int] = {}
    if frames:
        first_frame = frames[0]
        for elem in detected:
            element_counts[elem] = sum(1 for symbol in first_frame['elements'] if symbol == elem)

    return detected, element_counts


# ==================== 辅助输出函数 ====================

def ensure_directory(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def write_csv(path: str, fieldnames: List[str], rows: List[Dict[str, object]]):
    with open(path, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, '') for key in fieldnames})


def average_or_zero(values: List[float]) -> float:
    valid = [value for value in values if value == value]
    return mean(valid) if valid else 0.0


# ==================== 主分析函数 ====================

def analyze_trajectory(xyz_file, output_dir=None, dt_ps=1.0, sample_interval=10):
    print(f"⏳ 读取轨迹文件: {xyz_file}")
    start_time = time.time()

    frames = read_xyz_fast(xyz_file)
    if not frames:
        print("❌ ERROR: 未读取到任何帧")
        return None

    print(f"✅ 读取完成: {len(frames)}帧 ({time.time()-start_time:.2f}s)")

    if output_dir is None:
        output_dir = os.getcwd()
    ensure_directory(output_dir)

    detected_elements, element_counts = detect_elements(frames, ELEMENTS['target_elements'])
    target_elements = [e for e in detected_elements if e in ELEMENTS['metal_elements']]

    if not target_elements:
        print("❌ ERROR: 未检测到金属元素")
        return None

    print(f"✅ 检测到元素: {detected_elements}")
    print(f"✅ 金属元素: {target_elements}")
    for elem, count in element_counts.items():
        print(f"   {elem}: {count}个")

    # 预定义列
    base_columns = ['frame', 'time_ps']
    per_element_columns = []
    for elem in target_elements:
        per_element_columns.extend([
            f'{elem}_cn_total',
            f'{elem}_cn_{elem}_{elem}',
        ])
        if elem == 'Pt':
            per_element_columns.append(f'{elem}_cn_Pt_Sn')
        elif elem == 'Sn':
            per_element_columns.append(f'{elem}_cn_Sn_Pt')

        if GCN['enable']:
            per_element_columns.extend([
                f'{elem}_gcn_loc',
                f'{elem}_w_gcn_loc',
                f'{elem}_sn_w_gcn_loc',
                f'{elem}_shell_gcn_loc',
            ])

        per_element_columns.extend([
            f'{elem}_q6',
            f'{elem}_q4',
            f'{elem}_structure',
        ])

    time_series_columns = base_columns + per_element_columns
    unified_time_series = {col: [] for col in time_series_columns}

    global_q6_rows: List[Dict[str, object]] = []
    geometry_rows: List[Dict[str, object]] = []

    print("\n⏳ 开始逐帧分析...")
    for frame_idx, frame in enumerate(frames):
        if (frame_idx + 1) % DEBUG['progress_interval'] == 0:
            print(f"  进度: {frame_idx+1}/{len(frames)}")

        elements = frame['elements']
        positions = frame['positions']

        pt_positions = [pos for pos, elem in zip(positions, elements) if elem == 'Pt']
        sn_positions = [pos for pos, elem in zip(positions, elements) if elem == 'Sn']

        frame_number = frame_idx * sample_interval
        frame_time = frame_number * dt_ps

        # 全局Q6
        try:
            q6_result = calc_cluster_analysis(positions, elements, cutoff=Q6_Q4['q6_cutoff'])
            global_q6_rows.append({
                'frame': frame_number,
                'time_ps': frame_time,
                'cluster_all_q6_global': q6_result['cluster']['q6_global'],
                'cluster_metal_q6_global': q6_result.get('metal', {}).get('q6_global', 0.0),
                'pt_q6_global': q6_result['Pt']['q6_global'],
                'sn_q6_global': q6_result['Sn']['q6_global'],
            })
        except Exception as exc:
            if DEBUG['verbose']:
                print(f"  ⚠️  全局Q6计算失败（帧{frame_idx}）: {exc}")

        # 几何统计
        try:
            geo_stats = calc_geometry_statistics(positions, elements)
            geometry_rows.append({
                'frame': frame_number,
                'time_ps': frame_time,
                'sn_avg_dist_to_center': geo_stats['sn_avg_dist_to_center'],
                'pt_avg_dist_to_center': geo_stats['pt_avg_dist_to_center'],
                'gyration_radius': geo_stats['gyration_radius'],
            })
        except Exception as exc:
            if DEBUG['verbose']:
                print(f"  ⚠️  几何统计失败（帧{frame_idx}）: {exc}")

        frame_row: Dict[str, object] = {
            'frame': frame_number,
            'time_ps': frame_time,
        }

        for target_atom in target_elements:
            target_indices = [idx for idx, elem in enumerate(elements) if elem == target_atom]
            if not target_indices:
                continue

            cn_total_values: List[float] = []
            cn_center_center_values: List[float] = []
            cn_center_other_values: List[float] = []
            gcn_loc_values: List[float] = []
            w_gcn_values: List[float] = []
            sn_w_gcn_values: List[float] = []
            shell_gcn_values: List[float] = []
            q6_values: List[float] = []
            q4_values: List[float] = []

            for target_idx in target_indices:
                central_pos = positions[target_idx]

                bond_cn = calc_bond_specific_cn_smooth(
                    central_pos, target_atom, pt_positions, sn_positions
                )

                if GCN['enable']:
                    gcn_descriptors = calc_gcn_descriptors(
                        central_pos, pt_positions, sn_positions
                    )
                    gcn_loc_values.append(gcn_descriptors['gcn_loc'])
                    w_gcn_values.append(gcn_descriptors['w_gcn_loc'])
                    sn_w_gcn_values.append(gcn_descriptors['sn_w_gcn_loc'])
                    shell_gcn_values.append(gcn_descriptors['shell_gcn_loc'])

                q6 = calc_q6_fast(central_pos, positions, elements, cutoff=Q6_Q4['q6_cutoff'])
                q4 = calc_q4_fast(central_pos, positions, elements, cutoff=Q6_Q4['q6_cutoff'])

                cn_total_values.append(bond_cn['cn_total'])
                cn_center_center_values.append(bond_cn['cn_center_center'])
                cn_center_other_values.append(bond_cn['cn_center_other'])
                q6_values.append(q6)
                q4_values.append(q4)

            if cn_total_values:
                frame_row[f'{target_atom}_cn_total'] = mean(cn_total_values)
                frame_row[f'{target_atom}_cn_{target_atom}_{target_atom}'] = mean(cn_center_center_values)

                if target_atom == 'Pt':
                    frame_row[f'{target_atom}_cn_Pt_Sn'] = mean(cn_center_other_values)
                elif target_atom == 'Sn':
                    frame_row[f'{target_atom}_cn_Sn_Pt'] = mean(cn_center_other_values)

                if GCN['enable']:
                    frame_row[f'{target_atom}_gcn_loc'] = mean(gcn_loc_values)
                    frame_row[f'{target_atom}_w_gcn_loc'] = mean(w_gcn_values)
                    frame_row[f'{target_atom}_sn_w_gcn_loc'] = mean(sn_w_gcn_values)
                    frame_row[f'{target_atom}_shell_gcn_loc'] = mean(shell_gcn_values)

                avg_q6 = mean(q6_values)
                avg_q4 = mean(q4_values)
                frame_row[f'{target_atom}_q6'] = avg_q6
                frame_row[f'{target_atom}_q4'] = avg_q4
                frame_row[f'{target_atom}_structure'] = classify_structure_advanced(avg_q4, avg_q6)

        for column in time_series_columns:
            unified_time_series[column].append(frame_row.get(column, ''))

    print("\n⏳ 保存结果...")

    # 写入配位时间序列
    time_series_rows = []
    for idx in range(len(unified_time_series['frame'])):
        row = {column: unified_time_series[column][idx] for column in time_series_columns}
        time_series_rows.append(row)
    write_csv(os.path.join(output_dir, 'coordination_time_series.csv'), time_series_columns, time_series_rows)

    if global_q6_rows:
        write_csv(
            os.path.join(output_dir, 'cluster_global_q6_time_series.csv'),
            ['frame', 'time_ps', 'cluster_all_q6_global', 'cluster_metal_q6_global', 'pt_q6_global', 'sn_q6_global'],
            global_q6_rows,
        )
        all_q6_avg = average_or_zero([row['cluster_all_q6_global'] for row in global_q6_rows])
        metal_q6_avg = average_or_zero([row['cluster_metal_q6_global'] for row in global_q6_rows])
        print(f"\n✅ 全局Q6数据已保存")
        print(f"   PtSnO Q6: {all_q6_avg:.4f}")
        print(f"   Metal Q6: {metal_q6_avg:.4f}")

    if geometry_rows:
        write_csv(
            os.path.join(output_dir, 'cluster_geometry_time_series.csv'),
            ['frame', 'time_ps', 'sn_avg_dist_to_center', 'pt_avg_dist_to_center', 'gyration_radius'],
            geometry_rows,
        )

    comparison_data = []
    for elem in target_elements:
        row = {'Element': elem}
        cn_values = [value for value in unified_time_series[f'{elem}_cn_total'] if value != '']
        q6_values = [value for value in unified_time_series[f'{elem}_q6'] if value != '']
        q4_values = [value for value in unified_time_series[f'{elem}_q4'] if value != '']
        row['CN_total'] = average_or_zero(cn_values)

        if GCN['enable']:
            wgcn_values = [value for value in unified_time_series[f'{elem}_w_gcn_loc'] if value != '']
            row['wGCN'] = average_or_zero(wgcn_values)

        row['Q6'] = average_or_zero(q6_values)
        row['Q4'] = average_or_zero(q4_values)
        comparison_data.append(row)

    comparison_columns = ['Element', 'CN_total']
    if GCN['enable']:
        comparison_columns.append('wGCN')
    comparison_columns.extend(['Q6', 'Q4'])
    write_csv(os.path.join(output_dir, 'element_comparison.csv'), comparison_columns, comparison_data)

    with open(os.path.join(output_dir, 'detection_info.txt'), 'w') as f:
        f.write("元素检测结果 v6.2.3\n")
        f.write("=====================\n")
        f.write(f"检测到的元素: {', '.join(detected_elements)}\n")
        f.write(f"金属元素: {', '.join(target_elements)}\n\n")
        f.write("各元素原子数:\n")
        for elem, count in element_counts.items():
            f.write(f"  {elem}: {count}\n")
        f.write(f"\n总帧数: {len(frames)}\n")
        f.write("\n关键改进 (v6.2.3):\n")
        f.write("  - 平滑配位函数\n")
        f.write("  - GCN描述符\n")
        f.write("  - 全局/局域Q6\n")

    print("\n🎉 分析完成!")
    return unified_time_series


# ==================== CLI入口 ====================

def parse_args(argv=None):
    parser = argparse.ArgumentParser(description='Enhanced Coordination Analysis v6.2.3')
    parser.add_argument('xyz_file', nargs='?', help='XYZ轨迹文件路径')
    parser.add_argument('--auto', action='store_true', help='自动搜索默认XYZ文件')
    parser.add_argument('--output-dir', default='analysis_results', help='输出目录')
    parser.add_argument('--dt-ps', type=float, default=1.0, help='时间步长 (ps)')
    parser.add_argument('--sample-interval', type=int, default=10, help='采样间隔')
    return parser.parse_args(argv)


def auto_detect_xyz_file():
    candidates = ['sampling-simply_ase_unwrapped.xyz', 'sampling-simply.xyz']
    for candidate in candidates:
        path = Path(candidate)
        if path.exists():
            return str(path)
    return None


def main(argv=None):
    args = parse_args(argv)

    if args.auto:
        detected = auto_detect_xyz_file()
        if not detected:
            print("❌ ERROR: 未在当前目录找到默认XYZ文件")
            return 1
        xyz_path = detected
    else:
        if not args.xyz_file:
            print("❌ ERROR: 请提供XYZ文件路径或使用 --auto")
            return 1
        xyz_path = args.xyz_file

    if not os.path.exists(xyz_path):
        print(f"❌ ERROR: 文件不存在: {xyz_path}")
        return 1

    analyze_trajectory(
        xyz_path,
        output_dir=args.output_dir,
        dt_ps=args.dt_ps,
        sample_interval=args.sample_interval,
    )
    return 0


if __name__ == '__main__':
    sys.exit(main())
