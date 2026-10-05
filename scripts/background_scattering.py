"""Estimate: does scattering by the chamber's background N2 change wafer uniformity?

During plasma-assisted growth the chamber holds N2 at p = Q / S (flow Q, effective pumping
speed S). Beam atoms that collide with it leave the direct beam. The direct flux at a wafer
point is attenuated by exp(-s / lambda) over the path length s from the source, and s differs
across the wafer, so the attenuation is not uniform even after rotation. Scattered atoms are
removed from the direct beam; where they end up is not modelled (bounding case for the
non-uniformity change: they are lost).

Inputs (bracketed; no growth-pressure measurement is sourced in the repository):
- N2 flow 0.5 / 2 / 10 sccm (standard 273.15 K, 101325 Pa: 1.68875e-3 Pa m^3/s per sccm);
  effective N2 pumping speed 0.5 / 2 m^3/s (the proposal's turbo is >= 2000 L/s nameplate;
  effective speed at the chamber is lower). Background gas at 300 K.
- Hard-sphere collision diameter beam-N2 = (d_beam + 3.7 A) / 2 with d_Ga 6 / 8 A (the
  scenario range after the Bi2 result) and d_N 3 A (atomic N, not sourced). Fast-beam mean
  free path lambda = v_b / (n sigma <v_rel>) with <v_rel> = sqrt(v_b^2 + v_gas^2) (mean speeds).
- Sources: Ga cell at 350 mm, 46 and 58 deg, aimed at the wafer centre, cos^n emission with
  n = 1 and 4 (bracketing the crucible beam width); N plate at 350 mm, 65 deg aimed +75 mm,
  n = 4 (a narrow jet, L/r about 3). Ga beam temperature 1235 K, N 600 K (not sourced).
Output: mean direct-beam loss and the change in 200 mm range/mean (rotation-averaged) caused by
the attenuation, per case.

Usage: python scripts/background_scattering.py
"""

import itertools

import numpy as np

K_B = 1.380649e-23
AMU = 1.66053907e-27
SCCM = 1.68875e-3
RHO = np.linspace(0.0, 0.100, 41)
PHI = np.linspace(0.0, 2 * np.pi, 180, endpoint=False)


def mean_speed(t, m_amu):
    return np.sqrt(8 * K_B * t / (np.pi * m_amu * AMU))


def rotation_profile(polar_deg, aim_offset, n_cos, lam, throw=0.350):
    th = np.radians(polar_deg)
    src = np.array([throw * np.sin(th), 0.0, -throw * np.cos(th)])  # wafer at z = 0 facing -z
    aim = np.array([aim_offset, 0.0, 0.0])
    axis = (aim - src) / np.linalg.norm(aim - src)
    out = []
    for r in RHO:
        pts = np.stack([r * np.cos(PHI), r * np.sin(PHI), np.zeros_like(PHI)], 1)
        d = pts - src
        s = np.linalg.norm(d, axis=1)
        cos_t = (d @ axis) / s
        cos_p = d[:, 2] / s  # wafer normal +z... incoming from below
        f = np.clip(cos_t, 0, None) ** n_cos * np.clip(cos_p, 0, None) / s ** 2
        out.append([np.mean(f), np.mean(f * np.exp(-s / lam)) if np.isfinite(lam) else np.mean(f)])
    return np.array(out)


def rom(p):
    w = RHO / RHO.sum()
    mean = np.sum(w * p) / np.sum(w)
    return 100 * (p.max() - p.min()) / mean


def main():
    v_gas = mean_speed(300.0, 28.0134)
    print("case                                   p (Pa)   lambda (m)  mean loss   range/mean: none -> attenuated (change)")
    for (q, s_eff), (label, m_amu, t_b, d_b, polar, off, n_cos) in itertools.product(
            [(0.5, 2.0), (2.0, 2.0), (2.0, 0.5), (10.0, 0.5)],
            [("Ga 46 deg, cos^1, d 6 A", 69.72, 1235.0, 6e-10, 46.0, 0.0, 1),
             ("Ga 46 deg, cos^4, d 8 A", 69.72, 1235.0, 8e-10, 46.0, 0.0, 4),
             ("Ga 58 deg, cos^4, d 8 A", 69.72, 1235.0, 8e-10, 58.0, 0.0, 4),
             ("N 65 deg +75 mm, cos^4, d 3 A", 14.007, 600.0, 3e-10, 65.0, 0.075, 4)]):
        p = q * SCCM / s_eff
        n = p / (K_B * 300.0)
        sigma = np.pi * ((d_b + 3.7e-10) / 2) ** 2
        v_b = mean_speed(t_b, m_amu)
        lam = v_b / (n * sigma * np.sqrt(v_b ** 2 + v_gas ** 2))
        prof = rotation_profile(polar, off, n_cos, lam)
        loss = 1 - np.sum(RHO * prof[:, 1]) / np.sum(RHO * prof[:, 0])
        a, b = rom(prof[:, 0]), rom(prof[:, 1])
        print(f"{q:4.1f} sccm / {s_eff:3.1f} m3/s  {label:30s} {p:8.2e}  {lam:8.2f}    {100 * loss:5.1f} %    "
              f"{a:6.2f} -> {b:6.2f} ({b - a:+.2f} points)")


if __name__ == "__main__":
    main()
