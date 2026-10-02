"""Operating point that trades uniformity, growth rate and growth temperature (Pareto fronts per supply scenario).

The project's goals are as uniform as possible, as fast as possible, as cold as possible. They
conflict: a higher rate needs more nitrogen feed, which raises the pressure and scatters the
beams unevenly; a colder wafer narrows the Ga-rich growth window. There is no single optimum,
so this study scans the operating choices and reports the non-dominated set (Pareto front) in
(worst-case thickness, rate, temperature) for each supply scenario, with one balanced pick
(the front point nearest the ideal in range-normalized objectives).

Choices scanned: layout (B-p, B-L), growth temperature (680-780 C), wafer-mean net rate
(0.25-2 um/h). Supply scenarios (unknown hardware, not choices): conversion eta and the pair
(effective N2 pumping speed, feed limit).

Each point is the comparison's uncertainty grid (scripts/layout_comparison.py) restricted to
pointing within +/-0.8 deg: 25 pointing maps x Ga fills and diameters x 7 heater states x
3 lip heights x 3 droplet laws, each state with its own feed, pressure and attenuation
(layout_comparison.solve_states). Ga is steered from the temperature reading (the protocol
scripts/heater_robustness.py supports): in every state the Ga cell output is re-set so that the
centre flux is the middle of the window that the wafer-mean reading implies, computed with the
state's own N and Ga maps. Per point:
- worst-case thickness half-range/mean over valid states (N supply feasible with plate Kn >= 10,
  and the operating rate actually grown);
- nominal thickness;
- share of valid states, share of states in the growth window.
A point is admissible if at least ADMIT of its states are valid, at least ADMIT are in the
window, and the nominal heater state reaches the labelled temperature under the element limit
(1473 K) within 1 K; the front is taken over admissible points. Decomposition is fitted to 720-805 C data
(G02): points below 720 C are extrapolations and are flagged.

Not represented: crystal quality, morphology and impurity incorporation, which also set a
lower temperature bound in practice; scattered-beam redeposition; combined heater errors.

Usage: python scripts/operating_optimum.py [--out results/operating_optimum]
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
RECORD = ROOT / "data/runs/studies/layout_comparison_bc.json"
MAPS = ROOT / "results/layout_comparison_bc"
LAYOUTS = ("B-p", "B-L")
T_C = tuple(range(680, 790, 10))
RATES_UM_H = (0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0)
SCENARIOS = [{"eta": 1.0, "S_eff_m3_s": 2.0, "feed_limit_sccm": 10.0},
             {"eta": 1.0, "S_eff_m3_s": 4.0, "feed_limit_sccm": 35.0},
             {"eta": 0.3, "S_eff_m3_s": 4.0, "feed_limit_sccm": 35.0},
             {"eta": 0.1, "S_eff_m3_s": 4.0, "feed_limit_sccm": 35.0}]
LIMIT = ("1473 K element", 1473.15)
ADMIT = 0.95
DECOMPOSITION_VALID_C = 720.0


def load_inputs(rec, env, name, rho):
    """N maps (+/-0.8 deg ensemble, all lips) and Ga shapes / tables from the comparison's keyed caches."""
    lay = env["layouts"][name]
    n = lay["n"]
    prefix = f"N_{n['L_over_r']:g}_{n['polar_deg']:g}_{n['aim_offset_mm']:g}_"
    nf = next(c for c in rec["inputs"]["map_caches"] if c["file"].startswith(prefix))
    zn = np.load(MAPS / nf["file"])
    if str(zn["cache_key"]) != nf["key"]:
        raise SystemExit(f"operating_optimum: N cache key mismatch for {name}")
    states = json.loads(str(zn["states"]))
    idx08 = [0] + [i for i, s in enumerate(states) if s[1] == 0.8]
    n_vac = zn["maps"][idx08][:, None, :] * zn["lip"][None, :, :]                       # (N, L, rho)
    port = lay["ga_port_deg"]
    fills = env["ga_source"]["port_options_deg"][str(port)]["admissible_fills_mm"]
    labels = [(fill, d) for fill in fills for d in lc.GA_D]
    g_vac, att_g = [], []
    for fill, d in labels:
        gf = next(c for c in rec["inputs"]["map_caches"] if c["file"].startswith(f"Ga_{port}_{fill}_"))
        zg = np.load(MAPS / gf["file"])
        if str(zg["cache_key"]) != gf["key"]:
            raise SystemExit(f"operating_optimum: Ga cache key mismatch for {gf['file']}")
        g_vac.append(lc.ga_shape(lc.ga_record(port, fill, d), rho)[None, :] * zg["lip"])   # (L, rho)
        att_g.append(zg[f"att_{d}"])
    plate = lc.layout_plate(lay, env)
    kn_per_sccm = min(lc.plate_knudsen(1.0, plate, t, f) for t in (300.0, 600.0) for f in (1.3, 1.0, 1 / 1.3))
    return {"n_vac": n_vac, "att_n": zn["att"], "lip_n": zn["lip"], "map0": zn["maps"][0], "g_vac": np.array(g_vac),
            "att_g": np.array(att_g), "labels": labels, "nominal_g": labels.index((70, "8")), "kn_per_sccm": kn_per_sccm,
            "heater": lay["heater"]}


def evaluate_point(inp, t_maps, reading, params, laws, rho, target, k_atoms, scen, feed_cap, t_gas):
    """Corrected-Ga protocol over the ensemble at one operating point. Returns per-law arrays over (N, G, H, L)."""
    dec_mean = lc.area_mean(params.decomposition(t_maps), rho)                                         # (H,)
    s, feed, p, limited, att = lc.solve_states(inp["n_vac"], inp["att_n"], dec_mean, target, scen["eta"],
                                               scen["S_eff_m3_s"], feed_cap, t_gas, k_atoms, None, rho)
    jn = s[..., None] * inp["n_vac"][:, None] * att                                                    # (N, H, L, rho)
    ga = np.stack([inp["g_vac"][g][None, None] * lc.att_at_many(inp["att_g"][g], p) for g in range(len(inp["g_vac"]))], 1)
    jn_b = np.broadcast_to(jn[:, None], ga.shape)                                                      # (N, G, H, L, rho)
    t_b = np.broadcast_to(t_maps[None, None, :, None, :], ga.shape)
    uni = np.broadcast_to(reading[None, None, :, None, None], ga.shape)
    shape = ga / ga[..., :1]
    feasible = np.broadcast_to(((~limited) & (inp["kn_per_sccm"] / feed >= lc.KN_VALID))[:, None], ga.shape[:-1])
    out = {}
    for law in laws:
        fcrit = params.critical_excess(law, uni)
        lo = np.max(jn_b / (jn_b[..., :1] * shape), axis=-1)
        hi = np.min((jn_b + fcrit) / (jn_b[..., :1] * shape), axis=-1)
        mid = np.where(hi > lo, 0.5 * (lo + hi), lo * 1.02)
        st = steady_state((mid * jn_b[..., 0])[..., None] * shape, jn_b, t_b, params, law)
        h = st["net_growth"]
        mean_h = lc.area_mean(h, rho)
        out[law] = {"thickness": 100 * (h.max(-1) - h.min(-1)) / (2 * mean_h),
                    "margin": np.minimum(st["margin_to_n_rich"], st["margin_to_droplets"]).min(-1),
                    "valid": feasible & (mean_h >= target * (1.0 - lc.RATE_TOL))}
    return out, {"feed_sccm": [float(feed.min()), float(feed.max())], "pressure_Pa": [float(p.min()), float(p.max())],
                 "kn_min": float(inp["kn_per_sccm"] / feed.max())}


def pareto(points):
    """Indices of points not dominated in (thickness: min, rate: max, temperature: min)."""
    keep = []
    for i, a in enumerate(points):
        dominated = any((b["worst_pct"] <= a["worst_pct"] and b["rate_um_h"] >= a["rate_um_h"] and b["T_C"] <= a["T_C"])
                        and (b["worst_pct"] < a["worst_pct"] or b["rate_um_h"] > a["rate_um_h"] or b["T_C"] < a["T_C"])
                        for j, b in enumerate(points) if j != i)
        if not dominated:
            keep.append(i)
    return keep


def balanced(front):
    """Front point nearest the ideal (best of each objective) in objectives normalized by the front's range."""
    if not front:
        return None
    w = np.array([p["worst_pct"] for p in front])
    r = np.array([p["rate_um_h"] for p in front])
    t = np.array([p["T_C"] for p in front], float)

    def norm(x, best_low):
        span = x.max() - x.min()
        if span == 0:
            return np.zeros_like(x)
        return (x - x.min()) / span if best_low else (x.max() - x) / span
    d = np.sqrt(norm(w, True) ** 2 + norm(r, False) ** 2 + norm(t, True) ** 2)
    return front[int(np.argmin(d))]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="results/operating_optimum")
    args = ap.parse_args()
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    env = rec["inputs"]["envelope"]
    rho = np.asarray(rec["outputs"]["rho_m"])
    params = load_parameters()
    laws = env["operating_point"]["droplet_onset_law"]["value"]
    k_atoms = rec["inputs"]["atoms_per_m2_s_per_nm_min"]
    t_gas = env["vacuum"]["gas_temperature_K"]["value"]
    openings = env["wafer_and_mask"]["holder_opening_radius_m"]["value"]
    inputs = {name: load_inputs(rec, env, name, rho) for name in LAYOUTS}
    heat = {}
    for t0 in T_C:
        for opt in sorted({inp["heater"] for inp in inputs.values()}):
            opening = openings["3 mm overlap"] if opt == "3 zones" else openings["1 mm overlap"]
            heat[(opt, t0)] = lc.heater_states(opt, opening, t0 + lc.C, LIMIT[1], rho)
        print(f"heater states at {t0} C done", flush=True)
    points = []
    for scen, name, t0 in itertools.product(SCENARIOS, LAYOUTS, T_C):
        inp = inputs[name]
        t_maps, hrep = heat[(inp["heater"], t0)]
        reading = np.array(hrep["state_wafer_mean_K"])
        dec_nom = float(lc.area_mean(params.decomposition(t_maps[0]), rho))
        lip2 = lc.LIP_H.index(0.002)

        def delivered(p):
            return float(lc.area_mean(inp["map0"] * lc.att_at(inp["att_n"], p) * inp["lip_n"][lip2], rho))
        for rate in RATES_UM_H:
            target = 1000.0 * rate / 60.0
            op = lc.operating_point(delivered, dec_nom, target, scen["eta"], scen["S_eff_m3_s"], scen["feed_limit_sccm"],
                                    t_gas, k_atoms)
            base = {**scen, "layout": name, "T_C": t0, "rate_um_h": rate, "extrapolated_decomposition": t0 < DECOMPOSITION_VALID_C,
                    "nominal_feed_sccm": op["feed_sccm"], "nominal_kn": inp["kn_per_sccm"] / op["feed_sccm"]}
            if not op["target_reached"]:
                points.append({**base, "reachable": False})
                continue
            feed_cap = op["feed_sccm"] if op.get("rate_peaks_below_feed_limit") else scen["feed_limit_sccm"]
            res, nbal = evaluate_point(inp, t_maps, reading, params, laws, rho, target, k_atoms, scen, feed_cap, t_gas)
            th = np.stack([res[l]["thickness"] for l in laws], -1)
            mg = np.stack([res[l]["margin"] for l in laws], -1)
            va = np.stack([res[l]["valid"] for l in laws], -1)
            nom = (0, inp["nominal_g"], 0, lip2, laws.index("Ref14_growth"))
            pt = {**base, "reachable": True, **nbal, "valid_fraction": float(va.mean()), "in_window_fraction": float((mg >= 0).mean()),
                  "worst_pct": float(th[va].max()) if va.any() else None, "nominal_pct": float(th[nom]),
                  "heater_capped_fraction": float(np.mean(hrep["state_capped"])),
                  "nominal_shortfall_K": float(hrep["state_mean_shortfall_K"][0])}
            # the nominal heater state must reach the labelled temperature under the element limit
            pt["admissible"] = bool(pt["valid_fraction"] >= ADMIT and pt["in_window_fraction"] >= ADMIT
                                    and pt["nominal_shortfall_K"] <= 1.0)
            points.append(pt)
            print(f"eta {scen['eta']:.1f} S {scen['S_eff_m3_s']:.0f} feed<={scen['feed_limit_sccm']:.0f} {name:4s} {t0} C {rate:4.2f} um/h: "
                  f"valid {100 * pt['valid_fraction']:3.0f} %, window {100 * pt['in_window_fraction']:3.0f} %, nominal "
                  f"{pt['nominal_pct']:.2f} %, worst {pt['worst_pct'] if pt['worst_pct'] is None else round(pt['worst_pct'], 2)} %, "
                  f"capped {100 * pt['heater_capped_fraction']:.0f} %{' (admissible)' if pt['admissible'] else ''}", flush=True)
    fronts = []
    for scen in SCENARIOS:
        adm = [p for p in points if all(p[k] == v for k, v in scen.items()) and p.get("admissible")]
        front = [adm[i] for i in pareto(adm)]
        front.sort(key=lambda p: (p["rate_um_h"], p["T_C"]))
        pick = balanced(front)
        fronts.append({"scenario": scen, "admissible_points": len(adm), "front": front, "balanced": pick})
        print(f"\nscenario {scen}: {len(adm)} admissible points, front of {len(front)}", flush=True)
        for p in front:
            print(f"  {p['layout']:4s} {p['T_C']} C {p['rate_um_h']:4.2f} um/h: worst {p['worst_pct']:.2f} %, nominal {p['nominal_pct']:.2f} %"
                  + ("  <- balanced" if p is pick else "") + ("  (decomposition extrapolated)" if p["extrapolated_decomposition"] else ""))
    manifest = build_manifest(
        "operating_optimum", label="representative_chamber", validation_status="not_validated",
        inputs={"record": str(RECORD.relative_to(ROOT)), "record_run_id": rec["run_id"], "layouts": LAYOUTS, "T_C": T_C,
                "rates_um_h": RATES_UM_H, "scenarios": SCENARIOS, "element_limit": LIMIT, "admit": ADMIT, "kn_valid": lc.KN_VALID,
                "rate_tolerance_rel": lc.RATE_TOL, "pointing_ensemble_deg": 0.8, "decomposition_valid_from_C": DECOMPOSITION_VALID_C},
        outputs={"points": points, "fronts": fronts, "rho_m": rho},
        sources=[Path(__file__), ROOT / "scripts/layout_comparison.py", ROOT / "scripts/heater_zones.py",
                 ROOT / "src/mbe_twin/growth.py", ROOT / "src/mbe_twin/heater.py", ROOT / "data/parameters/gan_growth.json", RECORD],
        warnings=["Representative chamber; no model in the chain is validated on the proposed machine",
                  "Crystal quality, morphology and impurities are not modelled: the temperature objective is bounded only by the growth window",
                  "Decomposition fitted to 720-805 C; lower temperatures are extrapolated",
                  "Heater perturbations one at a time; Ga steered from an ideal wafer-mean reading",
                  "The balanced pick weights the three objectives equally after range normalization; other weights give other front points"])
    print(f"Wrote {write_manifest(manifest, Path(args.out) / 'manifest.json')}")


if __name__ == "__main__":
    main()
