"""Can the layout even out a beaming nitrogen plate? Aim-offset and port-angle scan.

Follows scripts/nitrogen_plate_scenarios.py, which found that straight-hole plates with the
published hole sets (R13, R30; L/r 2.9-19.7) aimed at the wafer centre from 350 mm give
20 % to over 200 % range/mean over 200 mm. A narrow beam aimed off-centre on a rotating wafer
spreads its dose over an annulus, which can flatten the rotation average. This scan moves
the aim point along the source's azimuth (aim_offset, beam.source_on_cone; positive towards
the source side) and the port angle, for:
- L/r 0 (thin plate, cosine holes), 2.92, 5.83 and 11.66 (R30's 0.343 mm holes in a 0.5 /
  1 / 2 mm plate; the map depends on L/r, not on hole size);
- active plate radius 20 mm, uniform hole output, throw 350 mm (and 450 mm at the best
  offsets, as a longer-throw option).
Hole sampling: hexagonal pitch R/2 (the scenario study found pitch R/4 -> R/8 changes the
deepest case by 0.25 points). Metric: range/mean over the whole 200 mm wafer of the
rotation-averaged flux (36 rotation angles). Free-molecular: valid where the hole Knudsen
number is at least about 10 (0.5-3 sccm for the many-hole plates). Shape only.

Output: the full grid, the best (offset, angle) per L/r with a +/-10 mm offset tolerance,
and the radial profile at the optimum.

The default grid (offsets -80..80 mm, angles 0-45 deg) put the beaming plates' optima on its
edge (2026-10-01); the extended run uses --aspects 2.92 5.83 11.66 --offsets 60 75 90 105 120
135 150 --angles 40 45 50 55 60 65 --out results/nitrogen_aim_study_ext.

Usage: python scripts/nitrogen_aim_study.py [--particles 20000] [--out results/nitrogen_aim_study]
                                            [--aspects ...] [--offsets ...] [--angles ...]
"""

import argparse
import itertools
from pathlib import Path

import numpy as np

from mbe_twin.aperture import aperture_plate_sources, hex_holes
from mbe_twin.beam import Wafer, rotation_averaged_flux
from mbe_twin.crucible import Crucible, simulate
from mbe_twin.manifest import build_manifest, write_manifest
from mbe_twin.metrics import radial_uniformity

ROOT = Path(__file__).resolve().parents[1]
WAFER_RADIUS = 0.100
HOLE_RADIUS = 0.1e-3
ASPECTS = (0.0, 2.92, 5.83, 11.66)
PLATE_RADIUS = 0.020
THROW = 0.350
LONG_THROW = 0.450
OFFSETS_MM = (-80, -60, -40, -20, 0, 20, 40, 60, 80)
ANGLES_DEG = (0.0, 15.0, 30.0, 45.0)
RHO = np.linspace(0.0, WAFER_RADIUS, 41)


def profile(events, offset_m, angle_deg, throw, wafer, holes):
    src = aperture_plate_sources("N", wafer, events, holes, throw=throw, polar_angle=np.radians(angle_deg),
                                 azimuth=0.0, total_rate=1.0, aim_offset=offset_m)
    return rotation_averaged_flux(src, wafer, RHO, n_angles=36)


def range_over_mean(prof):
    s = radial_uniformity(prof, RHO, WAFER_RADIUS)
    return float(100.0 * (s["max"] - s["min"]) / s["mean"])


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--particles", type=int, default=20_000)
    ap.add_argument("--out", default="results/nitrogen_aim_study")
    ap.add_argument("--aspects", type=float, nargs="+", default=list(ASPECTS))
    ap.add_argument("--offsets", type=int, nargs="+", default=list(OFFSETS_MM), help="aim offsets (mm)")
    ap.add_argument("--angles", type=float, nargs="+", default=list(ANGLES_DEG), help="port angles (deg)")
    args = ap.parse_args()
    offsets, angles = tuple(args.offsets), tuple(args.angles)
    wafer = Wafer(radius=WAFER_RADIUS)
    holes = hex_holes(PLATE_RADIUS, PLATE_RADIUS / 2.0)
    rows = []
    for i, a in enumerate(args.aspects):
        ev = simulate(Crucible(HOLE_RADIUS, a * HOLE_RADIUS), args.particles, rng=80 + i)
        grid = np.full((len(offsets), len(angles)), np.nan)
        print(f"\nL/r {a:5.2f} (transmission {ev.transmission:.3f}), {len(holes)} holes, throw {1e3 * THROW:.0f} mm: "
              "range/mean % by aim offset (rows, mm) and port angle " + " ".join(f"{x:5.0f}" for x in angles),
              flush=True)
        for (j, off), (k, ang) in itertools.product(enumerate(offsets), enumerate(angles)):
            grid[j, k] = range_over_mean(profile(ev, off / 1e3, ang, THROW, wafer, holes))
        for j, off in enumerate(offsets):
            print(f"  {off:5d} " + " ".join(f"{v:5.1f}" for v in grid[j]), flush=True)
        j, k = np.unravel_index(np.nanargmin(grid), grid.shape)
        best_off, best_ang = offsets[j], angles[k]
        # local refinement: 5 mm offset steps around the best grid point
        fine_offsets = np.arange(best_off - 15, best_off + 16, 5)
        fine = [range_over_mean(profile(ev, o / 1e3, best_ang, THROW, wafer, holes)) for o in fine_offsets]
        m = int(np.argmin(fine))
        opt_off = float(fine_offsets[m])
        tol = [v for o, v in zip(fine_offsets, fine) if abs(o - opt_off) <= 10]
        prof = profile(ev, opt_off / 1e3, best_ang, THROW, wafer, holes)
        long_throw = range_over_mean(profile(ev, opt_off / 1e3, best_ang, LONG_THROW, wafer, holes))
        centred_long = range_over_mean(profile(ev, 0.0, best_ang, LONG_THROW, wafer, holes))
        centred = range_over_mean(profile(ev, 0.0, best_ang, THROW, wafer, holes))
        print(f"  best: offset {opt_off:+.0f} mm at {best_ang:.0f} deg -> {fine[m]:.1f} % "
              f"(within +/-10 mm: {min(tol):.1f}-{max(tol):.1f} %); centred at that angle "
              f"{centred:.1f} %; at 450 mm: offset {long_throw:.1f} %, centred {centred_long:.1f} %",
              flush=True)
        print("  profile r mm " + " ".join(f"{v:6.0f}" for v in 1e3 * RHO[::5]))
        print("  relative     " + " ".join(f"{v:6.3f}" for v in (prof / prof.mean())[::5]), flush=True)
        rows.append({"L_over_r": a, "transmission": ev.transmission, "offsets_mm": offsets,
                     "angles_deg": angles, "range_over_mean_pct": grid.tolist(),
                     "fine_offsets_mm": fine_offsets.tolist(), "fine_range_over_mean_pct": fine,
                     "best": {"offset_mm": opt_off, "angle_deg": best_ang, "range_over_mean_pct": fine[m],
                              "within_10mm_pct": [min(tol), max(tol)],
                              "throw_450mm_offset_pct": long_throw, "throw_450mm_centred_pct": centred_long},
                     "best_profile_relative": (prof / prof.mean()).tolist()})

    manifest = build_manifest(
        "nitrogen_aim_study", label="representative_chamber", validation_status="not_validated",
        inputs={"particles": args.particles, "hole_radius_m": HOLE_RADIUS, "aspects": args.aspects,
                "plate_radius_m": PLATE_RADIUS, "hole_pitch_m": PLATE_RADIUS / 2.0, "throw_m": THROW,
                "long_throw_m": LONG_THROW, "offsets_mm": offsets, "angles_deg": angles},
        outputs={"rows": rows, "rho_m": RHO},
        sources=[Path(__file__), ROOT / "src/mbe_twin/aperture.py", ROOT / "src/mbe_twin/beam.py",
                 ROOT / "src/mbe_twin/crucible.py"],
        warnings=["Free-molecular straight holes; not valid where the hole Kn is below about 10",
                  "Plate radius, hole pattern and thickness not published; uniform hole output assumed",
                  "Hole-wall recombination, ions and plume collisions not modelled; shape only"],
        disabled_physics=["plasma chemistry", "wall recombination", "ion species", "transitional hole flow"])
    print(f"Wrote {write_manifest(manifest, Path(args.out) / 'manifest.json')}")


if __name__ == "__main__":
    main()
