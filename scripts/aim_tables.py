"""Pointing ensemble and attenuation tables of a layout at another aim offset (removes two approximations of --aim-maps).

scripts/nitrogen_aim_operating.py gives only the nominal map at a new aim; realizable_controller --aim-maps
then reuses the current aim's tilt responses and attenuation tables. This script recomputes, for the new aim,
everything layout_comparison.nitrogen_maps computes for the comparison: the 49 pointing maps (+/-0.8 and
1.6 deg, 12 directions, plate and flange pivots), the background-attenuation ratio profiles on the
comparison's pressure grid and the lip ratio profiles, with the same particles, seed, radii and grid. The
gas-scattered and plume factors (scattered_tables.py, scattered_plume_tables.py) are not recomputed: they
remain those of the layout's current aim (a residual approximation, recorded in the manifest).
Use with realizable_controller.py --n-tables FILE.

Usage: python scripts/aim_tables.py --layout B-L --aim-mm 95 [--out results/aim_tables]
"""

import argparse
import importlib.util
import json
import os
import time
from pathlib import Path

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402

from mbe_twin.manifest import build_manifest, write_manifest  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("layout_comparison", ROOT / "scripts/layout_comparison.py")
lc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lc)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--layout", required=True)
    ap.add_argument("--aim-mm", type=float, required=True)
    ap.add_argument("--out", default="results/aim_tables")
    args = ap.parse_args()
    env = json.loads(lc.ENVELOPE.read_text(encoding="utf-8"))
    rho = np.linspace(0.0, env["wafer_and_mask"]["usable_radius_m"]["value"], 39)
    lay = json.loads(json.dumps(env["layouts"][args.layout]))
    lay["n"]["aim_offset_mm"] = args.aim_mm
    opening = env["wafer_and_mask"]["holder_opening_radius_m"]["value"]["1 mm overlap" if lay["heater"] != "3 zones" else "3 mm overlap"]
    t = time.time()
    states, maps, att, lip = lc.nitrogen_maps(lay, env, rho, lc.Wafer(radius=0.100), lc.P_GRID, opening)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    f = out / f"n_tables_{args.layout}_{args.aim_mm:g}mm.npz"
    np.savez(f, layout=args.layout, aim_mm=args.aim_mm, states=json.dumps(states), maps=maps, att=att, lip=lip, rho=rho,
             p_grid=np.asarray(lc.P_GRID))
    man = build_manifest(f"aim_tables_{args.layout}_{args.aim_mm:g}", label="representative_chamber",
                         inputs={"layout": args.layout, "aim_mm": args.aim_mm, "n": lay["n"], "rho": rho, "p_grid": lc.P_GRID,
                                 "n_particles": lc.N_PARTICLES, "n_seed": lc.N_SEED, "opening": opening},
                         outputs={"file": f.as_posix(), "sha256": lc.file_sha256(f), "states": len(states),
                                  "seconds": time.time() - t},
                         sources=[Path(__file__), ROOT / "scripts/layout_comparison.py"] + lc.MAP_MODULES,
                         warnings=["Gas-scattered and plume factors are not recomputed for the new aim"])
    write_manifest(man, out / f"manifest_{args.layout}_{args.aim_mm:g}mm.json")
    print(f"wrote {f} ({len(states)} states) in {time.time() - t:.0f} s")


if __name__ == "__main__":
    main()
