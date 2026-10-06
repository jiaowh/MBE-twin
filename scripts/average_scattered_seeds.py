"""Average independent-seed runs of scripts/scattered_tables.py or scripts/scattered_plume_tables.py into one record.

The factor tables of a single 8e6-atom run carry 0.1-0.3 points of statistical half-range noise per entry,
comparable to the shape differences the uniformity studies resolve. Runs with the same settings and
different seeds are independent, so their factors (each a weighted quadratic fit in r^2 to equal-sized
batch means) are averaged with equal weights; the noise falls as 1/sqrt(runs). The parts must agree in
everything but the seed (layouts, aims, grid, radii, particle counts, code; for the plume tables also the
coverage). Plume parts may cover different pumping speeds (e.g. extra seeds run with --speeds 4 only): each
speed is averaged over the parts that have it, and the record gives the count per speed. The record keeps the format its generator writes, so realizable_controller.py
--n-scatter reads it unchanged, and adds per entry the seed-to-seed standard deviation of the factor
(the largest over radii) and each part's run summary.

--resample SEED draws the parts with replacement (as many draws as parts; for the plume tables per pumping
speed, among the parts that have it) for a bootstrap of the averaged table: rerunning the controller on such
resampled averages gives the uncertainty of a result computed from the averaged table, which the seed-to-seed
spread of single-table results divided by sqrt(runs) does not (the controller takes a maximum over states).

Usage: python scripts/average_scattered_seeds.py --parts results/scattered_tables_B-L_95mm results/scattered_tables_B-L_95mm_rep
                                                 --out results/scattered_tables_B-L_95mm_avg
"""

import argparse
import json
from pathlib import Path

import numpy as np

from mbe_twin.manifest import build_manifest, write_manifest

ROOT = Path(__file__).resolve().parents[1]


def _mean(entries):
    """Mean and largest seed-to-seed standard deviation of a list of equal-shaped factor arrays (None stays None)."""
    if any(e is None for e in entries):
        if not all(e is None for e in entries):
            raise SystemExit("average_scattered_seeds: parts differ in coverage")
        return None, None
    a = np.array(entries, dtype=float)
    return a.mean(0), float(a.std(0, ddof=1).max())


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--parts", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--resample", type=int, default=None, help="bootstrap: draw the parts with replacement (RNG seed)")
    args = ap.parse_args()
    rng = None if args.resample is None else np.random.default_rng(args.resample)
    draws = {}
    if len(args.parts) < 2:
        raise SystemExit("average_scattered_seeds: need at least two parts")
    parts = [json.loads((ROOT / p / "manifest.json").read_text(encoding="utf-8")) for p in args.parts]
    ref = parts[0]
    plume = "speeds_m3_s" in ref["inputs"]

    def draw(items, key):
        """The items themselves, or a bootstrap draw of them (indices recorded under `key`)."""
        if rng is None:
            return items
        idx = rng.integers(0, len(items), len(items))
        draws[key] = [int(i) for i in idx]
        return [items[i] for i in idx]
    seeds = [m["inputs"]["seed"] for m in parts]
    if len(set(seeds)) != len(seeds):
        raise SystemExit(f"average_scattered_seeds: repeated seeds {seeds}")
    for p, m in zip(args.parts, parts):
        a = {k: v for k, v in m["inputs"].items() if k not in ("seed", "extends", "speeds_m3_s")}
        b = {k: v for k, v in ref["inputs"].items() if k not in ("seed", "extends", "speeds_m3_s")}
        if a != b:
            raise SystemExit(f"average_scattered_seeds: {p} differs from {args.parts[0]} in "
                             f"{sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))}")
        if m["source_sha256"] != ref["source_sha256"]:
            raise SystemExit(f"average_scattered_seeds: {p} ran different code from {args.parts[0]}")
    spread, counts = {}, {}
    if plume:
        speeds = sorted({s for m in parts for s in m["inputs"]["speeds_m3_s"]})
        factors, diag = {}, {}
        for name in ref["inputs"]["layouts"]:
            factors[name], spread[name], counts[name], diag[name] = {}, {}, {}, {}
            for s in (f"{x:g}" for x in speeds):
                have = [m for m in parts if s in m["outputs"]["factors"][name]]
                if len(have) < 2:
                    raise SystemExit(f"average_scattered_seeds: speed {s} in fewer than two parts")
                have = draw(have, f"{name} {s}")
                v = have[0]["outputs"]["factors"][name][s]
                if any(m["outputs"]["factors"][name][s]["covered"] != v["covered"] for m in have):
                    raise SystemExit("average_scattered_seeds: parts differ in coverage")
                mean_sd = [_mean([m["outputs"]["factors"][name][s]["factors"][i] for m in have]) for i in range(len(v["covered"]))]
                factors[name][s] = {"factors": [x for x, _ in mean_sd], "covered": v["covered"]}
                spread[name][s] = [sd for _, sd in mean_sd]
                counts[name][s] = len(have)
                diag[name][s] = [[m["outputs"]["diagnostics"][name][s][i] for m in have] for i in range(len(v["covered"]))]
    else:
        factors = {"N": {}, "Ga": {}}
        parts_in = draw(parts, "parts")
        for sp in ("N", "Ga"):
            for key, val in ref["outputs"]["factors"][sp].items():
                if sp == "N":
                    factors["N"][key], spread.setdefault("N", {})[key] = {}, {}
                    for var in val:
                        tabs = [m["outputs"]["factors"]["N"][key][var] for m in parts_in]
                        ms = [_mean([t[i] for t in tabs]) for i in range(len(tabs[0]))]
                        factors["N"][key][var] = np.array([x for x, _ in ms])
                        spread["N"][key][var] = [sd for _, sd in ms]
                else:
                    tabs = [m["outputs"]["factors"]["Ga"][key] for m in parts_in]
                    factors["Ga"][key] = np.mean(np.array(tabs, dtype=float), 0)
        diag = {"parts": [m["outputs"]["diagnostics"] for m in parts]}
    summary = [{k: m[k] for k in ("run_id", "created_utc", "git_commit", "source_sha256", "inputs_sha256")} | {"seed": m["inputs"]["seed"], "part": p}
               for p, m in zip(args.parts, parts)]
    inputs = {k: v for k, v in ref["inputs"].items() if k not in ("seed", "extends")} | {"seeds": seeds, "parts": summary}
    if plume:
        inputs |= {"speeds_m3_s": speeds, "parts_per_speed": counts}
    if rng is not None:
        inputs |= {"resample": {"seed": args.resample, "draws": draws}}
    manifest = build_manifest(
        "scattered_plume_tables" if plume else "scattered_tables", label=ref.get("label", "representative_chamber"),
        validation_status="not_validated", inputs=inputs,
        outputs={"rho_m": np.asarray(ref["outputs"]["rho_m"]), "p_grid_Pa": ref["outputs"]["p_grid_Pa"], "factors": factors,
                 "diagnostics": diag, "seed_spread_max_sd": spread},
        sources=[Path(__file__)] + [ROOT / k for k in ref["source_sha256"]],
        warnings=ref["warnings"] + [f"Equal-weight mean of {len(parts)} independent-seed runs (inputs.parts)"
                                    + (", drawn with replacement (bootstrap, inputs.resample)" if rng is not None else "")
                                    + ("; the Ga factors use token samples" if not plume else "")],
        disabled_physics=ref["disabled_physics"])
    print(f"Wrote {write_manifest(manifest, Path(args.out) / 'manifest.json')}")


if __name__ == "__main__":
    main()
