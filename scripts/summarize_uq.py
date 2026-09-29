"""Summarize the R07 numerical-uncertainty batch (data/runs/sparta_r07/uq_batch/*.json).

For each benchmark case: profile RMS and bias against R07 and the centre-rate error, with
batch-means standard errors; seed-to-seed spread; timestep and cell effects as differences
from the base run. For the diameter scan at 3.5 A/s: a linear fit of bias against d gives the
zero-bias diameter d0; the reported interval is the set of d where |bias| stays within a
stated tolerance u, combining the digitization error of R07's curves (0.006-0.009, take
0.009), the statistical error and the numerical (timestep/cell/seed) differences in quadrature.
This is a sensitivity-based interval, not a statistical confidence interval.

Usage: python scripts/summarize_uq.py [--dir data/runs/sparta_r07/uq_batch]
"""

import argparse
import json
from pathlib import Path

import numpy as np

DIGITIZATION = 0.009


def load(d):
    runs = {}
    for f in sorted(Path(d).glob("*.json")):
        m = json.loads(f.read_text(encoding="utf-8"))
        runs[f.stem] = m["outputs"]
    return runs


def row(name, o):
    u = o["uncertainty"]["block"]
    rate = o["centre_rate_A_s"]
    out = {"run": name, "rate": rate["sparta"], "rate_se": u["rate"]["stderr"],
           "rate_err_pct": 100 * (rate["sparta"] / rate["r07"] - 1)}
    if "rms_vs_r07" in o:
        out.update(rms=o["rms_vs_r07"], rms_se=u["rms"]["stderr"], bias=o["bias_vs_r07"],
                   bias_se=u["bias"]["stderr"])
        # Statistical noise adds to the RMS in quadrature: report the noise level (RMS of the
        # per-bin standard errors) and the noise-corrected RMS, zero when unresolved.
        x = np.array(o["x_mm"])
        keep = x <= 45.0
        noise = float(np.sqrt(np.mean(np.array(o["profile_stderr"])[keep] ** 2)))
        out.update(noise=noise, rms_corr=float(np.sqrt(max(0.0, out["rms"] ** 2 - noise ** 2))))
    out["halves_rate"] = o["uncertainty"]["halves"]["rate"]
    out["np_rel_range"] = o["uncertainty"]["np_sampling"]["rel_range"]
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", default="data/runs/sparta_r07/uq_batch")
    args = ap.parse_args()
    runs = load(args.dir)
    rows = {k: row(k, v) for k, v in runs.items()}
    print(f"{'run':14s} {'rms':>7s} {'noise':>6s} {'corr':>6s} {'bias':>8s} {'+/-':>6s} {'rate A/s':>9s} {'+/-':>6s} "
          f"{'vs R07':>7s}  halves(rate)      Np range")
    for k, r in rows.items():
        print(f"{k:14s} {r.get('rms', np.nan):7.4f} {r.get('noise', np.nan):6.4f} {r.get('rms_corr', np.nan):6.4f} "
              f"{r.get("bias", np.nan):+8.4f} {r.get("bias_se", np.nan):6.4f} {r['rate']:9.4g} "
              f"{r['rate_se']:6.2g} {r['rate_err_pct']:+6.1f}%  "
              f"{r['halves_rate'][0]:.4g}/{r['halves_rate'][1]:.4g}  {100 * r['np_rel_range']:.2f}%")

    print("\nNumerical effects (difference from the base run of each case):")
    numerics = {}
    for case in ("0.35", "3.5", "11"):
        base = rows.get(f"{case}_base")
        if not base:
            continue
        for k, r in rows.items():
            if k.startswith(case + "_") and k != f"{case}_base" and not k[len(case):].startswith("_d")                     or k.startswith(case + "_dt"):
                d = {q: r[q] - base[q] for q in ("rms", "bias", "rate") if q in r}
                d["rate_pct"] = 100 * d["rate"] / base["rate"]
                numerics.setdefault(case, {})[k] = d
                print(f"  {k:14s} d_rms {d.get('rms', np.nan):+.4f}  d_bias {d.get('bias', np.nan):+.4f}  "
                      f"d_rate {d['rate_pct']:+.1f}%")

    scan = sorted(((runs[k]["config"]["diameter_m"] * 1e10, rows[k]) for k in rows
                   if (k.startswith("3.5_d") and not k.startswith("3.5_dt")) or k == "3.5_base"),
                  key=lambda item: item[0])
    if len(scan) >= 3:
        d = np.array([s[0] for s in scan])
        b = np.array([s[1]["bias"] for s in scan])
        rms = np.array([s[1]["rms"] for s in scan])
        slope, icpt = np.polyfit(d, b, 1)
        d0 = -icpt / slope
        num = [abs(v["bias"]) for v in numerics.get("3.5", {}).values()]
        stat = float(np.max([s[1]["bias_se"] for s in scan]))
        u = float(np.sqrt(DIGITIZATION ** 2 + stat ** 2 + (max(num) if num else 0.0) ** 2))
        half = u / abs(slope)
        print(f"\nDiameter scan at 3.5 A/s: d (A) {d}, bias {np.round(b, 4)}, rms {np.round(rms, 4)}")
        print(f"  bias = {slope:.4f} (d - {d0:.2f} A); tolerance u = {u:.4f} "
              f"(digitization {DIGITIZATION}, statistics {stat:.4f}, numerics {max(num) if num else 0:.4f})")
        print(f"  zero-bias diameter {d0:.2f} A; |bias| <= u for d in [{d0 - half:.2f}, {d0 + half:.2f}] A")


if __name__ == "__main__":
    main()
