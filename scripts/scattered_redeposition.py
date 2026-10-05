"""Where do the beam atoms scattered by the background N2 and the nitrogen plume land? Test-particle Monte Carlo.

The layout studies attenuate the direct Ga and N beams by the background N2 (exp(-s / lambda))
and drop the scattered atoms (scripts/background_scattering.py: "bounding case: they are lost").
At the operating pressures of the leading layouts (B-p near 8e-3 Pa at its Kn 3 point, B-L at
1.1e-2 Pa) that removes 50-70 % of the Ga beam and 25-30 % of the N beam, so where the scattered
atoms go is not a small correction. This script follows them (mbe_twin.scattering):
- emission: Ga from a point on the 46 deg cone aimed at the wafer centre, cos^2 (cos^1 and cos^4
  as a beam-width sensitivity); N uniformly from the plate's active disk (B-p 20 mm, B-L 30 mm),
  cos^n with the on-axis peaking of the holes' L/r (n = 2 / W - 1: 3.70 for L/r 2.92, 2.91 for L/r 2),
  aimed as the layout. Speeds from the flux-weighted
  Maxwellian at the beam temperature (Ga 1235 K, N 600 K, design envelope);
- the chamber's N2 at 300 K and the operating pressure; hard spheres, d_pair = (d_beam + 3.7 A) / 2,
  isotropic in the centre-of-mass frame, so heavy Ga (70 amu) on N2 (28 amu) stays forward-biased
  and N (14 amu) scatters broadly;
- optionally the free-molecular N2 plume of the plate: the feed leaves the active disk uniformly,
  with the same cos^n as the N atoms, at 300 or 600 K (plasma-heated gas, not sourced). Feeds are
  the operating points' (B-p 19.4 sccm, B-L p x S = 26.1 sccm). Its density in front of the plate
  is several times the chamber's; the plume is not modified by its own collisions (first order);
- chamber: a sphere of radius 0.5 m around the wafer centre (no chamber drawing exists; the
  sphere stands in for the cryoshroud); holder: an absorbing disk of radius 0.13 m in the wafer
  plane (the design envelope's holder assembly radius), the wafer is r <= 0.1 m of it;
- walls: Ga sticks (cryoshroud). N atoms recombine (are lost) with probability gamma per wall
  hit, otherwise are re-emitted diffusely at 300 K. gamma = 1 and 0.1 bracket the unsourced wall
  recombination; there is no pump in the model, so at gamma = 0.1 the wall-returned N is an upper
  case.

Outputs, rotation-averaged on the wafer (equal-area radial bins out to the 94 mm mask):
- D: atoms arriving with no collision; S: atoms arriving after one or more collisions or wall
  returns;
- per case, the fractions of the emitted atoms in D and S, the collisions per emitted atom (chamber
  gas and plume), the ratio F = (D + S) / D at the centre, mid-radius and edge, and the
  half-range/mean of F; errors from the batches;
- against a vacuum run of the same source: D / D_vac (the chamber attenuation the comparison
  applies, plus the plume's where present) and (D + S) / D_vac (the arrival with the scattered atoms
  kept). Their means and half-ranges say how much of the attenuation (amount and shape) survives;
- for the Ga / N ratio, the ratio of Ga's and N's F at the same pressure.

Sources are surrogates (cos^n with the layouts' port angles and aims), not the plate and crucible
models of the comparison: the scattered component is used relative to the direct beam, as a ratio.
Check: in vacuum D matches the analytic cos^n map of a point source
(background_scattering.rotation_profile). Not included: the pump, plasma-heated chamber gas,
collisions of the plume with itself.

Usage: python scripts/scattered_redeposition.py [--particles 400000] [--batches 8] [--out results/scattered_redeposition]
"""

import argparse
import importlib.util
import os
from pathlib import Path

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402

from mbe_twin.manifest import build_manifest, write_manifest  # noqa: E402
from mbe_twin.scattering import K_B, Chamber, Gas, Plume, Source, radial_arrival, track, tube_cos_n  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SCCM = 1.68875e-3            # Pa m^3/s per sccm (273.15 K standard)
MOLECULES_PER_SCCM = SCCM / (K_B * 273.15)
T_GAS = 300.0
THROW = 0.35
CHAMBER = Chamber(radius=0.5, holder_radius=0.13, wafer_radius=0.10)
R_MASK = 0.094
N_BINS = 10
EDGES = R_MASK * np.sqrt(np.arange(N_BINS + 1) / N_BINS)   # equal-area bins
CENTRES = np.sqrt((EDGES[:-1] ** 2 + EDGES[1:] ** 2) / 2)

SPECIES = {"Ga": {"mass_amu": 69.72, "temperature": 1235.0}, "N": {"mass_amu": 14.007, "temperature": 600.0}}
# layout surrogates: pressure Pa, N feed sccm, N polar deg, N aim m, hole L/r (sets cos^n), plate active radius m
LAYOUTS = {
    "B-p (Kn 3 point, eta 0.3, 19.4 sccm / 4 m^3/s)": {"p": 19.4 * SCCM / 4.0, "feed": 19.4, "polar": 46.0, "aim": 0.0975,
                                                        "l_over_r": 2.92, "plate_radius": 0.020},
    "B-L (eta 0.3, 4 m^3/s, 1 um/h)": {"p": 1.1e-2, "feed": 1.1e-2 * 4.0 / SCCM, "polar": 46.0, "aim": 0.090, "l_over_r": 2.0,
                                       "plate_radius": 0.030},
}
GA_PORT, GA_N = 46.0, 2


def geometry(polar_deg, aim):
    th = np.radians(polar_deg)
    src = np.array([THROW * np.sin(th), 0.0, -THROW * np.cos(th)])
    return src, np.array([aim, 0.0, 0.0]) - src


def half_range(p):
    return 100 * (p.max() - p.min()) / (2 * p.mean())


def se(a):
    return float(np.std(a, ddof=1) / np.sqrt(len(a)))


def case(rng, n_part, batches, source, sp, d_beam, gas=None, plume=None, gamma=1.0):
    ds, ss, info = [], [], []
    for _ in range(batches):
        r, ind, counts = track(rng, n_part, source, diameter=d_beam, gas=gas, plume=plume, chamber=CHAMBER, gamma=gamma,
                               **SPECIES[sp])
        d, s = radial_arrival(r, ind, n_part, EDGES)
        ds.append(d)
        ss.append(s)
        info.append((np.sum(~ind) / n_part, np.sum(ind) / n_part, counts["gas"] / n_part, counts["plume"] / n_part))
    ds, ss, info = np.array(ds), np.array(ss), np.array(info)
    d, s = ds.mean(0), ss.mean(0)
    f_b = (ds + ss) / ds
    f = (d + s) / d
    return {
        "direct_fraction_of_emitted_on_wafer": float(info[:, 0].mean()),
        "scattered_fraction_of_emitted_on_wafer": float(info[:, 1].mean()),
        "gas_collisions_per_emitted_atom": float(info[:, 2].mean()),
        "plume_collisions_per_emitted_atom": float(info[:, 3].mean()),
        "radius_mm": (1e3 * CENTRES).tolist(), "D": d.tolist(), "S": s.tolist(), "F": f.tolist(),
        "F_centre_mid_edge": [float(f[0]), float(f[N_BINS // 2]), float(f[-1])],
        "F_half_range_points": [float(half_range(f)), se([half_range(q) for q in f_b])],
        "_F_batches": f_b, "_D_batches": ds, "_S_batches": ss,
    }


def against_vacuum(r, vac):
    """Direct-only arrival over vacuum (D / D_vac) against the arrival with scattered atoms ((D + S) / D_vac)."""
    out = {}
    for key, num in (("direct_only", r["_D_batches"]), ("direct_plus_scattered", r["_D_batches"] + r["_S_batches"])):
        b = num / vac["_D_batches"]
        q = num.mean(0) / vac["_D_batches"].mean(0)
        out[key] = {"profile_over_vacuum_centre_mid_edge": [float(q[0]), float(q[N_BINS // 2]), float(q[-1])],
                    "mean_over_vacuum": float(q.mean()),
                    "half_range_points": [float(half_range(q)), se([half_range(x) for x in b])]}
    return out


def strip(d):
    return {k: v for k, v in d.items() if not k.startswith("_")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--particles", type=int, default=400_000)
    ap.add_argument("--batches", type=int, default=8)
    ap.add_argument("--out", default="results/scattered_redeposition")
    args = ap.parse_args()
    rng = np.random.default_rng(20261002)
    spec = importlib.util.spec_from_file_location("bs", ROOT / "scripts/background_scattering.py")
    bs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bs)

    # check: vacuum, a point cos^3 source as B-L's aim, against the analytic cos^n rotation profile
    src, axis = geometry(46.0, 0.090)
    chk = case(rng, args.particles, 4, Source(tuple(src), tuple(axis), 3), "N", 3e-10)
    bs.RHO = CENTRES
    ana = bs.rotation_profile(46.0, 0.090, 3, np.inf)[:, 0]
    mc = np.array(chk["D"])
    ratio = (mc / mc.mean()) / (ana / ana.mean())
    check = {"vacuum_D_over_analytic_shape_max_dev": float(np.max(np.abs(ratio - 1))),
             "vacuum_scattered_fraction": chk["scattered_fraction_of_emitted_on_wafer"]}
    print(f"check, vacuum: D shape vs analytic cos^n map within {100 * check['vacuum_D_over_analytic_shape_max_dev']:.2f} %; "
          f"scattered {check['vacuum_scattered_fraction']:.1e}", flush=True)

    results = {}
    for lay, L in LAYOUTS.items():
        L = {**L, "n_cos": tube_cos_n(L["l_over_r"])}
        res = {"n_cos": L["n_cos"], "pressure_Pa": L["p"], "feed_sccm": L["feed"]}
        gas = Gas(density=L["p"] / (K_B * T_GAS), temperature=T_GAS)
        nsrc, naxis = geometry(L["polar"], L["aim"])
        gsrc, gaxis = geometry(GA_PORT, 0.0)
        n_source = Source(tuple(nsrc), tuple(naxis), L["n_cos"], radius=L["plate_radius"])
        ga_source = {n: Source(tuple(gsrc), tuple(gaxis), n) for n in (1, GA_N, 4)}
        area = np.pi * L["plate_radius"] ** 2
        plumes = {t: Plume(tuple(nsrc), tuple(naxis / np.linalg.norm(naxis)), L["plate_radius"],
                           L["feed"] * MOLECULES_PER_SCCM / area, temperature=t, n_cos=L["n_cos"]) for t in (300.0, 600.0)}
        res["plume_density_at_plate_centre_Pa_equivalent_300K"] = {
            f"{t:g} K": float(pl.density(np.asarray(nsrc)[None] + 1e-4 * naxis / np.linalg.norm(naxis))[0] * K_B * T_GAS)
            for t, pl in plumes.items()}
        cases = {   # name: (species, diameter, source, gas, plume, gamma)
            "Ga, d 8 A": ("Ga", 8e-10, ga_source[GA_N], gas, None, 1.0),
            "Ga, d 6 A": ("Ga", 6e-10, ga_source[GA_N], gas, None, 1.0),
            "Ga, d 8 A, cos^1": ("Ga", 8e-10, ga_source[1], gas, None, 1.0),
            "Ga, d 8 A, cos^4": ("Ga", 8e-10, ga_source[4], gas, None, 1.0),
            "N, gamma 1": ("N", 3e-10, n_source, gas, None, 1.0),
            "N, gamma 0.1": ("N", 3e-10, n_source, gas, None, 0.1),
            "N, gamma 1, plume 300 K": ("N", 3e-10, n_source, gas, plumes[300.0], 1.0),
            "N, gamma 1, plume 600 K": ("N", 3e-10, n_source, gas, plumes[600.0], 1.0),
        }
        vac = {}
        for name, (sp, d_b, source, g, pl, gam) in cases.items():
            if source not in vac:
                vac[source] = case(rng, args.particles, args.batches, source, sp, d_b)
            r = case(rng, args.particles, args.batches, source, sp, d_b, gas=g, plume=pl, gamma=gam)
            r["against_vacuum"] = against_vacuum(r, vac[source])
            av = r["against_vacuum"]
            res[name] = r
            print(f"{lay[:3]} {L['p']:.2e} Pa {name:24s} direct {r['direct_fraction_of_emitted_on_wafer']:.4f} "
                  f"scattered {r['scattered_fraction_of_emitted_on_wafer']:.4f}; collisions gas "
                  f"{r['gas_collisions_per_emitted_atom']:.2f} plume {r['plume_collisions_per_emitted_atom']:.2f}; "
                  f"F half-range {r['F_half_range_points'][0]:.2f} +/- {r['F_half_range_points'][1]:.2f}; arrival/vacuum mean "
                  f"{av['direct_only']['mean_over_vacuum']:.3f} -> {av['direct_plus_scattered']['mean_over_vacuum']:.3f}, "
                  f"shape {av['direct_only']['half_range_points'][0]:.2f} +/- {av['direct_only']['half_range_points'][1]:.2f} -> "
                  f"{av['direct_plus_scattered']['half_range_points'][0]:.2f} +/- "
                  f"{av['direct_plus_scattered']['half_range_points'][1]:.2f} points", flush=True)
        for gname in ("Ga, d 8 A", "Ga, d 6 A"):
            for nname in ("N, gamma 1", "N, gamma 0.1", "N, gamma 1, plume 300 K"):
                q_b = res[gname]["_F_batches"] / res[nname]["_F_batches"]
                q = np.array(res[gname]["F"]) / np.array(res[nname]["F"])
                res[f"Ga/N ratio change: {gname} / {nname}"] = {
                    "ratio_centre_mid_edge": [float(q[0]), float(q[N_BINS // 2]), float(q[-1])],
                    "half_range_points": [float(half_range(q)), se([half_range(a) for a in q_b])]}
                print(f"    Ga/N factor {gname} / {nname}: centre/mid/edge "
                      f"{'/'.join(f'{x:.3f}' for x in q[[0, N_BINS // 2, -1]])}, half-range {half_range(q):.2f} points", flush=True)
        results[lay] = {k: strip(v) if isinstance(v, dict) else v for k, v in res.items()}

    manifest = build_manifest(
        "scattered_redeposition", label="representative_chamber", validation_status="not_validated",
        inputs={"particles_per_batch": args.particles, "batches": args.batches, "chamber": vars(CHAMBER), "mask_m": R_MASK,
                "layouts": LAYOUTS, "ga_port_deg": GA_PORT, "ga_cos_n": GA_N, "species": SPECIES,
                "gas": {"T_K": T_GAS}, "seed": 20261002},
        outputs={"check": check, "results": results},
        sources=[Path(__file__), ROOT / "src/mbe_twin/scattering.py", ROOT / "scripts/background_scattering.py"],
        warnings=["cos^n surrogates of the sources, not the comparison's plate and crucible models; use F as a ratio",
                  "Spherical 0.5 m chamber and a flat holder disk stand in for the missing chamber drawing",
                  "Hard spheres, isotropic in the centre-of-mass frame; uniform 300 K chamber gas; no pump",
                  "Plume free-molecular and unmodified by its own collisions; plume gas temperature bracketed (300 / 600 K)",
                  "N wall recombination bracketed (gamma 1 / 0.1), not sourced"],
        disabled_physics=["pumping of wall-returned atoms", "plasma-heated chamber gas", "plume self-collisions"])
    print(f"Wrote {write_manifest(manifest, Path(args.out) / 'manifest.json')}")


if __name__ == "__main__":
    main()
