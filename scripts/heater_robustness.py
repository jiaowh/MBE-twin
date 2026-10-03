"""Combined heater errors, element headroom, and a Ga correction tied to the measured temperature.

The layout comparison perturbs the heater one property at a time and found the decisive case
to be a wafer of higher emissivity: with no element headroom it runs about 14.5 K cold, and
with the Ga flux held it leaves the Ga-rich window. This study, for the designed-density heater
of the B family (1 mm overlap holder):
1. Combined errors: wafer emissivity 0.63 / 0.70 / 0.77 x wafer-ledge contact 50 / 200 / 1000
   W m^-2 K^-1 x zone power error none / +2 % / -2 % in the worst zone (27 states), at the
   nominal zone ratios. Two controllers:
   - mean: one reading holds the wafer mean (as the comparison);
   - centre pyrometer: the heater holds the reading of one spot at the wafer centre (bias
     -2 / 0 / +2 K), solved with the heater model (heater_zones.at_reading), not as a uniform
     shift; the uniform-shift approximation of earlier versions is reported as an error bound.
   For each: the element temperature needed and, under each element limit, the capped state
   (power at the limit, the wafer at whatever temperature that gives).
2. Headroom: the element limit at which every combined state holds the target.
3. Ga protocols, for the layouts B-p (the working layout), B and B-L at their 1 um/h operating
   points (eta = 1, 2 m^3/s, 10 sccm, the comparison record), over the comparison's matched
   ensemble for pointing within +/-0.8 deg (25 maps), the Ga fills and diameters (6) and the
   droplet laws (3), lip 2 mm. In every heater state the nitrogen balance is the comparison's:
   the output is re-set for the operating rate, so each state has its own feed, pressure and
   N and Ga attenuation (layout_comparison.solve_states). Ga protocols:
   - fixed: the Ga cell output (absolute) set once in the nominal state (nominal pointing,
     70 mm, d = 8 A, nominal heater, mean controller) to the middle of its window; its arrival
     in every other state follows that state's attenuation (the comparison protocol);
   - temperature-corrected: the cell output re-set so the centre flux is the middle of the
     window that the controller's reading implies (the window computed with the state's own N
     and Ga maps at its pressure, for a uniform wafer at the reading: a calibration table
     Ga(T), not the true temperature map);
   - ideal: re-set to the middle of the state's true window (a bound).
   The window margin (min over r <= 94 mm) is reported per state. States are counted over the
   whole ensemble and over its valid states (N supply feasible at Kn >= 10 and the operating rate
   actually grown), and at nominal pointing / 70 mm / d = 8 A for comparison with earlier records.
4. Thickness half-range/mean on r <= 94 mm with the temperature-corrected protocol, nominal
   pointing / 70 mm / d = 8 A and over the whole ensemble: the heater's contribution when its
   errors act together.

Usage: python scripts/heater_robustness.py [--layouts B-p B B-L] [--scattered none|gas|gas-gamma0.1|gas+plume] [--out results/heater_robustness]
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

from mbe_twin.growth import load_parameters, steady_state  # noqa: E402
from mbe_twin.manifest import build_manifest, write_manifest  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("layout_comparison", ROOT / "scripts/layout_comparison.py")
lc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lc)
hz = lc.hz
EPS = (0.63, 0.70, 0.77)
CONTACT = (50.0, 200.0, 1000.0)
ZONE = (0.0, 0.02, -0.02)
OPENING = 0.099
T0_C = (700.0, 740.0)
LIMITS = {"1473 K element": 1473.15, "1373 K element": 1373.15}
BIASES_K = (-2.0, 0.0, 2.0)
RECORD = ROOT / "data/runs/studies/layout_comparison_bc.json"
MAPS = ROOT / "results/layout_comparison_bc"
SCENARIO = {"eta": 1.0, "S_eff_m3_s": 2.0, "feed_limit_sccm": 10.0, "target": "1", "heater_limit": "1473 K element"}
NOMINAL = {"eps": 0.70, "contact": 200.0, "zone_error": 0.0}


def _held(m, f, target_k, reading, lim, p0):
    """Hold a reading at the target; cap the power at the element limit if that needs more."""
    rr = hz.at_reading(m, f, target_k, reading, p0=p0)
    need = float(rr["t_heater"].max())
    capped = lim is not None and need > lim
    if capped:
        rr = hz.at_limit(m, f, lim, p_hi=rr["zone_power"].sum())
    return rr, need, capped


def combined_states(t0_k, rho):
    """Zone ratios optimized for the nominal holder under each limit, then every combined error held by each
    controller (wafer mean; centre pyrometer with each bias). Returns a list of state dicts."""
    edges = hz.LAYOUTS["12 zones"]
    geo = {"ledge_inner": OPENING}
    base = hz.make(edges, geo, {})
    states = []
    for lname, lim in {"none": None, **LIMITS}.items():
        r, frac = hz.optimize(base, t0_k, limits=None if lim is None else {"t_heater_max": lim})
        p0 = r["zone_power"].sum()
        for eps, h, z in itertools.product(EPS, CONTACT, ZONE):
            m = hz.make(edges, geo, {"eps_wafer": eps, "h_contact": h})
            cands = [frac]
            if z != 0.0:
                cands = []
                for k in range(m.n_zones):
                    f = frac.copy()
                    f[k] *= 1 + z
                    cands.append(f / f.sum())
            worst = None
            for f in cands:
                rr = hz.at_mean(m, f, t0_k, p0=p0)
                if worst is None or rr["wafer_range"] > worst[0]["wafer_range"]:
                    worst = (rr, f)
            f = worst[1]
            common = {"limit": lname, "eps": eps, "contact": h, "zone_error": z}
            rr, need, capped = _held(m, f, t0_k, lambda x: x["wafer_mean"], lim, p0)
            mean_map = np.interp(rho, rr["r_wafer"], rr["t_wafer"])
            states.append({**common, "controller": "mean", "t_heater_needed_K": need, "capped": bool(capped),
                           "wafer_mean_K": rr["wafer_mean"], "wafer_range_K": rr["wafer_range"],
                           "reading_K": float(rr["wafer_mean"]), "t_map": mean_map})
            for bias in BIASES_K:
                rr, need, capped = _held(m, f, t0_k, lambda x, b=bias: hz.centre_reading(x, b), lim, p0)
                t_map = np.interp(rho, rr["r_wafer"], rr["t_wafer"])
                # the approximation of earlier versions: the mean-held map shifted uniformly to the centre target
                shift = t0_k - bias - mean_map[0]
                approx = mean_map + (min(shift, 0.0) if capped else shift)
                states.append({**common, "controller": f"pyrometer {bias:+g} K", "t_heater_needed_K": need,
                               "capped": bool(capped), "wafer_mean_K": rr["wafer_mean"], "wafer_range_K": rr["wafer_range"],
                               "reading_K": hz.centre_reading(rr, bias), "t_map": t_map,
                               "uniform_shift_error_K": float(np.max(np.abs(approx - t_map)))})
    return states


def window(jn, shape, t_map, params, law):
    """Centre Ga/N bounds of the Ga-rich window for N maps jn (..., rho) and Ga shapes (..., rho; any centre value),
    with the droplet onset of t_map (broadcast)."""
    s = shape / shape[..., :1]
    fcrit = params.critical_excess(law, t_map)
    lo = np.max(jn / (jn[..., :1] * s), axis=-1)
    hi = np.min((jn + fcrit) / (jn[..., :1] * s), axis=-1)
    return lo, hi


def mid(lo, hi):
    return np.where(hi > lo, 0.5 * (lo + hi), lo * 1.02)


def layout_inputs(rec, env, name, rho, scatter=None, speed=None):
    """N maps (+/-0.8 deg ensemble, 2 mm lip) and Ga shapes / attenuation tables from the comparison's keyed caches."""
    lay = env["layouts"][name]
    n = lay["n"]
    prefix = f"N_{n['L_over_r']:g}_{n['polar_deg']:g}_{n['aim_offset_mm']:g}_"
    nf = next(c for c in rec["inputs"]["map_caches"] if c["file"].startswith(prefix))
    zn = np.load(MAPS / nf["file"])
    if str(zn["cache_key"]) != nf["key"]:
        raise SystemExit(f"heater_robustness: N cache key mismatch for {name}")
    states = json.loads(str(zn["states"]))
    idx08 = [0] + [i for i, s in enumerate(states) if s[1] == 0.8]
    lip = lc.LIP_H.index(0.002)
    n_vac = (zn["maps"][idx08] * zn["lip"][lip])[:, None, :]                          # (N, 1, rho)
    port = lay["ga_port_deg"]
    fills = env["ga_source"]["port_options_deg"][str(port)]["admissible_fills_mm"]
    labels = [(fill, d) for fill in fills for d in lc.GA_D]
    g_vac, att_g = [], []
    for fill, d in labels:
        gf = next(c for c in rec["inputs"]["map_caches"] if c["file"].startswith(f"Ga_{port}_{fill}_"))
        zg = np.load(MAPS / gf["file"])
        if str(zg["cache_key"]) != gf["key"]:
            raise SystemExit(f"heater_robustness: Ga cache key mismatch for {gf['file']}")
        g_vac.append(lc.ga_shape(lc.ga_record(port, fill, d), rho) * zg["lip"][lip])
        att_g.append(zg[f"att_{d}"])
    att_n, att_g = lc.with_scattered(scatter, name, port, zn["att"], np.array(att_g), labels, speed)
    plate = lc.layout_plate(lay, env)
    kn_per_sccm = min(lc.plate_knudsen(1.0, plate, t, f) for t in (300.0, 600.0) for f in (1.3, 1.0, 1 / 1.3))
    return {"n_vac": n_vac, "att_n": att_n, "g_vac": np.array(g_vac), "att_g": att_g, "labels": labels,
            "nominal_g": labels.index((70, "8")), "kn_per_sccm": kn_per_sccm, "n_states": len(idx08)}


def protocols(inp, states, row, env, params, laws, rho, k_atoms):
    """Margins, rates and thickness over (N, G, H) for every protocol and law, with the per-state N balance."""
    t_maps = np.array([s["t_map"] for s in states])                                    # (H, rho)
    dec_mean = lc.area_mean(params.decomposition(t_maps), rho)                          # (H,)
    target = row["operating_point"]["rate_nm_min"]
    t_gas = env["vacuum"]["gas_temperature_K"]["value"]
    s, feed, p, limited, att = lc.solve_states(inp["n_vac"], inp["att_n"], dec_mean, target, SCENARIO["eta"],
                                               SCENARIO["S_eff_m3_s"], row["feed_cap_sccm"], t_gas, k_atoms, None, rho)
    jn = (s[..., None] * inp["n_vac"][:, None] * att)[:, :, 0]                          # (N, H, rho)
    p = p[:, :, 0]
    ga_unit = np.stack([inp["g_vac"][g] * lc.att_at_many(inp["att_g"][g], p) for g in range(len(inp["g_vac"]))], 1)  # (N, G, H, rho)
    jn_b = np.broadcast_to(jn[:, None], ga_unit.shape)
    t_b = np.broadcast_to(t_maps[None, None], ga_unit.shape)
    reading = np.array([s["reading_K"] for s in states])                                # (H,)
    uni = np.broadcast_to(reading[None, None, :, None], ga_unit.shape)
    feasible = np.broadcast_to(((~limited[:, :, 0]) & (inp["kn_per_sccm"] / feed[:, :, 0] >= lc.KN_VALID))[:, None],
                               ga_unit.shape[:-1])
    nom_h = next(i for i, st in enumerate(states) if st["controller"] == "mean"
                 and all(st[k] == v for k, v in NOMINAL.items()))
    out = {}
    for law in laws:
        jn0, gn = jn[0, nom_h], ga_unit[0, inp["nominal_g"], nom_h]
        lo0, hi0 = window(jn0, gn, t_maps[nom_h], params, law)
        a_fixed = float(mid(lo0, hi0)) * float(jn0[0]) / float(gn[0])                  # absolute cell output
        shape = ga_unit / ga_unit[..., :1]
        lo_c, hi_c = window(jn_b, shape, uni, params, law)
        lo_t, hi_t = window(jn_b, shape, t_b, params, law)
        arrivals = {"fixed": a_fixed * ga_unit,
                    "temperature-corrected": (mid(lo_c, hi_c) * jn_b[..., 0])[..., None] * shape,
                    "ideal": (mid(lo_t, hi_t) * jn_b[..., 0])[..., None] * shape}
        res = {}
        for proto, j_ga in arrivals.items():
            st = steady_state(j_ga, jn_b, t_b, params, law)
            h = st["net_growth"]
            mean_h = lc.area_mean(h, rho)
            res[proto] = {"margin": np.minimum(st["margin_to_n_rich"], st["margin_to_droplets"]).min(-1),
                          "on_target": mean_h >= target * (1.0 - lc.RATE_TOL),
                          "thickness": 100 * (h.max(-1) - h.min(-1)) / (2 * mean_h)}
        out[law] = res
    return out, feasible, {"feed_sccm": [float(feed.min()), float(feed.max())], "pressure_Pa": [float(p.min()), float(p.max())],
                           "supply_limited_fraction": float(np.mean(limited))}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--layouts", nargs="+", default=["B-p", "B", "B-L"])
    ap.add_argument("--scattered", default="none", choices=lc.SCATTER_VARIANTS,
                    help="add gas-scattered atoms (reads the comparison record of that variant)")
    ap.add_argument("--out", default="results/heater_robustness")
    args = ap.parse_args()
    record = lc.comparison_record(args.scattered)
    rec = json.loads(record.read_text(encoding="utf-8"))
    if rec["inputs"].get("scattered", "none") != args.scattered:
        raise SystemExit(f"heater_robustness: {record.name} was not run with --scattered {args.scattered}")
    env = rec["inputs"]["envelope"]
    rho = np.asarray(rec["outputs"]["rho_m"])
    params = load_parameters()
    laws = env["operating_point"]["droplet_onset_law"]["value"]
    k_atoms = rec["inputs"]["atoms_per_m2_s_per_nm_min"]
    scatter = lc.scatter_factors(args.scattered, rho)
    inputs = {name: layout_inputs(rec, env, name, rho, scatter, SCENARIO["S_eff_m3_s"]) for name in args.layouts}
    out, used_rows = {}, {}
    for t0 in T0_C:
        t0_k = t0 + lc.C
        states = combined_states(t0_k, rho)
        heater = {}
        for lname in ("none", *LIMITS):
            sub = [s for s in states if s["limit"] == lname]
            mean_sub = [s for s in sub if s["controller"] == "mean"]
            pyro = [s for s in sub if s["controller"] != "mean"]
            heater[lname] = {"capped_fraction_mean_controller": float(np.mean([s["capped"] for s in mean_sub])),
                             "capped_fraction_pyrometer": float(np.mean([s["capped"] for s in pyro])),
                             "t_heater_needed_max_K": max(s["t_heater_needed_K"] for s in sub),
                             "mean_shortfall_max_K": max(t0_k - s["wafer_mean_K"] for s in mean_sub),
                             "wafer_range_max_K": max(s["wafer_range_K"] for s in sub),
                             "pyrometer_wafer_mean_K": [min(s["wafer_mean_K"] for s in pyro), max(s["wafer_mean_K"] for s in pyro)],
                             "uniform_shift_error_max_K": max(s["uniform_shift_error_K"] for s in pyro)}
            h = heater[lname]
            print(f"{t0:.0f} C, limit {lname}: element needed up to {h['t_heater_needed_max_K']:.1f} K, capped "
                  f"{100 * h['capped_fraction_mean_controller']:.0f} % (mean) / {100 * h['capped_fraction_pyrometer']:.0f} % "
                  f"(pyrometer), shortfall up to {h['mean_shortfall_max_K']:.1f} K; uniform-shift error up to "
                  f"{h['uniform_shift_error_max_K']:.2f} K", flush=True)
        per_layout = {}
        for name in args.layouts:
            row = next((r for r in rec["outputs"]["rows"] if r["layout"] == name and r["T0_C"] == t0 and r.get("evaluated")
                        and all(r[k] == v for k, v in SCENARIO.items())), None)
            if row is None:
                per_layout[name] = {"evaluated": False, "reason": "no evaluated 1 um/h row for the scenario"}
                continue
            used_rows[f"{name} {t0:g}"] = {k: row[k] for k in ("layout", "T0_C", *SCENARIO)} | {
                "operating_point": row["operating_point"], "feed_cap_sccm": row["feed_cap_sccm"]}
            inp = inputs[name]
            per_limit = {}
            for lname in ("none", *LIMITS):
                sub = [s for s in states if s["limit"] == lname]
                res, feasible, nbal = protocols(inp, sub, row, env, params, laws, rho, k_atoms)
                groups = {"mean": [i for i, s in enumerate(sub) if s["controller"] == "mean"]}
                for b in BIASES_K:
                    groups[f"pyrometer {b:+g} K"] = [i for i, s in enumerate(sub) if s["controller"] == f"pyrometer {b:+g} K"]
                groups["pyrometer (all biases)"] = [i for i, s in enumerate(sub) if s["controller"] != "mean"]
                gi = inp["nominal_g"]
                summ = {}
                for gname, hs in groups.items():
                    for proto in ("fixed", "temperature-corrected", "ideal"):
                        mg = np.stack([res[l][proto]["margin"][:, :, hs] for l in laws], -1)        # (N, G, H, law)
                        ok = np.stack([res[l][proto]["on_target"][:, :, hs] for l in laws], -1)
                        fe = np.broadcast_to(feasible[:, :, hs][..., None], mg.shape)
                        th = np.stack([res[l][proto]["thickness"][:, :, hs] for l in laws], -1)
                        valid = fe & ok
                        summ[f"{gname} / {proto}"] = {
                            "in_window_fraction": float(np.mean(mg >= 0.0)),
                            "valid_fraction": float(np.mean(valid)),
                            "in_window_fraction_of_valid": float(np.mean(mg[valid] >= 0.0)) if valid.any() else None,
                            "in_window_fraction_nominal_maps": float(np.mean(mg[0, gi] >= 0.0)),
                            "thickness_pct_nominal_maps": [float(th[0, gi].min()), float(th[0, gi].max())],
                            "thickness_pct_max": float(th.max()), "thickness_pct_valid_max": float(th[valid].max()) if valid.any() else None}
                per_limit[lname] = {"nitrogen_balance": nbal, "protocols": summ}
                for key in ("mean / fixed", "mean / temperature-corrected", "pyrometer (all biases) / fixed",
                            "pyrometer (all biases) / temperature-corrected"):
                    v = summ[key]
                    print(f"{t0:.0f} C, {lname}, {name}: {key}: in window {100 * v['in_window_fraction']:.0f} % of the ensemble "
                          f"({100 * v['in_window_fraction_nominal_maps']:.0f} % at nominal maps); thickness nominal maps "
                          f"{v['thickness_pct_nominal_maps'][0]:.2f}-{v['thickness_pct_nominal_maps'][1]:.2f} %, ensemble max "
                          f"{v['thickness_pct_max']:.2f} %", flush=True)
            per_layout[name] = {"evaluated": True, "limits": per_limit}
        out[f"{t0:g}"] = {"heater": heater, "states": [{k: v for k, v in s.items() if k != "t_map"} for s in states],
                          "layouts": per_layout,
                          "headroom_needed_K": {ln: max(s["t_heater_needed_K"] for s in states if s["limit"] == ln) - lim
                                                for ln, lim in LIMITS.items()}}
    manifest = build_manifest(
        "heater_robustness", label="representative_chamber", validation_status="not_validated",
        inputs={"eps": EPS, "contact": CONTACT, "zone_error": ZONE, "opening_m": OPENING, "T0_C": T0_C, "limits_K": LIMITS,
                "pyrometer_bias_K": BIASES_K, "record": str(record.relative_to(ROOT)), "scattered": args.scattered, "record_run_id": rec["run_id"],
                "scenario": SCENARIO, "layouts": args.layouts, "rows": used_rows, "kn_valid": lc.KN_VALID,
                "rate_tolerance_rel": lc.RATE_TOL, "map_caches": [c for c in rec["inputs"]["map_caches"]]},
        outputs=out,
        sources=[Path(__file__), ROOT / "scripts/heater_zones.py", ROOT / "scripts/layout_comparison.py",
                 ROOT / "src/mbe_twin/heater.py", ROOT / "src/mbe_twin/growth.py", record]
        + lc.scatter_sources(scatter),
        warnings=["Pointing within +/-0.8 deg, Ga fills and diameters, droplet laws; lip 2 mm only",
                  "The controller's Ga(T) table is computed from the model itself; on the machine it would be a "
                  "commissioning calibration", "Reduced axisymmetric heater model",
                  "Grid of states, not a probability distribution"])
    print(f"Wrote {write_manifest(manifest, Path(args.out) / 'manifest.json')}")


if __name__ == "__main__":
    main()
