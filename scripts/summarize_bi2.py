"""Compare the R07 Bi + Bi2 runs (data/runs/sparta_r07/r07_bi2) with the monatomic ones (uq2_batch).

For each Bi2 run: centre-rate error against R07, noise-corrected profile RMS and bias (same
definitions as scripts/summarize_uq.py), the share of atoms arriving as Bi2, and the same
quantities for the monatomic run at the same rate and diameter. For the 3.5 A/s diameter scans
(monatomic, and Bi2 at each dimer fraction), a linear fit of bias against d gives the
zero-bias diameter; the interval uses the tolerance of summarize_uq.py (digitization 0.009,
statistics, numerics 0.005 from the monatomic checks) in quadrature. A sensitivity interval,
not a confidence interval.

Usage: python scripts/summarize_bi2.py
"""

import importlib.util
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("summarize_uq", ROOT / "scripts/summarize_uq.py")
uq = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(uq)
NUMERICS = 0.005  # largest |d_bias| of seed / timestep / cell checks at 3.5 A/s (uq2_batch)


def case_of(cfg):
    return cfg["case"]


def diameter(cfg):
    return round(cfg["diameter_m"] * 1e10, 2)


def scan_fit(points, label):
    """points: list of (d, row). Prints the zero-bias diameter and interval."""
    if len(points) < 3:
        print(f"  {label}: {len(points)} point(s), no fit")
        return None
    d = np.array([p[0] for p in points])
    b = np.array([p[1]["bias"] for p in points])
    slope, icpt = np.polyfit(d, b, 1)
    d0 = -icpt / slope
    stat = float(np.max([p[1]["bias_se"] for p in points]))
    u = float(np.sqrt(uq.DIGITIZATION ** 2 + stat ** 2 + NUMERICS ** 2))
    half = u / abs(slope)
    rms = [p[1]["rms_corr"] for p in points]
    print(f"  {label}: d {d.tolist()} bias {np.round(b, 4).tolist()} rms_corr {np.round(rms, 4).tolist()}")
    print(f"    zero-bias d {d0:.2f} A; |bias| <= {u:.4f} for d in [{d0 - half:.2f}, {d0 + half:.2f}] A")
    return d0, d0 - half, d0 + half


def main():
    mono = {k: (v, uq.row(k, v)) for k, v in uq.load(ROOT / "data/runs/sparta_r07/uq2_batch").items()}
    bi2 = {k: (v, uq.row(k, v)) for k, v in uq.load(ROOT / "data/runs/sparta_r07/r07_bi2").items()}
    print(f"{'Bi2 run':20s} {'x':>5s} {'rate err':>9s} {'rms_corr':>8s} {'bias':>8s} {'Bi2 share':>9s} | "
          f"{'monatomic':14s} {'rate err':>9s} {'rms_corr':>8s} {'bias':>8s}")
    for k, (o, r) in sorted(bi2.items()):
        c = o["config"]
        twin = [(mk, mr) for mk, (mo, mr) in mono.items()
                if case_of(mo["config"]) == c["case"] and diameter(mo["config"]) == diameter(c)
                and mo["config"]["seed"] == 12345 and "dt_factor=0.15" not in " ".join(mo["config"].get("overrides", []))
                and mo["config"]["cell_m"] == {"11": 0.6e-3}.get(c["case"], 1e-3)]
        share = o["uncertainty"].get("dimer_atom_share_centre")
        line = (f"{k:20s} {c['x_dimer']:5.3f} {r['rate_err_pct']:+8.1f}% {r.get('rms_corr', np.nan):8.4f} "
                f"{r.get('bias', np.nan):+8.4f} {100 * share if share is not None else np.nan:8.1f}% | ")
        if twin:
            mk, mr = twin[0]
            line += f"{mk:14s} {mr['rate_err_pct']:+8.1f}% {mr.get('rms_corr', np.nan):8.4f} {mr.get('bias', np.nan):+8.4f}"
        print(line)

    print("\nDiameter scans at 3.5 A/s")
    scan_fit(sorted(((diameter(o["config"]), r) for k, (o, r) in mono.items()
                     if o["config"]["case"] == "3.5" and o["config"]["seed"] == 12345
                     and o["config"]["cell_m"] == 1e-3 and o["config"]["dt_factor"] == 0.3), key=lambda p: p[0]),
             "monatomic")
    for x in sorted({o["config"]["x_dimer"] for o, _ in bi2.values()}):
        scan_fit(sorted(((diameter(o["config"]), r) for k, (o, r) in bi2.items()
                         if o["config"]["case"] == "3.5" and o["config"]["x_dimer"] == x), key=lambda p: p[0]),
                 f"Bi + Bi2, x = {x:g}")


if __name__ == "__main__":
    main()
