"""Growth rate the nitrogen feed can supply: minimum conversion fraction for each target rate.

Uses the nominal-state nitrogen maps of the layout comparison (keyed cache files listed in its
record, checked against their stored keys) and its operating-point model: active-N output
eta x 2 x feed, pressure = feed / S_eff, direct-beam attenuation at that pressure, net rate =
delivered N - decomposition at the nominal heater state (1473 K element limit). For each
layout, growth temperature and pumping speed, and for each feed ceiling, it reports:
- the highest rate reachable at eta = 1 (every feed atom active: a bound, not an efficiency);
- the smallest eta that reaches 1, 0.5 and 0.25 um/h (above 1: unreachable at any conversion).
The ceilings are the feed-limit scenarios of the envelope (10 sccm, H02's range; 35 sccm, R26)
and the feed at which the layout's plate holes stop being free-molecular (smallest Kn = 10 over
300 / 600 K and the N2 diameter x/ 1.3), beyond which the plate model behind the N maps is not
valid. A ceiling above the plate limit is reported, but its rates are extrapolations.

If the record of scripts/nitrogen_output_evidence.py exists, the rate at its inferred high-flow eta
range is also given per row.

The rate is maximized over the feed up to the ceiling, because it peaks where attenuation
grows faster than the feed. eta is solved by bisection on that maximum (linear in eta).

Usage: python scripts/nitrogen_rate_limits.py [--record data/runs/studies/layout_comparison_bc.json]
                                              [--maps results/layout_comparison_bc]
"""

import argparse
import importlib.util
import json
import os
from pathlib import Path

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402
from scipy.optimize import brentq  # noqa: E402

from mbe_twin.growth import load_parameters  # noqa: E402
from mbe_twin.manifest import build_manifest, write_manifest  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_RECORD = ROOT / "data/runs/studies/nitrogen_output_evidence.json"
_spec = importlib.util.spec_from_file_location("layout_comparison", ROOT / "scripts/layout_comparison.py")
lc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lc)
TARGETS_UM_H = (1.0, 0.5, 0.25)
N_FEEDS = 500


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--record", default="data/runs/studies/layout_comparison_bc.json")
    ap.add_argument("--maps", default="results/layout_comparison_bc")
    ap.add_argument("--out", default="results/nitrogen_rate_limits")
    args = ap.parse_args()
    rec = json.loads((ROOT / args.record).read_text(encoding="utf-8"))
    inp = rec["inputs"]
    env = inp["envelope"]
    rho = np.asarray(rec["outputs"]["rho_m"])
    k_atoms = inp["atoms_per_m2_s_per_nm_min"]
    feed_limits = inp["feed_limits_sccm"]
    t_gas = env["vacuum"]["gas_temperature_K"]["value"]
    params = load_parameters()
    lip_i = lc.LIP_H.index(0.002)
    # eta range inferred from published high-flow growth rates (scripts/nitrogen_output_evidence.py), if recorded
    eta_ev = None
    if EVIDENCE_RECORD.exists():
        eta_ev = json.loads(EVIDENCE_RECORD.read_text(encoding="utf-8"))["outputs"].get("eta_high_flow_joint")
    rows = []
    q_kn_all = {}
    for name in inp["layouts"]:
        plate = inp["plates"][name]
        kn1 = min(lc.plate_knudsen(1.0, plate, t, f) for t in (300.0, 600.0) for f in (1.3, 1.0, 1 / 1.3))
        q_kn = kn1 / lc.KN_VALID
        q_kn_all[name] = q_kn
        print(f"{name}: plate holes free-molecular (Kn >= {lc.KN_VALID:g}) up to {q_kn:.2f} sccm")
        n = env["layouts"][name]["n"]
        prefix = f"N_{n['L_over_r']:g}_{n['polar_deg']:g}_{n['aim_offset_mm']:g}_"
        cache = next(c for c in inp["map_caches"] if c["file"].startswith(prefix))
        z = np.load(ROOT / args.maps / cache["file"], allow_pickle=False)
        if str(z["cache_key"]) != cache["key"]:
            raise SystemExit(f"nitrogen_rate_limits: {cache['file']} does not carry the key recorded in {args.record}")
        maps, att, lip = z["maps"], z["att"], z["lip"]

        def delivered(p):
            return float(lc.area_mean(maps[0] * lc.att_at(att, p) * lip[lip_i], rho))

        opening = env["wafer_and_mask"]["holder_opening_radius_m"]["value"]["1 mm overlap"]
        for t0 in lc.T0_C:
            t_maps, _ = lc.heater_states(env["layouts"][name]["heater"], opening, t0 + lc.C, lc.LIMITS["1473 K element"], rho)
            dec = float(lc.area_mean(params.decomposition(t_maps[0]), rho))
            for speed in env["vacuum"]["effective_N2_speed_m3_s"]["bracket"]:
                for ceiling, q_max in [(f"feed limit {f:g} sccm", f) for f in feed_limits] + [("plate free-molecular", q_kn)]:
                    q_max = min(q_max, lc.P_GRID[-1] * speed / (lc.SCCM_PA_M3_S * t_gas / lc.T_STD))   # attenuation table top
                    feeds = np.linspace(q_max / N_FEEDS, q_max, N_FEEDS)
                    per_atom = np.array([lc.N_ATOMS_PER_SCCM * q / k_atoms * delivered(lc.pressure_from_flow(q, speed, t_gas))
                                         for q in feeds])   # nm/min per unit eta

                    def best(eta):
                        return float(np.max(eta * per_atom) - dec) * 0.06   # um/h; the argmax does not depend on eta
                    i = int(np.argmax(per_atom))
                    row = {"layout": name, "T0_C": t0, "S_eff_m3_s": speed, "ceiling": ceiling, "feed_ceiling_sccm": q_max,
                           "max_rate_eta1_um_h": best(1.0), "best_feed_sccm": float(feeds[i]),
                           "best_pressure_Pa": lc.pressure_from_flow(feeds[i], speed, t_gas),
                           "eta_min": {f"{t:g}": brentq(lambda e: best(e) - t, 1e-4, 100.0) for t in TARGETS_UM_H}}
                    if eta_ev:
                        row["rate_at_evidence_eta_um_h"] = {f"{e:.3f}": best(e) for e in eta_ev}
                    rows.append(row)
                    print(f"{name} {t0:.0f} C S {speed:g} {ceiling:20s} (<= {q_max:5.2f} sccm): max {row['max_rate_eta1_um_h']:.2f} um/h "
                          f"at {row['best_feed_sccm']:.2f} sccm; eta for 1 / 0.5 / 0.25 um/h: "
                          + " / ".join(f"{v:.2f}" for v in row["eta_min"].values()), flush=True)
    manifest = build_manifest(
        "nitrogen_rate_limits", label="representative_chamber", validation_status="not_validated",
        inputs={"record": args.record, "map_caches": inp["map_caches"], "targets_um_h": TARGETS_UM_H, "n_feeds": N_FEEDS,
                "kn_valid": lc.KN_VALID, "plates": inp["plates"]},
        outputs={"feed_at_kn_valid_sccm": q_kn_all, "rows": rows},
        sources=[Path(__file__), ROOT / "scripts/layout_comparison.py", ROOT / "scripts/heater_zones.py",
                 *([EVIDENCE_RECORD] if EVIDENCE_RECORD.exists() else []),
                 ROOT / "src/mbe_twin/vacuum.py", ROOT / "src/mbe_twin/growth.py", ROOT / args.record],
        warnings=["eta is a missing source input; eta_min above 1 means the rate is unreachable at any conversion",
                  "Nominal state only; direct-beam attenuation, scattered atoms not redeposited",
                  "Pressure from the N2 feed alone (atoms recombine on the walls); other gas loads not included"])
    print(f"Wrote {write_manifest(manifest, Path(args.out) / 'manifest.json')}")


if __name__ == "__main__":
    main()
