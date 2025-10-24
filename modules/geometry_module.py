"""Light-weight geometry descriptors used by the analysis pipeline."""

from __future__ import annotations

import numpy as np


def _average_distance(radial_distances: np.ndarray, mask: np.ndarray) -> float:
    """Return the average radial distance for the atoms selected by *mask*.

    The helper falls back to ``0.0`` when the mask selects no atoms to keep the
    downstream CSV writer simple.
    """

    if radial_distances.size == 0 or not np.any(mask):
        return 0.0

    return float(np.mean(radial_distances[mask]))


def calc_geometry_statistics(positions: np.ndarray, elements: np.ndarray):
    """Compute coarse geometric descriptors for the current frame.

    The implementation intentionally keeps the calculations light-weight so
    that it can serve as a reasonable default in the absence of the original
    proprietary module.  The following metrics are reported:

    ``sn_avg_dist_to_center``
        Mean distance of Sn atoms to the geometric center.
    ``pt_avg_dist_to_center``
        Mean distance of Pt atoms to the geometric center.
    ``gyration_radius``
        Square-root of the mean squared distance of all atoms to the center.
    """

    positions = np.asarray(positions, dtype=float)
    elements = np.asarray(elements)

    if positions.size == 0 or elements.size == 0:
        return {
            "sn_avg_dist_to_center": 0.0,
            "pt_avg_dist_to_center": 0.0,
            "gyration_radius": 0.0,
        }

    center = positions.mean(axis=0)
    displacements = positions - center
    radial_distances = np.linalg.norm(displacements, axis=1)

    sn_mask = elements == "Sn"
    pt_mask = elements == "Pt"

    gyration_radius = float(np.sqrt(np.mean(np.sum(displacements**2, axis=1))))

    return {
        "sn_avg_dist_to_center": _average_distance(radial_distances, sn_mask),
        "pt_avg_dist_to_center": _average_distance(radial_distances, pt_mask),
        "gyration_radius": gyration_radius,
    }


__all__ = ["calc_geometry_statistics"]
