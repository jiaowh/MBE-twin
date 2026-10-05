"""Chamber definition of the representative chamber for the integrated twin, at the provisional operating point.

Assembles one layout's subsystem operators from the layout comparison (scripts/layout_comparison.py
and its keyed map caches in results/layout_comparison_bc) into the chamber-definition contract of
mbe_twin.chamber, and solves the operating point the twin's recipes refer to:

- Layout B-L by default (large high-conductance plate, the layout that reaches 1 um/h at a
  realistic conversion), nominal pose, 2 mm holder lip, Ga port 46 deg at 70 mm fill with the
  8 A collision diameter (the comparison's nominal state). Arrival tables include the scattered-
  arrival factors of the chosen variant (default gas+plume, the main variant since 2026-10-03).
- Supply scenario: eta 0.3, 4 m^3/s, 35 sccm feed limit (the scenario where B-L is admissible).
- Heater: the layout's option ("designed density": 12 equal rings, 99 mm opening), zone power
  fractions optimized at the operating temperature under the 1473 K element limit
  (heater_zones.optimize), as the comparison does.
- Operating point (720 C, 1 um/h; adopted 2026-10-02): the twin's own pyrometer spot holds 720 C
  through the feedforward table; the N feed is the per-state balance of layout_comparison.solve_states
  at that wafer map; the Ga cell is steered from the reading (operating_optimum's protocol): the
  centre Ga flux is the middle of the window the reading implies, converted to a cell temperature
  through the DSMC record's absolute flux and the Hertz-Knudsen scaling.

Calibration and truth are separate. The operating point (Ga cell temperature, N2 feed, pyrometer
setpoint) is always solved with the calibration state: the nominal pose and the 70 mm / 8 A Ga
record, as a commissioning calibration would fix it once. The arrival maps written into the
definition are those of the truth state (--truth-tilt / --truth-fill / --truth-d; nominal by
default). A run with a perturbed truth state therefore shows what the frozen settings grow when the
machine differs from its calibration, with controllers that observe only the pyrometer and the gauge
(audit 2026-10-05, finding 1). In the truth state the Ga reference is the truth record's own
absolute flux at its cell temperature, so a deeper fill at the frozen cell temperature delivers
the depleted flux.

Priors (no repository source; listed in the definition's "priors"): chamber volume, MFC time
constant, heater element and ledge heat capacities, pyrometer spot, noise and valid range, gauge
noise, thickness-map radii.

Usage: python scripts/twin_chamber.py [--layout B-L] [--eta 0.3] [--speed 4] [--feed-limit 35]
                                      [--scattered gas+plume] [--t-c 720] [--rate-um-h 1.0]
                                      [--droplet-law Heying_growth] [--out cases/twin/chamber_B-L_720C.json]
                                      [--truth-tilt PIVOT DEG DIR] [--truth-fill MM] [--truth-d 8|5.68]
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
from mbe_twin.chamber import Chamber, heater_definition  # noqa: E402
from mbe_twin.growth import load_parameters  # noqa: E402
from mbe_twin.manifest import canonical_hash, source_sha256  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lc = _load("layout_comparison", ROOT / "scripts/layout_comparison.py")
oo = _load("operating_optimum", ROOT / "scripts/operating_optimum.py")

PRIORS = {
    "vacuum.chamber_volume_m3": (0.5, "order of a 200 mm production chamber; only sets V/S (0.1 s at 4 m^3/s)"),
    "vacuum.mfc_time_constant_s": (2.0, "typical thermal MFC response"),
    "heater.areal_heat_capacity_J_m2K.heater": (3700.0, "1 mm pyrolytic-graphite-like element, 2200 kg/m^3 x 1700 J/kg/K"),
    "heater.areal_heat_capacity_J_m2K.ledge": (5700.0, "2 mm Mo ledge, 10220 kg/m^3 x 280 J/kg/K"),
    "sensors.pyrometer.spot_radius_m": (0.005, "10 mm spot at the wafer centre"),
    "sensors.pyrometer.noise_K": (0.2, "reading noise; the bias budget is +/-2 K (audit 2026-10-03)"),
    "sensors.pyrometer.valid_min_K": (873.0, "Si opaque enough at the pyrometer wavelength above about 600 C"),
    "sensors.ion_gauge.noise_rel": (0.01, "1 % reading noise"),
}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--layout", default="B-L")
    ap.add_argument("--eta", type=float, default=0.3)
    ap.add_argument("--speed", type=float, default=4.0)
    ap.add_argument("--feed-limit", type=float, default=35.0)
    ap.add_argument("--scattered", default="gas+plume", choices=lc.SCATTER_VARIANTS)
    ap.add_argument("--t-c", type=float, default=720.0)
    ap.add_argument("--rate-um-h", type=float, default=1.0)
    ap.add_argument("--droplet-law", default="Heying_growth")
    ap.add_argument("--out", default=None)
    ap.add_argument("--truth-tilt", nargs=3, metavar=("PIVOT", "DEG", "DIR"), default=None,
                    help="truth N pointing: pivot name of the envelope (e.g. flange), tilt 0.8 or 1.6 deg, direction 0-330 deg")
    ap.add_argument("--truth-fill", type=int, default=None, help="truth Ga fill (mm) among the port's admissible fills")
    ap.add_argument("--truth-d", default=None, choices=list(lc.GA_D), help="truth Ga collision diameter label")
    args = ap.parse_args()
    truth_tag = ""
    if args.truth_tilt:
        truth_tag += f"_tilt-{args.truth_tilt[0]}-{float(args.truth_tilt[1]):g}deg-dir{float(args.truth_tilt[2]):g}"
    if args.truth_fill:
        truth_tag += f"_fill{args.truth_fill}"
    if args.truth_d:
        truth_tag += f"_d{args.truth_d}"
    out = Path(args.out or f"cases/twin/chamber_{args.layout}_{args.t_c:g}C{truth_tag}.json")

    env = json.loads(lc.ENVELOPE.read_text(encoding="utf-8"))
    rec_path = lc.comparison_record(args.scattered)
    rec = json.loads(rec_path.read_text(encoding="utf-8"))
    usable = env["wafer_and_mask"]["usable_radius_m"]["value"]
    rho = np.linspace(0.0, usable, 39)
    scatter = lc.scatter_factors(args.scattered, rho)
    inp = oo.load_inputs(rec, env, args.layout, rho, scatter, args.speed)
    lip = lc.LIP_H.index(env["wafer_and_mask"]["holder_lip_height_m"]["value"])
    port = env["layouts"][args.layout]["ga_port_deg"]
    n_cal = inp["n_vac"][0, lip]                       # calibration (nominal pose): m^-2 per atom/s
    g_cal = inp["nominal_g"]
    att_n = inp["att_n"]
    # truth state: N pointing from the comparison's +/-0.8 / 1.6 deg ensemble, Ga fill and diameter
    n_true, truth = n_cal, {"n_pointing": "nominal"}
    if args.truth_tilt:
        lay_n = env["layouts"][args.layout]["n"]
        prefix = f"N_{lay_n['L_over_r']:g}_{lay_n['polar_deg']:g}_{lay_n['aim_offset_mm']:g}_"
        nf = next(c for c in rec["inputs"]["map_caches"] if c["file"].startswith(prefix))
        zn = np.load(oo.MAPS / nf["file"])
        if str(zn["cache_key"]) != nf["key"]:
            raise SystemExit("twin_chamber: N cache key mismatch")
        states = [tuple(x) for x in json.loads(str(zn["states"]))]
        want = (args.truth_tilt[0], float(args.truth_tilt[1]), float(args.truth_tilt[2]))
        if want not in states:
            raise SystemExit(f"twin_chamber: no N state {want}; available pivots "
                             f"{sorted({x[0] for x in states[1:]})}, tilts {lc.TOLS_DEG}, directions {lc.TILT_DIRS_DEG}")
        n_true = zn["maps"][states.index(want)] * zn["lip"][lip]
        truth["n_pointing"] = {"pivot": want[0], "tilt_deg": want[1], "direction_deg": want[2]}
    g_true = g_cal
    if args.truth_fill or args.truth_d:
        lab = (args.truth_fill or inp["labels"][g_cal][0], args.truth_d or inp["labels"][g_cal][1])
        if lab not in inp["labels"]:
            raise SystemExit(f"twin_chamber: no Ga state {lab}; available {inp['labels']}")
        g_true = inp["labels"].index(lab)
    truth["ga"] = {"fill_mm": inp["labels"][g_true][0], "diameter": inp["labels"][g_true][1]}

    def ga_reference(g_i):
        fill, dlab = inp["labels"][g_i]
        rec_name = lc.ga_record(port, fill, dlab)
        js = json.loads((lc.GA_RECORDS / rec_name).read_text(encoding="utf-8"))
        o = js["outputs"]
        coef = profile_fit.annulus_fit(np.asarray(o["dsmc_flux"]), lc.GA_EDGES, 0.100, 4, np.asarray(o["dsmc_flux_stderr"]))
        return {"cell_K": float(js["inputs"]["T_K"]),
                "centre_flux_m2_s": float(profile_fit.evaluate(coef, np.array([0.0]), 0.100)[0]), "record": rec_name}

    ga_ref_cal, ga_ref_true = ga_reference(g_cal), ga_reference(g_true)
    n_map, ga_shape, att_g = n_true, inp["g_vac"][g_true, lip], inp["att_g"][g_true]
    ga_shape_cal, att_g_cal = inp["g_vac"][g_cal, lip], inp["att_g"][g_cal]
    cell_ref = ga_ref_cal["cell_K"]

    # heater: the layout's option, zone fractions optimized at the operating temperature under the element limit
    option = env["layouts"][args.layout]["heater"]
    openings = env["wafer_and_mask"]["holder_opening_radius_m"]["value"]
    opening = openings["3 mm overlap"] if option == "3 zones" else openings["1 mm overlap"]
    edges = lc.hz.LAYOUTS["3 zones"] if option == "3 zones" else lc.hz.LAYOUTS["12 zones"]
    model = lc.hz.make(edges, {"ledge_inner": opening}, {})
    limit = lc.LIMITS["1473 K element"]
    t0_k = args.t_c + lc.C
    r_opt, frac = lc.hz.optimize(model, t0_k, limits={"t_heater_max": limit})
    g_kw, p_kw = heater_definition(model.geometry, model.props)

    gp = json.loads((ROOT / "data/parameters/gan_growth.json").read_text(encoding="utf-8"))
    k_atoms = gp["units"]["ml_per_s_per_nm_per_min"] * 1.14e19
    vac = env["vacuum"]
    t_gas = vac["gas_temperature_K"]["value"]
    pr = {k: v[0] for k, v in PRIORS.items()}
    definition = {
        "schema_version": "0.1", "label": "representative_chamber",
        "name": f"{args.layout}, eta {args.eta:g}, {args.speed:g} m^3/s, {args.scattered} arrival, {args.t_c:g} C",
        "rho_m": rho.tolist(), "p_grid_Pa": list(lc.P_GRID), "wafer_radius_m": 0.100,
        "ga": {"shape": ga_shape.tolist(), "att": np.asarray(att_g).tolist(),
               "reference": ga_ref_true},
        "n": {"map_per_atom_s": n_map.tolist(), "att": np.asarray(att_n).tolist(), "eta": args.eta,
              "kn_per_sccm": inp["kn_per_sccm"], "kn_valid": lc.KN_VALID},
        "vacuum": {"effective_speed_m3_s": args.speed, "gas_temperature_K": t_gas,
                   "chamber_volume_m3": pr["vacuum.chamber_volume_m3"],
                   "mfc_time_constant_s": pr["vacuum.mfc_time_constant_s"], "feed_limit_sccm": args.feed_limit},
        "heater": {"option": option, "geometry": g_kw, "properties": p_kw, "zone_fractions": frac.tolist(),
                   "areal_heat_capacity_J_m2K": {"heater": pr["heater.areal_heat_capacity_J_m2K.heater"],
                                                 "ledge": pr["heater.areal_heat_capacity_J_m2K.ledge"]},
                   "element_limit_K": limit, "optimized_at_K": t0_k,
                   "optimized_wafer_range_K": float(r_opt["wafer_range"])},
        "growth": {"droplet_law": args.droplet_law, "n_rich_decomposition": "vacuum", "atoms_per_m2_s_per_nm_min": k_atoms},
        "sensors": {"pyrometer": {"spot_radius_m": pr["sensors.pyrometer.spot_radius_m"], "bias_K": 0.0,
                                  "noise_K": pr["sensors.pyrometer.noise_K"],
                                  "valid_min_K": pr["sensors.pyrometer.valid_min_K"]},
                    "ion_gauge": {"sensitivity": 1.0, "noise_rel": pr["sensors.ion_gauge.noise_rel"]},
                    "regime_spot_radius_m": 0.01,
                    "thickness_map_radii_m": [float(x) for x in np.arange(0.0, usable + 1e-9, 0.005)] + [usable]},
        "priors": {k: {"value": v, "basis": b} for k, (v, b) in PRIORS.items()},
        "truth_state": truth,
        "calibration_state": {"n_pointing": "nominal", "ga": {"fill_mm": inp["labels"][g_cal][0],
                                                             "diameter": inp["labels"][g_cal][1]}},
    }

    # ---- operating point with the twin's own operators, on the calibration state ----
    cal_def = json.loads(json.dumps(definition))
    cal_def["n"]["map_per_atom_s"] = n_cal.tolist()
    cal_def["ga"].update({"shape": ga_shape_cal.tolist(), "att": np.asarray(att_g_cal).tolist(), "reference": ga_ref_cal})
    ch = Chamber(cal_def)
    n_map, ga_shape, att_g = n_cal, ga_shape_cal, att_g_cal
    spot = definition["sensors"]["pyrometer"]["spot_radius_m"]
    p_ff = ch.feedforward_power(t0_k)
    steady = ch.heater.solve(heater_power=ch.zone_power(p_ff))
    t_map = np.interp(rho, steady["r_wafer"], steady["t_wafer"])
    reading = ch.spot_mean(t_map, spot)
    params = load_parameters()
    target = 1000.0 * args.rate_um_h / 60.0
    dec_mean = np.array([lc.area_mean(params.decomposition(t_map), rho)])
    s, feed, p, limited, att = lc.solve_states(n_map[None, None, :], att_n, dec_mean, target, args.eta, args.speed,
                                               args.feed_limit, t_gas, k_atoms, None, rho)
    if limited.any():
        raise SystemExit(f"twin_chamber: {args.rate_um_h} um/h is supply-limited in this scenario")
    feed, p = float(feed[0, 0, 0]), float(p[0, 0, 0])
    jn = float(s[0, 0, 0]) * n_map * att[0, 0, 0]                                   # nm/min
    gshape = ga_shape * lc.att_at(att_g, p)
    gshape = gshape / gshape[0]
    fcrit = params.critical_excess(args.droplet_law, reading)
    lo = float(np.max(jn / (jn[0] * gshape)))
    hi = float(np.min((jn + fcrit) / (jn[0] * gshape)))
    mid = 0.5 * (lo + hi) if hi > lo else lo * 1.02
    ga_centre_arrival = mid * jn[0] * k_atoms                                        # m^-2 s^-1 at pressure p
    ga_centre_vac = ga_centre_arrival / (ga_shape[0] * lc.att_at(att_g, p)[0])
    cell_k = ch.ga_cell_for_centre_vacuum(ga_centre_vac)
    definition["operating_point"] = {
        "wafer_C": args.t_c, "ga_cell_K": cell_k, "n2_sccm": feed,
        "expected": {"pressure_Pa": p, "rate_target_um_h": args.rate_um_h, "spot_reading_K": reading,
                     "wafer_mean_K": float(lc.area_mean(t_map, rho)), "wafer_range_K": float(t_map.max() - t_map.min()),
                     "heater_power_W": p_ff, "window_ga_over_n_centre": [lo, hi], "ga_over_n_centre": mid,
                     "ga_cell_minus_reference_K": cell_k - cell_ref, "plate_kn": inp["kn_per_sccm"] / feed},
        "basis": "solved once on the calibration state (nominal pose, 70 mm / 8 A) and frozen: pyrometer spot held at "
                 "wafer_C; N feed from the per-state balance (layout_comparison.solve_states) for the wafer-mean net rate; "
                 "Ga centre flux mid-window from the reading (operating_optimum protocol). The definition's maps are the "
                 "truth state's; the twin's controllers observe only the pyrometer and the gauge."}
    definition["provenance"] = {
        "comparison_record": rec_path.relative_to(ROOT).as_posix(), "comparison_record_sha256": lc.file_sha256(rec_path),
        "map_caches": [c for c in rec["inputs"]["map_caches"]
                       if c["file"].startswith((f"N_{env['layouts'][args.layout]['n']['L_over_r']:g}_"
                                                f"{env['layouts'][args.layout]['n']['polar_deg']:g}_"
                                                f"{env['layouts'][args.layout]['n']['aim_offset_mm']:g}_", f"Ga_{port}_"))],
        "ga_records_sha256": {r_["record"]: lc.file_sha256(lc.GA_RECORDS / r_["record"]) for r_ in (ga_ref_cal, ga_ref_true)},
        "envelope_sha256": lc.file_sha256(lc.ENVELOPE),
        "scattered": args.scattered, "scatter_sources": {p_.relative_to(ROOT).as_posix(): lc.file_sha256(p_)
                                                        for p_ in lc.scatter_sources(scatter)},
        "source_sha256": source_sha256([Path(__file__), ROOT / "scripts/layout_comparison.py",
                                        ROOT / "scripts/operating_optimum.py", ROOT / "scripts/heater_zones.py",
                                        ROOT / "src/mbe_twin/chamber.py", ROOT / "src/mbe_twin/heater.py"]),
        "settings": vars(args)}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(definition, indent=1) + "\n", encoding="utf-8", newline="\n")
    op = definition["operating_point"]
    print(f"{out}: sha256 {canonical_hash(definition)[:12]}; truth {truth}")
    print(f"operating point: {args.t_c:g} C spot, feed {feed:.2f} sccm, p {p:.3g} Pa, Ga cell {cell_k:.1f} K "
          f"(reference {cell_ref:.1f} K), Ga/N centre {mid:.3f} in [{lo:.3f}, {hi:.3f}], heater {p_ff:.0f} W, "
          f"wafer range {op['expected']['wafer_range_K']:.2f} K, plate Kn {op['expected']['plate_kn']:.1f}")


if __name__ == "__main__":
    main()
