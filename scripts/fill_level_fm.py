"""Free-molecular fill-level sensitivity of a tilted source on a rotating wafer.

Geometry: R14's cylindrical crucible (71.5 mm bore), orifice 350 mm from the wafer centre,
axis aimed at the centre, port angle measured from the wafer normal. The wafer faces down
and gravity points away from it, so "up" is along the wafer's outward normal.

Two melt models:
- axis-normal: the melt plane is perpendicular to the crucible axis (as in R14 and the
  first study, REFERENCE_CHAMBER.md, 2026-09-29). Every recess is geometrically allowed.
- level: the liquid stays horizontal. At port angle a, a bore of radius R holds a level
  melt only if its recess on the axis is at least R tan(a) (37.0 mm at 46 deg); shallower
  fills would spill and are reported as inadmissible.

Metrics: range/mean (%) over the whole wafer, the original definition, plus the area-weighted
standard deviation (%). Wafers: exact 8 inch (101.6 mm radius, as in the first study) and
200 mm. This is the free-molecular limit only: collisions inside production Ga cells change
the profiles (R07), in a direction that has to be computed, not assumed.

Usage: python scripts/fill_level_fm.py [--particles 100000] [--out results/fill_level_fm]
"""

import argparse
from pathlib import Path

import numpy as np

from mbe_twin.beam import Wafer, crucible_source_on_cone, level_melt_normal, rotation_averaged_flux
from mbe_twin.crucible import Crucible, simulate
from mbe_twin.manifest import build_manifest, write_manifest
from mbe_twin.metrics import radial_uniformity

BORE_RADIUS = 0.03575
THROW = 0.35
WAFERS = {"8inch": 0.1016, "200mm": 0.100}
N_RADII, N_ANGLES = 41, 72
AXIS_NORMAL_RECESS = (0.0, 0.034, 0.070, 0.120)  # the first study's fills
LEVEL_RECESS = (0.040, 0.050, 0.070, 0.095, 0.120)
ANGLES_DEG = np.arange(36.0, 64.1, 2.0)


def min_level_recess(angle_deg, radius=BORE_RADIUS):
    return radius * np.tan(np.radians(angle_deg))


def events_for(recess, angle_deg, model, particles, seed):
    """Random-walk events for one fill, or None when a level melt would spill."""
    normal = (0.0, 0.0, 1.0)
    if model == "level":
        if recess < min_level_recess(angle_deg):
            return None
        wafer = Wafer(radius=0.1)
        ref = crucible_source_on_cone("x", wafer, None, throw=THROW, polar_angle=np.radians(angle_deg),
                                      azimuth=0.0, emission_rate=1.0)
        normal = level_melt_normal(ref.axis, up=tuple(-np.asarray(wafer.normal)))
    return simulate(Crucible(BORE_RADIUS, recess, melt_normal=normal), particles, rng=seed)


def uniformity(events, angle_deg, radius):
    wafer = Wafer(radius=radius)
    src = crucible_source_on_cone("Ga", wafer, events, throw=THROW, polar_angle=np.radians(angle_deg),
                                  azimuth=0.0, emission_rate=1.0)
    rho = np.linspace(0.0, radius, N_RADII)
    prof = rotation_averaged_flux([src], wafer, rho, n_angles=N_ANGLES)
    s = radial_uniformity(prof, rho, radius)
    return {"range_over_mean_pct": 100 * (s["max"] - s["min"]) / s["mean"], "std_pct": s["std_pct"],
            "mean_per_emitted": s["mean"]}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--particles", type=int, default=100_000)
    ap.add_argument("--out", default="results/fill_level_fm")
    args = ap.parse_args()
    out = {"min_level_recess_mm_at_46deg": 1e3 * min_level_recess(46.0)}
    print(f"Level melt needs a recess >= {out['min_level_recess_mm_at_46deg']:.1f} mm at 46 deg "
          f"(bore {2e3 * BORE_RADIUS:.1f} mm)\n")

    for model, fills in (("axis-normal", AXIS_NORMAL_RECESS), ("level", LEVEL_RECESS)):
        rows = []
        print(f"{model} melt, 350 mm throw: 46 deg metrics | best angle by range/mean (8 inch)")
        print("  recess  T      8in r/m%  200mm r/m%  200mm std%  best-angle  r/m% there")
        for k, recess in enumerate(fills):
            ev46 = events_for(recess, 46.0, model, args.particles, 100 + k)
            if ev46 is None:
                print(f"  {1e3 * recess:5.0f}  spills at 46 deg")
                continue
            m = {w: uniformity(ev46, 46.0, r) for w, r in WAFERS.items()}
            scan = []
            for a in ANGLES_DEG:
                # a level melt depends on the port angle, so it needs its own events
                ev = ev46 if (model == "axis-normal" or a == 46.0) else \
                    events_for(recess, a, model, args.particles // 2, 1000 + k)
                scan.append(np.nan if ev is None else uniformity(ev, a, WAFERS["8inch"])["range_over_mean_pct"])
            scan = np.array(scan)
            best = float(ANGLES_DEG[np.nanargmin(scan)])
            rows.append({"recess_m": recess, "transmission": ev46.transmission, "at_46deg": m,
                         "angle_scan_deg": ANGLES_DEG, "angle_scan_range_over_mean_pct_8inch": scan,
                         "best_angle_deg": best})
            print(f"  {1e3 * recess:5.0f}  {ev46.transmission:.3f}  {m['8inch']['range_over_mean_pct']:8.2f}"
                  f"  {m['200mm']['range_over_mean_pct']:10.2f}  {m['200mm']['std_pct']:10.2f}"
                  f"  {best:10.0f}  {np.nanmin(scan):9.2f}")
        out[model] = rows
        print()

    manifest = build_manifest(
        "fill_level_fm", label="representative_chamber", validation_status="not_validated",
        inputs={"particles": args.particles, "bore_radius_m": BORE_RADIUS, "throw_m": THROW,
                "wafers_radius_m": WAFERS, "n_radii": N_RADII, "n_angles": N_ANGLES,
                "axis_normal_recess_m": AXIS_NORMAL_RECESS, "level_recess_m": LEVEL_RECESS},
        outputs=out, sources=[Path(__file__), Path(__file__).parents[1] / "src/mbe_twin/crucible.py",
                              Path(__file__).parents[1] / "src/mbe_twin/beam.py"],
        warnings=["Free-molecular limit: in-crucible collisions neglected (collisional at GaN rates)",
                  "Sensitivity study on a representative geometry, not a machine prediction",
                  "Axis-normal melts shallower than R tan(angle) are not physical for a liquid"],
        disabled_physics=["intermolecular collisions", "wall sticking/desorption", "melt meniscus"])
    print(f"Wrote {write_manifest(manifest, Path(args.out) / 'manifest.json')}")


if __name__ == "__main__":
    main()
