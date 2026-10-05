"""Monte Carlo noise of the scattered-atom factor tables in the uniformity worst case (summary of controller runs).

A factor table from one 8e6-atom run of scattered_tables.py / scattered_plume_tables.py carries 0.1-0.4
points of random radial shape per pressure. realizable_controller.py takes the worst case over states,
so that noise both scatters and, on average, raises the worst case. This script collects controller runs
(realizable_controller.py --n-tables ... --n-scatter ...) made with single-seed tables, with seed-averaged
tables (average_scattered_seeds.py) and with --scatter-flat, and tabulates per layout and temperature the
worst case and joint fraction of one controller: each run's value, and for the single-seed runs the mean,
standard deviation, minimum and maximum. Every run must share the settings other than the factor tables;
runs of kind aim (an aim scan with one set of averaged factors, --scatter-from-aim) may also differ in their
--n-tables, and are listed per run with the aim of their tables.
The run manifests stay in results/ (git ignores it), so each run's dependency hashes are kept under
inputs.constituents, where scripts/record_provenance.py checks them run by run.

Usage: python scripts/summarize_scatter_noise.py --runs single:results/ctl_s1 ... avg:results/ctl_avg10 flat:results/ctl_flat [aim:DIR ...]
                                                 [--controller "rate monitor + BFM"] --out DIR
"""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

from mbe_twin.manifest import build_manifest, write_manifest

ROOT = Path(__file__).resolve().parents[1]
SAME = ("record", "scattered", "scenarios", "rate_um_h", "T_C", "element_limit", "pyrometer_biases_K", "rate_monitor_errors",
        "bfm_errors", "rate_band", "admit", "heater_design_limit_K", "pointing_residual_deg", "heater_control", "n_tables",
        "aim_maps_sha256", "scatter_from_aim_mm")
DEPENDENCIES = ("aim_maps_sha256", "ga_records_sha256", "scattered_tables_sha256", "scattered_plume_tables_sha256",
                "n_scatter_sha256")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--runs", nargs="+", required=True, help="KIND:DIR with KIND single, avg, flat or aim")
    ap.add_argument("--controller", default="rate monitor + BFM")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    runs = []
    for spec in args.runs:
        kind, d = spec.split(":", 1)
        if kind not in ("single", "avg", "flat", "aim"):
            raise SystemExit(f"summarize_scatter_noise: unknown kind {kind}")
        m = json.loads((ROOT / d / "manifest.json").read_text(encoding="utf-8"))
        runs.append((kind, d, m))
    ref = runs[0][2]["inputs"]
    for kind, d, m in runs:
        diff = [k for k in SAME if m["inputs"].get(k) != ref.get(k)
                and not (kind == "aim" and k in ("n_tables", "aim_maps_sha256", "scatter_from_aim_mm"))]
        if diff:
            raise SystemExit(f"summarize_scatter_noise: {d} differs in {diff}")
        if not m["inputs"].get("n_scatter_sha256"):
            raise SystemExit(f"summarize_scatter_noise: {d} was not run with --n-scatter")
    table = {}
    for kind, d, m in runs:
        for r in m["outputs"]["rows"]:
            c = r["controllers"][args.controller]
            key = f"{r['layout']} {r['T_C']} C"
            table.setdefault(key, []).append({"kind": kind, "run": d, "n_tables": m["inputs"].get("n_tables"),
                                              "worst_pct": c["worst_pct"],
                                              "joint_fraction": c["joint_fraction"],
                                              "n_scatter": list(m["inputs"]["n_scatter_sha256"]),
                                              "scatter_flat": m["inputs"].get("scatter_flat", False)})
    summary = {}
    for key, rows in table.items():
        single = np.array([x["worst_pct"] for x in rows if x["kind"] == "single" and x["worst_pct"] is not None])
        summary[key] = {"single_n": int(len(single)),
                        "single_mean": float(single.mean()) if len(single) else None,
                        "single_sd": float(single.std(ddof=1)) if len(single) > 1 else None,
                        "single_min": float(single.min()) if len(single) else None,
                        "single_max": float(single.max()) if len(single) else None,
                        "avg": [x["worst_pct"] for x in rows if x["kind"] == "avg"],
                        "flat": [x["worst_pct"] for x in rows if x["kind"] == "flat"],
                        "aim": {str(x["n_tables"]): [x["worst_pct"], x["joint_fraction"]] for x in rows if x["kind"] == "aim"}}
        s = summary[key]
        def f3(v):
            return "n/a" if v is None else f"{v:.3f}"
        print(f"{key}: single {s['single_n']} runs mean {f3(s['single_mean'])} sd {f3(s['single_sd'])} "
              f"[{f3(s['single_min'])}, {f3(s['single_max'])}]; avg {s['avg']}; flat {s['flat']}; aim {s['aim']}")
    manifest = build_manifest(
        "scatter_noise", label="representative_chamber", validation_status="not_validated",
        inputs={"controller": args.controller,
                "runs": [{"kind": k, "dir": d, "run_id": m["run_id"], "scatter_flat": m["inputs"].get("scatter_flat", False),
                          "manifest_sha256": hashlib.sha256((ROOT / d / "manifest.json").read_bytes()).hexdigest()}
                         for k, d, m in runs],
                "constituents": {d: {"source_sha256": m["source_sha256"],
                                     **{k: m["inputs"][k] for k in DEPENDENCIES if m["inputs"].get(k)}} for _, d, m in runs},
                "settings": {k: ref.get(k) for k in SAME}},
        outputs={"per_run": table, "summary": summary},
        sources=[Path(__file__), ROOT / "scripts/realizable_controller.py", ROOT / "scripts/average_scattered_seeds.py"],
        warnings=["Spread over independent table seeds of one controller; heater, pointing and instrument states are fixed",
                  "The flat variant assumes the scattered arrival has no radial shape; it brackets, not replaces, the average"])
    print(f"Wrote {write_manifest(manifest, Path(args.out) / 'manifest.json')}")


if __name__ == "__main__":
    main()
