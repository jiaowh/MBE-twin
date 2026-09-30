"""Run Elmer FEM cases (ElmerGrid mesh generation + ElmerSolver) from Python.

Elmer is an external dependency, located through the ELMER_HOME environment variable (the
directory that contains bin/ElmerSolver) or the default development-laptop path. Pinned
build: rel26.1 Windows gui-nompi zip, banner "Version 9.0, compiled 2026-01-20", zip
SHA-256 bb7cfa105d2bb44e31ed8e45699dccdcaad13b31d48759415243b8f542071afb.
"""

import os
import shutil
import subprocess
from pathlib import Path

DEFAULT_HOME = Path(r"C:\Users\Jiaow\tools\ElmerFEM-26.1\ElmerFEM-gui-nompi-Windows-AMD64")


def elmer_home():
    home = Path(os.environ.get("ELMER_HOME", DEFAULT_HOME))
    solver = home / "bin" / ("ElmerSolver.exe" if os.name == "nt" else "ElmerSolver")
    return home if solver.exists() else None


def _exe(name):
    home = elmer_home()
    if home is None:
        raise FileNotFoundError("Elmer not found; set ELMER_HOME")
    return str(home / "bin" / (name + (".exe" if os.name == "nt" else "")))


def run_case(case_dir, work_dir, grd="mesh.grd", sif="case.sif", timeout=3600):
    """Copy `case_dir` to `work_dir`, mesh the .grd with ElmerGrid and run ElmerSolver.

    Returns the work directory. Raises CalledProcessError with the solver log on failure.
    """
    work = Path(work_dir)
    if work.exists():
        shutil.rmtree(work)
    shutil.copytree(case_dir, work)
    env = dict(os.environ)
    env["ELMER_HOME"] = str(elmer_home())
    env["PATH"] = str(Path(_exe("ElmerSolver")).parent) + os.pathsep + env.get("PATH", "")
    grid = subprocess.run([_exe("ElmerGrid"), "1", "2", grd, "-autoclean"], cwd=work, env=env,
                          capture_output=True, text=True, timeout=timeout)
    (work / "elmergrid.log").write_text(grid.stdout + grid.stderr, encoding="utf-8")
    grid.check_returncode()
    solve = subprocess.run([_exe("ElmerSolver"), sif], cwd=work, env=env, capture_output=True,
                           text=True, timeout=timeout)
    (work / "elmersolver.log").write_text(solve.stdout + solve.stderr, encoding="utf-8")
    if solve.returncode != 0 or "ALL DONE" not in solve.stdout:
        raise subprocess.CalledProcessError(solve.returncode, solve.args, solve.stdout, solve.stderr)
    return work


def read_saveline(work_dir, filename="line.dat"):
    """Columns of a SaveLine output as a dict, using the accompanying .names file."""
    work = Path(work_dir)
    data = __import__("numpy").loadtxt(work / filename, ndmin=2)
    names = []
    for line in (work / (filename + ".names")).read_text(encoding="utf-8").splitlines():
        parts = line.strip().split(":", 1)
        if len(parts) == 2 and parts[0].strip().isdigit():
            names.append(parts[1].strip())
    return {name: data[:, i] for i, name in enumerate(names) if i < data.shape[1]}
