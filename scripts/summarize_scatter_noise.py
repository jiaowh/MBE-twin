"""Monte Carlo noise of the scattered-atom factor tables in the uniformity worst case (summary of controller runs).

A factor table from one 8e6-atom run of scattered_tables.py / scattered_plume_tables.py carries 0.1-0.4
points of random radial shape per pressure. realizable_controller.py takes the worst case over states,
so that noise both scatters and, on average, raises the worst case. This script collects controller runs
(realizable_controller.py --n-tables ... --n-scatter ...) made with single-seed tables, with seed-averaged
tables (average_scattered_seeds.py) and with --scatter-flat, and tabulates per layout and temperature the
worst case and joint fraction of one controller: each run's value, and for the single-seed runs the mean,
standard deviation, minimum and maximum. Only the layouts whose factors a run replaced
(inputs.n_scatter_layouts) are collected; a run's other layouts would reuse unchanged tables and are not trials.

The single-seed spread describes one table, not the averaged one. Runs of kind boot (the controller on
bootstrap-resampled averages, average_scattered_seeds.py --resample) give the table-noise uncertainty of the
averaged-table result directly: the standard deviation and 5-95 % range of the worst case, the spread of the
joint fraction, and per controller the share of resamples that pass the admission gate. Their mean minus the
averaged-table value indicates the upward bias that residual table noise gives a maximum over states.
--compare OTHER pairs this summary's boot runs with those of another summary (the other layout, resampled
independently) and gives the bootstrap distribution of the layout difference.

Every run must share the settings other than the factor tables; runs of kind aim (an aim scan with one set of
averaged factors, --scatter-from-aim) may also differ in their --n-tables, and are listed per run with the aim
of their tables. The run manifests stay in results/ (git ignores it), so each run's dependency hashes are kept
under inputs.constituents, where scripts/record_provenance.py checks them run by run.

Usage: python scripts/summarize_scatter_noise.py --runs single:results/ctl_s1 ... avg:results/ctl_avg10 flat:results/ctl_flat
                                                 [aim:DIR ...] [boot:DIR ...] [--controller "rate monitor + BFM"]
                                                 [--compare OTHER_SUMMARY_DIR] --out DIR
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
        "aim_maps_sha256", "scatter_from_aim_mm", "n_scatter_layouts")
DEPENDENCIES = ("aim_maps_sha256", "ga_records_sha256", "scattered_tables_sha256", "scattered_plume_tables_sha256",
                "n_scatter_sha256")
KINDS = ("single", "avg", "flat", "aim", "boot")


def boot_stats(boot, avg):
    """Spread of the worst case and joint fraction over bootstrap-resampled averaged tables."""
    w = np.array([x["worst_pct"] for x in boot if x["worst_pct"] is not None])
    j = np.array([x["joint_fraction"] for x in boot])
    return {"n": len(boot), "n_with_worst": int(len(w)),
            "worst_mean": float(w.mean()), "worst_sd": float(w.std(ddof=1)),
            "worst_p05": float(np.percentile(w, 5)), "worst_p95": float(np.percentile(w, 95)),
            "bias_vs_avg": float(w.mean() - avg[0]) if len(avg) == 1 and avg[0] is not None else None,
            "joint_mean": float(j.mean()), "joint_sd": float(j.std(ddof=1)), "joint_min": float(j.min()),
            "joint_max": float(j.max()),
            "joint_min_by_controller": {c: float(min(x["joint_by_controller"][c] for x in boot))
                                        for c in boot[0]["joint_by_controller"]},
            "pass_fraction": {c: float(np.mean([x["admissible"][c] for x in boot])) for c in boot[0]["admissible"]}}


def paired_difference(table, other):
    """Bootstrap distribution of (this layout - other layout) worst case per temperature, pairing the i-th boot run
    of each (independent resamples of independent tables, so any fixed pairing is valid)."""
    def by_t(tab):
        out = {}
        for key, rows in tab.items():
            name, t = key.split(" ", 1)
            out[t] = (name, [x["worst_pct"] for x in rows if x["kind"] == "boot"],
                      [x["worst_pct"] for x in rows if x["kind"] == "avg"])
        return out
    mine, theirs = by_t(table), by_t(other["outputs"]["per_run"])
    res = {"by_T": {}}
    for t in sorted(set(mine) & set(theirs)):
        (a, ba, va), (b, bb, vb) = mine[t], theirs[t]
        n = min(len(ba), len(bb))
        if n < 2 or None in ba[:n] + bb[:n]:
            raise SystemExit(f"summarize_scatter_noise: --compare needs boot runs with a worst case on both sides at {t}")
        d = np.array(ba[:n]) - np.array(bb[:n])
        res["this"], res["that"] = a, b
        res["by_T"][t] = {"n": n, "avg_diff": float(va[0] - vb[0]) if len(va) == 1 and len(vb) == 1 else None,
                          "mean": float(d.mean()), "sd": float(d.std(ddof=1)), "p05": float(np.percentile(d, 5)),
                          "p95": float(np.percentile(d, 95)), "share_positive": float(np.mean(d > 0))}
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--runs", nargs="+", required=True, help="KIND:DIR with KIND single, avg, flat, aim or boot")
    ap.add_argument("--controller", default="rate monitor + BFM")
    ap.add_argument("--compare", default=None, help="summary DIR whose boot runs are paired with these (layout difference)")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    runs = []
    for spec in args.runs:
        kind, d = spec.split(":", 1)
        if kind not in KINDS:
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
        if not m["inputs"].get("n_scatter_layouts"):
            raise SystemExit(f"summarize_scatter_noise: {d} does not record which layouts --n-scatter replaced")
    table = {}
    for kind, d, m in runs:
        for r in m["outputs"]["rows"]:
            if r["layout"] not in m["inputs"]["n_scatter_layouts"]:
                continue
            c = r["controllers"][args.controller]
            key = f"{r['layout']} {r['T_C']} C"
            table.setdefault(key, []).append({"kind": kind, "run": d, "n_tables": m["inputs"].get("n_tables"),
                                              "worst_pct": c["worst_pct"],
                                              "joint_fraction": c["joint_fraction"],
                                              "admissible": {k: v["admissible"] for k, v in r["controllers"].items()},
                                              "joint_by_controller": {k: v["joint_fraction"] for k, v in r["controllers"].items()},
                                              "n_scatter": list(m["inputs"]["n_scatter_sha256"]),
                                              "scatter_flat": m["inputs"].get("scatter_flat", False)})

    def f3(v):
        return "n/a" if v is None else f"{v:.3f}"

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
        boot = [x for x in rows if x["kind"] == "boot"]
        if boot:
            summary[key]["boot"] = boot_stats(boot, summary[key]["avg"])
        s = summary[key]
        print(f"{key}: single {s['single_n']} runs mean {f3(s['single_mean'])} sd {f3(s['single_sd'])} "
              f"[{f3(s['single_min'])}, {f3(s['single_max'])}]; avg {s['avg']}; flat {s['flat']}; aim {s['aim']}")
        if boot:
            b = s["boot"]
            print(f"    boot {b['n']} resamples: worst sd {f3(b['worst_sd'])} [{f3(b['worst_p05'])}, {f3(b['worst_p95'])}], "
                  f"mean - avg {f3(b['bias_vs_avg'])}; joint {b['joint_mean']:.4f} [{b['joint_min']:.4f}, {b['joint_max']:.4f}]; "
                  f"pass {b['pass_fraction']}")
    compare = None
    if args.compare:
        compare = paired_difference(table, json.loads((ROOT / args.compare / "manifest.json").read_text(encoding="utf-8")))
        compare["other"] = args.compare
        for t, v in compare["by_T"].items():
            print(f"difference {compare['this']} - {compare['that']} at {t}: avg {f3(v['avg_diff'])}; boot sd {f3(v['sd'])} "
                  f"[{f3(v['p05'])}, {f3(v['p95'])}], share > 0 {v['share_positive']:.2f}")
    manifest = build_manifest(
        "scatter_noise", label="representative_chamber", validation_status="not_validated",
        inputs={"controller": args.controller, "compare": args.compare,
                "runs": [{"kind": k, "dir": d, "run_id": m["run_id"], "scatter_flat": m["inputs"].get("scatter_flat", False),
                          "manifest_sha256": hashlib.sha256((ROOT / d / "manifest.json").read_bytes()).hexdigest()}
                         for k, d, m in runs],
                "constituents": {d: {"source_sha256": m["source_sha256"],
                                     **{k: m["inputs"][k] for k in DEPENDENCIES if m["inputs"].get(k)}} for _, d, m in runs},
                "settings": {k: ref.get(k) for k in SAME}},
        outputs={"per_run": table, "summary": summary, **({"paired_difference": compare} if compare else {})},
        sources=[Path(__file__), ROOT / "scripts/realizable_controller.py", ROOT / "scripts/average_scattered_seeds.py"],
        warnings=["Spread over independent table seeds of one controller; heater, pointing and instrument states are fixed",
                  "The flat variant assumes the scattered arrival has no radial shape; it brackets, not replaces, the average",
                  "Only the layouts whose factors each run replaced are collected (inputs.n_scatter_layouts of each run)"]
                 + (["Bootstrap over the same seeds: it measures the table-noise uncertainty of the averaged result, not "
                     "model or physics uncertainty, and a 5-95 % range from a few dozen resamples is approximate"]
                    if any(k == "boot" for k, _, _ in runs) else []))
    print(f"Wrote {write_manifest(manifest, Path(args.out) / 'manifest.json')}")


if __name__ == "__main__":
    main()
