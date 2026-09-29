"""Area-weighted map statistics (mbe_twin.md section 14.5).

Uniformity is a property of one map, not a measure of model accuracy. Each metric is
reported by name; half-range and standard deviation are never mixed.
"""

import numpy as np


def radial_ring_weights(rho, radius):
    """Area weights for an axisymmetric profile sampled at increasing radii `rho`.

    Each sample owns the annulus between midpoints to its neighbours, clipped to [0, radius].
    """
    rho = np.asarray(rho, float)
    if np.any(np.diff(rho) <= 0.0):
        raise ValueError("rho must be strictly increasing")
    edges = np.concatenate(([0.0], 0.5 * (rho[1:] + rho[:-1]), [radius]))
    edges = np.clip(edges, 0.0, radius)
    return np.pi * (edges[1:] ** 2 - edges[:-1] ** 2)


def weighted_stats(values, weights):
    """Mean, standard deviation, min, max and named uniformity metrics (percent)."""
    values = np.asarray(values, float).ravel()
    weights = np.asarray(weights, float).ravel()
    keep = weights > 0.0
    v, w = values[keep], weights[keep]
    mean = np.sum(w * v) / np.sum(w)
    std = np.sqrt(np.sum(w * (v - mean) ** 2) / np.sum(w))
    vmin, vmax = v.min(), v.max()
    return {
        "mean": mean,
        "std": std,
        "min": vmin,
        "max": vmax,
        "std_pct": 100.0 * std / mean,
        "half_range_pct": 100.0 * (vmax - vmin) / (2.0 * mean),
    }


def radial_uniformity(profile, rho, radius, edge_exclusion=0.0):
    """Area-weighted statistics of an axisymmetric profile inside radius - edge_exclusion."""
    rho = np.asarray(rho, float)
    usable = radius - edge_exclusion
    if usable <= 0.0:
        raise ValueError("edge exclusion removes the whole wafer")
    inside = rho <= usable
    stats = weighted_stats(np.asarray(profile, float)[inside],
                           radial_ring_weights(rho[inside], usable))
    stats["edge_exclusion"] = edge_exclusion
    return stats
