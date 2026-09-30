"""Ga-rich growth window and thickness uniformity on the 200 mm wafer (first growth-model use).

Combines, per radius on the rotating wafer:
- Ga maps: recorded DSMC runs at d = 8 A (data/runs/sparta_ga): fills 40 / 70 / 120 mm at the
  46 deg port, and the angle optima (48 / 54 / 58 deg). Profiles are the order-4 annulus fits
  used for the uniformity metric (mbe_twin.profile_fit), normalized to the centre.
- N maps: the free-molecular optimum (aim offset, port angle) per hole aspect L/r from
  results/nitrogen_aim_study (thin plate and R30-type holes in 0.5 / 1 / 2 mm plates), plus a
  flat reference. Shape only; the centre active-N flux is 16.7 nm/min (1 um/h GaN).
- Wafer temperature: T0 + dT (r/R)^2 (edge hotter for dT > 0), T0 = 700 / 740 / 780 C, dT from
  -10 to +10 K. No heater model yet; dT stands in for heater non-uniformity.
- Growth: mbe_twin.growth steady state with each droplet-onset scenario.

For each combination, the centre Ga/N flux ratio R0 is varied. The window is the range of R0
for which every radius stays in the Ga-adlayer regime (no N-rich growth, no droplets). The
local ratio spread max(g/n)/min(g/n) must fit inside 1 + F_crit/J_N for a window to exist.
Thickness range/mean is reported at the window centre. Temperatures follow the sources' own
substrate-temperature scales (growth.py); all outputs are representative_chamber.

Usage: python scripts/growth_window.py [--aim ...] [--held] [--out results/growth_window]
--held replaces the Ga maps by the centre-flux-held runs where they exist.
"""

import argparse
import itertools
import json
from pathlib import Path

import numpy as np

from mbe_twin import profile_fit
from mbe_twin.growth import load_parameters, steady_state
from mbe_twin.manifest import build_manifest, write_manifest

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / "data/runs/sparta_ga"
AIM = ROOT / "results/nitrogen_aim_study/manifest.json"
WAFER_RADIUS = 0.100
EDGES = np.linspace(0.0, WAFER_RADIUS, 21)
RHO = np.linspace(0.0, WAFER_RADIUS, 41)  # same grid as the nitrogen studies
GA_CASES = {
    "40 mm, 46 deg": "ga_batch/fill040_d8.json", "70 mm, 46 deg": "ga_batch/fill070_d8.json",
    "120 mm, 46 deg": "ga_batch/fill120_d8.json", "40 mm, 48 deg": "ga_angle/fill040_d8_48deg.json",
    "70 mm, 54 deg": "ga_angle/fill070_d8_54deg.json", "120 mm, 58 deg": "ga_angle/fill120_d8_58deg.json",
}
HELD = {  # centre-flux-held states (data/runs/sparta_ga/ga_dsmchold, latest correction)
    "40 mm, 46 deg": "fill040_d8_dsmchold", "70 mm, 46 deg": "fill070_d8_dsmchold",
    "120 mm, 46 deg": "fill120_d8_dsmchold", "40 mm, 48 deg": "fill040_d8_48deg_dsmchold",
    "70 mm, 54 deg": "fill070_d8_54deg_dsmchold", "120 mm, 58 deg": "fill120_d8_58deg_dsmchold",
}
J_N0 = 1000.0 / 60.0  # nm/min for 1 um/h
T0_C = (700.0, 740.0, 780.0)
DT_K = (-10.0, -5.0, 0.0, 5.0, 10.0)
C = 273.15


def ga_profile(record):
    o = json.loads((RECORDS / record).read_text(encoding="utf-8"))["outputs"]
    coef = profile_fit.annulus_fit(np.asarray(o["dsmc_flux"]), EDGES, WAFER_RADIUS, 4,
                                   np.asarray(o["dsmc_flux_stderr"]))
    f = profile_fit.evaluate(coef, RHO, WAFER_RADIUS)
    return f / f[0]


def latest_held(name):
    """Record path of the latest completed correction of a held state, or None."""
    runs = [f"ga_dsmchold/{name}.json"] + [f"ga_dsmchold/{name}_it{k}.json" for k in range(2, 10)]
    done = [r for r in runs if (RECORDS / r).exists()]
    return done[-1] if done else None


def n_profiles(paths):
    best = {}
    for path in paths:
        for r in json.loads(Path(path).read_text(encoding="utf-8"))["outputs"]["rows"]:
            a = r["L_over_r"]
            if a not in best or r["best"]["range_over_mean_pct"] < best[a]["best"]["range_over_mean_pct"]:
                best[a] = r
    out = {"flat": np.ones_like(RHO)}
    for a in sorted(best):
        r = best[a]
        p = np.asarray(r["best_profile_relative"], float)
        b = r["best"]
        out[f"L/r {a:g} ({b['offset_mm']:+.0f} mm, {b['angle_deg']:.0f} deg)"] = p / p[0]
    return out


def window(g, n, t_k, params, scenario):
    """Feasible centre Ga/N ratios, thickness range/mean at the window centre, ratio spread.

    Every radius is Ga-adlayer iff R0 g >= n (no N-rich growth) and R0 J_N0 g - J_N0 n <= F_crit(T)
    (no droplets), so the window is [max(n/g), min((n + F_crit/J_N0)/g)]; the regimes at its
    centre are checked with growth.steady_state.
    """
    j_n = J_N0 * n
    spread = float(np.max(g / n) / np.min(g / n))
    lo = float(np.max(n / g))
    hi = float(np.min((n + params.critical_excess(scenario, t_k) / J_N0) / g))
    if hi <= lo:
        return {"window": None, "width": 0.0, "ratio_spread": spread, "thickness_range_over_mean_pct": None}
    mid = 0.5 * (lo + hi)
    st = steady_state(mid * J_N0 * g, j_n, t_k, params, scenario)
    assert np.all(st["regime"] == "Ga-adlayer")
    h = st["net_growth"]
    w = RHO / RHO.sum()  # area weighting on the uniform radial grid
    mean = float(np.sum(w * h) / np.sum(w))
    return {"window": [lo, hi], "width": hi - lo, "ratio_spread": spread,
            "thickness_range_over_mean_pct": float(100 * (h.max() - h.min()) / mean)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="results/growth_window")
    ap.add_argument("--aim", nargs="+", default=[str(AIM)],
                    help="nitrogen_aim_study manifests; per L/r the lowest range/mean is used")
    ap.add_argument("--held", action="store_true",
                    help="use the centre-flux-held Ga records (latest correction) where available")
    args = ap.parse_args()
    cases = dict(GA_CASES)
    if args.held:
        for k, name in HELD.items():
            rec = latest_held(name)
            if rec:
                cases[k] = rec
            else:
                print(f"note: no held record for {k}; using {cases[k]}")
    params = load_parameters()
    ga = {k: ga_profile(v) for k, v in cases.items()}
    nm = n_profiles(args.aim)
    rows = []
    for (gk, g), (nk, n), t0, dt, sc in itertools.product(ga.items(), nm.items(), T0_C, DT_K,
                                                         params.droplet_onset):
        t_k = t0 + C + dt * (RHO / WAFER_RADIUS) ** 2
        rows.append({"ga": gk, "n": nk, "T0_C": t0, "dT_edge_K": dt, "scenario": sc,
                     **window(g, n, t_k, params, sc)})

    def pick(**kw):
        return [r for r in rows if all(r[k] == v for k, v in kw.items())]

    for sc in params.droplet_onset:
        for t0 in T0_C:
            print(f"\nwindow width in centre Ga/N (flat wafer temperature {t0:.0f} C, droplet onset {sc}; "
                  f"F_crit/J_N = {params.critical_excess(sc, t0 + C) / J_N0:.3f})")
            print(f"  {'N map':34s} " + " ".join(f"{k:>14s}" for k in ga))
            for nk in nm:
                print(f"  {nk:34s} " + " ".join(f"{pick(ga=gk, n=nk, T0_C=t0, dT_edge_K=0.0, scenario=sc)[0]['width']:14.3f}"
                                                for gk in ga))
    print("\nthickness range/mean % at the window centre, 740 C, Ref14 onset, by edge dT (K) "
          + " ".join(f"{d:6.0f}" for d in DT_K))
    for gk, nk in itertools.product(["70 mm, 54 deg", "120 mm, 46 deg"], nm):
        vals = [pick(ga=gk, n=nk, T0_C=740.0, dT_edge_K=d, scenario="Ref14_growth")[0]["thickness_range_over_mean_pct"]
                for d in DT_K]
        print(f"  {gk:15s} {nk:34s} " + " ".join("     -" if v is None else f"{v:6.2f}" for v in vals))

    manifest = build_manifest(
        "growth_window", label="representative_chamber", validation_status="not_validated",
        inputs={"ga_records": cases, "n_source": args.aim, "J_N0_nm_min": J_N0,
                "T0_C": T0_C, "dT_edge_K": DT_K},
        outputs={"rows": rows, "rho_m": RHO},
        sources=[Path(__file__), ROOT / "src/mbe_twin/growth.py", ROOT / "data/parameters/gan_growth.json",
                 ROOT / "src/mbe_twin/profile_fit.py"],
        warnings=["Steady-state regime model; transients, droplet consumption and morphology not modelled",
                  "Droplet onset from three disagreeing literature scenarios; temperatures are the sources' scales",
                  "N maps free-molecular (aim-study optima); total active-N output assumed 1 um/h at the centre",
                  "Temperature map is a parameterized stand-in, not a heater model"],
        disabled_physics=["adlayer kinetics", "droplet consumption", "AlN", "polarity", "morphology"])
    print(f"Wrote {write_manifest(manifest, Path(args.out) / 'manifest.json')}")


if __name__ == "__main__":
    main()
