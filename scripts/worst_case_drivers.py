"""Which uncertainty sets the worst-case thickness at an operating point (realizable controller).

Reads the per-state arrays that scripts/realizable_controller.py --dump-t writes (states_<layout>_<T>C.npz)
and, for one controller, ranks the uncertain factors by their effect on the worst-case thickness
half-range/mean over the states that are valid and in the growth window:
- fixed: the worst case with that factor held at its nominal value (all others free); the drop from the
  overall worst case is what the factor's spread adds;
- alone: the worst case when only that factor varies (all others nominal; the droplet law, a truth
  scenario without a nominal, stays free in both).
Factors: N pointing (25 states within +/-0.8 deg), Ga state (fill x collision diameter), heater error
(wafer emissivity x contact x worst zone error), pyrometer bias, droplet law, rate-monitor error, BFM error.
Nominal: nominal pose, 70 mm / 8 A, emissivity 0.70, contact 200, no zone error, bias 0, zero errors.
The worst states themselves are listed with their factor values.

Usage: python scripts/worst_case_drivers.py DUMP.npz [DUMP.npz ...] [--controller "rate monitor + BFM"] [--out FILE.json]
"""

import argparse
import importlib.util
import json
import os
from pathlib import Path

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def pointing_labels(layout):
    """The +/-0.8 deg pointing states in the order of operating_optimum.load_inputs (nominal first)."""
    spec = importlib.util.spec_from_file_location("layout_comparison", ROOT / "scripts/layout_comparison.py")
    lc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lc)
    env = json.loads(lc.ENVELOPE.read_text(encoding="utf-8"))
    rec = json.loads(lc.comparison_record("gas+plume").read_text(encoding="utf-8"))
    n = env["layouts"][layout]["n"]
    prefix = f"N_{n['L_over_r']:g}_{n['polar_deg']:g}_{n['aim_offset_mm']:g}_"
    nf = next(c for c in rec["inputs"]["map_caches"] if c["file"].startswith(prefix))
    states = json.loads(str(np.load(ROOT / "results/layout_comparison_bc" / nf["file"])["states"]))
    keep = [states[0]] + [s for s in states if s[1] == 0.8]
    return ["nominal" if s[0] == "nominal" else f"{s[0]} {s[1]:g} deg dir {s[2]:g}" for s in keep]


def analyse(path, controller):
    z = np.load(path)
    meta = json.loads(str(z["meta"]))
    layout = Path(path).stem.split("_")[1]
    get = {k: z[f"{controller}|{k}"] for k in ("valid", "margin", "thick", "g", "h", "law", "n", "e", "eb")}
    joint = get["valid"] & (get["margin"] >= 0)
    th = np.where(joint, get["thick"], -np.inf)
    heat = meta["heater"]
    h_err = np.array([(s["eps"], s["contact"], s["zone_error"]) for s in heat])
    combo_keys = {tuple(r): i for i, r in enumerate(np.unique(h_err, axis=0))}
    h_combo = np.array([combo_keys[tuple(r)] for r in h_err])[get["h"]]
    h_bias = np.array([s["controller"] for s in heat])[get["h"]]
    g_nom = [tuple(x) for x in meta["ga_labels"]].index((70, "8"))
    combo_nom = combo_keys[(0.70, 200.0, 0.0)]
    factors = {
        "N pointing": (get["n"], 0),
        "Ga fill / diameter": (get["g"], g_nom),
        "heater error (emissivity, contact, zone)": (h_combo, combo_nom),
        "pyrometer bias": (h_bias, "pyrometer +0 K"),
        "rate-monitor error": (get["e"], 1),
        "BFM error": (get["eb"], 1),
    }
    nominal_all = np.ones(th.shape, bool)
    for v, nom in factors.values():
        if not (np.asarray(v) == -1).all():
            nominal_all &= (v == nom) | (np.asarray(v) == -1)
    worst = float(th.max())
    out = {"file": Path(path).name, "layout": layout, "controller": controller, "joint_fraction": float(joint.mean()),
           "worst_pct": worst, "nominal_pct_by_law": {}, "factors": {}}
    for li, law in enumerate(meta["laws"]):
        sel = nominal_all & (get["law"] == li)
        out["nominal_pct_by_law"][law] = float(th[sel].max()) if sel.any() and np.isfinite(th[sel]).any() else None
    for name, (v, nom) in factors.items():
        if (np.asarray(v) == -1).all():
            continue
        fixed = th[v == nom]
        others = np.ones(th.shape, bool)
        for n2, (v2, nom2) in factors.items():
            if n2 != name and not (np.asarray(v2) == -1).all():
                others &= v2 == nom2
        alone = th[others]
        out["factors"][name] = {"worst_fixed_pct": float(fixed.max()), "adds_pct": worst - float(fixed.max()),
                                "worst_alone_pct": float(alone.max()) if np.isfinite(alone).any() else None}
    labels = pointing_labels(layout)
    order = np.argsort(th)[::-1][:5]
    out["worst_states"] = [{"thickness_pct": float(th[i]), "pointing": labels[get["n"][i]],
                            "ga": meta["ga_labels"][get["g"][i]], "heater": heat[get["h"][i]],
                            "law": meta["laws"][get["law"][i]],
                            "rate_error": meta["e_rate"][get["e"][i]] if get["e"][i] >= 0 else None,
                            "bfm_error": meta["e_bfm"][get["eb"][i]] if get["eb"][i] >= 0 else None} for i in order]
    # worst case by pointing state (others free): how the pointing ensemble spreads
    out["worst_by_pointing"] = {labels[k]: float(th[get["n"] == k].max()) for k in range(len(labels))}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("dumps", nargs="+")
    ap.add_argument("--controller", default="rate monitor + BFM")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()
    res = [analyse(p, args.controller) for p in args.dumps]
    for r in res:
        print(f"\n{r['file']} ({r['controller']}): joint {100 * r['joint_fraction']:.1f} %, worst {r['worst_pct']:.2f} %; "
              f"all-nominal by law " + ", ".join(f"{k}: {v:.2f} %" for k, v in r["nominal_pct_by_law"].items() if v))
        for name, f in sorted(r["factors"].items(), key=lambda kv: -kv[1]["adds_pct"]):
            print(f"  {name:42s} fixed -> worst {f['worst_fixed_pct']:.2f} % (adds {f['adds_pct']:.2f} pt); "
                  f"alone -> {f['worst_alone_pct']:.2f} %")
        bp = sorted(r["worst_by_pointing"].items(), key=lambda kv: -kv[1])
        print("  worst pointing states: " + "; ".join(f"{k} {v:.2f} %" for k, v in bp[:4]) +
              f"; best {bp[-1][0]} {bp[-1][1]:.2f} %")
        w = r["worst_states"][0]
        print(f"  worst state: {w['pointing']}, Ga {w['ga']}, heater {w['heater']}, {w['law']}, "
              f"rate err {w['rate_error']}, BFM err {w['bfm_error']}")
    if args.out:
        Path(args.out).write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
