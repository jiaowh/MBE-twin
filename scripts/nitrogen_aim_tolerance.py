"""Pointing-tolerant nitrogen aim: the worst N map within an angular pointing error of the source.

A pointing error is a tilt of the source axis, not a fixed shift of the aim point: at an
oblique, off-centre aim the same tilt moves the aim point by more than throw x angle
(+/-0.8 deg is about +/-7.5 mm at 65 deg / +75 mm, not +/-5 mm), and unequally on the two
sides. So this script tilts the axis directly (`aperture_plate_sources(axis=...)`) about the
plate centre:
- in the plane of incidence by -tol..+tol in 0.4 deg steps (positive moves the aim outwards,
  away from the wafer centre), at every scanned aim within +/-10 mm of the nominal optimum;
- sideways (out of that plane) by +/-0.8 and +/-1.6 deg at the nominal optimum, to check that
  lateral error is second order under rotation.
For each plate and port angle it reports the nominal optimum, the worst range/mean within
+/-0.8 and +/-1.6 deg there, and the scanned aim whose worst case is lowest (robust aim).
The tilted runs reuse each scan's hole events (same particles and seed), so the untilted
value reproduces the scanned one.

Inputs (versioned records, default): data/runs/studies/nitrogen_aim_fine_<L/r>.json (5 mm
aim scans at 55 / 60 / 65 deg) and the thin plate (L/r 0) fine row of nitrogen_aim_study.json.
The script stops with an error if the record of any requested plate (default: all
of PLATES) is missing or does not hold that plate.

Usage: python scripts/nitrogen_aim_tolerance.py [--out results/nitrogen_aim_tolerance]
                                                [--studies data/runs/studies] [--plates 2.92 ...]
"""

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nitrogen_aim_study as study  # noqa: E402  (same geometry and metric as the scans)

from mbe_twin.aperture import aperture_plate_sources, hex_holes  # noqa: E402
from mbe_twin.beam import Wafer, rotation_averaged_flux, source_on_cone  # noqa: E402
from mbe_twin.crucible import Crucible, simulate  # noqa: E402
from mbe_twin.manifest import build_manifest, write_manifest  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TOLERANCES_DEG = (0.8, 1.6)
TILT_STEP_DEG = 0.4
CANDIDATE_WINDOW_MM = 10
PLATES = (0.0, 2.92, 5.83, 11.66, 19.69)  # thin plate; R30 hole in 0.5 / 1 / 2 mm; R13 hole in 2 mm
SEED = 80  # nitrogen_aim_study.py: rng = 80 + index of the aspect in --aspects; every input scan ran one aspect first


def load_scans(studies_dir, plates=PLATES):
    """(L/r, particles, offsets_mm, angles_deg, grid %) for each requested plate from the versioned records.

    Every plate must be one of PLATES and have its record: the thin plate (L/r 0) comes from the
    fine row of nitrogen_aim_study.json, the others from nitrogen_aim_fine_<L/r>.json.
    """
    studies_dir = Path(studies_dir)
    unknown = [a for a in plates if not any(abs(a - b) < 1e-6 for b in PLATES)]
    if unknown:
        raise SystemExit(f"nitrogen_aim_tolerance: no aim scan defined for L/r {unknown} (known: {list(PLATES)})")
    plates = sorted({next(b for b in PLATES if abs(a - b) < 1e-6) for a in plates})
    paths = {a: studies_dir / ("nitrogen_aim_study.json" if a == 0.0 else f"nitrogen_aim_fine_{a:g}.json") for a in plates}
    missing = [str(p) for p in paths.values() if not p.exists()]
    if missing:
        raise SystemExit("nitrogen_aim_tolerance: required aim scans not found: " + ", ".join(missing))
    scans = []
    for a, path in paths.items():
        m = json.loads(path.read_text(encoding="utf-8"))
        rows = [r for r in m["outputs"]["rows"] if abs(r["L_over_r"] - a) < 1e-6]
        if len(rows) != 1 or m["inputs"]["aspects"][0] != a:
            # the seed (SEED) is only right for the first aspect of the run that wrote the record
            raise SystemExit(f"nitrogen_aim_tolerance: {path} does not hold L/r {a:g} as its first aspect")
        r = rows[0]
        if a == 0.0:
            offsets, angles = r["fine_offsets_mm"], [r["best"]["angle_deg"]]
            grid = np.asarray(r["fine_range_over_mean_pct"], float)[:, None]
        else:
            offsets, angles, grid = r["offsets_mm"], r["angles_deg"], np.asarray(r["range_over_mean_pct"], float)
        scans.append({"source": path, "L_over_r": a, "particles": m["inputs"]["particles"],
                      "offsets_mm": offsets, "angles_deg": angles, "grid": grid})
    return scans


def nominal_geometry(wafer, offset_m, angle_deg):
    """Plate centre, nominal axis, in-plane tilt direction (outwards) and sideways direction."""
    src = source_on_cone("ref", wafer, throw=study.THROW, polar_angle=np.radians(angle_deg), azimuth=0.0,
                         emission_rate=1.0, aim_offset=offset_m)
    pos, a0 = np.asarray(src.position), np.asarray(src.axis)
    side = np.cross(np.asarray(wafer.normal, float), wafer.basis[0])  # normal to the plane of incidence
    side /= np.linalg.norm(side)
    out = wafer.basis[0] - (wafer.basis[0] @ a0) * a0  # in-plane, perpendicular to the axis, outwards
    return pos, a0, out / np.linalg.norm(out), side


def tilted_axis(a0, direction, tilt_deg):
    t = np.radians(tilt_deg)
    return np.cos(t) * a0 + np.sin(t) * direction


def aim_point(wafer, pos, axis):
    """Where the axis meets the wafer plane, as (radial, lateral) metres in the source frame."""
    c, n = np.asarray(wafer.center, float), np.asarray(wafer.normal, float)
    p = pos + ((c - pos) @ n) / (axis @ n) * axis
    e1, e2 = wafer.basis
    return float((p - c) @ e1), float((p - c) @ e2)


def range_with_axis(events, wafer, holes, offset_m, angle_deg, axis):
    src = aperture_plate_sources("N", wafer, events, holes, throw=study.THROW, polar_angle=np.radians(angle_deg),
                                 azimuth=0.0, total_rate=1.0, aim_offset=offset_m, axis=axis)
    return study.range_over_mean(rotation_averaged_flux(src, wafer, study.RHO, n_angles=36))


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="results/nitrogen_aim_tolerance")
    ap.add_argument("--studies", default=str(ROOT / "data/runs/studies"), help="directory of the versioned aim scans")
    ap.add_argument("--plates", type=float, nargs="+", help=f"only these L/r (default: all of {PLATES})")
    args = ap.parse_args()
    scans = load_scans(args.studies, args.plates or PLATES)
    wafer = Wafer(radius=study.WAFER_RADIUS)
    holes = hex_holes(study.PLATE_RADIUS, study.PLATE_RADIUS / 2.0)
    n_steps = int(round(max(TOLERANCES_DEG) / TILT_STEP_DEG))
    tilts = TILT_STEP_DEG * np.arange(-n_steps, n_steps + 1)
    rows = []
    for scan in scans:
        a = scan["L_over_r"]
        ev = simulate(Crucible(study.HOLE_RADIUS, a * study.HOLE_RADIUS), scan["particles"], rng=SEED)
        offs = np.asarray(scan["offsets_mm"], float)
        for k, angle in enumerate(scan["angles_deg"]):
            col = scan["grid"][:, k]
            j0 = int(np.argmin(col))
            cands = [j for j in range(len(offs)) if abs(offs[j] - offs[j0]) <= CANDIDATE_WINDOW_MM]
            per_aim = []
            for j in cands:
                pos, a0, out, side = nominal_geometry(wafer, offs[j] / 1e3, angle)
                vals = [range_with_axis(ev, wafer, holes, offs[j] / 1e3, angle, tilted_axis(a0, out, t)) for t in tilts]
                shift = [1e3 * aim_point(wafer, pos, tilted_axis(a0, out, t))[0] - offs[j] for t in tilts]
                rec = {"offset_mm": float(offs[j]), "scanned_pct": float(col[j]), "tilts_deg": tilts.tolist(),
                       "pct": vals, "aim_shift_mm": shift,
                       "worst_pct": {f"{t}": float(max(v for v, d in zip(vals, tilts) if abs(d) <= t + 1e-9))
                                     for t in TOLERANCES_DEG},
                       "aim_shift_at_tol_mm": {f"{t}": [shift[int(np.argmin(np.abs(tilts + t)))],
                                                        shift[int(np.argmin(np.abs(tilts - t)))]]
                                               for t in TOLERANCES_DEG}}
                if j == j0:
                    lat = [-max(TOLERANCES_DEG), -min(TOLERANCES_DEG), min(TOLERANCES_DEG), max(TOLERANCES_DEG)]
                    rec["lateral"] = {"tilts_deg": lat, "pct": [range_with_axis(ev, wafer, holes, offs[j] / 1e3, angle,
                                                                                 tilted_axis(a0, side, t)) for t in lat]}
                per_aim.append(rec)
            nominal = next(r for r in per_aim if r["offset_mm"] == offs[j0])
            row = {"L_over_r": a, "angle_deg": angle, "nominal": nominal,
                   "reproduces_scan_pct": abs(nominal["pct"][n_steps] - nominal["scanned_pct"]),
                   "robust": {f"{t}": min(({"offset_mm": r["offset_mm"], "worst_pct": r["worst_pct"][f"{t}"],
                                            "nominal_pct_there": r["scanned_pct"]} for r in per_aim),
                                           key=lambda x: x["worst_pct"]) for t in TOLERANCES_DEG},
                   "candidates": per_aim}
            rows.append(row)
            n, r8, r16 = nominal, row["robust"]["0.8"], row["robust"]["1.6"]
            print(f"L/r {a:5.2f} {angle:4.0f} deg  nominal {n['offset_mm']:+.0f} mm {n['scanned_pct']:.2f} %  "
                  f"+/-0.8 deg (aim {n['aim_shift_at_tol_mm']['0.8'][0]:+.1f}/{n['aim_shift_at_tol_mm']['0.8'][1]:+.1f} mm): "
                  f"worst {n['worst_pct']['0.8']:.2f} %  +/-1.6 deg: worst {n['worst_pct']['1.6']:.2f} %  "
                  f"lateral +/-1.6: {max(n['lateral']['pct']):.2f} %  robust 0.8: {r8['offset_mm']:+.0f} mm "
                  f"{r8['worst_pct']:.2f} %  robust 1.6: {r16['offset_mm']:+.0f} mm {r16['worst_pct']:.2f} %", flush=True)
    manifest = build_manifest(
        "nitrogen_aim_tolerance", label="representative_chamber", validation_status="not_validated",
        inputs={"tolerances_deg": TOLERANCES_DEG, "tilt_step_deg": TILT_STEP_DEG,
                "candidate_window_mm": CANDIDATE_WINDOW_MM, "seed": SEED,
                "scans": sorted({Path(s["source"]).resolve().relative_to(ROOT).as_posix() for s in scans})},
        outputs={"rows": rows},
        sources=[Path(__file__), ROOT / "scripts/nitrogen_aim_study.py", ROOT / "src/mbe_twin/aperture.py",
                 ROOT / "src/mbe_twin/beam.py", ROOT / "src/mbe_twin/crucible.py"],
        warnings=["Axis tilt about the plate centre; port position error and plate tilt relative to the axis not included",
                  "Worst case sampled at 0.4 deg steps; robust aim chosen among scanned aims (5 mm steps) within +/-10 mm",
                  "Free-molecular straight holes; Monte Carlo scatter 0.3-0.5 points on the absolute level"])
    print(f"Wrote {write_manifest(manifest, Path(args.out) / 'manifest.json')}")


if __name__ == "__main__":
    main()
