"""Light-weight geometry descriptors used by the analysis pipeline."""

from __future__ import annotations

from math import sqrt
from typing import Sequence

from .math_utils import mean, vector_norm, vector_sub


def _average_distance(radial_distances: Sequence[float], mask: Sequence[bool]) -> float:
    if not radial_distances or not any(mask):
        return 0.0
    selected = [dist for dist, flag in zip(radial_distances, mask) if flag]
    return mean(selected)


def calc_geometry_statistics(positions: Sequence[Sequence[float]], elements: Sequence[str]):
    """Compute coarse geometric descriptors for the current frame."""

    if not positions or not elements:
        return {
            "sn_avg_dist_to_center": 0.0,
            "pt_avg_dist_to_center": 0.0,
            "gyration_radius": 0.0,
        }

    count = len(positions)
    center = [sum(pos[idx] for pos in positions) / count for idx in range(3)]
    displacements = [vector_sub(pos, center) for pos in positions]
    radial_distances = [vector_norm(vec) for vec in displacements]

    sn_mask = [elem == "Sn" for elem in elements]
    pt_mask = [elem == "Pt" for elem in elements]

    mean_square = sum(vec[0] ** 2 + vec[1] ** 2 + vec[2] ** 2 for vec in displacements) / count
    gyration_radius = sqrt(mean_square)

    return {
        "sn_avg_dist_to_center": _average_distance(radial_distances, sn_mask),
        "pt_avg_dist_to_center": _average_distance(radial_distances, pt_mask),
        "gyration_radius": float(gyration_radius),
    }


__all__ = ["calc_geometry_statistics"]
