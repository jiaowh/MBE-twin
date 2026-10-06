"""Heater power margin at the operating point: zone design below the element limit, and what it buys.

The zone fractions of the comparison are optimized under the 1473 K element limit, so at 720 C the
hottest element ring sits on the limit and no power is left for the controller (integrated twin,
2026-10-05: a pyrometer reading 2 K low is clamped). Here the designed-density heater (12 equal rings,
99 mm opening) is optimized under a lower design limit; the true limit stays 1473 K. For each design
limit and growth temperature:
- headroom: the total power at which the hottest ring reaches 1473 K with those fractions, over the
  operating power (the extra power the controller can command);
- the nominal wafer range (the uniformity cost);
- the combined heater errors of heater_robustness (wafer emissivity 0.63 / 0.70 / 0.77 x contact
  50 / 200 / 1000 W m^-2 K^-1 x worst +/-2 % zone error) held by the centre pyrometer at bias -2 / 0 /
  +2 K, with the power capped at the true limit: the share of states that are capped and the largest
  shortfall of the reading.

Usage: python scripts/heater_margin.py [--t-c 720 730] [--limits 1473.15 1450 1425 1400 1375]
                                       [--out results/heater_margin]
"""

import argparse
import importlib.util
import itertools
import os
from pathlib import Path

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402

from mbe_twin.manifest import build_manifest, write_manifest  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


hz = _load("heater_zones")
hr = _load("heater_robustness")
TRUE_LIMIT = 1473.15
BIASES_K = (-2.0, 0.0, 2.0)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--t-c", type=float, nargs="+", default=[720.0, 730.0])
    ap.add_argument("--limits", type=float, nargs="+", default=[1473.15, 1450.0, 1425.0, 1400.0, 1375.0])
    ap.add_argument("--out", default="results/heater_margin")
    args = ap.parse_args()
    edges = hz.LAYOUTS["12 zones"]
    geo = {"ledge_inner": hr.OPENING}
    base = hz.make(edges, geo, {})
    rows = []
    for t_c, lim in itertools.product(args.t_c, args.limits):
        t0 = t_c + 273.15
        r, frac = hz.optimize(base, t0, limits={"t_heater_max": lim})
        p_op = float(r["zone_power"].sum())
        top = hz.at_limit(base, frac, TRUE_LIMIT, p_hi=3.0 * p_op)
        headroom = float(top["zone_power"].sum() / p_op - 1.0)
        capped, short = [], []
        for eps, h, z in itertools.product(hr.EPS, hr.CONTACT, hr.ZONE):
            m = hz.make(edges, geo, {"eps_wafer": eps, "h_contact": h})
            cands = [frac]
            if z != 0.0:
                cands = []
                for k in range(m.n_zones):
                    f = frac.copy()
                    f[k] *= 1 + z
                    cands.append(f / f.sum())
            worst = max((hz.at_mean(m, f, t0, p0=p_op) for f in cands), key=lambda x: x["wafer_range"])
            f = worst["zone_power"] / worst["zone_power"].sum()
            for b in BIASES_K:
                rr, need, cap = hr._held(m, f, t0, lambda x, b=b: hz.centre_reading(x, b), TRUE_LIMIT, p_op)
                capped.append(cap)
                short.append(t0 - hz.centre_reading(rr, b) if cap else 0.0)
        row = {"T_C": t_c, "design_limit_K": lim, "operating_power_W": p_op, "headroom_pct": 100 * headroom,
               "element_max_at_operation_K": float(r["t_heater"].max()), "wafer_range_K": float(r["wafer_range"]),
               "capped_share": float(np.mean(capped)), "max_reading_shortfall_K": float(np.max(short)),
               "zone_fractions": frac.tolist()}
        rows.append(row)
        print(f"{t_c:.0f} C, design limit {lim:.1f} K: headroom {row['headroom_pct']:.1f} %, wafer range "
              f"{row['wafer_range_K']:.2f} K, capped {100 * row['capped_share']:.0f} % of 81 combined states, "
              f"largest shortfall {row['max_reading_shortfall_K']:.2f} K", flush=True)
    manifest = build_manifest(
        "heater_margin", label="representative_chamber", validation_status="not_validated",
        inputs={"t_c": args.t_c, "design_limits_K": args.limits, "true_limit_K": TRUE_LIMIT, "biases_K": BIASES_K,
                "eps": hr.EPS, "contact": hr.CONTACT, "zone_error": hr.ZONE, "opening_m": hr.OPENING},
        outputs={"rows": rows},
        sources=[Path(__file__), ROOT / "scripts/heater_zones.py", ROOT / "scripts/heater_robustness.py",
                 ROOT / "src/mbe_twin/heater.py", ROOT / "src/mbe_twin/radiation.py"],
        warnings=["Representative heater model; element rating, zone capacity and supply limits are vendor inputs",
                  "Headroom is steady-state power; transient overshoot needs are not included"])
    print(f"Wrote {write_manifest(manifest, Path(args.out) / 'manifest.json')}")


if __name__ == "__main__":
    main()
