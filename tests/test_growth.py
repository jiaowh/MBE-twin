"""GaN growth-regime model: atom balances, limits and the sources' own numbers."""

import numpy as np
import pytest

from mbe_twin.growth import active_n_from_ga_rich_rate, ga_balance_residual, grow, load_parameters, steady_state

P = load_parameters()
C = 273.15


@pytest.mark.parametrize("scenario", ["G01_adsorption", "Heying_growth", "Ref14_growth"])
def test_ga_balance_closes_in_every_regime(scenario):
    j_n = 10.0
    j_ga = np.array([2.0, 9.9, 10.0, 11.0, 14.0, 40.0])  # N-rich ... droplets
    for t in (700 + C, 760 + C, 800 + C):
        for mode in ("vacuum", "none"):
            st = steady_state(j_ga, j_n, t, P, scenario, mode)
            assert np.allclose(ga_balance_residual(st, j_ga), 0.0, atol=1e-12)
            assert np.all(st["desorbed_ga"] >= 0) and np.all(st["into_droplets"] >= 0)


def test_growth_limits():
    t = 750 + C
    d = P.decomposition(t)
    ga_rich = steady_state(15.0, 10.0, t, P, "Ref14_growth")
    assert ga_rich["regime"] == "Ga-adlayer" and ga_rich["net_growth"] == pytest.approx(10.0 - d)
    n_rich = steady_state(6.0, 10.0, t, P, "Ref14_growth", "none")
    assert n_rich["regime"] == "N-rich" and n_rich["net_growth"] == pytest.approx(6.0)
    assert n_rich["unused_n"] == pytest.approx(4.0)
    drop = steady_state(60.0, 10.0, t, P, "Ref14_growth")
    assert drop["regime"] == "droplets"
    assert drop["into_droplets"] == pytest.approx(50.0 - P.critical_excess("Ref14_growth", t))


def test_decomposition_matches_g02():
    # G02: nearly zero at 720 C, above about 3.5 nm/min at 805 C (Figs. 1-3)
    assert P.decomposition(720 + C) < 0.4
    assert 3.5 < P.decomposition(805 + C) < 6.0


def test_droplet_onset_cross_checks():
    # G01 Fig. 3 at 740 C: 2 -> 3 transition at 0.72 ML/s without N
    assert 0.5 < P.droplet_onset["G01_adsorption"](740 + C) < 1.2
    # R20 at 700 C: droplets beyond an excess of about 5 nm/min; only Ref14 reproduces it
    assert 4.0 < P.critical_excess("Ref14_growth", 700 + C) < 6.0
    assert P.critical_excess("Heying_growth", 700 + C) < 2.5


def test_active_n_calibration_adds_decomposition():
    t = 780 + C
    assert active_n_from_ga_rich_rate(10.0, t, P) == pytest.approx(10.0 + P.decomposition(t))


def test_recipe_with_shutter_segments():
    t = 740 + C
    segs = [{"duration_s": 600, "j_ga": 12.0, "j_n": 10.0, "t_k": t},
            {"duration_s": 30, "j_ga": 0.0, "j_n": 10.0, "t_k": t},    # Ga shutter closed
            {"duration_s": 600, "j_ga": 30.0, "j_n": 10.0, "t_k": t}]  # droplets
    out = grow(segs, P, "Ref14_growth", "vacuum")
    d = P.decomposition(t)
    assert out["thickness_nm"] == pytest.approx(10 * (10 - d) + 0.5 * (0 - d) + 10 * (10 - d))
    assert out["droplet_ga_nm"] > 0 and abs(out["ga_balance_residual"]) < 1e-9
    assert len(out["warnings"]) == 1 and "30 s" in out["warnings"][0]
