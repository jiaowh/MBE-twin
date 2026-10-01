"""Does transitional hole flow change the nitrogen beam? DSMC of one aperture-plate hole.

The nitrogen maps of the layout studies treat each plate hole as a free-molecular tube
(crucible.py random walk). At the feeds a 200 mm wafer needs, the leading plate's holes are
transitional (Kn = lambda / d_hole of 1-10; scripts/nitrogen_plate_design.py), as were the
published high-rate plates (R26, 20-34 sccm). This script runs SPARTA (2d axisymmetric, serial,
in WSL) on one hole of the R30 set in a 0.5 mm plate (d 0.343 mm, L/r 2.92):
- a wide, short reservoir (radius 3 mm, 0.5 mm deep) fed over its whole far face by an
  equilibrium N2 flux (fix emit/face) at density n0 and 300 K, so that the gas reaching the plate
  is close to isotropic at every Kn, as in a plasma bulb many mean free paths across. (A narrow
  feed tube beams collisionless gas towards the hole and was rejected after the first runs:
  at Kn 100 it made the beam 7 % more peaked than the free-molecular reference.) Diffuse walls
  at 300 K; the plate spans the domain so no gas passes round it;
- the hole; an open downstream region with outflow boundaries.
n0 is set from the nominal Knudsen number Kn = lambda_HS / d_hole (hard-sphere N2, 3.7 A,
as the plate studies); collisions use SPARTA's VSS N2 (air.vss), whose mean free path is
about 0.8 lambda_HS. Kn = 100 is the free-molecular check.

Measured, from particles dumped in two slabs (straight-line flux estimators, sum of v_x / slab
thickness): the transmitted rate (slab just past the exit, r < r_hole), the transmission
probability against the inlet flux the feed face sends to the hole, n0 <v> / 4 pi r_hole^2 times
the face's cosine-weighted coverage of the hole's view (0.973; Clausing W for free flow; the
density probed in front of the plate reads low because the hole returns no gas), and the angular intensity I(theta) per transmitted particle (slab 1 mm downstream,
directions of particles moving outward, up to 70 deg). I(theta) is fitted with
I_FM(theta) x R(theta), with R a quadratic in theta fitted to the binned ratio (weighted least
squares on the 2.5 deg bins): the raw bins are noisy at small theta where their solid angle
is small, and the map metrics respond to the shape of I near theta = 0 (a fit of I itself
within 0.5 % moved B's thickness by 0.07 points), which the free-molecular reference carries. Statistical errors of every reported metric come from 8 contiguous time
blocks (standard error of the block means). The Kn 100 case is compared with the free-molecular
maps; it reproduces B but not C (C's nominal map responds to small differences in the beam
shape near the axis, here from the feed face missing the most grazing directions). Each lower-
Kn case is therefore also reported against the Kn 100 DSMC run, which shares that set-up, so
the difference isolates collisions (errors from both runs' blocks combined).

Then, at the 350 mm throw, the plate's hex pattern of holes (20 mm active radius, uniform
output, as the comparison) is summed with each tabulated I(theta) on the rotating wafer for
the nominal B and C aims, without lip or attenuation, giving the N-limited thickness
half-range/mean on r <= 94 mm. The free-molecular table is computed the same way from the
random-walk events (far-field next-event flux), so differences are due to the hole flow alone.

Usage: python scripts/sparta_hole.py [--kn 100 10 3 1 0.3] [--out results/sparta_hole] [--reuse]
"""

import argparse
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402

from mbe_twin.aperture import hex_holes  # noqa: E402
from mbe_twin.beam import Wafer  # noqa: E402
from mbe_twin.crucible import Crucible, next_event_flux, simulate  # noqa: E402
from mbe_twin.layout import SourcePort  # noqa: E402
from mbe_twin.manifest import build_manifest, write_manifest  # noqa: E402
from mbe_twin.sparta import expected_dump_steps, iter_dumps, run_case, wsl_path  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
K_B = 1.380649e-23
M_N2 = 28.0134 * 1.66053907e-27
D_HS = 3.7e-10
T_GAS = 300.0
R_HOLE, L_HOLE = 0.1715e-3, 0.5e-3
R_RES, X_UP, X_DN, Y_TOP = 3.0e-3, 0.5e-3, 1.5e-3, 3.0e-3
CELL = 0.04e-3
DT = 2.0e-8
STEPS_EQ, STEPS_SAMPLE, DUMP_EVERY = 4000, 100000, 50
SLAB_EXIT = 0.02e-3          # thickness of the full-width slab just past the exit plane
PROBE = (-0.4e-3, -0.2e-3)   # reservoir density probe (x range; r < PROBE_R)
PROBE_R = 1.0e-3
N_BLOCKS = 8
SLAB_FAR = (1.0e-3, 0.1e-3)  # distance past the exit, thickness
TARGET_PARTICLES = 300_000
THETA_EDGES = np.radians(np.arange(0.0, 72.5, 2.5))
LAYOUTS = {"B": (46.0, 105.0), "C": (65.0, 75.0)}
RHO = np.linspace(0.0, 0.094, 39)


def n_from_kn(kn):
    lam = kn * 2 * R_HOLE
    return 1.0 / (np.sqrt(2) * np.pi * D_HS ** 2 * lam)


def write_surface(path):
    """Plate x 0..L from the hole radius to beyond the domain top (clipped), listed counter-clockwise
    (solid on the left) and written edge-reversed so the normals face the gas (SPARTA: outward normal
    = z x (p2 - p1))."""
    top = Y_TOP + 0.2e-3
    pts = [(0.0, R_HOLE), (L_HOLE, R_HOLE), (L_HOLE, top), (0.0, top)]
    lines = ["# hole plate (2d axisymmetric)", "", f"{len(pts)} points", f"{len(pts)} lines", "", "Points", ""]
    lines += [f"{i + 1} {x:.17g} {y:.17g}" for i, (x, y) in enumerate(pts)]
    lines += ["", "Lines", ""]
    lines += [f"{i + 1} {(i + 1) % len(pts) + 1} {i + 1}" for i in range(len(pts))]
    Path(path).write_text("\n".join(lines) + "\n", encoding="ascii", newline="\n")


def case_input(n0, fnum, seed):
    nx = int(round((X_UP + L_HOLE + X_DN) / CELL))
    ny = int(round(Y_TOP / CELL))
    x_far = L_HOLE + SLAB_FAR[0]
    return "\n".join([
        f"seed {seed}", "dimension 2", "units si", "global gridcut 0.0",
        "boundary o ao p",
        f"create_box {-X_UP:.9g} {L_HOLE + X_DN:.9g} 0 {Y_TOP:.9g} -0.5 0.5",
        f"create_grid {nx} {ny} 1",
        "balance_grid rcb cell",
        f"global nrho {n0:.6e} fnum {fnum:.6e}",
        "species air.species N2",
        f"mixture gas N2 nrho {n0:.6e} temp {T_GAS}",
        "read_surf hole.surf clip",
        f"surf_collide wall diffuse {T_GAS} 1.0",
        "surf_modify all collide wall",
        "collide vss gas air.vss",
        "fix in emit/face gas xlo",
        f"timestep {DT:.6e}",
        "stats 5000", "stats_style step cpu np nscoll",
        f"run {STEPS_EQ}",
        f"region exitslab block {L_HOLE:.9g} {L_HOLE + SLAB_EXIT:.9g} INF INF INF INF",
        f"region farslab block {x_far:.9g} {x_far + SLAB_FAR[1]:.9g} INF INF INF INF",
        f"region inlet block {PROBE[0]:.9g} {PROBE[1]:.9g} INF {PROBE_R:.9g} INF INF",
        f"dump ex particle gas {DUMP_EVERY} dump.exit.* id x y z vx vy vz", "dump_modify ex region exitslab",
        f"dump fa particle gas {DUMP_EVERY} dump.far.* id x y z vx vy vz", "dump_modify fa region farslab",
        f"dump in particle gas {DUMP_EVERY} dump.inlet.* id x y z vx vy vz", "dump_modify in region inlet",
        f"run {STEPS_SAMPLE}", ""])


def run_kn(kn, out, reuse, seed=11):
    work = out / f"kn{kn:g}"
    cfg = {"kn": kn, "n0": n_from_kn(kn), "geometry": [R_HOLE, L_HOLE, R_RES, X_UP, X_DN, Y_TOP], "cell": CELL, "dt": DT,
           "steps": [STEPS_EQ, STEPS_SAMPLE, DUMP_EVERY], "target_particles": TARGET_PARTICLES, "seed": seed}
    steps = expected_dump_steps(STEPS_EQ, STEPS_SAMPLE, DUMP_EVERY)
    done = (work / "config.json").exists() and json.loads((work / "config.json").read_text()) == cfg and \
        (work / "log.sparta").exists() and "Loop time" in (work / "log.sparta").read_text(errors="replace")
    if not (reuse and done):
        if work.exists():
            shutil.rmtree(work)
        work.mkdir(parents=True)
        n0 = cfg["n0"]
        volume = np.pi * R_RES ** 2 * X_UP
        fnum = n0 * volume / TARGET_PARTICLES
        for f in ("air.species", "air.vss"):
            subprocess.run(["wsl.exe", "-e", "bash", "-lc", f"cp ~/sparta/data/{f} '{wsl_path(work)}/'"], check=True)
        write_surface(work / "hole.surf")
        (work / "in.case").write_text(case_input(n0, fnum, seed), encoding="ascii", newline="\n")
        cfg["fnum"] = fnum
        t = time.time()
        run_case(work)
        print(f"Kn {kn:g}: SPARTA {time.time() - t:.0f} s", flush=True)
        (work / "config.json").write_text(json.dumps({k: v for k, v in cfg.items() if k != "fnum"}), encoding="utf-8")
    return work, steps


def slab_flux(work, steps, prefix, thickness, fn):
    """Per-block means over snapshots of fn(positions, velocities) / thickness (straight-line flux
    estimator: sum of v_x / slab thickness), shape (N_BLOCKS, ...)."""
    bounds = np.linspace(0, len(steps), N_BLOCKS + 1).astype(int)
    sums, counts = None, np.zeros(N_BLOCKS)
    for i, p, v in iter_dumps(work, steps, prefix):
        y = np.asarray(fn(p, v), float) / thickness
        k = np.searchsorted(bounds, i, side="right") - 1
        if sums is None:
            sums = np.zeros((N_BLOCKS,) + y.shape)
        sums[k] += y
        counts[k] += 1
    return sums / counts.reshape((-1,) + (1,) * (sums.ndim - 1))


def analyse(work, steps):
    """Per-block exit rate, far-slab angular flux histogram and reservoir particle density (simulation units)."""
    exit_rate = slab_flux(work, steps, "dump.exit.", SLAB_EXIT, lambda p, v: np.array([v[:, 0].sum()]))[:, 0]

    def angles(p, v):
        out = v[:, 0] > 0
        th = np.arctan2(np.hypot(v[out, 1], v[out, 2]), v[out, 0])
        return np.histogram(th, THETA_EDGES, weights=v[out, 0])[0]
    far = slab_flux(work, steps, "dump.far.", SLAB_FAR[1], angles)
    count = slab_flux(work, steps, "dump.inlet.", 1.0, lambda p, v: np.array([len(p)]))[:, 0]
    dens = count / ((PROBE[1] - PROBE[0]) * np.pi * PROBE_R ** 2)
    return exit_rate, far, dens


SOLID = 2 * np.pi * (np.cos(THETA_EDGES[:-1]) - np.cos(THETA_EDGES[1:]))
TH_C = 0.5 * (THETA_EDGES[:-1] + THETA_EDGES[1:])
RATIO_DEGREE = 2


def fit_intensity(intensity, reference):
    """I(theta) = reference(theta) x R(theta), R a polynomial in theta of RATIO_DEGREE fitted to the binned
    ratio (least squares weighted by bin solid angle). The reference (the free-molecular table) carries
    the cusp at theta = 0 that low-order fits of I itself miss; the map metrics are sensitive to it."""
    basis = np.stack([TH_C ** k for k in range(RATIO_DEGREE + 1)], 1)
    w = np.sqrt(SOLID)
    coef, *_ = np.linalg.lstsq(basis * w[:, None], (intensity / reference) * w, rcond=None)
    return reference * (basis @ coef)


def mean_err(x):
    x = np.asarray(x, float)
    return float(x.mean()), float(x.std(ddof=1) / np.sqrt(len(x)))


def fm_intensity(aspect, particles=200_000, seed=80):
    ev = simulate(Crucible(1.0, aspect), particles, rng=seed)
    R = 1e4
    th = 0.5 * (THETA_EDGES[:-1] + THETA_EDGES[1:])
    pts = np.stack([R * np.sin(th), np.zeros_like(th), R * np.cos(th)], 1)
    normals = -pts / R
    flux = next_event_flux(ev, pts, normals)
    return (flux * R ** 2 / ev.transmission), ev.transmission, ev


def tabulated_map(intensity, polar_deg, offset_mm, n_angles=72):
    """Rotation-averaged N flux per unit plate output from point holes with intensity I(theta) (per sr)."""
    wafer = Wafer(radius=0.100)
    port = SourcePort("N", polar_deg=polar_deg, azimuth_deg=0.0, throw=0.350, aim_offset=offset_mm / 1e3)
    centre, axis = port.pose(wafer)
    centre, axis = np.asarray(centre, float), np.asarray(axis, float) / np.linalg.norm(axis)
    a0 = np.cross(axis, [0.0, 0.0, 1.0]) if abs(axis[2]) < 0.9 else np.cross(axis, [1.0, 0.0, 0.0])
    a0 /= np.linalg.norm(a0)
    a1 = np.cross(axis, a0)
    holes = hex_holes(0.020, 0.010)
    hp = centre + holes[:, :1] * a0 + holes[:, 1:] * a1
    th_c = 0.5 * (THETA_EDGES[:-1] + THETA_EDGES[1:])
    normal = np.asarray(wafer.normal, float)
    phi = np.linspace(0.0, 2 * np.pi, 4 * n_angles, endpoint=False)   # rotation average = azimuthal average
    pts = wafer.points(RHO[:, None], phi[None, :]).reshape(-1, 3)
    d = pts[None, :, :] - hp[:, None, :]
    r = np.linalg.norm(d, axis=-1)
    cos_th = (d @ axis) / r
    cos_in = -(d @ normal) / r
    theta = np.arccos(np.clip(cos_th, -1, 1))
    inten = np.interp(theta, th_c, intensity, right=0.0)
    f = np.where((cos_in > 0) & (cos_th > 0), inten * cos_in / r ** 2, 0.0).mean(0)   # mean over holes: per unit output
    return f.reshape(len(RHO), len(phi)).mean(1)


def thickness(m):
    w = np.diff(np.concatenate(([0.0], 0.5 * (RHO[1:] + RHO[:-1]), [RHO[-1]])) ** 2)
    mean = np.sum(w * m) / w.sum()
    return float(100 * (m.max() - m.min()) / (2 * mean))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--kn", nargs="+", type=float, default=[100.0, 10.0, 3.0, 1.0, 0.3])
    ap.add_argument("--out", default="results/sparta_hole")
    ap.add_argument("--reuse", action="store_true")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    fm_I, fm_W, _ = fm_intensity(L_HOLE / R_HOLE)
    fm_maps = {k: tabulated_map(fm_I, *v) for k, v in LAYOUTS.items()}
    print("free-molecular: W = %.4f; maps " % fm_W + ", ".join(f"{k} {thickness(m):.2f} %" for k, m in fm_maps.items()), flush=True)
    rows = []
    fm_fit = fm_I
    fm_fit_maps = {k: tabulated_map(fm_fit, *v) for k, v in LAYOUTS.items()}
    for kn in args.kn:
        n0 = n_from_kn(kn)
        work, steps = run_kn(kn, out, args.reuse)
        exit_rate, far, dens = analyse(work, steps)
        fnum = n0 * np.pi * R_RES ** 2 * X_UP / TARGET_PARTICLES
        vbar = np.sqrt(8 * K_B * T_GAS / (np.pi * M_N2))
        n_res = dens * fnum
        kn_res = 1.0 / (np.sqrt(2) * np.pi * D_HS ** 2 * n_res) / (2 * R_HOLE)
        coverage = 1.0 - (X_UP / np.hypot(X_UP, R_RES)) ** 2      # cosine-weighted view of the feed face from the hole
        w_blocks = exit_rate * fnum / (coverage * n0 * vbar / 4 * np.pi * R_HOLE ** 2)
        frac = far / exit_rate[:, None]
        raw = frac / SOLID
        fits = np.array([fit_intensity(r, fm_I) for r in raw])
        per_block = {k: [tabulated_map(f, *v) for f in fits] for k, v in LAYOUTS.items()}
        whole_fit = fit_intensity(raw.mean(0), fm_I)
        maps = {k: tabulated_map(whole_fit, *v) for k, v in LAYOUTS.items()}
        row = {"kn_nominal": kn, "kn_reservoir": mean_err(kn_res), "n0_m3": n0, "n_reservoir_m3": mean_err(n_res),
               "pressure_Pa": float(n_res.mean() * K_B * T_GAS), "transmission": mean_err(w_blocks),
               "captured_fraction_to_70deg": mean_err(frac.sum(1)),
               "intensity_raw_per_sr": raw.mean(0).tolist(), "intensity_fit_per_sr": whole_fit.tolist(),
               "peak_over_fm": mean_err(fits[:, 0] / fm_fit[0]),
               "thickness_pct": {k: {"whole_run": thickness(maps[k]), "blocks": mean_err([thickness(m) for m in per_block[k]])}
                                 for k in LAYOUTS},
               "thickness_minus_fm_points": {k: mean_err([thickness(m) - thickness(fm_fit_maps[k]) for m in per_block[k]])
                                             for k in LAYOUTS},
               "delivered_over_fm": {k: mean_err([np.mean(m) / np.mean(fm_fit_maps[k]) for m in per_block[k]]) for k in LAYOUTS}}
        row["_block_thickness"] = {k: [thickness(m) for m in per_block[k]] for k in LAYOUTS}
        row["_block_delivered"] = {k: [float(np.mean(m)) for m in per_block[k]] for k in LAYOUTS}
        rows.append(row)
        t = row["thickness_minus_fm_points"]
        print(f"Kn {kn:g} (reservoir Kn {row['kn_reservoir'][0]:.2f}, p {row['pressure_Pa']:.2f} Pa): W {row['transmission'][0]:.3f} "
              f"+/- {row['transmission'][1]:.3f} (FM {fm_W:.3f}); I(0)/I_FM(0) {row['peak_over_fm'][0]:.3f} +/- {row['peak_over_fm'][1]:.3f}; "
              f"thickness - FM: B {t['B'][0]:+.3f} +/- {t['B'][1]:.3f}, C {t['C'][0]:+.3f} +/- {t['C'][1]:.3f} points; "
              f"delivered/FM B {row['delivered_over_fm']['B'][0]:.3f} +/- {row['delivered_over_fm']['B'][1]:.3f}", flush=True)
    # differences against the most rarefied DSMC run (same set-up), errors combined in quadrature
    ref = max(rows, key=lambda r: r["kn_nominal"])
    for r in rows:
        r["minus_dsmc_reference"] = {"reference_kn": ref["kn_nominal"]}
        for k in LAYOUTS:
            a, b = np.asarray(r["_block_thickness"][k]), np.asarray(ref["_block_thickness"][k])
            da, db = np.asarray(r["_block_delivered"][k]), np.asarray(ref["_block_delivered"][k])
            r["minus_dsmc_reference"][k] = {
                "thickness_points": [float(a.mean() - b.mean()), float(np.hypot(a.std(ddof=1), b.std(ddof=1)) / np.sqrt(len(a)))],
                "delivered_ratio": [float(da.mean() / db.mean()),
                                    float(da.mean() / db.mean() * np.hypot(da.std(ddof=1) / da.mean(), db.std(ddof=1) / db.mean())
                                          / np.sqrt(len(da)))]}
        m = r["minus_dsmc_reference"]
        print(f"Kn {r['kn_nominal']:g} vs Kn {ref['kn_nominal']:g} DSMC: thickness B {m['B']['thickness_points'][0]:+.3f} +/- "
              f"{m['B']['thickness_points'][1]:.3f}, C {m['C']['thickness_points'][0]:+.3f} +/- {m['C']['thickness_points'][1]:.3f} "
              f"points; delivered B {m['B']['delivered_ratio'][0]:.3f} +/- {m['B']['delivered_ratio'][1]:.3f}", flush=True)
    for r in rows:
        r.pop("_block_thickness")
        r.pop("_block_delivered")
    manifest = build_manifest(
        "sparta_hole", label="representative_chamber", validation_status="not_validated",
        inputs={"kn": args.kn, "geometry_m": {"r_hole": R_HOLE, "L": L_HOLE, "r_reservoir": R_RES, "x_up": X_UP, "x_dn": X_DN,
                                              "y_top": Y_TOP}, "cell_m": CELL, "dt_s": DT,
                "steps": [STEPS_EQ, STEPS_SAMPLE, DUMP_EVERY], "theta_edges_deg": np.degrees(THETA_EDGES).tolist(),
                "T_gas_K": T_GAS, "layouts": LAYOUTS},
        outputs={"fm": {"transmission": fm_W, "intensity_per_sr": fm_I.tolist(), "intensity_fit_per_sr": fm_fit.tolist(),
                        "thickness_pct": {k: thickness(m) for k, m in fm_maps.items()},
                        "thickness_fit_pct": {k: thickness(m) for k, m in fm_fit_maps.items()}}, "rows": rows,
                 "ratio_degree": RATIO_DEGREE, "n_blocks": N_BLOCKS},
        sources=[Path(__file__), ROOT / "src/mbe_twin/sparta.py", ROOT / "src/mbe_twin/crucible.py",
                 ROOT / "src/mbe_twin/aperture.py", ROOT / "src/mbe_twin/layout.py", ROOT / "src/mbe_twin/beam.py"],
        warnings=["Single hole fed from a wide isotropic reservoir; interaction between neighbouring holes not represented", "300 K neutral N2 only; discharge heating and atoms not modelled",
                  "Maps without lip, attenuation or Ga; shape comparison only"])
    print(f"Wrote {write_manifest(manifest, out / 'manifest.json')}")


if __name__ == "__main__":
    main()
