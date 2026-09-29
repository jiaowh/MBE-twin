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
Collisions: hard-sphere Bi (VSS omega 0.5, alpha 1) with diameter --diameter (m).

Usage: python scripts/sparta_r07.py CASE [--diameter 5.68e-10] [--cell 1.0e-3]
       [--steps-eq N] [--steps-sample N] [--slab 1.5 2.0]
"""

import argparse
import json
from pathlib import Path

import numpy as np

from mbe_twin.crucible import Crucible, next_event_flux, simulate
from mbe_twin.manifest import build_manifest, write_manifest
from mbe_twin.sparta import crucible_surface, propagate_slab, run_case, write_surf
from mbe_twin.units import K_B, N_A

ROOT = Path(__file__).resolve().parents[1]
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


def box_geometry(slab, cell, coarse):
    """Box extents on the coarse (level-1) grid: wide enough that rays from the orifice to
    the 48 mm edge of the 115 mm plane (about 23 deg) stay inside up to the slab top."""
    h = coarse * cell
    half_width = h * np.ceil(max(2.5 * D, slab[1] * np.tan(np.radians(25.0)) + D) / h)
    zlo = -DEPTH - 0.5 * h  # melt plane away from cell faces
    nz = int(np.ceil((slab[1] + 0.5 * D - zlo) / h))
    return half_width, zlo, zlo + nz * h, int(round(2 * half_width / h)), nz


def write_inputs(work, t, p, collide, diameter, cell, coarse, slab, fnum, dt,
                 steps_eq, steps_sample, dump_every, seed):
    """Two-level grid: level-1 cells of coarse * cell, refined coarse^3 inside a cylinder
    around the bore up to one D above the orifice, where the gas is dense."""
    work.mkdir(parents=True, exist_ok=True)
    half_width, zlo, top, nx, nz = box_geometry(slab, cell, coarse)
    write_surf(crucible_surface(D / 2, DEPTH, half_width, taper_half_angle=TAPER, n_segments=64),
               work / "surf.crucible", comment="R07 conical crucible, L/D = 4 (SI units)")
    (work / "bi.species").write_text(
        f"Bi 208.9804 {BI_MASS:.6e} 0 0 0 0 0 1.0 0.0\n", encoding="ascii", newline="\n")
    (work / "bi.vss").write_text(f"Bi {diameter:.6e} 0.5 {t:.2f} 1.0\n", encoding="ascii", newline="\n")
    grid = f"create_grid {nx} {nx} {nz}"
    if coarse > 1:
        grid += f" levels 2 region 2 fine {coarse} {coarse} {coarse} inside any"
    lines = [
        f"seed {seed}", "dimension 3", "units si", "global gridcut 0.0",
        "boundary o o o",
        f"create_box {-half_width} {half_width} {-half_width} {half_width} {zlo} {top}",
        f"region fine cylinder z 0 0 {D} {zlo} {D}",
        grid,
        f"global fnum {fnum:.6e}",
        "species bi.species Bi",
        f"mixture melt Bi nrho {p / (K_B * t):.6e} temp {t} vstream 0 0 0",
        "read_surf surf.crucible type",
        "group melt surf type 1", "group wall surf type 2", "group lip surf type 3",
        "surf_collide absorb vanish",
        f"surf_collide hot diffuse {t} 1.0",
        "surf_modify melt collide absorb", "surf_modify lip collide absorb",
        "surf_modify wall collide hot",
        "collide vss melt bi.vss" if collide else "collide none",
        "fix evap emit/surf melt melt",
        f"timestep {dt:.6e}",
        "stats 1000", "stats_style step cpu np nattempt ncoll nscoll",
        f"run {steps_eq}",
        f"region slab block INF INF INF INF {slab[0]} {slab[1]}",
        f"dump slab particle melt {dump_every} dump.slab.* id x y z vx vy vz",
        "dump_modify slab region slab",
        f"run {steps_sample}",
    ]
    (work / "in.case").write_text("\n".join(lines) + "\n", encoding="ascii", newline="\n")


def read_dumps(work):
    pos, vel, n = [], [], 0
    for f in sorted(work.glob("dump.slab.*")):
        text = f.read_text().splitlines()
        start = next(i for i, line in enumerate(text) if line.startswith("ITEM: ATOMS")) + 1
        if start < len(text):
            a = np.loadtxt(text[start:], ndmin=2)
            pos.append(a[:, 1:4])
            vel.append(a[:, 4:7])
        n += 1
    return np.concatenate(pos), np.concatenate(vel), n


def measured(curve):
    data = json.loads((ROOT / "data/benchmarks/r07_gericke1991.json").read_text(encoding="utf-8"))
    c = data["panels"]["fig4"]["curves"][curve]
    x, y = np.array(c["x_mm"]), np.array(c["y"])
    o = np.argsort(x)
    x, y = x[o], y[o]
    return x, y / np.interp(0.0, x, y)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("case", choices=list(CASES))
    ap.add_argument("--diameter", type=float, default=5.68e-10)
    ap.add_argument("--cell", type=float, default=1.0e-3, help="fine cell size in and near the bore (m)")
    ap.add_argument("--coarse", type=int, default=3, help="coarse cell = coarse * cell elsewhere (1: uniform)")
    ap.add_argument("--particles", type=float, default=2e5, help="target simulated particles in the bore")
    ap.add_argument("--steps-eq", type=int, default=6000)
    ap.add_argument("--steps-sample", type=int, default=6000)
    ap.add_argument("--dump-every", type=int, default=20)
    ap.add_argument("--slab", type=float, nargs=2, default=(1.5, 2.0), help="slab z range in units of D")
    ap.add_argument("--seed", type=int, default=12345)
    ap.add_argument("--out", default=None)
    ap.add_argument("--reuse", action="store_true", help="post-process an existing run")
    args = ap.parse_args()

    t, p, rate_r07, curve, collide = CASES[args.case]
    tag = args.case if not collide else f"{args.case}_d{args.diameter * 1e10:.2f}A"
    work = Path(args.out or ROOT / "results/sparta_r07" / tag)
    n_sat = p / (K_B * t)
    v_mean = np.sqrt(8 * K_B * t / (np.pi * BI_MASS))
    bore_volume = np.pi * DEPTH * (D / 2) ** 2
    fnum = n_sat * bore_volume / args.particles
    dt = 0.3 * args.cell / v_mean
    slab = (args.slab[0] * D, args.slab[1] * D)
    if not args.reuse:
        write_inputs(work, t, p, collide, args.diameter, args.cell, args.coarse, slab, fnum, dt,
                     args.steps_eq, args.steps_sample, args.dump_every, args.seed)
        run_case(work)
    pos, vel, n_snap = read_dumps(work)
    flux, _ = propagate_slab(pos, vel, slab, PLANE, X_EDGES_MM / 1000)
    # Snapshot weights v_z / thickness are rates (1/s); each sample is fnum real atoms.
    flux *= fnum / n_snap  # real atoms m^-2 s^-1
    x_mid = 0.5 * (X_EDGES_MM[1:] + X_EDGES_MM[:-1])
    area = np.diff(X_EDGES_MM ** 2)
    core = X_EDGES_MM[1:] <= 6.0  # inside R07's +/-15 mm plateau; single bins are noisy

    def centre_of(f):
        return float(np.sum(f[core] * area[core]) / np.sum(area[core]))

    rate = centre_of(flux) / BI_ATOMS_PER_M3 * 1e10  # A/s, unit sticking

    # Free-molecular reference (crucible.py) at the same state.
    ev = simulate(Crucible(D / 2, DEPTH, taper_half_angle=TAPER), 150_000, rng=21)
    melt_area = np.pi * (D / 2 - DEPTH * np.tan(TAPER)) ** 2
    emitted = melt_area * n_sat * v_mean / 4
    pts = np.stack([x_mid / 1000, np.zeros_like(x_mid), np.full_like(x_mid, PLANE)], 1)
    fm = next_event_flux(ev, pts, (0.0, 0.0, -1.0)) * emitted
    fm_rate = centre_of(fm) / BI_ATOMS_PER_M3 * 1e10

    # Smallest physical mean free path: the gas never exceeds the saturation density.
    lam_sat = K_B * t / (np.sqrt(2.0) * np.pi * args.diameter ** 2 * p) if collide else np.inf
    print(f"  lambda at saturation {lam_sat * 1e3:.2f} mm = {lam_sat / args.cell:.1f} fine cells")
    out = {"case": args.case, "lambda_sat_m": lam_sat, "lambda_sat_over_cell": lam_sat / args.cell, "T_K": t, "p_Pa": p, "collisions": collide, "diameter_m": args.diameter,
           "cell_m": args.cell, "fnum": fnum, "dt_s": dt, "snapshots": n_snap, "samples": len(pos),
           "slab_m": slab, "x_mm": x_mid.tolist(), "sparta_flux": flux.tolist(),
           "free_molecular_flux": fm.tolist(), "centre_rate_A_s": {"sparta": rate,
           "free_molecular": fm_rate, "r07": rate_r07}}
    print(f"{args.case}: {n_snap} snapshots, {len(pos)} slab samples")
    print("  SPARTA/FM absolute, by bin: " + " ".join(f"{v:.3f}" for v in (flux / fm)[::3]))
    print(f"  centre rate: SPARTA {rate:.3g} A/s, free-molecular {fm_rate:.3g} A/s, R07 {rate_r07} A/s")
    prof, prof_fm = flux / centre_of(flux), fm / centre_of(fm)
    out["absolute_ratio_sparta_over_fm"] = (flux / fm).tolist()
    print("  x mm   " + " ".join(f"{v:6.1f}" for v in x_mid[::3]))
    print("  SPARTA " + " ".join(f"{v:6.3f}" for v in prof[::3]))
    print("  FM     " + " ".join(f"{v:6.3f}" for v in prof_fm[::3]))
    keep = x_mid <= 45.0
    d_fm = prof[keep] - prof_fm[keep]
    out["rms_vs_free_molecular"] = float(np.sqrt(np.mean(d_fm ** 2)))
    print(f"  rms SPARTA vs free-molecular {out['rms_vs_free_molecular']:.3f}")
    if curve:
        xm, ym = measured(curve)
        # measured profile averaged over +/- x, at the bin centres
        y = 0.5 * (np.interp(x_mid, xm, ym) + np.interp(-x_mid, xm, ym))
        for name, pr in (("SPARTA", prof), ("free-molecular", prof_fm)):
            d = pr[keep] - y[keep]
            out[f"rms_vs_r07_{name}"] = float(np.sqrt(np.mean(d ** 2)))
            out[f"bias_vs_r07_{name}"] = float(np.mean(d))
        print("  R07    " + " ".join(f"{v:6.3f}" for v in y[::3]))
        print(f"  rms vs R07: SPARTA {out['rms_vs_r07_SPARTA']:.3f} (bias {out['bias_vs_r07_SPARTA']:+.3f}), "
              f"free-molecular {out['rms_vs_r07_free-molecular']:.3f}")
    manifest = build_manifest(
        f"sparta_r07_{tag}", label="representative_chamber", validation_status="not_validated",
        inputs={k: out[k] for k in ("case", "T_K", "p_Pa", "collisions", "diameter_m", "cell_m",
                                     "fnum", "dt_s", "slab_m")},
        outputs=out,
        warnings=["Bi treated as monatomic hard spheres (Bi2 in the vapour neglected)",
                  "Collisions above the sampling slab neglected (ballistic propagation)",
                  "Sensor size neglected; profiles averaged over +/- x and azimuth"],
        disabled_physics=["Bi2 dimers", "surface diffusion/condensation on the lip"])
    print(f"Wrote {write_manifest(manifest, work / 'manifest.json')}")


if __name__ == "__main__":
    main()
