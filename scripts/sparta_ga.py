"""Collisional (DSMC) Ga source on the 200 mm representative chamber: fill level and rate.

Geometry (representative, REFERENCE_CHAMBER.md): R14's cylindrical crucible (71.5 mm bore),
orifice 350 mm from the wafer centre, axis aimed at the centre, 46 deg from the wafer normal,
level (horizontal) melt. A level melt needs a recess >= R tan 46 deg = 37.0 mm; admissible
fills 40-120 mm are studied. Wafer: 200 mm, uniform rotation.

State: Ga at its saturation pressure (Alcock 1984, R15) at the melt temperature T, emitted
from the melt by Hertz-Knudsen (evaporation coefficient 1). Two ways of setting T:
- "hold": T chosen per fill so that the free-molecular model gives the wafer-centre Ga flux
  of the target GaN growth rate (flux ratio Ga/N = 1). This mimics an operator raising the
  cell temperature as the charge is consumed; the DSMC centre flux then shows how far
  collisions move the delivered rate from that estimate.
- "fixed": T held at the value for a reference fill (40 mm), so the rate drops as the melt
  recedes.
Collisions: hard-sphere Ga with diameter d. No Ga collision diameter is sourced, so d is
bracketed: 2.5 A (sigma/5 of R07's Knudsen statement, a deliberately small atom), 5.68 A
(R07's Knudsen statement for Bi) and 8 A (the value calibrated on R07's Bi rate series,
whose vapour contains Bi2). d = none runs are collisionless code-to-code checks against
crucible.py on the same wafer.

Numerics: fine cells <= lambda_sat / 2 and <= D / 16 in and one D above the bore; sampling
slab 3.0-3.5 D above the orifice (the nearest wafer edge is 3.9 D away along the axis), so
collisions beyond 3.5 D are neglected (R07 benchmark: moving the slab from 3 D to 4.5 D
changed the profile by about 0.015). Uncertainty: batch means over time blocks.

Usage: python scripts/sparta_ga.py --fill 0.07 --diameter 5.68e-10 [--rate 1.0] [--mode hold]
                                   [--out DIR] [--record NAME] [--set key=value ...]
       python scripts/sparta_ga.py --reuse DIR [--record NAME]
"""

import argparse
import json
from pathlib import Path

import numpy as np

from mbe_twin.beam import Wafer, crucible_source_on_cone, level_melt_normal, rotation_averaged_flux
from mbe_twin.crucible import Crucible, simulate
from mbe_twin.manifest import build_manifest, source_sha256, write_manifest
from mbe_twin.sparta import (batch_means, expected_dump_steps, load_run_config, log_stats,
                             prepare_run_dir, read_dumps, run_case, sparta_commit)
from mbe_twin.sparta_source import SourceRun, crucible_surface, wafer_profile
from mbe_twin.sparta import MELT
from mbe_twin.units import kelvin_to_celsius
from mbe_twin.vapour import atomic_mass_kg, evaporation_flux, vapour_pressure

ROOT = Path(__file__).resolve().parents[1]
RECORD_DIR = ROOT / "data/runs/sparta_ga"
BORE_RADIUS = 0.03575
THROW = 0.350
POLAR_DEG = 46.0
WAFER_RADIUS = 0.100
REFERENCE_FILL = 0.040
GA_MASS = atomic_mass_kg("Ga")
# Ga atoms per m^3 of GaN (wurtzite a 318.9 pm, c 518.6 pm; see scripts/crucible_knudsen.py)
N_GA_GAN = 2.0 / (np.sqrt(3.0) / 2.0 * 318.9e-12 ** 2 * 518.6e-12)
UM_PER_H = 1e-6 / 3600.0
EDGES = np.linspace(0.0, WAFER_RADIUS, 21)
MID = 0.5 * (EDGES[1:] + EDGES[:-1])
AREA = np.pi * np.diff(EDGES ** 2)
SOURCES = [Path(__file__), ROOT / "src/mbe_twin/sparta_source.py", ROOT / "src/mbe_twin/sparta.py",
           ROOT / "src/mbe_twin/crucible.py", ROOT / "src/mbe_twin/beam.py", ROOT / "src/mbe_twin/vapour.py"]
# Particles and sampling length set for about 0.3 % standard error on range/mean (a 2e5 /
# 16000-step trial gave several tenths of a percent on single bins at the wafer).
NUMERICS = {"coarse": 3, "particles": 6e5, "dt_factor": 0.3, "steps_eq": 8000,
            "steps_sample": 24000, "dump_every": 20, "slab_D": [3.0, 3.5], "seed": 12345,
            "cells_per_bore": 16.0}


def placement():
    wafer = Wafer(radius=WAFER_RADIUS)
    src = crucible_source_on_cone("Ga", wafer, None, throw=THROW, polar_angle=np.radians(POLAR_DEG),
                                  azimuth=0.0, emission_rate=1.0)
    return wafer, src


def crucible_for(fill):
    wafer, src = placement()
    return Crucible(BORE_RADIUS, fill, melt_normal=level_melt_normal(src.axis, up=tuple(-np.asarray(wafer.normal))))


def melt_area(crucible):
    mesh = crucible_surface(crucible, 2.0 * crucible.lip_radius, n_segments=512)
    return float(mesh.areas()[mesh.types == MELT].sum())


def fm_events(fill, particles=200_000, seed=7):
    return simulate(crucible_for(fill), particles, rng=seed)


def centre_flux_per_melt_particle(events):
    wafer, src = placement()
    s = crucible_source_on_cone("Ga", wafer, events, throw=THROW, polar_angle=np.radians(POLAR_DEG),
                                azimuth=0.0, emission_rate=1.0)
    return float(s.flux([wafer.center], wafer.normal)[0])


def hold_temperature(fill, rate_um_h, events):
    """Melt temperature giving the target wafer-centre Ga flux in the free-molecular model."""
    target = rate_um_h * UM_PER_H * N_GA_GAN
    g = centre_flux_per_melt_particle(events)
    area = melt_area(crucible_for(fill))
    lo, hi = 900.0, 1590.0
    for _ in range(80):
        t = 0.5 * (lo + hi)
        lo, hi = (t, hi) if g * area * evaporation_flux(vapour_pressure("Ga", t), t, GA_MASS) < target else (lo, t)
    return 0.5 * (lo + hi)


def build_run(cfg):
    c = crucible_for(cfg["fill_m"])
    d = cfg["diameter_m"]
    t = cfg["T_K"]
    p = float(vapour_pressure("Ga", t))
    probe = SourceRun(c, "Ga", GA_MASS, t, p, d, 1.0)
    cell = min(2.0 * BORE_RADIUS / cfg["cells_per_bore"], 0.5 * probe.lambda_sat)
    return SourceRun(c, "Ga", GA_MASS, t, p, d, cell, coarse=cfg["coarse"], particles=cfg["particles"],
                     dt_factor=cfg["dt_factor"], steps_eq=cfg["steps_eq"], steps_sample=cfg["steps_sample"],
                     dump_every=cfg["dump_every"], slab_D=tuple(cfg["slab_D"]), seed=cfg["seed"],
                     half_angle_deg=25.0)


def smooth_metrics(profile, stderr=None):
    """Range/mean and std (%) of an even-polynomial fit a + b r^2 + c r^4 to a binned profile.

    Max-minus-min of noisy bins is biased upward; the fit gives a noise-robust estimate.
    """
    x = (MID / WAFER_RADIUS) ** 2
    A = np.stack([np.ones_like(x), x, x * x], 1)
    w = np.ones_like(x) if stderr is None else 1.0 / np.maximum(stderr, 1e-12 * np.abs(profile).max())
    coef = np.linalg.lstsq(A * w[:, None], profile * w, rcond=None)[0]
    r = np.linspace(0.0, WAFER_RADIUS, 401)
    f = coef[0] + coef[1] * (r / WAFER_RADIUS) ** 2 + coef[2] * (r / WAFER_RADIUS) ** 4
    ring = np.pi * np.diff(np.concatenate(([0.0], 0.5 * (r[1:] + r[:-1]), [WAFER_RADIUS])) ** 2)
    mean = np.sum(ring * f) / ring.sum()
    std = np.sqrt(np.sum(ring * (f - mean) ** 2) / ring.sum())
    return {"range_over_mean_pct": 100 * (f.max() - f.min()) / mean, "std_pct": 100 * std / mean,
            "centre_to_edge": f[-1] / f[0], "mean": mean, "fit": coef.tolist()}


def fm_reference(cfg, run):
    """crucible.py prediction on the same wafer, absolute (atoms m^-2 s^-1)."""
    ev = fm_events(cfg["fill_m"], 150_000, seed=21)
    wafer, _ = placement()
    src = crucible_source_on_cone("Ga", wafer, ev, throw=THROW, polar_angle=np.radians(POLAR_DEG),
                                  azimuth=0.0,
                                  emission_rate=melt_area(run.crucible) * evaporation_flux(run.pressure_pa, run.temperature_k, GA_MASS))
    r = np.linspace(0.0, WAFER_RADIUS, 201)
    f = rotation_averaged_flux([src], wafer, r, n_angles=72)
    rm = 0.5 * (r[1:] + r[:-1])
    fm = 0.5 * (f[1:] + f[:-1])
    return np.array([np.sum((fm * rm)[(rm >= a) & (rm < b)]) / np.sum(rm[(rm >= a) & (rm < b)])
                     for a, b in zip(EDGES[:-1], EDGES[1:])]), ev.transmission


def postprocess(work, cfg, n_blocks):
    run = build_run(cfg)
    steps = expected_dump_steps(run.steps_eq, run.steps_sample, run.dump_every)
    pos, vel, snap = read_dumps(work, steps)
    wafer, src = placement()

    def flux_of(mask, n):
        return wafer_profile(pos[mask], vel[mask], run.slab, src, wafer, EDGES)[0] * run.fnum / n

    n_snap = len(steps)
    flux = flux_of(np.ones(len(pos), bool), n_snap)
    bounds = np.linspace(0, n_snap, n_blocks + 1).astype(int)
    blocks = [flux_of((snap >= a) & (snap < b), b - a) for a, b in zip(bounds[:-1], bounds[1:])]
    _, flux_se = batch_means(blocks)
    metrics = smooth_metrics(flux, flux_se)
    block_m = [smooth_metrics(b, flux_se * np.sqrt(n_blocks)) for b in blocks]
    unc = {k: float(batch_means([m[k] for m in block_m])[1]) for k in ("range_over_mean_pct", "std_pct", "mean")}
    half = n_snap // 2
    halves = [smooth_metrics(flux_of(snap < half, half), flux_se * np.sqrt(2)),
              smooth_metrics(flux_of(snap >= half, n_snap - half), flux_se * np.sqrt(2))]
    stats = log_stats((work / "log.sparta").read_text(encoding="utf-8", errors="replace"))
    npart = np.array([r["Np"] for r in stats if r["Step"] >= run.steps_eq])
    return run, flux, flux_se, metrics, unc, halves, npart


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fill", type=float, help="melt recess on the axis (m)")
    ap.add_argument("--diameter", default=None, help="hard-sphere diameter (m) or 'none'")
    ap.add_argument("--rate", type=float, default=1.0, help="target GaN growth rate (um/h)")
    ap.add_argument("--mode", choices=("hold", "fixed"), default="hold")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE")
    ap.add_argument("--out", default=None)
    ap.add_argument("--reuse", default=None, metavar="DIR")
    ap.add_argument("--blocks", type=int, default=8)
    ap.add_argument("--record", default=None, metavar="NAME")
    args = ap.parse_args()

    if args.reuse:
        work = Path(args.reuse)
        cfg = load_run_config(work)
    else:
        if args.fill is None or args.diameter is None:
            ap.error("give --fill and --diameter (or --reuse DIR)")
        cfg = {"fill_m": args.fill, "rate_um_h": args.rate, "mode": args.mode,
               "diameter_m": None if args.diameter == "none" else float(args.diameter), **NUMERICS}
        for item in args.set:
            key, _, value = item.partition("=")
            if key not in NUMERICS:
                ap.error(f"--set: unknown key {key!r}")
            cfg[key] = json.loads(value) if key == "slab_D" else type(NUMERICS[key])(float(value))
        ref_fill = cfg["fill_m"] if args.mode == "hold" else REFERENCE_FILL
        cfg["T_K"] = hold_temperature(ref_fill, args.rate, fm_events(ref_fill))
        cfg["T_reference_fill_m"] = ref_fill
        run = build_run(cfg)
        cfg["derived"] = run.config()
        cfg["sparta_commit"] = sparta_commit()
        # the code that writes the inputs; the manifest hashes the post-processing code
        cfg["source_sha256_at_start"] = source_sha256(SOURCES)
        d = "fm" if cfg["diameter_m"] is None else f"d{cfg['diameter_m'] * 1e10:.2f}"
        work = Path(args.out or ROOT / "results/sparta_ga" /
                    f"fill{1e3 * args.fill:.0f}_{d}_{args.rate:g}umh_{args.mode}")
        prepare_run_dir(work, cfg)
        run.write_inputs(work)
        run_case(work)

    run, flux, flux_se, m, unc, halves, npart = postprocess(work, cfg, args.blocks)
    fm, transmission_fm = fm_reference(cfg, run)
    m_fm = smooth_metrics(fm)
    target = cfg["rate_um_h"] * UM_PER_H * N_GA_GAN
    centre = float(np.sum((flux * AREA)[:2]) / AREA[:2].sum())  # inside 10 mm
    centre_fm = float(np.sum((fm * AREA)[:2]) / AREA[:2].sum())
    print(f"{work.name}: T = {kelvin_to_celsius(run.temperature_k):.1f} C, p = {run.pressure_pa:.3g} Pa, "
          f"lambda_sat/D = {run.lambda_sat / run.bore:.3g}, cell {1e3 * run.cell_m:.2f} mm")
    print(f"  centre Ga flux / target ({cfg['rate_um_h']:g} um/h GaN): DSMC {centre / target:.3f}, "
          f"free-molecular {centre_fm / target:.3f}")
    print(f"  200 mm range/mean: DSMC {m['range_over_mean_pct']:.2f} +/- {unc['range_over_mean_pct']:.2f} %, "
          f"free-molecular {m_fm['range_over_mean_pct']:.2f} %; std {m['std_pct']:.2f} vs {m_fm['std_pct']:.2f} %")
    print(f"  centre-to-edge: DSMC {m['centre_to_edge']:.4f}, free-molecular {m_fm['centre_to_edge']:.4f}")
    print(f"  steady state: halves range/mean {halves[0]['range_over_mean_pct']:.2f} / "
          f"{halves[1]['range_over_mean_pct']:.2f} %; Np range {100 * np.ptp(npart) / npart.mean():.2f} %")
    print("  r mm    " + " ".join(f"{v:6.0f}" for v in 1e3 * MID[::2]))
    print("  DSMC    " + " ".join(f"{v:6.3f}" for v in (flux / m['mean'])[::2]))
    print("  +/-     " + " ".join(f"{v:6.3f}" for v in (flux_se / m['mean'])[::2]))
    print("  FM      " + " ".join(f"{v:6.3f}" for v in (fm / m_fm['mean'])[::2]))
    summary = {
        "config": cfg, "r_mm": 1e3 * MID, "dsmc_flux": flux, "dsmc_flux_stderr": flux_se,
        "free_molecular_flux": fm, "target_centre_flux": target,
        "centre_flux_over_target": {"dsmc": centre / target, "free_molecular": centre_fm / target},
        "metrics_dsmc": m, "metrics_dsmc_stderr": unc, "metrics_free_molecular": m_fm,
        "transmission_free_molecular": transmission_fm,
        "steady_state": {"halves_range_over_mean_pct": [h["range_over_mean_pct"] for h in halves],
                         "np_rel_range": float(np.ptp(npart) / npart.mean())},
    }
    manifest = build_manifest(
        f"sparta_ga_{work.name}", label="representative_chamber", validation_status="not_validated",
        inputs=cfg, outputs=summary, sources=SOURCES,
        solver={"name": "SPARTA", "build": "serial (WSL)", "commit": cfg.get("sparta_commit")},
        warnings=["Ga collision diameter not sourced: bracketed 2.5-8 A",
                  "Melt temperature set by a free-molecular mass balance (hold mode)",
                  "Collisions beyond the sampling slab (3.5 D) neglected",
                  "Representative geometry (R14 bore, 350 mm, 46 deg), not the proposed machine"],
        disabled_physics=["Ga2 and other dimers", "wall sticking/condensation (hot lip assumed)",
                          "desorption/re-evaporation at the wafer", "chamber background gas"])
    print(f"Wrote {write_manifest(manifest, work / 'summary.json')}")
    if args.record:
        print(f"Recorded {write_manifest(manifest, RECORD_DIR / f'{args.record}.json')}")


if __name__ == "__main__":
    main()
