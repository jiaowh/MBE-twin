"""Summarize the Ga centre-flux-hold runs (data/runs/sparta_ga/ga_dsmchold/).

For each state of cases/sparta_ga/ga_dsmchold.json: the latest completed correction (NAME,
NAME_it2, ...), its melt temperature, centre and wafer-mean delivered/target, and the 200 mm
range/mean with bootstrap scatter, next to the precursor run at the free-molecular temperature
schedule (the --correct-from record in ga_batch or ga_angle). A state counts as centre-flux-held
only if |delivered/target - 1| <= 1.5 %. Then, per diameter, the melt-temperature rise from the
40 mm to the 120 mm fill needed to hold the centre flux at 46 deg and at the angle optima.

Usage: python scripts/summarize_flux_hold.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "data/runs/sparta_ga"
JOBS = ROOT / "cases/sparta_ga/ga_dsmchold.json"
TOL = 0.015
C = 273.15


def outputs(path):
    return json.loads(path.read_text(encoding="utf-8"))["outputs"]


def latest(name):
    runs = [RECORDS / "ga_dsmchold" / f"{name}.json"]
    k = 2
    while (RECORDS / "ga_dsmchold" / f"{name}_it{k}.json").exists():
        runs.append(RECORDS / "ga_dsmchold" / f"{name}_it{k}.json")
        k += 1
    done = [r for r in runs if r.exists()]
    return (outputs(done[-1]), len(done)) if done else (None, 0)


def main():
    jobs = json.loads(JOBS.read_text(encoding="utf-8"))["jobs"]
    rows = {}
    print(f"{'state':30s} it   T (C)   centre   wafer-mean  range/mean %        | precursor: T (C) centre  range/mean %")
    for job in jobs:
        a = job["args"]
        pre = outputs(RECORDS / (a[a.index("--correct-from") + 1].replace("results/", "") + ".json"))
        o, n = latest(job["name"])
        pm = pre["metrics_dsmc"]["range_over_mean_pct"]
        pe = pre["metrics_dsmc_stderr"]["bootstrap"]["range_over_mean_pct"]
        line = f"{job['name']:30s} "
        if o is None:
            line += " -   (no completed run)                              "
        else:
            c = o["centre_flux_over_target"]["dsmc"]
            w = o.get("wafer_mean_flux_over_target", {}).get("dsmc", float("nan"))
            held = abs(c - 1.0) <= TOL
            m = o["metrics_dsmc"]["range_over_mean_pct"]
            e = o["metrics_dsmc_stderr"]["bootstrap"]["range_over_mean_pct"]
            rows[job["name"]] = {"T_C": o["config"]["T_K"] - C, "held": held, "rom": m}
            line += (f"{n:2d}  {o['config']['T_K'] - C:7.1f}  {c:6.3f}{'' if held else '*'}  {w:9.3f}   "
                     f"{m:5.2f} +/- {e:4.2f}     ")
        line += f"| {pre['config']['T_K'] - C:7.1f}  {pre['centre_flux_over_target']['dsmc']:6.3f}  {pm:5.2f} +/- {pe:4.2f}"
        print(line)
    print("* outside +/-1.5 %: not centre-flux-held")
    print("\nmelt-temperature rise to hold the centre Ga flux, 40 -> 120 mm fill")
    for d in ("d8", "d5.68"):
        for label, a40, a120 in (("46 deg", f"fill040_{d}_dsmchold", f"fill120_{d}_dsmchold"),
                                 ("optima 48 -> 58 deg", f"fill040_{d}_48deg_dsmchold", f"fill120_{d}_58deg_dsmchold")):
            r40, r120 = rows.get(a40), rows.get(a120)
            if r40 and r120 and r40["held"] and r120["held"]:
                print(f"  {d:6s} {label:20s}: {r40['T_C']:.1f} -> {r120['T_C']:.1f} C (+{r120['T_C'] - r40['T_C']:.1f} K)")
            else:
                print(f"  {d:6s} {label:20s}: not available (states missing or not held)")


if __name__ == "__main__":
    main()
