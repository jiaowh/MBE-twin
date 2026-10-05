"""Iterate the Ga melt temperature until DSMC delivers the target wafer-centre Ga flux.

What is held: the Ga arrival rate at the wafer centre (inside r = 10 mm), expressed as the Ga
flux of the target GaN rate at Ga/N = 1. It is not a growth rate (that needs the nitrogen
supply and incorporation/desorption) and not the wafer-average flux; each run records both
centre and wafer-mean delivered/target.

`sparta_ga.py --mode dsmc-hold --correct-from DIR` makes one correction: it scales the
previous run's saturation pressure by target / delivered centre flux. This driver runs the
first correction (cases/sparta_ga/ga_dsmchold.json, results/ga_dsmchold/NAME), then repeats the
step per state until delivered/target is within --tolerance or --max-iterations corrections
have been made. Further corrections are NAME_it2, NAME_it3, ... in the same results and record
directories, run through scripts/sparta_batch.py (memory-guarded). The tolerance, 1.5 %, is
about three times the statistical error of the centre flux (inner 10 mm, 6e5 particles).

Exit status (review 3): 0 only if every state in the job file has a completed run within
tolerance. A missing state, a failed batch or a state still outside tolerance after
--max-iterations gives 1, so an unattended run cannot look successful. Only states that meet
the tolerance may be described as "centre-flux-held".

Usage: python scripts/ga_flux_hold.py            # status table only (exit 1 until all held)
       python scripts/ga_flux_hold.py --iterate [--workers 2 --min-free-gb 3 --min-free-wsl-gb 2.5
                                                          --max-wsl-load 3.2]
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIRST = ROOT / "cases/sparta_ga/ga_dsmchold.json"
NEXT = ROOT / "cases/sparta_ga/iterations/ga_dsmchold.json"  # same stem: same result directories
RESULTS = ROOT / "results/ga_dsmchold"


def ratio(run_dir):
    s = run_dir / "summary.json"
    if not s.exists():
        return None
    return json.loads(s.read_text(encoding="utf-8"))["outputs"]["centre_flux_over_target"]["dsmc"]


def chain(name):
    """Completed and pending iteration directories of one state, in order."""
    dirs = [RESULTS / name]
    k = 2
    while (RESULTS / f"{name}_it{k}").exists():
        dirs.append(RESULTS / f"{name}_it{k}")
        k += 1
    return dirs


def status(jobs, tol):
    rows = []
    for job in jobs:
        dirs = chain(job["name"])
        last = [d for d in dirs if ratio(d) is not None]
        r = ratio(last[-1]) if last else None
        rows.append({"job": job, "iterations": len(last), "last": last[-1] if last else None, "ratio": r,
                     "converged": r is not None and abs(r - 1.0) <= tol})
    return rows


def print_status(rows):
    print(f"{'state':32s} iter  delivered/target  converged")
    for r in rows:
        print(f"{r['job']['name']:32s} {r['iterations']:4d}  "
              f"{'-' if r['ratio'] is None else format(r['ratio'], '.3f'):>16s}  {r['converged']}", flush=True)


def run_batch(spec_path, args):
    cmd = [sys.executable, str(ROOT / "scripts/sparta_batch.py"), str(spec_path), "--retry-incomplete",
           "--workers", str(args.workers), "--min-free-gb", str(args.min_free_gb),
           "--min-free-wsl-gb", str(args.min_free_wsl_gb), "--max-wsl-load", str(args.max_wsl_load)]
    if args.no_start_after:
        cmd += ["--no-start-after", args.no_start_after]
    return subprocess.run(cmd).returncode


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--tolerance", type=float, default=0.015)
    ap.add_argument("--max-iterations", type=int, default=3)
    ap.add_argument("--iterate", action="store_true")
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--min-free-gb", type=float, default=3.0)
    ap.add_argument("--min-free-wsl-gb", type=float, default=2.5)
    ap.add_argument("--max-wsl-load", type=float, default=3.2, help="WSL has 4 cores shared with other work")
    ap.add_argument("--no-start-after", default=None, metavar="YYYY-MM-DDTHH:MM")
    args = ap.parse_args()
    jobs = json.loads(FIRST.read_text(encoding="utf-8"))["jobs"]
    if args.iterate and run_batch(FIRST, args) != 0:
        print("first-correction batch reported failures; stopping", flush=True)
        print_status(status(jobs, args.tolerance))
        sys.exit(1)
    while True:
        rows = status(jobs, args.tolerance)
        print_status(rows)
        todo = [r for r in rows if r["last"] is not None and not r["converged"]
                and r["iterations"] < args.max_iterations]
        if not args.iterate or not todo:
            break
        nxt = []
        for r in todo:
            a = list(r["job"]["args"])
            a[a.index("--correct-from") + 1] = str(r["last"].relative_to(ROOT)).replace("\\", "/")
            nxt.append({"name": f"{r['job']['name']}_it{r['iterations'] + 1}", "args": a})
        NEXT.parent.mkdir(parents=True, exist_ok=True)
        NEXT.write_text(json.dumps({"description": "Generated by scripts/ga_flux_hold.py: next temperature "
                                    "correction for states outside tolerance.", "script": "scripts/sparta_ga.py",
                                    "jobs": nxt}, indent=2) + "\n", encoding="utf-8", newline="\n")
        if run_batch(NEXT, args) != 0:
            print("batch reported failures; stopping", flush=True)
            sys.exit(1)
    rows = status(jobs, args.tolerance)
    missing = [r["job"]["name"] for r in rows if r["last"] is None]
    outside = [r["job"]["name"] for r in rows if r["last"] is not None and not r["converged"]]
    if missing:
        print(f"no completed run: {', '.join(missing)}", flush=True)
    if outside:
        print(f"outside tolerance after {args.max_iterations} iterations: {', '.join(outside)}", flush=True)
    if missing or outside:
        sys.exit(1)
    print(f"all {len(rows)} states centre-flux-held within {100 * args.tolerance:g} %", flush=True)


if __name__ == "__main__":
    main()
