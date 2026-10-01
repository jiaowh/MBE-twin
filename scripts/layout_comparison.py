"""Complete layouts compared at equal net growth rate under combined uncertainty (representative).

For each layout of data/design/design_envelope.json (Ga port, nitrogen plate and aim, heater
option), the chain of scripts/wafer_outcome.py is evaluated over a grid of uncertain states,
and reported together: thickness half-range/mean on the usable area (r <= 94 mm, the same
mask for every layout), the active-N output each layout needs for the same wafer-mean net
growth rate, the growth rate a fixed output would give, and the Ga-rich window margin.

Operating protocol (what is calibrated and what is not):
- Equal net growth rate: in every state the nitrogen output is set so that the wafer-mean net
  rate is the target (1 um/h). Static errors are thus calibrated out of the rate; the output
  this needs is reported (atoms/s), as is the rate a fixed output, set in the nominal state,
  would give instead.
- Ga/N: the centre Ga/N ratio is set to the middle of the Ga-rich window of the nominal state
  (70 mm fill, d = 8 A, nominal pointing and heater, 2 mm lip) under the same droplet law and
  pressure, i.e. the onset is calibrated at the centre. It then stays fixed: the centre Ga
  flux is held over the campaign (flux hold) and the other uncertainties act through the map
  shapes. The window margin is min over the usable area of the distance to N-rich growth and
  to droplets, as a fraction of the local N flux; negative means part of the wafer leaves the
  window.

Uncertain states (a grid, not a probability distribution; all combinations are evaluated):
- nitrogen pointing: the source axis tilted by 0.8 and 1.6 deg in 12 directions (every 30 deg
  round the axis), about the plate centre or about the mounting flange 0.30 m behind it (which
  also moves the plate); 49 maps per layout including nominal;
- Ga: the port's admissible fills (40 / 70 / 120 mm at 46 deg, 70 / 120 mm at 54 deg) and
  collision diameters 5.68 / 8 A (DSMC records, centre-flux-held where available);
- heater: zone powers optimized for the nominal holder under the heater limit, then held at
  those ratios while one wafer reading holds the mean: wafer emissivity 0.63 / 0.77, wafer-ledge
  contact 50 / 1000 W m^-2 K^-1, and +/-2 % in one zone's power (worst zone for each sign);
- holder lip height 1 / 2 / 3 mm (shadow ratio profiles);
- droplet-onset law: the three literature scenarios.
Operating conditions reported separately: growth temperature 700 / 740 C, heater limit (none,
1473 K element, 1373 K element), and background pressure from the envelope's flow / pumping
cases (direct-beam attenuation; zero pressure is the exact unattenuated regression).

Approximations: background attenuation and lip shadow enter as ratio profiles computed for the
nominal pose (nitrogen: its plate model; Ga: the free-molecular level-melt crucible of the same
fill and port). Free-molecular straight-hole nitrogen plates with uniform output. The net-rate
scaling assumes Ga-rich growth everywhere (states outside the window are flagged by the
margin). Ranking survival compares layouts in matched states (same tilt, Ga fill and diameter,
heater perturbation category, lip and droplet law), over the fills every layout admits.

Usage: python scripts/layout_comparison.py [--out results/layout_comparison] [--layouts ...]
                                          [--maps DIR] (reuse cached map files)
"""

import argparse
import importlib.util
import itertools
import json
import os
import time
from dataclasses import replace
from pathlib import Path

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402

from mbe_twin import profile_fit  # noqa: E402
from mbe_twin.aperture import aperture_plate_sources, hex_holes  # noqa: E402
from mbe_twin.beam import HolderLip, Wafer, crucible_source_on_cone, level_melt_normal, rotation_averaged_flux  # noqa: E402
from mbe_twin.crucible import Crucible, simulate  # noqa: E402
from mbe_twin.growth import load_parameters, steady_state  # noqa: E402
from mbe_twin.layout import SourcePort  # noqa: E402
from mbe_twin.manifest import build_manifest, write_manifest  # noqa: E402
from mbe_twin.vacuum import beam_mean_free_path, pressure_from_flow  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ENVELOPE = ROOT / "data/design/design_envelope.json"
GA_RECORDS = ROOT / "data/runs/sparta_ga"
_spec = importlib.util.spec_from_file_location("heater_zones", ROOT / "scripts/heater_zones.py")
hz = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hz)

C = 273.15
GA_EDGES = np.linspace(0.0, 0.100, 21)
TOLS_DEG = (0.8, 1.6)
TILT_DIRS_DEG = tuple(range(0, 360, 30))
LIP_H = (0.001, 0.002, 0.003)
T0_C = (700.0, 740.0)
LIMITS = {"none": None, "1473 K element": 1473.15, "1373 K element": 1373.15}
N_PARTICLES, N_SEED = 20_000, 80   # as nitrogen_aim_study.py (first aspect of a run)
GA_FM_PARTICLES = 60_000
GA_D = {"5.68": 6e-10, "8": 8e-10}  # DSMC diameter -> background-collision diameter scenario
HEATER_STATES = ("nominal", "eps 0.63", "eps 0.77", "contact 50", "contact 1000", "zone +2 % (worst)", "zone -2 % (worst)")


def ga_record(port, fill_mm, d):
    """Latest centre-flux-held record of a state, else the unheld one."""
    tag = f"fill{fill_mm:03d}_d{d}" + ("" if port == 46 else f"_{port}deg")
    held = [f"ga_dsmchold/{tag}_dsmchold.json"] + [f"ga_dsmchold/{tag}_dsmchold_it{k}.json" for k in range(2, 10)]
    held = [h for h in held if (GA_RECORDS / h).exists()]
    if held:
        return held[-1]
    plain = f"ga_batch/{tag}.json" if port == 46 else f"ga_angle/{tag}.json"
    if not (GA_RECORDS / plain).exists():
        raise SystemExit(f"layout_comparison: no Ga record for {tag}")
    return plain


def ga_shape(record, rho):
    o = json.loads((GA_RECORDS / record).read_text(encoding="utf-8"))["outputs"]
    coef = profile_fit.annulus_fit(np.asarray(o["dsmc_flux"]), GA_EDGES, 0.100, 4, np.asarray(o["dsmc_flux_stderr"]))
    f = profile_fit.evaluate(coef, rho, 0.100)
    return f / f[0]


def area_mean(x, rho):
    w = rho / rho.sum()
    return np.sum(w * x, axis=-1) / np.sum(w)


def nitrogen_maps(lay, env, rho, wafer, pressures, openings):
    """Absolute N flux per unit plate output for every pointing state, plus ratio profiles."""
    n = lay["n"]
    a = n["L_over_r"]
    ev = simulate(Crucible(1e-4, a * 1e-4), N_PARTICLES, rng=N_SEED)
    holes = hex_holes(0.020, 0.010)
    pivots = env["pointing_and_adjustment"]["tilt_pivot_behind_plate_m"]["value"]
    base = SourcePort("N", polar_deg=n["polar_deg"], azimuth_deg=0.0, throw=env["chamber"]["source_throw_m"]["value"],
                      aim_offset=n["aim_offset_mm"] / 1e3)

    def flux(port, **kw):
        pos, ax = port.pose(wafer)
        src = aperture_plate_sources("N", wafer, ev, holes, throw=port.throw, polar_angle=np.radians(port.polar_deg),
                                     azimuth=0.0, total_rate=1.0, aim_offset=port.aim_offset, axis=ax, centre=pos)
        return rotation_averaged_flux(src, wafer, rho, n_angles=36, **kw)

    states, maps = [("nominal", 0.0, 0.0)], [flux(base)]
    a0, out, side = base.frame(wafer)
    for pname, back in pivots.items():
        for tol in TOLS_DEG:
            for psi in TILT_DIRS_DEG:
                d = np.cos(np.radians(psi)) * out + np.sin(np.radians(psi)) * side
                states.append((pname, tol, float(psi)))
                maps.append(flux(replace(base, pivot_back=back).tilted(d, np.radians(tol))))
    env_v = env["vacuum"]
    d_n = env_v["collision_diameters_m"]["N"]
    t_n = env_v["beam_temperatures_K"]["N"]
    att = np.array([flux(base, mean_free_path=beam_mean_free_path(p, d_n, 14.007, t_n)) / maps[0] for p in pressures])
    lip = {o: np.array([flux(base, occluders=(HolderLip((0.0, 0.0, 0.0), tuple(wafer.normal), o, h),)) / maps[0]
                        for h in LIP_H]) for o in openings}
    return states, np.array(maps), att, lip


def ga_ratios(port, fill_mm, rho, wafer, pressures, openings, env):
    """Attenuation (per pressure and diameter) and lip ratio profiles from the free-molecular crucible."""
    env_v = env["vacuum"]
    ref = crucible_source_on_cone("x", wafer, None, throw=0.35, polar_angle=np.radians(port), azimuth=0.0, emission_rate=1.0)
    normal = level_melt_normal(ref.axis, up=tuple(-np.asarray(wafer.normal)))
    ev = simulate(Crucible(0.03575, fill_mm / 1e3, melt_normal=normal), GA_FM_PARTICLES, rng=300 + fill_mm)
    src = [crucible_source_on_cone("Ga", wafer, ev, throw=0.35, polar_angle=np.radians(port), azimuth=0.0, emission_rate=1.0)]
    f0 = rotation_averaged_flux(src, wafer, rho, n_angles=36)
    att = {d: np.array([rotation_averaged_flux(src, wafer, rho, n_angles=36, mean_free_path=beam_mean_free_path(
        p, dd, 69.72, env_v["beam_temperatures_K"]["Ga"])) / f0 for p in pressures]) for d, dd in GA_D.items()}
    lip = {o: np.array([rotation_averaged_flux(src, wafer, rho, n_angles=36, occluders=(
        HolderLip((0.0, 0.0, 0.0), tuple(wafer.normal), o, h),)) / f0 for h in LIP_H]) for o in openings}
    return att, lip


def heater_states(option, opening, t0_k, limit, rho):
    """Wafer temperature maps for the matched heater states, and the nominal heater report."""
    edges = hz.LAYOUTS["3 zones"] if option == "3 zones" else hz.LAYOUTS["12 zones"]
    geo = {"ledge_inner": opening}
    model = hz.make(edges, geo, {})
    r, frac = hz.optimize(model, t0_k, limits=None if limit is None else {"t_heater_max": limit})
    rep = {"wafer_range_K": r["wafer_range"], "violation": r["violation"], **hz.limit_report(model, r),
           "zone_fractions": frac.tolist()}
    maps, heaters = [np.interp(rho, r["r_wafer"], r["t_wafer"])], [float(r["t_heater"].max())]
    for props in ({"eps_wafer": 0.63}, {"eps_wafer": 0.77}, {"h_contact": 50.0}, {"h_contact": 1000.0}):
        m = hz.make(edges, geo, props)
        rr = hz.at_mean(m, frac, t0_k, p0=r["zone_power"].sum())
        maps.append(np.interp(rho, rr["r_wafer"], rr["t_wafer"]))
        heaters.append(float(rr["t_heater"].max()))
    for sgn in (1, -1):
        worst = None
        for k in range(model.n_zones):
            f = frac.copy()
            f[k] *= 1 + sgn * 0.02
            rr = hz.at_mean(model, f / f.sum(), t0_k, p0=r["zone_power"].sum())
            if worst is None or rr["wafer_range"] > worst["wafer_range"]:
                worst = rr
        maps.append(np.interp(rho, worst["r_wafer"], worst["t_wafer"]))
        heaters.append(float(worst["t_heater"].max()))
    rep["state_ranges_K"] = [float(m.max() - m.min()) for m in maps]
    rep["state_t_heater_max_K"] = heaters
    return np.array(maps), rep


def evaluate(n_maps, ga, t_maps, params, law, rho, target, k_atoms, nominal_idx):
    """Growth over the grid. n_maps (N, L, rho) absolute per unit output; ga (G, L, rho) centre-normalized;
    t_maps (H, rho). Returns arrays over (N, G, H, L)."""
    dec = params.decomposition(t_maps)                    # (H, rho)
    fcrit = params.critical_excess(law, t_maps)           # (H, rho)
    mean_n = area_mean(n_maps, rho)                       # (N, L)
    s = (target + area_mean(dec, rho))[None, :, None] / mean_n[:, None, :]   # (N, H, L) nm/min per unit
    j_n = s[:, None, :, :, None] * n_maps[:, None, None, :, :]               # (N, 1, H, L, rho)
    # centre Ga/N from the nominal state's window
    i_n, i_g, i_h, i_l = nominal_idx
    jn0 = j_n[i_n, 0, i_h, i_l]
    g0 = ga[i_g, i_l]
    lo = float(np.max(jn0 / (jn0[0] * g0)))
    hi = float(np.min((jn0 + fcrit[i_h]) / (jn0[0] * g0)))
    r0 = 0.5 * (lo + hi) if hi > lo else lo * 1.02
    j_ga = r0 * j_n[..., :1] * ga[None, :, None, :, :]                      # (N, G, H, L, rho)
    j_n = np.broadcast_to(j_n, j_ga.shape)
    st = steady_state(j_ga, j_n, np.broadcast_to(t_maps[None, None, :, None, :], j_ga.shape), params, law)
    h = st["net_growth"]
    mean_h = area_mean(h, rho)
    thick = 100 * (h.max(-1) - h.min(-1)) / (2 * mean_h)
    margin = np.minimum(st["margin_to_n_rich"], st["margin_to_droplets"]).min(-1)
    q = np.broadcast_to((s * k_atoms)[:, None, :, :], thick.shape)          # atoms/s
    q_nom = s[i_n, i_h, i_l] * k_atoms
    rate_fixed = np.broadcast_to((q_nom / k_atoms * mean_n[:, None, None, :] - area_mean(dec, rho)[None, None, :, None]),
                                 thick.shape)                                 # nm/min at the nominal output
    return {"thickness": thick, "margin": margin, "q": q, "rate_fixed": rate_fixed, "r0": r0,
            "window_nominal": [lo, hi], "mean_net": mean_h}


def summarize(res, factor_axes, nominal_idx):
    th, mg = res["thickness"], res["margin"]
    nom = tuple(nominal_idx)
    one = {}
    for name, ax in factor_axes.items():
        sl = list(nom)
        sl[ax] = slice(None)
        one[name] = {"thickness_max_pct": float(np.max(th[tuple(sl)])), "margin_min": float(np.min(mg[tuple(sl)]))}
    return {"nominal": {"thickness_pct": float(th[nom]), "margin": float(mg[nom]), "q_atoms_s": float(res["q"][nom])},
            "grid": {"thickness_pct": [float(th.min()), float(np.median(th)), float(np.percentile(th, 90)), float(th.max())],
                     "margin_min": float(mg.min()), "fraction_in_window": float(np.mean(mg >= 0.0)),
                     "q_atoms_s": [float(res["q"].min()), float(res["q"].max())],
                     "rate_at_nominal_output_nm_min": [float(res["rate_fixed"].min()), float(res["rate_fixed"].max())]},
            "one_factor": one, "centre_ga_n": res["r0"], "window_nominal": res["window_nominal"]}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="results/layout_comparison")
    ap.add_argument("--layouts", nargs="+")
    ap.add_argument("--maps", help="directory with cached nitrogen/Ga map files (written to --out otherwise)")
    args = ap.parse_args()
    env = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cache = Path(args.maps) if args.maps else out
    usable = env["wafer_and_mask"]["usable_radius_m"]["value"]
    rho = np.linspace(0.0, usable, 39)
    wafer = Wafer(radius=0.100)
    openings = env["wafer_and_mask"]["holder_opening_radius_m"]["value"]
    vac = env["vacuum"]
    t_gas = vac["gas_temperature_K"]["value"]
    pcases = {k: pressure_from_flow(q, s, t_gas) if q > 0 else 0.0 for k, (q, s) in vac["pressure_cases"].items()}
    pressures = list(pcases.values())
    params = load_parameters()
    gp = json.loads((ROOT / "data/parameters/gan_growth.json").read_text(encoding="utf-8"))
    k_atoms = gp["units"]["ml_per_s_per_nm_per_min"] * 1.14e19  # atoms m^-2 s^-1 per nm/min (1 ML = 1.14e15 cm^-2)
    target = 1000.0 * env["operating_point"]["net_growth_rate_um_h"]["value"] / 60.0
    laws = env["operating_point"]["droplet_onset_law"]["value"]
    names = args.layouts or list(env["layouts"])
    unknown = [n for n in names if n not in env["layouts"]]
    if unknown:
        raise SystemExit(f"layout_comparison: unknown layouts {unknown}")

    # ---- maps ----------------------------------------------------------------------------
    nmaps, gamaps = {}, {}
    for name in names:
        lay = env["layouts"][name]
        n = lay["n"]
        key = f"N_{n['L_over_r']:g}_{n['polar_deg']:g}_{n['aim_offset_mm']:g}"
        f = cache / f"{key}.npz"
        if f.exists():
            z = np.load(f, allow_pickle=False)
            nmaps[name] = (json.loads(str(z["states"])), z["maps"], z["att"], {o: z[f"lip_{k}"] for k, o in openings.items()})
        else:
            t = time.time()
            states, maps, att, lip = nitrogen_maps(lay, env, rho, wafer, pressures, list(openings.values()))
            np.savez(out / f"{key}.npz", states=json.dumps(states), maps=maps, att=att,
                     **{f"lip_{k}": lip[o] for k, o in openings.items()})
            nmaps[name] = (states, maps, att, {o: lip[o] for o in openings.values()})
            print(f"N maps {name}: {len(states)} pointing states in {time.time() - t:.0f} s", flush=True)
        port = lay["ga_port_deg"]
        fills = env["ga_source"]["port_options_deg"][str(port)]["admissible_fills_mm"]
        for fill in fills:
            gkey = f"Ga_{port}_{fill}"
            if gkey in gamaps:
                continue
            f = cache / f"{gkey}.npz"
            if f.exists():
                z = np.load(f)
                gamaps[gkey] = ({d: z[f"att_{d}"] for d in GA_D}, {o: z[f"lip_{k}"] for k, o in openings.items()})
            else:
                att, lip = ga_ratios(port, fill, rho, wafer, pressures, list(openings.values()), env)
                np.savez(out / f"{gkey}.npz", **{f"att_{d}": v for d, v in att.items()},
                         **{f"lip_{k}": lip[o] for k, o in openings.items()})
                gamaps[gkey] = (att, lip)
                print(f"Ga ratios {gkey} done", flush=True)

    # ---- heater ----------------------------------------------------------------------------
    heat = {}
    for opt, opening in (("3 zones", openings["3 mm overlap"]), ("designed density", openings["1 mm overlap"])):
        if not any(env["layouts"][n]["heater"] == opt for n in names):
            continue
        for t0 in T0_C:
            for lname, lim in LIMITS.items():
                heat[(opt, t0, lname)] = heater_states(opt, opening, t0 + C, lim, rho)
                r = heat[(opt, t0, lname)][1]
                print(f"heater {opt}, {t0:.0f} C, limit {lname}: range {r['wafer_range_K']:.2f} K, element max "
                      f"{r['t_heater_max_K']:.0f} K, {r['total_power_W']:.0f} W, violation {r['violation']:.3f}; "
                      f"perturbed ranges {min(r['state_ranges_K']):.1f}-{max(r['state_ranges_K']):.1f} K, element up to "
                      f"{max(r['state_t_heater_max_K']):.0f} K", flush=True)

    # ---- growth over the grid --------------------------------------------------------------
    rows, keep = [], {}
    for name in names:
        lay = env["layouts"][name]
        opening = openings["3 mm overlap"] if lay["heater"] == "3 zones" else openings["1 mm overlap"]
        states, maps, att_n, lip_n = nmaps[name]
        port = lay["ga_port_deg"]
        fills = env["ga_source"]["port_options_deg"][str(port)]["admissible_fills_mm"]
        g_labels = [(fill, d) for fill in fills for d in GA_D]
        ga_base = {lab: ga_shape(ga_record(port, lab[0], lab[1]), rho) for lab in g_labels}
        nominal_idx = (0, g_labels.index((70, "8")), 0, LIP_H.index(0.002))
        for (pk, p), t0, lname in itertools.product(pcases.items(), T0_C, LIMITS):
            n_full = maps[:, None, :] * att_n[list(pcases).index(pk)][None, None, :] * lip_n[opening][None, :, :]   # (N, L, rho)
            ga = []
            for fill, d in g_labels:
                att_g, lip_g = gamaps[f"Ga_{port}_{fill}"]
                g = ga_base[(fill, d)][None, :] * att_g[d][list(pcases).index(pk)][None, :] * lip_g[opening]
                ga.append(g / g[:, :1])
            ga = np.array(ga)                                                                      # (G, L, rho)
            t_maps, hrep = heat[(lay["heater"], t0, lname)]
            per_law = {}
            for law in laws:
                res = evaluate(n_full, ga, t_maps, params, law, rho, target, k_atoms, nominal_idx)
                per_law[law] = res
                keep[(name, p, t0, lname, law)] = (res["thickness"].astype(np.float32), res["margin"].astype(np.float32), g_labels)
            th = np.stack([per_law[l]["thickness"] for l in laws], -1)
            mg = np.stack([per_law[l]["margin"] for l in laws], -1)
            q = np.stack([per_law[l]["q"] for l in laws], -1)
            rf = np.stack([per_law[l]["rate_fixed"] for l in laws], -1)
            comb = {"thickness": th, "margin": mg, "q": q, "rate_fixed": rf,
                    "r0": {l: per_law[l]["r0"] for l in laws}, "window_nominal": {l: per_law[l]["window_nominal"] for l in laws}}
            axes = {"pointing (plate pivot)": None, "pointing (flange pivot)": None, "Ga fill and diameter": 1,
                    "heater perturbation": 2, "lip height": 3, "droplet law": 4}
            nom = nominal_idx + (laws.index("Ref14_growth"),)
            summ = summarize(comb, {k: v for k, v in axes.items() if v is not None}, nom)
            for pname in ("plate", "flange"):
                for tol in TOLS_DEG:
                    idx = [0] + [i for i, s in enumerate(states) if s[0] == pname and s[1] == tol]
                    sl = (idx,) + nom[1:]
                    summ["one_factor"][f"pointing {pname} pivot +/-{tol} deg"] = {
                        "thickness_max_pct": float(th[sl].max()), "margin_min": float(mg[sl].min())}
            # pointing within +/-0.8 deg only (the specified tolerance), all other factors varied
            idx08 = [0] + [i for i, s in enumerate(states) if s[1] == 0.8]
            summ["grid_0.8deg"] = {"thickness_pct_max": float(th[idx08].max()), "margin_min": float(mg[idx08].min()),
                                   "fraction_in_window": float(np.mean(mg[idx08] >= 0.0))}
            row = {"layout": name, "pressure_case": pk, "pressure_Pa": p, "T0_C": t0, "heater_limit": lname,
                   "heater": hrep, **summ}
            rows.append(row)
            if lname != "none" or p == 0.0:
                g = summ["grid"]
                print(f"{name:26s} p {p:7.1e} Pa {t0:.0f} C limit {lname:15s}: thickness nominal "
                      f"{summ['nominal']['thickness_pct']:.2f} %, grid {g['thickness_pct'][0]:.2f}-{g['thickness_pct'][3]:.2f} % "
                      f"(+/-0.8 deg: max {summ['grid_0.8deg']['thickness_pct_max']:.2f} %); margin nominal "
                      f"{summ['nominal']['margin']:+.3f}, min {g['margin_min']:+.3f}, in window {100 * g['fraction_in_window']:.0f} %; "
                      f"N output {summ['nominal']['q_atoms_s']:.2e} atoms/s", flush=True)

    # ---- ranking survival in matched states ------------------------------------------------
    ranking = []
    common_fills = set.intersection(*[set(env["ga_source"]["port_options_deg"][str(env["layouts"][n]["ga_port_deg"])]
                                          ["admissible_fills_mm"]) for n in names])
    for (pk, p), t0, lname in itertools.product(pcases.items(), T0_C, LIMITS):
        vals = {}
        for name in names:
            th_l, mg_l = [], []
            for law in laws:
                th, mg, g_labels = keep[(name, p, t0, lname, law)]
                gi = [i for i, (f, d) in enumerate(g_labels) if f in common_fills]
                th_l.append(th[:, gi])
                mg_l.append(mg[:, gi])
            vals[name] = (np.stack(th_l, -1), np.stack(mg_l, -1))
        pairs = {}
        for a, b in itertools.permutations(names, 2):
            ta, ma = vals[a]
            tb, mb = vals[b]
            pairs[f"{a} | {b}"] = {"thinner": float(np.mean(ta < tb)),
                                   "thinner_and_in_window": float(np.mean((ta < tb) & (ma >= 0.0)))}
        best_count = {}
        stack = np.stack([vals[n][0] for n in names])
        winner = np.argmin(stack, axis=0)
        for i, n in enumerate(names):
            best_count[n] = float(np.mean(winner == i))
        ranking.append({"pressure_case": pk, "pressure_Pa": p, "T0_C": t0, "heater_limit": lname,
                        "fraction_best": best_count, "pairwise": pairs, "matched_fills_mm": sorted(common_fills)})
        if lname == "1473 K element" and p in (0.0, pcases["2 sccm / 2 m3/s"]):
            print(f"best-layout share, p {p:.1e} Pa, {t0:.0f} C, {lname}: "
                  + ", ".join(f"{n} {100 * v:.0f} %" for n, v in best_count.items()))

    manifest = build_manifest(
        "layout_comparison", label="representative_chamber", validation_status="not_validated",
        inputs={"envelope": env, "layouts": names, "pressure_cases_Pa": pcases, "T0_C": T0_C, "heater_limits_K": LIMITS,
                "tilts_deg": TOLS_DEG, "tilt_directions_deg": TILT_DIRS_DEG, "lip_heights_m": LIP_H,
                "heater_states": HEATER_STATES, "ga_diameters": GA_D, "n_particles": N_PARTICLES, "n_seed": N_SEED,
                "usable_radius_m": usable, "target_nm_min": target, "atoms_per_m2_s_per_nm_min": k_atoms},
        outputs={"rows": rows, "ranking": ranking, "rho_m": rho},
        sources=[Path(__file__), ROOT / "scripts/heater_zones.py", ROOT / "src/mbe_twin/growth.py",
                 ROOT / "src/mbe_twin/heater.py", ROOT / "src/mbe_twin/aperture.py", ROOT / "src/mbe_twin/beam.py",
                 ROOT / "src/mbe_twin/layout.py", ROOT / "src/mbe_twin/vacuum.py", ENVELOPE,
                 ROOT / "data/parameters/gan_growth.json"],
        warnings=["Representative-chamber comparison; no model in the chain is validated on the proposed machine",
                  "Uncertainty grid, not a probability distribution: percentiles are over grid states",
                  "Background attenuation removes direct beam only; scattered arrival not modelled",
                  "Attenuation and lip shadow as nominal-pose ratio profiles; free-molecular N plates with uniform output",
                  "Total active-N output capability of the source is unknown: required outputs are reported, not checked"],
        disabled_physics=["transients", "morphology", "AlN", "scattered-beam redeposition", "Ga pointing error"])
    print(f"Wrote {write_manifest(manifest, out / 'manifest.json')}")


if __name__ == "__main__":
    main()
