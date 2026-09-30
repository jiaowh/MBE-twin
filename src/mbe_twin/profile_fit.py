"""Uniformity of a rotation-averaged wafer profile estimated from annulus-averaged bins.

DSMC (and any particle method) delivers the flux as averages over annuli. Uniformity metrics
(range/mean) need the point profile, including its centre and edge values. `annulus_fit` fits
a polynomial in x = (r / R)^2 whose *annulus averages* match the bins (weighted least
squares), which removes the bias of fitting a point model to averages; the fitted polynomial is
then evaluated on a dense grid. Checked against dense reference profiles in
tests/test_profile_fit.py and scripts/check_uniformity_estimator.py.
"""

import numpy as np


def annulus_design(edges, radius, order):
    """Matrix A with A[i, j] = average of (r/R)^(2j) over annulus i (area-weighted)."""
    e = np.asarray(edges, float) / radius
    a, b = e[:-1], e[1:]
    cols = [(b ** (2 * j + 2) - a ** (2 * j + 2)) / ((j + 1) * (b ** 2 - a ** 2)) for j in range(order + 1)]
    return np.stack(cols, 1)


def annulus_fit(bins, edges, radius, order=3, stderr=None):
    """Polynomial coefficients c_j of f(r) = sum_j c_j (r/R)^(2j) fitted to annulus averages."""
    A = annulus_design(edges, radius, order)
    y = np.asarray(bins, float)
    w = np.ones_like(y) if stderr is None else 1.0 / np.maximum(np.asarray(stderr, float), 1e-12 * np.abs(y).max())
    return np.linalg.lstsq(A * w[:, None], y * w, rcond=None)[0]


def evaluate(coef, r, radius):
    x = (np.asarray(r, float) / radius) ** 2
    return sum(c * x ** j for j, c in enumerate(coef))


def uniformity(profile, r, radius):
    """Range/mean and std (%) and centre-to-edge of a point profile on radii r (0..radius)."""
    r = np.asarray(r, float)
    f = np.asarray(profile, float)
    ring = np.pi * np.diff(np.concatenate(([0.0], 0.5 * (r[1:] + r[:-1]), [radius])) ** 2)
    mean = np.sum(ring * f) / ring.sum()
    std = np.sqrt(np.sum(ring * (f - mean) ** 2) / ring.sum())
    return {"range_over_mean_pct": 100 * (f.max() - f.min()) / mean, "std_pct": 100 * std / mean,
            "centre_to_edge": f[-1] / f[0], "mean": mean}


def fitted_uniformity(bins, edges, radius, order=3, stderr=None, n=401):
    coef = annulus_fit(bins, edges, radius, order, stderr)
    r = np.linspace(0.0, radius, n)
    out = uniformity(evaluate(coef, r, radius), r, radius)
    out["fit"] = coef.tolist()
    out["order"] = order
    resid = np.asarray(bins, float) - annulus_design(edges, radius, order) @ coef
    out["max_abs_residual_pct"] = float(100 * np.max(np.abs(resid)) / out["mean"])
    return out


def binned_uniformity(bins, edges):
    """Range/mean (%) of the bins themselves (no extrapolation; biased low by bin averaging)."""
    b = np.asarray(bins, float)
    area = np.diff(np.asarray(edges, float) ** 2)
    mean = np.sum(area * b) / area.sum()
    return 100 * (b.max() - b.min()) / mean
