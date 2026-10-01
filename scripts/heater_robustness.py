"""Combined heater errors, element headroom, and a Ga correction tied to the measured temperature.

The layout comparison perturbs the heater one property at a time and found the decisive case
to be a wafer of higher emissivity: with no element headroom it runs about 14.5 K cold, and
with the Ga flux held it leaves the Ga-rich window. This study, for the designed-density heater
of layouts B and C (1 mm overlap holder):
1. Combined errors: wafer emissivity 0.63 / 0.70 / 0.77 x wafer-ledge contact 50 / 200 / 1000
   W m^-2 K^-1 x zone power error none / +2 % / -2 % in the worst zone (27 states), at the
   nominal zone ratios with one reading holding the mean (as the comparison). For each: the
   element temperature needed, and under each element limit, the capped wafer mean and range.
2. Headroom: the element limit at which every combined state holds the target.
3. Ga protocols for layout B's nominal maps at its 1 um/h operating point (eta = 1, 2 m^3/s):
   - fixed: the Ga centre flux of the nominal state is held (layout_comparison protocol);
   - temperature-corrected: the Ga flux is re-set to the middle of the window that the
     measured wafer mean temperature implies (the window computed for a uniform wafer at the
     measured mean with the nominal N map: a calibration table Ga(T), not the true map);
   - ideal: re-set to the middle of the true window of that state (a bound);
   - with a centre pyrometer: the heater holds the reading of one spot at the wafer centre
     (bias -2 / 0 / +2 K) instead of the true mean, approximated as a uniform shift of the
     state's map (a capped state cannot be heated further), and the Ga table is looked up at
     that reading; with the Ga flux fixed, and corrected.
   The window margin (min over r <= 94 mm) is reported per state and droplet law.
4. Thickness half-range/mean on r <= 94 mm for layouts B and C (nominal pointing, 70 mm fill,
   2 mm lip) at their 1 um/h operating points, with the temperature-corrected Ga protocol,
   over the combined states: the heater's contribution when its errors act together.

Usage: python scripts/heater_robustness.py
"""

import importlib.util
import itertools
import json
import os
from pathlib import Path

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402

from mbe_twin.growth import load_parameters, steady_state  # noqa: E402
from mbe_twin.manifest import build_manifest, write_manifest  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("layout_comparison", ROOT / "scripts/layout_comparison.py")
lc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lc)
hz = lc.hz
EPS = (0.63, 0.70, 0.77)
CONTACT = (50.0, 200.0, 1000.0)
ZONE = (0.0, 0.02, -0.02)
OPENING = 0.099
T0_C = (700.0, 740.0)
LIMITS = {"1473 K element": 1473.15, "1373 K element": 1373.15}
BIASES_K = (-2.0, 0.0, 2.0)
RECORD = ROOT / "data/runs/studies/layout_comparison_bc.json"


def combined_states(t0_k, rho):
    """Zone ratios optimized for the nominal holder (no limit), then every combined error held at the mean."""
    edges = hz.LAYOUTS["12 zones"]
    geo = {"ledge_inner": OPENING}
    base = hz.make(edges, geo, {})
    states = []
    for lname, lim in {"none": None, **LIMITS}.items():
        r, frac = hz.optimize(base, t0_k, limits=None if lim is None else {"t_heater_max": lim})
        p0 = r["zone_power"].sum()
        for eps, h, z in itertools.product(EPS, CONTACT, ZONE):
            m = hz.make(edges, geo, {"eps_wafer": eps, "h_contact": h})
            cands = [frac] if z == 0.0 else []
            if z != 0.0:
                for k in range(m.n_zones):
                    f = frac.copy()
                    f[k] *= 1 + z
                    cands.append(f / f.sum())
            worst = None
            for f in cands:
                rr = hz.at_mean(m, f, t0_k, p0=p0)
                if worst is None or rr["wafer_range"] > worst[0]["wafer_range"]:
                    worst = (rr, f)
            rr, f = worst
            need = float(rr["t_heater"].max())
            capped = lim is not None and need > lim
            if capped:
                rr = hz.at_limit(m, f, lim, p_hi=rr["zone_power"].sum())
            states.append({"limit": lname, "eps": eps, "contact": h, "zone_error": z, "t_heater_needed_K": need,
                           "capped": bool(capped), "wafer_mean_K": rr["wafer_mean"], "wafer_range_K": rr["wafer_range"],
                           "t_map": np.interp(rho, rr["r_wafer"], rr["t_wafer"])})
    return states


def window(jn, ga_shape, t_map, params, law):
    """Centre Ga/N bounds of the Ga-rich window for N map jn (nm/min) and Ga shape (centre 1)."""
    fcrit = params.critical_excess(law, t_map)
    lo = float(np.max(jn / (jn[0] * ga_shape)))
    hi = float(np.min((jn + fcrit) / (jn[0] * ga_shape)))
    return lo, hi


def main():
    rec = json.loads(RECORD.read_text(encoding="utf-8"))
    env = rec["inputs"]["envelope"]
    rho = np.asarray(rec["outputs"]["rho_m"])
    params = load_parameters()
    laws = env["operating_point"]["droplet_onset_law"]["value"]
    # layout B nominal maps at its 1 um/h operating point (eta 1, 2 m^3/s, 740 C, 1473 K)
    row = next(r for r in rec["outputs"]["rows"] if r["layout"] == "B" and r["eta"] == 1.0 and r["S_eff_m3_s"] == 2.0
               and r.get("feed_limit_sccm", 10.0) == 10.0 and r["target"] == "1" and r["T0_C"] == 740.0
               and r["heater_limit"] == "1473 K element")
    p = row["operating_point"]["pressure_Pa"]
    nfile = next(c for c in rec["inputs"]["map_caches"] if c["file"].startswith("N_2.92_46_105_"))
    gfile = next(c for c in rec["inputs"]["map_caches"] if c["file"].startswith("Ga_46_70_"))
    z = np.load(ROOT / "results/layout_comparison_bc" / nfile["file"])
    if str(z["cache_key"]) != nfile["key"]:
        raise SystemExit("heater_robustness: N cache key mismatch")
    n_map = z["maps"][0] * lc.att_at(z["att"], p) * z["lip"][lc.LIP_H.index(0.002)]
    zg = np.load(ROOT / "results/layout_comparison_bc" / gfile["file"])
    if str(zg["cache_key"]) != gfile["key"]:
        raise SystemExit("heater_robustness: Ga cache key mismatch")
    g = lc.ga_shape(lc.ga_record(46, 70, "8"), rho) * lc.att_at(zg["att_8"], p) * zg["lip"][lc.LIP_H.index(0.002)]
    g = g / g[0]
    out = {}
    for t0 in T0_C:
        t0_k = t0 + lc.C
        states = combined_states(t0_k, rho)
        rate = row["operating_point"]["rate_nm_min"]
        res = []
        for st in states:
            tm = st["t_map"]
            dec = params.decomposition(tm)
            per_law = {}
            for law in laws:
                # nominal state (uniform target-temperature reference for the controller and the fixed protocol)
                nom = next(s for s in states if s["limit"] == st["limit"] and s["eps"] == 0.70 and s["contact"] == 200.0
                           and s["zone_error"] == 0.0)
                dec0 = params.decomposition(nom["t_map"])
                jn0 = (rate + lc.area_mean(dec0, rho)) / lc.area_mean(n_map, rho) * n_map
                lo0, hi0 = window(jn0, g, nom["t_map"], params, law)
                ga_fixed = 0.5 * (lo0 + hi0) * jn0[0]
                jn = (rate + lc.area_mean(dec, rho)) / lc.area_mean(n_map, rho) * n_map     # N re-set for the rate
                uni = np.full_like(tm, st["wafer_mean_K"])
                lo_c, hi_c = window(jn, g, uni, params, law)                              # controller's table at the reading
                lo_t, hi_t = window(jn, g, tm, params, law)                               # true window
                margins = {}
                for name, ga_c in (("fixed", ga_fixed), ("temperature-corrected", 0.5 * (lo_c + hi_c) * jn[0]),
                                   ("ideal", 0.5 * (lo_t + hi_t) * jn[0])):
                    s = steady_state(ga_c * g, jn, tm, params, law)
                    margins[name] = float(np.minimum(s["margin_to_n_rich"], s["margin_to_droplets"]).min())
                for bias in BIASES_K:
                    shift = t0_k - bias - tm[0]                  # heater drives the centre reading to the target
                    if st["capped"]:
                        shift = min(shift, 0.0)
                    tms = tm + shift
                    jns = (rate + lc.area_mean(params.decomposition(tms), rho)) / lc.area_mean(n_map, rho) * n_map
                    lo_p, hi_p = window(jns, g, np.full_like(tms, tms[0] + bias), params, law)
                    for name, ga_c in ((f"pyrometer {bias:+g} K, fixed", ga_fixed),
                                       (f"pyrometer {bias:+g} K, corrected", 0.5 * (lo_p + hi_p) * jns[0])):
                        s = steady_state(ga_c * g, jns, tms, params, law)
                        margins[name] = float(np.minimum(s["margin_to_n_rich"], s["margin_to_droplets"]).min())
                per_law[law] = margins
            res.append({k: v for k, v in st.items() if k != "t_map"} | {"margin": per_law})
        summary = {}
        for lname in ("none", *LIMITS):
            sub = [r for r in res if r["limit"] == lname]
            summary[lname] = {
                "capped_fraction": float(np.mean([r["capped"] for r in sub])),
                "t_heater_needed_max_K": max(r["t_heater_needed_K"] for r in sub),
                "mean_shortfall_max_K": max(t0_k - r["wafer_mean_K"] for r in sub),
                "wafer_range_max_K": max(r["wafer_range_K"] for r in sub),
                "in_window_fraction": {proto: float(np.mean([r["margin"][law][proto] >= 0 for r in sub for law in laws]))
                                       for proto in sub[0]["margin"][laws[0]]}}
            s = summary[lname]
            print(f"{t0:.0f} C, limit {lname}: element needed up to {s['t_heater_needed_max_K']:.1f} K, capped "
                  f"{100 * s['capped_fraction']:.0f} %, shortfall up to {s['mean_shortfall_max_K']:.1f} K, range up to "
                  f"{s['wafer_range_max_K']:.1f} K; in window: " + ", ".join(f"{k} {100 * v:.0f} %" for k, v in s["in_window_fraction"].items()),
                  flush=True)
        thick = {}
        for lay, (prefix, gprefix) in {"B": ("N_2.92_46_105_", "Ga_46_70_"), "C": ("N_2.92_65_75_", "Ga_46_70_")}.items():
            lrow = next(r for r in rec["outputs"]["rows"] if r["layout"] == lay and r["eta"] == 1.0 and r["S_eff_m3_s"] == 2.0
                        and r.get("feed_limit_sccm", 10.0) == 10.0 and r["target"] == "1" and r["T0_C"] == t0
                        and r["heater_limit"] == "1473 K element")
            pl = lrow["operating_point"]["pressure_Pa"]
            nf = next(c for c in rec["inputs"]["map_caches"] if c["file"].startswith(prefix))
            zn = np.load(ROOT / "results/layout_comparison_bc" / nf["file"])
            if str(zn["cache_key"]) != nf["key"]:
                raise SystemExit("heater_robustness: N cache key mismatch")
            nm = zn["maps"][0] * lc.att_at(zn["att"], pl) * zn["lip"][lc.LIP_H.index(0.002)]
            gl = lc.ga_shape(lc.ga_record(46, 70, "8"), rho) * lc.att_at(zg["att_8"], pl) * zg["lip"][lc.LIP_H.index(0.002)]
            gl = gl / gl[0]
            rl = lrow["operating_point"]["rate_nm_min"]
            per = {}
            for lname in ("none", *LIMITS):
                vals = []
                for st in (x for x in states if x["limit"] == lname):
                    tm = st["t_map"]
                    jn = (rl + lc.area_mean(params.decomposition(tm), rho)) / lc.area_mean(nm, rho) * nm
                    lo_c, hi_c = window(jn, gl, np.full_like(tm, st["wafer_mean_K"]), params, "Ref14_growth")
                    sres = steady_state(0.5 * (lo_c + hi_c) * jn[0] * gl, jn, tm, params, "Ref14_growth")
                    h = sres["net_growth"]
                    vals.append(float(100 * (h.max() - h.min()) / (2 * lc.area_mean(h, rho))))
                nom = [v for v, st in zip(vals, (x for x in states if x["limit"] == lname))
                       if st["eps"] == 0.70 and st["contact"] == 200.0 and st["zone_error"] == 0.0]
                per[lname] = {"nominal_pct": nom[0], "max_pct": max(vals), "median_pct": float(np.median(vals))}
                print(f"{t0:.0f} C, limit {lname}, layout {lay}: thickness nominal {nom[0]:.2f} %, combined heater errors "
                      f"median {np.median(vals):.2f} %, max {max(vals):.2f} %", flush=True)
            thick[lay] = per
        out[f"{t0:g}"] = {"states": res, "summary": summary, "thickness_combined_heater": thick,
                          "headroom_needed_K": {ln: max(r["t_heater_needed_K"] for r in res if r["limit"] == ln) - lim
                                                for ln, lim in LIMITS.items()}}
    manifest = build_manifest(
        "heater_robustness", label="representative_chamber", validation_status="not_validated",
        inputs={"eps": EPS, "contact": CONTACT, "zone_error": ZONE, "opening_m": OPENING, "T0_C": T0_C, "limits_K": LIMITS, "pyrometer_bias_K": BIASES_K,
                "record": str(RECORD.relative_to(ROOT)), "operating_point": row["operating_point"]},
        outputs=out,
        sources=[Path(__file__), ROOT / "scripts/heater_zones.py", ROOT / "scripts/layout_comparison.py",
                 ROOT / "src/mbe_twin/heater.py", ROOT / "src/mbe_twin/growth.py", RECORD],
        warnings=["Layout B nominal pointing, Ga fill and lip only", "The controller's Ga(T) table is computed from the model "
                  "itself; on the machine it would be a commissioning calibration", "Reduced axisymmetric heater model"])
    print(f"Wrote {write_manifest(manifest, ROOT / 'results/heater_robustness/manifest.json')}")


if __name__ == "__main__":
    main()
