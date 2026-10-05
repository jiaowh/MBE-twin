"""Nominal N arrival maps over a range of aim offsets, for re-aiming at the operating point (uniformity first).

The layouts' aims were optimized for the N map at the 740 C operating pressure (nitrogen_aim_pressure /
nitrogen_aim_bigplate). With uniformity as the priority and the operating point now 720 C, the aim is
re-checked on the grown thickness: this script computes the nominal-pose N map per unit plate output
(with the 2 mm lip) for each aim offset, exactly as layout_comparison.nitrogen_maps does for the nominal
pose. scripts/realizable_controller.py --aim-maps FILE --aim-mm A then evaluates the whole ensemble with
that aim: pointing states keep their map differences from the current aim's ensemble (the tilt response
is assumed not to change over a few mm of aim; linear in tilt as checked for the residual-pointing option),
and the attenuation tables stay those of the current aim.

Usage: python scripts/nitrogen_aim_operating.py --layout B-L --aims 80 85 90 95 100 [--out results/aim_operating]
"""

import argparse
import importlib.util
import json
import os
from dataclasses import replace
from pathlib import Path

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("layout_comparison", ROOT / "scripts/layout_comparison.py")
lc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lc)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--layout", required=True)
    ap.add_argument("--aims", type=float, nargs="+", required=True, help="aim offsets (mm)")
    ap.add_argument("--out", default="results/aim_operating")
    args = ap.parse_args()
    env = json.loads(lc.ENVELOPE.read_text(encoding="utf-8"))
    rho = np.linspace(0.0, env["wafer_and_mask"]["usable_radius_m"]["value"], 39)
    wafer = lc.Wafer(radius=0.100)
    lay = env["layouts"][args.layout]
    opening = env["wafer_and_mask"]["holder_opening_radius_m"]["value"]["1 mm overlap" if lay["heater"] != "3 zones" else "3 mm overlap"]
    lc.TOLS_DEG = ()          # nominal pose only
    maps = {}
    for a in args.aims:
        lay_a = json.loads(json.dumps(lay))
        lay_a["n"]["aim_offset_mm"] = a
        states, m, _, lip = lc.nitrogen_maps(lay_a, env, rho, wafer, (0.0,), opening)
        maps[f"{a:g}"] = m[0] * lip[lc.LIP_H.index(0.002)]
        print(f"{args.layout} aim {a:g} mm: N map half-range {100 * (maps[f'{a:g}'].max() - maps[f'{a:g}'].min()) / (maps[f'{a:g}'].max() + maps[f'{a:g}'].min()):.3f} %", flush=True)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    np.savez(out / f"aim_maps_{args.layout}.npz", rho=rho, layout=args.layout,
             **{f"aim_{k}": v for k, v in maps.items()})
    print(f"wrote {out / f'aim_maps_{args.layout}.npz'}")


if __name__ == "__main__":
    main()
