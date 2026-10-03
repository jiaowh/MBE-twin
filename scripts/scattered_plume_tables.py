"""Scattered-arrival factors with the nitrogen plate's plume, per pumping speed (extends scripts/scattered_tables.py).

The chamber gas depends on the pressure p alone; the plume in front of the nitrogen plate depends
on the feed Q = p S / (k T) itself (scripts/scattered_redeposition.py: at B-p's Kn 3 point it adds
3-6 % N attenuation and 0.4-0.6 points of shape change). This script tabulates the N factor
G(p, r) = (direct + scattered arrival with chamber gas and plume) / (deterministic direct arrival
attenuated by the chamber gas the comparison's way), as scripts/scattered_tables.py does without
the plume, on the comparison's pressure grid, for each effective pumping speed S:
- S = 2 and 4 m^3/s (the scenarios that can reach 1 um/h), at every grid pressure up to and including
  the first one whose feed reaches 35 sccm (the highest feed limit), so that every pressure a feed of
  at most 35 sccm produces lies between two plume-covered grid points; beyond that the gas-only
  factor is used and the coverage is recorded;
- the plume: the feed leaves the layout's active disk uniformly, cos^n as the N atoms (hole
  peaking), N2 at 300 K (the larger effect of the 300 / 600 K bracket of
  scattered_redeposition.py), unmodified by its own collisions;
- walls recombine N with gamma = 1.
The comparison (layout_comparison.py --scattered gas+plume) uses these factors for S = 2 and 4 and
the gas-only factors for S = 0.5 (flagged).

Usage: python scripts/scattered_plume_tables.py [--layouts B B-p B-L] [--speeds 2 4] [--n-particles 8000000]
                                                [--batches 8] [--extend RECORD] [--out results/scattered_plume_tables]
--extend RECORD keeps that record's covered entries (same layouts, speeds and settings) and computes
only the grid points the coverage rule adds (2026-10-03 audit: the first records stopped below 35 sccm).
"""

import argparse
import importlib.util
import json
import os
import time
from pathlib import Path

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402

from mbe_twin.manifest import build_manifest, write_manifest  # noqa: E402
from mbe_twin.scattering import (K_B, Gas, Plume, Source, binned_direct_flux, fit_even, radial_arrival, track,  # noqa: E402
                                 tube_cos_n)
from mbe_twin.vacuum import SCCM_PA_M3_S, T_STD, beam_mean_free_path  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ENVELOPE = ROOT / "data/design/design_envelope.json"
_spec = importlib.util.spec_from_file_location("scattered_tables", ROOT / "scripts/scattered_tables.py")
st = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(st)
lc = st.lc
FEED_MAX_SCCM = 35.0
PLUME_T = 300.0


def factor(rng, source, plume, d_beam, p, t_gas, n_total, batches, edges, centres, rho):
    n_part = n_total // batches
    sp = st.SPECIES["N"]
    lam = beam_mean_free_path(p, d_beam, sp["mass_amu"], sp["temperature"], t_gas=t_gas)
    a = binned_direct_flux(source, edges, lam)
    gas = Gas(p / (K_B * t_gas), t_gas)
    g_b, counts = [], []
    for _ in range(batches):
        r, ind, c = track(rng, n_part, source, diameter=d_beam, gas=gas, plume=plume, chamber=st.CHAMBER, gamma=1.0, **sp)
        d, s = radial_arrival(r, ind, n_part, edges)
        g_b.append((d + s) / a)
        counts.append(c["plume"] / n_part)
    g_b = np.array(g_b)
    g = g_b.mean(0)
    err = g_b.std(0, ddof=1) / np.sqrt(batches)
    fit = fit_even(centres, g, err, rho)
    chi2 = float(np.sum(((g - fit_even(centres, g, err, centres)) / err) ** 2) / (st.N_BINS - 3))

    def hr(f):
        return 100 * (f.max() - f.min()) / (2 * f.mean())
    hr_b = [hr(fit_even(centres, b, err, rho)) for b in g_b]
    return fit, {"bins": g.tolist(), "bins_err": err.tolist(), "reduced_chi2": chi2, "half_range_points": float(hr(fit)),
                 "half_range_points_err": float(np.std(hr_b, ddof=1) / np.sqrt(batches)),
                 "plume_collisions_per_emitted_atom": float(np.mean(counts))}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--layouts", nargs="+", default=["B", "B-p", "B-L"])
    ap.add_argument("--speeds", nargs="+", type=float, default=[2.0, 4.0])
    ap.add_argument("--n-particles", type=int, default=8_000_000)
    ap.add_argument("--batches", type=int, default=8)
    ap.add_argument("--seed", type=int, default=20261004)
    ap.add_argument("--extend", help="earlier record whose covered entries are kept")
    ap.add_argument("--out", default="results/scattered_plume_tables")
    args = ap.parse_args()
    old = None
    if args.extend:
        old = json.loads(Path(args.extend).read_text(encoding="utf-8"))
        oi = old["inputs"]
        for key, val in (("n_particles", args.n_particles), ("batches", args.batches), ("plume_temperature_K", PLUME_T)):
            if oi[key] != val:
                raise SystemExit(f"scattered_plume_tables: --extend record has {key} {oi[key]}, not {val}")
        if not set(args.layouts) <= set(oi["layouts"]) or not set(args.speeds) <= set(oi["speeds_m3_s"]):
            raise SystemExit("scattered_plume_tables: --extend record lacks a requested layout or speed")
    env = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    usable = env["wafer_and_mask"]["usable_radius_m"]["value"]
    rho = np.linspace(0.0, usable, 39)
    edges = usable * np.sqrt(np.arange(st.N_BINS + 1) / st.N_BINS)
    centres = np.sqrt((edges[:-1] ** 2 + edges[1:] ** 2) / 2)
    throw = env["chamber"]["source_throw_m"]["value"]
    vac = env["vacuum"]
    t_gas = vac["gas_temperature_K"]["value"]
    to_p = SCCM_PA_M3_S * (t_gas / T_STD)
    rng = np.random.default_rng(args.seed)
    tables, diag = {}, {}
    for name in args.layouts:
        n = env["layouts"][name]["n"]
        n_cos = tube_cos_n(n["L_over_r"])
        radius = n.get("plate_radius_m", 0.020)
        src, axis = st.geometry(n["polar_deg"], n["aim_offset_mm"] / 1e3, throw)
        source = Source(tuple(src), tuple(axis), n_cos, radius=radius)
        tables[name], diag[name] = {}, {}
        for speed in args.speeds:
            tab, dg, covered = [np.ones(len(rho))], [None], [True]
            prev_feed = 0.0
            for i, p in enumerate(lc.P_GRID[1:], start=1):
                feed = p * speed / to_p
                below, prev_feed = prev_feed, feed
                if below >= FEED_MAX_SCCM * (1 - 1e-9):   # the previous grid point already reached the feed limit
                    tab.append(None)
                    dg.append(None)
                    covered.append(False)
                    continue
                if old is not None and old["outputs"]["factors"][name][f"{speed:g}"]["covered"][i]:
                    tab.append(np.asarray(old["outputs"]["factors"][name][f"{speed:g}"]["factors"][i]))
                    dg.append({**old["outputs"]["diagnostics"][name][f"{speed:g}"][i], "from_record": old["run_id"]})
                    covered.append(True)
                    continue
                molecules = p * speed / (K_B * t_gas)
                plume = Plume(tuple(src), tuple(axis / np.linalg.norm(axis)), radius, molecules / (np.pi * radius ** 2),
                              temperature=PLUME_T, n_cos=n_cos)
                t = time.time()
                f, info = factor(rng, source, plume, vac["collision_diameters_m"]["N"], p, t_gas, args.n_particles,
                                 args.batches, edges, centres, rho)
                tab.append(f)
                dg.append({**info, "feed_sccm": feed})
                covered.append(True)
                print(f"N {name} S {speed:g} p {p:.2e} Pa ({feed:.1f} sccm): G centre/edge {f[0]:.4f}/{f[-1]:.4f}, half-range "
                      f"{info['half_range_points']:.2f} +/- {info['half_range_points_err']:.2f}, chi2 {info['reduced_chi2']:.2f}, "
                      f"plume collisions {info['plume_collisions_per_emitted_atom']:.3f} ({time.time() - t:.0f} s)", flush=True)
            tables[name][f"{speed:g}"] = {"factors": [None if x is None else np.asarray(x) for x in tab], "covered": covered}
            diag[name][f"{speed:g}"] = dg
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(
        "scattered_plume_tables", label="representative_chamber", validation_status="not_validated",
        inputs={"layouts": args.layouts, "speeds_m3_s": args.speeds, "n_particles": args.n_particles, "batches": args.batches,
                "feed_max_sccm": FEED_MAX_SCCM, "plume_temperature_K": PLUME_T, "chamber": vars(st.CHAMBER),
                "species": st.SPECIES, "p_grid_Pa": lc.P_GRID, "rho_m": rho, "gas_temperature_K": t_gas, "seed": args.seed,
                "coverage_rule": "through the first grid pressure whose feed reaches feed_max_sccm",
                "extends": None if old is None else {"run_id": old["run_id"], "seed": old["inputs"]["seed"]}},
        outputs={"rho_m": rho, "p_grid_Pa": lc.P_GRID, "factors": tables, "diagnostics": diag},
        sources=[Path(__file__), ROOT / "scripts/scattered_tables.py", ROOT / "src/mbe_twin/scattering.py",
                 ROOT / "src/mbe_twin/crucible.py", ROOT / "src/mbe_twin/vacuum.py", ENVELOPE],
        warnings=["Scattered component from cos^n surrogate sources, applied as a ratio to the comparison's direct maps",
                  "Plume free-molecular, N2 at 300 K, not modified by its own collisions",
                  "Spherical 0.5 m chamber, flat holder disk, hard spheres, uniform 300 K chamber gas, no pump; gamma = 1"],
        disabled_physics=["plume self-collisions", "pumping of wall-returned atoms", "plasma-heated chamber gas"])
    print(f"Wrote {write_manifest(manifest, out / 'manifest.json')}")


if __name__ == "__main__":
    main()
