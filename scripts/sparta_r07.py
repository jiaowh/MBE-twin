"""DSMC (SPARTA) of R07's conical Bi crucible: collisionless check and rate series.

Geometry (R07): conical crucible, aperture D = 16.5 mm, 2.6 deg taper, melt L = 4 D below
the orifice; measurement plane at 115 mm. Melt: fix emit/surf at the saturation density
n = p / kT (Hertz-Knudsen, cosine law), returning particles absorbed (vanish). Bore wall:
diffuse at the source temperature. Orifice plane outside the lip: absorbing (as in the
free-molecular model). Particles are sampled in a slab above the orifice and propagated
ballistically to the plane (mbe_twin.sparta.propagate_slab).

Cases (T, p from R07; 666 C pressure interpolated as in scripts/crucible_knudsen.py):
  fm      0.35 A/s state with collisions off: code-to-code check against crucible.py
  0.35    573 C, 0.08 Pa           3.5   666 C, 1.05 Pa           11    723 C, 4 Pa
Collisions: hard-sphere Bi (VSS omega 0.5, alpha 1) with diameter diameter_m.

Bi2 option (x_dimer > 0; physics-data note 2026-09-30, section 1): the vapour at total pressure
p is a Bi + Bi2 mixture with dimer mole fraction x_dimer; each species evaporates by
Hertz-Knudsen at its partial pressure (SPARTA emit/surf with mixture fractions). Bi2 has
twice the mass, diameter dimer_diameter_scale * diameter_m (default 2^(1/3), equal-volume
scaling; an assumption), 2 rotational degrees of freedom with relaxation number 5 (assumed)
and no vibration (SPARTA default "vibrate none"; Bi2 constants are not sourced). Species are
dumped separately; the arriving atom flux counts each Bi2 as two atoms. With x_dimer = 0 the
SPARTA input is identical to the monatomic benchmark.

Runs are defined by named benchmark configurations (BENCHMARKS), optionally modified with
--set key=value. Every run gets a fresh directory holding config.json, written before
SPARTA starts; post-processing (also with --reuse) reads only that file, and checks that the
dump files are exactly those the configuration produces. Uncertainty: batch means over
--blocks time blocks of the sampling run, plus a first-half/second-half comparison and the
drift of the particle count as steady-state checks.

Usage: python scripts/sparta_r07.py BENCHMARK [--set diameter_m=7e-10 ...] [--out DIR]
                                    [--record NAME]
       python scripts/sparta_r07.py --reuse DIR [--record NAME]
--record copies the compact summary to data/runs/sparta_r07/NAME.json (versioned).
"""

import argparse
import json
from pathlib import Path

import numpy as np

from mbe_twin.crucible import Crucible, next_event_flux, simulate
from mbe_twin.manifest import build_manifest, source_sha256, write_manifest
from mbe_twin.sparta import (accumulate_snapshots, batch_means, crucible_surface, expected_dump_steps,
                             load_run_config, log_stats, prepare_run_dir, propagate_slab, run_case, sparta_commit, write_surf)
from mbe_twin.units import K_B, N_A

ROOT = Path(__file__).resolve().parents[1]
RECORD_DIR = ROOT / "data/runs/sparta_r07"
D = 0.0165
TAPER = np.radians(2.6)
DEPTH = 4 * D
PLANE = 0.115
BI_MASS = 208.9804e-3 / N_A
BI_ATOMS_PER_M3 = 9.78e3 / 208.9804e-3 * N_A  # solid Bi 9.78 g/cm^3 (CRC), for A/s
CASES = {  # name: (T_K, p_Pa, R07 centre rate A/s, fig4 curve or None, collisions)
    "fm": (846.15, 0.08, 0.35, None, False),
    "0.35": (846.15, 0.08, 0.35, "0.35 A/s", True),
    "3.5": (939.15, 1.05, 3.5, "3.5 A/s", True),
    "11": (996.15, 4.0, 11.0, "11.0 A/s", True),
}
X_EDGES_MM = np.linspace(0.0, 48.0, 25)
DEFAULTS = {
    "diameter_m": 8.0e-10,  # calibrated on 3.5 A/s (ref/notes/REFERENCE_CHAMBER.md)
    "cell_m": 1.0e-3,       # fine cell in and near the bore; keep <= lambda_sat / 2
    "coarse": 3,            # coarse cell = coarse * cell elsewhere (1: uniform grid)
    "particles": 1.0e6,     # target simulated particles in the bore at saturation density
    "dt_factor": 0.3,       # timestep = dt_factor * cell / mean speed
    "steps_eq": 8000,
    "steps_sample": 48000,
    "dump_every": 20,
    "slab_D": [5.0, 5.5],   # sampling slab above the orifice, in units of D (>= 4.5 D)
    "seed": 12345,
    "x_dimer": 0.0,               # Bi2 mole fraction of the vapour at the stated total pressure
    "dimer_diameter_scale": 2 ** (1 / 3),
}
# Configurations behind the results in REFERENCE_CHAMBER.md. The 11 A/s case needs finer
# cells (lambda_sat = 1.2 mm) and, with them, more particles and a longer equilibration.
# Statistics: with 2e5 particles and 16000 sampling steps the per-bin profile error is about
# 0.02, as large as the model-data misfit (uq_batch, 2026-09-29); these settings bring it
# to about 0.005.
BENCHMARKS = {
    "r07_fm": {"case": "fm"},
    "r07_0.35": {"case": "0.35"},
    "r07_3.5": {"case": "3.5"},
    "r07_11": {"case": "11", "cell_m": 0.6e-3, "particles": 1.2e6, "steps_eq": 14000,
               "steps_sample": 72000},
}
SOURCES = [Path(__file__), ROOT / "src/mbe_twin/sparta.py", ROOT / "src/mbe_twin/crucible.py"]


def resolve_config(benchmark, overrides):
    cfg = {"benchmark": benchmark, **DEFAULTS, **BENCHMARKS[benchmark]}
    for item in overrides:
        key, _, value = item.partition("=")
        if key not in DEFAULTS:
            raise SystemExit(f"--set: unknown key {key!r}; allowed: {sorted(DEFAULTS)}")
        cfg[key] = json.loads(value) if key == "slab_D" else type(DEFAULTS[key])(float(value))
    cfg["overrides"] = list(overrides)
    t, p, _, _, collide = CASES[cfg["case"]]
    n_sat = p / (K_B * t)
    v_mean = np.sqrt(8 * K_B * t / (np.pi * BI_MASS))
    bore_volume = np.pi * DEPTH * (D / 2) ** 2
    cfg.update({
        "T_K": t, "p_Pa": p, "collisions": collide,
        "fnum": n_sat * bore_volume / cfg["particles"],
        "dt_s": cfg["dt_factor"] * cfg["cell_m"] / v_mean,
        "slab_m": [cfg["slab_D"][0] * D, cfg["slab_D"][1] * D],
        "lambda_sat_m": (K_B * t / (np.sqrt(2.0) * np.pi * cfg["diameter_m"] ** 2 * p)
                         if collide else None),
    })
    return cfg


def box_geometry(slab, cell, coarse):
    """Box extents on the coarse (level-1) grid: wide enough that rays from the orifice to
    the 48 mm edge of the 115 mm plane (about 23 deg) stay inside up to the slab top."""
    h = coarse * cell
    half_width = h * np.ceil(max(2.5 * D, slab[1] * np.tan(np.radians(25.0)) + D) / h)
    zlo = -DEPTH - 0.5 * h  # melt plane away from cell faces
    nz = int(np.ceil((slab[1] + 0.5 * D - zlo) / h))
    return half_width, zlo, zlo + nz * h, int(round(2 * half_width / h)), nz


def write_inputs(work, cfg):
    """Two-level grid: level-1 cells of coarse * cell, refined coarse^3 inside a cylinder
    around the bore up to one D above the orifice, where the gas is dense."""
    t, p, cell, coarse, slab = cfg["T_K"], cfg["p_Pa"], cfg["cell_m"], cfg["coarse"], cfg["slab_m"]
    half_width, zlo, top, nx, nz = box_geometry(slab, cell, coarse)
    write_surf(crucible_surface(D / 2, DEPTH, half_width, taper_half_angle=TAPER, n_segments=64),
               work / "surf.crucible", comment="R07 conical crucible, L/D = 4 (SI units)")
    x2 = cfg.get("x_dimer", 0.0)
    species = f"Bi 208.9804 {BI_MASS:.6e} 0 0 0 0 0 1.0 0.0\n"
    vss = f"Bi {cfg['diameter_m']:.6e} 0.5 {t:.2f} 1.0\n"
    if x2 > 0:
        species += f"Bi2 417.9608 {2 * BI_MASS:.6e} 2 5.0 0 0 0 1.0 0.0\n"
        vss += f"Bi2 {cfg['dimer_diameter_scale'] * cfg['diameter_m']:.6e} 0.5 {t:.2f} 1.0\n"
    (work / "bi.species").write_text(species, encoding="ascii", newline="\n")
    (work / "bi.vss").write_text(vss, encoding="ascii", newline="\n")
    grid = f"create_grid {nx} {nx} {nz}"
    if coarse > 1:
        grid += f" levels 2 region 2 fine {coarse} {coarse} {coarse} inside any"
    lines = [
        f"seed {cfg['seed']}", "dimension 3", "units si", "global gridcut 0.0",
        "boundary o o o",
        f"create_box {-half_width} {half_width} {-half_width} {half_width} {zlo} {top}",
        f"region fine cylinder z 0 0 {D} {zlo} {D}",
        grid,
        f"global fnum {cfg['fnum']:.6e}",
        "species bi.species Bi" + (" Bi2" if x2 > 0 else ""),
        f"mixture melt Bi{' Bi2' if x2 > 0 else ''} nrho {p / (K_B * t):.6e} temp {t} vstream 0 0 0",
        *([f"mixture melt Bi frac {1 - x2:.6f}", f"mixture melt Bi2 frac {x2:.6f}",
           "mixture mono Bi", "mixture dimer Bi2"] if x2 > 0 else []),
        "read_surf surf.crucible type",
        "group melt surf type 1", "group wall surf type 2", "group lip surf type 3",
        "surf_collide absorb vanish",
        f"surf_collide hot diffuse {t} 1.0",
        "surf_modify melt collide absorb", "surf_modify lip collide absorb",
        "surf_modify wall collide hot",
        "collide vss melt bi.vss" if cfg["collisions"] else "collide none",
        "fix evap emit/surf melt melt",
        f"timestep {cfg['dt_s']:.6e}",
        "stats 1000", "stats_style step cpu np nattempt ncoll nscoll",
        f"run {cfg['steps_eq']}",
        f"region slab block INF INF INF INF {slab[0]} {slab[1]}",
        f"dump slab particle {'mono' if x2 > 0 else 'melt'} {cfg['dump_every']} dump.slab.* id x y z vx vy vz",
        "dump_modify slab region slab",
        *([f"dump slabd particle dimer {cfg['dump_every']} dump.dimer.* id x y z vx vy vz",
           "dump_modify slabd region slab"] if x2 > 0 else []),
        f"run {cfg['steps_sample']}",
    ]
    (work / "in.case").write_text("\n".join(lines) + "\n", encoding="ascii", newline="\n")


def measured(curve):
    data = json.loads((ROOT / "data/benchmarks/r07_gericke1991.json").read_text(encoding="utf-8"))
    c = data["panels"]["fig4"]["curves"][curve]
    x, y = np.array(c["x_mm"]), np.array(c["y"])
    o = np.argsort(x)
    x, y = x[o], y[o]
    return x, y / np.interp(0.0, x, y)


X_MID = 0.5 * (X_EDGES_MM[1:] + X_EDGES_MM[:-1])
AREA = np.diff(X_EDGES_MM ** 2)
CORE = X_EDGES_MM[1:] <= 6.0  # inside R07's +/-15 mm plateau; single bins are noisy
KEEP = X_MID <= 45.0


def centre_of(f):
    return float(np.sum(f[CORE] * AREA[CORE]) / np.sum(AREA[CORE]))


def profile_metrics(flux, ref):
    """Centre rate (A/s), normalized profile and, when a reference is given, RMS and bias."""
    prof = flux / centre_of(flux)
    out = {"rate": centre_of(flux) / BI_ATOMS_PER_M3 * 1e10, "profile": prof}
    if ref is not None:
        d = prof[KEEP] - ref[KEEP]
        out["rms"], out["bias"] = float(np.sqrt(np.mean(d ** 2))), float(np.mean(d))
    return out


def postprocess(work, cfg, n_blocks):
    steps = expected_dump_steps(cfg["steps_eq"], cfg["steps_sample"], cfg["dump_every"])
    n_snap = len(steps)
    slab = tuple(cfg["slab_m"])
    edges = X_EDGES_MM / 1000
    # Stream the snapshots (memory of one snapshot). Snapshot weights v_z / thickness are
    # rates (1/s); each sample is fnum real atoms.
    acc = accumulate_snapshots(work, steps, lambda p, v: propagate_slab(p, v, slab, PLANE, edges)[0], n_blocks)
    dimer_share = None
    if cfg.get("x_dimer", 0.0) > 0:
        # atom flux: each Bi2 sample carries two atoms; same snapshots, so blocks and halves align
        acc2 = accumulate_snapshots(work, steps, lambda p, v: propagate_slab(p, v, slab, PLANE, edges)[0],
                                    n_blocks, prefix="dump.dimer.")
        mono_centre = centre_of(acc["total"])
        for key in ("total", "blocks", "halves"):
            acc[key] = acc[key] + 2.0 * acc2[key]
        acc["samples"] += acc2["samples"]
        dimer_share = 1.0 - mono_centre / centre_of(acc["total"])
    flux = acc["total"] / n_snap * cfg["fnum"]
    curve = CASES[cfg["case"]][3]
    ref = None
    if curve:
        xm, ym = measured(curve)
        # measured profile averaged over +/- x, at the bin centres
        ref = 0.5 * (np.interp(X_MID, xm, ym) + np.interp(-X_MID, xm, ym))
    whole = profile_metrics(flux, ref)

    # Batch means over contiguous time blocks (the boundary snapshot goes to the last block).
    blocks = [profile_metrics(acc["blocks"][b] / acc["n_blocks"][b] * cfg["fnum"], ref) for b in range(n_blocks)]
    unc = {}
    for key in ("rate", "rms", "bias"):
        if key in blocks[0]:
            mean, se = batch_means([bl[key] for bl in blocks])
            unc[key] = {"block_mean": float(mean), "stderr": float(se)}
    prof_se = batch_means([bl["profile"] for bl in blocks])[1]
    first, second = (profile_metrics(acc["halves"][h] / acc["n_halves"][h] * cfg["fnum"], ref) for h in (0, 1))
    stats = log_stats((work / "log.sparta").read_text(encoding="utf-8", errors="replace"))
    sample = [r for r in stats if r["Step"] >= cfg["steps_eq"]]
    npart = np.array([r["Np"] for r in sample])
    return flux, ref, whole, {
        "n_blocks": n_blocks, "snapshots": n_snap, "samples": int(acc["samples"]),
        "block": unc, "profile_stderr": prof_se,
        "halves": {"rate": [first["rate"], second["rate"]],
                   "profile_max_abs_diff": float(np.max(np.abs(first["profile"] - second["profile"])[KEEP])),
                   **({"rms": [first["rms"], second["rms"]]} if ref is not None else {})},
        "np_sampling": {"first": float(npart[0]), "last": float(npart[-1]),
                        "rel_range": float(np.ptp(npart) / npart.mean())},
        "dimer_atom_share_centre": dimer_share,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("benchmark", nargs="?", choices=list(BENCHMARKS))
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    ap.add_argument("--out", default=None)
    ap.add_argument("--reuse", default=None, metavar="DIR",
                    help="post-process an existing run from its recorded config.json")
    ap.add_argument("--blocks", type=int, default=8, help="time blocks for batch-means errors")
    ap.add_argument("--record", default=None, metavar="NAME")
    args = ap.parse_args()

    if args.reuse:
        if args.benchmark or args.set or args.out:
            ap.error("--reuse takes its configuration from the run directory only")
        work = Path(args.reuse)
        cfg = load_run_config(work)
    else:
        if not args.benchmark:
            ap.error("give a benchmark name or --reuse DIR")
        cfg = resolve_config(args.benchmark, args.set)
        suffix = "".join("_" + s.replace("=", "") for s in args.set)
        work = Path(args.out or ROOT / "results/sparta_r07" / f"{args.benchmark}{suffix}")
        cfg["sparta_commit"] = sparta_commit()
        # the code that writes the inputs; the manifest hashes the post-processing code
        cfg["source_sha256_at_start"] = source_sha256(SOURCES)
        prepare_run_dir(work, cfg)  # refuses a non-empty directory
        write_inputs(work, cfg)
        run_case(work)

    flux, ref, whole, unc = postprocess(work, cfg, args.blocks)
    lam = cfg["lambda_sat_m"]
    if lam:
        print(f"  lambda at saturation {lam * 1e3:.2f} mm = {lam / cfg['cell_m']:.1f} fine cells")

    # Free-molecular reference (crucible.py) at the same state.
    t, p = cfg["T_K"], cfg["p_Pa"]
    ev = simulate(Crucible(D / 2, DEPTH, taper_half_angle=TAPER), 150_000, rng=21)
    melt_area = np.pi * (D / 2 - DEPTH * np.tan(TAPER)) ** 2
    x2 = cfg.get("x_dimer", 0.0)
    # atoms leaving the melt: Hertz-Knudsen per species; a dimer carries 2 atoms at 1/sqrt(2) the speed
    emitted = (melt_area * p / (K_B * t) * np.sqrt(8 * K_B * t / (np.pi * BI_MASS)) / 4
               * (1 - x2 + np.sqrt(2.0) * x2))
    pts = np.stack([X_MID / 1000, np.zeros_like(X_MID), np.full_like(X_MID, PLANE)], 1)
    fm = next_event_flux(ev, pts, (0.0, 0.0, -1.0)) * emitted
    fm_m = profile_metrics(fm, ref)

    rate_r07 = CASES[cfg["case"]][2]
    b = unc["block"]
    print(f"{work.name}: {unc['snapshots']} snapshots, {unc['samples']} slab samples, "
          f"{unc['n_blocks']} blocks")
    print(f"  centre rate: SPARTA {whole['rate']:.3g} +/- {b['rate']['stderr']:.2g} A/s, "
          f"free-molecular {fm_m['rate']:.3g} A/s, R07 {rate_r07} A/s")
    print("  x mm   " + " ".join(f"{v:6.1f}" for v in X_MID[::3]))
    print("  SPARTA " + " ".join(f"{v:6.3f}" for v in whole["profile"][::3]))
    print("  +/-    " + " ".join(f"{v:6.3f}" for v in unc["profile_stderr"][::3]))
    print("  FM     " + " ".join(f"{v:6.3f}" for v in fm_m["profile"][::3]))
    d_fm = whole["profile"][KEEP] - fm_m["profile"][KEEP]
    summary = {
        "config": cfg, "x_mm": X_MID, "sparta_flux": flux, "free_molecular_flux": fm,
        "profile": whole["profile"], "profile_stderr": unc["profile_stderr"],
        "centre_rate_A_s": {"sparta": whole["rate"], "free_molecular": fm_m["rate"], "r07": rate_r07},
        "rms_vs_free_molecular": float(np.sqrt(np.mean(d_fm ** 2))),
        "uncertainty": {k: v for k, v in unc.items() if k != "profile_stderr"},
    }
    if ref is not None:
        print("  R07    " + " ".join(f"{v:6.3f}" for v in ref[::3]))
        print(f"  rms vs R07: SPARTA {whole['rms']:.4f} +/- {b['rms']['stderr']:.4f} "
              f"(bias {whole['bias']:+.4f} +/- {b['bias']['stderr']:.4f}), "
              f"free-molecular {fm_m['rms']:.3f}")
        summary.update({"r07_profile": ref, "rms_vs_r07": whole["rms"], "bias_vs_r07": whole["bias"],
                        "rms_vs_r07_free_molecular": fm_m["rms"],
                        "rate_error_vs_r07": whole["rate"] / rate_r07 - 1.0})
    h = unc["halves"]
    if unc["dimer_atom_share_centre"] is not None:
        print(f"  atoms arriving as Bi2 (centre): {100 * unc['dimer_atom_share_centre']:.1f} %")
    print(f"  steady state: halves rate {h['rate'][0]:.3g} / {h['rate'][1]:.3g}, profile max diff "
          f"{h['profile_max_abs_diff']:.3f}; Np range {100 * unc['np_sampling']['rel_range']:.2f} %")

    manifest = build_manifest(
        f"sparta_r07_{work.name}", label="representative_chamber", validation_status="not_validated",
        inputs=cfg, outputs=summary, sources=SOURCES,
        solver={"name": "SPARTA", "build": "serial (WSL)", "commit": cfg.get("sparta_commit")},
        warnings=[("Bi + Bi2 mixture, x_dimer = {:.3f}; Bi2 diameter, rotational relaxation and no vibration "
                   "are assumptions".format(x2)) if x2 > 0 else
                  "Bi treated as monatomic hard spheres (Bi2 in the vapour neglected)",
                  "Collisions above the sampling slab neglected (ballistic propagation)",
                  "Sensor size neglected; profiles averaged over +/- x and azimuth",
                  "Uncertainties are statistical (batch means) only; discretization is "
                  "assessed by separate runs"],
        disabled_physics=(["Bi2 vibration", "Bi2 dissociation/recombination"] if x2 > 0 else ["Bi2 dimers"])
        + ["surface diffusion/condensation on the lip"])
    print(f"Wrote {write_manifest(manifest, work / 'summary.json')}")
    if args.record:
        print(f"Recorded {write_manifest(manifest, RECORD_DIR / f'{args.record}.json')}")


if __name__ == "__main__":
    main()
