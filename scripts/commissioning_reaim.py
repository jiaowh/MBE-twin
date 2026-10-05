"""Commissioning dry run of the N-source re-aim: can thickness maps find the tilt well enough to correct it to 0.2 deg?

The uniformity levers (LAYOUT_COMPARISON section 12) assume the N source is re-aimed at commissioning to a residual
pointing of 0.2 deg. This rehearses that step on synthetic data:

- Truth: a hidden misalignment, a tilt drawn uniformly in the +/-0.8 deg disk about the flange pivot (the harmful
  set of worst_case_drivers.py), or about the plate centre in a second scenario. Its N arrival map is
  m0 + (tx/0.8) Dx + (ty/0.8) Dy, with Dx, Dy the comparison's 0.8 deg responses at directions 0 and 90 deg
  (superposition checked against the 30 / 60 deg maps and reported; linearity in tilt checked to 0.07 %).
- Measurement: the radial thickness profile of an N-limited (Ga-rich) calibration growth at the operating
  pressure, sampled at the mapping tool's radii (0-94 mm in 5 mm steps), with relative Gaussian noise sigma_map
  per point, averaged over n_wafers wafers. Each wafer's decomposition profile follows a heater state drawn from
  the combined heater errors (heater_robustness), which the fit does not know: a systematic error source.
- Fit: the profile is modelled as scale x (m0 + ax Dx + ay Dy) x attenuation - decomposition(nominal heater map),
  with the misalignment in flange-tilt coordinates (the mount's axes). A sideways tilt barely changes a radial
  profile (rotation averages it), so an unweighted fit amplifies noise along that axis. The estimate is
  therefore Bayesian: weighted least squares (map noise plus the heater-state spread of the decomposition
  profile at each radius) with a Gaussian prior on the tilt from the +/-0.8 deg tolerance (0.4 deg per axis).
  It corrects what the data resolve and leaves the invisible, and equally harmless, component alone.
- Rounds: one or two measure-and-correct rounds (the second map is grown after the first correction).
- Correction: the mount is tilted by the opposite of the estimate, with a Gaussian repeatability error
  sigma_mount per axis. A plate-centred truth is corrected through the same flange axes (the fit returns the
  flange tilt whose profile is closest).
- Result per setting (Monte Carlo over truths and noise): the residual tilt (deg; 50th / 95th percentile) and the
  half-range of the residual N profile in excess of the nominal one (points), against the 0.2 deg requirement.

Usage: python scripts/commissioning_reaim.py [--layout B-p B-L] [--trials 2000] [--n-tables FILE] [--out DIR]
"""

import argparse
import importlib.util
import itertools
import json
import os
from pathlib import Path

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402

from mbe_twin.growth import load_parameters  # noqa: E402
from mbe_twin.manifest import build_manifest, write_manifest  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lc = _load("layout_comparison")
hr = _load("heater_robustness")
MAP_RADII = np.append(np.arange(0.0, 0.094, 0.005), 0.094)
SIGMA_MAP = (0.001, 0.003, 0.005, 0.01)
N_WAFERS = (1, 3)
SIGMA_MOUNT_DEG = (0.05, 0.1)
ROUNDS = (1, 2)
PRIOR_DEG = 0.4
P_OP = {"B-p": 4.32e-3, "B-L": 8.62e-3}       # calibration pressure at 1 um/h (realizable_controller records)
N_CENTRE = 17.0                               # nm/min, N-limited centre rate scale for the decomposition term


def tables(layout, n_tables=None):
    env = json.loads(lc.ENVELOPE.read_text(encoding="utf-8"))
    if n_tables:
        z = np.load(n_tables)
        states, maps, att, lip = json.loads(str(z["states"])), z["maps"], z["att"], z["lip"]
    else:
        rec = json.loads(lc.comparison_record("gas+plume").read_text(encoding="utf-8"))
        n = env["layouts"][layout]["n"]
        prefix = f"N_{n['L_over_r']:g}_{n['polar_deg']:g}_{n['aim_offset_mm']:g}_"
        nf = next(c for c in rec["inputs"]["map_caches"] if c["file"].startswith(prefix))
        z = np.load(ROOT / "results/layout_comparison_bc" / nf["file"])
        states, maps, att, lip = json.loads(str(z["states"])), z["maps"], z["att"], z["lip"]
    states = [tuple(s) for s in states]
    lip2 = lip[lc.LIP_H.index(0.002)]
    maps = maps * lip2
    return states, maps, att


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--layout", nargs="+", default=["B-p", "B-L"])
    ap.add_argument("--trials", type=int, default=2000)
    ap.add_argument("--n-tables", default=None, help="tables of scripts/aim_tables.py for the (single) layout")
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--out", default="results/commissioning_reaim")
    args = ap.parse_args()
    rho = np.linspace(0.0, 0.094, 39)
    params = load_parameters()
    hr.BIASES_K = (0.0,)
    heat = [s for s in hr.combined_states(993.15, rho) if s["limit"] == "1473 K element" and s["controller"] == "pyrometer +0 K"]
    t_nom = next(s["t_map"] for s in heat if all(s[k] == v for k, v in hr.NOMINAL.items()))
    dec_states = np.array([params.decomposition(s["t_map"]) for s in heat])            # nm/min (H, rho)
    dec_nom = params.decomposition(t_nom)
    rows, checks = [], {}
    for layout in args.layout:
        states, maps, att = tables(layout, args.n_tables)
        a = lc.att_at(att, P_OP[layout])
        m0 = maps[0]
        resp = {}
        for pivot in ("flange", "plate"):
            dx = maps[states.index((pivot, 0.8, 0.0))] - m0
            dy = maps[states.index((pivot, 0.8, 90.0))] - m0
            resp[pivot] = (dx, dy)
            # superposition check at 30 and 60 deg
            err = []
            for psi in (30.0, 60.0):
                pred = m0 + np.cos(np.radians(psi)) * dx + np.sin(np.radians(psi)) * dy
                true = maps[states.index((pivot, 0.8, psi))]
                err.append(float(100 * np.max(np.abs(pred / pred.mean() - true / true.mean()))))
            checks[f"{layout} {pivot}"] = {"superposition_max_shape_err_pct": max(err)}

        def profile(tx, ty, pivot):
            dx, dy = resp[pivot]
            return m0 + (tx / 0.8) * dx + (ty / 0.8) * dy

        def half_range(p):
            p = p * a
            return 100 * (p.max() - p.min()) / (p.max() + p.min())
        hr_nom = half_range(m0)
        # fit basis on the mapping radii (flange axes), thickness units: N arrival scaled to N_CENTRE at the centre
        scale = N_CENTRE / (m0[0] * a[0])
        basis = np.stack([np.interp(MAP_RADII, rho, scale * v * a) for v in (m0, resp["flange"][0] / 0.8, resp["flange"][1] / 0.8)], 1)
        dec_fit = np.interp(MAP_RADII, rho, dec_nom)
        dec_sys = np.interp(MAP_RADII, rho, dec_states.std(0))                 # heater-state spread (nm/min)
        rng = np.random.default_rng(args.seed)
        for truth_pivot, s_map, n_w, s_mount, rounds in itertools.product(("flange", "plate"), SIGMA_MAP, N_WAFERS,
                                                                          SIGMA_MOUNT_DEG, ROUNDS):
            r = np.sqrt(rng.uniform(0, 1, args.trials)) * 0.8
            phi = rng.uniform(0, 2 * np.pi, args.trials)
            tx, ty = r * np.cos(phi), r * np.sin(phi)
            res_t, excess = [], []
            for k in range(args.trials):
                cx_tot = cy_tot = 0.0
                for _ in range(rounds):
                    cur = profile(tx[k], ty[k], truth_pivot) + (cx_tot / 0.8) * resp["flange"][0] + (cy_tot / 0.8) * resp["flange"][1]
                    prof = scale * cur * a
                    meas = []
                    for _ in range(n_w):
                        dec = dec_states[rng.integers(len(dec_states))]
                        h = np.interp(MAP_RADII, rho, prof - dec)
                        meas.append(h * (1.0 + rng.normal(0.0, s_map, h.size)))
                    y = np.mean(meas, 0) + dec_fit                  # the fit adds back the nominal decomposition
                    sig = np.sqrt((s_map * y) ** 2 / n_w + dec_sys ** 2 / n_w)
                    bw, yw = basis / sig[:, None], y / sig
                    c0 = np.linalg.lstsq(bw[:, :1], yw, rcond=None)[0][0]
                    # posterior mean of (c0, c0 ax, c0 ay) with a flat prior on c0 and N(0, (c0 prior)^2) on the tilts
                    reg = np.diag([0.0, 1.0, 1.0]) / (c0 * PRIOR_DEG) ** 2
                    c = np.linalg.solve(bw.T @ bw + reg, bw.T @ yw)
                    ex, ey = c[1] / c[0], c[2] / c[0]              # estimated remaining flange tilt (deg)
                    cx_tot += -ex + rng.normal(0.0, s_mount)
                    cy_tot += -ey + rng.normal(0.0, s_mount)
                corr = profile(tx[k], ty[k], truth_pivot) + (cx_tot / 0.8) * resp["flange"][0] + (cy_tot / 0.8) * resp["flange"][1]
                excess.append(half_range(corr) - hr_nom)
                if truth_pivot == "flange":
                    res_t.append(np.hypot(tx[k] + cx_tot, ty[k] + cy_tot))
            row = {"layout": layout, "truth_pivot": truth_pivot, "sigma_map": s_map, "n_wafers": n_w,
                   "sigma_mount_deg": s_mount, "rounds": rounds, "nominal_half_range_pct": hr_nom,
                   "excess_half_range_pt_p50": float(np.percentile(excess, 50)),
                   "excess_half_range_pt_p95": float(np.percentile(excess, 95)),
                   "uncorrected_excess_pt_p95": float(np.percentile(
                       [half_range(profile(tx[k], ty[k], truth_pivot)) - hr_nom for k in range(args.trials)], 95))}
            if res_t:
                row.update({"residual_tilt_deg_p50": float(np.percentile(res_t, 50)),
                            "residual_tilt_deg_p95": float(np.percentile(res_t, 95))})
            # the 0.2 deg reference: excess of a flange tilt of 0.2 deg in the worst direction
            row["excess_at_0p2deg_worst_pt"] = float(max(half_range(profile(0.2 * np.cos(p_), 0.2 * np.sin(p_), "flange")) - hr_nom
                                                         for p_ in np.radians(np.arange(0, 360, 15))))
            rows.append(row)
            print(f"{layout} truth {truth_pivot:6s} map {100 * s_map:.1f} % x{n_w}, mount {s_mount:.2f} deg, {rounds} round(s): "
                  + (f"residual tilt p50 {row['residual_tilt_deg_p50']:.3f} / p95 {row['residual_tilt_deg_p95']:.3f} deg; "
                     if res_t else "")
                  + f"excess half-range p95 {row['excess_half_range_pt_p95']:.3f} pt "
                    f"(uncorrected {row['uncorrected_excess_pt_p95']:.3f}; 0.2 deg worst {row['excess_at_0p2deg_worst_pt']:.3f})",
                  flush=True)
    out = Path(args.out)
    man = build_manifest("commissioning_reaim", label="synthetic",
                         inputs={"layouts": args.layout, "trials": args.trials, "seed": args.seed, "map_radii_m": MAP_RADII,
                                 "sigma_map": SIGMA_MAP, "n_wafers": N_WAFERS, "sigma_mount_deg": SIGMA_MOUNT_DEG,
                                 "rounds": ROUNDS, "prior_deg": PRIOR_DEG,
                                 "p_op_Pa": P_OP, "n_tables": args.n_tables,
                                 "n_tables_sha256": lc.file_sha256(Path(args.n_tables)) if args.n_tables else None},
                         outputs={"rows": rows, "checks": checks},
                         sources=[Path(__file__), ROOT / "scripts/layout_comparison.py", ROOT / "scripts/heater_robustness.py",
                                  ROOT / "scripts/heater_zones.py", ROOT / "src/mbe_twin/growth.py",
                                  ROOT / "data/parameters/gan_growth.json", lc.comparison_record("gas+plume")],
                         warnings=["Synthetic rehearsal; map noise, wafer count and mount repeatability are scenarios",
                                   "Tilt response superposed from the 0 / 90 deg maps (check reported)",
                                   "Each calibration wafer's heater state is unknown to the fit (nominal decomposition assumed)"])
    write_manifest(man, out / "manifest.json")
    print("checks", checks)


if __name__ == "__main__":
    main()
