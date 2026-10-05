"""Integrated twin, first slice: verification cases V07, V09, V13, V14 and conservation through shutter events.

Uses a synthetic chamber (uniform maps, coarse heater) so the expected results are exact or
independently computable; the representative chamber is built by scripts/twin_chamber.py.
"""

import math

import numpy as np
import pytest

from mbe_twin import recipe as recipe_mod
from mbe_twin import sensors, surface, thermal_transient
from mbe_twin.chamber import N_ATOMS_PER_SCCM, Chamber, heater_definition
from mbe_twin.growth import load_parameters, steady_state
from mbe_twin.heater import HeaterGeometry, HeaterModel, HeaterProperties
from mbe_twin.twin import Twin

COARSE = dict(n_heater=30, n_wafer=25, n_over=3, n_outer=4)
RHO = np.linspace(0.0, 0.094, 11)
K_ATOMS = 0.064 * 1.14e19
PARAMS = load_parameters()


def definition(ga_shape=None, n_map=None, att=1.0, speed=4.0, volume=0.5, mfc_tau=2.0, zones=(0.0, 0.06, 0.115),
               fractions=(0.4, 0.6), eta=0.3):
    g, p = heater_definition(HeaterGeometry(zone_edges=zones, **COARSE), HeaterProperties())
    p_grid = [0.0, 1e-3, 1e-2, 0.15]
    return {
        "schema_version": "0.1", "label": "synthetic", "name": "test chamber",
        "rho_m": RHO.tolist(), "p_grid_Pa": p_grid,
        "ga": {"shape": (np.ones_like(RHO) if ga_shape is None else ga_shape).tolist(),
               "att": np.full((4, len(RHO)), att).tolist(),
               "reference": {"cell_K": 1227.6, "centre_flux_m2_s": 1.2163e19}},
        "n": {"map_per_atom_s": (np.full_like(RHO, 1.0e19 / (0.3 * N_ATOMS_PER_SCCM * 10.0)) if n_map is None
                                 else n_map).tolist(),
              "att": np.full((4, len(RHO)), att).tolist(), "eta": eta, "kn_per_sccm": 200.0, "kn_valid": 10.0},
        "vacuum": {"effective_speed_m3_s": speed, "gas_temperature_K": 300.0, "chamber_volume_m3": volume,
                   "mfc_time_constant_s": mfc_tau},
        "heater": {"geometry": g, "properties": p, "zone_fractions": list(fractions),
                   "areal_heat_capacity_J_m2K": {"heater": 3700.0, "ledge": 5700.0}, "element_limit_K": 1473.15},
        "growth": {"droplet_law": "Heying_growth", "n_rich_decomposition": "vacuum", "atoms_per_m2_s_per_nm_min": K_ATOMS},
        "sensors": {"pyrometer": {"spot_radius_m": 0.01, "bias_K": 0.0, "noise_K": 0.0, "valid_min_K": 873.0},
                    "ion_gauge": {"sensitivity": 1.0, "noise_rel": 0.0}, "regime_spot_radius_m": 0.01,
                    "thickness_map_radii_m": [0.0, 0.045, 0.09]},
        "operating_point": {"wafer_C": 720.0, "ga_cell_K": 1227.6, "n2_sccm": 10.0},
    }


def growth_recipe(growth_s=600.0, ga=True, n=True, pre_s=900.0):
    return {"schema_version": "0.1", "name": "test",
            "initial": {"wafer_C": 700.0, "ga_cell_K": 1227.6},
            "steps": [
                {"name": "stabilize", "duration_s": pre_s, "heater": {"mode": "pyrometer", "target_C": 720.0},
                 "ga_cell": {"target_K": "operating_point"}, "n2_sccm": "operating_point", "plasma": True,
                 "rotation_rpm": 10.0},
                {"name": "grow", "duration_s": growth_s, "shutters": {"ga": ga, "n": n}},
                {"name": "consume", "duration_s": 120.0, "shutters": {"ga": False, "n": True}},
                {"name": "close", "duration_s": 60.0, "shutters": {"ga": False, "n": False}, "plasma": False,
                 "n2_sccm": 0.0},
            ]}


# ---- heater transient ------------------------------------------------------------------------------

def test_heater_transient_reaches_the_steady_solution_and_closes_energy():
    m = HeaterModel(HeaterGeometry(zone_edges=(0.0, 0.06, 0.115), **COARSE), HeaterProperties())
    cap = thermal_transient.capacities(m, 3700.0, 5700.0)
    zp = np.array([800.0, 1500.0])
    t = np.full(len(cap), 300.0)
    for dt in [5.0] * 40 + [200.0] * 100:
        t_new = thermal_transient.step(m, t, dt, cap, zp)
        e = thermal_transient.energy_residual(m, t, t_new, dt, cap, zp)
        assert abs(e) < 1e-6 * zp.sum() * dt
        t = t_new
    steady = m.solve(heater_power=zp)
    assert np.max(np.abs(t[m.iw] - steady["t_wafer"])) < 1e-3


def test_heater_transient_is_first_order_in_time():
    m = HeaterModel(HeaterGeometry(**COARSE), HeaterProperties())
    cap = thermal_transient.capacities(m, 3700.0, 5700.0)
    zp = np.array([2000.0])

    def wafer_at(t_end, dt):
        t = np.full(len(cap), 900.0)
        for _ in range(round(t_end / dt)):
            t = thermal_transient.step(m, t, dt, cap, zp)
        return t[m.iw].mean()
    e1 = wafer_at(120.0, 4.0) - wafer_at(120.0, 0.5)
    e2 = wafer_at(120.0, 2.0) - wafer_at(120.0, 0.5)
    # implicit Euler: halving the step halves the error (ratio (4-0.5)/(2-0.5) = 2.33 against the fine reference)
    assert e1 / e2 == pytest.approx(3.5 / 1.5, rel=0.05)


# ---- surface ---------------------------------------------------------------------------------------

def test_v09_constant_flux_gives_the_exact_integrated_thickness():
    # N-rich, cold enough that decomposition is negligible: thickness = Ga flux x time
    s = surface.SurfaceState.bare(3)
    for _ in range(7):
        s, _ = surface.advance(s, 10.0, 12.0, 873.15, 60.0, PARAMS, "Heying_growth")
    dec = PARAMS.decomposition(873.15)
    assert s.thickness == pytest.approx(np.full(3, (10.0 - dec) * 7.0), rel=1e-12)


def test_surface_ledgers_close_through_droplets_consumption_and_etching():
    s = surface.SurfaceState.bare(4)
    t = np.array([993.0, 1003.0, 1013.0, 1063.0])
    for j_ga, j_n, minutes in [(30.0, 10.0, 5.0), (0.0, 12.0, 3.0), (0.0, 0.0, 2.0), (16.0, 15.0, 4.0), (0.0, 0.0, 600.0)]:
        s, info = surface.advance(s, j_ga, j_n, t, minutes * 60.0, PARAMS, "Heying_growth")
    res = surface.ledger_residuals(s)
    for k, v in res.items():
        assert np.max(np.abs(v)) < 1e-9, k
    assert np.all(s.thickness >= 0.0)
    assert s.ledger["etch_limited"][-1] > 0.0          # the hottest point etched through
    formed = s.ledger["ga_into_droplets"] > 0.0          # the cooler points formed droplets (onset rises with T)
    assert formed[0] and not formed[-1]
    assert np.all(s.ledger["ga_from_droplets"][formed] > 0.0)   # and the N-only step consumed them


def test_droplets_are_consumed_at_the_unused_n_rate():
    s = surface.SurfaceState(np.zeros(1), np.array([5.0]), {k: np.zeros(1) for k in surface.LEDGER_KEYS})
    s2, info = surface.advance(s, 0.0, 2.0, 873.15, 60.0, PARAMS, "Heying_growth")   # 1 min, 2 nm/min of N
    assert s2.droplets[0] == pytest.approx(3.0)
    assert info["regime"][0] == "droplet-consumption"


# ---- sensors ---------------------------------------------------------------------------------------

def test_v14_pyrometer_reads_the_area_weighted_spot_of_a_prescribed_field():
    rho = np.linspace(0.0, 0.1, 101)
    t = 1000.0 + 50.0 * (rho / 0.1) ** 2
    rng = np.random.default_rng(0)
    r, flag = sensors.pyrometer(rho, t, rng, spot_radius=0.02, bias_k=1.5)
    w = sensors.ring_weights(rho, 0.02)
    assert flag == "ok"
    assert r == pytest.approx(np.sum(w * t) / w.sum() + 1.5)
    # exact area mean of a + b r^2 over r < R is a + b R^2 / 2; the sample-ring rule converges to it
    assert np.sum(w * t) / w.sum() == pytest.approx(1000.0 + 50.0 * 0.04 / 2, abs=0.05)
    assert sensors.pyrometer(rho, t - 400.0, rng, spot_radius=0.02)[1] == "below_range"


# ---- recipe ----------------------------------------------------------------------------------------

def test_recipe_inherits_resolves_and_rejects():
    ini, steps, _ = recipe_mod.load(growth_recipe(), {"wafer_C": 720.0, "ga_cell_K": 1230.0, "n2_sccm": 10.0})
    assert steps[1].heater == {"mode": "pyrometer", "target_C": 720.0}
    assert steps[1].ga_cell["target_K"] == 1230.0 and steps[1].n2_sccm == 10.0
    assert steps[2].shutters == {"ga": False, "n": True} and steps[3].plasma is False
    bad = growth_recipe()
    bad["steps"][0]["n2_flow"] = 3.0
    with pytest.raises(ValueError, match="unknown keys"):
        recipe_mod.load(bad, {})
    with pytest.raises(ValueError, match="operating_point"):
        recipe_mod.load(growth_recipe(), {})


# ---- integrated runs -------------------------------------------------------------------------------

def test_v07_pressure_follows_the_well_mixed_pump_down():
    ch = Chamber(definition(volume=2.0, speed=0.5, mfc_tau=0.0))      # V/S = 4 s
    rec = {"schema_version": "0.1", "steps": [
        {"duration_s": 20.0, "n2_sccm": 5.0}, {"duration_s": 8.0, "n2_sccm": 0.0}]}
    tw = Twin(ch, rec, dt_max=0.5, sample_s=0.5).run()
    ts = tw.timeseries()
    p_eq = ch.pressure_eq(5.0)
    t = ts["t_s"]
    expect = np.where(t <= 20.0, p_eq * (1 - np.exp(-t / 4.0)),
                      p_eq * (1 - math.exp(-5.0)) * np.exp(-(t - 20.0) / 4.0))
    assert np.allclose(ts["pressure_Pa"], expect, rtol=1e-10, atol=1e-18)


def test_closed_shutters_grow_nothing_and_the_heater_controller_holds_the_reading():
    ch = Chamber(definition())
    tw = Twin(ch, growth_recipe(ga=False, n=False), dt_max=2.0).run()
    out, _ = tw.results()
    assert out["thickness_mean_nm"] == 0.0
    ts = tw.timeseries()
    grow = ts["step"] == 1
    assert np.max(np.abs(ts["pyrometer_K"][grow] - (720.0 + 273.15))) < 0.05
    assert abs(out["conservation"]["heater_energy_rel"]) < 1e-6


def test_growth_through_shutter_events_conserves_atoms_and_matches_the_steady_rate():
    ch = Chamber(definition())
    tw = Twin(ch, growth_recipe(growth_s=1200.0), dt_max=2.0).run()
    out, maps = tw.results()
    cons = out["conservation"]
    assert cons["ga_max_abs_rel"] < 1e-12 and cons["n_max_abs_rel"] < 1e-12 and cons["solid_max_abs_rel"] < 1e-12
    assert cons["droplets_max_abs_rel"] < 1e-12
    assert abs(cons["heater_energy_rel"]) < 1e-6
    # uniform maps: the layer is the steady net rate at the held wafer temperature over the 20 min exposure, plus
    # the droplets formed where the cooler edge passes the onset, which the N-only step converts into GaN, minus the
    # decomposition in the 3 min after the Ga shutter closes
    t_w = np.asarray(maps["t_wafer_K"])
    j_ga = ch.ga_flux(1227.6, ch.pressure_eq(10.0)) / K_ATOMS
    j_n = ch.n_flux(10.0, ch.pressure_eq(10.0)) / K_ATOMS
    st = steady_state(j_ga, j_n, t_w, PARAMS, "Heying_growth")
    led = tw.results()[0]["ledger_area_mean_nm"]
    grown = np.asarray(maps["thickness_nm"])
    s_end = surface.SurfaceState.from_dict(tw.state["surface"])
    expected = st["net_growth"] * 20.0 + s_end.ledger["ga_from_droplets"] - PARAMS.decomposition(t_w) * 3.0
    assert np.allclose(grown, expected, rtol=2e-3)
    assert s_end.ledger["ga_from_droplets"][-1] > 0.0 and s_end.ledger["ga_from_droplets"][0] == 0.0
    # 2 min of N cannot consume them all at the edge: what remains is what the ledger says
    assert out["droplets_mean_nm"] == pytest.approx(led["ga_into_droplets"] - led["ga_from_droplets"], rel=1e-12)
    assert out["exposure_s"] == {"ga": 1200.0, "n": 1320.0, "growth": 0.0}


def test_v13_restart_across_a_shutter_event_is_identical():
    ch = Chamber(definition())
    rec = growth_recipe(growth_s=300.0, pre_s=300.0)
    full = Twin(ch, rec, dt_max=5.0, seed=3).run()
    part = Twin(ch, rec, dt_max=5.0, seed=3).run(stop_at=(1, 0))      # stop exactly at the shutter opening
    ckpt = part.checkpoint()
    resumed = Twin(ch, rec, dt_max=5.0, seed=3)
    resumed.restore(ckpt)
    resumed.run()
    a, b = full.results()[1], resumed.results()[1]
    assert a["thickness_nm"] == b["thickness_nm"] and a["t_wafer_K"] == b["t_wafer_K"]
    for k in full.log:
        assert list(map(str, full.log[k])) == list(map(str, resumed.log[k])), k


def test_time_step_convergence_of_the_integrated_thickness():
    ch = Chamber(definition())
    h = {}
    for dt in (10.0, 5.0, 2.5):
        out, maps = Twin(ch, growth_recipe(growth_s=600.0, pre_s=600.0), dt_max=dt).run().results()
        h[dt] = out["thickness_mean_nm"]
    # first-order heater coupling: differences shrink by about 2 per halving, and are small
    d1, d2 = abs(h[10.0] - h[5.0]), abs(h[5.0] - h[2.5])
    assert d2 < d1 or d1 < 1e-9
    assert d2 / h[2.5] < 1e-3


def test_representative_chamber_reproduces_the_steady_operating_point():
    # The committed B-L chamber (scripts/twin_chamber.py): with a noiseless pyrometer the twin's growth map at the end
    # of a long growth step equals the steady chain of the studies at the operating point (arrival maps at the
    # balanced pressure, the steady heater map at the feedforward power, growth.steady_state), and grows 1 um/h.
    from pathlib import Path
    from mbe_twin.chamber import load_definition
    d = load_definition(Path(__file__).resolve().parents[1] / "cases/twin/chamber_B-L_720C.json")
    d["sensors"]["pyrometer"]["noise_K"] = 0.0
    d["sensors"]["ion_gauge"]["noise_rel"] = 0.0
    ch = Chamber(d)
    op = d["operating_point"]
    rec = {"schema_version": "0.1", "initial": {"wafer_C": 720.0, "ga_cell_K": "operating_point"},
           "steps": [{"duration_s": 600.0, "heater": {"mode": "pyrometer", "target_C": "operating_point"},
                      "ga_cell": {"target_K": "operating_point"}, "n2_sccm": "operating_point", "plasma": True,
                      "rotation_rpm": 10.0},
                     {"duration_s": 600.0, "shutters": {"ga": True, "n": True}}]}
    tw = Twin(ch, rec, dt_max=2.0).run()
    ts = tw.timeseries()
    assert ts["pyrometer_K"][-1] == pytest.approx(op["wafer_C"] + 273.15, abs=1e-3)
    p = op["expected"]["pressure_Pa"]
    assert ts["pressure_Pa"][-1] == pytest.approx(p, rel=1e-9)
    t_w = np.asarray(tw._last["t_wafer"])
    steady = ch.heater.solve(heater_power=ch.zone_power(ch.feedforward_power(op["wafer_C"] + 273.15)))
    assert np.max(np.abs(t_w - np.interp(ch.rho, steady["r_wafer"], steady["t_wafer"]))) < 0.05
    st = steady_state(ch.ga_flux(op["ga_cell_K"], p) / ch.k_atoms, ch.n_flux(op["n2_sccm"], p) / ch.k_atoms, t_w, PARAMS,
                      ch.droplet_law)
    assert np.allclose(tw._last["net_growth"], st["net_growth"], rtol=1e-9)
    w = ch.rho
    mean_rate = float(np.sum(sensors.ring_weights(w, w[-1]) * st["net_growth"]) / np.sum(sensors.ring_weights(w, w[-1])))
    assert mean_rate * 0.06 == pytest.approx(op["expected"]["rate_target_um_h"], rel=2e-3)
    assert set(tw._last["regime"]) == {"Ga-adlayer"}


@pytest.mark.parametrize("truth", ["tilt-flange-0.8deg-dir180", "fill120"])
def test_realizable_controllers_converge_to_the_steady_realizable_state(truth):
    # Rate monitor + BFM in the twin, on truth chambers that differ from the calibration. At the end of a long growth
    # step the commanded feed and the Ga arrival equal the steady realizable solution computed here independently:
    # the feed puts the true centre N arrival at the calibrated centre rate plus decomposition, and the Ga centre
    # arrival is the controller's window middle (exact BFM).
    from pathlib import Path
    from mbe_twin.chamber import load_definition
    from mbe_twin.control import ControllerModel
    d = load_definition(Path(__file__).resolve().parents[1] / f"cases/twin/chamber_B-L_720C_{truth}.json")
    d["sensors"]["pyrometer"]["noise_K"] = 0.0
    ch = Chamber(d)
    rec = {"schema_version": "0.1", "initial": {"wafer_C": 720.0, "ga_cell_K": "operating_point"},
           "steps": [{"duration_s": 300.0, "heater": {"mode": "pyrometer", "target_C": "operating_point"},
                      "ga_cell": {"target_K": "steered"}, "n2_sccm": "rate_monitor", "plasma": True, "rotation_rpm": 10.0},
                     {"duration_s": 120.0, "bfm": True, "shutters": {"ga": True, "n": False}},
                     {"duration_s": 4200.0, "shutters": {"ga": True, "n": True}}]}
    tw = Twin(ch, rec, dt_max=5.0).run()
    cm = ControllerModel(d, ch, PARAMS)
    t_w = np.asarray(tw._last["t_wafer"])
    reading = ch.spot_mean(t_w, d["sensors"]["pyrometer"]["spot_radius_m"])
    need = cm.centre_rate_target() + float(PARAMS.decomposition(t_w[0]))

    def centre_n(f):
        return float(ch.n_flux(f, ch.pressure_eq(f))[0]) / ch.k_atoms
    lo, hi = 1.0, 35.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if centre_n(mid) < need else (lo, mid)
    feed = 0.5 * (lo + hi)
    assert tw.state["feed_cmd"] == pytest.approx(feed, rel=2e-3)          # 7 rate windows: converged geometrically
    ts = tw.timeseries()
    assert ts["ga_centre_nm_min"][-1] == pytest.approx(cm.ga_target(reading, ch.pressure_eq(feed)), rel=2e-3)
    assert set(tw._last["regime"]) == {"Ga-adlayer"}
