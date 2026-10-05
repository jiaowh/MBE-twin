"""Back-calculate the active-N conversion fraction eta from published N-limited growth rates.

For each point of data/parameters/nitrogen_output_evidence.json (N2 flow, measured N-limited
growth rate at the substrate centre, aperture plate), the plate model of the layout studies
gives the centre flux per atom/s of plate output, F, for the source aimed at the substrate
centre (straight-hole free-molecular plate, crucible.py random walk per L/r, 20 mm active
radius, uniform output, no background attenuation). Then

    eta = J / (F x 2 x Q x 8.956e17)

with J the N atom arrival rate per area that the growth rate implies (GaN atom rate of the
growth model, scaled by N density for InN). Unpublished geometry is bracketed: throw, source
angle to the substrate normal, plate thickness (hence L/r). The result is a range of eta per
point, not a measurement. Without attenuation in the published chambers (below 1e-4 Torr, R26)
eta is slightly underestimated; a lower F (wider beam, longer throw) raises it.

eta > 1 is impossible: a geometry that implies it for any point is rejected, not reported as a
scenario. Per point, the range over all bracketed geometries and over the admissible ones
(eta <= 1 for that point) are both given. Jointly, points measured in one chamber share its
geometry and points with one plate share its thickness, so a geometry is admissible only if
every point it implies has eta <= 1 (and, as a stricter variant, <= 0.7, the highest
dissociation reported at low flow). The joint ranges are the result to quote, conditional on
the bracket and on the plate model applying to the published plates. The 200 mm consequence
is evaluated by scripts/nitrogen_rate_limits.py, which reads this record.

Usage: python scripts/nitrogen_output_evidence.py
"""

import itertools
import json
import os
from pathlib import Path

for _v in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import numpy as np  # noqa: E402

from mbe_twin.aperture import aperture_plate_sources, hex_holes  # noqa: E402
from mbe_twin.beam import Wafer, rotation_averaged_flux  # noqa: E402
from mbe_twin.crucible import Crucible, simulate  # noqa: E402
from mbe_twin.manifest import build_manifest, write_manifest  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "data/parameters/nitrogen_output_evidence.json"
N_PER_SCCM = 2 * 1.68875e-3 / (1.380649e-23 * 273.15)
HDRS_ASPECTS = (0.0, 2.92, 5.83)
PARTICLES, SEED = 20_000, 80


def centre_flux_per_output(aspect, throw, polar_deg, events_cache):
    if aspect not in events_cache:
        events_cache[aspect] = simulate(Crucible(1e-4, max(aspect, 0.0) * 1e-4), PARTICLES, rng=SEED)
    wafer = Wafer(radius=0.0254)
    src = aperture_plate_sources("N", wafer, events_cache[aspect], hex_holes(0.020, 0.010), throw=throw,
                                 polar_angle=np.radians(polar_deg), azimuth=0.0, total_rate=1.0)
    return float(rotation_averaged_flux(src, wafer, np.array([0.0, 0.002]), n_angles=1)[0])   # centre: rotation-free


def main():
    ev = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    gp = json.loads((ROOT / "data/parameters/gan_growth.json").read_text(encoding="utf-8"))
    k_atoms = gp["units"]["ml_per_s_per_nm_per_min"] * 1.14e19   # GaN N atoms m^-2 s^-1 per nm/min, as layout_comparison
    dens = ev["conventions"]["material_N_density_cm3"]
    cache = {}
    rows = []
    for pt in ev["points"]:
        sysd = ev["systems"][pt["system"]]
        plate = ev["plates"][pt["plate"]]
        if plate["hole_diameter_m"]:
            aspects = [round(t / (plate["hole_diameter_m"] / 2), 2) for t in plate["thickness_m"]["bracket"]]
        else:
            aspects = list(HDRS_ASPECTS)
        j = pt["rate_um_h"] * 1000 / 60 * k_atoms * dens[pt["material"]] / dens["GaN"]
        etas = []
        for a, throw, pol in itertools.product(aspects, sysd["throw_m"]["bracket"], sysd["source_polar_deg"]["bracket"]):
            f = centre_flux_per_output(a, throw, pol, cache)
            etas.append({"L_over_r": a, "throw_m": throw, "polar_deg": pol, "F_per_m2": f,
                         "eta": j / (f * N_PER_SCCM * pt["flow_sccm"])})
        lo, hi = min(e["eta"] for e in etas), max(e["eta"] for e in etas)
        adm = [e["eta"] for e in etas if e["eta"] <= 1.0]
        rows.append({"id": pt["id"], "flow_sccm": pt["flow_sccm"], "power_W": pt["power_W"], "rate_um_h": pt["rate_um_h"],
                     "material": pt["material"], "J_atoms_m2_s": j, "eta_range_all_geometries": [lo, hi],
                     "eta_range_admissible": [min(adm), max(adm)] if adm else None,
                     "rejected_geometries": sum(e["eta"] > 1.0 for e in etas), "cases": etas})
        print(f"{pt['id']:8s} {pt['flow_sccm']:5.1f} sccm {str(pt['power_W']):>4s} W {pt['rate_um_h']:5.2f} um/h {pt['material']}: "
              f"eta {lo:.3f} - {hi:.3f} over the bracket; admissible (<= 1) "
              + (f"{min(adm):.3f} - {max(adm):.3f}" if adm else "none"), flush=True)

    # joint constraint: points from one chamber share its geometry, and points with one plate share its
    # thickness; a geometry is admissible only if every point it implies has eta <= bound
    joint = {}
    for sname, sysd in ev["systems"].items():
        pts = [p for p in ev["points"] if p["system"] == sname]
        plates = sorted({p["plate"] for p in pts})
        if any(ev["plates"][pl]["hole_diameter_m"] is None for pl in plates):
            continue
        thick = [ev["plates"][pl]["thickness_m"]["bracket"] for pl in plates]
        thick = [np.linspace(t[0], t[1], 3) for t in thick]
        throws = np.linspace(*sysd["throw_m"]["bracket"], 5)
        polars = np.linspace(*sysd["source_polar_deg"]["bracket"], 3)
        combos = []
        for throw, pol, *ts in itertools.product(throws, polars, *thick):
            tmap = dict(zip(plates, ts))
            e = {}
            for p in pts:
                a = round(tmap[p["plate"]] / (ev["plates"][p["plate"]]["hole_diameter_m"] / 2), 2)
                j = p["rate_um_h"] * 1000 / 60 * k_atoms * dens[p["material"]] / dens["GaN"]
                e[p["id"]] = j / (centre_flux_per_output(a, float(throw), float(pol), cache) * N_PER_SCCM * p["flow_sccm"])
            combos.append({"throw_m": float(throw), "polar_deg": float(pol),
                           "thickness_m": {k: float(v) for k, v in tmap.items()}, "eta": e})
        joint[sname] = {}
        for bound in (1.0, 0.7):
            ok = [c for c in combos if max(c["eta"].values()) <= bound]
            ranges = {p["id"]: [min(c["eta"][p["id"]] for c in ok), max(c["eta"][p["id"]] for c in ok)] if ok else None
                      for p in pts}
            joint[sname][f"eta<={bound:g}"] = {"admissible": len(ok), "of": len(combos), "eta_ranges": ranges}
            print(f"{sname}, every point eta <= {bound:g}: {len(ok)} of {len(combos)} geometries admissible")
            for pid, rg in ranges.items():
                if rg:
                    print(f"   {pid:8s} eta {rg[0]:.3f} - {rg[1]:.3f}")
        joint[sname]["combos"] = combos

    gt = joint.get("GT_Riber32", {}).get("eta<=1", {}).get("eta_ranges", {})
    high = [v for pid in ("R26-a", "R26-b", "R26-c") if gt.get(pid) for v in gt[pid]]
    if high:
        print(f"high-flow points (15-34 sccm, R26), joint admissible geometries: eta {min(high):.3f} - {max(high):.3f}")
    manifest = build_manifest(
        "nitrogen_output_evidence", label="representative_chamber", validation_status="not_validated",
        inputs={"evidence": ev, "hdrs_aspects": HDRS_ASPECTS, "particles": PARTICLES, "seed": SEED, "k_atoms": k_atoms},
        outputs={"points": rows, "joint": joint, "eta_high_flow_joint": [min(high), max(high)] if high else None},
        sources=[Path(__file__), EVIDENCE, ROOT / "src/mbe_twin/aperture.py", ROOT / "src/mbe_twin/beam.py",
                 ROOT / "src/mbe_twin/crucible.py", ROOT / "data/parameters/gan_growth.json"],
        warnings=["eta is inferred under bracketed, unpublished geometry (throw, source angle, plate thickness)",
                  "Free-molecular plate model with uniform output, as in the layout studies; published plates may differ",
                  "Point R26-a's power assignment and R13-old's rate are approximate (see evidence file)"])
    print(f"Wrote {write_manifest(manifest, ROOT / 'results/nitrogen_output_evidence/manifest.json')}")


if __name__ == "__main__":
    main()
