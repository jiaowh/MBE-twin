"""The closed-form Ga-rich window of scripts/growth_window.py against a brute-force regime scan."""

import importlib.util
from pathlib import Path

import numpy as np
import pytest

from mbe_twin.growth import load_parameters, steady_state

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.parametrize("scenario, t0", [("Ref14_growth", 700.0), ("Heying_growth", 740.0), ("G01_adsorption", 700.0)])
def test_window_matches_brute_force(scenario, t0):
    gw = _load("growth_window")
    p = load_parameters()
    rho = gw.RHO / gw.WAFER_RADIUS
    g = 1.0 - 0.06 * rho ** 2          # edge-low Ga
    n = 1.0 - 0.02 * rho ** 2 + 0.01 * rho ** 4
    t = t0 + 273.15 + 4.0 * rho ** 2   # edge 4 K hotter
    out = gw.window(g, n, t, p, scenario)
    grid = np.arange(0.9, 3.0, 1e-4)
    ok = np.array([np.all(steady_state(r0 * gw.J_N0 * g, gw.J_N0 * n, t, p, scenario)["regime"] == "Ga-adlayer")
                   for r0 in grid])
    if out["window"] is None:
        assert not ok.any()
    else:
        assert ok.any()
        assert grid[ok].min() == pytest.approx(out["window"][0], abs=2e-4)
        assert grid[ok].max() == pytest.approx(out["window"][1], abs=2e-4)
