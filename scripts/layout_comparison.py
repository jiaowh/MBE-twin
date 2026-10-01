"""Complete layouts at a physically achievable operating point, under combined uncertainty (representative).

For each layout of data/design/design_envelope.json (Ga port, nitrogen plate and aim, heater
option), the chain of scripts/wafer_outcome.py is evaluated over a grid of uncertain states at
an operating point that the nitrogen feed, the pumping and the heater can actually supply.
Reported together: thickness half-range/mean and area-weighted standard deviation/mean on the
usable area (r <= 94 mm, the same mask for every layout), the growth rate reached, the Ga-rich
window margin, and every equipment-limit violation (feed, plate flow regime, heater element).

Nitrogen balance (one operating point per layout and scenario):
- The active-N output leaving the plate is q = eta x 2 x (N2 feed in molecules/s); eta, the
  fraction of the feed's N atoms that leave as growth-active N, is a missing source input and
  is set by scenario (1 is the atom-content bound, not an achievable efficiency).
- The growth pressure is p = Q / S_eff (vacuum.pressure_from_flow, all feed counted as N2:
  atoms recombine on the walls). It attenuates the direct N and Ga beams.
- The feed is solved so that the wafer-mean net rate is the target (1 um/h). The solution is
  a fixed point, because more feed raises the pressure, which lowers the delivered fraction.
  If it needs more than the feed limit, or no fixed point exists, the operating point becomes
  the highest rate reachable at any feed up to the limit (the rate peaks where attenuation
  grows faster than the feed). The row is then evaluated at that achievable rate.
- The same is done at lower target rates (0.5 and 0.25 um/h): less feed means lower pressure
  and less attenuation, so uniformity trades against rate. Rows whose reachable rate is below
  0.1 um/h are recorded as operating points only (decomposition rivals growth there; this is
  a reporting floor, not a requirement). Layouts are ranked only at equal target rates.
- The plate holes are checked at that feed: Knudsen number lambda/(2 r) behind the plate of
  the envelope's hole set (free-molecular conductance, as scripts/nitrogen_plate_scenarios.py).
  Kn < 10 means the free-molecular plate model behind every N map is outside its validity.

Operating protocol over the uncertainty grid:
- Nitrogen: in every state the output is re-set for the operating rate, i.e. the rate is
  calibrated in the state the machine is in, up to the output that the feed limit gives. A
  state that would need more is supply-limited: it runs at the limit and grows slower. Where
  the rate peaks below the feed limit, the peak feed is the limit. The pressure stays at the
  operating point's.
- Ga: a fixed absolute centre flux. It is set once, in the nominal state (70 mm fill, d = 8 A,
  nominal pointing, nominal heater, 2 mm lip), to the middle of that state's Ga-rich window at
  the centre, under the same droplet law. Every other state uses the same centre flux (the
  centre-flux hold of the Ga DSMC records); only the map shapes change. Because N is re-set
  per state, the centre Ga/N ratio moves with it. The window margin is the minimum over the
  usable area of the distance to N-rich growth and to droplets, as a fraction of the local N
  flux; negative means part of the wafer leaves the window.
- Heater: zone powers optimized for the nominal holder under the element limit, then held at
  those ratios while one wafer reading holds the mean. If a perturbed state needs the element
  above the limit to hold the mean, the power is capped at the limit and the state is grown at
  the wafer temperature it reaches (flagged, with the shortfall).

Uncertain states (a grid, not a probability distribution; all combinations are evaluated):
- nitrogen pointing: the source axis tilted by 0.8 and 1.6 deg in 12 directions (every 30 deg
  round the axis), about the plate centre or about the mounting flange 0.30 m behind it (which
  also moves the plate); 49 maps per layout including nominal;
- Ga: the port's admissible fills (40 / 70 / 120 mm at 46 deg, 70 / 120 mm at 54 deg) and
  collision diameters 5.68 / 8 A (DSMC records, centre-flux-held where available);
- heater, seven categories, each perturbed alone (not combined with each other): nominal,
  wafer emissivity 0.63 / 0.77, wafer-ledge contact 50 / 1000 W m^-2 K^-1, +/-2 % in one zone's
  power (worst zone for each sign);
- holder lip height 1 / 2 / 3 mm (shadow ratio profiles);
- droplet-onset law: the three literature scenarios.
Not in the grid: the N plate output profile, the plate geometry, scattered-beam redeposition,
Ga pointing, and combinations of heater perturbations. Operating scenarios (not uncertainty
states): conversion fraction, effective pumping speed, growth temperature 700 / 740 C, element
limit 1473 / 1373 K.

Approximations: background attenuation and lip shadow enter as ratio profiles computed for the
nominal pose (nitrogen: its plate model; Ga: the free-molecular level-melt crucible of the same
fill and port), attenuation interpolated in log between pressures of a fixed grid. Free-molecular
straight-hole nitrogen plates with uniform output. Ranking compares layouts in matched states
(same tilt, Ga fill and diameter, heater category, lip and droplet law) over the fills every
layout admits.

Caches: every map file is keyed by a hash of its generating inputs and code; a cached file
whose key does not match is an error, not a reuse.

Usage: python scripts/layout_comparison.py [--out results/layout_comparison_bc] [--layouts B C]
                                          [--maps DIR] (directory of keyed map files)
"""

import argparse
import hashlib
import importlib.util
import inspect
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
from mbe_twin.manifest import build_manifest, canonical_hash, source_sha256, write_manifest  # noqa: E402
from mbe_twin.metrics import radial_ring_weights  # noqa: E402
from mbe_twin.vacuum import K_B, SCCM_PA_M3_S, T_STD, beam_mean_free_path, pressure_from_flow  # noqa: E402

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
LIMITS = {"1473 K element": 1473.15, "1373 K element": 1373.15}
N_PARTICLES, N_SEED = 20_000, 80   # as nitrogen_aim_study.py (first aspect of a run)
GA_FM_PARTICLES = 60_000
GA_D = {"5.68": 6e-10, "8": 8e-10}  # DSMC diameter -> background-collision diameter scenario
HEATER_STATES = ("nominal", "eps 0.63", "eps 0.77", "contact 50", "contact 1000", "zone +2 % (worst)", "zone -2 % (worst)")
P_GRID = (0.0, 2.5e-4, 5e-4, 1e-3, 2e-3, 4e-3, 7e-3, 1e-2, 1.5e-2, 2e-2, 3e-2, 4e-2, 5e-2)  # Pa, attenuation tables
N_ATOMS_PER_SCCM = 2.0 * SCCM_PA_M3_S / (K_B * T_STD)   # N atoms/s in 1 sccm of N2 (8.956e17)
KN_VALID = 10.0
THRESHOLDS_PCT = (1.0, 2.0, 3.0, 5.0)
TARGETS_UM_H = (1.0, 0.5, 0.25)   # wafer-mean net rates; 1 um/h is the envelope working rate
USEFUL_RATE_UM_H = 0.1   # reporting floor, not a requirement: below it decomposition rivals growth
SOURCES = [Path(__file__), ROOT / "scripts/heater_zones.py", ROOT / "src/mbe_twin/growth.py", ROOT / "src/mbe_twin/heater.py",
           ROOT / "src/mbe_twin/radiation.py", ROOT / "src/mbe_twin/aperture.py", ROOT / "src/mbe_twin/beam.py",
           ROOT / "src/mbe_twin/crucible.py", ROOT / "src/mbe_twin/layout.py", ROOT / "src/mbe_twin/vacuum.py",
           ROOT / "src/mbe_twin/profile_fit.py", ROOT / "src/mbe_twin/metrics.py", ROOT / "src/mbe_twin/units.py",
           ENVELOPE, ROOT / "data/parameters/gan_growth.json"]
MAP_MODULES = [ROOT / "src/mbe_twin/aperture.py", ROOT / "src/mbe_twin/beam.py", ROOT / "src/mbe_twin/crucible.py",
               ROOT / "src/mbe_twin/layout.py", ROOT / "src/mbe_twin/vacuum.py"]


def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


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


def area_weights(rho):
    """Annulus area weights of the samples (each owns the ring between midpoints), normalized."""
    w = radial_ring_weights(rho, rho[-1])
    return w / w.sum()


def area_mean(x, rho):
    return np.sum(area_weights(rho) * x, axis=-1)


def area_std(x, rho):
    w = area_weights(rho)
    m = np.sum(w * x, axis=-1, keepdims=True)
    return np.sqrt(np.sum(w * (x - m) ** 2, axis=-1))


def cache_key(kind, inputs, funcs):
    """Hash of everything that generates a map file: inputs, generating functions, model modules."""
    return canonical_hash({"kind": kind, "inputs": inputs, "code": [inspect.getsource(f) for f in funcs],
                           "modules": {p.name: file_sha256(p) for p in MAP_MODULES}})


def load_or_build(cache, out, kind, inputs, funcs, build):
    """Keyed cache: reuse only a file whose stored key matches; otherwise build and write it."""
    key = cache_key(kind, inputs, funcs)
    name = f"{kind}_{key[:12]}.npz"
    for d in dict.fromkeys((cache, out)):
        f = d / name
        if f.exists():
            z = np.load(f, allow_pickle=False)
            if str(z["cache_key"]) != key:
                raise SystemExit(f"layout_comparison: cache {f} has key {str(z['cache_key'])[:12]}, expected {key[:12]}")
            return {k: z[k] for k in z.files if k not in ("cache_key", "inputs")}, {"file": name, "key": key, "reused": True}
    t = time.time()
    arrays = build()
    np.savez(out / name, cache_key=key, inputs=json.dumps(inputs, sort_keys=True, default=np.ndarray.tolist), **arrays)
    print(f"built {name} in {time.time() - t:.0f} s", flush=True)
    return arrays, {"file": name, "key": key, "reused": False}


def nitrogen_maps(lay, env, rho, wafer, pressures, opening):
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
    lip = np.array([flux(base, occluders=(HolderLip((0.0, 0.0, 0.0), tuple(wafer.normal), opening, h),)) / maps[0]
                    for h in LIP_H])
    return states, np.array(maps), att, lip


def ga_ratios(port, fill_mm, rho, wafer, pressures, opening, env):
    """Attenuation (per pressure and diameter) and lip ratio profiles from the free-molecular crucible."""
    env_v = env["vacuum"]
    ref = crucible_source_on_cone("x", wafer, None, throw=0.35, polar_angle=np.radians(port), azimuth=0.0, emission_rate=1.0)
    normal = level_melt_normal(ref.axis, up=tuple(-np.asarray(wafer.normal)))
    ev = simulate(Crucible(0.03575, fill_mm / 1e3, melt_normal=normal), GA_FM_PARTICLES, rng=300 + fill_mm)
    src = [crucible_source_on_cone("Ga", wafer, ev, throw=0.35, polar_angle=np.radians(port), azimuth=0.0, emission_rate=1.0)]
    f0 = rotation_averaged_flux(src, wafer, rho, n_angles=36)
    att = {d: np.array([rotation_averaged_flux(src, wafer, rho, n_angles=36, mean_free_path=beam_mean_free_path(
        p, dd, 69.72, env_v["beam_temperatures_K"]["Ga"])) / f0 for p in pressures]) for d, dd in GA_D.items()}
    lip = np.array([rotation_averaged_flux(src, wafer, rho, n_angles=36, occluders=(
        HolderLip((0.0, 0.0, 0.0), tuple(wafer.normal), opening, h),)) / f0 for h in LIP_H])
    return att, lip


def att_at(table, p, grid=P_GRID):
    """Attenuation ratio profile at pressure p, interpolated in log between grid pressures."""
    grid = np.asarray(grid)
    if not 0.0 <= p <= grid[-1]:
        raise ValueError(f"pressure {p:.3g} Pa outside the attenuation table (0-{grid[-1]:g} Pa)")
    k = int(np.clip(np.searchsorted(grid, p, side="right") - 1, 0, len(grid) - 2))
    u = (p - grid[k]) / (grid[k + 1] - grid[k])
    return np.exp((1.0 - u) * np.log(table[k]) + u * np.log(table[k + 1]))


def plate_knudsen(q_sccm, plate, t_gas, d_factor=1.0):
    """Hole Knudsen number behind the plate (free-molecular conductance; nitrogen_plate_scenarios.knudsen)."""
    r = plate["hole_diameter_m"] / 2.0
    m = 28.0134 * 1.66053907e-27
    v = np.sqrt(8 * K_B * t_gas / (np.pi * m))
    conductance = plate["holes"] * v / 4 * np.pi * r * r * plate["transmission"]
    p = q_sccm * SCCM_PA_M3_S * (t_gas / T_STD) / conductance
    lam = K_B * t_gas / (np.sqrt(2) * np.pi * (3.7e-10 * d_factor) ** 2 * p)
    return float(lam / (2 * r))


def operating_point(delivered, dec_mean, target, eta, speed, feed_max, t_gas, k_atoms, n_feed=400):
    """Feed, pressure and rate that the nitrogen balance allows (see module docstring).

    delivered(p): wafer-mean N flux per unit output (nominal pose) at pressure p. Rates in nm/min.
    Returns the target operating point if a fixed point exists within feed_max, else the
    highest rate reachable at any feed up to feed_max.
    """
    def rate(q_sccm):
        p = pressure_from_flow(q_sccm, speed, t_gas)
        return eta * N_ATOMS_PER_SCCM * q_sccm / k_atoms * delivered(p) - dec_mean, p

    q = 0.0
    for _ in range(200):   # monotone fixed-point iteration from zero pressure
        p = pressure_from_flow(q, speed, t_gas) if q > 0 else 0.0
        q_new = (target + dec_mean) / delivered(p) * k_atoms / (eta * N_ATOMS_PER_SCCM)
        if q_new > feed_max:
            break
        if abs(q_new - q) < 1e-9 * q_new:
            r, p = rate(q_new)
            return {"feed_sccm": q_new, "pressure_Pa": p, "rate_nm_min": r, "target_reached": True, "feed_limited": False}
        q = q_new
    feeds = np.linspace(feed_max / n_feed, feed_max, n_feed)
    rates = np.array([rate(f)[0] for f in feeds])
    i = int(np.argmax(rates))
    r, p = rate(feeds[i])
    return {"feed_sccm": float(feeds[i]), "pressure_Pa": p, "rate_nm_min": float(r), "target_reached": False,
            "feed_limited": True, "rate_peaks_below_feed_limit": bool(i < n_feed - 1)}


def heater_states(option, opening, t0_k, limit, rho):
    """Wafer temperature maps for the matched heater states, with every state held to the element limit."""
    edges = hz.LAYOUTS["3 zones"] if option == "3 zones" else hz.LAYOUTS["12 zones"]
    geo = {"ledge_inner": opening}
    model = hz.make(edges, geo, {})
    r, frac = hz.optimize(model, t0_k, limits=None if limit is None else {"t_heater_max": limit})
    rep = {"wafer_range_K": r["wafer_range"], "violation": r["violation"], **hz.limit_report(model, r),
           "zone_fractions": frac.tolist()}
    p0 = r["zone_power"].sum()

    def held(m, f):
        """Hold the mean with one reading; cap the power at the element limit if that needs more."""
        rr = hz.at_mean(m, f, t0_k, p0=p0)
        need = float(rr["t_heater"].max())
        if limit is not None and need > limit:
            rr = hz.at_limit(m, f, limit, p_hi=rr["zone_power"].sum())
            return rr, need, True
        return rr, need, False

    results = [held(model, frac)]
    for props in ({"eps_wafer": 0.63}, {"eps_wafer": 0.77}, {"h_contact": 50.0}, {"h_contact": 1000.0}):
        results.append(held(hz.make(edges, geo, props), frac))
    for sgn in (1, -1):
        worst = None
        for k in range(model.n_zones):
            f = frac.copy()
            f[k] *= 1 + sgn * 0.02
            res = held(model, f / f.sum())
            if worst is None or res[0]["wafer_range"] > worst[0]["wafer_range"]:
                worst = res
        results.append(worst)
    maps = np.array([np.interp(rho, rr["r_wafer"], rr["t_wafer"]) for rr, _, _ in results])
    rep["state_ranges_K"] = [float(m.max() - m.min()) for m in maps]
    rep["state_t_heater_max_K"] = [float(rr["t_heater"].max()) for rr, _, _ in results]
    rep["state_t_heater_needed_K"] = [need for _, need, _ in results]
    rep["state_capped"] = [cap for _, _, cap in results]
    rep["state_wafer_mean_K"] = [rr["wafer_mean"] for rr, _, _ in results]
    rep["state_mean_shortfall_K"] = [t0_k - rr["wafer_mean"] for rr, _, _ in results]
    return maps, rep


def evaluate(n_maps, ga, t_maps, params, law, rho, target, k_atoms, nominal_idx, s_max=np.inf):
    """Growth over the grid. n_maps (N, L, rho) absolute per unit output; ga (G, L, rho) centre-normalized;
    t_maps (H, rho). s_max: the output (in nm/min per unit map) the feed limit allows. Returns arrays
    over (N, G, H, L)."""
    dec = params.decomposition(t_maps)                    # (H, rho)
    fcrit = params.critical_excess(law, t_maps)           # (H, rho)
    mean_n = area_mean(n_maps, rho)                       # (N, L)
    s_req = (target + area_mean(dec, rho))[None, :, None] / mean_n[:, None, :]   # (N, H, L) output for the target
    s = np.minimum(s_req, s_max)
    j_n = s[:, None, :, :, None] * n_maps[:, None, None, :, :]               # (N, 1, H, L, rho)
    # Ga centre flux: set once from the nominal state's window, then held (absolute)
    i_n, i_g, i_h, i_l = nominal_idx
    jn0 = j_n[i_n, 0, i_h, i_l]
    g0 = ga[i_g, i_l]
    lo = float(np.max(jn0 / (jn0[0] * g0)))
    hi = float(np.min((jn0 + fcrit[i_h]) / (jn0[0] * g0)))
    r0 = 0.5 * (lo + hi) if hi > lo else lo * 1.02
    ga_centre = r0 * float(jn0[0])
    j_ga = np.broadcast_to(ga_centre * ga[None, :, None, :, :], (j_n.shape[0],) + ga.shape[:1] + j_n.shape[2:])
    j_n = np.broadcast_to(j_n, j_ga.shape)
    st = steady_state(j_ga, j_n, np.broadcast_to(t_maps[None, None, :, None, :], j_ga.shape), params, law)
    h = st["net_growth"]
    mean_h = area_mean(h, rho)
    thick = 100 * (h.max(-1) - h.min(-1)) / (2 * mean_h)
    std = 100 * area_std(h, rho) / mean_h
    margin = np.minimum(st["margin_to_n_rich"], st["margin_to_droplets"]).min(-1)
    q = np.broadcast_to((s * k_atoms)[:, None, :, :], thick.shape)          # atoms/s
    limited = np.broadcast_to((s_req > s_max)[:, None, :, :], thick.shape)
    q_nom = s[i_n, i_h, i_l] * k_atoms
    rate_fixed = np.broadcast_to((q_nom / k_atoms * mean_n[:, None, None, :] - area_mean(dec, rho)[None, None, :, None]),
                                 thick.shape)                                 # nm/min at the nominal output
    return {"thickness": thick, "std": std, "margin": margin, "q": q, "supply_limited": limited, "rate_fixed": rate_fixed,
            "r0": r0, "ga_centre": ga_centre, "window_nominal": [lo, hi], "mean_net": mean_h}


def summarize(res, factor_axes, nominal_idx, idx08):
    th, sd, mg, rate, lim = res["thickness"], res["std"], res["margin"], res["mean_net"], res["supply_limited"]
    nom = tuple(nominal_idx)
    one = {}
    for name, ax in factor_axes.items():
        sl = list(nom)
        sl[ax] = slice(None)
        one[name] = {"thickness_max_pct": float(np.max(th[tuple(sl)])), "margin_min": float(np.min(mg[tuple(sl)]))}
    t8, m8, r8 = th[idx08], mg[idx08], rate[idx08]
    return {"nominal": {"thickness_pct": float(th[nom]), "std_pct": float(sd[nom]), "margin": float(mg[nom]),
                        "q_atoms_s": float(res["q"][nom]), "rate_nm_min": float(rate[nom])},
            "grid": {"thickness_pct": [float(th.min()), float(np.median(th)), float(np.percentile(th, 90)), float(th.max())],
                     "std_pct_max": float(sd.max()), "margin_min": float(mg.min()), "fraction_in_window": float(np.mean(mg >= 0.0)),
                     "fraction_supply_limited": float(np.mean(lim)),
                     "rate_nm_min": [float(rate.min()), float(rate.max())],
                     "q_atoms_s": [float(res["q"].min()), float(res["q"].max())],
                     "rate_at_nominal_output_nm_min": [float(res["rate_fixed"].min()), float(res["rate_fixed"].max())]},
            "grid_0.8deg": {"thickness_pct_max": float(t8.max()), "std_pct_max": float(sd[idx08].max()),
                            "margin_min": float(m8.min()), "fraction_in_window": float(np.mean(m8 >= 0.0)),
                            "fraction_supply_limited": float(np.mean(lim[idx08])),
                            "rate_nm_min": [float(r8.min()), float(r8.max())],
                            # share of states in the window whose thickness is at most each threshold
                            "fraction_in_window_and_within_pct": {f"{t:g}": float(np.mean((t8 <= t) & (m8 >= 0.0)))
                                                                  for t in THRESHOLDS_PCT}},
            "one_factor": one, "centre_ga_n": res["r0"], "ga_centre_nm_min": res["ga_centre"],
            "window_nominal": res["window_nominal"]}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="results/layout_comparison_bc")
    ap.add_argument("--layouts", nargs="+", default=["B", "C"])
    ap.add_argument("--maps", help="directory with keyed map files (written to --out otherwise)")
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
    nsrc = env["nitrogen_source"]
    etas = nsrc["active_n_fraction_of_feed_atoms"]["scenarios"]
    feed_max = nsrc["feed_limit_sccm"]["value"]
    speeds = vac["effective_N2_speed_m3_s"]["bracket"]
    plate = dict(nsrc["plate"]["value"])
    plate["transmission"] = simulate(Crucible(1.0, plate["thickness_m"] / (plate["hole_diameter_m"] / 2)), 200_000, rng=5,
                                     record_events=False).transmission
    params = load_parameters()
    gp = json.loads((ROOT / "data/parameters/gan_growth.json").read_text(encoding="utf-8"))
    k_atoms = gp["units"]["ml_per_s_per_nm_per_min"] * 1.14e19  # atoms m^-2 s^-1 per nm/min (1 ML = 1.14e15 cm^-2)
    target = 1000.0 * env["operating_point"]["net_growth_rate_um_h"]["value"] / 60.0
    laws = env["operating_point"]["droplet_onset_law"]["value"]
    names = args.layouts
    unknown = [n for n in names if n not in env["layouts"]]
    if unknown:
        raise SystemExit(f"layout_comparison: unknown layouts {unknown}")
    opening_of = {n: openings["3 mm overlap"] if env["layouts"][n]["heater"] == "3 zones" else openings["1 mm overlap"]
                  for n in names}

    # ---- maps (keyed caches) ------------------------------------------------------------------
    nmaps, gamaps, caches = {}, {}, []
    for name in names:
        lay = env["layouts"][name]
        opening = opening_of[name]
        inputs = {"n": lay["n"], "env_pointing": env["pointing_and_adjustment"]["tilt_pivot_behind_plate_m"],
                  "throw": env["chamber"]["source_throw_m"]["value"], "vacuum": {k: vac[k] for k in ("collision_diameters_m", "beam_temperatures_K")},
                  "rho": rho, "wafer_radius": wafer.radius, "opening": opening, "lip_h": LIP_H, "p_grid": P_GRID,
                  "tols": TOLS_DEG, "tilt_dirs": TILT_DIRS_DEG, "n_particles": N_PARTICLES, "n_seed": N_SEED}

        def build_n(lay=lay, opening=opening):
            states, maps, att, lip = nitrogen_maps(lay, env, rho, wafer, P_GRID, opening)
            return {"states": json.dumps(states), "maps": maps, "att": att, "lip": lip}
        n = lay["n"]
        arr, info = load_or_build(cache, out, f"N_{n['L_over_r']:g}_{n['polar_deg']:g}_{n['aim_offset_mm']:g}", inputs,
                                  [nitrogen_maps], build_n)
        caches.append(info)
        nmaps[name] = (json.loads(str(arr["states"])), arr["maps"], arr["att"], arr["lip"])
        port = lay["ga_port_deg"]
        for fill in env["ga_source"]["port_options_deg"][str(port)]["admissible_fills_mm"]:
            gkey = (port, fill, opening)
            if gkey in gamaps:
                continue
            ginputs = {"port": port, "fill_mm": fill, "rho": rho, "wafer_radius": wafer.radius, "opening": opening,
                       "lip_h": LIP_H, "p_grid": P_GRID, "ga_d": GA_D, "particles": GA_FM_PARTICLES,
                       "t_beam": vac["beam_temperatures_K"]["Ga"]}

            def build_ga(port=port, fill=fill, opening=opening):
                att, lip = ga_ratios(port, fill, rho, wafer, P_GRID, opening, env)
                return {**{f"att_{d}": v for d, v in att.items()}, "lip": lip}
            arr, info = load_or_build(cache, out, f"Ga_{port}_{fill}_{opening * 1e3:g}", ginputs, [ga_ratios], build_ga)
            caches.append(info)
            gamaps[gkey] = ({d: arr[f"att_{d}"] for d in GA_D}, arr["lip"])

    # ---- heater (every state held to the element limit) ---------------------------------------
    heat = {}
    for opt in sorted({env["layouts"][n]["heater"] for n in names}):
        opening = openings["3 mm overlap"] if opt == "3 zones" else openings["1 mm overlap"]
        for t0 in T0_C:
            for lname, lim in LIMITS.items():
                heat[(opt, t0, lname)] = heater_states(opt, opening, t0 + C, lim, rho)
                r = heat[(opt, t0, lname)][1]
                capped = [s for s, c in zip(HEATER_STATES, r["state_capped"]) if c]
                print(f"heater {opt}, {t0:.0f} C, {lname}: range {r['wafer_range_K']:.2f} K, element {r['t_heater_max_K']:.1f} K; "
                      f"capped states {capped or 'none'}"
                      + (f", shortfall up to {max(r['state_mean_shortfall_K']):.1f} K (needed up to "
                         f"{max(r['state_t_heater_needed_K']):.1f} K)" if capped else ""), flush=True)

    # ---- Ga records consumed ---------------------------------------------------------------------
    ga_used = {}
    for name in names:
        port = env["layouts"][name]["ga_port_deg"]
        for fill in env["ga_source"]["port_options_deg"][str(port)]["admissible_fills_mm"]:
            for d in GA_D:
                rec = ga_record(port, fill, d)
                ga_used[rec] = file_sha256(GA_RECORDS / rec)

    # ---- operating points and growth over the grid ------------------------------------------------
    rows, keep, op_table = [], {}, []
    for name in names:
        lay = env["layouts"][name]
        opening = opening_of[name]
        states, maps, att_n, lip_n = nmaps[name]
        port = lay["ga_port_deg"]
        fills = env["ga_source"]["port_options_deg"][str(port)]["admissible_fills_mm"]
        g_labels = [(fill, d) for fill in fills for d in GA_D]
        ga_base = {lab: ga_shape(ga_record(port, lab[0], lab[1]), rho) for lab in g_labels}
        nominal_idx = (0, g_labels.index((70, "8")), 0, LIP_H.index(0.002))
        idx08 = [0] + [i for i, s in enumerate(states) if s[1] == 0.8]

        def delivered(p):
            return float(area_mean(maps[0] * att_at(att_n, p) * lip_n[LIP_H.index(0.002)], rho))

        for eta, speed, t0, lname in itertools.product(etas, speeds, T0_C, LIMITS):
            t_maps, hrep = heat[(lay["heater"], t0, lname)]
            dec_mean = float(area_mean(params.decomposition(t_maps[0]), rho))
            ops = []
            for tgt in TARGETS_UM_H:
                op = operating_point(delivered, dec_mean, 1000.0 * tgt / 60.0, eta, speed, feed_max, t_gas, k_atoms)
                if op["target_reached"]:
                    ops.append((f"{tgt:g}", op))
                elif tgt == TARGETS_UM_H[0]:
                    ops.append(("max", op))   # the highest reachable rate, once
            for label, op in ops:
                p = op["pressure_Pa"]
                op["kn_plate"] = {f"{t:g} K": [plate_knudsen(op["feed_sccm"], plate, t, f) for f in (1.3, 1.0, 1 / 1.3)]
                                  for t in (300.0, 600.0)}
                op["plate_free_molecular"] = min(min(v) for v in op["kn_plate"].values()) >= KN_VALID
                # past the rate peak more feed lowers the rate, so the peak feed is the most any state can use
                feed_cap = op["feed_sccm"] if op.get("rate_peaks_below_feed_limit") else feed_max
                q_max = eta * N_ATOMS_PER_SCCM * feed_cap
                head = {"layout": name, "eta": eta, "S_eff_m3_s": speed, "target": label, "T0_C": t0,
                        "heater_limit": lname, "operating_point": op, "q_max_atoms_s": q_max}
                if op["rate_nm_min"] < 1000.0 * USEFUL_RATE_UM_H / 60.0:
                    rows.append({**head, "evaluated": False,
                                 "reason": f"reachable rate below {USEFUL_RATE_UM_H:g} um/h: decomposition comparable to growth"})
                    print(f"{name:2s} eta {eta:5.2f} S {speed:3.1f} {t0:.0f} C {lname}: at most "
                          f"{op['rate_nm_min'] * 0.06:5.2f} um/h, not evaluated", flush=True)
                    continue
                n_full = maps[:, None, :] * att_at(att_n, p)[None, None, :] * lip_n[None, :, :]       # (N, L, rho)
                ga = []
                for fill, d in g_labels:
                    att_g, lip_g = gamaps[(port, fill, opening)]
                    g = ga_base[(fill, d)][None, :] * att_at(att_g[d], p)[None, :] * lip_g
                    ga.append(g / g[:, :1])
                ga = np.array(ga)                                                                      # (G, L, rho)
                per_law = {}
                for law in laws:
                    res = evaluate(n_full, ga, t_maps, params, law, rho, op["rate_nm_min"], k_atoms, nominal_idx,
                                   s_max=q_max / k_atoms)
                    if not np.all(res["mean_net"] > 0.0):
                        raise SystemExit(f"layout_comparison: non-positive net growth in an evaluated row ({name}, {label})")
                    per_law[law] = res
                    keep[(name, eta, speed, label, t0, lname, law)] = (res["thickness"].astype(np.float32),
                                                                        res["margin"].astype(np.float32), g_labels)
                comb = {k: np.stack([per_law[l][k] for l in laws], -1)
                        for k in ("thickness", "std", "margin", "q", "supply_limited", "rate_fixed", "mean_net")}
                comb.update({"r0": {l: per_law[l]["r0"] for l in laws}, "ga_centre": {l: per_law[l]["ga_centre"] for l in laws},
                             "window_nominal": {l: per_law[l]["window_nominal"] for l in laws}})
                axes = {"Ga fill and diameter": 1, "heater perturbation": 2, "lip height": 3, "droplet law": 4}
                nom = nominal_idx + (laws.index("Ref14_growth"),)
                summ = summarize(comb, axes, nom, idx08)
                for pname in ("plate", "flange"):
                    for tol in TOLS_DEG:
                        idx = [0] + [i for i, s in enumerate(states) if s[0] == pname and s[1] == tol]
                        sl = (idx,) + nom[1:]
                        summ["one_factor"][f"pointing {pname} pivot +/-{tol} deg"] = {
                            "thickness_max_pct": float(comb["thickness"][sl].max()), "margin_min": float(comb["margin"][sl].min())}
                # window losses by heater state (capped states grow colder with the same Ga flux)
                summ["fraction_in_window_by_heater_state"] = {
                    hs: float(np.mean(comb["margin"][:, :, i] >= 0.0)) for i, hs in enumerate(HEATER_STATES)}
                summ["heater_capped_fraction"] = float(np.mean(hrep["state_capped"]))
                rows.append({**head, "evaluated": True, "heater": hrep, **summ})
                g8 = summ["grid_0.8deg"]
                print(f"{name:2s} eta {eta:5.2f} S {speed:3.1f} {label:>4s} {t0:.0f} C {lname}: feed {op['feed_sccm']:5.2f} sccm, "
                      f"p {p:7.1e} Pa, rate {op['rate_nm_min'] * 0.06:4.2f} um/h, "
                      f"Kn min {min(min(v) for v in op['kn_plate'].values()):5.1f}; thickness nominal "
                      f"{summ['nominal']['thickness_pct']:.2f} % (std {summ['nominal']['std_pct']:.2f} %), +/-0.8 deg max "
                      f"{g8['thickness_pct_max']:.2f} %, in window {100 * g8['fraction_in_window']:.0f} %, "
                      f"supply-limited {100 * g8['fraction_supply_limited']:.0f} %", flush=True)
        # operating-point surface: finer scan of the conversion fraction, nominal state, 740 C, 1473 K
        t_maps, _ = heat[(lay["heater"], 740.0, "1473 K element")]
        dec_mean = float(area_mean(params.decomposition(t_maps[0]), rho))
        for speed in speeds:
            feed_table_max = P_GRID[-1] * speed / (SCCM_PA_M3_S * t_gas / T_STD)   # feed at the table's top pressure
            for eta in np.geomspace(0.01, 1.0, 25):
                for tgt in TARGETS_UM_H:
                    op = operating_point(delivered, dec_mean, 1000.0 * tgt / 60.0, float(eta), speed, feed_max, t_gas, k_atoms)
                    op["kn_min"] = min(plate_knudsen(op["feed_sccm"], plate, t, 1.3) for t in (300.0, 600.0))
                    free = operating_point(delivered, dec_mean, 1000.0 * tgt / 60.0, float(eta), speed, feed_table_max, t_gas,
                                           k_atoms)
                    op["without_feed_limit"] = {"feed_sccm": free["feed_sccm"], "pressure_Pa": free["pressure_Pa"],
                                                "target_reached": free["target_reached"], "rate_nm_min": free["rate_nm_min"]}
                    op_table.append({"layout": name, "eta": float(eta), "S_eff_m3_s": speed, "target_um_h": tgt, **op})

    # ---- ranking in matched states, only where both layouts run at the same target rate ---------------
    ranking = []
    common_fills = set.intersection(*[set(env["ga_source"]["port_options_deg"][str(env["layouts"][n]["ga_port_deg"])]
                                          ["admissible_fills_mm"]) for n in names])
    for eta, speed, tgt, t0, lname in itertools.product(etas, speeds, TARGETS_UM_H, T0_C, LIMITS):
        label = f"{tgt:g}"
        if not all((name, eta, speed, label, t0, lname, laws[0]) in keep for name in names):
            continue
        vals = {}
        for name in names:
            th_l, mg_l = [], []
            for law in laws:
                th, mg, g_labels = keep[(name, eta, speed, label, t0, lname, law)]
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
        ranking.append({"eta": eta, "S_eff_m3_s": speed, "target_um_h": tgt, "T0_C": t0, "heater_limit": lname,
                        "pairwise": pairs, "matched_fills_mm": sorted(common_fills)})

    manifest = build_manifest(
        "layout_comparison", label="representative_chamber", validation_status="not_validated",
        inputs={"envelope": env, "layouts": names, "conversion_fractions": etas, "effective_speeds_m3_s": speeds,
                "feed_limit_sccm": feed_max, "plate": plate, "kn_valid": KN_VALID, "p_grid_Pa": P_GRID, "T0_C": T0_C,
                "heater_limits_K": LIMITS, "tilts_deg": TOLS_DEG, "tilt_directions_deg": TILT_DIRS_DEG,
                "lip_heights_m": LIP_H, "heater_states": HEATER_STATES, "ga_diameters": GA_D, "n_particles": N_PARTICLES,
                "n_seed": N_SEED, "usable_radius_m": usable, "target_nm_min": target, "atoms_per_m2_s_per_nm_min": k_atoms,
                "n_atoms_per_sccm": N_ATOMS_PER_SCCM, "ga_records_sha256": ga_used, "map_caches": caches,
                "thresholds_pct": THRESHOLDS_PCT, "targets_um_h": TARGETS_UM_H,
                "useful_rate_floor_um_h": USEFUL_RATE_UM_H},
        outputs={"rows": rows, "ranking": ranking, "operating_surface": op_table, "rho_m": rho},
        sources=SOURCES,
        warnings=["Representative-chamber comparison; no model in the chain is validated on the proposed machine",
                  "Uncertainty grid, not a probability distribution: shares are over grid states",
                  "Conversion fraction of the N2 feed to active N is a missing input, set by scenario",
                  "Background attenuation removes direct beam only; scattered arrival not modelled",
                  "Attenuation and lip shadow as nominal-pose ratio profiles; free-molecular N plates with uniform output",
                  "Heater perturbations are not combined with each other; N profile and plate geometry are not in the grid",
                  "No uniformity target or minimum growth rate is agreed: threshold shares are tradeoffs, not pass/fail"],
        disabled_physics=["transients", "morphology", "AlN", "scattered-beam redeposition", "Ga pointing error",
                          "transitional plate-hole flow"])
    print(f"Wrote {write_manifest(manifest, out / 'manifest.json')}")


if __name__ == "__main__":
    main()
