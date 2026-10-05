"""Collect the uniformity-lever runs of 2026-10-05 into one study record (data/runs/studies/uniformity_levers.json).

Each lever is a scripts/realizable_controller.py run (rate monitor + BFM controller): commissioning re-aim
(--pointing-residual), aim offset at the operating point (--aim-maps / --aim-mm), heater design limit and
multi-spot heater control (--heater-control multispot). For every run listed in RUNS the record keeps its
settings, the per-layout joint fraction and worst-case thickness at each temperature, and the SHA-256 of
its manifest. The manifests stay in results/, which git ignores, so each run's own dependency hashes
(source_sha256, aim_maps_sha256, ga_records_sha256, scattered-table hashes) are kept per run under
inputs.constituents, where scripts/record_provenance.py checks them run by run.
Worst-case drivers (scripts/worst_case_drivers.py) are added for the dumps listed in DRIVERS.

Usage: python scripts/summarize_uniformity_levers.py
"""

import hashlib
import importlib.util
import json
from pathlib import Path

from mbe_twin.manifest import build_manifest, write_manifest

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / "results"
RUNS = (["reaim_check08"]
        + [f"reaim_d{d}_h{h}" for d in ("0.4", "0.2", "0.1") for h in ("1473", "1460", "1450")]
        + [f"aim_BL_a{a}_d{d}" for d in ("0.2", "0.8") for a in ("90", "92.5", "95", "97.5", "100", "105")]
        + [f"aim_Bp_a{a}_d{d}" for d in ("0.2", "0.8") for a in ("92.5", "97.5", "102.5")]
        + ["ms_h1460_d0.2", "ms_h1450_d0.2", "ms_h1425_d0.2", "ms_h1450_d0.8", "ms_h1460_d0.2_cold"])
DRIVERS = ["drivers_h1460/states_B-p_720C.npz", "drivers_cur/states_B-L_730C.npz",
           "drivers_d02_h1450/states_B-p_720C.npz", "drivers_d02_h1460/states_B-L_720C.npz",
           "ms_h1450_d0.2/states_B-p_720C.npz", "ms_h1460_d0.2/states_B-L_720C.npz"]
CONTROLLER = "rate monitor + BFM"
CONTROLLERS = ("rate monitor + BFM", "rate monitor + BFM + fill")
SETTINGS = ("heater_design_limit_K", "heater_control", "pointing_residual_deg", "aim_maps", "aim_mm",
            "rate_monitor_errors", "bfm_errors", "T_C", "rate_um_h", "scattered", "scenarios", "admit", "rate_band",
            "element_limit", "pyrometer_biases_K")
DEPENDENCIES = ("aim_maps_sha256", "ga_records_sha256", "scattered_tables_sha256", "scattered_plume_tables_sha256")


def main():
    runs, constituents = [], {}
    for name in RUNS:
        f = RES / name / "manifest.json"
        if not f.exists():
            print(f"missing {name}")
            continue
        m = json.loads(f.read_text(encoding="utf-8"))
        constituents[name] = {"source_sha256": m["source_sha256"],
                              **{k: m["inputs"][k] for k in DEPENDENCIES if m["inputs"].get(k)}}
        rows = [{"layout": r["layout"], "T_C": r["T_C"], "controller": c,
                 "joint_fraction": r["controllers"][c]["joint_fraction"], "worst_pct": r["controllers"][c]["worst_pct"],
                 "admissible": r["controllers"][c]["admissible"],
                 "bound_worst_pct": r["controllers"]["known maps (bound)"]["worst_pct"]}
                for r in m["outputs"]["rows"] if r.get("reachable") for c in CONTROLLERS if c in r["controllers"]]
        runs.append({"run": name, "manifest_sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
                     "settings": {k: m["inputs"].get(k) for k in SETTINGS}, "rows": rows})
    spec = importlib.util.spec_from_file_location("wcd", ROOT / "scripts/worst_case_drivers.py")
    wcd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wcd)
    drivers = [wcd.analyse(RES / d, CONTROLLER) for d in DRIVERS if (RES / d).exists()]
    best = {}
    for r in runs:
        for row in r["rows"]:
            key = f"{row['layout']} / {row['controller']}"
            if row["admissible"] and (key not in best or row["worst_pct"] < best[key]["worst_pct"]):
                best[key] = {**row, "run": r["run"], "settings": r["settings"]}
    man = build_manifest("uniformity_levers", label="representative_chamber", inputs={"runs": RUNS, "controllers": CONTROLLERS, "constituents": constituents},
                         outputs={"runs": runs, "drivers": drivers, "best_admissible": best},
                         sources=[Path(__file__), ROOT / "scripts/realizable_controller.py",
                                  ROOT / "scripts/worst_case_drivers.py", ROOT / "scripts/multispot_heater.py",
                                  ROOT / "scripts/nitrogen_aim_operating.py"],
                         warnings=["Each run's own source hashes are in its manifest in results/; the realizable "
                                   "controller's priors (instrument errors, exact commissioned maps) apply",
                                   "Aim maps reuse the current aim's attenuation tables and tilt responses"])
    write_manifest(man, ROOT / "data/runs/studies/uniformity_levers.json")
    for lay, b in best.items():
        print(f"best {lay}: {b['worst_pct']:.2f} % at {b['T_C']} C ({b['run']}, joint {100 * b['joint_fraction']:.1f} %)")


if __name__ == "__main__":
    main()
