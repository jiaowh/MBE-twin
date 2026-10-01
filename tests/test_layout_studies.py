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


def _grid_inputs(lc, n_maps, rho, pressures_att=None):
    """Attenuation tables of ones (vacuum) unless given; one Ga shape, flat."""
    n_p = len(lc.P_GRID)
    att_n = np.ones((n_p, len(rho))) if pressures_att is None else pressures_att
    g_vac = np.ones((1, n_maps.shape[1], len(rho)))
    att_g = np.ones((1, n_p, len(rho)))
    return att_n, g_vac, att_g


def _run(lc, n_maps, rho, *, eta=1.0, speed=2.0, feed_cap=1e3, kn_per_sccm=1e6, att_n=None, target=1000.0 / 60.0):
    params = load_parameters()
    att_n, g_vac, att_g = _grid_inputs(lc, n_maps, rho, att_n)
    t_maps = np.full((1, len(rho)), 1013.15)
    return lc.evaluate(n_maps, att_n, g_vac, att_g, t_maps, params, "Ref14_growth", rho, target, 7.296e17, (0, 0, 0, 0),
                       eta, speed, feed_cap, 300.0, 0.0, kn_per_sccm)


def test_equal_rate_scaling_and_window_margin():
    lc = _load("layout_comparison")
    rho = np.linspace(0.0, 0.094, 21)
    n_maps = np.stack([1.0 - 0.05 * (rho / 0.094) ** 2, 1.0 + 0.02 * (rho / 0.094)])[:, None, :] * 10.0   # (N=2, L=1)
    res = _run(lc, n_maps, rho)
    assert (res["margin"] >= 0.0).all() and res["valid"].all()
    # Ga-rich everywhere: the wafer-mean net rate equals the target in every state
    assert np.allclose(res["mean_net"], 1000.0 / 60.0, rtol=1e-9)
    flat = _run(lc, np.full((1, 1, len(rho)), 10.0), rho)
    assert flat["thickness"][0, 0, 0, 0] == pytest.approx(0.0, abs=1e-10)
    # without attenuation the output scales inversely with the delivered flux per unit output
    assert res["q"][0, 0, 0, 0] / flat["q"][0, 0, 0, 0] == pytest.approx(10.0 / lc.area_mean(n_maps[0, 0], rho), rel=1e-9)


def test_ga_centre_flux_is_held_absolute_while_n_is_reset():
    """Changing only the N map shape must not move the Ga centre flux (audit 2026-10-01, finding 2)."""
    lc = _load("layout_comparison")
    rho = np.linspace(0.0, 0.094, 39)
    n_maps = np.stack([np.ones_like(rho), 1.0 + 0.2 * (rho / 0.094) ** 2])[:, None, :] * 10.0   # same centre, other shape
    captured = {}
    original = lc.steady_state

    def capture(j_ga, j_n, *args):
        captured["ga"], captured["n"] = np.array(j_ga[..., 0]), np.array(j_n[..., 0])
        return original(j_ga, j_n, *args)
    lc.steady_state = capture
    try:
        res = _run(lc, n_maps, rho)
    finally:
        lc.steady_state = original
    assert np.allclose(captured["ga"], res["ga_centre"], rtol=1e-12)
    assert captured["n"].ravel()[1] < captured["n"].ravel()[0]       # N was re-set for the rate
    assert res["margin"][1, 0, 0, 0] != pytest.approx(res["margin"][0, 0, 0, 0], rel=1e-6)


def test_each_state_has_its_own_feed_and_pressure():
    """The audit follow-up: a state's output fixes its feed (at fixed eta) and so its own pressure."""
    lc = _load("layout_comparison")
    rho = np.linspace(0.0, 0.094, 21)
    grid = np.asarray(lc.P_GRID)
    att = np.exp(-np.outer(grid, np.ones_like(rho)) / 2e-2)            # uniform attenuation, e-fold at 0.02 Pa
    n_maps = np.stack([np.full_like(rho, 10.0), np.full_like(rho, 8.0)])[:, None, :]   # state 1 delivers less
    res = _run(lc, n_maps, rho, att_n=att)
    f, p = res["feed"][:, 0, 0, 0], res["pressure"][:, 0, 0, 0]
    assert f[1] > f[0]
    to_p = lc.SCCM_PA_M3_S * (300.0 / lc.T_STD) / 2.0
    assert np.allclose(p, f * to_p, rtol=1e-9)
    # each state reaches the target at its own attenuation
    assert np.allclose(res["mean_net"], 1000.0 / 60.0, rtol=1e-6)
    per_feed = lc.N_ATOMS_PER_SCCM / 7.296e17
    dec = lc.area_mean(load_parameters().decomposition(np.full(len(rho), 1013.15)), rho)
    for i, m in enumerate((10.0, 8.0)):
        assert f[i] * per_feed * m * np.exp(-p[i] / 2e-2) - dec == pytest.approx(1000.0 / 60.0, rel=1e-6)


def test_ga_arrival_follows_each_state_attenuation():
    lc = _load("layout_comparison")
    rho = np.linspace(0.0, 0.094, 21)
    grid = np.asarray(lc.P_GRID)
    params = load_parameters()
    n_maps = np.stack([np.full_like(rho, 10.0), np.full_like(rho, 8.0)])[:, None, :]
    att_n = np.exp(-np.outer(grid, np.ones_like(rho)) / 2e-2)
    att_g = np.exp(-np.outer(grid, np.ones_like(rho)) / 1e-2)[None]   # Ga attenuates faster
    captured = {}
    original = lc.steady_state

    def capture(j_ga, j_n, *args):
        captured["ga"] = np.array(j_ga[..., 0])
        return original(j_ga, j_n, *args)
    lc.steady_state = capture
    try:
        res = lc.evaluate(n_maps, att_n, np.ones((1, 1, len(rho))), att_g, np.full((1, len(rho)), 1013.15), params,
                          "Ref14_growth", rho, 1000.0 / 60.0, 7.296e17, (0, 0, 0, 0), 1.0, 2.0, 1e3, 300.0, 0.0, 1e6)
    finally:
        lc.steady_state = original
    ga = captured["ga"].ravel()
    p = res["pressure"][:, 0, 0, 0]
    assert ga[1] / ga[0] == pytest.approx(np.exp(-(p[1] - p[0]) / 1e-2), rel=1e-9)


def test_supply_limited_and_invalid_states():
    lc = _load("layout_comparison")
    rho = np.linspace(0.0, 0.094, 21)
    n_maps = np.stack([np.full_like(rho, 10.0), np.full_like(rho, 6.0)])[:, None, :]
    free = _run(lc, n_maps, rho)
    cap = 1.05 * free["feed"][0, 0, 0, 0]
    held = _run(lc, n_maps, rho, feed_cap=cap)
    assert not held["supply_limited"][0].any() and held["supply_limited"][1].all()
    assert held["mean_net"][0, 0, 0, 0] == pytest.approx(1000.0 / 60.0, rel=1e-9)
    assert held["mean_net"][1, 0, 0, 0] < 1000.0 / 60.0
    assert held["feed"][1, 0, 0, 0] == pytest.approx(cap, rel=1e-12)
    assert held["valid"][0].all() and not held["valid"][1].any()
    # plate outside the free-molecular range: Kn = kn_per_sccm / feed below 10
    f0 = free["feed"][0, 0, 0, 0]
    bad = _run(lc, n_maps, rho, kn_per_sccm=5.0 * f0)
    assert not bad["valid"].any() and not bad["supply_limited"].any()


def test_operating_point_feed_budget():
    """1 sccm N2 holds at most 8.956e17 N atoms/s; beyond the feed limit the rate is the best reachable."""
    lc = _load("layout_comparison")
    assert lc.N_ATOMS_PER_SCCM == pytest.approx(8.956e17, rel=1e-3)
    k = 7.296e17
    flat = lambda p: 10.0   # wafer-mean flux per unit output, no attenuation (needs 1.36 sccm at eta 1)
    op = lc.operating_point(flat, 0.0, 1000.0 / 60.0, 1.0, 2.0, 100.0, 300.0, k)
    assert op["target_reached"]
    assert op["feed_sccm"] == pytest.approx(1000.0 / 60.0 / 10.0 * k / lc.N_ATOMS_PER_SCCM, rel=1e-6)
    lim = lc.operating_point(flat, 0.0, 1000.0 / 60.0, 1.0, 2.0, 1.0, 300.0, k)
    assert lim["feed_limited"] and not lim["target_reached"]
    assert lim["rate_nm_min"] == pytest.approx(lc.N_ATOMS_PER_SCCM * 1.0 / k * 10.0, rel=1e-9)
    # strong attenuation: the rate peaks below the feed limit and the target is unreachable
    att = lambda p: 10.0 * np.exp(-p / 2e-3)
    peak = lc.operating_point(att, 0.0, 1000.0 / 60.0, 1.0, 0.5, 10.0, 300.0, k)
    assert peak["feed_limited"] and peak["rate_peaks_below_feed_limit"]
    assert peak["pressure_Pa"] == pytest.approx(2e-3, rel=0.05)   # d(Q e^{-p/p0})/dQ = 0 at p = p0


def test_heater_states_respect_the_element_limit_in_every_state():
    """Perturbed heater states may not run the element above the limit (audit finding 3)."""
    lc = _load("layout_comparison")
    rho = np.linspace(0.0, 0.094, 39)
    limit = 1373.15   # binds for the 3-zone optimum (test_heater_limit_is_respected...)
    maps, rep = lc.heater_states("3 zones", 0.097, 1013.15, limit, rho)
    assert max(rep["state_t_heater_max_K"]) <= limit + 0.01
    assert any(rep["state_capped"])
    for cap, need, mean, short in zip(rep["state_capped"], rep["state_t_heater_needed_K"], rep["state_wafer_mean_K"],
                                      rep["state_mean_shortfall_K"]):
        if cap:
            assert need > limit and short > 0.0 and mean < 1013.15
        else:
            assert mean == pytest.approx(1013.15, abs=1e-2)
    # a higher wafer emissivity loses more from the growth face, so it needs the hotter element
    i63, i77 = lc.HEATER_STATES.index("eps 0.63"), lc.HEATER_STATES.index("eps 0.77")
    assert rep["state_t_heater_needed_K"][i77] > rep["state_t_heater_needed_K"][0] > rep["state_t_heater_needed_K"][i63]


def test_area_mean_is_an_area_quadrature():
    lc = _load("layout_comparison")
    errs = []
    for n in (39, 77, 153):
        rho = np.linspace(0.0, 0.094, n)
        errs.append(abs(lc.area_mean((rho / 0.094) ** 2, rho) - 0.5))
    assert errs[0] < 1e-3 and errs[2] < errs[1] < errs[0]
    rho = np.linspace(0.0, 0.094, 39)
    assert lc.area_std(np.ones_like(rho), rho) == pytest.approx(0.0, abs=1e-15)


def test_attenuation_interpolation_and_range():
    lc = _load("layout_comparison")
    grid = np.array(lc.P_GRID)
    table = np.exp(-np.outer(grid, [1.0, 2.0]) / 1e-2)    # exactly exponential in p
    for p in (0.0, 3e-3, 2.2e-2, grid[-1]):
        assert np.allclose(lc.att_at(table, p), np.exp(-p * np.array([1.0, 2.0]) / 1e-2), rtol=1e-12)
    with pytest.raises(ValueError):
        lc.att_at(table, 1.5 * grid[-1])


def test_cache_rejects_a_file_with_another_key(tmp_path):
    lc = _load("layout_comparison")
    build = lambda: {"x": np.arange(3.0)}
    arr, info = lc.load_or_build(tmp_path, tmp_path, "T", {"a": 1}, [lc.att_at], build)
    assert not info["reused"]
    again, info2 = lc.load_or_build(tmp_path, tmp_path, "T", {"a": 1}, [lc.att_at], build)
    assert info2["reused"] and np.array_equal(again["x"], arr["x"])
    other, info3 = lc.load_or_build(tmp_path, tmp_path, "T", {"a": 2}, [lc.att_at], build)   # new inputs, new file
    assert info3["file"] != info["file"]
    f = tmp_path / info["file"]
    np.savez(f, cache_key="tampered", inputs="{}", x=np.zeros(3))
    with pytest.raises(SystemExit):
        lc.load_or_build(tmp_path, tmp_path, "T", {"a": 1}, [lc.att_at], build)


def test_state_past_the_rate_peak_runs_at_its_best_feed():
    """With strong attenuation the rate peaks below the feed cap; a state that cannot reach the target runs at the
    peak feed (p = p0 for an e-folding pressure p0), not at the cap."""
    lc = _load("layout_comparison")
    rho = np.linspace(0.0, 0.094, 21)
    grid = np.asarray(lc.P_GRID)
    p0 = 5e-3
    att = np.exp(-np.outer(grid, np.ones_like(rho)) / p0)
    n_maps = np.full((1, 1, len(rho)), 0.01)        # far too little delivery for 1 um/h at any feed
    res = _run(lc, n_maps, rho, att_n=att, feed_cap=35.0, speed=0.5)
    assert res["supply_limited"].all() and not res["valid"].any()
    assert res["pressure"][0, 0, 0, 0] == pytest.approx(p0, rel=0.02)
    assert res["feed"][0, 0, 0, 0] < 35.0
