"""Robustness of the nitrogen aim optima to the plate's output profile and active radius.

The aim-offset / port-angle optima (scripts/nitrogen_aim_study.py) assume uniform output from a
20 mm active radius. The discharge is not known to be uniform, and the active radius is not
published. At each optimum (aim, angle) from results/nitrogen_aim_study*/manifest.json this
recomputes the 200 mm range/mean with:
- centre-peaked output 1 - 0.5 (r/R)^2 and edge-peaked 1 + 0.5 (r/R)^2 (the brackets of
  scripts/nitrogen_plate.py);
- active radius 12.5 mm (uniform output), aim and angle unchanged;
- a re-optimized aim (5 mm steps, +/-20 mm) for the 12.5 mm plate.
Free-molecular straight holes, 350 mm throw, hole pitch R/2 (converged, see the scenario study).

Usage: python scripts/nitrogen_aim_robustness.py [--particles 20000] [--out results/nitrogen_aim_robustness]
"""

import argparse
import json
from pathlib import Path

import numpy as np

from mbe_twin.aperture import aperture_plate_sources, hex_holes
from mbe_twin.beam import Wafer, rotation_averaged_flux
from mbe_twin.crucible import Crucible, simulate
from mbe_twin.manifest import build_manifest, write_manifest
from mbe_twin.metrics import radial_uniformity

ROOT = Path(__file__).resolve().parents[1]
AIM = [ROOT / "results/nitrogen_aim_study/manifest.json", ROOT / "results/nitrogen_aim_study_ext/manifest.json"]
WAFER_RADIUS = 0.100
HOLE_RADIUS = 0.1e-3
THROW = 0.350
RHO = np.linspace(0.0, WAFER_RADIUS, 41)
PROFILES = {"uniform": None, "centre-peaked": lambda r, R: 1.0 - 0.5 * (r / R) ** 2,
            "edge-peaked": lambda r, R: 1.0 + 0.5 * (r / R) ** 2}


def rom(events, plate_r, offset_mm, angle, wafer, profile=None):
    holes = hex_holes(plate_r, plate_r / 2.0)
    prof = None if profile is None else (lambda r, f=profile, R=plate_r: f(r, R))
    src = aperture_plate_sources("N", wafer, events, holes, throw=THROW, polar_angle=np.radians(angle), azimuth=0.0,
                                 total_rate=1.0, profile=prof, aim_offset=offset_mm / 1e3)
    s = radial_uniformity(rotation_averaged_flux(src, wafer, RHO, n_angles=36), RHO, WAFER_RADIUS)
    return float(100.0 * (s["max"] - s["min"]) / s["mean"])


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--particles", type=int, default=20_000)
    ap.add_argument("--out", default="results/nitrogen_aim_robustness")
    args = ap.parse_args()
    best = {}
    for path in AIM:
        for r in json.loads(path.read_text(encoding="utf-8"))["outputs"]["rows"]:
            a = r["L_over_r"]
            if a not in best or r["best"]["range_over_mean_pct"] < best[a]["range_over_mean_pct"]:
                best[a] = r["best"]
    wafer = Wafer(radius=WAFER_RADIUS)
    rows = []
    print("range/mean % at each optimum: uniform 20 mm / centre-peaked / edge-peaked / 12.5 mm plate "
          "/ 12.5 mm re-aimed (offset)")
    for i, (a, b) in enumerate(sorted(best.items())):
        ev = simulate(Crucible(HOLE_RADIUS, a * HOLE_RADIUS), args.particles, rng=80 + i)
        vals = {name: rom(ev, 0.020, b["offset_mm"], b["angle_deg"], wafer, f) for name, f in PROFILES.items()}
        vals["plate 12.5 mm"] = rom(ev, 0.0125, b["offset_mm"], b["angle_deg"], wafer)
        offs = np.arange(b["offset_mm"] - 20, b["offset_mm"] + 21, 5)
        re = [rom(ev, 0.0125, o, b["angle_deg"], wafer) for o in offs]
        k = int(np.argmin(re))
        vals["plate 12.5 mm re-aimed"] = re[k]
        rows.append({"L_over_r": a, "optimum": b, "range_over_mean_pct": vals, "reaimed_offset_mm": float(offs[k])})
        print(f"  L/r {a:5.2f} ({b['offset_mm']:+.0f} mm, {b['angle_deg']:.0f} deg): "
              + " / ".join(f"{v:.2f}" for v in vals.values()) + f" ({offs[k]:+.0f} mm)", flush=True)
    manifest = build_manifest(
        "nitrogen_aim_robustness", label="representative_chamber", validation_status="not_validated",
        inputs={"particles": args.particles, "optima_from": [str(p.relative_to(ROOT)) for p in AIM],
                "profiles": list(PROFILES), "throw_m": THROW},
        outputs={"rows": rows},
        sources=[Path(__file__), ROOT / "src/mbe_twin/aperture.py", ROOT / "src/mbe_twin/beam.py",
                 ROOT / "src/mbe_twin/crucible.py"],
        warnings=["Free-molecular straight holes; output profiles are brackets, not measured"],
        disabled_physics=["plasma chemistry", "wall recombination", "transitional hole flow"])
    print(f"Wrote {write_manifest(manifest, Path(args.out) / 'manifest.json')}")


if __name__ == "__main__":
    main()
