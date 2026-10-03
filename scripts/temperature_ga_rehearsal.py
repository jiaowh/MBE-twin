"""Synthetic rehearsal of the temperature and Ga calibrations (docs/COMMISSIONING_PLAN.md, steps 2, 3 and 6).

Question: which calibration route keeps the Ga set point inside the +/-3 K budget of the
pyrometer-steered operating point (operating_cold_limit.py --pyrometer-bias), once the
uncertainty of the literature laws and of the source labs' temperature scales is included?

Common currency. operating_cold_limit.py biases the centre reading by b: the Ga is steered to the
window middle the reading implies, the wafer sits at another temperature, and the droplet edge
F_crit(T) moves by dF_crit/dT x b. Any error in the steered excess Ga - N is therefore expressed
as an equivalent reading error b_eq = 2 x (error in the window middle) / (dF_crit/dT), and an error
in the onset itself as b_eq = (error in ln F_crit) / (d ln F_crit / dT), both at the operating
point (1 um/h, reading 720 C). The routes stay within budget if b_eq stays within about 3 K.

True machine, per draw:
- the reading is R = T + d0 + d1 (T - 993 K), with d0 uniform in +/-30 K and d1 normal with
  sd 0.05 (5 K per 100 K);
- decomposition: Arrhenius with E uniform in 3.1-3.6 eV (the literature range,
  gan_growth.json), equal to the twin's law (G02, E = 3.1 eV) at 762 C on G02's scale, and G02's
  scale off the true one by e_dec (normal, sd SIGMA_LAB);
- droplet onset: one of the three literature laws (each in turn), on its lab's scale, off the
  true one by e_drop (normal, sd SIGMA_LAB, independent of e_dec).
Measurements (noise as stated, all at the working N flow):
- C2: decomposition rate at readings 740, 770 and 800 C, 5 % noise;
- C2 anchor: Si(111) 7x7 -> 1x1 seen at a reading; true temperature 830 C +/- SIGMA_SI (the
  literature spread of the transition), reading noise 2 K;
- C8: droplet onset flux at readings 700 and 740 C, relative noise SIGMA_ONSET;
- C4 / C6: N-rich (Ga-limited) and Ga-rich (N-limited) growth rates at the operating reading, 1 % each
  (0.5 and 2 % also reported);
  under N-rich growth the decomposition is between 0 and its vacuum rate (growth.py), uniform.
Routes for the window at the operating reading:
- A. literature law, absolute temperature from C2 alone (the twin's decomposition law inverted at
  the three readings, offset averaged);
- B. as A, plus the Si anchor (offset and slope from C2 and the anchor together);
- C. the onset measured on the machine (C8), Arrhenius through the two readings, interpolated to
  720 C: no absolute temperature is needed;
- the Ga/N term: C4 and C6 give the excess Ga - N the steering sets; its error is converted the
  same way (route-independent).
Reported per true droplet law and route: |b_eq| at 50 / 95 %, and for route C the combined
95 % with the Ga/N term.

Usage: python scripts/temperature_ga_rehearsal.py [--draws 20000] [--out results/temperature_ga_rehearsal]
"""

import argparse
import json
from pathlib import Path

import numpy as np

from mbe_twin.growth import K_B_EV, load_parameters
from mbe_twin.manifest import build_manifest, write_manifest

ROOT = Path(__file__).resolve().parents[1]
C = 273.15
T_OP_READ = 720.0 + C
RATE_NM_MIN = 1000.0 / 60.0                       # 1 um/h
C2_READ = np.array([740.0, 770.0, 800.0]) + C
C8_READ = np.array([700.0, 740.0]) + C
T_DEC_PIVOT = 762.0 + C                           # middle of G02's fitted range (720-805 C)
T_SI = 830.0 + C
SIGMA_LAB = (5.0, 10.0, 20.0)                     # K, source-lab scale error (each law)
SIGMA_SI = 10.0                                   # K
SIGMA_ONSET = (0.05, 0.10, 0.20)
NOISE = {"decomposition": 0.05, "si_reading_K": 2.0, "growth_rate": 0.01}
GROWTH_RATE_NOISE = (0.005, 0.01, 0.02)
OFFSET_K, SLOPE_SD = 30.0, 0.05


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--draws", type=int, default=20000)
    ap.add_argument("--out", default="results/temperature_ga_rehearsal")
    args = ap.parse_args()
    params = load_parameters()
    dec_nom = params.decomposition
    laws = list(params.droplet_onset)
    rng = np.random.default_rng(20261008)
    n = args.draws
    pct = lambda a: [float(np.percentile(np.abs(a), 50)), float(np.percentile(np.abs(a), 95))]  # noqa: E731
    rows = []
    for sigma_lab in SIGMA_LAB:
        for law in laws:
            f_nom = params.droplet_onset[law]
            e_f = f_nom.energy_ev
            d0 = rng.uniform(-OFFSET_K, OFFSET_K, n)
            d1 = rng.normal(0.0, SLOPE_SD, n)
            to_true = lambda r: (r - d0 + d1 * 993.0) / (1.0 + d1)  # noqa: E731  inverse of R = T + d0 + d1 (T - 993)
            e_dec = rng.normal(0.0, sigma_lab, n)
            e_drop = rng.normal(0.0, sigma_lab, n)
            e_true = rng.uniform(3.1, 3.6, n)
            # true decomposition: equals the twin's law at the pivot on G02's scale (T_G02 = T + e_dec)
            col = lambda a, t: a if np.ndim(t) == 1 else a[:, None]  # noqa: E731

            def dec_true(t):
                return dec_nom(T_DEC_PIVOT) * np.exp(-col(e_true, t) / K_B_EV * (1.0 / (t + col(e_dec, t)) - 1.0 / T_DEC_PIVOT))

            def f_true(t):                                   # nm/min, the law on its lab's scale
                return f_nom(t + col(e_drop, t)) / params.ml_per_s_per_nm_per_min
            to_read = lambda t: t + d0 + d1 * (t - 993.0)  # noqa: E731
            # each route runs where it believes the window has its planned width (the twin's law at 720 C)
            f_plan = f_nom(T_OP_READ) / params.ml_per_s_per_nm_per_min
            t_op = T_OP_READ - e_drop                        # true temperature at which the true window has that width
            f_op = f_true(t_op)
            r_op = to_read(t_op)                             # route C runs at this reading
            dlnf_dt = e_f / (K_B_EV * t_op ** 2)
            # C2: decomposition at three readings
            t_c2 = np.stack([to_true(np.full(n, r)) for r in C2_READ], -1)
            r_c2 = dec_true(t_c2) * (1 + NOISE["decomposition"] * rng.standard_normal(t_c2.shape))
            t_hat_c2 = dec_nom.energy_ev / (K_B_EV * np.log(dec_nom.prefactor / r_c2))   # twin's law inverted
            # route A: offset only from C2; the wafer is run at the reading the fit maps to 720 C
            off_a = np.mean(C2_READ - t_hat_c2, -1)
            t_op_a = to_true(T_OP_READ + off_a)
            # route B: offset and slope from C2 and the Si anchor (least squares, reading = T + a + b (T - 993))
            t_si_actual = T_SI + rng.normal(0, SIGMA_SI, n)
            r_si = t_si_actual + d0 + d1 * (t_si_actual - 993.0) + rng.normal(0, NOISE["si_reading_K"], n)
            t_si_assumed = np.full(n, T_SI)
            t_pts = np.concatenate([t_hat_c2, t_si_assumed[:, None]], -1)
            r_pts = np.concatenate([np.broadcast_to(C2_READ, t_hat_c2.shape), r_si[:, None]], -1)
            x = t_pts - 993.0
            y = r_pts - t_pts
            xm, ym = x.mean(-1), y.mean(-1)
            b_hat = np.sum((x - xm[:, None]) * (y - ym[:, None]), -1) / np.sum((x - xm[:, None]) ** 2, -1)
            a_hat = ym - b_hat * xm
            t_op_b = to_true(T_OP_READ + a_hat + b_hat * (T_OP_READ - 993.0))
            # routes A and B steer with the literature law at 720 C; the true onset is that of the wafer's true temperature
            b_eq = {}
            for route, t_act in (("A_decomposition_only", t_op_a), ("B_decomposition_and_Si", t_op_b)):
                b_eq[route] = np.log(f_plan / f_true(t_act)) / (e_f / (K_B_EV * t_act ** 2))
            # route C: onset at two readings, Arrhenius in reading, interpolated to 720 C
            f_c8 = f_true(np.stack([to_true(np.full(n, r)) for r in C8_READ], -1))
            f_c8 = f_c8 * np.exp(SIGMA_ONSET[1] * rng.standard_normal(f_c8.shape))
            u = 1.0 / C8_READ
            slope = (np.log(f_c8[:, 1]) - np.log(f_c8[:, 0])) / (u[1] - u[0])
            lnf_c = np.log(f_c8[:, 0]) + slope * (1.0 / r_op - u[0])
            b_eq["C_onset_measured"] = (lnf_c - np.log(f_op)) / dlnf_dt
            onset_noise = {}
            for s_on in SIGMA_ONSET:
                f_s = f_true(np.stack([to_true(np.full(n, r)) for r in C8_READ], -1)) * np.exp(s_on * rng.standard_normal((n, 2)))
                sl = (np.log(f_s[:, 1]) - np.log(f_s[:, 0])) / (u[1] - u[0])
                onset_noise[f"{s_on:g}"] = pct((np.log(f_s[:, 0]) + sl * (1.0 / r_op - u[0]) - np.log(f_op)) / dlnf_dt)
            # Ga/N term: the steering sets excess = Ga - N to F_crit / 2 using C4 (Ga) and C6 (N)
            dec_op = dec_true(t_op)
            j_n = RATE_NM_MIN + dec_op
            j_ga = j_n + 0.5 * f_op

            def b_ga_n(noise):
                n_hat = RATE_NM_MIN * (1 + noise * rng.standard_normal(n)) + dec_op                 # C6 + C2 at the reading
                frac = rng.uniform(0.0, 1.0, n)                                                     # N-rich decomposition share
                ga_hat = (j_ga - frac * dec_op) * (1 + noise * rng.standard_normal(n)) + 0.5 * dec_op
                return 2.0 * ((ga_hat - n_hat) - (j_ga - j_n)) / (dlnf_dt * f_op)
            gan_noise = {f"{v:g}": pct(b_ga_n(v)) for v in GROWTH_RATE_NOISE}
            b_gan = b_ga_n(NOISE["growth_rate"])
            b_eq["GaN_rates"] = b_gan
            b_eq["C_plus_GaN"] = b_eq["C_onset_measured"] + b_gan
            row = {"sigma_lab_K": sigma_lab, "droplet_law": law,
                   "window_half_width_nm_min_median": float(np.median(0.5 * f_op)),
                   "dF_crit_dT_nm_min_per_K_median": float(np.median(dlnf_dt * f_op)),
                   "abs_T_error_K_A_50_95": pct(t_op_a - T_OP_READ), "abs_T_error_K_B_50_95": pct(t_op_b - T_OP_READ),
                   "b_eq_K_50_95": {k: pct(v) for k, v in b_eq.items()},
                   "b_eq_K_route_C_by_onset_noise_50_95": onset_noise, "b_eq_K_GaN_by_rate_noise_50_95": gan_noise}
            rows.append(row)
            print(f"lab scale sd {sigma_lab:4.0f} K, law {law:15s}: half-width {row['window_half_width_nm_min_median']:.2f} nm/min, "
                  f"dF/dT {row['dF_crit_dT_nm_min_per_K_median']:.3f} nm/min/K; |T error| 95 % A {row['abs_T_error_K_A_50_95'][1]:.1f} "
                  f"B {row['abs_T_error_K_B_50_95'][1]:.1f} K; |b_eq| 95 %: " + ", ".join(
                      f"{k} {v[1]:.1f}" for k, v in row["b_eq_K_50_95"].items())
                  + "; C by onset noise " + ", ".join(f"{k}: {v[1]:.1f}" for k, v in onset_noise.items())
                  + "; Ga/N by rate noise " + ", ".join(f"{k}: {v[1]:.1f}" for k, v in gan_noise.items()), flush=True)
    manifest = build_manifest(
        "temperature_ga_rehearsal", label="synthetic", validation_status="not_validated",
        inputs={"T_op_reading_C": T_OP_READ - C, "rate_um_h": 1.0, "c2_readings_C": (C2_READ - C).tolist(),
                "c8_readings_C": (C8_READ - C).tolist(), "decomposition_pivot_C": T_DEC_PIVOT - C,
                "decomposition_energy_true_eV": [3.1, 3.6], "si_transition_C": T_SI - C, "sigma_si_K": SIGMA_SI,
                "sigma_lab_K": SIGMA_LAB, "sigma_onset": SIGMA_ONSET, "route_C_onset_noise": SIGMA_ONSET[1],
                "growth_rate_noise": GROWTH_RATE_NOISE,
                "noise": NOISE, "reading_offset_K": OFFSET_K, "reading_slope_sd": SLOPE_SD, "draws": n, "seed": 20261008},
        outputs={"rows": rows},
        sources=[Path(__file__), ROOT / "src/mbe_twin/growth.py", ROOT / "data/parameters/gan_growth.json"],
        warnings=["Synthetic: the true machine follows the twin's law forms with assumed spreads; tests the calibration routes",
                  "Uniform wafer at the centre reading; the radial temperature map and the heater model are not in this rehearsal",
                  "Reading reproducibility between calibration and production (emissivity drift with layer thickness, "
                  "wafer to wafer) is not modelled: it adds directly to b_eq",
                  "Lab scale errors of the decomposition and droplet laws assumed independent, normal"])
    print(f"Wrote {write_manifest(manifest, Path(args.out) / 'manifest.json')}")


if __name__ == "__main__":
    main()
