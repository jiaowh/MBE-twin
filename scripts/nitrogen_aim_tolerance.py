"""Pointing-tolerant nitrogen aim: the aim minimizing the worst case within a pointing error.

Reads the fine aim scans (5 mm steps at 55 / 60 / 65 deg) written by
    python scripts/nitrogen_aim_study.py --aspects A --offsets ... --angles 55 60 65
        --out results/nitrogen_aim_fine_A
and, for each plate and angle, reports:
- the nominal optimum (lowest range/mean on the grid);
- the robust optimum for a pointing tolerance of +/-5 and +/-10 mm at the wafer (+/-0.8 and
  +/-1.6 deg at 350 mm): the grid aim whose worst range/mean over grid points within the
  tolerance is lowest, with that worst value.
Aims whose tolerance window runs off the scanned grid are skipped. All scans of one plate use
the same hole events (common random numbers), so differences between aims are smoother than
the 0.3-0.5 point Monte Carlo scatter of the absolute level.

Usage: python scripts/nitrogen_aim_tolerance.py [--out results/nitrogen_aim_tolerance]
"""

import argparse
import json
from pathlib import Path

import numpy as np

from mbe_twin.manifest import build_manifest, write_manifest

ROOT = Path(__file__).resolve().parents[1]
TOLERANCES_MM = (5, 10)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="results/nitrogen_aim_tolerance")
    args = ap.parse_args()
    rows = []
    for path in sorted(ROOT.glob("results/nitrogen_aim_fine_*/manifest.json")):
        for r in json.loads(path.read_text(encoding="utf-8"))["outputs"]["rows"]:
            offs = np.asarray(r["offsets_mm"], float)
            grid = np.asarray(r["range_over_mean_pct"], float)
            for k, angle in enumerate(r["angles_deg"]):
                col = grid[:, k]
                j = int(np.argmin(col))
                row = {"L_over_r": r["L_over_r"], "angle_deg": angle, "nominal": {"offset_mm": offs[j], "pct": col[j]}}
                for tol in TOLERANCES_MM:
                    best = None
                    for i, o in enumerate(offs):
                        if o - tol < offs[0] or o + tol > offs[-1]:
                            continue
                        worst = float(col[np.abs(offs - o) <= tol + 1e-9].max())
                        if best is None or worst < best[1]:
                            best = (float(o), worst, float(col[i]))
                    row[f"robust_{tol}mm"] = (None if best is None else
                                              {"offset_mm": best[0], "worst_pct": best[1], "nominal_pct_there": best[2]})
                rows.append(row)
    print("plate   angle  nominal best         robust +/-5 mm (worst)        robust +/-10 mm (worst)")
    for row in rows:
        r5, r10 = row["robust_5mm"], row["robust_10mm"]
        fmt = lambda r: "-" if r is None else f"{r['offset_mm']:+.0f} mm: {r['worst_pct']:.2f} % (nominal {r['nominal_pct_there']:.2f})"
        print(f"L/r {row['L_over_r']:5.2f} {row['angle_deg']:4.0f}   {row['nominal']['offset_mm']:+.0f} mm {row['nominal']['pct']:.2f} %   "
              f"{fmt(r5):32s} {fmt(r10)}")
    manifest = build_manifest(
        "nitrogen_aim_tolerance", label="representative_chamber", validation_status="not_validated",
        inputs={"tolerances_mm": TOLERANCES_MM, "scans": [str(p.relative_to(ROOT)) for p in sorted(ROOT.glob("results/nitrogen_aim_fine_*/manifest.json"))]},
        outputs={"rows": rows}, sources=[Path(__file__), ROOT / "scripts/nitrogen_aim_study.py"],
        warnings=["Radial pointing error only (along the source azimuth); lateral error is second order under rotation",
                  "Free-molecular straight holes; Monte Carlo scatter 0.3-0.5 points on the absolute level"])
    print(f"Wrote {write_manifest(manifest, Path(args.out) / 'manifest.json')}")


if __name__ == "__main__":
    main()
