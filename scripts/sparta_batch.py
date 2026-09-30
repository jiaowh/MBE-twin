"""Run a list of SPARTA jobs (sparta_r07.py or sparta_ga.py invocations) a few at a time.

The job file is JSON: {"description": ..., "script": "scripts/sparta_r07.py",
"jobs": [{"name": ..., "args": [...]}, ...]}. Each job runs `python <script> <args> --out
results/<batch>/<name> --record <batch>/<name>`, so its compact summary lands in the
script's versioned record directory (data/runs/<script>/<batch>/).
A job counts as complete when its run directory holds summary.json; complete jobs are
skipped. A directory without it (a failed or interrupted run) is reported as incomplete and
left untouched, unless --retry-incomplete is given, which moves it aside to
<name>.failed-<timestamp> and reruns the job. The batch exits with status 1 if any job failed or
is incomplete, so unattended runs cannot look successful.
Serial SPARTA uses one core per job; the laptop's WSL has four.

Usage: python scripts/sparta_batch.py cases/sparta_r07/uq_batch.json [--workers 4]
                                      [--retry-incomplete]
"""

import argparse
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(job, batch, log_dir, script, retry_incomplete=False, results=ROOT / "results"):
    out = Path(results) / batch / job["name"]
    if (out / "summary.json").exists():
        return job["name"], "skipped (complete)", 0.0
    if out.exists():
        if not retry_incomplete:
            return job["name"], "INCOMPLETE (no summary.json; rerun with --retry-incomplete)", 0.0
        out.rename(out.with_name(f"{out.name}.failed-{time.strftime('%Y%m%d-%H%M%S')}"))
    cmd = [sys.executable, str(ROOT / script), *job["args"], "--out", str(out),
           "--record", f"{batch}/{job['name']}"]
    t0 = time.time()
    with open(log_dir / f"{job['name']}.log", "w", encoding="utf-8") as log:
        r = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT,
                           env={**os.environ, "PYTHONPATH": str(ROOT / "src")})
    return job["name"], "ok" if r.returncode == 0 else f"FAILED ({r.returncode})", time.time() - t0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("jobs")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--results", default=str(ROOT / "results"), help="parent of the batch's run directories")
    ap.add_argument("--retry-incomplete", action="store_true",
                    help="move incomplete run directories aside and rerun those jobs")
    args = ap.parse_args()
    spec = json.loads(Path(args.jobs).read_text(encoding="utf-8"))
    batch = Path(args.jobs).stem
    script = spec.get("script", "scripts/sparta_r07.py")
    log_dir = Path(args.results) / batch / "_logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    bad = []
    with ThreadPoolExecutor(args.workers) as pool:
        for name, status, secs in pool.map(lambda j: run(j, batch, log_dir, script, args.retry_incomplete,
                                                             args.results),
                                           spec["jobs"]):
            print(f"{time.strftime('%H:%M:%S')} {name}: {status} ({secs / 60:.1f} min)", flush=True)
            if not (status == "ok" or status.startswith("skipped")):
                bad.append(name)
    if bad:
        print(f"{len(bad)} job(s) failed or incomplete: {', '.join(bad)}", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
