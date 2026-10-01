"""Can each candidate nitrogen aim be mounted, adjusted and shuttered? Source-layout feasibility.

For each layout in data/design/design_envelope.json the chamber is populated with the ten
effusion cells (3 Ga, 3 Al, Si, Mg, 2 spare) on the common cell cone and the nitrogen plasma
source (mbe_twin.layout: bodies as solid cylinders from the lip to the mounting flange,
shutter blades on rotary arms, the holder lip and the heater/manipulator assembly). Ports:
- nitrogen on the cell cone (layouts A, B, R0): eleven ports round the cone, nitrogen at 0;
- nitrogen on a steeper port (C, D): the ten cells round the cone, nitrogen at 0 between the
  first and last cell; Ga cells on their own cone where the layout says so (C-Ga54).
Cells go round the cone as Ga, Al, Si, Ga, Al, Mg, Ga, Al, spare, spare, so the large Ga
bodies are spread out. The azimuth step between neighbours on the cone is proportional to the
sum of their body radii, so large bodies get more room.

Checks, all with the assumed dimensions of the envelope:
1. Clearance (m) between every pair of solids, as a certified lower bound: bodies as capsules,
   flanges and shutter blades as disks whose sampled distances are reduced by the samples'
   covering radius. Pairs: body/body, flange/flange, flange/body, flange/blade, blade/body over
   each blade's opening sweep, blade/blade with both shutters at every pair of sweep positions,
   and every solid against the holder/heater assembly (a capsule for the bodies). The swing
   side of each shutter (two choices per source) is chosen to maximize the smallest
   clearance (exhaustive over 2^11 combinations). A layout fails if any clearance is below
   the margin (5 mm).
2. Shadowing: rotation-averaged direct flux of the nitrogen plate and of each Ga cell (flat
   cos^n emitters of the lip radius; n = 1, and n = 4 for the plate) with and without the other
   solids in the growth state (Ga and N shutters open, the others closed) and with the holder
   lip; the largest loss inside the usable radius (94 mm) and at the holder opening.
3. Adjustment: the tilt between a port aimed at the wafer centre and the nitrogen aim (what a
   tilting adapter would have to supply if the port is not machined to the aim), and the aim
   point movement per 0.8 deg of tilt about the plate centre and about the mounting flange,
   over all tilt directions.

Usage: python scripts/layout_feasibility.py [--out results/layout_feasibility]
"""

import argparse
import itertools
import json
from dataclasses import replace
from pathlib import Path

import numpy as np

from mbe_twin.beam import HolderLip, rotation_averaged_flux
from mbe_twin.beam import DiskOccluder
from mbe_twin.layout import (SourcePort, cylinder_clearance, disk_to_cylinder_bounds, disk_to_disk_bounds,
                             holder_assembly, point_to_cylinder, shutter_sweep, wafer_frame)
from mbe_twin.manifest import build_manifest, write_manifest

ROOT = Path(__file__).resolve().parents[1]
ENVELOPE = ROOT / "data/design/design_envelope.json"
MARGIN = 0.005
CELL_ORDER = ("Ga", "Al", "Si_Mg_spare", "Ga", "Al", "Si_Mg_spare", "Ga", "Al", "Si_Mg_spare", "Si_Mg_spare")
CELL_LABELS = ("Ga1", "Al1", "Si", "Ga2", "Al2", "Mg", "Ga3", "Al3", "spare1", "spare2")
RHO = np.linspace(0.0, 0.099, 34)


def port_from(env, kind, name, polar, azimuth, offset=0.0, side=1):
    b = env["source_bodies"][kind]
    return SourcePort(name, polar_deg=polar, azimuth_deg=azimuth, throw=env["chamber"]["source_throw_m"]["value"],
                      aim_offset=offset, lip_radius=b["lip_radius_m"], body_radius=b["body_radius_m"],
                      body_length=b["body_length_m"], flange_radius=b["flange_radius_m"],
                      shutter_radius=b["shutter_radius_m"], shutter_standoff=b["shutter_standoff_m"],
                      shutter_arm=b["shutter_arm_m"], shutter_side=side)


def build_ports(env, layout):
    cone = env["chamber"]["cell_cone_polar_deg"]["value"]
    n = layout["n"]
    on_cone = abs(n["polar_deg"] - cone) <= 1.0
    radii = [env["source_bodies"][k]["body_radius_m"] for k in CELL_ORDER]
    ring = ([env["source_bodies"]["N_plasma"]["body_radius_m"]] if on_cone else []) + radii
    steps = np.array([ring[k] + ring[(k + 1) % len(ring)] for k in range(len(ring))])
    az = np.concatenate([[0.0], np.cumsum(360.0 * steps / steps.sum())[:-1]])
    if on_cone:
        az_cells = az[1:]
    else:  # nitrogen off the cone, midway in the gap between the last and the first cell
        az_cells = az + 0.5 * 360.0 * steps[-1] / steps.sum()
    ports = [port_from(env, "N_plasma", "N", n["polar_deg"], 0.0, n["aim_offset_mm"] / 1e3)]
    for kind, label, az in zip(CELL_ORDER, CELL_LABELS, az_cells):
        polar = layout["ga_port_deg"] if kind == "Ga" else cone
        ports.append(port_from(env, kind, label, polar, az))
    return ports


SWEEP_STEPS = 6
DISK_SAMPLING = {"n_r": 4, "n_phi": 36}
REFINED = {"n_r": 16, "n_phi": 128}   # covering radius 0.056 R: 2.6 mm on a 46 mm Ga blade


def flange_disk(port, wafer):
    """The mounting flange as a disk at the body's far end, normal to the source axis."""
    return DiskOccluder(tuple(port.flange_centre(wafer)), tuple(port.pose(wafer)[1]), port.flange_radius, name=f"{port.name} flange")


def pair_clearances(p, q, wafer, sampling=None):
    """Certified lower bound (m) on the clearance between ports p and q, for each pair of shutter sides (2 x 2).

    Solids: bodies (capsules: a lower bound), flanges and shutter blades (disks: sampled distance minus the
    samples' covering radius, mbe_twin.layout.disk_to_disk_bounds). Pairs: body/body, flange/flange,
    flange/body (both ways), flange/blade and blade/body over each blade's sweep, and blade/blade with both
    shutters at every pair of sweep positions (moving together or one at a time). Where the bound is below the
    margin but the sampled value is not, the combination is recomputed with REFINED sampling, so that a loose
    bound is not reported as a conflict. Also returns the body and flange gaps and the closest sampled value
    (an upper estimate of the same minimum)."""
    out, sampled = np.empty((2, 2)), np.empty((2, 2))
    body_gap = cylinder_clearance(p.body(wafer), q.body(wafer))
    for i, si in enumerate((1, -1)):
        for j, sj in enumerate((1, -1)):
            for smp in (sampling or DISK_SAMPLING, REFINED):
                lo, hi, flange_lo = _combo_gaps(replace(p, shutter_side=si), replace(q, shutter_side=sj), wafer, smp, body_gap)
                if lo >= MARGIN or hi < MARGIN:
                    break
            out[i, j], sampled[i, j] = lo, hi
    return out, body_gap, flange_lo, sampled


def _combo_gaps(pp, qq, wafer, smp, body_gap):
    fp, fq = flange_disk(pp, wafer), flange_disk(qq, wafer)
    gaps = [disk_to_disk_bounds(fp, fq, **smp), disk_to_cylinder_bounds(fp, qq.body(wafer), **smp),
            disk_to_cylinder_bounds(fq, pp.body(wafer), **smp)]
    flange_lo = min(g[0] for g in gaps)
    sw_p, sw_q = shutter_sweep(pp, wafer, steps=SWEEP_STEPS), shutter_sweep(qq, wafer, steps=SWEEP_STEPS)
    for blades, body, fl in ((sw_p, qq.body(wafer), fq), (sw_q, pp.body(wafer), fp)):
        for blade in blades:
            gaps.append(disk_to_cylinder_bounds(blade, body, **smp))
            gaps.append(disk_to_disk_bounds(blade, fl, **smp))
    for bp in sw_p:
        for bq in sw_q:
            gaps.append(disk_to_disk_bounds(bp, bq, **smp))
    return min([body_gap] + [g[0] for g in gaps]), min([body_gap] + [g[1] for g in gaps]), flange_lo


def holder_clearance(p, wafer, assembly):
    """Certified lower bound on the clearance of the port's blade (over its sweep) and body to the holder assembly."""
    gaps = [disk_to_cylinder_bounds(b, assembly, **DISK_SAMPLING)[0] for b in shutter_sweep(p, wafer, steps=SWEEP_STEPS)]
    # body: exact distance from points on its axis to the solid assembly, less the body radius and half the
    # point spacing (a certified bound; a capsule would round the 130 mm assembly's face and over-state the risk)
    pos, a = p.pose(wafer)
    n_ax = 61
    axis_pts = pos[None, :] - np.linspace(0.0, p.body_length, n_ax)[:, None] * a
    gaps.append(float(point_to_cylinder(axis_pts, assembly).min()) - p.body_radius - 0.5 * p.body_length / (n_ax - 1))
    gaps.append(disk_to_cylinder_bounds(flange_disk(p, wafer), assembly, **DISK_SAMPLING)[0])
    return min(gaps)


def best_sides(ports, table):
    n = len(ports)
    best = (-np.inf, None)
    for sides in itertools.product((0, 1), repeat=n):
        worst = min(table[(i, j)][sides[i], sides[j]] for i in range(n) for j in range(i + 1, n))
        if worst > best[0]:
            best = (worst, sides)
    return best


def shadow_loss(port, others, wafer, lip, n_cos, usable, attribute=True):
    src = [port.beam_source(wafer, cosine_exponent=n_cos, radial_nodes=4, azimuthal_nodes=12)]
    free = rotation_averaged_flux(src, wafer, RHO, n_angles=72)
    with_lip = rotation_averaged_flux(src, wafer, RHO, n_angles=72, occluders=(lip,))
    full = rotation_averaged_flux(src, wafer, RHO, n_angles=72, occluders=(lip, *others))
    inside = RHO <= usable + 1e-12
    edge = RHO < lip.inner_radius - 1e-9  # exposed wafer only
    culprits = {}
    if attribute and np.max(1 - full[inside] / with_lip[inside]) > 1e-4:
        for o in others:
            f = rotation_averaged_flux(src, wafer, RHO, n_angles=72, occluders=(lip, o))
            loss = float(100 * np.max(1 - f[inside] / with_lip[inside]))
            if loss > 0.01:
                culprits[o.name] = loss
    return {"culprits_pct": culprits,"lip_loss_usable_pct": float(100 * np.max(1 - with_lip[inside] / free[inside])),
            "lip_loss_opening_pct": float(100 * np.max(1 - with_lip[edge] / free[edge])),
            "other_solids_loss_usable_pct": float(100 * np.max(1 - full[inside] / with_lip[inside])),
            "ratio_with_lip": (with_lip / free).tolist(), "ratio_all": (full / free).tolist()}


def adjustment(port, wafer, pivots):
    pos, a = port.pose(wafer)
    centre_axis = -pos / np.linalg.norm(pos)
    required = float(np.degrees(np.arccos(np.clip(centre_axis @ a, -1.0, 1.0))))
    a0, out, side = port.frame(wafer)
    res = {"tilt_from_centre_pointing_port_deg": required}
    for name, back in pivots.items():
        p = replace(port, pivot_back=back)
        aim0 = p.aim_point(wafer)
        shifts = []
        for psi in np.radians(np.arange(0.0, 360.0, 15.0)):
            d = np.cos(psi) * out + np.sin(psi) * side
            shifts.append(np.linalg.norm(p.tilted(d, np.radians(0.8)).aim_point(wafer) - aim0))
        res[f"aim_shift_per_0.8deg_mm_{name}"] = [1e3 * float(min(shifts)), 1e3 * float(max(shifts))]
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default="results/layout_feasibility")
    ap.add_argument("--layouts", nargs="+", help="subset of the envelope's layouts")
    args = ap.parse_args()
    env = json.loads(ENVELOPE.read_text(encoding="utf-8"))
    wafer = wafer_frame()
    usable = env["wafer_and_mask"]["usable_radius_m"]["value"]
    lip_h = env["wafer_and_mask"]["holder_lip_height_m"]["value"]
    openings = env["wafer_and_mask"]["holder_opening_radius_m"]["value"]
    ha = env["chamber"]["holder_assembly"]
    assembly = holder_assembly(wafer, ha["radius_m"], ha["depth_m"], lip_h)
    pivots = env["pointing_and_adjustment"]["tilt_pivot_behind_plate_m"]["value"]
    names = args.layouts or list(env["layouts"])
    unknown = [n for n in names if n not in env["layouts"]]
    if unknown:
        raise SystemExit(f"layout_feasibility: unknown layouts {unknown}")
    rows = []
    for name in names:
        layout = env["layouts"][name]
        ports = build_ports(env, layout)
        table, body_gaps, flange_gaps, sampled = {}, {}, {}, {}
        for i, j in itertools.combinations(range(len(ports)), 2):
            table[(i, j)], body_gaps[(i, j)], flange_gaps[(i, j)], sampled[(i, j)] = pair_clearances(ports[i], ports[j], wafer)
        worst, sides = best_sides(ports, table)
        ports = [replace(p, shutter_side=(1, -1)[s]) for p, s in zip(ports, sides)]
        holder = {p.name: holder_clearance(p, wafer, assembly) for p in ports}
        pairs = sorted(((float(table[k][sides[k[0]], sides[k[1]]]), ports[k[0]].name, ports[k[1]].name) for k in table))
        opening = openings["3 mm overlap"] if layout["heater"] == "3 zones" else openings["1 mm overlap"]
        lip = HolderLip(center=(0.0, 0.0, 0.0), normal=tuple(wafer.normal), inner_radius=opening, height=lip_h)
        growth_open = {"N", "Ga1", "Ga2", "Ga3"}
        solids = {p.name: [p.body(wafer), p.shutter(wafer) if p.name in growth_open else p.shutter(wafer, 0.0)]
                  for p in ports}

        def others(name):
            return [s for k, v in solids.items() if k != name for s in v] + [solids[name][1]]  # own open blade too

        shadows = {"N": {f"cos^{n}": shadow_loss(ports[0], others("N"), wafer, lip, n, usable) for n in (1, 4)}}
        for p in ports:
            if p.name.startswith("Ga"):
                shadows[p.name] = {"cos^1": shadow_loss(p, others(p.name), wafer, lip, 1, usable)}
        adj = adjustment(ports[0], wafer, pivots)
        # innermost radius a lip of height h shadows (straight-ahead estimate h tan(port angle)), both openings
        reach = {f"{k} {h * 1e3:.0f} mm lip": {src: 1e3 * (o - h * np.tan(np.radians(ang))) for src, ang in
                                                (("N", layout["n"]["polar_deg"]), ("Ga", layout["ga_port_deg"]))}
                 for k, o in openings.items() for h in (0.001, 0.002, 0.003)}
        flange_pos = {p.name: [float(np.hypot(*p.flange_centre(wafer)[:2])), float(-p.flange_centre(wafer)[2])] for p in ports}
        ok = worst >= MARGIN and min(holder.values()) >= MARGIN
        worst_sampled = min(sampled[k][sides[k[0]], sides[k[1]]] for k in sampled)
        row = {"layout": name, "feasible_at_margin": bool(ok), "min_clearance_m": float(worst),
               "min_clearance_sampled_m": float(worst_sampled), "clearance_is": "certified lower bound (sampled value: upper estimate)",
               "closest_pairs": pairs[:5], "holder_clearance_m": holder, "shutter_sides": {p.name: p.shutter_side for p in ports},
               "port_azimuths_deg": {p.name: p.azimuth_deg for p in ports}, "port_polar_deg": {p.name: p.polar_deg for p in ports},
               "flange_centre_radial_and_depth_m": flange_pos, "holder_opening_m": opening,
               "shadowing": shadows, "lip_shadow_inner_edge_mm": reach, "nitrogen_adjustment": adj, "rho_m": RHO.tolist()}
        rows.append(row)
        print(f"\n{name}: {'NO CONFLICT FOUND' if ok else 'CONFLICT'} at {1e3 * MARGIN:.0f} mm margin; smallest clearance "
              f"{1e3 * worst:.1f} mm certified ({1e3 * worst_sampled:.1f} sampled; {pairs[0][1]}-{pairs[0][2]}); holder/heater assembly {1e3 * min(holder.values()):.0f} mm "
              f"({min(holder, key=holder.get)})", flush=True)
        for g, s in shadows.items():
            for k, v in s.items():
                print(f"  {g:4s} {k}: holder lip loss {v['lip_loss_usable_pct']:.2f} % inside {1e3 * usable:.0f} mm "
                      f"({v['lip_loss_opening_pct']:.1f} % at the {1e3 * opening:.0f} mm opening); other solids "
                      f"{v['other_solids_loss_usable_pct']:.3f} %" + (f" {v['culprits_pct']}" if v["culprits_pct"] else ""))
        print(f"  N tilt from a centre-pointing port: {adj['tilt_from_centre_pointing_port_deg']:.1f} deg; aim shift per 0.8 deg "
              + ", ".join(f"{k.split('_mm_')[1]} pivot {v[0]:.1f}-{v[1]:.1f} mm" for k, v in adj.items() if k.startswith("aim")))
        fl = flange_pos["N"]
        print(f"  N flange centre at radius {1e3 * fl[0]:.0f} mm, {1e3 * fl[1]:.0f} mm below the wafer plane")

    manifest = build_manifest(
        "layout_feasibility", label="representative_chamber", validation_status="not_validated",
        inputs={"envelope": json.loads(ENVELOPE.read_text(encoding="utf-8")), "margin_m": MARGIN, "cell_order": CELL_LABELS,
                "layouts": names},
        outputs={"rows": rows},
        sources=[Path(__file__), ROOT / "src/mbe_twin/layout.py", ROOT / "src/mbe_twin/beam.py", ENVELOPE],
        warnings=["Simplified solids with assumed dimensions; no chamber drawing, cryoshroud, RHEED or pyrometer lines of sight",
                  "Clearances are certified lower bounds for the modelled solids (capsule bodies, disk flanges and blades); "
                  "real cell, shutter and flange drawings may differ",
                  "Shadowing with flat cos^n emitters; the beam models of the comparison are not used here"])
    print(f"Wrote {write_manifest(manifest, Path(args.out) / 'manifest.json')}")


if __name__ == "__main__":
    main()
