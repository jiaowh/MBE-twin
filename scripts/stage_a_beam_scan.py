"""Stage A design scan: rotation-averaged direct-beam uniformity over a 200 mm wafer.

Representative chamber only (ref/notes/REFERENCE_CHAMBER.md). Throw, port angle, aim and
cosine exponent are design variables with proposed ranges, not vendor values. The result
compares geometries for one source; it is not a thickness prediction for the proposed
machine. Excluded physics: scattering, re-emission, gas collisions, sticking/desorption,
temperature dependence and shutter transients.

Usage: python scripts/stage_a_beam_scan.py [--out results/stage_a_beam_scan]
"""

import argparse
import csv
import itertools
import time
from pathlib import Path

import numpy as np

from mbe_twin.beam import Wafer, rotation_averaged_flux, source_on_cone
from mbe_twin.manifest import build_manifest, write_manifest
from mbe_twin.metrics import radial_uniformity

WAFER_RADIUS = 0.100  # m, 200 mm (user decision 2026-09-28)
EDGE_EXCLUSION = 0.003  # m, assumed; replace with the process edge-exclusion spec
APERTURE_RADIUS = 0.020  # m, assumed crucible opening
EMISSION_RATE = 1.0  # particles/s; results are reported per emitted particle
THROWS = (0.30, 0.40, 0.50, 0.60)  # m
POLAR_ANGLES_DEG = (20.0, 30.0, 40.0, 50.0)
COSINE_EXPONENTS = (1.0, 2.0, 3.0)
# m along the source azimuth from the wafer centre; positive aims toward the source side
AIM_OFFSETS = tuple(round(a, 3) for a in np.arange(-0.30, 0.5001, 0.025))
N_RADII = 41
N_ANGLES = 120


def evaluate(throw, polar_deg, n, aim, n_angles=N_ANGLES):
    wafer = Wafer(radius=WAFER_RADIUS)
    src = source_on_cone("Ga", wafer, throw=throw, polar_angle=np.radians(polar_deg), azimuth=0.0,
                         emission_rate=EMISSION_RATE, cosine_exponent=n,
                         aperture_radius=APERTURE_RADIUS, aim_offset=aim)
    rho = np.linspace(0.0, WAFER_RADIUS, N_RADII)
    profile = rotation_averaged_flux([src], wafer, rho, n_angles=n_angles)
    stats = radial_uniformity(profile, rho, WAFER_RADIUS, EDGE_EXCLUSION)
    usable_area = np.pi * (WAFER_RADIUS - EDGE_EXCLUSION) ** 2
    return {
        "throw_m": throw, "polar_angle_deg": polar_deg, "cosine_exponent": n, "aim_offset_m": aim,
        "half_range_pct": stats["half_range_pct"], "std_pct": stats["std_pct"],
        "collection_efficiency": stats["mean"] * usable_area / EMISSION_RATE,
        "center_to_edge": profile[0] / profile[rho <= WAFER_RADIUS - EDGE_EXCLUSION][-1],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="results/stage_a_beam_scan")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # Angular-resolution check on one case before trusting the scan.
    coarse = evaluate(0.4, 40.0, 2.0, -0.05)["half_range_pct"]
    fine = evaluate(0.4, 40.0, 2.0, -0.05, n_angles=720)["half_range_pct"]

    t0 = time.perf_counter()
    rows = [evaluate(*c) for c in itertools.product(THROWS, POLAR_ANGLES_DEG, COSINE_EXPONENTS,
                                                    AIM_OFFSETS)]
    elapsed = time.perf_counter() - t0

    csv_path = out / "scan.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    print(f"{len(rows)} geometries in {elapsed:.1f} s; angular check half-range "
          f"{coarse:.6f}% (120) vs {fine:.6f}% (720)\n")
    print("Best aim per throw/angle/exponent: half-range % over the usable 194 mm | efficiency")
    print("(* = best aim at the edge of the scanned range)")
    print("n    throw  " + "  ".join(f"{a:>13.0f}deg" for a in POLAR_ANGLES_DEG))
    best = {}
    for n in COSINE_EXPONENTS:
        for throw in THROWS:
            cells = []
            for ang in POLAR_ANGLES_DEG:
                cand = [r for r in rows if r["cosine_exponent"] == n and r["throw_m"] == throw
                        and r["polar_angle_deg"] == ang]
                b = min(cand, key=lambda r: r["half_range_pct"])
                best[(n, throw, ang)] = b
                pinned = "*" if b["aim_offset_m"] in (AIM_OFFSETS[0], AIM_OFFSETS[-1]) else " "
                cells.append(f"{b['half_range_pct']:6.2f}{pinned}| {100 * b['collection_efficiency']:4.1f}%")
            print(f"{n:<4.0f} {throw:5.2f}  " + "  ".join(f"{c:>16}" for c in cells))

    manifest = build_manifest(
        "stage_a_beam_scan",
        label="representative_chamber",
        inputs={"wafer_radius_m": WAFER_RADIUS, "edge_exclusion_m": EDGE_EXCLUSION,
                "aperture_radius_m": APERTURE_RADIUS, "throws_m": THROWS,
                "polar_angles_deg": POLAR_ANGLES_DEG, "cosine_exponents": COSINE_EXPONENTS,
                "aim_offsets_m": AIM_OFFSETS, "n_radii": N_RADII, "n_angles": N_ANGLES},
        outputs={"csv": csv_path.name, "n_geometries": len(rows), "elapsed_s": elapsed,
                 "angular_check_half_range_pct": {"n120": coarse, "n720": fine}},
        warnings=["Design variable ranges, edge exclusion and aperture radius are assumptions",
                  "Cosine exponent is not yet fitted to a measured crucible (R07 pending)"],
        disabled_physics=["scattering", "re-emission", "gas collisions", "sticking/desorption",
                          "temperature dependence", "shutter transients", "finite rotation"],
    )
    # Robustness: the crucible exponent is not yet measured and drifts with fill level, so tune
    # the aim for the middle exponent and evaluate the same geometry at the others.
    mid = COSINE_EXPONENTS[len(COSINE_EXPONENTS) // 2]
    print(f"\nAim tuned for n={mid:.0f}; half-range % if the crucible is actually n = "
          + " / ".join(f"{n:.0f}" for n in COSINE_EXPONENTS))
    print("throw  angle    aim  " + "  ".join(f"n={n:.0f}".rjust(6) for n in COSINE_EXPONENTS)
          + "   worst")
    robustness = []
    for throw in THROWS:
        for ang in POLAR_ANGLES_DEG:
            aim = best[(mid, throw, ang)]["aim_offset_m"]
            hr = [next(r["half_range_pct"] for r in rows if r["throw_m"] == throw
                       and r["polar_angle_deg"] == ang and r["cosine_exponent"] == n
                       and r["aim_offset_m"] == aim) for n in COSINE_EXPONENTS]
            robustness.append({"throw_m": throw, "polar_angle_deg": ang, "aim_offset_m": aim,
                               "half_range_pct_by_exponent": hr, "worst_half_range_pct": max(hr)})
            print(f"{throw:5.2f}  {ang:5.0f}  {aim:5.3f}  "
                  + "  ".join(f"{h:6.2f}" for h in hr) + f"  {max(hr):6.2f}")

    edge = sum(b["aim_offset_m"] in (AIM_OFFSETS[0], AIM_OFFSETS[-1]) for b in best.values())
    print(f"\n{edge} of {len(best)} best aims lie at the edge of the scanned range")
    manifest["outputs"]["robustness_aim_tuned_for_exponent"] = mid
    manifest["outputs"]["robustness"] = robustness
    manifest["outputs"]["best_aims_at_scan_edge"] = edge
    print(f"\nWrote {csv_path} and {write_manifest(manifest, out / 'manifest.json')}")


if __name__ == "__main__":
    main()
