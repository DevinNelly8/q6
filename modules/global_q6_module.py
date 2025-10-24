"""Utilities for computing simple global Q6 descriptors."""

from __future__ import annotations

import numpy as np

from .config import ELEMENTS, Q6_Q4
from .q6_module import calc_q6_fast


def _average_q6_for_mask(positions: np.ndarray, elements: np.ndarray, mask: np.ndarray, cutoff: float) -> float:
    """Compute the average local Q6 value for the atoms selected by *mask*.

    The helper returns ``0.0`` when the mask is empty or all values are NaN so
    that downstream code can safely consume the value without additional checks.
    """

    indices = np.where(mask)[0]
    if indices.size == 0:
        return 0.0

    q6_values = []
    for idx in indices:
        value = calc_q6_fast(positions[idx], positions, elements, cutoff=cutoff)
        if not np.isnan(value):
            q6_values.append(value)

    if not q6_values:
        return 0.0

    return float(np.mean(q6_values))


def calc_cluster_analysis(positions: np.ndarray, elements: np.ndarray, cutoff: float | None = None):
    """Compute simple global Q6 statistics for the provided structure.

    Parameters
    ----------
    positions:
        ``(N, 3)`` array containing the atomic coordinates of the current frame.
    elements:
        Sequence of element symbols for the atoms in *positions*.
    cutoff:
        Radial cutoff passed to :func:`calc_q6_fast`.  When ``None`` the value
        from :mod:`modules.config` is used.

    Returns
    -------
    dict
        Nested dictionary following the structure expected by
        :mod:`v6_2_3_main_Version2`.  Each entry contains an average ``q6``
        value along with the atom count of the corresponding selection.
    """

    if cutoff is None:
        cutoff = Q6_Q4["q6_cutoff"]

    positions = np.asarray(positions, dtype=float)
    elements = np.asarray(elements)

    if positions.size == 0 or elements.size == 0:
        return {
            "cluster": {"count": 0, "q6_global": 0.0},
            "metal": {},
            "Pt": {"count": 0, "q6_global": 0.0},
            "Sn": {"count": 0, "q6_global": 0.0},
        }

    pt_mask = elements == "Pt"
    sn_mask = elements == "Sn"
    metal_mask = np.isin(elements, ELEMENTS.get("metal_elements", []))
    all_mask = np.ones(len(elements), dtype=bool)

    result = {
        "cluster": {
            "count": int(all_mask.sum()),
            "q6_global": _average_q6_for_mask(positions, elements, all_mask, cutoff),
        },
        "metal": {},
        "Pt": {
            "count": int(pt_mask.sum()),
            "q6_global": _average_q6_for_mask(positions, elements, pt_mask, cutoff),
        },
        "Sn": {
            "count": int(sn_mask.sum()),
            "q6_global": _average_q6_for_mask(positions, elements, sn_mask, cutoff),
        },
    }

    if metal_mask.any():
        result["metal"] = {
            "count": int(metal_mask.sum()),
            "q6_global": _average_q6_for_mask(positions, elements, metal_mask, cutoff),
        }

    return result


__all__ = ["calc_cluster_analysis"]
