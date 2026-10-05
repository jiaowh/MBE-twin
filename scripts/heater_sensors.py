"""Wafer temperature sensor count and placement for zone control (design-freeze observability).

Uses mbe_twin.heater and the zone optimizer of scripts/heater_zones.py. A 3-zone heater (split at
60 and 95 mm) is optimized for the nominal representative holder at a 740 C wafer mean, giving
zone powers P* and the nominal wafer profile T*(r). The real holder differs from the nominal one
in parameters no source fixes (wafer-ledge contact, overlap, Si conductivity, ledge emissivity,
heater gap). For each such perturbation, a controller sets the zone powers so that the chosen
sensors read their nominal values T*(r_s):
- at least as many sensors as zones: least squares on the readings (Gauss-Newton, powers >= 0;
  exact when the counts are equal);
- fewer sensors than zones: all zones scaled together at the nominal power ratios to match the
  mean sensor reading, as a single-loop controller does;
- open loop: P* unchanged (no wafer sensing; zone powers held by the supplies).
The outcome per case is the wafer temperature range and the mean offset from 740 C. A +1 K
bias on the outermost sensor tests sensitivity to a reading error.

Sensors are ideal point readings of the wafer temperature at radius r_s (a pyrometer spot or
an instrumented wafer); spot size, emissivity drift and viewport access are not modelled.

Usage: python scripts/heater_sensors.py [--out results/heater_sensors]
"""

import argparse
import importlib.util
import os
from pathlib import Path

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402

from mbe_twin.manifest import build_manifest, write_manifest  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("heater_zones", ROOT / "scripts/heater_zones.py")
hz = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hz)

LAYOUT = hz.LAYOUTS["3 zones"]
TARGET = 740.0 + 273.15
SENSOR_SETS = {
    "open loop": (),
    "1: centre": (0.0,),
    "1: mid-radius (60 mm)": (60.0,),
    "3: 0 / 70 / 97 mm": (0.0, 70.0, 97.0),
    "3: 30 / 77 / 90 mm": (30.0, 77.0, 90.0),
    "5: 0 / 40 / 70 / 90 / 98 mm": (0.0, 40.0, 70.0, 90.0, 98.0),
}
PERTURBATIONS = [
    ("contact 50", {}, {"h_contact": 50.0}), ("contact 1000", {}, {"h_contact": 1000.0}),
    ("overlap 1 mm", {"ledge_inner": 0.099}, {}), ("overlap 5 mm", {"ledge_inner": 0.095}, {}),
    ("k_Si 20", {}, {"k_wafer": 20.0}), ("k_Si 40", {}, {"k_wafer": 40.0}),
    ("ledge eps 0.15", {}, {"eps_ledge": 0.15}), ("ledge eps 0.6", {}, {"eps_ledge": 0.6}),
    ("gap 8 mm", {"gap": 0.008}, {}), ("gap 12 mm", {"gap": 0.012}, {}),
    ("wafer eps 0.63", {}, {"eps_wafer": 0.63}), ("wafer eps 0.77", {}, {"eps_wafer": 0.77}),
]


def readings(result, radii_mm):
    return np.interp(np.asarray(radii_mm) / 1e3, result["r_wafer"], result["t_wafer"])


def control(model, p0, radii_mm, targets, iters=30):
    """Zone powers making the sensor readings match the targets (see module docstring)."""
    if not radii_mm:
        return model.solve(heater_power=p0), p0.copy()
    n = len(p0)
    if len(radii_mm) < n:  # one loop: common scale factor on the nominal powers
        a = 1.0
        for _ in range(iters):
            r = model.solve(heater_power=a * p0)
            y = float(np.mean(readings(r, radii_mm) - targets))
            r2 = model.solve(heater_power=1.01 * a * p0)
            dy = float(np.mean(readings(r2, radii_mm) - readings(r, radii_mm))) / (0.01 * a)
            a -= y / dy
            if abs(y) < 1e-4:
                break
        return model.solve(heater_power=a * p0), a * p0
    p = p0.copy()
    for _ in range(iters):
        r = model.solve(heater_power=p)
        y = readings(r, radii_mm) - targets
        s = np.empty((len(radii_mm), n))
        for k in range(n):
            dp = np.zeros(n)
            dp[k] = 0.01 * p0.sum()
            s[:, k] = (readings(model.solve(heater_power=p + dp), radii_mm) - readings(r, radii_mm)) / dp[k]
        dp = np.linalg.lstsq(s, -y, rcond=None)[0]
        p = np.maximum(p + dp, 0.0)
        if np.max(np.abs(dp)) < 1e-4 * p0.sum():
            break
    return model.solve(heater_power=p), p


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="results/heater_sensors")
    args = ap.parse_args()
    nominal = hz.make(LAYOUT, {}, {})
    r0, _ = hz.optimize(nominal, TARGET)
    p_star = r0["zone_power"].copy()
    print(f"nominal: range {r0['wafer_range']:.2f} K, zone powers {np.round(p_star).tolist()} W")
    rows = []
    header = f"{'perturbation':16s} " + " ".join(f"{k:>24s}" for k in SENSOR_SETS)
    print("wafer range K (mean offset K) with each sensor set\n" + header)
    for pname, gk, pk in PERTURBATIONS:
        model = hz.make(LAYOUT, gk, pk)
        cells = []
        for sname, radii in SENSOR_SETS.items():
            targets = readings(r0, radii)
            res, p = control(model, p_star, radii, targets)
            out = {"perturbation": pname, "sensors": sname, "radii_mm": radii, "zone_power_W": p.tolist(),
                   "range_K": res["wafer_range"], "mean_offset_K": res["wafer_mean"] - TARGET}
            if radii:  # +1 K bias on the outermost sensor
                tb = targets.copy()
                tb[int(np.argmax(radii))] -= 1.0  # controller believes it is 1 K hotter than it is
                rb, _ = control(model, p_star, radii, tb)
                out["range_with_edge_bias_K"] = rb["wafer_range"]
            rows.append(out)
            cells.append(f"{res['wafer_range']:6.2f} ({res['wafer_mean'] - TARGET:+6.2f})")
        print(f"{pname:16s} " + " ".join(f"{c:>24s}" for c in cells), flush=True)
    print("\nworst over perturbations: range K / |mean offset| K / range with +1 K edge-sensor bias")
    for sname in SENSOR_SETS:
        sel = [r for r in rows if r["sensors"] == sname]
        worst = max(r["range_K"] for r in sel)
        off = max(abs(r["mean_offset_K"]) for r in sel)
        bias = max((r.get("range_with_edge_bias_K", np.nan) for r in sel), default=np.nan)
        print(f"  {sname:28s} {worst:6.2f} / {off:6.2f} / {bias:6.2f}")

    manifest = build_manifest(
        "heater_sensors", label="representative_chamber", validation_status="not_validated",
        inputs={"layout": LAYOUT, "target_K": TARGET, "sensor_sets": SENSOR_SETS,
                "perturbations": [p[0] for p in PERTURBATIONS], "nominal_zone_power_W": p_star.tolist()},
        outputs={"rows": rows, "nominal_range_K": r0["wafer_range"]},
        sources=[Path(__file__), ROOT / "scripts/heater_zones.py", ROOT / "src/mbe_twin/heater.py",
                 ROOT / "src/mbe_twin/radiation.py"],
        warnings=["Ideal point sensors of true wafer temperature; spot size, emissivity drift and access not modelled",
                  "Reduced axisymmetric heater model with bracketed parameters; not validated"],
        disabled_physics=["sensor optics", "transients and control dynamics"])
    print(f"Wrote {write_manifest(manifest, Path(args.out) / 'manifest.json')}")


if __name__ == "__main__":
    main()
