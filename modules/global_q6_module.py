"""Utilities for computing simple global Q6 descriptors."""

from __future__ import annotations

from typing import Sequence

from .config import ELEMENTS, Q6_Q4
from .q6_module import calc_q6_fast


def _average_q6_for_mask(positions: Sequence[Sequence[float]], elements: Sequence[str], mask, cutoff: float) -> float:
    indices = [idx for idx, flag in enumerate(mask) if flag]
    if not indices:
        return 0.0

    values = []
    for idx in indices:
        value = calc_q6_fast(positions[idx], positions, elements, cutoff=cutoff)
        if not _is_nan(value):
            values.append(value)
    if not values:
        return 0.0
    return sum(values) / len(values)


def calc_cluster_analysis(positions: Sequence[Sequence[float]], elements: Sequence[str], cutoff: float | None = None):
    """Compute simple global Q6 statistics for the provided structure."""

    if cutoff is None:
        cutoff = Q6_Q4["q6_cutoff"]

    if not positions or not elements:
        return {
            "cluster": {"count": 0, "q6_global": 0.0},
            "metal": {},
            "Pt": {"count": 0, "q6_global": 0.0},
            "Sn": {"count": 0, "q6_global": 0.0},
        }

    pt_mask = [elem == "Pt" for elem in elements]
    sn_mask = [elem == "Sn" for elem in elements]
    metal_elements = set(ELEMENTS.get("metal_elements", []))
    metal_mask = [elem in metal_elements for elem in elements]
    all_mask = [True] * len(elements)

    result = {
        "cluster": {
            "count": len(elements),
            "q6_global": _average_q6_for_mask(positions, elements, all_mask, cutoff),
        },
        "metal": {},
        "Pt": {
            "count": sum(1 for flag in pt_mask if flag),
            "q6_global": _average_q6_for_mask(positions, elements, pt_mask, cutoff),
        },
        "Sn": {
            "count": sum(1 for flag in sn_mask if flag),
            "q6_global": _average_q6_for_mask(positions, elements, sn_mask, cutoff),
        },
    }

    if any(metal_mask):
        result["metal"] = {
            "count": sum(1 for flag in metal_mask if flag),
            "q6_global": _average_q6_for_mask(positions, elements, metal_mask, cutoff),
        }

    return result


def _is_nan(value: float) -> bool:
    return value != value


__all__ = ["calc_cluster_analysis"]
