"""Check the Ga-study uniformity estimator against dense free-molecular reference profiles.

For each geometry, crucible.py gives a dense rotation-averaged profile (401 radii, 360
rotation angles, 4e5 particles); its range/mean is the reference. The profile is reduced to
the same 20 annulus averages the DSMC runs use, and the estimators are applied:
- noise-free: bins alone, and annulus fits of order 2-5 (mbe_twin.profile_fit);
- with noise: 400 synthetic realizations using the relative per-bin standard errors recorded
  by a DSMC run of that geometry; bias and scatter of each estimator.
The 120 mm / 46 deg reference profile is saved to tests/data for tests/test_profile_fit.py.
Limitation: validated for these smooth beam profiles only; a profile with kinks can defeat a
low-order fit (the order-3 / order-5 spread reported by sparta_ga.py flags this).

Usage: python scripts/check_uniformity_estimator.py
"""

import json
from pathlib import Path

import numpy as np

import sparta_ga as g
from mbe_twin import profile_fit as pf
from mbe_twin.beam import Wafer, crucible_source_on_cone, rotation_averaged_flux
from mbe_twin.crucible import simulate

ROOT = Path(__file__).resolve().parents[1]
R = g.WAFER_RADIUS
E = g.EDGES
CASES = {  # (fill m, angle deg): DSMC run whose per-bin errors set the noise level
    (0.04, 46.0): "ga_batch/fill040_fm",
    (0.07, 46.0): "ga_batch/fill070_fm",
    (0.12, 46.0): "ga_batch/fill120_fm",
    (0.12, 58.0): "ga_angle/fill120_d8_58deg",
    (0.07, 54.0): "ga_angle/fill070_d8_54deg",
}


def dense_reference(fill, angle):
    g.POLAR_DEG = angle
    ev = simulate(g.crucible_for(fill), 400_000, rng=1)
    wafer = Wafer(radius=R)
    src = crucible_source_on_cone("Ga", wafer, ev, throw=g.THROW, polar_angle=np.radians(angle), azimuth=0.0,
                                  emission_rate=1.0)
    r = np.linspace(0.0, R, 801)
    return r, rotation_averaged_flux([src], wafer, r, n_angles=360)


def annulus_bins(r, f):
    out = []
    for a, b in zip(E[:-1], E[1:]):
        m = (r >= a - 1e-12) & (r <= b + 1e-12)
        out.append(np.trapezoid(f[m] * r[m], r[m]) / np.trapezoid(r[m], r[m]))
    return np.array(out)


def main():
    rng = np.random.default_rng(0)
    print("range/mean %: reference | noise-free estimates | with recorded noise: bias (scatter)")
    for (fill, angle), run in CASES.items():
        r, f = dense_reference(fill, angle)
        ref = pf.uniformity(f, r, R)["range_over_mean_pct"]
        bins = annulus_bins(r, f)
        if (fill, angle) == (0.12, 46.0):
            out = ROOT / "tests/data/fm_profile_120mm_46deg.json"
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps({"r_m": r[::2].tolist(), "flux": f[::2].tolist(),
                                       "note": "crucible.py, 4e5 particles, 360 angles; scripts/check_uniformity_estimator.py"}),
                           encoding="utf-8", newline="\n")
        clean = {"bins": pf.binned_uniformity(bins, E)}
        clean.update({k: pf.fitted_uniformity(bins, E, R, k)["range_over_mean_pct"] for k in (2, 3, 4, 5)})
        o = json.loads((ROOT / "data/runs/sparta_ga" / f"{run}.json").read_text(encoding="utf-8"))["outputs"]
        rel = np.array(o["dsmc_flux_stderr"]) / np.array(o["dsmc_flux"])
        noisy = {}
        for k in ("bins", 2, 3, 4, 5):
            est = []
            for _ in range(400):
                nb = bins * (1 + rel * rng.standard_normal(len(bins)))
                est.append(pf.binned_uniformity(nb, E) if k == "bins"
                           else pf.fitted_uniformity(nb, E, R, k, bins * rel)["range_over_mean_pct"])
            noisy[k] = (np.mean(est) - ref, np.std(est))
        print(f"{1e3 * fill:3.0f} mm {angle:2.0f} deg: {ref:5.2f} | " + " ".join(f"{k}:{v:5.2f}" for k, v in clean.items())
              + " | " + " ".join(f"{k}:{b:+.2f}({s:.2f})" for k, (b, s) in noisy.items()))


if __name__ == "__main__":
    main()
