"""Synthetic commissioning rehearsal for the nitrogen supply (docs/COMMISSIONING_PLAN.md, section 6).

Question: do the planned runs C1 (chamber pressure at several N2 flows), C6 (Ga-rich, i.e. N-limited,
growth rate at the wafer centre at those flows) and C6b (the same rate at the working flow with the
pumping throttled) recover the effective pumping speed S and the active-N conversion eta, and can
they tell the twin's scattered-atom models apart when eta itself may change with flow?

Method. A "true" machine is the twin itself with chosen values (layout, eta, S, a scattered-atom
model, and how eta changes with flow). From it:
- C1: chamber pressure p = Q k T / S at each flow (vacuum.pressure_from_flow), read with 3 %
  random gauge noise per point and, in a second set, a common gauge-factor error of +10 %;
- C6: the centre growth rate at each flow, r = eta(Q) x (N atoms per sccm) x Q x n_c(p) / k, where
  n_c(p) is the centre N arrival per unit plate output at pressure p (the comparison's nominal map
  with the 2 mm lip, its attenuation table, and the scattered-arrival factors of the true model),
  with 2 % random noise. Decomposition is taken as measured separately (C2) and added back, so r is
  the gross N-limited incorporation rate;
- C6b (throttle series): at the working flow and RF power, the pumping is throttled to S x
  THROTTLE (gate valve), so the chamber pressure rises while the flow, the discharge and hence eta
  stay fixed (the source pressure behind the plate, set by the flow and the plate conductance, is
  hundreds of times the chamber pressure). Each point has its own gauge reading and rate.
True eta: constant, or falling with flow as eta0 (Q_working / Q)^0.25 (about 1.5x higher at the
lowest calibration flow; a plausible fixed-power trend, not a measured one).
Fit designs (all linear least squares in the eta parameters, weighted by the rate noise):
- flow, eta constant: S from C1 (mean of k T Q / p), one eta over the C6 flows (the 2026-10-03 rehearsal);
- flow, eta linear or quadratic in x = (Q - Q_w) / Q_w over the C6 flows, as the plan's C6 fit of eta(flow);
- throttle: one eta over the C6b points, pressures as read;
- flow + throttle: eta quadratic in x over C6 and C6b together (the throttle points share eta(Q_w)).
For each candidate model (direct beam only; scattered atoms with gamma = 1; with gamma = 0.1), over
2000 noise draws: the fraction of draws in which the candidate is rejected (chi^2 above its 95 %
point), eta at the working flow recovered / true (5-50-95 %), and the error of the predicted centre
rate at two held-out flows (validation run V3), one beyond the calibrated flows and one inside them. The N-limited map's half-range/mean at the working flow
under each candidate against the truth (shape only, no noise) is reported once per machine.

Usage: python scripts/commissioning_rehearsal.py [--draws 2000] [--out results/commissioning_rehearsal]
"""

import argparse
import importlib.util
import json
import os
from pathlib import Path

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402
from scipy.stats import chi2 as chi2_dist  # noqa: E402

from mbe_twin.manifest import build_manifest, write_manifest  # noqa: E402
from mbe_twin.vacuum import SCCM_PA_M3_S, T_STD, pressure_from_flow  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("layout_comparison", ROOT / "scripts/layout_comparison.py")
lc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lc)
RECORD = ROOT / "data/runs/studies/layout_comparison_bc.json"
MAPS = ROOT / "results/layout_comparison_bc"
MODELS = ("none", "gas", "gas-gamma0.1")
# true machines: layout, eta at the working flow, S (m^3/s), calibration flows, held-out flows (one outside and
# one inside the calibrated range), working flow (sccm)
MACHINES = [
    {"layout": "B-L", "eta": 0.3, "S": 4.0, "flows": [5.0, 10.0, 15.0, 20.0, 25.0], "holdout": 35.0, "holdout_inside": 17.5,
     "working": 26.1},
    {"layout": "B-p", "eta": 1.0, "S": 2.0, "flows": [2.0, 4.0, 6.0, 8.0], "holdout": 10.0, "holdout_inside": 5.0, "working": 9.0},
]
THROTTLE = (1.0, 0.7, 0.5, 0.35, 0.25)          # pumping speed fractions of the throttle series (C6b)
ETA_TRENDS = {"constant": 0.0, "falling": 0.25}  # eta(Q) = eta_w (Q_w / Q)^exponent
DESIGNS = ("flow_const", "flow_linear", "flow_quadratic", "throttle", "flow_quadratic+throttle")
NOISE = {"gauge_random": 0.03, "rate_random": 0.02}
GAUGE_FACTOR_ERRORS = (0.0, 0.10)


def centre_arrival(env, rec, name, scatter):
    """Centre N arrival per unit plate output against pressure, and the full map at one pressure."""
    lay = env["layouts"][name]
    n = lay["n"]
    prefix = f"N_{n['L_over_r']:g}_{n['polar_deg']:g}_{n['aim_offset_mm']:g}_"
    nf = next(c for c in rec["inputs"]["map_caches"] if c["file"].startswith(prefix))
    z = np.load(MAPS / nf["file"])
    if str(z["cache_key"]) != nf["key"]:
        raise SystemExit(f"commissioning_rehearsal: N cache key mismatch for {name}")
    vac_map = z["maps"][0] * z["lip"][lc.LIP_H.index(0.002)]
    att = z["att"] * (scatter["N"][name] if scatter else 1.0)
    return (lambda ps: np.array([vac_map[0] * lc.att_at(att, p)[0] for p in np.atleast_1d(ps)]),
            lambda p: vac_map * lc.att_at(att, p))


def fit(r, q, g, basis):
    """Weighted linear least squares r ~ (basis @ c) * g with 2 % relative noise: (c, chi^2, dof)."""
    sig = NOISE["rate_random"] * r
    a = basis * g[:, None] / sig[:, None]
    c, *_ = np.linalg.lstsq(a, r / sig, rcond=None)
    chi2 = float(np.sum((r / sig - a @ c) ** 2))
    return c, chi2, len(r) - basis.shape[1]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--draws", type=int, default=2000)
    ap.add_argument("--out", default="results/commissioning_rehearsal")
    args = ap.parse_args()
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    env = rec["inputs"]["envelope"]
    rho = np.asarray(rec["outputs"]["rho_m"])
    k_atoms = rec["inputs"]["atoms_per_m2_s_per_nm_min"]
    t_gas = env["vacuum"]["gas_temperature_K"]["value"]
    to_p = SCCM_PA_M3_S * (t_gas / T_STD)
    factors = {m: lc.scatter_factors(m, rho) for m in MODELS}
    rng = np.random.default_rng(20261003)
    pc = lambda a: [float(np.percentile(a, 5)), float(np.median(a)), float(np.percentile(a, 95))]  # noqa: E731
    results, maps = [], {}
    for mach in MACHINES:
        name, qw = mach["layout"], mach["working"]
        arr = {m: centre_arrival(env, rec, name, factors[m]) for m in MODELS}
        q_flow = np.asarray(mach["flows"])
        n_flow = len(q_flow)
        q_all = np.concatenate([q_flow, np.full(len(THROTTLE), qw)])          # C6 then C6b
        s_all = np.concatenate([np.full(n_flow, mach["S"]), mach["S"] * np.asarray(THROTTLE)])
        p_all = q_all * to_p / s_all
        p_work = pressure_from_flow(qw, mach["S"], t_gas)
        hr = lambda m: 100 * (m.max() - m.min()) / (2 * m.mean())  # noqa: E731
        maps[name] = {m: hr(arr[m][1](p_work)) for m in MODELS}
        per_sccm = lc.N_ATOMS_PER_SCCM / k_atoms
        for truth in ("gas", "gas-gamma0.1"):
            for trend, expo in ETA_TRENDS.items():
                eta_q = lambda q: mach["eta"] * (qw / np.asarray(q)) ** expo  # noqa: E731
                r_true = eta_q(q_all) * per_sccm * q_all * arr[truth][0](p_all)
                q_h = np.array([mach["holdout"], mach["holdout_inside"]])
                r_hold = eta_q(q_h) * per_sccm * q_h * arr[truth][0](q_h * to_p / mach["S"])
                for gerr in GAUGE_FACTOR_ERRORS:
                    acc = {(d, m): {"eta": [], "rej": [], "hold": [], "hold_in": []} for d in DESIGNS for m in MODELS}
                    for _ in range(args.draws):
                        p_meas = p_all * (1 + gerr) * (1 + NOISE["gauge_random"] * rng.standard_normal(len(p_all)))
                        r_meas = r_true * (1 + NOISE["rate_random"] * rng.standard_normal(len(p_all)))
                        s_hat = float(np.mean(q_flow * to_p / p_meas[:n_flow]))          # C1, plasma off
                        p_hold = q_h * to_p / s_hat
                        for m in MODELS:
                            # flow points: pressure from the fitted S (C1); throttle points: pressure as read
                            p_fit = np.concatenate([q_flow * to_p / s_hat, p_meas[n_flow:]])
                            g = per_sccm * q_all * arr[m][0](p_fit)
                            g_hold = per_sccm * q_h * arr[m][0](p_hold)
                            x = (q_all - qw) / qw
                            for d in DESIGNS:
                                sel = slice(n_flow, None) if d == "throttle" else slice(None) if "+" in d else slice(0, n_flow)
                                order = 2 if "quadratic" in d else 1 if "linear" in d else 0
                                basis = np.column_stack([x ** k for k in range(order + 1)])[sel]
                                c, chi2, dof = fit(r_meas[sel], q_all[sel], g[sel], basis)
                                eta_w = c[0]
                                x_hold = (q_h - qw) / qw
                                eta_hold = sum(ck * x_hold ** k for k, ck in enumerate(c))
                                err = eta_hold * g_hold / r_hold - 1
                                a = acc[(d, m)]
                                a["eta"].append(eta_w / mach["eta"])
                                a["rej"].append(chi2 > chi2_dist.ppf(0.95, dof))
                                a["hold"].append(err[0])
                                a["hold_in"].append(err[1])
                    for d in DESIGNS:
                        row = {"layout": name, "eta_true_working": mach["eta"], "S_true": mach["S"], "truth": truth,
                               "eta_trend": trend, "gauge_factor_error": gerr, "design": d, "models": {}}
                        for m in MODELS:
                            a = acc[(d, m)]
                            row["models"][m] = {"rejected_fraction": float(np.mean(a["rej"])),
                                                "eta_working_recovered_over_true_5_50_95": pc(a["eta"]),
                                                "holdout_rate_error_5_50_95": pc(a["hold"]),
                                                "holdout_inside_rate_error_5_50_95": pc(a["hold_in"])}
                        results.append(row)
                        print(f"{name} truth {truth:13s} eta {trend:8s} gauge {gerr:+.0%} {d:24s}: " + "; ".join(
                            f"{m} rej {100 * row['models'][m]['rejected_fraction']:3.0f} % "
                            f"eta {row['models'][m]['eta_working_recovered_over_true_5_50_95'][1]:.3f} "
                            f"hold {100 * row['models'][m]['holdout_rate_error_5_50_95'][1]:+.1f}/"
                            f"{100 * row['models'][m]['holdout_inside_rate_error_5_50_95'][1]:+.1f} %" for m in MODELS),
                            flush=True)
    manifest = build_manifest(
        "commissioning_rehearsal", label="synthetic", validation_status="not_validated",
        inputs={"record": str(RECORD.relative_to(ROOT).as_posix()), "record_run_id": rec["run_id"], "machines": MACHINES,
                "models": MODELS, "throttle_fractions": THROTTLE, "eta_trends_exponent": ETA_TRENDS, "designs": DESIGNS,
                "noise": NOISE, "gauge_factor_errors": GAUGE_FACTOR_ERRORS, "draws": args.draws, "seed": 20261003,
                "scattered_tables_sha256": factors["gas"]["sha256"]},
        outputs={"rows": results, "working_map_half_range_points": maps},
        sources=[Path(__file__), ROOT / "scripts/layout_comparison.py", ROOT / "src/mbe_twin/vacuum.py", RECORD, lc.SCATTER_TABLES],
        warnings=["Synthetic: the true machine is the twin itself; tests the measurement plan, not the twin",
                  "Centre growth rate only (C6, C6b); decomposition taken as measured separately",
                  "Noise levels assumed (3 % gauge, 2 % rate); the real run-to-run scatter comes from C9",
                  "Throttle series assumes eta does not change with chamber pressure at fixed flow and power",
                  "True eta trend is assumed (constant or (Q_w/Q)^0.25), not measured"])
    print(f"Wrote {write_manifest(manifest, Path(args.out) / 'manifest.json')}")


if __name__ == "__main__":
    main()
