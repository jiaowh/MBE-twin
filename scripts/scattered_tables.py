"""Scattered-arrival factors for the layout comparison: G(p, r) = (direct + scattered) / direct, per pressure.

scripts/layout_comparison.py attenuates the direct beams by the chamber's N2 with ratio tables on
its pressure grid (P_GRID) and drops scattered atoms. This script follows the scattered atoms
(mbe_twin.scattering, as scripts/scattered_redeposition.py) at every grid pressure and tabulates
the factor that adds them back, on the comparison's radii (39 points to the 94 mm mask):
- N, per layout: plate disk (the layout's active radius), cos^n with the holes' on-axis peaking
  (n = 2 / W - 1), the layout's polar angle and aim; walls recombine N with gamma = 1 (variant
  "gas") or 0.1 (variant "gas-gamma0.1", an upper case without a pump);
- Ga: a point on the 46 deg cone aimed at the wafer centre, cos^2, for the comparison's two
  background-collision diameters (6 and 8 A); Ga sticks on the walls.
The factor multiplies the comparison's attenuation table entry by entry (both on P_GRID), so the
comparison keeps its own plate and crucible maps and its own direct attenuation; only the
scattered component, relative to the direct one, comes from the cos^n surrogates.

Estimator: the factor is the Monte Carlo total arrival (direct + scattered, per emitted atom, in
10 equal-area bins out to 94 mm) divided by the deterministic direct flux of the same surrogate
source attenuated the comparison's way (exp(-s / lambda), lambda = vacuum.beam_mean_free_path:
mean speeds), averaged over each bin (scattering.binned_direct_flux). The denominator is exact,
so the factor stays well conditioned at high pressure where the direct beam is nearly gone, and
the comparison's own direct attenuation times the factor is the surrogate's total arrival
relative to its direct beam. The batch means are fitted by weighted least squares as a quadratic
in (r / 0.1 m)^2 (weights from the batch spread) and evaluated at the comparison's radii.
Recorded per entry: the fit's reduced chi^2, the factor's statistical half-range error, and the
Monte Carlo direct arrival over the deterministic one (the effect of the speed distribution
against the comparison's mean-speed mean free path). At p = 0 the factor is 1.

Usage: python scripts/scattered_tables.py [--layouts B B-p B-L] [--n-particles 8000000] [--ga-particles 16000000]
                                          [--batches 8] [--seed 20261003] [--aim-mm A] [--out results/scattered_tables]
--aim-mm A replaces the envelope's N aim offset (mm) of the one layout given, for tables at another aim
(read by realizable_controller.py --n-scatter); the Ga factors do not depend on it.
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
from mbe_twin.scattering import (K_B, Chamber, Gas, Source, binned_direct_flux, fit_even, radial_arrival, track,  # noqa: E402
                                 tube_cos_n)
from mbe_twin.vacuum import beam_mean_free_path  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ENVELOPE = ROOT / "data/design/design_envelope.json"
_spec = importlib.util.spec_from_file_location("layout_comparison", ROOT / "scripts/layout_comparison.py")
lc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(lc)

CHAMBER = Chamber(radius=0.5, holder_radius=0.13, wafer_radius=0.10)
N_BINS = 10
GA_COS_N = 2
SPECIES = {"Ga": {"mass_amu": 69.72, "temperature": 1235.0}, "N": {"mass_amu": 14.007, "temperature": 600.0}}
VARIANTS = {"gas": 1.0, "gas-gamma0.1": 0.1}


def geometry(polar_deg, aim, throw):
    th = np.radians(polar_deg)
    src = np.array([throw * np.sin(th), 0.0, -throw * np.cos(th)])
    return src, np.array([aim, 0.0, 0.0]) - src


def factor(rng, source, sp, d_beam, p, t_gas, gamma, n_total, batches, edges, centres, rho):
    n_part = n_total // batches
    gas = Gas(p / (K_B * t_gas), t_gas)
    lam = beam_mean_free_path(p, d_beam, SPECIES[sp]["mass_amu"], SPECIES[sp]["temperature"], t_gas=t_gas)
    a = binned_direct_flux(source, edges, lam)
    g_b, d_b = [], []
    for _ in range(batches):
        r, ind, _ = track(rng, n_part, source, diameter=d_beam, gas=gas, chamber=CHAMBER, gamma=gamma, **SPECIES[sp])
        d, s = radial_arrival(r, ind, n_part, edges)
        g_b.append((d + s) / a)
        d_b.append(d / a)
    g_b = np.array(g_b)
    g = g_b.mean(0)
    err = g_b.std(0, ddof=1) / np.sqrt(batches)
    fit = fit_even(centres, g, err, rho)
    chi2 = float(np.sum(((g - fit_even(centres, g, err, centres)) / err) ** 2) / (N_BINS - 3))

    def hr(f):
        return 100 * (f.max() - f.min()) / (2 * f.mean())
    hr_b = [hr(fit_even(centres, b, err, rho)) for b in g_b]
    return fit, {"bins": g.tolist(), "bins_err": err.tolist(), "reduced_chi2": chi2, "half_range_points": float(hr(fit)),
                 "half_range_points_err": float(np.std(hr_b, ddof=1) / np.sqrt(batches)),
                 "mc_direct_over_deterministic_mean": float(np.mean(d_b))}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--layouts", nargs="+", default=["B", "B-p", "B-L"])
    ap.add_argument("--n-particles", type=int, default=8_000_000)
    ap.add_argument("--ga-particles", type=int, default=16_000_000)
    ap.add_argument("--batches", type=int, default=8)
    ap.add_argument("--seed", type=int, default=20261003)
    ap.add_argument("--aim-mm", type=float, default=None, help="N aim offset (mm) replacing the envelope's (one layout)")
    ap.add_argument("--out", default="results/scattered_tables")
    args = ap.parse_args()
    if args.aim_mm is not None and len(args.layouts) != 1:
        raise SystemExit("scattered_tables: --aim-mm needs exactly one layout")
    env = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    usable = env["wafer_and_mask"]["usable_radius_m"]["value"]
    rho = np.linspace(0.0, usable, 39)                       # as layout_comparison.main
    edges = usable * np.sqrt(np.arange(N_BINS + 1) / N_BINS)
    centres = np.sqrt((edges[:-1] ** 2 + edges[1:] ** 2) / 2)
    throw = env["chamber"]["source_throw_m"]["value"]
    vac = env["vacuum"]
    t_gas = vac["gas_temperature_K"]["value"]
    rng = np.random.default_rng(args.seed)
    aims = {name: env["layouts"][name]["n"]["aim_offset_mm"] if args.aim_mm is None else args.aim_mm for name in args.layouts}
    tables, diag = {"N": {}, "Ga": {}}, {"N": {}, "Ga": {}}

    for name in args.layouts:
        n = env["layouts"][name]["n"]
        n_cos = tube_cos_n(n["L_over_r"])
        src, axis = geometry(n["polar_deg"], aims[name] / 1e3, throw)
        source = Source(tuple(src), tuple(axis), n_cos, radius=n.get("plate_radius_m", 0.020))
        tables["N"][name], diag["N"][name] = {}, {"n_cos": n_cos}
        for var, gamma in VARIANTS.items():
            tab, dg = [np.ones(len(rho))], [None]
            for p in lc.P_GRID[1:]:
                t = time.time()
                f, info = factor(rng, source, "N", vac["collision_diameters_m"]["N"], p, t_gas, gamma, args.n_particles, args.batches, edges, centres, rho)
                tab.append(f)
                dg.append(info)
                print(f"N {name} {var} p {p:.2e} Pa: G centre/edge {f[0]:.4f}/{f[-1]:.4f}, half-range "
                      f"{info['half_range_points']:.2f} +/- {info['half_range_points_err']:.2f}, chi2 {info['reduced_chi2']:.2f}, "
                      f"MC/det direct {info['mc_direct_over_deterministic_mean']:.3f} "
                      f"({time.time() - t:.0f} s)", flush=True)
            tables["N"][name][var] = np.array(tab)
            diag["N"][name][var] = dg

    port = 46
    src, axis = geometry(float(port), 0.0, throw)
    ga_source = Source(tuple(src), tuple(axis), GA_COS_N)
    for d_label, d in lc.GA_D.items():
        tab, dg = [np.ones(len(rho))], [None]
        for p in lc.P_GRID[1:]:
            t = time.time()
            f, info = factor(rng, ga_source, "Ga", d, p, t_gas, 1.0, args.ga_particles, args.batches, edges, centres, rho)
            tab.append(f)
            dg.append(info)
            print(f"Ga {port} deg d {d_label} p {p:.2e} Pa: G centre/edge {f[0]:.4f}/{f[-1]:.4f}, half-range "
                  f"{info['half_range_points']:.2f} +/- {info['half_range_points_err']:.2f}, chi2 {info['reduced_chi2']:.2f}, "
                      f"MC/det direct {info['mc_direct_over_deterministic_mean']:.3f} "
                  f"({time.time() - t:.0f} s)", flush=True)
        tables["Ga"][f"{port}_{d_label}"] = np.array(tab)
        diag["Ga"][f"{port}_{d_label}"] = dg

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = build_manifest(
        "scattered_tables", label="representative_chamber", validation_status="not_validated",
        inputs={"layouts": args.layouts, "n_particles": args.n_particles, "ga_particles": args.ga_particles,
                "batches": args.batches, "chamber": vars(CHAMBER), "species": SPECIES, "ga_cos_n": GA_COS_N,
                "variants_gamma": VARIANTS, "p_grid_Pa": lc.P_GRID, "rho_m": rho, "ga_d": lc.GA_D,
                "collision_diameters_m": vac["collision_diameters_m"], "gas_temperature_K": t_gas, "seed": args.seed}
               | ({} if args.aim_mm is None else {"aim_offset_mm": aims}),
        outputs={"rho_m": rho, "p_grid_Pa": lc.P_GRID, "factors": tables, "diagnostics": diag},
        sources=[Path(__file__), ROOT / "src/mbe_twin/scattering.py", ROOT / "src/mbe_twin/crucible.py",
                 ROOT / "src/mbe_twin/vacuum.py", ENVELOPE],
        warnings=["Scattered component from cos^n surrogate sources, applied as a ratio to the comparison's direct maps",
                  "Spherical 0.5 m chamber, flat holder disk, hard spheres, uniform 300 K gas, no pump",
                  "N wall recombination bracketed (gamma 1 / 0.1); the plate plume is not included",
                  "Ga factor for the 46 deg port, cos^2, independent of fill"],
        disabled_physics=["nitrogen plate plume", "pumping of wall-returned atoms", "plasma-heated chamber gas"])
    print(f"Wrote {write_manifest(manifest, out / 'manifest.json')}")


if __name__ == "__main__":
    main()
