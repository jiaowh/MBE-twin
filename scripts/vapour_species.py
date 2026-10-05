"""Vapour species and collision-size estimates behind the 2026-09-30 physics-data search.

Three questions, each answered from sourced inputs only (see
ref/notes/PHYSICS_DATA_SEARCH_2026-09-30.md):

  1. Bi2 in R07's bismuth vapour. Kubaschewski's separate Bi and Bi2 correlations (R21, NEA
     2015 Table 2.8.2) give the dimer fraction at R07's temperatures. At a fixed total
     pressure, each Bi2 carries two atoms at 1/sqrt(2) of the monomer speed, so the arriving
     atom flux is (p1 + sqrt(2) p2) / (p1 + p2) times the monatomic value.
  2. A Ga hard-sphere diameter from dispersion scaling. For an r^-6 attraction the classical
     transport cross-section scales as (C6/kT)^(1/3), so d ~ (C6/kT)^(1/6). The scaling is
     tested on noble gases (C6 from R22, hard-sphere d from R29 viscosities at 273.15 K), then
     applied to Ga, Al and Bi. Open-shell metals also bond, so this is the closed-shell
     (dispersion-only) value; the R07-fitted Bi diameter measures how much larger the
     effective value is for Bi.
  3. Ga2 in the Ga cell vapour. Rigid-rotor/harmonic-oscillator equilibrium with R23's D0,
     bond length and frequency, and an effective electronic factor taken from R23's own
     measured Ga2+/Ga+ ion currents (Table I), then extrapolated to the cell temperature.

Usage: python scripts/vapour_species.py [--out results/vapour_species]
"""

import argparse
import math
from pathlib import Path

from mbe_twin.manifest import build_manifest, write_manifest
from mbe_twin.units import K_B, N_A, celsius_to_kelvin

H = 6.62607015e-34  # J s, exact
C_CM = 2.99792458e10  # cm/s
AMU = 1.66053906660e-27  # kg

# R21: Kubaschewski (1979) via NEA 2015 Table 2.8.2, p in Pa, T in K.
def p_bi1(t):
    return 10 ** (2.1249 - 10400 / t - 1.26 * math.log10(t) + 12.35)


def p_bi2(t):
    return 10 ** (2.1249 - 10730 / t - 3.2 * math.log10(t) + 18.1)


def p_bi_nea(t):  # NEA recommended total, Eq. (2.17), about +/-40 %
    return 2.67e10 * math.exp(-22858 / t)


# R07 states (scripts/crucible_knudsen.py): T in C, stated or interpolated p in Pa.
R07_STATES = [("0.35 A/s", 573.0, 0.08), ("3.5 A/s", 666.0, 1.05), ("11 A/s", 723.0, 4.0)]

# R29: NIST SRD 69 dilute-gas viscosity at 273.15 K (Pa s); molar masses (g/mol).
NOBLE = {"Ne": (29.900e-6, 20.180), "Ar": (20.998e-6, 39.948), "Kr": (23.373e-6, 83.798),
         "Xe": (21.075e-6, 131.293)}
# R22: same-species C6 in atomic units (Table 2, benchmark set).
C6 = {"Ne": 6.91, "Ar": 67.4, "Kr": 136.0, "Xe": 302.0, "Ga": 456.0, "Al": 520.0, "Bi": 513.0}
# Metal temperatures (K): Ga and Al at the 1 um/h cell temperatures of the crucible_knudsen
# mass balance (about 972 C and 1107 C); Bi at R07's 3.5 A/s fit state (666 C).
METAL_T = {"Ga": 1245.0, "Al": 1380.0, "Bi": celsius_to_kelvin(666.0)}
BI_FIT_D = (8.0e-10, 10.3e-10)  # R07 DSMC sensitivity interval (REFERENCE_CHAMBER.md)

# R23 (Balducci, Gigli and Meloni 1998): D0(Ga2) = 110.8 +/- 4.9 kJ/mol; thermal functions
# from Re = 0.272 nm, omega_e = 180 cm-1 (Shim et al. 1991, as used in R23).
GA2_D0 = 110.8e3 / N_A
GA2_WE = 180.0
GA2_RE = 2.72e-10
GA_P = (1.0, 10.0)  # Pa, bracket of in-crucible Ga pressure at 0.5-1 um/h
GA_2P32 = 826.0  # cm-1, Ga 2P3/2 level above 2P1/2 (standard atomic data)
# R23 Table I, runs MS1 and MS2 (Ga-In alloy, points with both Ga+ and Ga2+):
# (instrument constant K in atm/(A K), T in K, I(Ga+), I(Ga2+)); p_i = K f_i I_i T.
R23_F = {"Ga": 2.325, "Ga2": 2.770}
R23_POINTS = [
    (0.463, 1465, 1.17e-07, 1.00e-11), (0.463, 1468, 1.20e-07, 2.50e-11), (0.463, 1502, 2.13e-07, 2.50e-11),
    (0.463, 1531, 2.13e-07, 2.40e-11), (0.463, 1582, 5.00e-07, 1.02e-10), (0.463, 1517, 3.10e-07, 4.50e-11),
    (0.463, 1464, 1.32e-07, 1.10e-11), (0.463, 1596, 7.50e-07, 1.53e-10), (0.463, 1587, 7.60e-07, 1.68e-10),
    (0.513, 1446, 6.10e-08, 3.00e-12), (0.513, 1452, 6.10e-08, 3.00e-12), (0.513, 1501, 1.29e-07, 1.30e-11),
    (0.513, 1501, 1.38e-07, 1.30e-11), (0.513, 1558, 3.02e-07, 4.56e-11), (0.513, 1505, 1.71e-07, 1.70e-11),
    (0.513, 1470, 1.11e-07, 9.00e-12), (0.513, 1531, 2.70e-07, 3.60e-11), (0.513, 1583, 4.94e-07, 1.03e-10),
    (0.513, 1632, 9.31e-07, 2.85e-10), (0.513, 1596, 5.13e-07, 1.03e-10),
]
ATM_PA = 101325.0


def hard_sphere_d(mu, molar_g, t):
    """Hard-sphere diameter from first-order Chapman-Enskog viscosity."""
    m = molar_g * 1e-3 / N_A
    return math.sqrt(5 / 16 * math.sqrt(math.pi * m * K_B * t) / (math.pi * mu))


def bismuth():
    rows = []
    for label, tc, p_stated in R07_STATES:
        t = celsius_to_kelvin(tc)
        a, b = p_bi1(t), p_bi2(t)
        rows.append({"state": label, "T_C": tc, "p_Bi_Pa": a, "p_Bi2_Pa": b, "x_Bi2": b / (a + b),
                     "atom_flux_gain_at_fixed_p": (a + math.sqrt(2) * b) / (a + b),
                     "p_R07_Pa": p_stated, "p_R07_over_kubaschewski": p_stated / (a + b),
                     "p_R07_over_nea": p_stated / p_bi_nea(t)})
    return rows


def dispersion():
    d_noble = {e: hard_sphere_d(mu, m, 273.15) for e, (mu, m) in NOBLE.items()}
    test = {ref: {e: d_noble[ref] * (C6[e] / C6[ref]) ** (1 / 6) for e in NOBLE} for ref in ("Ar", "Kr", "Xe")}
    metals = {}
    for e, t in METAL_T.items():
        est = [d_noble[ref] * (C6[e] / C6[ref]) ** (1 / 6) * (273.15 / t) ** (1 / 6) for ref in ("Ar", "Kr", "Xe")]
        metals[e] = {"T_K": t, "d_dispersion_min_m": min(est), "d_dispersion_max_m": max(est)}
    scale = (C6["Ga"] / C6["Bi"]) ** (1 / 6) * (METAL_T["Bi"] / METAL_T["Ga"]) ** (1 / 6)
    transfer = [d * scale for d in BI_FIT_D]
    enhancement = [d / metals["Bi"]["d_dispersion_max_m"] for d in BI_FIT_D]
    return {"noble_hs_d_273K_m": d_noble, "scaling_test_m": test, "metals": metals,
            "bi_fit_d_m": list(BI_FIT_D), "bi_fit_over_dispersion": enhancement,
            "ga_d_from_bi_transfer_m": transfer}


def ga2_kp_model(t):
    """K_p = p(Ga2) / p(Ga)^2 in 1/Pa, rigid rotor + harmonic oscillator, Ga2 electronic factor 1."""
    m = 69.723 * AMU
    qtr = lambda mass: (2 * math.pi * mass * K_B * t / H ** 2) ** 1.5 * K_B * t  # per Pa
    qrot = 8 * math.pi ** 2 * (m / 2) * GA2_RE ** 2 * K_B * t / (2 * H ** 2)
    qvib = 1 / (1 - math.exp(-H * C_CM * GA2_WE / (K_B * t)))
    g_atom = 2 + 4 * math.exp(-H * C_CM * GA_2P32 / (K_B * t))
    return qtr(2 * m) / qtr(m) ** 2 * qrot * qvib / g_atom ** 2 * math.exp(GA2_D0 / (K_B * t))


def gallium_dimer():
    """Effective Ga2 electronic factor from R23's measured equilibria, then x(Ga2) at the cell."""
    factors = []
    for k, t, i1, i2 in R23_POINTS:
        p1 = k * R23_F["Ga"] * i1 * t * ATM_PA
        p2 = k * R23_F["Ga2"] * i2 * t * ATM_PA
        factors.append(p2 / p1 ** 2 / ga2_kp_model(t))
    factors.sort()
    median = factors[len(factors) // 2 - 1: len(factors) // 2 + 1]
    g_eff = {"min": factors[0], "median": sum(median) / 2, "max": factors[-1]}
    t = METAL_T["Ga"]
    cells = [{"g_eff": name, "p_Ga_Pa": p, "x_Ga2": ga2_kp_model(t) * g * p / (1 + ga2_kp_model(t) * g * p)}
             for name, g in g_eff.items() for p in GA_P]
    return {"g_eff": g_eff, "n_points": len(factors), "cell": cells}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="results/vapour_species")
    args = ap.parse_args()

    bi = bismuth()
    print("1. Bi2 in R07 vapour (Kubaschewski via NEA 2015)")
    for r in bi:
        print(f"  {r['state']:>9} {r['T_C']:.0f} C: x_Bi2 {r['x_Bi2']:.3f}, atom-flux gain {r['atom_flux_gain_at_fixed_p']:.3f}, "
              f"R07 p / Kubaschewski {r['p_R07_over_kubaschewski']:.2f}, R07 p / NEA {r['p_R07_over_nea']:.2f}")

    disp = dispersion()
    print("\n2. Hard-sphere diameters (A)")
    print("  noble gases from NIST viscosity at 273.15 K: "
          + ", ".join(f"{e} {d * 1e10:.2f}" for e, d in disp["noble_hs_d_273K_m"].items()))
    for ref, row in disp["scaling_test_m"].items():
        print(f"  C6 scaling anchored on {ref}: " + ", ".join(f"{e} {d * 1e10:.2f}" for e, d in row.items()))
    for e, r in disp["metals"].items():
        print(f"  {e} at {r['T_K']:.0f} K, dispersion only: {r['d_dispersion_min_m'] * 1e10:.2f}-{r['d_dispersion_max_m'] * 1e10:.2f}")
    lo, hi = disp["bi_fit_over_dispersion"]
    print(f"  R07-fitted Bi 8.0-10.3 A is {lo:.2f}-{hi:.2f} x the dispersion-only value")
    lo, hi = disp["ga_d_from_bi_transfer_m"]
    print(f"  Bi fit transferred to Ga by the same scaling: {lo * 1e10:.2f}-{hi * 1e10:.2f}")

    ga2 = gallium_dimer()
    g = ga2["g_eff"]
    print(f"\n3. Ga2: R23's {ga2['n_points']} measured equilibria give an effective electronic factor "
          f"{g['min']:.1f}-{g['max']:.1f} (median {g['median']:.1f})")
    for r in ga2["cell"]:
        print(f"  {METAL_T['Ga']:.0f} K, p_Ga {r['p_Ga_Pa']:>4.0f} Pa, factor {r['g_eff']:>6}: x_Ga2 {r['x_Ga2']:.1e}")

    manifest = build_manifest(
        "vapour_species", label="representative_chamber", validation_status="not_validated",
        inputs={"r07_states": R07_STATES, "noble_viscosity_273K": NOBLE, "c6_au": C6, "metal_T_K": METAL_T,
                "bi_fit_d_m": BI_FIT_D, "ga2": {"D0_J": GA2_D0, "we_cm": GA2_WE, "re_m": GA2_RE,
                                                "p_Pa": GA_P, "r23_f": R23_F, "r23_points": R23_POINTS}},
        outputs={"bismuth": bi, "dispersion": disp, "ga2": ga2},
        warnings=["Dispersion scaling gives a closed-shell diameter; Ga and Bi also bond, so it is a lower-end estimate, not a transport property.",
                  "Kubaschewski's Bi/Bi2 split has no stated uncertainty; a harmonic D0-based estimate gives about 0.5 instead of 0.3.",
                  "The Ga2 electronic factor is fitted to R23's alloy data at 1446-1632 K and extrapolated to the cell temperature."],
        sources=["scripts/vapour_species.py"])
    print(f"\nWrote {write_manifest(manifest, Path(args.out) / 'manifest.json')}")


if __name__ == "__main__":
    main()
