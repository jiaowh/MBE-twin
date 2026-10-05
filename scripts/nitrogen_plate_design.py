"""Aperture-plate designs that keep the holes free-molecular at the feed a 200 mm wafer needs.

The layout studies assume free-molecular holes (Kn = lambda / d_hole >= 10, the criterion of
scripts/nitrogen_plate_scenarios.py). For the leading plate (R30 hole set in 0.5 mm) that holds
only up to 5.9 sccm with the conservative N2 diameter (x1.3) at 300 K, below what 1 um/h needs
at realistic conversion. Kn scales as N d W(L/r) / Q (N holes of diameter d, transmission W,
feed Q), so more or larger holes raise the flow limit. Two other limits bound the design:
- the discharge must stay in its bright mode: R26 reports the original 712-hole plate going dim
  above 3.25 sccm from back pressure, and the 5.6x higher-conductance plate needing at least
  3 sccm to stay lit and staying bright to 34 sccm. Expressed as the free-molecular pressure
  behind each plate, that is a bracket for the bright-mode window (computed here, reported);
- machinability: the web between neighbouring holes on a hexagonal pattern filling the active
  radius must be at least 0.1 mm (nitrogen_plate_scenarios.py).
Also reported: L/r, which sets the beam shape (the layout studies use 2.92; deeper holes beam
more and are harder to even out).

Grid: hole diameter 0.2-0.6 mm, hole count 500-16000, plate thickness 0.5 / 1 mm, active radius
20 mm (as the layout studies) and 30 mm (a larger plate; changes the map, not checked here); gas at 300 and 600 K; N2 diameter x1 and x1.3. Output: per design the highest feed at
which the smallest Kn is 10, the pressure-window check at that feed, and the feasible designs
that reach 20 and 35 sccm.

Usage: python scripts/nitrogen_plate_design.py
"""

import itertools
from pathlib import Path

import numpy as np

from mbe_twin.crucible import Crucible, simulate
from mbe_twin.manifest import build_manifest, write_manifest
from mbe_twin.units import K_B, N_A

ROOT = Path(__file__).resolve().parents[1]
SCCM = 101325.0 * 1e-6 / 60.0
M_N2 = 28.0134e-3 / N_A
D_N2 = 3.7e-10
ACTIVE_RADII = (0.020, 0.030)   # 20 mm as the layout studies; 30 mm a larger plate (not sourced)
MIN_WEB = 0.1e-3
DIAMETERS_MM = (0.2032, 0.25, 0.3, 0.343, 0.4, 0.5, 0.6)
COUNTS = (500, 712, 1000, 2000, 3000, 4000, 6000, 8000)
THICK_MM = (0.5, 1.0)
REFERENCE = {"R13_original": (712, 0.2032), "R13_modified": (4000, 0.2032), "R30": (2000, 0.343)}
KN_VALID = 10.0


def conductance(n, d, w, t):
    v = np.sqrt(8 * K_B * t / (np.pi * M_N2))
    return n * v / 4 * np.pi * (d / 2) ** 2 * w          # m^3/s


def pressure(q_sccm, n, d, w, t):
    return q_sccm * SCCM * (t / 273.15) / conductance(n, d, w, t)


def knudsen(q_sccm, n, d, w, t, f=1.0):
    lam = K_B * t / (np.sqrt(2) * np.pi * (D_N2 * f) ** 2 * pressure(q_sccm, n, d, w, t))
    return lam / d


def feed_at_kn(n, d, w, t, f):
    return float(knudsen(1.0, n, d, w, t, f) / KN_VALID)   # Kn is inversely proportional to the feed


def web(n, d, radius):
    pitch = np.sqrt(2 * np.pi * radius ** 2 / (np.sqrt(3) * n))
    return pitch - d


def main():
    trans = {}
    aspects = sorted({round(2 * t / dd, 3) for t in THICK_MM for dd in DIAMETERS_MM} |
                     {round(2 * t / REFERENCE[k][1], 3) for t in THICK_MM for k in REFERENCE})
    for a in aspects:
        trans[a] = simulate(Crucible(1.0, a), 100_000, rng=5, record_events=False).transmission
    # bright-mode window from R26, as free-molecular pressures behind the published plates (300 K, plates 0.5-1 mm)
    window = {}
    for t_mm in THICK_MM:
        n0, d0 = REFERENCE["R13_original"]
        n1, d1 = REFERENCE["R13_modified"]
        w0, w1 = trans[round(2 * t_mm / d0, 3)], trans[round(2 * t_mm / d1, 3)]
        window[f"{t_mm:g} mm"] = {
            "dim_above_Pa (712 holes at 3.25 sccm)": pressure(3.25, n0, d0 * 1e-3, w0, 300.0),
            "lit_down_to_Pa (4000 holes at 3 sccm)": pressure(3.0, n1, d1 * 1e-3, w1, 300.0),
            "bright_up_to_Pa (4000 holes at 34 sccm)": pressure(34.0, n1, d1 * 1e-3, w1, 300.0)}
    print("bright-mode evidence as free-molecular pressure behind the plate (300 K):")
    for k, v in window.items():
        print(f"  {k}: " + ", ".join(f"{a} {b:.2f}" for a, b in v.items()))
    print("note: 4000 holes stayed bright at a higher computed pressure than the 712-hole plate went dim at; the window "
          "is not a single pressure (hole count and discharge geometry matter), so it is reported, not imposed")

    rows = []
    for (n, d_mm, t_mm, radius) in itertools.product(COUNTS + (12000, 16000), DIAMETERS_MM, THICK_MM, ACTIVE_RADII):
        d = d_mm * 1e-3
        a = round(2 * t_mm / d_mm, 3)
        w = trans[a]
        wb = web(n, d, radius)
        q_cons = min(feed_at_kn(n, d, w, t, 1.3) for t in (300.0, 600.0))
        q_nom = feed_at_kn(n, d, w, 300.0, 1.0)
        rows.append({"holes": n, "hole_diameter_mm": d_mm, "thickness_mm": t_mm, "active_radius_mm": 1e3 * radius, "L_over_r": a, "transmission": w,
                     "conductance_L_s_300K": 1e3 * conductance(n, d, w, 300.0), "web_mm": 1e3 * wb,
                     "machinable": bool(wb >= MIN_WEB), "open_area_fraction": n * (d / 2) ** 2 / radius ** 2,
                     "feed_at_kn10_sccm": {"conservative (d x1.3, 300 K)": q_cons, "nominal (d x1, 300 K)": q_nom},
                     "pressure_behind_Pa_at_feed": {f"{q:g}": pressure(q, n, d, w, 300.0) for q in (5.0, 10.0, 20.0, 35.0)}})
    for k, (n, d_mm) in REFERENCE.items():
        for t_mm in THICK_MM:
            r = next(x for x in rows if x["holes"] == n and abs(x["hole_diameter_mm"] - d_mm) < 1e-9 and x["thickness_mm"] == t_mm
                     and x["active_radius_mm"] == 20.0) \
                if d_mm in DIAMETERS_MM and n in COUNTS else None
            if r:
                print(f"{k:13s} {t_mm:g} mm (L/r {r['L_over_r']:.2f}): Kn >= 10 up to {r['feed_at_kn10_sccm']['conservative (d x1.3, 300 K)']:.1f} "
                      f"(conservative) / {r['feed_at_kn10_sccm']['nominal (d x1, 300 K)']:.1f} sccm (nominal); web {r['web_mm']:.2f} mm")
    best = {}
    for target in (10.0, 20.0, 35.0):
        ok = [r for r in rows if r["machinable"] and r["feed_at_kn10_sccm"]["conservative (d x1.3, 300 K)"] >= target]
        ok.sort(key=lambda r: (r["L_over_r"], r["holes"]))
        best[f"{target:g}"] = ok[:8]
        print(f"\nmachinable plates free-molecular (conservative) up to {target:g} sccm, shallowest first: {len(ok)}")
        for r in ok[:8]:
            print(f"  {r['holes']:5d} x {r['hole_diameter_mm']:.3f} mm in {r['thickness_mm']:g} mm, R {r['active_radius_mm']:g} mm: L/r {r['L_over_r']:.2f}, "
                  f"web {r['web_mm']:.2f} mm, {r['conductance_L_s_300K']:.0f} L/s, p behind at {target:g} sccm "
                  f"{r['pressure_behind_Pa_at_feed'].get(f'{target:g}', float('nan')):.2f} Pa")
    manifest = build_manifest(
        "nitrogen_plate_design", label="representative_chamber", validation_status="not_validated",
        inputs={"diameters_mm": DIAMETERS_MM, "counts": COUNTS, "thickness_mm": THICK_MM, "active_radii_m": ACTIVE_RADII,
                "min_web_m": MIN_WEB, "kn_valid": KN_VALID, "reference_plates": REFERENCE},
        outputs={"bright_mode_evidence_Pa": window, "designs": rows, "best": best},
        sources=[Path(__file__), ROOT / "src/mbe_twin/crucible.py", ROOT / "src/mbe_twin/units.py"],
        warnings=["Free-molecular conductance with straight holes; transitional flow not modelled (that is what Kn checks)",
                  "Bright-mode window from two published plates only; it depends on the discharge, not only on pressure",
                  "Hole-wall recombination grows with L/r and is not modelled"])
    print(f"Wrote {write_manifest(manifest, ROOT / 'results/nitrogen_plate_design/manifest.json')}")


if __name__ == "__main__":
    main()
