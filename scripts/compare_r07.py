"""Compare the free-molecular crucible model with R07 measurements (Gericke et al. 1991).

Geometry from R07: conical graphite crucible, aperture D = 16.5 mm, taper half-angle 2.6 deg,
melt depth L below the aperture given as L/D, deposition measured in a plane normal to the
crucible axis at R = 115 mm. The crucible length and quartz-sensor size are not reported;
sensor averaging is neglected. Measurements are the digitized curves in
data/benchmarks/r07_gericke1991.json, normalized to their own centre value.

Cases:
  fig3        filling level L/D = 0.5, 1, 2, 4 at ~0.35 A/s (near the collision-free limit)
  fig4        L/D = 4 at 0.35, 3.5, 11 A/s (collisions flatten profiles; model-form limit)
  fig5_top    60 deg inclined crucible, liquid (level) melt, L/D = 4, 0.07 A/s (collision-free)
  fig7        distance transfer 115 -> 265 mm, L/D = 2, 593 C, centre rates 10.0 / 1.9 A/s.
              The 265 mm panel has no x axis of its own and is read with the 115 mm axis.

Usage: python scripts/compare_r07.py [--particles 150000] [--out results/r07_comparison]
"""

import argparse
import json
from pathlib import Path

import numpy as np

from mbe_twin.beam import EffusionSource, arrival_flux
from mbe_twin.crucible import Crucible, next_event_flux, simulate
from mbe_twin.manifest import build_manifest, write_manifest

ROOT = Path(__file__).resolve().parents[1]
D = 0.0165
TAPER = np.radians(2.6)
R_PLANE = 0.115
X_EVAL = np.linspace(-0.045, 0.045, 91)
COMPARE_MAX_MM = 45.0


APEX_DEPTH = (D / 2) / np.tan(TAPER)  # taper apex below the orifice (R07's virtual source)


def measured(panel, curve):
    data = json.loads((ROOT / "data/benchmarks/r07_gericke1991.json").read_text(encoding="utf-8"))
    c = data["panels"][panel]["curves"][curve]
    x, y = np.array(c["x_mm"]), np.array(c["y"])
    order = np.argsort(x)
    x, y = x[order], y[order]
    centre = np.interp(0.0, x, y)  # dashed curves can have gaps at the centre
    return x, y / centre, data["panels"][panel]["estimated_error_y"]


def model_profile(crucible, particles, seed, azimuth_deg=0.0):
    """Normalized flux across the scan line at azimuth `azimuth_deg` in the crucible frame."""
    ev = simulate(crucible, particles, rng=seed)
    a = np.radians(azimuth_deg)
    pts = np.stack([X_EVAL * np.cos(a), X_EVAL * np.sin(a), np.full_like(X_EVAL, R_PLANE)], axis=1)
    f = next_event_flux(ev, pts, (0.0, 0.0, -1.0))
    return f / np.interp(0.0, X_EVAL, f), ev.transmission


def flat_orifice_profile():
    src = EffusionSource("flat", (0, 0, 0), (0, 0, 1), 1.0, 1.0, D / 2, 16, 64)
    pts = np.stack([X_EVAL, np.zeros_like(X_EVAL), np.full_like(X_EVAL, R_PLANE)], axis=1)
    f = arrival_flux([src], pts, (0.0, 0.0, -1.0))
    return f / np.interp(0.0, X_EVAL, f)


def compare(model, x_mm, y):
    keep = np.abs(x_mm) <= COMPARE_MAX_MM
    diff = np.interp(x_mm[keep], 1000 * X_EVAL, model) - y[keep]
    return {"rms": float(np.sqrt(np.mean(diff ** 2))), "max_abs": float(np.max(np.abs(diff))),
            "mean_bias": float(np.mean(diff)), "n": int(keep.sum())}


def transfer_rms(x_near, y_near, x_far, y_far, r_near, r_far, depth):
    """Point-source transfer between planes normal to the axis: a source `depth` below the
    orifice gives y_far(x) = y_near(x (r_near + depth) / (r_far + depth))."""
    keep = np.abs(x_far) <= COMPARE_MAX_MM
    scaled = x_far[keep] * (r_near + depth) / (r_far + depth)
    diff = np.interp(scaled, x_near, y_near) - y_far[keep]
    return {"rms": float(np.sqrt(np.mean(diff ** 2))), "max_abs": float(np.max(np.abs(diff))),
            "mean_bias": float(np.mean(diff)), "n": int(keep.sum())}


def half_width(x, y, level):
    """Outer x > 0 where the normalized profile falls to `level` (profiles decrease there)."""
    pos = x > 0
    return float(np.interp(-level, -y[pos], x[pos]))


def fig7_distance_transfer(particles):
    print("\nFig. 7, distance transfer 115 -> 265 mm (L/D = 2, 593 C, 10.0 / 1.9 A/s)")
    x1, y1, e1 = measured("fig7_115", "R=115 mm")
    x2, y2, e2 = measured("fig7_265", "R=265 mm")
    r1, r2 = 1000 * R_PLANE, 265.0
    res = {"digitization_error": [e1, e2], "apex_depth_mm": 1000 * APEX_DEPTH}

    # Measured 115 mm profile transferred with a point source at a given depth.
    depths = {"orifice (0 mm)": 0.0, f"taper apex ({1000 * APEX_DEPTH:.0f} mm)": 1000 * APEX_DEPTH}
    res["measured_transfer"] = {k: transfer_rms(x1, y1, x2, y2, r1, r2, z) for k, z in depths.items()}
    scan = np.arange(-50.0, 401.0, 1.0)
    rms = [transfer_rms(x1, y1, x2, y2, r1, r2, z)["rms"] for z in scan]
    res["measured_best_depth_mm"] = float(scan[np.argmin(rms)])
    for k, m in res["measured_transfer"].items():
        print(f"  measured 115 mm, point source at {k:18s} rms {m['rms']:.3f}  bias {m['mean_bias']:+.3f}")
    print(f"  best-fit point-source depth {res['measured_best_depth_mm']:.0f} mm (rms {min(rms):.3f})")

    # Free-molecular crucible model at both distances.
    ev = simulate(Crucible(D / 2, 2 * D, taper_half_angle=TAPER), particles, rng=7)
    xm = np.linspace(-0.048, 0.048, 193)
    prof, centre = {}, {}
    for r in (r1, r2):
        pts = np.stack([xm, np.zeros_like(xm), np.full_like(xm, r / 1000)], axis=1)
        f = next_event_flux(ev, pts, (0.0, 0.0, -1.0))
        centre[r] = float(np.interp(0.0, xm, f))
        prof[r] = f / centre[r]
    xmm = 1000 * xm
    for r, (x, y) in ((r1, (x1, y1)), (r2, (x2, y2))):
        keep = np.abs(x) <= COMPARE_MAX_MM
        d = np.interp(x[keep], xmm, prof[r]) - y[keep]
        res[f"model_{r:g}mm"] = {"rms": float(np.sqrt(np.mean(d ** 2))), "mean_bias": float(d.mean())}
        print(f"  crucible model at {r:g} mm             rms {res[f'model_{r:g}mm']['rms']:.3f}  "
              f"bias {res[f'model_{r:g}mm']['mean_bias']:+.3f}")
    rms = [transfer_rms(xmm, prof[r1], xmm, prof[r2], r1, r2, z)["rms"] for z in scan]
    res["model_best_depth_mm"] = float(scan[np.argmin(rms)])

    # Profile growth between the planes, and centre-rate decay.
    res["half_width_ratio"] = {}
    for level in (0.95, 0.9, 0.85):
        meas = half_width(x2, y2, level) / half_width(x1, y1, level)
        mod = half_width(xmm, prof[r2], level) / half_width(xmm, prof[r1], level)
        res["half_width_ratio"][f"{level:g}"] = {"measured": meas, "model": mod}
        print(f"  half-width growth at {level:.2f}: measured {meas:.3f}, model {mod:.3f} "
              f"(orifice point source {r2 / r1:.3f}, apex "
              f"{(r2 + 1000 * APEX_DEPTH) / (r1 + 1000 * APEX_DEPTH):.3f})")
    ratio_meas = 10.0 / 1.9
    ratio_lo, ratio_hi = 10.0 / 1.95, 10.0 / 1.85  # printed rates rounded to 0.1 A/s
    ratio_model = centre[r1] / centre[r2]
    res["centre_rate_ratio"] = {"measured": ratio_meas, "measured_range_from_rounding": [ratio_lo, ratio_hi],
                                "model": ratio_model, "inverse_square_from_orifice": (r2 / r1) ** 2}
    print(f"  centre-rate ratio 115/265: measured {ratio_meas:.2f} ({ratio_lo:.2f}-{ratio_hi:.2f} "
          f"from rounding), model {ratio_model:.2f}, 1/R^2 from orifice {(r2 / r1) ** 2:.2f}")
    print(f"  model's own shape-transfer depth {res['model_best_depth_mm']:.0f} mm "
          f"(measured {res['measured_best_depth_mm']:.0f} mm)")
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--particles", type=int, default=150_000)
    ap.add_argument("--out", default="results/r07_comparison")
    args = ap.parse_args()
    out = {"fig3": {}, "fig4": {}, "fig5_top": {}, "fig7": {}}
    flat = flat_orifice_profile()

    print("Fig. 3, filling level (conical, ~0.35 A/s); normalized-profile error over |x| <= 45 mm")
    print("  L/D   model rms  max|d|  bias    | flat orifice rms | digitization error")
    for ld in (0.5, 1.0, 2.0, 4.0):
        x, y, err = measured("fig3", f"L/D={ld:g}")
        prof, trans = model_profile(Crucible(D / 2, ld * D, taper_half_angle=TAPER), args.particles, 1)
        m, f = compare(prof, x, y), compare(flat, x, y)
        out["fig3"][f"L/D={ld:g}"] = {"model": m, "flat_orifice": f, "transmission": trans}
        print(f"  {ld:<4g}  {m['rms']:.3f}     {m['max_abs']:.3f}   {m['mean_bias']:+.3f}  | "
              f"{f['rms']:.3f}            | {err:.3f}")

    print("\nFig. 4, rate series at L/D = 4 (free-molecular model is rate-independent)")
    prof4, _ = model_profile(Crucible(D / 2, 4 * D, taper_half_angle=TAPER), args.particles, 2)
    for curve in ("0.35 A/s", "3.5 A/s", "11.0 A/s"):
        x, y, _ = measured("fig4", curve)
        m = compare(prof4, x, y)
        out["fig4"][curve] = m
        print(f"  {curve:9s} rms {m['rms']:.3f}  bias {m['mean_bias']:+.3f}")

    print("\nFig. 5 (upper), 60 deg inclined crucible, L/D = 4, 0.07 A/s, level melt")
    tilt = np.radians(60.0)
    variants = {"level melt, tilt toward +x": (np.sin(tilt), 0.0, np.cos(tilt)),
                "level melt, tilt toward -x": (-np.sin(tilt), 0.0, np.cos(tilt)),
                "melt normal to axis": (0.0, 0.0, 1.0)}
    for label, normal in variants.items():
        c = Crucible(D / 2, 4 * D, taper_half_angle=TAPER, melt_normal=normal)
        res = {}
        for curve, az in (("tau=0", 0.0), ("tau=90", 90.0)):
            x, y, err = measured("fig5_top", curve)
            prof, _ = model_profile(c, args.particles, 3, azimuth_deg=az)
            res[curve] = compare(prof, x, y)
        out["fig5_top"][label] = res
        print(f"  {label:28s} tau=0 rms {res['tau=0']['rms']:.3f} (max {res['tau=0']['max_abs']:.3f})"
              f"   tau=90 rms {res['tau=90']['rms']:.3f} (max {res['tau=90']['max_abs']:.3f})")
    print(f"  digitization error ~{err:.3f}; R07 does not state which scan direction is +x")

    # Diagnostic: which filling level would the level-melt model need to match Fig. 5?
    fits = {}
    for ld in (0.9, 1.0, 1.25, 1.5, 1.75, 2.0, 3.0, 4.0):
        c = Crucible(D / 2, ld * D, taper_half_angle=TAPER, melt_normal=variants["level melt, tilt toward +x"])
        rms = []
        for curve, az in (("tau=0", 0.0), ("tau=90", 90.0)):
            x, y, _ = measured("fig5_top", curve)
            prof, _ = model_profile(c, args.particles // 2, 4, azimuth_deg=az)
            rms.append(compare(prof, x, y)["rms"])
        fits[ld] = float(np.mean(rms))
    best = min(fits, key=fits.get)
    out["fig5_top"]["effective_L_over_D_scan"] = fits
    print("  effective L/D needed (mean rms over both azimuths): "
          + "  ".join(f"{k:g}:{v:.3f}" for k, v in fits.items()) + f"  -> best {best:g} (stated 4)")

    out["fig7"] = fig7_distance_transfer(args.particles)

    manifest = build_manifest(
        "r07_comparison", label="representative_chamber",
        validation_status="not_validated",
        inputs={"particles": args.particles, "aperture_m": D, "taper_half_angle_deg": 2.6,
                "plane_distance_m": R_PLANE, "compare_max_mm": COMPARE_MAX_MM,
                "data": "data/benchmarks/r07_gericke1991.json"},
        outputs=out,
        warnings=["Measured curves are the authors' averaged fits, digitized from a scan",
                  "Crucible length and quartz-sensor size unreported; sensor averaging neglected",
                  "Bismuth, not Ga/Al; free-molecular model has no rate dependence",
                  "Fig. 7: the 265 mm panel has no x axis; it is read with the 115 mm panel's "
                  "axis, and a 5-10% scale error there would change the shape-transfer result",
                  "Fig. 7: 593 C with 10 A/s at 115 mm conflicts with Figs. 3-4 (573 C -> "
                  "0.35 A/s at L/D = 4); the profile shape supports an elevated rate"],
        disabled_physics=["intermolecular collisions in the crucible", "sensor spatial averaging"])
    print(f"\nWrote {write_manifest(manifest, Path(args.out) / 'manifest.json')}")


if __name__ == "__main__":
    main()
