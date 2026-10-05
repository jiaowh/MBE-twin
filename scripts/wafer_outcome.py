"""Baseline versus candidate layout: predicted thickness maps and outcome metrics (representative).

First end-to-end use of the Stage A models, in the form the improvement protocol asks for
(docs/DATA_AND_VALIDATION_PLAN.md): baseline and candidate thickness maps on the same 200 mm
wafer, the primary metric thickness half-range/mean (%) and the companion area-weighted std (%),
and the predicted change in percentage points. Every input is a representative-chamber model
with the uncertainties recorded in the notes; this is a predicted comparison, not a
demonstrated improvement.

Chain per configuration:
- Ga: a recorded DSMC run (data/runs/sparta_ga, d = 8 A), order-4 annulus fit, normalized.
- N: aperture plate (free-molecular, straight holes, 20 mm active radius, uniform output) at a
  port angle and aim offset, rotation-averaged; the centre active-N flux gives 1 um/h.
- Wafer temperature: the axisymmetric heater model with its zone powers optimized for a
  T0 wafer mean (scripts/heater_zones.py).
- Growth: mbe_twin.growth steady state (droplet-onset scenario Ref14 by default); the centre
  Ga/N ratio is set to the middle of the Ga-rich window. Points outside the window are flagged.

Configurations: each subsystem has a baseline and a candidate option, and all 8 combinations
are evaluated, so each change's contribution is visible rather than credited to the whole
package:
- Ga: 46 deg port with a depleted 120 mm charge (baseline) or the 58 deg optimum (candidate);
- N: plate aimed at the wafer centre at 45 deg (baseline) or at its aim optimum (candidate), for
  two plates: R30-type holes in a 1 mm plate (L/r 5.8; optimum +105 mm, 65 deg) and a thin plate
  (L/r 0; optimum +55 mm, 45 deg);
- heater: 3 uniform zones on a 3 mm ledge overlap (baseline) or a designed power density
  (12-zone proxy) on a 1 mm overlap (candidate).
Growth temperatures 700 and 740 C.

Usage: python scripts/wafer_outcome.py [--out results/wafer_outcome]
"""

import argparse
import importlib.util
import json
import os
from pathlib import Path

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402

from mbe_twin import profile_fit  # noqa: E402
from mbe_twin.aperture import aperture_plate_sources, hex_holes  # noqa: E402
from mbe_twin.beam import Wafer, rotation_averaged_flux  # noqa: E402
from mbe_twin.crucible import Crucible, simulate  # noqa: E402
from mbe_twin.growth import load_parameters, steady_state  # noqa: E402
from mbe_twin.manifest import build_manifest, write_manifest  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("heater_zones", ROOT / "scripts/heater_zones.py")
hz = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hz)

WAFER_RADIUS = 0.100
RHO = np.linspace(0.0, WAFER_RADIUS, 41)
EDGES = np.linspace(0.0, WAFER_RADIUS, 21)
J_N0 = 1000.0 / 60.0
C = 273.15
GA = {"baseline": "ga_batch/fill120_d8.json", "candidate": "ga_angle/fill120_d8_58deg.json"}
PLATES = {"L/r 5.8": {"aspect": 5.83, "baseline": (0.0, 45.0), "candidate": (105.0, 65.0)},
          "thin plate": {"aspect": 0.0, "baseline": (0.0, 45.0), "candidate": (55.0, 45.0)}}
HEATER = {"baseline": ("3 zones", {}), "candidate": ("12 zones", {"ledge_inner": 0.099})}
T0_C = (700.0, 740.0)


def ga_map(record):
    o = json.loads((ROOT / "data/runs/sparta_ga" / record).read_text(encoding="utf-8"))["outputs"]
    coef = profile_fit.annulus_fit(np.asarray(o["dsmc_flux"]), EDGES, WAFER_RADIUS, 4, np.asarray(o["dsmc_flux_stderr"]))
    f = profile_fit.evaluate(coef, RHO, WAFER_RADIUS)
    return f / f[0]


def n_map(aspect, offset_mm, angle_deg, particles=20_000):
    ev = simulate(Crucible(0.1e-3, aspect * 0.1e-3), particles, rng=81)
    wafer = Wafer(radius=WAFER_RADIUS)
    holes = hex_holes(0.020, 0.010)
    src = aperture_plate_sources("N", wafer, ev, holes, throw=0.350, polar_angle=np.radians(angle_deg), azimuth=0.0,
                                 total_rate=1.0, aim_offset=offset_mm / 1e3)
    f = rotation_averaged_flux(src, wafer, RHO, n_angles=36)
    return f / f[0]


def t_map(layout, geometry, t0_k):
    model = hz.make(hz.LAYOUTS[layout], geometry, {})
    r, _ = hz.optimize(model, t0_k)
    return np.interp(RHO, r["r_wafer"], r["t_wafer"]), r["wafer_range"]


def metrics(h):
    w = RHO / RHO.sum()
    mean = float(np.sum(w * h) / np.sum(w))
    std = float(np.sqrt(np.sum(w * (h - mean) ** 2) / np.sum(w)))
    return {"half_range_over_mean_pct": float(100 * (h.max() - h.min()) / (2 * mean)), "std_pct": 100 * std / mean,
            "mean_nm_min": mean}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--scenario", default="Ref14_growth")
    ap.add_argument("--out", default="results/wafer_outcome")
    args = ap.parse_args()
    params = load_parameters()
    rows = []
    ga = {k: ga_map(v) for k, v in GA.items()}
    nmaps = {(p, k): n_map(v["aspect"], *v[k]) for p, v in PLATES.items() for k in ("baseline", "candidate")}
    for t0 in T0_C:
        tmaps = {k: t_map(*v, t0 + C) for k, v in HEATER.items()}
        for plate in PLATES:
            print(f"\n{t0:.0f} C, {plate}: thickness half-range/mean % (std %) by Ga / N aim / heater option")
            res = {}
            for gk in ("baseline", "candidate"):
                for nk in ("baseline", "candidate"):
                    for hk in ("baseline", "candidate"):
                        g, n = ga[gk], nmaps[(plate, nk)]
                        t, t_range = tmaps[hk]
                        f_crit = params.critical_excess(args.scenario, t)
                        lo, hi = float(np.max(n / g)), float(np.min((n + f_crit / J_N0) / g))
                        r0 = 0.5 * (lo + hi) if hi > lo else lo * 1.02
                        st = steady_state(r0 * J_N0 * g, J_N0 * n, t, params, args.scenario)
                        m = metrics(st["net_growth"])
                        regimes = {k: int(np.sum(st["regime"] == k)) for k in ("N-rich", "Ga-adlayer", "droplets")}
                        m.update({"window": [lo, hi], "window_empty": hi <= lo, "centre_ga_n": r0, "regime_points": regimes,
                                  "t_range_K": t_range, "n_range_over_mean_pct": float(100 * (n.max() - n.min()) / n.mean())})
                        res[(gk, nk, hk)] = m
                        rows.append({"T0_C": t0, "plate": plate, "ga": gk, "n_aim": nk, "heater": hk, **m,
                                     "thickness_relative": (st["net_growth"] / m["mean_nm_min"]).tolist()})
                        flag = " window EMPTY: droplets or N-rich somewhere" if hi <= lo else ""
                        print(f"  Ga {gk:9s} N {nk:9s} heater {hk:9s}: {m['half_range_over_mean_pct']:6.2f} ({m['std_pct']:5.2f})"
                              f"  [N {m['n_range_over_mean_pct']:5.1f} %, T range {t_range:4.1f} K, window {hi - lo:+.3f}]{flag}",
                              flush=True)
            b, c = res[("baseline",) * 3], res[("candidate",) * 3]
            print(f"  all baseline -> all candidate: {b['half_range_over_mean_pct'] - c['half_range_over_mean_pct']:.2f} points")

    manifest = build_manifest(
        "wafer_outcome", label="representative_chamber", validation_status="not_validated",
        inputs={"ga": GA, "plates": PLATES, "heater": HEATER, "T0_C": T0_C, "scenario": args.scenario, "J_N0_nm_min": J_N0},
        outputs={"rows": rows, "rho_m": RHO},
        sources=[Path(__file__), ROOT / "scripts/heater_zones.py", ROOT / "src/mbe_twin/growth.py",
                 ROOT / "src/mbe_twin/heater.py", ROOT / "src/mbe_twin/aperture.py", ROOT / "data/parameters/gan_growth.json"],
        warnings=["Predicted representative-chamber comparison; no model in the chain is validated on the proposed machine",
                  "N map free-molecular with an assumed plate; heater reduced model with bracketed parameters",
                  "Pointing errors and heater perturbations are not included here (see the nitrogen and heater studies)"],
        disabled_physics=["transients", "morphology", "AlN"])
    print(f"Wrote {write_manifest(manifest, Path(args.out) / 'manifest.json')}")


if __name__ == "__main__":
    main()
