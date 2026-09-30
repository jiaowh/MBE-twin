"""Digitize measured profiles from R07 (Gericke et al., Vacuum 42 (1991) 1209).

The PDF is a scan; figures are rasterised at 400 dpi with PyMuPDF. Axes are calibrated from
the detected axis lines and tick marks, and curves are traced column by column as centres of
dark pixel runs. Where the curves of one panel are separated, they are assigned in vertical
order; where they merge (the central plateau), the merged run is shared by all of them.
Columns with an ambiguous number of runs are skipped. The authors' curves are averaged fits
to microbalance scans (their Sec. 3), not raw points.

Output: data/benchmarks/r07_gericke1991.json with page/figure locators, calibration, method,
estimated digitization error and the source PDF hash.

Usage: python scripts/digitize_r07.py [--check-images DIR]
"""

import argparse
import hashlib
import json
from pathlib import Path

import fitz  # PyMuPDF
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
PDF = ROOT / "ref/reference/R07_Gericke_1991_effusion_flux_distribution.pdf"
OUT = ROOT / "data/benchmarks/r07_gericke1991.json"
DPI = 400


def render(page_index):
    pix = fitz.open(PDF)[page_index].get_pixmap(dpi=DPI, colorspace=fitz.csGRAY)
    return np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width) < 128


def runs(column):
    """Centres of consecutive True runs in a boolean column."""
    idx = np.flatnonzero(column)
    if idx.size == 0:
        return []
    splits = np.flatnonzero(np.diff(idx) > 1) + 1
    return [float(g.mean()) for g in np.split(idx, splits)]


def calibrate(dark, box, x_tick_step, y_tick_step, x_zero_hint, y_axis_value=0.0):
    """Axis calibration from tick marks inside box = (x0, y0, x1, y1) in page pixels.

    The x axis line sits at y = y_axis_value; ticks are assumed equally spaced.
    """
    x0, y0, x1, y1 = box
    sub = dark[y0:y1, x0:x1]
    axis_row = y0 + int(np.argmax(sub.sum(axis=1)))
    axis_col = x0 + int(np.argmax(sub.sum(axis=0)))
    # x ticks protrude above the x axis; y ticks protrude right of the y axis.
    band = dark[axis_row - 14:axis_row - 5, axis_col + 20:x1].any(axis=0)
    xt = np.array(runs(band)) + axis_col + 20
    band = dark[y0:axis_row - 5, axis_col + 5:axis_col + 14].any(axis=1)
    yt = np.array(runs(band)) + y0
    spacing = np.median(np.diff(xt))
    k = np.round((xt - xt[np.argmin(abs(xt - x_zero_hint))]) / spacing)
    ax, bx = np.polyfit(k * x_tick_step, xt, 1)
    ky = np.round((axis_row - yt) / np.median(np.diff(np.sort(axis_row - yt))))
    yv = y_axis_value + np.concatenate(([0.0], ky * y_tick_step))
    ay, by = np.polyfit(yv, np.concatenate(([axis_row], yt)), 1)
    resid_x = np.max(abs(np.polyval([ax, bx], k * x_tick_step) - xt))
    resid_y = np.max(abs(np.polyval([ay, by], yv) - np.concatenate(([axis_row], yt))))
    return {"axis_row": axis_row, "axis_col": axis_col, "px_per_x_unit": ax, "x_offset_px": bx,
            "px_per_y_unit": ay, "y_offset_px": by, "n_x_ticks": int(len(xt)),
            "n_y_ticks": int(len(yt)), "max_tick_residual_px": float(max(resid_x, resid_y))}


def calibrate_floating(dark, y_box, y_tick_values, x_box, x_tick_step, x_zero_hint,
                       x_px_per_unit_hint):
    """Calibration for panels whose y axis does not meet the x axis (R07 Fig. 7).

    y_box holds the panel's y axis; its ticks protrude to the right and are assigned
    y_tick_values from top to bottom. x_box holds a (possibly shared) x axis whose major ticks
    protrude upwards every x_tick_step; tick candidates off that grid (lines crossing the
    axis) are rejected. x_px_per_unit_hint only needs to identify the outermost tick's index.
    """
    x0, y0, x1, y1 = y_box
    axis_col = x0 + int(np.argmax(dark[y0:y1, x0:x1].sum(axis=0)))
    yt = np.array(runs(dark[y0:y1, axis_col + 5:axis_col + 14].any(axis=1))) + y0
    if len(yt) != len(y_tick_values):
        raise ValueError(f"found {len(yt)} y ticks, expected {len(y_tick_values)}")
    ay, by = np.polyfit(y_tick_values, yt, 1)
    resid_y = np.max(abs(np.polyval([ay, by], y_tick_values) - yt))

    x0, y0, x1, y1 = x_box
    axis_row = y0 + int(np.argmax(dark[y0:y1, x0:x1].sum(axis=1)))
    cand = np.array(runs(dark[axis_row - 14:axis_row - 5, x0:x1].any(axis=0))) + x0
    zero = cand[np.argmin(abs(cand - x_zero_hint))]
    outer = cand[np.argmax(abs(cand - zero))]
    nominal = (outer - zero) / round((outer - zero) / (x_px_per_unit_hint * x_tick_step))  # px per major tick
    k = (cand - zero) / nominal
    keep = abs(k - np.round(k)) * nominal < 4.0
    xt, k = cand[keep], np.round(k[keep])
    ax, bx = np.polyfit(k * x_tick_step, xt, 1)
    resid_x = np.max(abs(np.polyval([ax, bx], k * x_tick_step) - xt))
    return {"axis_row": axis_row, "axis_col": axis_col, "px_per_x_unit": ax, "x_offset_px": bx,
            "px_per_y_unit": ay, "y_offset_px": by, "n_x_ticks": int(len(xt)),
            "n_x_rejected": int((~keep).sum()), "n_y_ticks": int(len(yt)),
            "max_tick_residual_px": float(max(resid_x, resid_y))}


def remove_vertical_dashes(mask, min_length, min_component_px=200):
    """Remove near-vertical dashes (construction lines) that are at least min_length px tall.

    Slanted dashes leave thin edge slivers after the opening; components smaller than
    min_component_px (far smaller than a traced curve) are dropped as well.
    """
    from scipy import ndimage

    dashes = ndimage.binary_opening(mask, structure=np.ones((min_length, 1), bool))
    rest = mask & ~ndimage.binary_dilation(dashes, structure=np.ones((3, 3), bool))
    labels, n = ndimage.label(rest, structure=np.ones((3, 3)))
    sizes = ndimage.sum(rest, labels, index=np.arange(1, n + 1))
    return np.isin(labels, 1 + np.flatnonzero(sizes >= min_component_px))


def _mask(dark, boxes):
    m = dark.copy()
    for x0, y0, x1, y1 in boxes:
        m[y0:y1, x0:x1] = False
    return m


def split_dashed(mask, y_range, x_px, min_solid_px):
    """Separate a solid curve (large connected components) from a dashed one (short dashes)."""
    from scipy import ndimage

    region = np.zeros_like(mask)
    region[y_range[0]:y_range[1], x_px[0]:x_px[1]] = mask[y_range[0]:y_range[1], x_px[0]:x_px[1]]
    labels, n = ndimage.label(region, structure=np.ones((3, 3)))
    sizes = ndimage.sum(region, labels, index=np.arange(1, n + 1))
    solid = np.isin(labels, 1 + np.flatnonzero(sizes >= min_solid_px))
    dashed = np.isin(labels, 1 + np.flatnonzero((sizes >= 15) & (sizes < min_solid_px)))
    return solid, dashed


def trace(mask, cal, x_range, y_range_px, n_curves):
    """Trace n_curves curves; returns x values and an (n_curves, N) array.

    Columns with n_curves runs are assigned in vertical order, a single run is shared by all
    curves (merged plateau), and other columns are skipped.
    """
    xs, ys = [], []
    lo_px = int(cal["x_offset_px"] + cal["px_per_x_unit"] * x_range[0])
    hi_px = int(cal["x_offset_px"] + cal["px_per_x_unit"] * x_range[1])
    for col in range(lo_px, hi_px + 1, 2):
        centres = [c + y_range_px[0] for c in runs(mask[y_range_px[0]:y_range_px[1], col])]
        if len(centres) == n_curves:
            vals = sorted(centres)
        elif len(centres) == 1:
            vals = centres * n_curves
        else:
            continue
        xs.append((col - cal["x_offset_px"]) / cal["px_per_x_unit"])
        ys.append([(v - cal["y_offset_px"]) / cal["px_per_y_unit"] for v in vals])
    return np.array(xs), np.array(ys).T


PANELS = {
    "fig3": {
        "page": 2, "locator": "Fig. 3, p. 1210",
        "caption": "Normalized thickness, conical crucible, filling levels L/D = 0.5, 1, 2, 4; "
                   "T = 573 C (p_Bi = 8e-2 Pa), R = 115 mm, alpha = 0",
        "box": (1820, 280, 2980, 1330), "x_zero_hint": 2395, "x_tick_step": 10.0,
        "y_tick_step": 0.1, "y_axis_value": 0.0, "trace_y": (320, 1270), "x_range": (-48.0, 48.0),
        "exclude_boxes": [(2840, 280, 2990, 1300)], "mode": "ordered",
        "curves": ["L/D=0.5", "L/D=1", "L/D=2", "L/D=4"],
    },
    "fig4": {
        "page": 2, "locator": "Fig. 4, p. 1210",
        "caption": "Normalized thickness, conical crucible, L/D = 4, T = 723, 666, 572 C; centre "
                   "deposition rates 11.0, 3.5, 0.35 A/s; R = 115 mm, alpha = 0",
        "box": (1780, 2650, 2900, 3700), "x_zero_hint": 2372, "x_tick_step": 10.0,
        "y_tick_step": 0.1, "y_axis_value": 0.0, "trace_y": (2700, 3650), "x_range": (-47.0, 47.0),
        "exclude_boxes": [(2100, 2975, 2665, 3045), (1815, 2960, 1922, 3420)], "mode": "ordered",
        "curves": ["11.0 A/s", "3.5 A/s", "0.35 A/s"],
    },
    "fig5_top": {
        "page": 3, "locator": "Fig. 5 (upper panel), p. 1211",
        "caption": "Normalized thickness, conical crucible inclined alpha = 60 deg, L/D = 4, "
                   "T = 499 C, 0.07 A/s; azimuth tau = 0 (solid) and 90 deg (dashed); R = 115 mm",
        "box": (500, 250, 1350, 720), "x_zero_hint": 923, "x_tick_step": 20.0,
        "y_tick_step": 0.2, "y_axis_value": 0.4, "trace_y": (290, 686), "x_range": (-47.0, 47.0),
        "exclude_boxes": [(770, 470, 1080, 545), (690, 570, 1130, 635)], "mode": "solid_dashed",
        "curves": ["tau=0", "tau=90"],
    },
    "fig5_bottom": {
        "page": 3, "locator": "Fig. 5 (lower panel), p. 1211",
        "caption": "As upper panel at T = 746 C, 26.5 A/s",
        "box": (500, 900, 1350, 1360), "x_zero_hint": 923, "x_tick_step": 20.0,
        "y_tick_step": 0.2, "y_axis_value": 0.4, "trace_y": (930, 1325), "x_range": (-47.0, 47.0),
        "exclude_boxes": [(770, 1095, 1095, 1162), (695, 1205, 1140, 1270)], "mode": "solid_dashed",
        "curves": ["tau=0", "tau=90"],
    },
    # Fig. 7: two stacked panels with floating y axes (0.6-1.0) and one x axis under the lower
    # panel. The upper panel is read with that shared x axis: the figure draws both panels
    # over one mm scale and joins the plateau edges with construction lines (dashed), which
    # are removed before tracing.
    "fig7_265": {
        "page": 3, "locator": "Fig. 7 (upper panel, 265 mm), p. 1211",
        "caption": "Normalized thickness, conical crucible, L/D = 2, T = 593 C, R = 265 mm, centre "
                   "rate 1.9 A/s, alpha = 0; x read from the lower panel's axis (shared scale)",
        "mode": "floating", "y_box": (2000, 300, 2100, 560),
        "y_tick_values": [1.0, 0.9, 0.8, 0.7, 0.6], "x_box": (2050, 1250, 2600, 1360),
        "x_tick_step": 20.0, "x_zero_hint": 2327, "x_px_per_unit_hint": 4.7,
        "trace_y": (300, 560), "x_range": (-48.0, 48.0), "exclude_boxes": [],
        "curves": ["R=265 mm"],
    },
    "fig7_115": {
        "page": 3, "locator": "Fig. 7 (lower panel, 115 mm), p. 1211",
        "caption": "Normalized thickness, conical crucible, L/D = 2, T = 593 C, R = 115 mm, centre "
                   "rate 10.0 A/s, alpha = 0",
        "mode": "floating", "y_box": (2000, 1010, 2100, 1270),
        "y_tick_values": [1.0, 0.9, 0.8, 0.7, 0.6], "x_box": (2050, 1250, 2600, 1360),
        "x_tick_step": 20.0, "x_zero_hint": 2327, "x_px_per_unit_hint": 4.7,
        "trace_y": (1010, 1292), "x_range": (-48.0, 48.0), "exclude_boxes": [],
        "curves": ["R=115 mm"],
    },
}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--only", nargs="*", default=list(PANELS))
    args = ap.parse_args()
    pages = {}
    record = {"source_id": "R07", "source_pdf": str(PDF.relative_to(ROOT)).replace("\\", "/"),
              "source_sha256": hashlib.sha256(PDF.read_bytes()).hexdigest(),
              "provenance": "digitized", "dpi": DPI, "script": "scripts/digitize_r07.py",
              "units": {"x": "mm from the centre, in a plane normal to the crucible axis",
                        "y": "thickness normalized to the centre"},
              "notes": "Curves are the authors' averaged fits. Digitization error is estimated "
                       "from line half-width and tick residuals; left/right asymmetry is kept.",
              "panels": {}}
    for name in args.only:
        p = PANELS[name]
        dark = pages.setdefault(p["page"], render(p["page"] - 1))
        if p["mode"] == "floating":
            cal = calibrate_floating(dark, p["y_box"], p["y_tick_values"], p["x_box"],
                                     p["x_tick_step"], p["x_zero_hint"], p["x_px_per_unit_hint"])
        else:
            cal = calibrate(dark, p["box"], p["x_tick_step"], p["y_tick_step"], p["x_zero_hint"],
                            p["y_axis_value"])
        mask = _mask(dark, p["exclude_boxes"])
        # Keep the axes out of the traced region.
        mask[:, :cal["axis_col"] + 16] = False
        mask[cal["axis_row"] - 16:, :] = False
        curves = {}
        if p["mode"] == "ordered":
            xs, ys = trace(mask, cal, p["x_range"], p["trace_y"], len(p["curves"]))
            curves = {c: (xs, y) for c, y in zip(p["curves"], ys)}
        elif p["mode"] == "floating":
            mask = remove_vertical_dashes(mask, min_length=21)
            xs, ys = trace(mask, cal, p["x_range"], p["trace_y"], 1)
            curves[p["curves"][0]] = (xs, ys[0])
        else:
            x_px = (int(cal["x_offset_px"] + cal["px_per_x_unit"] * p["x_range"][0]),
                    int(cal["x_offset_px"] + cal["px_per_x_unit"] * p["x_range"][1]))
            solid, dashed = split_dashed(mask, p["trace_y"], x_px, min_solid_px=800)
            for c, m in zip(p["curves"], (solid, dashed)):
                xs, ys = trace(m, cal, p["x_range"], p["trace_y"], 1)
                curves[c] = (xs, ys[0])
        err = (3.0 + cal["max_tick_residual_px"]) / abs(cal["px_per_y_unit"])
        record["panels"][name] = {
            "locator": p["locator"], "caption": p["caption"], "calibration": cal,
            "estimated_error_y": round(err, 4),
            "curves": {c: {"x_mm": np.round(x, 3).tolist(), "y": np.round(y, 4).tolist()}
                       for c, (x, y) in curves.items()}}
        counts = ", ".join(f"{c}: {len(x)}" for c, (x, _) in curves.items())
        print(f"{name}: ticks x/y {cal['n_x_ticks']}/{cal['n_y_ticks']}, residual "
              f"{cal['max_tick_residual_px']:.1f} px, {cal['px_per_x_unit']:.2f} px/mm, "
              f"error ~{err:.3f}; points {counts}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=1) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
