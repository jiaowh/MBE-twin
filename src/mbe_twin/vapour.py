"""Saturated vapour pressure, evaporation flux and mean free path for source metals.

Vapour pressures use Alcock, Itkin and Horrigan, Canadian Metallurgical Quarterly 23 (1984)
309, as reprinted in the CRC Handbook table "Vapor pressure of the metallic elements"
(C. B. Alcock, 2000): log10(p/atm) = A + B/T + C log10(T) + D/T^3, stated accuracy +/-5 %
for 1e-10 to 1e2 Pa. Only liquid phases in their stated ranges are included. Bi is not in
that table (its vapour contains Bi2), so R07 comparisons use R07's own stated pressures.

Collision cross-sections for metal vapours are not sourced here; callers pass them
explicitly (see scripts/crucible_knudsen.py for the R07-calibrated bracket).
"""

import numpy as np

from .units import ATM_PA, K_B, N_A

# element: (A, B, C, D, T_max_K) for the liquid, log10(p/atm) form.
ALCOCK_LIQUID = {
    "Ga": (6.754, -13984.0, -0.3413, 0.0, 1600.0),
    "Al": (5.911, -16211.0, 0.0, 0.0, 1800.0),
}

# Standard atomic weights (IUPAC), g/mol.
ATOMIC_MASS_G_MOL = {"Ga": 69.723, "Al": 26.9815385, "Bi": 208.9804}


def atomic_mass_kg(element):
    return ATOMIC_MASS_G_MOL[element] * 1e-3 / N_A


def vapour_pressure(element, temperature_k):
    """Saturated vapour pressure of the liquid metal in Pa."""
    a, b, c, d, t_max = ALCOCK_LIQUID[element]
    t = np.asarray(temperature_k, float)
    if np.any(t > t_max):
        raise ValueError(f"{element}: {t.max():.0f} K is above the equation's range ({t_max:.0f} K)")
    return ATM_PA * 10.0 ** (a + b / t + c * np.log10(t) + d / t ** 3)


def temperature_for_pressure(element, pressure_pa, lo=500.0):
    """Inverse of vapour_pressure by bisection (the pressure is monotonic in T)."""
    hi = ALCOCK_LIQUID[element][4]
    if not vapour_pressure(element, lo) <= pressure_pa <= vapour_pressure(element, hi):
        raise ValueError(f"{element}: {pressure_pa:.3g} Pa is outside {lo:.0f}-{hi:.0f} K")
    for _ in range(100):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if vapour_pressure(element, mid) < pressure_pa else (lo, mid)
    return 0.5 * (lo + hi)


def evaporation_flux(pressure_pa, temperature_k, mass_kg):
    """Hertz-Knudsen one-sided flux (particles m^-2 s^-1) from a surface at saturation,
    evaporation coefficient 1."""
    return pressure_pa / np.sqrt(2.0 * np.pi * mass_kg * K_B * temperature_k)


def mean_free_path(pressure_pa, temperature_k, cross_section_m2):
    """Hard-sphere mean free path in a single-species gas, k T / (sqrt(2) sigma p)."""
    return K_B * temperature_k / (np.sqrt(2.0) * cross_section_m2 * pressure_pa)


def cross_section_from_knudsen(knudsen, length_m, pressure_pa, temperature_k):
    """Cross-section that makes lambda / length equal `knudsen` at the given state."""
    return K_B * temperature_k / (np.sqrt(2.0) * knudsen * length_m * pressure_pa)
