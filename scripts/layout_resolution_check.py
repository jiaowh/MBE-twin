"""Radial resolution and ratio-profile check of the layout comparison's nominal state.

scripts/layout_comparison.py evaluates thickness on 39 radii (0-94 mm) and applies background
attenuation and the holder-lip shadow as ratio profiles interpolated over a pressure grid. This
script recomputes the nominal state of each layout (nominal pointing, 70 mm fill, d = 8 A,
nominal heater, 2 mm lip, Ref14 droplet law) at the operating point recorded for one scenario,
with the N flux computed directly at that pressure with the lip in place, on 39, 77 and 153
radii. It reports thickness half-range/mean and area-weighted std/mean against the record.

Usage: python scripts/layout_resolution_check.py [--record data/runs/studies/layout_comparison_bc.json]
                                                 [--eta 1.0 --speed 2.0 --t0 740 --limit "1473 K element" --target 1]
"""

import argparse
import importlib.util
import json
import os
from pathlib import Path

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402

from mbe_twin.aperture import aperture_plate_sources, hex_holes  # noqa: E402
from mbe_twin.beam import HolderLip, Wafer, rotation_averaged_flux  # noqa: E402
from mbe_twin.crucible import Crucible, simulate  # noqa: E402
from mbe_twin.growth import load_parameters  # noqa: E402
from mbe_twin.layout import SourcePort  # noqa: E402
from mbe_twin.manifest import build_manifest, write_manifest  # noqa: E402
from mbe_twin.vacuum import beam_mean_free_path  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("layout_comparison", ROOT / "scripts/layout_comparison.py")
lc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lc)
GRIDS = (39, 77, 153)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--record", default="data/runs/studies/layout_comparison_bc.json")
    ap.add_argument("--eta", type=float, default=1.0)
    ap.add_argument("--speed", type=float, default=2.0)
    ap.add_argument("--t0", type=float, default=740.0)
    ap.add_argument("--limit", default="1473 K element")
    ap.add_argument("--target", default="1", help="row target label (1, 0.5, 0.25 or max)")
    ap.add_argument("--out", default="results/layout_resolution_check")
    args = ap.parse_args()
    rec = json.loads((ROOT / args.record).read_text(encoding="utf-8"))
    env = rec["inputs"]["envelope"]
    k_atoms = rec["inputs"]["atoms_per_m2_s_per_nm_min"]
    params = load_parameters()
    wafer = Wafer(radius=0.100)
    usable = env["wafer_and_mask"]["usable_radius_m"]["value"]
    vac = env["vacuum"]
    out_rows = []
    for name in rec["inputs"]["layouts"]:
        row = next(r for r in rec["outputs"]["rows"] if r["layout"] == name and r["eta"] == args.eta
                   and r["S_eff_m3_s"] == args.speed and r["T0_C"] == args.t0 and r["heater_limit"] == args.limit
                   and r["target"] == args.target)
        lay = env["layouts"][name]
        n = lay["n"]
        p = row["operating_point"]["pressure_Pa"]
        rate = row["operating_point"]["rate_nm_min"]
        opening = env["wafer_and_mask"]["holder_opening_radius_m"]["value"]["1 mm overlap" if lay["heater"] != "3 zones" else "3 mm overlap"]
        lip = HolderLip((0.0, 0.0, 0.0), tuple(wafer.normal), opening, 0.002)
        ev = simulate(Crucible(1e-4, n["L_over_r"] * 1e-4), lc.N_PARTICLES, rng=lc.N_SEED)
        port = SourcePort("N", polar_deg=n["polar_deg"], azimuth_deg=0.0, throw=env["chamber"]["source_throw_m"]["value"],
                          aim_offset=n["aim_offset_mm"] / 1e3)
        pos, ax = port.pose(wafer)
        src = aperture_plate_sources("N", wafer, ev, hex_holes(0.020, 0.010), throw=port.throw,
                                     polar_angle=np.radians(port.polar_deg), azimuth=0.0, total_rate=1.0,
                                     aim_offset=port.aim_offset, axis=ax, centre=pos)
        mfp = beam_mean_free_path(p, vac["collision_diameters_m"]["N"], 14.007, vac["beam_temperatures_K"]["N"])
        res = {}
        for m in GRIDS:
            rho = np.linspace(0.0, usable, m)
            n_map = rotation_averaged_flux(src, wafer, rho, n_angles=36, mean_free_path=mfp, occluders=(lip,))
            att, lipg = lc.ga_ratios(lay["ga_port_deg"], 70, rho, wafer, [p], opening, env)
            g = lc.ga_shape(lc.ga_record(lay["ga_port_deg"], 70, "8"), rho) * att["8"][0] * lipg[1]
            t_maps, _ = lc.heater_states(lay["heater"], opening, args.t0 + lc.C, rec["inputs"]["heater_limits_K"][args.limit], rho)
            r = lc.evaluate(n_map[None, None, :], (g / g[0])[None, None, :], t_maps[:1], params, "Ref14_growth", rho, rate,
                            k_atoms, (0, 0, 0, 0))
            res[m] = {"thickness_pct": float(r["thickness"][0, 0, 0, 0]), "std_pct": float(r["std"][0, 0, 0, 0]),
                      "rate_nm_min": float(r["mean_net"][0, 0, 0, 0])}
            print(f"{name}: {m:3d} radii, direct at {p:.2e} Pa: thickness {res[m]['thickness_pct']:.3f} %, "
                  f"std {res[m]['std_pct']:.3f} %", flush=True)
        print(f"{name}: record (39 radii, ratio profiles): thickness {row['nominal']['thickness_pct']:.3f} %, "
              f"std {row['nominal']['std_pct']:.3f} %")
        out_rows.append({"layout": name, "pressure_Pa": p, "rate_nm_min": rate, "direct": res,
                         "record_nominal": row["nominal"]})
    manifest = build_manifest(
        "layout_resolution_check", label="representative_chamber", validation_status="verified_numerically",
        inputs={"record": args.record, "eta": args.eta, "speed": args.speed, "t0_C": args.t0, "limit": args.limit,
                "target": args.target,
                "grids": GRIDS},
        outputs={"rows": out_rows},
        sources=[Path(__file__), ROOT / "scripts/layout_comparison.py", ROOT / "scripts/heater_zones.py",
                 ROOT / "src/mbe_twin/beam.py", ROOT / "src/mbe_twin/aperture.py", ROOT / "src/mbe_twin/growth.py"],
        warnings=["Nominal state only; the Monte Carlo event sample is the same seed as the comparison"])
    print(f"Wrote {write_manifest(manifest, Path(args.out) / 'manifest.json')}")


if __name__ == "__main__":
    main()
