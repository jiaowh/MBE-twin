"""Active-N map on the rotating 200 mm wafer from an aperture-plate source: sensitivity study.

Representative only (ref/notes/NITROGEN_BOUNDARY.md). No hole map or plate drawing of the
proposed source is available, so every plate parameter is bracketed:
- hole aspect L/r (plate thickness over hole radius): 0 (thin plate), 2, 5;
- active plate radius: 10 and 20 mm;
- radial output profile across the plate: uniform, centre-peaked 1 - 0.5 (r/R)^2,
  edge-peaked 1 + 0.5 (r/R)^2.
Throw: 267 mm (H02's typical 10.5 inch) and 350 mm; the plate axis aims at the wafer centre.
Metric: range/mean (%) of the rotation-averaged flux over the whole 200 mm wafer, reported
for port angles 0-50 deg. Hole-wall recombination and collisions in the plume are not
modelled. Hole pitch is coarse (the wafer does not resolve it); the checked quantity is the
map shape, which depends on the plate extent and the hole angular distribution.

Usage: python scripts/nitrogen_plate.py [--out results/nitrogen_plate]
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
HOLE_RADIUS = 0.0002
ASPECTS = (0.0, 2.0, 5.0)
PLATE_RADII = (0.010, 0.020)
PROFILES = {
    "uniform": None,
    "centre-peaked": lambda r, R: 1.0 - 0.5 * (r / R) ** 2,
    "edge-peaked": lambda r, R: 1.0 + 0.5 * (r / R) ** 2,
}
THROWS = (0.267, 0.350)
ANGLES_DEG = (0.0, 10.0, 20.0, 30.0, 40.0, 50.0)
RHO = np.linspace(0.0, WAFER_RADIUS, 41)


def range_over_mean(prof):
    s = radial_uniformity(prof, RHO, WAFER_RADIUS)
    return 100.0 * (s["max"] - s["min"]) / s["mean"]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--particles", type=int, default=20_000)
    ap.add_argument("--out", default="results/nitrogen_plate")
    args = ap.parse_args()
    wafer = Wafer(radius=WAFER_RADIUS)
    events = {a: simulate(Crucible(HOLE_RADIUS, a * HOLE_RADIUS), args.particles, rng=40 + i)
              for i, a in enumerate(ASPECTS)}
    rows = []
    print("range/mean % over 200 mm by port angle " + " ".join(f"{a:5.0f}" for a in ANGLES_DEG))
    for throw, aspect, plate_r, (pname, pfun) in itertools.product(THROWS, ASPECTS, PLATE_RADII,
                                                                    PROFILES.items()):
        holes = hex_holes(plate_r, plate_r / 4.0)
        profile = None if pfun is None else (lambda r, f=pfun, R=plate_r: f(r, R))
        vals = []
        for angle in ANGLES_DEG:
            src = aperture_plate_sources("N", wafer, events[aspect], holes, throw=throw,
                                         polar_angle=np.radians(angle), azimuth=0.0,
                                         total_rate=1.0, profile=profile)
            vals.append(range_over_mean(rotation_averaged_flux(src, wafer, RHO, n_angles=36)))
        rows.append({"throw_m": throw, "aspect_L_over_r": aspect, "plate_radius_m": plate_r,
                     "profile": pname, "transmission": events[aspect].transmission,
                     "angles_deg": ANGLES_DEG, "range_over_mean_pct": vals})
        print(f"  throw {1e3 * throw:3.0f} mm  L/r {aspect:3.0f}  plate {1e3 * plate_r:2.0f} mm  "
              f"{pname:13s}" + " ".join(f"{v:5.1f}" for v in vals))

    manifest = build_manifest(
        "nitrogen_plate", label="representative_chamber", validation_status="not_validated",
        inputs={"particles": args.particles, "hole_radius_m": HOLE_RADIUS, "aspects": ASPECTS,
                "plate_radii_m": PLATE_RADII, "profiles": list(PROFILES), "throws_m": THROWS,
                "angles_deg": ANGLES_DEG},
        outputs={"rows": rows},
        sources=[Path(__file__), ROOT / "src/mbe_twin/aperture.py", ROOT / "src/mbe_twin/beam.py",
                 ROOT / "src/mbe_twin/crucible.py"],
        warnings=["All plate parameters bracketed; no drawing of the proposed source",
                  "Hole-wall recombination, ions and plume collisions not modelled",
                  "Shape only: total active-N output needs R10-R12 and commissioning data"],
        disabled_physics=["plasma chemistry", "wall recombination", "ion species"])
    print(f"Wrote {write_manifest(manifest, Path(args.out) / 'manifest.json')}")


if __name__ == "__main__":
    main()
