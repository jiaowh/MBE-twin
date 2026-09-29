"""Are the aperture-plate holes of an RF nitrogen source free-molecular?

The pressure behind the plate follows from the N2 flow and the plate's conductance, so it
need not be assumed: p = Q / C with C = N_holes * (v_mean / 4) * pi r^2 * W(L/r), where W is
the free-molecular transmission of one hole (crucible.py random walk). The hole Knudsen number
is then lambda(p, T) / (2 r). If it is large, the free-molecular aperture model
(scripts/nitrogen_plate.py) is self-consistent; if not, the holes are transitional and beam
differently.

Inputs are bracketed (no drawing of the proposed source): N2 flow 0.5-3 sccm (H02 lists
0.1-10 sccm), hole count 50-500, hole radius 0.1-0.3 mm, L/r 2 and 5, gas temperature 300 and
600 K (a discharge heats the gas; not sourced). Only neutral N2 is counted (dissociation
changes the number density by less than a factor of 2). The N2 hard-sphere diameter, 3.7 A,
is a standard kinetic-theory value that is not sourced in this repository; it is bracketed by
x/÷ 1.3, which changes lambda by 1.7x.

Usage: python scripts/nitrogen_knudsen.py
"""

import itertools

import numpy as np

from mbe_twin.crucible import Crucible, simulate
from mbe_twin.units import K_B, N_A

SCCM_PA_M3_S = 101325.0 * 1e-6 / 60.0  # 1 sccm at 273.15 K, 101325 Pa (see SOLVER_AND_FIDELITY.md)
N2_MASS = 28.0134e-3 / N_A
D_N2 = 3.7e-10


def main():
    trans = {a: simulate(Crucible(1.0, a), 200_000, rng=5, record_events=False).transmission
             for a in (2.0, 5.0)}
    print("hole transmission W(L/r): " + ", ".join(f"L/r {a:g}: {w:.4f}" for a, w in trans.items()))
    print("\nflow  holes  r(mm)  L/r   T(K)   p_behind(Pa)   Kn = lambda/(2r) for d x1.3 / x1 / /1.3")
    worst = np.inf
    for q_sccm, n, r_mm, a, t in itertools.product((0.5, 3.0), (50, 500), (0.1, 0.3), (2.0, 5.0), (300.0, 600.0)):
        r = r_mm * 1e-3
        v = np.sqrt(8 * K_B * t / (np.pi * N2_MASS))
        conductance = n * v / 4 * np.pi * r * r * trans[a]
        # throughput in sccm is defined at 273.15 K; at gas temperature t the volume flow scales by t / 273.15
        p = q_sccm * SCCM_PA_M3_S * (t / 273.15) / conductance
        kn = [K_B * t / (np.sqrt(2) * np.pi * (D_N2 * f) ** 2 * p) / (2 * r) for f in (1.3, 1.0, 1 / 1.3)]
        worst = min(worst, kn[0])
        print(f"{q_sccm:4.1f}  {n:5d}  {r_mm:5.1f}  {a:3.0f}  {t:5.0f}   {p:12.3g}   "
              + "  ".join(f"{k:8.3g}" for k in kn))
    print(f"\nsmallest hole Knudsen number in the bracket: {worst:.3g}")


if __name__ == "__main__":
    main()
