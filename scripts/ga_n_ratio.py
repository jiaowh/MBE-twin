"""Local Ga/N flux-ratio range across the rotating 200 mm wafer (Ga-rich PAMBE margin).

In Ga-rich growth the local growth rate follows active N, and Ga must exceed N everywhere
without reaching the droplet threshold (ref/notes/NITROGEN_BOUNDARY.md). The quantity that
matters for the Ga source is therefore the spread of the local Ga/N ratio, not the Ga range
alone. This script combines:
- Ga: the fitted DSMC profiles recorded by scripts/sparta_ga.py (annulus fit, order 4)
  (data/runs/sparta_ga/ga_batch), 46 deg / 350 mm, level melt, three fills and the diameter
  bracket;
- N: representative aperture-plate maps (scripts/nitrogen_plate.py model) at 40 deg and
  350 mm: a thin plate (L/r = 0, the most uniform case) and beaming holes (L/r = 2). The N
  hole regime depends on the plate drawing (free-molecular only for large open area).
Both are rotation-averaged, so the ratio is a radial profile. Reported: (max - min) / mean of
Ga/N over the wafer, and the ratio at the edge relative to the centre.

Usage: python scripts/ga_n_ratio.py
"""

import json
from pathlib import Path

import numpy as np

from mbe_twin import profile_fit
from mbe_twin.aperture import aperture_plate_sources, hex_holes
from mbe_twin.beam import Wafer, rotation_averaged_flux
from mbe_twin.crucible import Crucible, simulate

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "data/runs/sparta_ga/ga_batch"
R = 0.100
RHO = np.linspace(0.0, R, 41)


def ga_profile(name):
    m = json.loads((RUNS / f"{name}.json").read_text(encoding="utf-8"))["outputs"]["metrics_dsmc"]
    f = profile_fit.evaluate(m["fit"], RHO, R)  # annulus-fit polynomial in (r/R)^2 (sparta_ga.py)
    return f / f[0]


def n_profile(aspect):
    ev = simulate(Crucible(0.0002, aspect * 0.0002), 20_000, rng=40)
    src = aperture_plate_sources("N", Wafer(radius=R), ev, hex_holes(0.02, 0.005), throw=0.35,
                                 polar_angle=np.radians(40.0), azimuth=np.pi, total_rate=1.0)
    f = rotation_averaged_flux(src, Wafer(radius=R), RHO, n_angles=36)
    return f / f[0]


def spread(f):
    ring = np.pi * np.diff(np.concatenate(([0.0], 0.5 * (RHO[1:] + RHO[:-1]), [R])) ** 2)
    mean = np.sum(ring * f) / ring.sum()
    return 100 * (f.max() - f.min()) / mean


def main():
    n_maps = {"thin plate (L/r 0)": n_profile(0.0), "beaming holes (L/r 2)": n_profile(2.0)}
    for label, n in n_maps.items():
        print(f"N map, {label}: range/mean {spread(n):.1f} %, edge/centre {n[-1]:.3f}")
    print("\nGa/N ratio over 200 mm: range/mean %  (edge/centre)")
    print(f"{'Ga run':22s} {'Ga alone':>14s}" + "".join(f"{k:>26s}" for k in n_maps))
    for fill in ("040", "070", "120"):
        for d in ("fm", "d2.5", "d5.68", "d8"):
            name = f"fill{fill}_{d}"
            if not (RUNS / f"{name}.json").exists():
                continue
            g = ga_profile(name)
            cells = [f"{spread(g / n):7.1f} % ({(g / n)[-1]:.3f})" for n in n_maps.values()]
            print(f"{name:22s} {spread(g):7.1f} % ({g[-1]:.3f})" + "".join(f"{c:>26s}" for c in cells))


if __name__ == "__main__":
    main()
