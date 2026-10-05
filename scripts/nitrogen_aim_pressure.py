"""Nitrogen aim and port angle re-optimized at the growth pressure the nitrogen feed itself creates.

The aims of layouts B and C are free-molecular optima found in vacuum (nitrogen_aim_study.py).
The coupled operating point of scripts/layout_comparison.py showed that the pressure each
layout's own N2 feed creates (4.8e-3 Pa for B, 7.1e-3 Pa for C at 1 um/h, eta = 1, 2 m^3/s)
moves those optima: C's nominal thickness rose from 0.35 to 0.94 %. This scan repeats the
aim/angle search with the attenuation in place.

For each port angle and aim offset (L/r 2.92 plate, 20 mm active radius, 350 mm throw, as the
comparison), the rotation-averaged N flux on r <= 94 mm with the 2 mm holder lip (1 mm overlap
holder) is computed at the pressures of P_SCAN. Then, per aim:
- the self-consistent operating point for each target rate (1 / 0.5 um/h) at eta = 1 and
  S_eff = 2 m^3/s (layout_comparison.operating_point; attenuation interpolated in log between
  the scan pressures), and the N-limited thickness half-range/mean there, with decomposition
  at the nominal 740 C heater map;
- the same at the feed-limit pressure (10 sccm into 2 m^3/s), the pressure of any eta < 1
  operating point that is feed-limited.
The best aim per port angle, and overall, is reported for each case, with the active N it
needs. A lower demand lowers the pressure, so the optimum is a trade between map shape and
demand; both are reported. Pointing robustness of the new optima is evaluated afterwards by
scripts/layout_comparison.py (layouts B-p, C-p in the envelope).

Options --aspect, --plate-radius, --eta, --speed and --feed-max set another plate and operating point
(the large-plate variant: --aspect 2.0 --plate-radius 0.03 --eta 0.3 --speed 4 --feed-max 35).

--scattered VARIANT --factor-layout NAME (with --combine): the attenuation of every aim is multiplied by
the scattered-arrival factor of layout NAME (layout_comparison.scatter_factors: gas-scattered atoms,
and with gas+plume the plate's plume at --speed), interpolated in log onto the scan pressures. The
factor belongs to that layout's own aim and angle; it varies little with the aim, so the re-aim is
meaningful near that layout (same plate, same port angle), not across port angles.

Usage: python scripts/nitrogen_aim_pressure.py --angles 46 55 65 --out results/nitrogen_aim_pressure_a
       python scripts/nitrogen_aim_pressure.py --combine results/nitrogen_aim_pressure_a results/nitrogen_aim_pressure_b
                                               [--scattered gas+plume --factor-layout B-p]
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

from mbe_twin.aperture import aperture_plate_sources, hex_holes  # noqa: E402
from mbe_twin.beam import HolderLip, Wafer, rotation_averaged_flux  # noqa: E402
from mbe_twin.crucible import Crucible, simulate  # noqa: E402
from mbe_twin.growth import load_parameters  # noqa: E402
from mbe_twin.layout import SourcePort  # noqa: E402
from mbe_twin.manifest import build_manifest, write_manifest  # noqa: E402
from mbe_twin.vacuum import beam_mean_free_path, pressure_from_flow  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("layout_comparison", ROOT / "scripts/layout_comparison.py")
lc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lc)
P_SCAN = (0.0, 2.5e-3, 5e-3, 7.5e-3, 1e-2, 1.5e-2, 2.5e-2)
ANGLES = (40.0, 46.0, 50.0, 55.0, 60.0, 65.0)
OFFSETS_MM = tuple(np.arange(45.0, 150.1, 7.5))
TARGETS_UM_H = (1.0, 0.5)
L_OVER_R = 2.92
PLATE_RADIUS = 0.020
ETA, SPEED = 1.0, 2.0


def scan(angles, offsets, env, rho, wafer, aspect=L_OVER_R, plate_radius=PLATE_RADIUS):
    ev = simulate(Crucible(1e-4, aspect * 1e-4), lc.N_PARTICLES, rng=lc.N_SEED)
    holes = hex_holes(plate_radius, plate_radius / 2)
    vac = env["vacuum"]
    d_n, t_n = vac["collision_diameters_m"]["N"], vac["beam_temperatures_K"]["N"]
    opening = env["wafer_and_mask"]["holder_opening_radius_m"]["value"]["1 mm overlap"]
    lip = HolderLip((0.0, 0.0, 0.0), tuple(wafer.normal), opening, 0.002)
    out = []
    for angle in angles:
        for off in offsets:
            t = time.time()
            port = SourcePort("N", polar_deg=angle, azimuth_deg=0.0, throw=env["chamber"]["source_throw_m"]["value"],
                              aim_offset=off / 1e3)
            pos, ax = port.pose(wafer)
            src = aperture_plate_sources("N", wafer, ev, holes, throw=port.throw, polar_angle=np.radians(angle),
                                         azimuth=0.0, total_rate=1.0, aim_offset=port.aim_offset, axis=ax, centre=pos)
            maps = [rotation_averaged_flux(src, wafer, rho, n_angles=36, occluders=(lip,),
                                           mean_free_path=beam_mean_free_path(p, d_n, 14.007, t_n)) for p in P_SCAN]
            out.append({"angle_deg": angle, "offset_mm": float(off), "maps": np.array(maps).tolist()})
            print(f"angle {angle:g} offset {off:g}: {time.time() - t:.0f} s", flush=True)
    return out


def evaluate(rows, env, rho, dec_map, k_atoms, eta=ETA, speed=SPEED, feed_max=None, p_scan=P_SCAN, factor=None):
    """factor: optional (len(p_scan), rho) multiplier of every aim's attenuation (scattered arrival)."""
    t_gas = env["vacuum"]["gas_temperature_K"]["value"]
    feed_max = feed_max or env["nitrogen_source"]["feed_limit_sccm"]["value"]
    dec_mean = float(lc.area_mean(dec_map, rho))
    p_limit = pressure_from_flow(feed_max, speed, t_gas)
    res = []
    for r in rows:
        maps = np.array(r["maps"])
        att = maps / maps[0] * (1.0 if factor is None else factor)

        def at(p):
            return maps[0] * lc.att_at(att, p, p_scan)

        def delivered(p):
            return float(lc.area_mean(at(p), rho))

        def thickness(m, rate_nm_min):
            s = (rate_nm_min + dec_mean) / float(lc.area_mean(m, rho))
            h = s * m - dec_map
            return float(100 * (h.max() - h.min()) / (2 * lc.area_mean(h, rho))), s * k_atoms

        cases = {"vacuum": {}}
        th, q = thickness(maps[0], 1000.0 / 60.0)
        cases["vacuum"] = {"thickness_pct": th, "q_atoms_s": q}
        for tgt in TARGETS_UM_H:
            op = lc.operating_point(delivered, dec_mean, 1000.0 * tgt / 60.0, eta, speed, feed_max, t_gas, k_atoms)
            th, q = thickness(at(op["pressure_Pa"]), op["rate_nm_min"])
            cases[f"{tgt:g} um/h self-consistent"] = {"thickness_pct": th, "q_atoms_s": q, "pressure_Pa": op["pressure_Pa"],
                                                      "feed_sccm": op["feed_sccm"], "target_reached": op["target_reached"]}
        th, q = thickness(at(p_limit), 1000.0 / 60.0)
        cases["feed-limit pressure"] = {"thickness_pct": th, "pressure_Pa": p_limit}
        res.append({"angle_deg": r["angle_deg"], "offset_mm": r["offset_mm"], "cases": cases})
    return res


def best_by(res, case, angle=None):
    pool = [r for r in res if angle is None or r["angle_deg"] == angle]
    return min(pool, key=lambda r: r["cases"][case]["thickness_pct"])


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--angles", nargs="+", type=float, default=list(ANGLES))
    ap.add_argument("--offsets", nargs="+", type=float, default=list(OFFSETS_MM))
    ap.add_argument("--out", default="results/nitrogen_aim_pressure")
    ap.add_argument("--combine", nargs="+", help="combine the scan files of these output directories")
    ap.add_argument("--aspect", type=float, default=L_OVER_R, help="hole L/r of the plate")
    ap.add_argument("--plate-radius", type=float, default=PLATE_RADIUS, help="active plate radius (m)")
    ap.add_argument("--eta", type=float, default=ETA, help="active-N fraction of the feed atoms for the operating point")
    ap.add_argument("--speed", type=float, default=SPEED, help="effective N2 pumping speed (m^3/s)")
    ap.add_argument("--feed-max", type=float, help="feed limit (sccm); default the envelope's")
    ap.add_argument("--scattered", default="none", choices=lc.SCATTER_VARIANTS, help="add gas-scattered atoms (with --combine)")
    ap.add_argument("--factor-layout", help="layout whose scattered-arrival factors are applied (with --scattered)")
    args = ap.parse_args()
    env = json.loads(lc.ENVELOPE.read_text(encoding="utf-8"))
    usable = env["wafer_and_mask"]["usable_radius_m"]["value"]
    rho = np.linspace(0.0, usable, 39)
    wafer = Wafer(radius=0.100)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if not args.combine:
        rows = scan(args.angles, args.offsets, env, rho, wafer, args.aspect, args.plate_radius)
        (out / "scan.json").write_text(json.dumps({"p_scan": P_SCAN, "rho": rho.tolist(), "aspect": args.aspect,
                                                   "plate_radius_m": args.plate_radius, "rows": rows}), encoding="utf-8",
                                       newline="\n")
        print(f"wrote {out / 'scan.json'}")
        return
    rows, grids = [], set()
    for d in args.combine:
        scan_file = json.loads((Path(d) / "scan.json").read_text(encoding="utf-8"))
        rows += scan_file["rows"]
        grids.add(tuple(scan_file["p_scan"]))
    if len(grids) != 1:
        raise SystemExit("nitrogen_aim_pressure: scans to combine were made on different pressure grids")
    p_scan = grids.pop()
    params = load_parameters()
    t_maps, _ = lc.heater_states("designed density", env["wafer_and_mask"]["holder_opening_radius_m"]["value"]["1 mm overlap"],
                                 740.0 + lc.C, lc.LIMITS["1473 K element"], rho)
    gp = json.loads((ROOT / "data/parameters/gan_growth.json").read_text(encoding="utf-8"))
    k_atoms = gp["units"]["ml_per_s_per_nm_per_min"] * 1.14e19
    factor, scatter = None, lc.scatter_factors(args.scattered, rho)
    if scatter is not None:
        if not args.factor_layout:
            raise SystemExit("nitrogen_aim_pressure: --scattered needs --factor-layout")
        f_n = scatter["N"][args.factor_layout]
        if "N_plume" in scatter:
            f_n = scatter["N_plume"][args.factor_layout].get(f"{args.speed:g}", f_n)
        factor = np.array([lc.att_at(f_n, p) for p in p_scan])
    res = evaluate(rows, env, rho, params.decomposition(t_maps[0]), k_atoms, args.eta, args.speed, args.feed_max, p_scan,
                   factor)
    summary = {}
    for case in res[0]["cases"]:
        per_angle = {}
        for angle in sorted({r["angle_deg"] for r in res}):
            b = best_by(res, case, angle)
            per_angle[f"{angle:g}"] = {"offset_mm": b["offset_mm"], **b["cases"][case]}
        b = best_by(res, case)
        summary[case] = {"best": {"angle_deg": b["angle_deg"], "offset_mm": b["offset_mm"], **b["cases"][case]},
                         "per_angle": per_angle}
        print(f"\n{case}: best {b['angle_deg']:g} deg / +{b['offset_mm']:g} mm, {b['cases'][case]['thickness_pct']:.2f} %")
        for a, v in per_angle.items():
            extra = f", q {v['q_atoms_s']:.2e}" if "q_atoms_s" in v else ""
            extra += f", p {v['pressure_Pa']:.1e} Pa" if "pressure_Pa" in v else ""
            print(f"  {a:>3s} deg: +{v['offset_mm']:5.1f} mm  {v['thickness_pct']:.2f} %{extra}")
    for name, (angle, off) in {"B": (46.0, 105.0), "C": (65.0, 75.0)}.items():
        r = next((x for x in res if x["angle_deg"] == angle and abs(x["offset_mm"] - off) < 1e-6), None)
        if r:
            print(f"current {name} ({angle:g} deg, +{off:g} mm): " + ", ".join(
                f"{c} {v['thickness_pct']:.2f} %" for c, v in r["cases"].items()))
    manifest = build_manifest(
        "nitrogen_aim_pressure", label="representative_chamber", validation_status="not_validated",
        inputs={"p_scan_Pa": p_scan, "angles_deg": sorted({r["angle_deg"] for r in res}),
                "offsets_mm": sorted({r["offset_mm"] for r in res}), "L_over_r": args.aspect,
                "plate_radius_m": args.plate_radius, "eta": args.eta, "S_eff_m3_s": args.speed, "feed_max_sccm": args.feed_max,
                "targets_um_h": TARGETS_UM_H, "n_particles": lc.N_PARTICLES, "n_seed": lc.N_SEED, "usable_radius_m": usable,
                "lip_height_m": 0.002, "T0_C": 740.0, "heater_limit": "1473 K element", "scattered": args.scattered,
                "factor_layout": args.factor_layout},
        outputs={"summary": summary, "aims": res},
        sources=[Path(__file__), ROOT / "scripts/layout_comparison.py", ROOT / "scripts/heater_zones.py",
                 ROOT / "src/mbe_twin/aperture.py", ROOT / "src/mbe_twin/beam.py", ROOT / "src/mbe_twin/crucible.py",
                 ROOT / "src/mbe_twin/layout.py", ROOT / "src/mbe_twin/vacuum.py", ROOT / "src/mbe_twin/growth.py",
                 lc.ENVELOPE] + lc.scatter_sources(scatter),
        warnings=["Nominal pose only; pointing robustness of new optima is evaluated by layout_comparison.py",
                  ("Direct-beam attenuation only; scattered atoms not redeposited" if scatter is None else
                   f"Scattered arrival ({args.scattered}) from layout {args.factor_layout}'s factors, applied to every aim"),
                  "Free-molecular plate; uniform output; Monte Carlo scatter about 0.3-0.5 points at single aims"])
    print(f"Wrote {write_manifest(manifest, out / 'manifest.json')}")


if __name__ == "__main__":
    main()
