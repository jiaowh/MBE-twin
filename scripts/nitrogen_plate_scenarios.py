"""Nitrogen aperture plates from R13 and R30: flow regime, geometric plausibility and wafer maps.

Review 3 (2026-09-30): scripts/nitrogen_plate.py is a sensitivity study with a fixed hole
radius, L/r up to 5 and normalized output, so it cannot simply be run for real plates. This
script takes the published hole counts and diameters and brackets what is not published:
- plates: R13 original (712 x 0.2032 mm) and modified (4000 x 0.2032 mm), both from the patent's
  aperture tables; R30 Veeco UNI-Bulb plate (about 2000 holes, #80 drill, 0.343 mm);
- plate thickness L 0.5 / 1 / 2 mm (machined PBN; not sourced), so L/r is 2.9-19.7;
- active plate radius 12.5 / 20 mm (hole pattern not published; hexagonal assumed);
- N2 flow 0.5 / 3 / 10 sccm (H02 lists 0.1-10 sccm), gas temperature 300 / 600 K.

Outputs, per plate and thickness:
1. Flow regime. Pressure behind the plate p = Q / C, with C = N (v_mean / 4) pi r^2 W(L/r)
   (free-molecular conductance; W from the crucible.py random walk) and the hole Knudsen
   number lambda / (2 r). Same method and N2 diameter bracket (3.7 A x/÷ 1.3, not sourced) as
   scripts/nitrogen_knudsen.py. Kn > 10: free-molecular model self-consistent; 0.1-10:
   transitional (the free-molecular hole beaming is not reliable); < 0.1: viscous.
   A free-molecular C gives the highest p (continuum conductance is larger), so Kn here is a
   lower bound on the true Kn only if the flow is actually free-molecular; in the
   transitional range it is an order-of-magnitude indicator.
2. Geometry. Open-area fraction and the web between neighbouring holes on a hexagonal pattern
   filling the active radius; webs below 0.1 mm are flagged as implausible to machine.
3. Free-molecular wafer map (range/mean over the 200 mm wafer, rotation-averaged, 350 mm
   throw, port angles 0-50 deg, plate aimed at the wafer centre, uniform hole output). The
   wafer is far from the plate, so the map depends on L/r and the plate extent, not on the
   hole count or the hole size (at 350 mm, 0.1 vs 0.17 mm is invisible); maps use a 0.1 mm
   hole radius at each L/r. The hole set is sampled on a coarse hexagonal grid (pitch R/4);
   halving the pitch is checked on the deepest, widest case, where the cost is highest.
   Hole-wall recombination is not modelled; it grows with L/r.

The total active-N output is not addressed (R10-R12, R18, commissioning). Maps are shape only.

Usage: python scripts/nitrogen_plate_scenarios.py [--particles 20000] [--out results/nitrogen_plate_scenarios]
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
from mbe_twin.units import K_B, N_A

ROOT = Path(__file__).resolve().parents[1]
PLATES = {  # name: (hole count, hole diameter m, source)
    "R13_original": (712, 0.2032e-3, "R13 (US 10,526,723) aperture table, PDF p. 9"),
    "R13_modified": (4000, 0.2032e-3, "R13 aperture table, PDF p. 9"),
    "R30_UNI-Bulb": (2000, 0.343e-3, "R30 (Clinton et al. 2019): about 2000 holes, #80 drill"),
}
THICKNESSES = (0.5e-3, 1.0e-3, 2.0e-3)
PLATE_RADII = (0.0125, 0.020)
FLOWS_SCCM = (0.5, 3.0, 10.0)
TEMPS_K = (300.0, 600.0)
THROW = 0.350
ANGLES_DEG = (0.0, 10.0, 20.0, 30.0, 40.0, 50.0)
WAFER_RADIUS = 0.100
RHO = np.linspace(0.0, WAFER_RADIUS, 41)
SCCM_PA_M3_S = 101325.0 * 1e-6 / 60.0
N2_MASS = 28.0134e-3 / N_A
D_N2 = 3.7e-10
MIN_WEB = 0.1e-3
MAP_HOLE_RADIUS = 0.1e-3  # hole radius for the wafer maps (shape depends on L/r only)


def hex_pitch(n_holes, plate_radius):
    """Pitch of a hexagonal pattern putting n_holes inside a disc of plate_radius."""
    return float(np.sqrt(2.0 * np.pi * plate_radius ** 2 / (np.sqrt(3.0) * n_holes)))


def knudsen(n_holes, r, transmission, q_sccm, t, d_factor=1.0):
    v = np.sqrt(8 * K_B * t / (np.pi * N2_MASS))
    conductance = n_holes * v / 4 * np.pi * r * r * transmission
    p = q_sccm * SCCM_PA_M3_S * (t / 273.15) / conductance  # sccm defined at 273.15 K
    lam = K_B * t / (np.sqrt(2) * np.pi * (D_N2 * d_factor) ** 2 * p)
    return p, lam / (2 * r)


def range_over_mean(prof):
    s = radial_uniformity(prof, RHO, WAFER_RADIUS)
    return 100.0 * (s["max"] - s["min"]) / s["mean"]


def wafer_map(events, plate_radius, pitch, wafer):
    holes = hex_holes(plate_radius, pitch)
    vals = []
    for angle in ANGLES_DEG:
        src = aperture_plate_sources("N", wafer, events, holes, throw=THROW, polar_angle=np.radians(angle),
                                     azimuth=0.0, total_rate=1.0)
        vals.append(range_over_mean(rotation_averaged_flux(src, wafer, RHO, n_angles=36)))
    return vals, len(holes)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--particles", type=int, default=20_000)
    ap.add_argument("--out", default="results/nitrogen_plate_scenarios")
    args = ap.parse_args()
    wafer = Wafer(radius=WAFER_RADIUS)

    aspects = sorted({round(L / (d / 2), 3) for (_, d, _), L in itertools.product(PLATES.values(), THICKNESSES)})
    events = {a: simulate(Crucible(MAP_HOLE_RADIUS, a * MAP_HOLE_RADIUS), args.particles, rng=60 + i)
              for i, a in enumerate(aspects)}
    print("hole transmission W(L/r): " + ", ".join(f"{a:.2f}: {events[a].transmission:.4f}" for a in aspects))

    regime, geometry, maps = [], [], []
    print("\n1. Flow regime: hole Kn = lambda/(2r) (N2 d x1.3 / x1 / /1.3); p behind the plate")
    print(f"{'plate':14s} {'L mm':>5s} {'L/r':>6s} {'sccm':>5s} {'T K':>4s} {'p Pa':>8s}  Kn")
    for (name, (n, d, _)), L in itertools.product(PLATES.items(), THICKNESSES):
        a = round(L / (d / 2), 3)
        for q, t in itertools.product(FLOWS_SCCM, TEMPS_K):
            p, _ = knudsen(n, d / 2, events[a].transmission, q, t)
            kn = [knudsen(n, d / 2, events[a].transmission, q, t, f)[1] for f in (1.3, 1.0, 1 / 1.3)]
            regime.append({"plate": name, "L_m": L, "L_over_r": a, "flow_sccm": q, "T_K": t, "p_Pa": p,
                           "Kn_d_x1.3_x1_div1.3": kn})
            print(f"{name:14s} {1e3 * L:5.1f} {a:6.2f} {q:5.1f} {t:4.0f} {p:8.3g}  "
                  + " / ".join(f"{k:.3g}" for k in kn))

    print("\n2. Geometry (hexagonal pattern filling the active radius)")
    for (name, (n, d, _)), R in itertools.product(PLATES.items(), PLATE_RADII):
        pitch = hex_pitch(n, R)
        web = pitch - d
        open_frac = n * (d / 2) ** 2 / R ** 2
        geometry.append({"plate": name, "plate_radius_m": R, "pitch_m": pitch, "web_m": web,
                         "open_fraction": open_frac, "plausible": web >= MIN_WEB})
        print(f"{name:14s} R {1e3 * R:4.1f} mm: pitch {1e3 * pitch:.3f} mm, web {1e3 * web:.3f} mm, "
              f"open {100 * open_frac:4.1f} %{'' if web >= MIN_WEB else '  <- web < 0.1 mm, implausible'}")

    print("\n3. Free-molecular range/mean % over 200 mm, 350 mm throw, by port angle "
          + " ".join(f"{a:5.0f}" for a in ANGLES_DEG))
    for a, R in itertools.product(aspects, PLATE_RADII):
        vals, n_sampled = wafer_map(events[a], R, R / 4.0, wafer)
        row = {"L_over_r": a, "plate_radius_m": R, "sampled_holes": n_sampled, "angles_deg": ANGLES_DEG,
               "range_over_mean_pct": vals}
        if R == PLATE_RADII[-1] and a == aspects[-1]:  # hole-sampling convergence, costliest case
            fine, n_fine = wafer_map(events[a], R, R / 8.0, wafer)
            row.update({"half_pitch_range_over_mean_pct": fine, "half_pitch_sampled_holes": n_fine,
                        "max_abs_change_points": float(np.max(np.abs(np.subtract(fine, vals))))})
        maps.append(row)
        extra = f"  (half pitch: max change {row['max_abs_change_points']:.2f} points)" if "max_abs_change_points" in row else ""
        print(f"  L/r {a:6.2f} plate R {1e3 * R:4.1f} mm ({n_sampled:3d} holes sampled) "
              + " ".join(f"{v:5.1f}" for v in vals) + extra)

    manifest = build_manifest(
        "nitrogen_plate_scenarios", label="representative_chamber", validation_status="not_validated",
        inputs={"particles": args.particles, "plates": {k: {"holes": v[0], "diameter_m": v[1], "source": v[2]}
                                                        for k, v in PLATES.items()},
                "thicknesses_m": THICKNESSES, "plate_radii_m": PLATE_RADII, "flows_sccm": FLOWS_SCCM,
                "temperatures_K": TEMPS_K, "throw_m": THROW, "angles_deg": ANGLES_DEG,
                "n2_diameter_m": D_N2},
        outputs={"transmission": {str(a): events[a].transmission for a in aspects},
                 "flow_regime": regime, "geometry": geometry, "wafer_maps": maps},
        sources=[Path(__file__), ROOT / "src/mbe_twin/aperture.py", ROOT / "src/mbe_twin/beam.py",
                 ROOT / "src/mbe_twin/crucible.py"],
        warnings=["Plate thickness, active radius and hole pattern are not published: bracketed",
                  "N2 hard-sphere diameter not sourced (bracketed x/÷ 1.3)",
                  "Wafer maps are free-molecular; not valid where the hole Kn is below about 10",
                  "Hole-wall recombination, ions and plume collisions not modelled; shape only"],
        disabled_physics=["plasma chemistry", "wall recombination", "ion species", "transitional hole flow"])
    print(f"Wrote {write_manifest(manifest, Path(args.out) / 'manifest.json')}")


if __name__ == "__main__":
    main()
