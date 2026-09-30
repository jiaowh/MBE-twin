"""Code-to-code comparison with R14 (Tao et al. 2025, COMSOL free-molecular flow, 8-inch).

R14 geometry: cylindrical crucible, bore 71.5 mm, depth 174 mm in the text but 170 mm in
Fig. 7, fill depth 140 mm (melt 34 or 30 mm below the orifice), axis aimed at the wafer
centre, distance measured from the orifice to the wafer centre, angle from the wafer normal.
Conical crucible (Fig. 7c): 71.5 mm mouth, 170 mm deep, 14 deg included angle.
R14 is itself a simulation, so agreement is corroboration, not validation. Its non-uniformity
metric is undefined, so several metrics are reported. The R14 values quoted below were read
from its text and figures.

Usage: python scripts/compare_r14.py [--particles 100000] [--out results/r14_comparison]
"""

import argparse
from pathlib import Path

import numpy as np

from mbe_twin.beam import Wafer, crucible_source_on_cone, rotation_averaged_flux
from mbe_twin.crucible import Crucible, simulate
from mbe_twin.manifest import build_manifest, write_manifest

WAFER_RADIUS = 0.1016  # m, 8 inch as in R14
BORE_RADIUS = 0.03575
RHO = np.linspace(0.0, WAFER_RADIUS, 41)
N_ANGLES = 72

R14 = {
    "base_35deg_350mm_centre_to_edge": 2.405 / 2.665,  # Fig. 10, read from the plot
    "base_35deg_350mm_nonuniformity_pct": 8.2,  # text, metric undefined
    "best_angle_deg": 46.0,  # Fig. 11 and text
    "range_beyond_300mm_pct": 1.4,  # at 46 deg, Fig. 12 and text
    "shape_40deg_350mm_pct": {"cylindrical": 4.36, "conical": 1.4},  # Fig. 14 and text
}


def metrics(profile):
    mx, mn = profile.max(), profile.min()
    w = np.diff(np.concatenate(([0.0], 0.5 * (RHO[1:] + RHO[:-1]), [WAFER_RADIUS])) ** 2)
    mean = np.sum(w * profile) / np.sum(w)
    return {"centre_to_edge": profile[-1] / profile[0],
            "range_over_min_pct": 100 * (mx - mn) / mn,
            "range_over_mean_pct": 100 * (mx - mn) / mean,
            "half_range_pct": 100 * (mx - mn) / (2 * mean)}


def profile(events, angle_deg, distance):
    wafer = Wafer(radius=WAFER_RADIUS)
    src = crucible_source_on_cone("CdTe", wafer, events, throw=distance,
                                  polar_angle=np.radians(angle_deg), azimuth=0.0, emission_rate=1.0)
    return rotation_averaged_flux([src], wafer, RHO, n_angles=N_ANGLES)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--particles", type=int, default=100_000)
    ap.add_argument("--out", default="results/r14_comparison")
    args = ap.parse_args()
    out = {}

    cyl = {depth: simulate(Crucible(BORE_RADIUS, depth), args.particles, rng=1)
           for depth in (0.034, 0.030)}
    cyl_b = simulate(Crucible(BORE_RADIUS, 0.034), args.particles, rng=2)  # independent seed
    half_angle = np.radians(7.0)
    cone = simulate(Crucible(BORE_RADIUS, 0.030,
                             melt_radius=BORE_RADIUS - 0.030 * np.tan(half_angle)),
                    args.particles, rng=3)
    print(f"Transmission: cylinder melt 34 mm {cyl[0.034].transmission:.3f}, "
          f"30 mm {cyl[0.030].transmission:.3f}; conical {cone.transmission:.3f}\n")

    print("Base case 35 deg / 350 mm (R14: centre-to-edge %.3f, 'non-uniformity' %.1f%%)"
          % (R14["base_35deg_350mm_centre_to_edge"], R14["base_35deg_350mm_nonuniformity_pct"]))
    base = {}
    for label, ev in (("melt 34 mm", cyl[0.034]), ("melt 34 mm, seed 2", cyl_b),
                      ("melt 30 mm", cyl[0.030])):
        base[label] = metrics(profile(ev, 35.0, 0.35))
        m = base[label]
        print(f"  {label:20s} centre-to-edge {m['centre_to_edge']:.3f}  range/min "
              f"{m['range_over_min_pct']:.2f}%  range/mean {m['range_over_mean_pct']:.2f}%  "
              f"half-range {m['half_range_pct']:.2f}%")
    out["base"] = base

    angles = np.arange(20.0, 61.0, 2.0)
    scan = [metrics(profile(cyl[0.034], a, 0.35))["range_over_mean_pct"] for a in angles]
    best = float(angles[int(np.argmin(scan))])
    print(f"\nAngle scan at 350 mm, range/mean %: best at {best:.0f} deg (R14: 46 deg)")
    print("  " + "  ".join(f"{a:.0f}:{s:.2f}" for a, s in zip(angles, scan)))
    out["angle_scan"] = {"angles_deg": angles, "range_over_mean_pct": scan, "best_deg": best}

    distances = np.array([0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5])
    dscan = [metrics(profile(cyl[0.034], 46.0, d))["range_over_mean_pct"] for d in distances]
    print("\nDistance scan at 46 deg, range/mean % (R14: below 1.4% beyond 300 mm)")
    print("  " + "  ".join(f"{1000 * d:.0f}:{s:.2f}" for d, s in zip(distances, dscan)))
    out["distance_scan"] = {"distances_m": distances, "range_over_mean_pct": dscan}

    shape = {"cylindrical": metrics(profile(cyl[0.030], 40.0, 0.35)),
             "conical": metrics(profile(cone, 40.0, 0.35))}
    print("\nCrucible shape at 40 deg / 350 mm, range/mean % (R14: cylindrical 4.36, conical 1.4)")
    for k, m in shape.items():
        print(f"  {k:12s} {m['range_over_mean_pct']:.2f}%  (range/min {m['range_over_min_pct']:.2f}%)")
    out["shape"] = shape

    manifest = build_manifest(
        "r14_comparison", label="representative_chamber", validation_status="not_validated",
        inputs={"particles": args.particles, "wafer_radius_m": WAFER_RADIUS,
                "bore_radius_m": BORE_RADIUS, "n_angles": N_ANGLES, "n_radii": len(RHO),
                "r14_reference_values": R14},
        outputs=out,
        warnings=["R14 is a simulation: code-to-code corroboration only",
                  "R14 reference values read from figures/text; its metric is undefined",
                  "Melt surface modelled perpendicular to the crucible axis (not horizontal)"],
        disabled_physics=["intermolecular collisions", "melt tilt", "wall sticking/desorption"])
    print(f"\nWrote {write_manifest(manifest, Path(args.out) / 'manifest.json')}")


if __name__ == "__main__":
    main()
