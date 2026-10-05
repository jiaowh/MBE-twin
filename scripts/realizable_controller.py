"""Operating point with a realizable controller: frozen calibration, explicit observations with errors.

Audit 2026-10-05 (finding 1): the temperature-corrected protocol of operating_optimum /
operating_cold_limit computes the Ga window of every uncertain state from that state's own N map,
Ga shape and pressure, which the centre pyrometer does not observe. This study replaces it by
controllers that use only a calibration frozen on the nominal state plus named observations, and
evaluates growth with the true maps of every state.

Calibration (commissioning, on the nominal state: nominal pose, 70 mm / 8 A Ga record, nominal
heater, 2 mm lip; at the operating temperature): the N feed for the target wafer-mean rate; the Ga
cell temperature that puts the centre Ga/N in the middle of the window; the nominal N and Ga
arrival shapes; the centre-to-mean ratio of the net rate. The droplet onset is measured at the
centre on the machine's own scale, so each droplet law is a truth scenario with its own calibration.

Truth states (the comparison's grid): N pointing within +/-0.8 deg (25 maps), Ga fills 40 / 70 /
120 mm x collision diameters 5.68 / 8 A (6 records, each with its own absolute flux versus cell
temperature: a frozen cell temperature delivers the depleted flux of a deeper charge), 27
combined heater errors x centre pyrometer bias -2 / 0 / +2 K (heater_robustness.combined_states,
1473 K element limit), three droplet laws, plus observation errors.

Controllers (what each observes; all see the pyrometer and the ion gauge):
- known maps (bound): operating_optimum.evaluate_point, the earlier protocol (each state's maps known).
- frozen: feed and Ga cell temperature as calibrated; nothing re-set.
- rate monitor: an in-situ growth-rate monitor at the centre (laser reflectometry) with relative
  error e_rate in {-1, 0, +1} %. The feed is re-set until the measured centre rate equals the
  calibrated centre rate; the Ga target is the window middle computed from the calibrated shapes
  at the reading, scaled to the centre N flux the controller infers (measured rate + modelled
  decomposition at the reading); the cell temperature for it comes from the calibrated Ga model
  (nominal record, nominal attenuation table at the gauge pressure).
- rate monitor + BFM: as above, but the Ga cell is set until a beam-flux monitor at the wafer
  centre reads the target, with relative error e_bfm in {-2, 0, +2} % (BEP-to-flux conversion
  calibrated on the nominal state). The Ga shape across the wafer is still not observed.
- rate monitor + BFM + fill: as above, with the Ga window computed from the calibrated Ga shape of the
  charge's current fill (known from charge bookkeeping; shapes per fill from commissioning Ga-limited
  maps at several fills, here the 8 A records), so the fill's shape change is known but the collision
  diameter is not.
- rate monitor + BFM + commissioned maps: the N pointing and the Ga shapes are fixed properties of the
  installed machine, which commissioning measures (N-limited and Ga-limited thickness maps); here the
  window uses the state's own N and Ga shapes at the calibration pressure, taken as exactly measured
  (an optimistic limit of map calibration). The N centre flux is still the controller's estimate, the
  heater state and pyrometer bias are not known, and the rate-monitor and BFM errors apply. It differs
  from the bound only in what changes from run to run.
The error magnitudes are priors (instrument specifications not selected).

A state is valid if the plate holes stay free-molecular (Kn >= 10), the feed is within the limit
and the wafer-mean net rate is within RATE_BAND of the target (the realizable controllers hold the
centre, not the mean; the bound keeps its exact-rate definition). A point is admissible if at least
ADMIT of all states are both valid and in the window (joint fraction) and the nominal heater state
reaches the temperature under the element limit.

Usage: python scripts/realizable_controller.py [--scattered gas+plume] [--t-min 690] [--t-max 790]
                                               [--rate-error 0.01] [--bfm-error 0.02] [--out DIR]
"""

import argparse
import importlib.util
import itertools
import json
import os
from pathlib import Path

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402

from mbe_twin import profile_fit  # noqa: E402
from mbe_twin.growth import load_parameters, steady_state  # noqa: E402
from mbe_twin.manifest import build_manifest, write_manifest  # noqa: E402
from mbe_twin.vapour import vapour_pressure  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


oo = _load("operating_optimum")
hr = _load("heater_robustness")
lc = oo.lc
SCENARIOS = [("B-p", {"eta": 1.0, "S_eff_m3_s": 2.0, "feed_limit_sccm": 10.0}),
             ("B-L", {"eta": 0.3, "S_eff_m3_s": 4.0, "feed_limit_sccm": 35.0})]
RATE_UM_H = 1.0
LIMIT_NAME = "1473 K element"
BIASES_K = (-2.0, 0.0, 2.0)
E_RATE = (-0.01, 0.0, 0.01)
E_BFM = (-0.02, 0.0, 0.02)
RATE_BAND = 0.03
ADMIT = 0.95
CONTROLLERS = ("known maps (bound)", "frozen", "rate monitor", "rate monitor + BFM", "rate monitor + BFM + fill",
               "rate monitor + BFM + commissioned maps")


def heater_states(t0_k, rho, design_limit):
    """heater_robustness.combined_states for the 1473 K limit, with the zone fractions optimized under a lower
    design limit (scripts/heater_margin.py) when design_limit < 1473.15 K; power still capped at 1473.15 K."""
    if design_limit >= hr.LIMITS[LIMIT_NAME]:
        return [s for s in hr.combined_states(t0_k, rho) if s["limit"] == LIMIT_NAME and s["controller"].startswith("pyrometer")]
    hz, lim = hr.hz, hr.LIMITS[LIMIT_NAME]
    edges, geo = hz.LAYOUTS["12 zones"], {"ledge_inner": hr.OPENING}
    r, frac = hz.optimize(hz.make(edges, geo, {}), t0_k, limits={"t_heater_max": design_limit})
    p0 = r["zone_power"].sum()
    states = []
    for eps, h, z in itertools.product(hr.EPS, hr.CONTACT, hr.ZONE):
        m = hz.make(edges, geo, {"eps_wafer": eps, "h_contact": h})
        cands = [frac] if z == 0.0 else [np.where(np.arange(m.n_zones) == k, frac * (1 + z), frac) / (frac.sum() + frac[k] * z)
                                         for k in range(m.n_zones)]
        f = max(((hz.at_mean(m, c, t0_k, p0=p0), c) for c in cands), key=lambda x: x[0]["wafer_range"])[1]
        for bias in hr.BIASES_K:
            rr, need, capped = hr._held(m, f, t0_k, lambda x, b=bias: hz.centre_reading(x, b), lim, p0)
            states.append({"limit": LIMIT_NAME, "eps": eps, "contact": h, "zone_error": z,
                           "controller": f"pyrometer {bias:+g} K", "capped": bool(capped),
                           "reading_K": hz.centre_reading(rr, bias), "t_map": np.interp(rho, rr["r_wafer"], rr["t_wafer"])})
    return states


def hk(t):
    return vapour_pressure("Ga", t) / np.sqrt(t)


def ga_reference(port, fill, dlab):
    """(cell K, absolute vacuum centre flux m^-2 s^-1) of a Ga record (annulus fit at r = 0)."""
    js = json.loads((lc.GA_RECORDS / lc.ga_record(port, fill, dlab)).read_text(encoding="utf-8"))
    o = js["outputs"]
    coef = profile_fit.annulus_fit(np.asarray(o["dsmc_flux"]), lc.GA_EDGES, 0.100, 4, np.asarray(o["dsmc_flux_stderr"]))
    return float(js["inputs"]["T_K"]), float(profile_fit.evaluate(coef, np.array([0.0]), 0.100)[0])


def cell_for(flux, ref):
    """Cell temperature that gives a vacuum centre flux under the Hertz-Knudsen scaling of a reference."""
    t_ref, f_ref = ref
    flux = np.asarray(flux, float)
    lo, hi = np.full(flux.shape, 600.0), np.full(flux.shape, 1600.0)
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        below = f_ref * hk(mid) / hk(t_ref) < flux
        lo, hi = np.where(below, mid, lo), np.where(below, hi, mid)
    return 0.5 * (lo + hi)


def window_mid(n_shape, g_shape, n_centre, fcrit):
    """Middle of the Ga/N centre-ratio window for N = n_centre x n_shape and a Ga shape (both centre 1)."""
    lo = np.max(n_shape / g_shape, axis=-1)
    hi = np.min((n_shape * n_centre[..., None] + fcrit[..., None]) / (n_centre[..., None] * g_shape), axis=-1)
    return np.where(hi > lo, 0.5 * (lo + hi), lo * 1.02)


def feed_for_centre(y, n_centre_vac, att_n, per_feed, to_p, cap, n_grid=400):
    """Lowest feed whose centre N arrival (nm/min) reaches y (array, any shape broadcast against n_centre_vac);
    supply-limited entries get the rate-maximizing feed. Returns feed, limited."""
    feeds = np.linspace(cap / n_grid, cap, n_grid)
    att_c = lc.att_at_many(att_n, feeds * to_p)[:, 0]                      # (F,)
    g = per_feed * feeds[:, None] * att_c[:, None] * np.ravel(n_centre_vac)[None, :]   # (F, Nn)
    yb, nb = np.broadcast_arrays(y, n_centre_vac)
    shape = yb.shape
    yf, idx_n = yb.ravel(), np.broadcast_to(np.arange(np.size(n_centre_vac)).reshape(np.shape(n_centre_vac)), shape).ravel()
    gg = g[:, idx_n]                                                        # (F, M)
    ok = gg >= yf[None, :]
    limited = ~ok.any(0)
    k = np.where(limited, np.argmax(gg, 0), np.argmax(ok, 0))
    hi = feeds[k]
    lo = np.where((k > 0) & ~limited, feeds[np.maximum(k - 1, 0)], hi)
    nc = np.ravel(n_centre_vac)[idx_n]
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        up = per_feed * mid * lc.att_at_many(att_n, mid * to_p)[:, 0] * nc >= yf
        hi = np.where(~limited & up, mid, hi)
        lo = np.where(~limited & ~up, mid, lo)
    return hi.reshape(shape), limited.reshape(shape)


def main():
    global E_RATE, E_BFM, RATE_UM_H
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--scattered", default="gas+plume", choices=lc.SCATTER_VARIANTS)
    ap.add_argument("--t-min", type=int, default=690)
    ap.add_argument("--t-max", type=int, default=790)
    ap.add_argument("--out", default=None)
    ap.add_argument("--rate-error", type=float, default=0.01, help="rate-monitor error e: states at -e, 0, +e")
    ap.add_argument("--bfm-error", type=float, default=0.02, help="BFM error e: states at -e, 0, +e")
    ap.add_argument("--aim-maps", nargs="*", default=None,
                    help="npz files of scripts/nitrogen_aim_operating.py (one per layout): nominal N maps at other aims")
    ap.add_argument("--aim-mm", type=float, nargs="*", default=None, help="aim offset (mm) per --aim-maps file; the "
                    "pointing states keep their map differences from the current aim's ensemble")
    ap.add_argument("--heater-control", default="single", choices=("single", "multispot"),
                    help="single: one centre pyrometer, fixed zone ratios; multispot: three spots and three zone groups "
                         "(scripts/multispot_heater.py)")
    ap.add_argument("--pointing-residual", type=float, default=None,
                    help="residual pointing (deg) after a commissioning re-aim: the 0.8 deg states are scaled to this tilt "
                         "by linear interpolation from the nominal map (checked against direct maps to 0.07 %% in shape)")
    ap.add_argument("--dump-t", type=int, nargs="*", default=None,
                    help="temperatures (C) whose per-state arrays are saved to OUT/states_<layout>_<T>C.npz")
    ap.add_argument("--rate-um-h", type=float, default=RATE_UM_H, help="wafer-mean net rate")
    ap.add_argument("--heater-design-limit", type=float, default=1473.15,
                    help="element temperature the zone fractions are optimized under (K); the cap stays 1473.15 K")
    args = ap.parse_args()
    RATE_UM_H = args.rate_um_h
    E_RATE = (-args.rate_error, 0.0, args.rate_error)
    E_BFM = (-args.bfm_error, 0.0, args.bfm_error)
    out = Path(args.out or f"results/realizable_controller{'' if args.scattered == 'none' else '_sc_' + args.scattered.replace('+', '_')}")
    out.mkdir(parents=True, exist_ok=True)
    record = lc.comparison_record(args.scattered)
    rec = json.loads(record.read_text(encoding="utf-8"))
    env = rec["inputs"]["envelope"]
    rho = np.asarray(rec["outputs"]["rho_m"])
    params = load_parameters()
    laws = env["operating_point"]["droplet_onset_law"]["value"]
    k_atoms = rec["inputs"]["atoms_per_m2_s_per_nm_min"]
    t_gas = env["vacuum"]["gas_temperature_K"]["value"]
    lip2 = lc.LIP_H.index(0.002)
    scatter = lc.scatter_factors(args.scattered, rho)
    target = 1000.0 * RATE_UM_H / 60.0
    hr.BIASES_K = BIASES_K
    t_c = tuple(range(args.t_min, args.t_max + 10, 10))
    w = lc.area_weights(rho)
    rows = []
    heater_cache = {}
    for (name, scen), t0 in itertools.product(SCENARIOS, t_c):
        inp = oo.load_inputs(rec, env, name, rho, scatter, scen["S_eff_m3_s"])
        inp = {**inp, "n_vac": inp["n_vac"][:, [lip2]], "g_vac": inp["g_vac"][:, [lip2]]}
        for f_aim, a_mm in zip(args.aim_maps or (), args.aim_mm or ()):
            za = np.load(f_aim)
            if str(za["layout"]) == name:
                n_aim = za[f"aim_{a_mm:g}"]
                inp["n_vac"] = n_aim[None, None, :] + (inp["n_vac"] - inp["n_vac"][:1])
        if args.pointing_residual is not None:
            n0 = inp["n_vac"][:1]
            inp["n_vac"] = n0 + (args.pointing_residual / 0.8) * (inp["n_vac"] - n0)
            shape = inp["n_vac"][:, 0] / inp["n_vac"][:, 0].mean(-1, keepdims=True)
            profile_change = float(100 * np.max(np.abs(shape - shape[:1])))
        port = env["layouts"][name]["ga_port_deg"]
        refs = [ga_reference(port, f, d) for f, d in inp["labels"]]
        g_cal = inp["nominal_g"]
        if t0 not in heater_cache:
            if args.heater_control == "multispot":
                ms = _load("multispot_heater")
                heater_cache[t0] = ms.multispot_states(hr.hz, hr, t0 + lc.C, rho, args.heater_design_limit,
                                                       hr.LIMITS[LIMIT_NAME])[0]
            else:
                heater_cache[t0] = heater_states(t0 + lc.C, rho, args.heater_design_limit)
            print(f"heater states at {t0} C: {len(heater_cache[t0])}", flush=True)
        hs = heater_cache[t0]
        t_maps = np.array([s["t_map"] for s in hs])                        # (H, rho)
        reading = np.array([s["reading_K"] for s in hs])                   # (H,)
        i_nom = next(i for i, s in enumerate(hs) if s["controller"] == "pyrometer +0 K"
                     and s.get("edge_spot_error_K", 0.0) == 0.0 and all(s[k] == v for k, v in hr.NOMINAL.items()))
        shortfall = float(t0 + lc.C - hs[i_nom]["reading_K"])
        per_feed = scen["eta"] * lc.N_ATOMS_PER_SCCM / k_atoms
        to_p = lc.SCCM_PA_M3_S * (t_gas / lc.T_STD) / scen["S_eff_m3_s"]
        cap = scen["feed_limit_sccm"]
        n_true = inp["n_vac"][:, 0]                                        # (N, rho) per atom/s
        g_true = inp["g_vac"][:, 0]                                        # (G, rho) vacuum shape with lip
        att_g = inp["att_g"]                                               # (G, P, rho)
        n_cal, ga_cal = n_true[0], g_true[g_cal]
        # ---- calibration on the nominal state ----
        dec_cal = np.array([lc.area_mean(params.decomposition(t_maps[i_nom]), rho)])
        s_c, f_c, p_c, lim_c, att_c = lc.solve_states(n_cal[None, None], inp["att_n"], dec_cal, target, scen["eta"],
                                                     scen["S_eff_m3_s"], cap, t_gas, k_atoms, None, rho)
        row = {**scen, "layout": name, "T_C": t0, "rate_um_h": RATE_UM_H, "nominal_shortfall_K": shortfall,
               "pointing_profile_change_pct": profile_change if args.pointing_residual is not None else None,
               "heater_capped_share": float(np.mean([s["capped"] for s in hs]))}
        if lim_c.any():
            rows.append({**row, "reachable": False})
            continue
        feed_cal, p_cal = float(f_c.ravel()[0]), float(p_c.ravel()[0])
        jn_cal = per_feed * feed_cal * n_cal * att_c.reshape(-1, len(rho))[0]          # nm/min
        n_shape_cal = jn_cal / jn_cal[0]
        ga_arr_shape_cal = ga_cal * lc.att_at(att_g[g_cal], p_cal)
        ga_shape_cal = ga_arr_shape_cal / ga_arr_shape_cal[0]
        r_cal = reading[i_nom]
        row.update({"reachable": True, "calibration": {"feed_sccm": feed_cal, "pressure_Pa": p_cal}, "controllers": {}})
        bound, _ = oo.evaluate_point(inp, t_maps, reading, params, laws, rho, target, k_atoms, scen, cap, t_gas)
        keys = ("valid", "margin", "m_nrich", "m_drop", "thick", "rate", "feed", "g", "h", "law", "n", "e", "eb")
        per_ctrl = {c: {k: [] for k in keys} for c in CONTROLLERS}
        for law in laws:
            b = bound[law]
            kb = per_ctrl["known maps (bound)"]
            kb["valid"].append(b["valid"].ravel())
            kb["margin"].append(b["margin"].ravel())
            kb["thick"].append(b["thickness"].ravel())
            ni, gi_, hi_, li_ = np.indices(b["valid"].shape)
            kb["g"].append(gi_.ravel())
            kb["h"].append(hi_.ravel())
            kb["law"].append(np.full(b["valid"].size, laws.index(law)))
            kb["n"].append(ni.ravel())
            kb["e"].append(np.full(b["valid"].size, -1))
            kb["eb"].append(np.full(b["valid"].size, -1))
            fc_cal = float(params.critical_excess(law, r_cal))
            mid_cal = float(window_mid(n_shape_cal, ga_shape_cal, np.array(jn_cal[0]), np.array(fc_cal)))
            ga_centre_cal = mid_cal * jn_cal[0]                                         # nm/min arrival at p_cal
            vac_needed = ga_centre_cal * k_atoms / ga_arr_shape_cal[0]
            t_cell_cal = float(cell_for(vac_needed, refs[g_cal]))
            st_cal = steady_state(ga_centre_cal * ga_shape_cal, jn_cal, t_maps[i_nom], params, law)
            c_ratio = float(st_cal["net_growth"][0] / lc.area_mean(st_cal["net_growth"], rho))
            row.setdefault("calibration_by_law", {})[law] = {"ga_cell_K": t_cell_cal, "ga_over_n_centre": mid_cal,
                                                            "centre_over_mean_rate": c_ratio}
            dec_true = params.decomposition(t_maps)                                     # (H, rho)
            dec_read = params.decomposition(reading)                                    # (H,)
            fcrit_read = params.critical_excess(law, reading)                           # (H,)

            def evaluate(feed, limited, ga_centre_vac_or_arrival, mode, n_err=1):
                """Growth for feeds (N, H, E) and Ga set by `mode`; returns valid, margin, thickness, rate, feed."""
                p = feed * to_p
                att_n = lc.att_at_many(inp["att_n"], p)                                 # (N, H, E, rho)
                jn = per_feed * feed[..., None] * n_true[:, None, None, :] * att_n      # (N, H, E, rho)
                out = {k: [] for k in keys}
                for gi in range(len(g_true)):
                    ga_arr = g_true[gi] * lc.att_at_many(att_g[gi], p)                  # (N, H, E, rho) per unit vac centre
                    if mode == "cell":       # cell temperature (N, H, E) -> true record flux
                        t_ref, f_ref = refs[gi]
                        vac = f_ref * hk(ga_centre_vac_or_arrival) / hk(t_ref)
                        jg = vac[..., None] * ga_arr / k_atoms
                    else:                    # BFM: true centre arrival (N, H, E, Eb) in nm/min, or per Ga state
                        arr = ga_centre_vac_or_arrival
                        arr = arr[gi] if isinstance(arr, dict) else arr
                        jg = arr[..., None] * (ga_arr / ga_arr[..., :1])[..., None, :]
                    jn_b = jn if mode == "cell" else jn[..., None, :]
                    tm = t_maps[None, :, None, :] if mode == "cell" else t_maps[None, :, None, None, :]
                    st = steady_state(jg, np.broadcast_to(jn_b, jg.shape), np.broadcast_to(tm, jg.shape), params, law)
                    h = st["net_growth"]
                    mean_h = np.sum(w * h, -1)
                    m_nrich, m_drop = st["margin_to_n_rich"].min(-1), st["margin_to_droplets"].min(-1)
                    margin = np.minimum(m_nrich, m_drop)
                    kn_ok = inp["kn_per_sccm"] / feed >= lc.KN_VALID
                    ok = (~limited) & kn_ok & (feed <= cap * (1 + 1e-9))
                    if mode != "cell":
                        ok = ok[..., None]
                    valid = np.broadcast_to(ok, mean_h.shape) & (np.abs(mean_h / target - 1.0) <= RATE_BAND)
                    out["valid"].append(valid.ravel())
                    out["margin"].append(margin.ravel())
                    out["m_nrich"].append(m_nrich.ravel())
                    out["m_drop"].append(m_drop.ravel())
                    hidx = np.broadcast_to(np.arange(len(hs)).reshape((1, -1) + (1,) * (mean_h.ndim - 2)), mean_h.shape)
                    out["g"].append(np.full(mean_h.size, gi))
                    out["h"].append(hidx.ravel())
                    out["law"].append(np.full(mean_h.size, laws.index(law)))
                    idx = np.indices(mean_h.shape)
                    out["n"].append(idx[0].ravel())
                    out["e"].append(idx[2].ravel())
                    out["eb"].append(idx[3].ravel() if mean_h.ndim > 3 else np.full(mean_h.size, -1))
                    out["thick"].append((100 * (h.max(-1) - h.min(-1)) / (2 * mean_h)).ravel())
                    out["rate"].append((mean_h / target - 1.0).ravel())
                    out["feed"].append(np.broadcast_to(feed if mode == "cell" else feed[..., None], mean_h.shape).ravel())
                return {k: np.concatenate(v) for k, v in out.items()}

            # frozen: calibrated feed and cell temperature
            feed_fr = np.full((len(n_true), len(hs), 1), feed_cal)
            res = evaluate(feed_fr, np.zeros_like(feed_fr, bool), np.full(feed_fr.shape, t_cell_cal), "cell")
            for k in res:
                per_ctrl["frozen"][k].append(res[k])
            # rate monitor: feed so the measured centre rate equals the calibrated centre rate
            r_c_star = target * c_ratio
            e = np.array(E_RATE)
            y = r_c_star / (1.0 + e)[None, None, :] + dec_true[None, :, None, 0]         # true centre N arrival needed
            feed_rm, lim_rm = feed_for_centre(y, n_true[:, None, None, 0], inp["att_n"], per_feed, to_p, cap)
            n_est = r_c_star + dec_read                                                   # (H,) controller's centre N
            mid = window_mid(n_shape_cal, ga_shape_cal, n_est, fcrit_read)                # (H,)
            ga_target = mid * n_est                                                       # (H,) centre arrival nm/min
            p_rm = feed_rm * to_p
            ga_att_model = lc.att_at_many(att_g[g_cal], p_rm)[..., 0] * ga_cal[0]         # controller's own model
            vac_set = ga_target[None, :, None] * k_atoms / ga_att_model
            t_cell = cell_for(vac_set, refs[g_cal])
            res = evaluate(feed_rm, lim_rm, t_cell, "cell")
            for k in res:
                per_ctrl["rate monitor"][k].append(res[k])
            # rate monitor + BFM: the true centre arrival is the target within the BFM error
            arrival = ga_target[None, :, None, None] / (1.0 + np.array(E_BFM))[None, None, None, :]
            arrival = np.broadcast_to(arrival, feed_rm.shape + (len(E_BFM),))
            res = evaluate(feed_rm, lim_rm, arrival, "bfm")
            for k in res:
                per_ctrl["rate monitor + BFM"][k].append(res[k])
            # fill-aware: the window from the 8 A shape of the state's fill (at the calibration pressure)
            by_g = {}
            for gi, (fill, _) in enumerate(inp["labels"]):
                gk = inp["labels"].index((fill, "8"))
                gsh = g_true[gk] * lc.att_at(att_g[gk], p_cal)
                mid_f = window_mid(n_shape_cal, gsh / gsh[0], n_est, fcrit_read)
                a_f = (mid_f * n_est)[None, :, None, None] / (1.0 + np.array(E_BFM))[None, None, None, :]
                by_g[gi] = np.broadcast_to(a_f, feed_rm.shape + (len(E_BFM),))
            res = evaluate(feed_rm, lim_rm, by_g, "bfm")
            for k in res:
                per_ctrl["rate monitor + BFM + fill"][k].append(res[k])
            # commissioned maps: each state's own N and Ga shapes (calibration pressure)
            jn_shapes = n_true * lc.att_at(inp["att_n"], p_cal)
            jn_shapes = jn_shapes / jn_shapes[:, :1]                                       # (N, rho)
            by_g = {}
            for gi in range(len(g_true)):
                gsh = g_true[gi] * lc.att_at(att_g[gi], p_cal)
                mid_m = window_mid(jn_shapes[:, None, :], (gsh / gsh[0])[None, None, :], n_est[None, :], fcrit_read[None, :])
                a_m = (mid_m * n_est[None, :])[:, :, None, None] / (1.0 + np.array(E_BFM))[None, None, None, :]
                by_g[gi] = np.broadcast_to(a_m, feed_rm.shape + (len(E_BFM),))
            res = evaluate(feed_rm, lim_rm, by_g, "bfm")
            for k in res:
                per_ctrl["rate monitor + BFM + commissioned maps"][k].append(res[k])
        for c, d in per_ctrl.items():
            va = np.concatenate(d["valid"])
            mg = np.concatenate(d["margin"])
            th = np.concatenate(d["thick"])
            adm = oo.admission(va, mg)
            joint = va & (mg >= 0)
            entry = {**adm, "states": int(va.size),
                     "worst_pct": float(th[joint].max()) if joint.any() else None,
                     "worst_valid_pct": float(th[va].max()) if va.any() else None,
                     "admissible": bool(adm["joint_fraction"] >= ADMIT and shortfall <= 1.0)}
            joint_v = joint
            g_idx, h_idx, l_idx = (np.concatenate(d[k]) for k in ("g", "h", "law"))
            bias_of = np.array([s["controller"] for s in hs])
            entry["joint_by_ga_state"] = {f"{f} mm / {dd} A": float(joint_v[g_idx == i].mean())
                                          for i, (f, dd) in enumerate(inp["labels"])}
            entry["joint_by_law"] = {lw: float(joint_v[l_idx == i].mean()) for i, lw in enumerate(laws)}
            entry["joint_by_pyrometer"] = {bb: float(joint_v[bias_of[h_idx] == bb].mean()) for bb in sorted(set(bias_of))}
            if d["m_nrich"]:
                mn, md = np.concatenate(d["m_nrich"]), np.concatenate(d["m_drop"])
                entry["out_of_window_by_side"] = {"N-rich somewhere": float((mn < 0).mean()),
                                                  "droplets somewhere": float((md < 0).mean())}
            if d["rate"]:
                rate = np.concatenate(d["rate"])
                feed = np.concatenate(d["feed"])
                entry.update({"mean_rate_error_pct": [float(100 * rate.min()), float(100 * rate.max())],
                              "feed_sccm": [float(feed.min()), float(feed.max())]})
            row["controllers"][c] = entry
        rows.append(row)
        if t0 in (args.dump_t or ()):
            meta = {"laws": laws, "ga_labels": inp["labels"], "e_rate": E_RATE, "e_bfm": E_BFM,
                    "heater": [{k: s_[k] for k in ("eps", "contact", "zone_error", "controller")} for s_ in hs]}
            np.savez_compressed(out / f"states_{name}_{t0}C.npz", meta=json.dumps(meta),
                                **{f"{c}|{k}": np.concatenate(v) for c, d in per_ctrl.items() for k, v in d.items() if v})
        print(f"{name} {t0} C: " + "; ".join(f"{c}: joint {100 * e['joint_fraction']:.1f} %, worst "
                                            f"{e['worst_pct'] if e['worst_pct'] is None else round(e['worst_pct'], 2)} %"
                                            for c, e in row["controllers"].items()), flush=True)
    summary = []
    for name, scen in SCENARIOS:
        rr = [r for r in rows if r["layout"] == name and r.get("reachable")]
        for c in CONTROLLERS:
            ok = [r for r in rr if r["controllers"][c]["admissible"]]
            summary.append({"layout": name, **scen, "controller": c,
                            "coldest_T_C": ok[0]["T_C"] if ok else None,
                            "worst_pct_there": ok[0]["controllers"][c]["worst_pct"] if ok else None,
                            "joint_at_720C": next((r["controllers"][c]["joint_fraction"] for r in rr if r["T_C"] == 720), None)})
            s = summary[-1]
            print(f"{name} {c}: coldest admissible {s['coldest_T_C']} C, worst {s['worst_pct_there']}, joint at 720 C "
                  f"{s['joint_at_720C']}", flush=True)
    manifest = build_manifest(
        "realizable_controller", label="representative_chamber", validation_status="not_validated",
        inputs={"record": str(record.relative_to(ROOT)), "scattered": args.scattered, "scenarios": SCENARIOS,
                "rate_um_h": RATE_UM_H, "T_C": t_c, "element_limit": LIMIT_NAME, "pyrometer_biases_K": BIASES_K,
                "rate_monitor_errors": E_RATE, "bfm_errors": E_BFM, "rate_band": RATE_BAND, "admit": ADMIT,
                "controllers": CONTROLLERS, "heater_design_limit_K": args.heater_design_limit,
                "pointing_residual_deg": args.pointing_residual, "heater_control": args.heater_control, "aim_maps": args.aim_maps, "aim_mm": args.aim_mm,
                "aim_maps_sha256": {f: lc.file_sha256(Path(f)) for f in (args.aim_maps or ())}, "lip_m": 0.002, "pointing_ensemble_deg": 0.8,
                "ga_records_sha256": {lc.ga_record(env["layouts"][n]["ga_port_deg"], f, d):
                                      lc.file_sha256(lc.GA_RECORDS / lc.ga_record(env["layouts"][n]["ga_port_deg"], f, d))
                                      for n, _ in SCENARIOS for f, d in itertools.product((40, 70, 120), lc.GA_D)}},
        outputs={"rows": rows, "summary": summary},
        sources=([ROOT / "scripts/multispot_heater.py"] if args.heater_control == "multispot" else [])
                + ([ROOT / "scripts/nitrogen_aim_operating.py"] if args.aim_maps else [])
                + [Path(__file__), ROOT / "scripts/operating_optimum.py", ROOT / "scripts/heater_robustness.py",
                 ROOT / "scripts/layout_comparison.py", ROOT / "scripts/heater_zones.py", ROOT / "src/mbe_twin/growth.py",
                 ROOT / "src/mbe_twin/heater.py", ROOT / "src/mbe_twin/vapour.py", ROOT / "data/parameters/gan_growth.json",
                 record] + lc.scatter_sources(scatter),
        warnings=["Representative chamber; no model in the chain is validated on the proposed machine",
                  "Observation error magnitudes (rate monitor 1 %, BFM 2 %) are priors; instruments not selected",
                  "Steady state per state; transients and campaign drift between measurements are in the twin, not here",
                  "Crystal quality is not modelled; the cold limit is the growth-window limit only"])
    print(f"Wrote {write_manifest(manifest, out / 'manifest.json')}")


if __name__ == "__main__":
    main()
