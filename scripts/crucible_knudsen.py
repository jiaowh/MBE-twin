"""Collision regime inside Ga and Al crucibles at production rates, calibrated on R07.

Question: is the free-molecular crucible model valid for GaN/AlN growth on the 200 mm
representative chamber, or is a collisional (DSMC) crucible model needed?

Criterion (R07, Gericke 1991, Sec. 3 and conclusions): Bi profiles stop changing with source
temperature below 550 C, p = 4e-2 Pa, which R07 equates to Knudsen number lambda/D > 12
(D = 16.5 mm aperture). R07's measured states then span lambda/D = 12 (onset) down to
~0.1 (11 A/s, strongly flattened). The hard-sphere cross-section implied by R07's statement
is used as the reference sigma; metal-vapour cross-sections are not sourced, so results are
also given for sigma / 2 and sigma / 5.

Steps:
  1. R07 states: lambda/D for its stated (T, p) pairs.
  2. RIBER ABI anchor: "Ga @ 1 um/h" at a 950 C crucible for every ABI size (H03 product
     page); lambda/D over a range of apertures.
  3. Mass balance on the representative geometry (R14 cylinder, bore 71.5 mm, 350 mm throw,
     46 deg, fill recess 0-120 mm): growth rate -> wafer-centre metal flux -> melt emission
     (free-molecular crucible model) -> saturation pressure -> melt temperature (Alcock
     1984) -> lambda/D. Collisions alter the transmission, so this is an order-of-magnitude
     estimate; p doubles every ~40-60 K, so the temperature is insensitive to that error.

Usage: python scripts/crucible_knudsen.py [--particles 60000] [--out results/crucible_knudsen]
"""

import argparse
from pathlib import Path

import numpy as np

from mbe_twin.crucible import Crucible, next_event_flux, simulate
from mbe_twin.manifest import build_manifest, write_manifest
from mbe_twin.units import N_A, celsius_to_kelvin, kelvin_to_celsius
from mbe_twin.vapour import (atomic_mass_kg, cross_section_from_knudsen, evaporation_flux,
                             mean_free_path, temperature_for_pressure, vapour_pressure)

# R07 (Gericke et al., Vacuum 42 (1991) 1209).
R07_D = 0.0165
R07_THRESHOLD = {"T_C": 550.0, "p_Pa": 4e-2, "knudsen": 12.0}  # Sec. 3 / conclusions
R07_STATED = [  # (label, T_C, p_Pa as stated by R07)
    ("threshold, ~0.2 A/s", 550.0, 4e-2),
    ("Figs. 2b/3/4, 573 C, 0.35 A/s", 573.0, 8e-2),
    ("Figs. 2a/4, 723 C, 11 A/s", 723.0, 4.0),
]
# States whose pressure R07 does not give: interpolated with a Clausius-Clapeyron fit
# (log p = a - b/T) through the stated points.
R07_INTERPOLATED = [
    ("Fig. 5 upper, 499 C, 0.07 A/s", 499.0),
    ("Fig. 4, 666 C, 3.5 A/s", 666.0),
]
# Normalized-profile RMS of the free-molecular model against R07's L/D = 4 series
# (scripts/compare_r07.py), to read collisionality as profile error.
R07_L4_MODEL_RMS = {573.0: 0.042, 666.0: 0.142, 723.0: 0.212}

# Metal atoms per m^3 of film. Lattice route (Wikipedia infoboxes: GaN a 318.9 pm, c 518.6 pm,
# Levinshtein 2001; AlN a 311.17 pm, c 497.88 pm, Vurgaftman 2003; GaAs a 565.315 pm) and
# density route (CRC: GaN 6.1, AlN 3.255, GaAs 5.3176 g/cm^3) agree within 0.3 %.
def _wurtzite(a, c):
    return 2.0 / (np.sqrt(3.0) / 2.0 * a * a * c)


FILMS = {
    "GaN": {"metal": "Ga", "n_metal": _wurtzite(318.9e-12, 518.6e-12),
            "n_density_route": 6.1e6 / (69.723 + 14.007) * N_A},
    "AlN": {"metal": "Al", "n_metal": _wurtzite(311.17e-12, 497.88e-12),
            "n_density_route": 3.255e6 / (26.9815385 + 14.007) * N_A},
    "GaAs": {"metal": "Ga", "n_metal": 4.0 / 565.315e-12 ** 3,
             "n_density_route": 5.3176e6 / (69.723 + 74.921595) * N_A},
}

BORE_RADIUS = 0.03575  # R14 cylinder, as in the 8-inch fill-level study
THROW = 0.350
POLAR = np.radians(46.0)
RECESSES = (0.0, 0.034, 0.070, 0.120)
UM_PER_H = 1e-6 / 3600.0
CASES = [  # (film, growth rate um/h, metal flux / stoichiometric flux)
    ("GaN", 0.5, 1.0), ("GaN", 1.0, 1.0), ("GaN", 1.0, 1.5),
    ("AlN", 0.3, 1.0), ("AlN", 1.0, 1.0),
    ("GaAs", 1.0, 1.0),  # the RIBER ABI data-sheet condition, for the 950 C cross-check
]


def centre_arrival_per_melt_particle(recess, particles, seed):
    """Wafer-centre arrival flux per particle leaving the melt, wafer tilted by POLAR."""
    ev = simulate(Crucible(BORE_RADIUS, recess), particles, rng=seed)
    normal = (np.sin(POLAR), 0.0, -np.cos(POLAR))
    return float(next_event_flux(ev, [[0.0, 0.0, THROW]], normal)[0]), ev.transmission


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--particles", type=int, default=60_000)
    ap.add_argument("--out", default="results/crucible_knudsen")
    args = ap.parse_args()
    out = {}

    t_ref = celsius_to_kelvin(R07_THRESHOLD["T_C"])
    sigma_ref = cross_section_from_knudsen(R07_THRESHOLD["knudsen"], R07_D, R07_THRESHOLD["p_Pa"], t_ref)
    sigmas = {"sigma_R07": sigma_ref, "sigma_R07/2": sigma_ref / 2, "sigma_R07/5": sigma_ref / 5}
    out["sigma_R07_m2"] = sigma_ref
    print(f"R07-implied hard-sphere cross-section (Bi): {sigma_ref:.3g} m^2 "
          f"(sigma = pi d^2, d = {np.sqrt(sigma_ref / np.pi) * 1e10:.2f} A; sigma/5: "
          f"d = {np.sqrt(sigma_ref / 5 / np.pi) * 1e10:.2f} A)")

    inv_t = np.array([1.0 / celsius_to_kelvin(t) for _, t, _ in R07_STATED])
    log_p = np.log10([p for _, _, p in R07_STATED])
    slope, icpt = np.polyfit(inv_t, log_p, 1)
    fit_resid = float(np.max(np.abs(np.polyval([slope, icpt], inv_t) - log_p)))
    states = [(lbl, t, p, "stated") for lbl, t, p in R07_STATED]
    states += [(lbl, t, 10 ** np.polyval([slope, icpt], 1.0 / celsius_to_kelvin(t)), "interpolated")
               for lbl, t in R07_INTERPOLATED]
    states.sort(key=lambda st: st[1])
    print(f"\n1. R07 states (D = 16.5 mm), lambda/D with sigma_R07; Clausius-Clapeyron fit "
          f"through stated points: slope {-slope:.0f} K, max residual {fit_resid:.3f} decades")
    out["r07_states"] = {"clausius_clapeyron_slope_K": float(-slope), "fit_residual_decades": fit_resid}
    for label, t_c, p, how in states:
        kn = mean_free_path(p, celsius_to_kelvin(t_c), sigma_ref) / R07_D
        rms = R07_L4_MODEL_RMS.get(t_c)
        out["r07_states"][label] = {"T_C": t_c, "p_Pa": float(p), "pressure": how, "knudsen": kn,
                                    "model_rms_L/D=4": rms}
        print(f"  {label:32s} {p:8.3g} Pa ({how:12s})  lambda/D = {kn:6.2f}"
              + (f"   free-molecular model rms (L/D = 4) {rms:.3f}" if rms else ""))

    print("\n2. RIBER ABI: Ga at 950 C (their 'Ga @ 1 um/h' condition)")
    t_riber = celsius_to_kelvin(950.0)
    p_riber = float(vapour_pressure("Ga", t_riber))
    out["riber_950C"] = {"p_Pa": p_riber, "knudsen": {}}
    print(f"  p_Ga(950 C) = {p_riber:.3g} Pa")
    print("  aperture D   " + "  ".join(f"{k:>12s}" for k in sigmas))
    for d_mm in (25, 40, 60, 75):
        row = {k: mean_free_path(p_riber, t_riber, s) / (d_mm / 1000) for k, s in sigmas.items()}
        out["riber_950C"]["knudsen"][f"D={d_mm}mm"] = row
        print(f"  {d_mm:3d} mm       " + "  ".join(f"{v:12.2f}" for v in row.values()))

    print(f"\n3. Mass balance: bore {2000 * BORE_RADIUS:.1f} mm, throw {1000 * THROW:.0f} mm, "
          f"{np.degrees(POLAR):.0f} deg, lambda/D with D = bore")
    geo = {r: centre_arrival_per_melt_particle(r, args.particles, 11 + i) for i, r in enumerate(RECESSES)}
    area = np.pi * BORE_RADIUS ** 2
    out["geometry"] = {f"recess_{1000 * r:.0f}mm": {"arrival_per_melt_particle_m2": g, "transmission": w}
                       for r, (g, w) in geo.items()}
    out["cases"] = []
    print("  film  rate    excess  recess  T_melt   p_sat     lambda/D (sigma, /2, /5)")
    for film, rate, excess in CASES:
        f = FILMS[film]
        flux = rate * UM_PER_H * f["n_metal"] * excess  # metal atoms m^-2 s^-1 at the wafer
        m = atomic_mass_kg(f["metal"])
        for r, (g, _) in geo.items():
            # flux = g * emitted, emitted = area * evaporation_flux(p(T), T); solve for T.
            lo, hi = 800.0, 1599.0
            for _ in range(80):
                t = 0.5 * (lo + hi)
                emitted = area * evaporation_flux(vapour_pressure(f["metal"], t), t, m)
                lo, hi = (t, hi) if g * emitted < flux else (lo, t)
            p = float(vapour_pressure(f["metal"], t))
            kn = [mean_free_path(p, t, s) / (2 * BORE_RADIUS) for s in sigmas.values()]
            out["cases"].append({"film": film, "rate_um_h": rate, "metal_excess": excess,
                                 "recess_mm": 1000 * r, "T_melt_C": kelvin_to_celsius(t),
                                 "p_sat_Pa": p, "knudsen": dict(zip(sigmas, kn))})
            print(f"  {film:5s} {rate:4.1f}um/h  {excess:4.1f}   {1000 * r:4.0f}mm  "
                  f"{kelvin_to_celsius(t):6.0f} C  {p:8.3g} Pa  " + "  ".join(f"{k:6.2f}" for k in kn))

    ga = [c for c in out["cases"] if c["film"] == "GaAs"]
    print(f"\n  cross-check: GaAs 1 um/h needs {ga[0]['T_melt_C']:.0f}-{ga[-1]['T_melt_C']:.0f} C here "
          f"(RIBER ABI: 950 C crucible; ABI throw and insert geometry unknown)")
    for name, f in FILMS.items():
        print(f"  {name} metal density {f['n_metal'] * 1e-6:.4g} cm^-3 (density route "
              f"{f['n_density_route'] * 1e-6:.4g})")

    manifest = build_manifest(
        "crucible_knudsen", label="representative_chamber", validation_status="not_validated",
        inputs={"particles": args.particles, "bore_radius_m": BORE_RADIUS, "throw_m": THROW,
                "polar_angle_deg": float(np.degrees(POLAR)), "recesses_m": RECESSES,
                "r07_threshold": R07_THRESHOLD, "cases": CASES},
        outputs=out,
        warnings=["Metal-vapour collision cross-sections are not sourced; sigma is calibrated "
                  "on R07's Bi statement and bracketed down to sigma/5",
                  "Mass balance uses the free-molecular transmission and evaporation "
                  "coefficient 1; collisions change the flux by tens of percent",
                  "Alcock (1984) equations, +/-5 %; Bi pressures are R07's own"],
        disabled_physics=["intermolecular collisions in the crucible (being assessed)",
                          "Ga desorption from the growth front (enters via metal_excess)"])
    print(f"\nWrote {write_manifest(manifest, Path(args.out) / 'manifest.json')}")


if __name__ == "__main__":
    main()
