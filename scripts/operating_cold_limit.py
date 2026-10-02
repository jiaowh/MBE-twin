"""Coldest growth temperature that keeps the growth window at a given rate, with combined heater errors.

scripts/operating_optimum.py finds that, at a given rate, the coldest admissible temperature is
also the most uniform: the three goals (uniform, fast, cold) conflict only through the
Ga-rich growth window, which narrows relative to the flux as the wafer cools or the rate rises.
Its heater states are perturbed one at a time, which is optimistic. This study re-checks the
cold limit with the combined heater errors of scripts/heater_robustness.py (emissivity x contact
x worst-zone power error, 27 states) under the 1473 K element limit, with two controllers:
- mean: one reading holds the wafer mean;
- centre pyrometer with a bias of -2 / 0 / +2 K, the heater re-solved holding that reading.
Ga is steered from the controller's reading (temperature-corrected protocol), each state with
its own feed, pressure and attenuation, over the +/-0.8 deg pointing ensemble, the Ga fills and
diameters, the three droplet laws and the 2 mm lip.

For each supply scenario, layout and rate, the coldest temperature (10 K steps) at which at least
ADMIT of the states are valid and in the window is reported for each controller, with the
worst-case thickness there.

Usage: python scripts/operating_cold_limit.py [--out results/operating_cold_limit]
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

from mbe_twin.growth import load_parameters  # noqa: E402
from mbe_twin.manifest import build_manifest, write_manifest  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


oo = _load("operating_optimum")
hr = _load("heater_robustness")
lc = oo.lc
T_C = tuple(range(690, 770, 10))
SCENARIOS = [{"eta": 1.0, "S_eff_m3_s": 2.0, "feed_limit_sccm": 10.0},
             {"eta": 0.3, "S_eff_m3_s": 4.0, "feed_limit_sccm": 35.0}]
RATES_UM_H = (0.5, 1.0, 1.25, 1.5)
LIMIT_NAME = "1473 K element"
ADMIT = 0.95
CONTROLLERS = {"mean": ("mean",), "centre pyrometer +/-2 K": ("pyrometer -2 K", "pyrometer +0 K", "pyrometer +2 K")}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="results/operating_cold_limit")
    args = ap.parse_args()
    rec = json.loads(oo.RECORD.read_text(encoding="utf-8"))
    env = rec["inputs"]["envelope"]
    rho = np.asarray(rec["outputs"]["rho_m"])
    params = load_parameters()
    laws = env["operating_point"]["droplet_onset_law"]["value"]
    k_atoms = rec["inputs"]["atoms_per_m2_s_per_nm_min"]
    t_gas = env["vacuum"]["gas_temperature_K"]["value"]
    lip2 = lc.LIP_H.index(0.002)
    inputs = {}
    for name in oo.LAYOUTS:
        inp = oo.load_inputs(rec, env, name, rho)
        inp = {**inp, "n_vac": inp["n_vac"][:, [lip2]], "g_vac": inp["g_vac"][:, [lip2]]}
        inputs[name] = inp
    states_at = {}
    for t0 in T_C:
        states_at[t0] = [s for s in hr.combined_states(t0 + lc.C, rho) if s["limit"] == LIMIT_NAME]
        print(f"combined heater states at {t0} C done", flush=True)
    rows = []
    for scen, name, rate in itertools.product(SCENARIOS, oo.LAYOUTS, RATES_UM_H):
        inp = inputs[name]
        target = 1000.0 * rate / 60.0
        per_t = []
        for t0 in T_C:
            states = states_at[t0]
            nom = next(s for s in states if s["controller"] == "mean" and all(s[k] == v for k, v in hr.NOMINAL.items()))
            dec_nom = float(lc.area_mean(params.decomposition(nom["t_map"]), rho))

            def delivered(p):
                return float(lc.area_mean(inp["map0"] * lc.att_at(inp["att_n"], p) * inp["lip_n"][lip2], rho))
            op = lc.operating_point(delivered, dec_nom, target, scen["eta"], scen["S_eff_m3_s"], scen["feed_limit_sccm"],
                                    t_gas, k_atoms)
            entry = {"T_C": t0, "reachable": bool(op["target_reached"]), "nominal_shortfall_K": float(t0 + lc.C - nom["wafer_mean_K"])}
            if op["target_reached"]:
                feed_cap = op["feed_sccm"] if op.get("rate_peaks_below_feed_limit") else scen["feed_limit_sccm"]
                for cname, groups in CONTROLLERS.items():
                    sub = [s for s in states if s["controller"] in groups]
                    t_maps = np.array([s["t_map"] for s in sub])
                    reading = np.array([s["reading_K"] for s in sub])
                    res, _ = oo.evaluate_point(inp, t_maps, reading, params, laws, rho, target, k_atoms, scen, feed_cap, t_gas)
                    th = np.stack([res[l]["thickness"] for l in laws], -1)
                    mg = np.stack([res[l]["margin"] for l in laws], -1)
                    va = np.stack([res[l]["valid"] for l in laws], -1)
                    entry[cname] = {"valid_fraction": float(va.mean()), "in_window_fraction": float((mg >= 0).mean()),
                                    "worst_pct": float(th[va].max()) if va.any() else None,
                                    "admissible": bool(va.mean() >= ADMIT and (mg >= 0).mean() >= ADMIT
                                                       and entry["nominal_shortfall_K"] <= 1.0)}
            per_t.append(entry)
        row = {**scen, "layout": name, "rate_um_h": rate, "temperatures": per_t}
        for cname in CONTROLLERS:
            ok = [e for e in per_t if e["reachable"] and e[cname]["admissible"]]
            row[f"coldest_{cname}"] = ({"T_C": ok[0]["T_C"], "worst_pct": ok[0][cname]["worst_pct"],
                                        "in_window_fraction": ok[0][cname]["in_window_fraction"]} if ok else None)
        rows.append(row)
        cm, cp = row["coldest_mean"], row["coldest_centre pyrometer +/-2 K"]
        print(f"eta {scen['eta']:.1f} S {scen['S_eff_m3_s']:.0f} feed<={scen['feed_limit_sccm']:.0f} {name:4s} {rate:4.2f} um/h: coldest "
              f"(mean controller) {cm['T_C'] if cm else 'none'} C" + (f" worst {cm['worst_pct']:.2f} %" if cm else "")
              + f"; (centre pyrometer) {cp['T_C'] if cp else 'none'} C" + (f" worst {cp['worst_pct']:.2f} %" if cp else "")
              + "  | window by T (pyrometer): " + " ".join(
                  f"{e['T_C']}:{100 * e['centre pyrometer +/-2 K']['in_window_fraction']:.0f}" if e["reachable"] else f"{e['T_C']}:-"
                  for e in per_t), flush=True)
    manifest = build_manifest(
        "operating_cold_limit", label="representative_chamber", validation_status="not_validated",
        inputs={"record": str(oo.RECORD.relative_to(ROOT)), "record_run_id": rec["run_id"], "layouts": oo.LAYOUTS, "T_C": T_C,
                "scenarios": SCENARIOS, "rates_um_h": RATES_UM_H, "element_limit": LIMIT_NAME, "admit": ADMIT,
                "controllers": CONTROLLERS, "lip_m": 0.002, "pointing_ensemble_deg": 0.8},
        outputs={"rows": rows},
        sources=[Path(__file__), ROOT / "scripts/operating_optimum.py", ROOT / "scripts/heater_robustness.py",
                 ROOT / "scripts/layout_comparison.py", ROOT / "scripts/heater_zones.py", ROOT / "src/mbe_twin/growth.py",
                 ROOT / "src/mbe_twin/heater.py", ROOT / "data/parameters/gan_growth.json", oo.RECORD],
        warnings=["Representative chamber; no model in the chain is validated on the proposed machine",
                  "Crystal quality, morphology and impurities are not modelled: this is the growth-window limit only",
                  "Decomposition fitted to 720-805 C; lower temperatures are extrapolations (decomposition is below 1 % of the rate there)",
                  "Lip 2 mm only; one Ga steering rule (the window middle at the reading)"])
    print(f"Wrote {write_manifest(manifest, Path(args.out) / 'manifest.json')}")


if __name__ == "__main__":
    main()
