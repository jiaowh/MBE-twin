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
Serial SPARTA uses one core per job; the laptop's WSL has four. Memory guard (best effort): jobs are admitted one at a time, only
when at least --min-free-gb of physical memory is available, and the next job waits until the
previous one has run --settle seconds so its start-up allocation shows in the free memory. Together with
streamed post-processing this keeps overnight batches from exhausting the 15 GB laptop, which
happened on 2026-09-30 when four post-processing jobs each loaded ~55 million samples.

Usage: python scripts/sparta_batch.py cases/sparta_r07/uq_batch.json [--workers 3] [--min-free-gb 3]
                                      [--retry-incomplete]
"""

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def available_gb():
    """Available physical memory in GB (Windows API, or /proc/meminfo elsewhere)."""
    if os.name == "nt":
        import ctypes

        class MemoryStatus(ctypes.Structure):
            _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                        ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                        ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                        ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                        ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

        m = MemoryStatus()
        m.dwLength = ctypes.sizeof(MemoryStatus)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
        return m.ullAvailPhys / 2 ** 30
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) / 2 ** 20
    return float("inf")


_START_LOCK = threading.Lock()


def launch_admitted(cmd, log, name, min_free_gb, settle_s):
    """Start one job under admission control and return its Popen.

    The lock is held while memory is checked, the job is launched and it runs for settle_s
    seconds, so the next job is admitted only after this one's start-up allocation (SPARTA
    creates its particles in the first tens of seconds) is visible in the free-memory figure.
    Best effort: a job's memory can still grow later, so the per-job footprint must stay small
    (post-processing streams snapshots) and the threshold leaves headroom.
    """
    with _START_LOCK:
        while available_gb() < min_free_gb:
            print(f"{time.strftime('%H:%M:%S')} {name}: waiting, {available_gb():.1f} GB free "
                  f"< {min_free_gb} GB", flush=True)
            time.sleep(30)
        proc = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT,
                                env={**os.environ, "PYTHONPATH": str(ROOT / "src")})
        deadline = time.time() + settle_s
        while time.time() < deadline and proc.poll() is None:
            time.sleep(1)
        return proc


def run(job, batch, log_dir, script, retry_incomplete=False, results=ROOT / "results", min_free_gb=0.0,
        settle_s=0.0):
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
        rc = launch_admitted(cmd, log, job["name"], min_free_gb, settle_s).wait()
    return job["name"], "ok" if rc == 0 else f"FAILED ({rc})", time.time() - t0


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("jobs")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--min-free-gb", type=float, default=3.0,
                    help="start a job only when this much physical memory is available")
    ap.add_argument("--settle", type=float, default=90.0,
                    help="seconds a newly started job runs before the next one may be admitted")
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
                                                             args.results, args.min_free_gb, args.settle),
                                           spec["jobs"]):
            print(f"{time.strftime('%H:%M:%S')} {name}: {status} ({secs / 60:.1f} min)", flush=True)
            if not (status == "ok" or status.startswith("skipped")):
                bad.append(name)
    if bad:
        print(f"{len(bad)} job(s) failed or incomplete: {', '.join(bad)}", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
