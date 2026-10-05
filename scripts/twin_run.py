"""Run the integrated twin: one chamber definition and one recipe to a run bundle and a study record.

The bundle (results/twin/<run id>/) holds the manifest, the time series (timeseries.npz, every
sample_s), the final radial maps and the event log; the study record
(data/runs/studies/twin_<run id>.json) holds the manifest with the summary, conservation residuals,
warnings, disabled couplings and timings, without the time series. Wall-clock time is reported
against the PHASE1 laptop performance gate (accelerated mode within 60 minutes for a 60-minute recipe).

Usage: python scripts/twin_run.py [--chamber cases/twin/chamber_B-L_720C.json] [--recipe cases/twin/gan_1um_720C.json]
                                  [--dt 1.0] [--sample 10] [--seed 0] [--pyrometer-bias 0] [--run-id NAME]
                                  [--no-record]
"""

import argparse
import json
import os
import time
from pathlib import Path

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402

from mbe_twin.chamber import Chamber, load_definition  # noqa: E402
from mbe_twin.manifest import build_manifest, canonical_hash, write_manifest  # noqa: E402
from mbe_twin.twin import DISABLED_COUPLINGS, Twin  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [Path(__file__)] + [ROOT / f"src/mbe_twin/{m}.py" for m in
                              ("twin", "chamber", "recipe", "surface", "sensors", "thermal_transient", "heater",
                               "growth", "vacuum", "vapour", "radiation", "manifest")]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--chamber", default="cases/twin/chamber_B-L_720C.json")
    ap.add_argument("--recipe", default="cases/twin/gan_1um_720C.json")
    ap.add_argument("--dt", type=float, default=1.0, help="largest sub-step (s)")
    ap.add_argument("--sample", type=float, default=10.0, help="time-series interval (s)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--pyrometer-bias", type=float, default=None, help="override the pyrometer bias (K)")
    ap.add_argument("--run-id", default=None)
    ap.add_argument("--no-record", action="store_true", help="write the bundle only, not the study record")
    args = ap.parse_args()

    definition = load_definition(args.chamber)
    if args.pyrometer_bias is not None:
        definition["sensors"]["pyrometer"]["bias_K"] = args.pyrometer_bias
    chamber = Chamber(definition)
    recipe = json.loads(Path(args.recipe).read_text(encoding="utf-8"))
    run_id = args.run_id or f"{recipe['name']}_{Path(args.chamber).stem.removeprefix('chamber_')}"
    if args.pyrometer_bias:
        run_id += f"_bias{args.pyrometer_bias:+g}K"
    out = ROOT / "results/twin" / run_id
    out.mkdir(parents=True, exist_ok=True)

    t_build = time.perf_counter()
    twin = Twin(chamber, recipe, dt_max=args.dt, sample_s=args.sample, seed=args.seed)
    ff = chamber.feedforward_table()
    t_build = time.perf_counter() - t_build
    twin.run()
    summary, maps = twin.results()
    ts = twin.timeseries()
    np.savez_compressed(out / "timeseries.npz", **ts)
    (out / "maps.json").write_text(json.dumps(maps, indent=1) + "\n", encoding="utf-8", newline="\n")
    (out / "events.json").write_text(json.dumps(twin.events, indent=1) + "\n", encoding="utf-8", newline="\n")

    # growth-step figures: steady rate and window over the last half of the growth step
    growth = [s for s in twin.steps if s.shutters["ga"] and s.shutters["n"] and s.plasma]
    per_step = []
    for s in growth:
        sel = (ts["step"] == s.index)
        half = sel & (ts["t_s"] >= ts["t_s"][sel].min() + 0.5 * s.duration_s)
        per_step.append({"step": s.index, "name": s.name, "duration_s": s.duration_s,
                         "rate_mean_um_h": float(np.mean(ts["growth_rate_mean_nm_min"][half]) * 0.06),
                         "window_fraction_min": float(np.min(ts["window_fraction"][half])),
                         "pyrometer_K": [float(np.nanmin(ts["pyrometer_K"][half])), float(np.nanmax(ts["pyrometer_K"][half]))],
                         "wafer_mean_K": [float(ts["wafer_mean_K"][half].min()), float(ts["wafer_mean_K"][half].max())],
                         "pressure_Pa": float(np.mean(ts["pressure_Pa"][half])),
                         "regime_centre": sorted(set(ts["regime_centre"][half].tolist()))})
    gains = {f"{k:.2f}": v[2] | {"kp_W_per_K": v[0], "ki_W_per_K_s": v[1]} for k, v in twin._gains.items()}
    outputs = {
        "summary": summary, "growth_steps": per_step, "events": twin.events, "final_maps": maps,
        "controller": {"pi": gains, "power_limit_W": ff["p_limit_W"],
                       "power_clamped_samples": int(np.sum(ts["power_clamped"]))},
        "expected_operating_point": definition.get("operating_point", {}).get("expected"),
        "performance": {"recipe_s": summary["t_end_s"], "build_s": t_build, "run_wall_s": summary["wall_s"],
                        "gate": "accelerated completion within 60 min for a 60-minute recipe (PHASE1 section 4)",
                        "sub_steps": int(sum(twin.n_sub(s) for s in twin.steps))},
        "bundle": out.relative_to(ROOT).as_posix(),
        # one sample per minute of the main channels, so figures can be drawn from the record alone
        "trace_60s": {k: [None if (isinstance(v, float) and np.isnan(v)) else v for v in ts[k][::max(1, round(60.0 / args.sample))].tolist()]
                      for k in ("t_s", "step", "pyrometer_K", "wafer_mean_K", "element_max_K", "power_W", "ga_cell_K",
                                "pressure_Pa", "shutter_ga", "shutter_n", "plasma", "thickness_mean_nm", "window_fraction")},
    }
    inputs = {"chamber": Path(args.chamber).as_posix(), "chamber_sha256": chamber.sha256(), "recipe": recipe,
              "recipe_sha256": canonical_hash(recipe), "dt_max_s": args.dt, "sample_s": args.sample, "seed": args.seed,
              "pyrometer_bias_K": definition["sensors"]["pyrometer"].get("bias_K", 0.0),
              "chamber_priors": definition.get("priors"), "chamber_provenance": definition.get("provenance")}
    man = build_manifest(f"twin_{run_id}", label=chamber.label, inputs=inputs, outputs=outputs,
                         warnings=twin.warnings, disabled_physics=DISABLED_COUPLINGS, sources=SOURCES)
    write_manifest(man, out / "manifest.json")
    if not args.no_record:
        write_manifest(man, ROOT / f"data/runs/studies/twin_{run_id}.json")
    c = summary["conservation"]
    print(f"{run_id}: {summary['t_end_s']:.0f} s recipe in {summary['wall_s']:.1f} s wall (+{t_build:.1f} s set-up)")
    print(f"thickness {summary['thickness_mean_nm']:.1f} nm, half-range {summary['thickness_half_range_pct']:.3f} %, "
          f"droplets left max {summary['droplets_max_nm']:.3g} nm")
    for g in per_step:
        print(f"  {g['name']}: {g['rate_mean_um_h']:.4f} um/h, window >= {g['window_fraction_min']:.3f} of area, "
              f"pyrometer {g['pyrometer_K'][0]:.2f}-{g['pyrometer_K'][1]:.2f} K, p {g['pressure_Pa']:.3g} Pa, "
              f"centre {g['regime_centre']}")
    print(f"conservation: Ga {c['ga_max_abs_rel']:.1e}, N {c['n_max_abs_rel']:.1e}, solid {c['solid_max_abs_rel']:.1e}, "
          f"heater energy {c['heater_energy_rel']:.1e}")
    print(f"{len(twin.warnings)} warnings; bundle {out}")


if __name__ == "__main__":
    main()
