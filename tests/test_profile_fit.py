"""Uniformity estimator for annulus-averaged profiles (mbe_twin.profile_fit)."""

import numpy as np
import pytest

from mbe_twin import profile_fit as pf

R = 0.1
EDGES = np.linspace(0.0, R, 21)


def annulus_averages(f, n=4001):
    out = []
    for a, b in zip(EDGES[:-1], EDGES[1:]):
        r = np.linspace(a, b, n)
        out.append(np.trapezoid(f(r) * r, r) / np.trapezoid(r, r))
    return np.array(out)


def test_design_matrix_integrates_powers_exactly():
    c = np.array([1.0, -0.3, 0.2, 0.05])
    poly = lambda r: pf.evaluate(c, r, R)
    assert pf.annulus_design(EDGES, R, 3) @ c == pytest.approx(annulus_averages(poly), rel=1e-9)


def test_polynomial_profile_is_recovered_exactly():
    c = np.array([1.0, 0.08, -0.25, 0.1, -0.02])
    bins = pf.annulus_design(EDGES, R, 4) @ c
    assert pf.annulus_fit(bins, EDGES, R, 4) == pytest.approx(c, abs=1e-9)
    r = np.linspace(0.0, R, 401)
    exact = pf.uniformity(pf.evaluate(c, r, R), r, R)["range_over_mean_pct"]
    assert pf.fitted_uniformity(bins, EDGES, R, 4)["range_over_mean_pct"] == pytest.approx(exact, abs=1e-9)


def test_dense_free_molecular_profile_120mm_46deg():
    # Stored reference (scripts/check_uniformity_estimator.py): non-monotonic, maximum near
    # 36 mm, range/mean 10.3 %. The order-4 annulus fit recovers it within 0.2 points; the
    # former point quartic (order 2) overstated it by 1.1 points and raw bins understate it.
    import json
    from pathlib import Path

    d = json.loads((Path(__file__).parent / "data/fm_profile_120mm_46deg.json").read_text())
    r, f = np.array(d["r_m"]), np.array(d["flux"])
    exact = pf.uniformity(f, r, R)["range_over_mean_pct"]
    bins = []
    for a, b in zip(EDGES[:-1], EDGES[1:]):
        m = (r >= a - 1e-12) & (r <= b + 1e-12)
        bins.append(np.trapezoid(f[m] * r[m], r[m]) / np.trapezoid(r[m], r[m]))
    bins = np.array(bins)
    assert exact == pytest.approx(10.3, abs=0.1)
    assert pf.fitted_uniformity(bins, EDGES, R, 4)["range_over_mean_pct"] == pytest.approx(exact, abs=0.2)
    assert pf.fitted_uniformity(bins, EDGES, R, 2)["range_over_mean_pct"] > exact + 0.8
    assert pf.binned_uniformity(bins, EDGES) < exact - 0.3
