"""Heater zone count and wafer temperature uniformity on the representative 200 mm holder.

Uses mbe_twin.heater (axisymmetric heater-ledge-wafer radiation and conduction). For each zone
layout the zone powers are optimized to minimize the wafer temperature range at a target mean
wafer temperature (740 C by default) by sequential linear programming: the wafer temperatures
are linearized in the zone powers (finite differences), the exact minimax problem (minimize
max - min at the target area-weighted mean, powers >= 0) is solved as a linear programme within
a trust region, and the step is accepted only if the true range falls. For 1-3 zones this
reproduces a direct Nelder-Mead minimization of the range; for more zones Nelder-Mead and
Powell stalled. Zone layouts (heater radius 115 mm):
  1 zone; 2 zones split at 80 mm; 3 zones split at 60 and 95 mm; 6 and 12 equal-width zones,
  which stand for a heater whose radial power density is designed (element pitch), not for
  12 independently controlled zones.
Parameters no repository source fixes are varied one at a time around a base case:
  gap 5 / 10 / 20 mm; heater emissivity 0.7 / 0.85 / 0.95; ledge emissivity 0.15 (clean Mo-like)
  / 0.3 / 0.6 (coated); wafer-ledge conductance 50 / 200 / 1000 W m^-2 K^-1; ledge inner radius
  95 / 97 / 99 mm (wafer overlap 5 / 3 / 1 mm); Si conductivity 20 / 30 / 40 W m^-1 K^-1; rim
  surroundings 300 K (open) / 700 K (shielded); heater radius 115 / 130 mm (overhang).
Also reported: the wafer range after a +/-5 % error in one zone's power (robustness), and
R05's qualitative mechanisms (zone ratio, heater gap, ledge reflectivity, overlap) as checks.

The wafer temperature range converts to thickness through the growth model: see
ref/notes/GROWTH_EVIDENCE.md (about 0.03 / 0.13 / 0.5 % range/mean per K at 700 / 740 / 780 C).

Usage: python scripts/heater_zones.py [--target-c 740] [--out results/heater_zones]
"""

import argparse
import dataclasses
import os
from pathlib import Path

# Small dense solves: multithreaded BLAS made each 130x130 solve 0.4 s on the shared laptop
# (thread oversubscription), single-threaded it takes microseconds.
for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402
from scipy.optimize import linprog  # noqa: E402

from mbe_twin.heater import HeaterGeometry, HeaterModel, HeaterProperties  # noqa: E402
from mbe_twin.manifest import build_manifest, write_manifest  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
LAYOUTS = {"1 zone": (0.0, 1.0), "2 zones": (0.0, 80 / 115, 1.0), "3 zones": (0.0, 60 / 115, 95 / 115, 1.0),
           "6 zones": tuple(np.linspace(0.0, 1.0, 7)), "12 zones": tuple(np.linspace(0.0, 1.0, 13))}
VARIATIONS = [
    ("base", {}, {}),
    ("gap 5 mm", {"gap": 0.005}, {}), ("gap 20 mm", {"gap": 0.020}, {}),
    ("heater eps 0.7", {}, {"eps_heater": 0.7}), ("heater eps 0.95", {}, {"eps_heater": 0.95}),
    ("ledge eps 0.15", {}, {"eps_ledge": 0.15}), ("ledge eps 0.6", {}, {"eps_ledge": 0.6}),
    ("contact 50", {}, {"h_contact": 50.0}), ("contact 1000", {}, {"h_contact": 1000.0}),
    ("overlap 5 mm", {"ledge_inner": 0.095}, {}), ("overlap 1 mm", {"ledge_inner": 0.099}, {}),
    ("k_Si 20", {}, {"k_wafer": 20.0}), ("k_Si 40", {}, {"k_wafer": 40.0}),
    ("rim 700 K (shielded)", {}, {"t_rim": 700.0}),
    ("heater radius 130 mm", {"heater_radius": 0.130}, {}),
]


def make(layout, geo_kw, prop_kw):
    geo = HeaterGeometry(**geo_kw)
    geo = dataclasses.replace(geo, zone_edges=tuple(f * geo.heater_radius for f in layout))
    return HeaterModel(geo, HeaterProperties(**prop_kw))


def at_mean(model, fractions, target_k, p0=3000.0):
    """Solve with power fractions, scaling the total power until the wafer mean hits target_k."""
    f = np.asarray(fractions, float)
    p_a, p_b = p0, 1.3 * p0
    t_a = model.solve(heater_power=p_a * f)["wafer_mean"]
    for _ in range(40):
        r = model.solve(heater_power=p_b * f)
        if abs(r["wafer_mean"] - target_k) < 1e-3:
            return r
        # emissive losses scale roughly as T^4: secant in T^4
        p_a, p_b, t_a = p_b, p_b + (p_b - p_a) * (target_k ** 4 - r["wafer_mean"] ** 4) / (r["wafer_mean"] ** 4 - t_a ** 4), r["wafer_mean"]
    raise RuntimeError("power iteration did not converge")


def optimize(model, target_k, iters=40):
    """Sequential linear programming for the minimax zone powers (see module docstring)."""
    n = model.n_zones
    r = at_mean(model, np.full(n, 1.0 / n), target_k)
    if n == 1:
        return r, np.array([1.0])
    p = r["zone_power"].copy()
    w = r["area_wafer"] / r["area_wafer"].sum()
    trust, best = 0.2, r
    for _ in range(iters):
        t0 = best["t_wafer"]
        s = np.empty((len(t0), n))
        for k in range(n):
            dp = np.zeros(n)
            dp[k] = 0.01 * p.sum()
            s[:, k] = (model.solve(heater_power=p + dp)["t_wafer"] - t0) / dp[k]
        m = len(t0)
        c = np.concatenate([np.zeros(n), [1.0, -1.0]])  # variables dP, upper u, lower l
        a_ub = np.vstack([np.hstack([s, -np.ones((m, 1)), np.zeros((m, 1))]),
                          np.hstack([-s, np.zeros((m, 1)), np.ones((m, 1))])])
        b_ub = np.concatenate([-t0, t0])
        a_eq = np.concatenate([w @ s, [0.0, 0.0]])[None, :]
        lim = trust * p.sum() / n
        bounds = [(max(-p[k], -lim), lim) for k in range(n)] + [(None, None), (None, None)]
        lp = linprog(c, A_ub=a_ub, b_ub=b_ub, A_eq=a_eq, b_eq=[target_k - w @ t0], bounds=bounds, method="highs")
        if lp.status != 0:
            trust *= 0.5
        else:
            p_new = np.maximum(p + lp.x[:n], 0.0)
            r_new = at_mean(model, p_new / p_new.sum(), target_k, p0=p_new.sum())
            if r_new["wafer_range"] < best["wafer_range"] - 1e-4:
                p, best = r_new["zone_power"].copy(), r_new
                continue
            trust *= 0.5
        if trust < 1e-3:
            break
    return best, p / p.sum()


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--target-c", type=float, default=740.0)
    ap.add_argument("--out", default="results/heater_zones")
    args = ap.parse_args()
    target = args.target_c + 273.15
    rows = []
    print(f"wafer temperature range (K) at a {args.target_c:g} C mean, optimized zone powers")
    print(f"{'variation':24s} " + " ".join(f"{k:>18s}" for k in LAYOUTS))
    for name, geo_kw, prop_kw in VARIATIONS:
        cells = []
        for lname, layout in LAYOUTS.items():
            model = make(layout, geo_kw, prop_kw)
            r, f = optimize(model, target)
            robust = []
            if model.n_zones > 1:
                for k in range(model.n_zones):
                    for sgn in (-1, 1):
                        pw = r["zone_power"].copy()
                        pw[k] *= 1 + sgn * 0.05
                        rr = model.solve(heater_power=pw)
                        robust.append(rr["wafer_range"])
            rows.append({"variation": name, "layout": lname, "geometry": geo_kw, "properties": prop_kw,
                         "zone_fractions": f.tolist(), "zone_power_W": r["zone_power"].tolist(),
                         "total_power_W": float(r["zone_power"].sum()), "wafer_range_K": r["wafer_range"],
                         "worst_range_5pct_zone_error_K": max(robust) if robust else None,
                         "r_wafer_m": r["r_wafer"].tolist(), "t_wafer_K": r["t_wafer"].tolist(),
                         "energy_residual_W": r["energy_residual"]})
            cells.append(f"{r['wafer_range']:6.2f} ({r['zone_power'].sum() / 1e3:4.2f} kW)"
                         + (f"[{max(robust):5.1f}]" if robust else "       "))
        print(f"{name:24s} " + " ".join(f"{c:>18s}" for c in cells), flush=True)
    print("[ ]: worst range after a +/-5 % error in one zone's power")

    manifest = build_manifest(
        "heater_zones", label="representative_chamber", validation_status="not_validated",
        inputs={"target_C": args.target_c, "layouts": LAYOUTS, "variations": [v[0] for v in VARIATIONS],
                "base_geometry": dataclasses.asdict(HeaterGeometry()), "base_properties": dataclasses.asdict(HeaterProperties())},
        outputs={"rows": rows},
        sources=[Path(__file__), ROOT / "src/mbe_twin/heater.py", ROOT / "src/mbe_twin/radiation.py"],
        warnings=["Representative geometry; heater emissivity, ledge properties, contact and Si conductivity bracketed, not sourced",
                  "Axisymmetric (rotation-averaged); heater meander, platen and shields not resolved",
                  "Gray opaque wafer (Si eps 0.7, R28); GaN-on-Si stack optics and backside roughness not included",
                  "Chamber heat loads from cells and plasma source not included; no published 200 mm heater benchmark"],
        disabled_physics=["spectral / semitransparent radiation", "gas conduction", "transients", "wafer bow"])
    print(f"Wrote {write_manifest(manifest, Path(args.out) / 'manifest.json')}")


if __name__ == "__main__":
    main()
