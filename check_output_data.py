#!/usr/bin/env python3
"""Validate analysis output data for Enhanced Coordination Analysis v6.2.3.

This script inspects the generated CSV/TXT files to make sure that:
* Required files are present and readable.
* Numeric columns contain finite values in a sensible range.
* No column is dominated by missing data.

It is intended as a lightweight regression guard to quickly spot corrupted
results without re-running the heavy trajectory analysis.
"""

from __future__ import annotations

import argparse
import csv
import math
import os
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

# Expected files written by ``analyze_trajectory``
REQUIRED_FILES = [
    "coordination_time_series.csv",
    "element_comparison.csv",
    "detection_info.txt",
]

OPTIONAL_FILES = [
    "cluster_global_q6_time_series.csv",
    "cluster_geometry_time_series.csv",
]


@dataclass
class ColumnStats:
    name: str
    count: int = 0
    missing: int = 0
    nan: int = 0
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    sum_value: float = 0.0

    def register(self, raw: str) -> None:
        if raw is None or raw == "":
            self.missing += 1
            return

        try:
            value = float(raw)
        except ValueError:
            self.nan += 1
            return

        if math.isnan(value) or math.isinf(value):
            self.nan += 1
            return

        self.count += 1
        self.sum_value += value
        if self.min_value is None or value < self.min_value:
            self.min_value = value
        if self.max_value is None or value > self.max_value:
            self.max_value = value

    @property
    def mean(self) -> Optional[float]:
        if self.count:
            return self.sum_value / self.count
        return None

    def completeness(self, total_rows: int) -> float:
        if total_rows == 0:
            return 0.0
        return (total_rows - self.missing) / total_rows


# Broad, physics-informed ranges for sanity checks. The upper bounds are
# intentionally loose to avoid false positives while still catching egregious
# errors such as swapped units.
COLUMN_RANGES: List[Tuple[str, float, float]] = [
    ("frame", 0, float("inf")),
    ("time_ps", 0.0, float("inf")),
    ("_cn_", 0.0, 20.0),
    ("_q6", 0.0, 1.5),
    ("_q4", 0.0, 1.5),
    ("gcn", 0.0, 30.0),
    ("dist", 0.0, float("inf")),
    ("radius", 0.0, float("inf")),
]


def collect_csv_stats(path: str) -> Tuple[List[ColumnStats], List[Dict[str, str]]]:
    with open(path, "r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    stats: Dict[str, ColumnStats] = {name: ColumnStats(name) for name in reader.fieldnames or []}
    for row in rows:
        for name, raw in row.items():
            stats[name].register(raw)

    return list(stats.values()), rows


def check_ranges(stats: Sequence[ColumnStats]) -> List[str]:
    issues: List[str] = []
    for column in stats:
        if column.count == 0:
            continue
        for marker, lower, upper in COLUMN_RANGES:
            if marker in column.name:
                if column.min_value is not None and column.min_value < lower:
                    issues.append(
                        f"列 {column.name} 包含小于 {lower} 的值 (最小值 {column.min_value:.4g})"
                    )
                if column.max_value is not None and column.max_value > upper:
                    issues.append(
                        f"列 {column.name} 包含大于 {upper} 的值 (最大值 {column.max_value:.4g})"
                    )
                break
    return issues


def summarize_stats(stats: Sequence[ColumnStats], total_rows: int) -> str:
    important = [
        column
        for column in stats
        if any(marker in column.name for marker in ("_cn_", "_q6", "_q4", "gcn"))
    ]
    lines: List[str] = []
    for column in important:
        completeness = column.completeness(total_rows) * 100 if total_rows else 0.0
        mean_value = column.mean
        mean_str = f"{mean_value:.4f}" if mean_value is not None else "—"
        lines.append(
            f"  {column.name:30s} 完整度 {completeness:5.1f}%  平均 {mean_str}"
        )
    return "\n".join(lines)


def check_detection_info(path: str) -> List[str]:
    issues: List[str] = []
    try:
        with open(path, "r", encoding="utf-8") as handle:
            content = handle.read()
    except OSError as exc:
        return [f"无法读取 detection_info.txt: {exc}"]

    required_tokens = ["元素检测结果", "金属元素", "总帧数"]
    for token in required_tokens:
        if token not in content:
            issues.append(f"detection_info.txt 缺少关键字段: {token}")
    return issues


class Reporter:
    """Collect human-readable messages while also streaming them to stdout."""

    def __init__(self) -> None:
        self.lines: List[str] = []

    def add(self, message: str = "") -> None:
        print(message)
        self.lines.append(message)

    def extend(self, messages: Sequence[str]) -> None:
        for message in messages:
            self.add(message)

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("\n".join(self.lines))
            if self.lines and not self.lines[-1].endswith("\n"):
                handle.write("\n")


def check_directory(result_dir: str, reporter: Reporter) -> int:
    reporter.add(f"检查输出目录: {result_dir}\n{'=' * 60}")

    all_issues: List[str] = []
    exit_code = 0

    # Required files must exist.
    for name in REQUIRED_FILES:
        path = os.path.join(result_dir, name)
        if not os.path.exists(path):
            all_issues.append(f"缺少必要文件: {name}")
            exit_code = 1

    # Optional files: warn if missing but do not fail.
    for name in OPTIONAL_FILES:
        path = os.path.join(result_dir, name)
        if not os.path.exists(path):
            reporter.add(f"⚠️ 可选文件缺失: {name}")

    # Analyse CSV files that are present.
    for csv_name in REQUIRED_FILES + OPTIONAL_FILES:
        if not csv_name.endswith(".csv"):
            continue
        path = os.path.join(result_dir, csv_name)
        if not os.path.exists(path):
            continue
        try:
            stats, rows = collect_csv_stats(path)
        except Exception as exc:  # pragma: no cover - safeguard
            all_issues.append(f"读取 {csv_name} 失败: {exc}")
            exit_code = 1
            continue

        total_rows = len(rows)
        reporter.add("")
        reporter.add(f"{csv_name}: {total_rows} 行")
        numeric_issues = check_ranges(stats)
        missing_ratio: Dict[str, float] = {}
        for column in stats:
            if total_rows:
                ratio = column.missing / total_rows
                if ratio > 0.25:
                    missing_ratio[column.name] = ratio
            if column.nan:
                numeric_issues.append(
                    f"列 {column.name} 包含 {column.nan} 个无法解析的数值"
                )
        if missing_ratio:
            all_issues.append(
                "; ".join(
                    f"列 {name} 缺失率 {ratio*100:.1f}%" for name, ratio in missing_ratio.items()
                )
            )
            exit_code = 1
        if numeric_issues:
            all_issues.extend(numeric_issues)
            exit_code = 1
        summary = summarize_stats(stats, total_rows)
        if summary:
            reporter.extend(summary.splitlines())

    detection_path = os.path.join(result_dir, "detection_info.txt")
    all_issues.extend(check_detection_info(detection_path))
    if any(issue for issue in all_issues if "缺少关键字段" in issue):
        exit_code = 1

    if all_issues:
        reporter.add("")
        reporter.add("发现以下问题:")
        for issue in all_issues:
            reporter.add(f" - {issue}")
    else:
        reporter.add("")
        reporter.add("✓ 未发现问题")

    return exit_code


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="检查 Enhanced Coordination Analysis 输出目录的数据质量"
    )
    parser.add_argument(
        "result_dir",
        help="分析输出目录 (包含 coordination_time_series.csv 等文件)",
    )
    parser.add_argument(
        "--report",
        help="若提供则将检查结果写入指定文件",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    if not os.path.isdir(args.result_dir):
        print(f"❌ 目录不存在: {args.result_dir}")
        return 1
    reporter = Reporter()
    exit_code = check_directory(args.result_dir, reporter)
    if args.report:
        try:
            reporter.save(args.report)
        except OSError as exc:
            print(f"❌ 无法写入报告 {args.report}: {exc}")
            return 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
