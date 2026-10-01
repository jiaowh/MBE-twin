"""Heater limits in the zone optimizer and the equal-rate growth evaluation of the layout comparison."""

import importlib.util
import os
from pathlib import Path

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402
import pytest  # noqa: E402

from mbe_twin.growth import load_parameters  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_heater_limit_is_respected_and_costs_uniformity():
    hz = _load("heater_zones")
    model = hz.make(hz.LAYOUTS["3 zones"], {}, {})
    free, _ = hz.optimize(model, 1013.15)
    assert free["violation"] == 0.0
    assert free["t_heater"].max() > 1400.0  # the unconstrained optimum runs the element above 1373 K
    held, frac = hz.optimize(model, 1013.15, limits={"t_heater_max": 1373.15})
    assert held["violation"] < 1e-3
    assert held["t_heater"].max() <= 1373.15 * 1.001
    assert held["wafer_mean"] == pytest.approx(1013.15, abs=1e-2)
    assert held["wafer_range"] >= free["wafer_range"] - 1e-6
    assert hz.violation(model, free, {"t_heater_max": 1373.15}) > 0.0
    assert hz.optimize(model, 1013.15, limits={"t_heater_max": None})[0]["wafer_range"] == free["wafer_range"]


def test_equal_rate_scaling_and_window_margin():
    lc = _load("layout_comparison")
    params = load_parameters()
    rho = np.linspace(0.0, 0.094, 21)
    n_maps = np.stack([1.0 - 0.05 * (rho / 0.094) ** 2, 1.0 + 0.02 * (rho / 0.094)])[:, None, :] * 3e-3  # (N=2, L=1)
    ga = np.stack([np.ones_like(rho), 1.0 - 0.03 * (rho / 0.094) ** 2])[:, None, :]                       # (G=2, L=1)
    t_maps = np.full((1, len(rho)), 740.0 + 273.15)
    res = lc.evaluate(n_maps, ga, t_maps, params, "Ref14_growth", rho, 1000.0 / 60.0, 7.296e17, (0, 0, 0, 0))
    in_window = res["margin"] >= 0.0
    assert in_window.all()
    # Ga-rich everywhere: the wafer-mean net rate equals the target in every state
    assert np.allclose(res["mean_net"], 1000.0 / 60.0, rtol=1e-12)
    # a flat N map with uniform temperature gives zero thickness spread
    flat = lc.evaluate(np.full((1, 1, len(rho)), 3e-3), ga[:1], t_maps, params, "Ref14_growth", rho, 1000.0 / 60.0,
                       7.296e17, (0, 0, 0, 0))
    assert flat["thickness"][0, 0, 0, 0] == pytest.approx(0.0, abs=1e-10)
    # output scales inversely with the delivered flux per unit output
    assert res["q"][0, 0, 0, 0] / flat["q"][0, 0, 0, 0] == pytest.approx(
        3e-3 / lc.area_mean(n_maps[0, 0], rho), rel=1e-12)
