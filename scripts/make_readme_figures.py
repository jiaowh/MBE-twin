"""Draw the README figures (docs/figures/*.png) from the recorded run summaries.

Schematics (chamber, level melt) are illustrations, not to scale. Data figures read only
data/runs/ records, so they change only when those records change.

Usage: python scripts/make_readme_figures.py
"""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Circle, FancyArrowPatch, Polygon, Rectangle  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/figures"
RUNS = ROOT / "data/runs"
BLUE, ORANGE, GREEN, GREY, RED = "#1f77b4", "#ff7f0e", "#2ca02c", "#7f7f7f", "#d62728"
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                     "savefig.dpi": 150, "savefig.bbox": "tight"})


def load(rel):
    return json.loads((RUNS / rel).read_text(encoding="utf-8"))["outputs"]


def arrow(ax, a, b, **kw):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle="-|>", mutation_scale=12, **kw))


def chamber():
    """Side view: wafer at the top facing down, sources on a ring below it."""
    fig, ax = plt.subplots(figsize=(7.2, 5.2))
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Circle((0, 0), 420, fill=False, lw=2, ec=GREY))
    ax.text(-300, -330, "vacuum chamber\n(cold walls)", color=GREY, ha="center")
    ax.add_patch(Rectangle((-100, 120), 200, 8, fc="#555"))
    ax.text(125, 124, "200 mm wafer\n(spins, faces down)", va="center")
    ax.add_patch(Rectangle((-110, 140), 220, 30, fc="#f4b183", ec="#c55a11"))
    ax.text(0, 155, "heater", ha="center", va="center")
    ax.annotate("", xy=(40, 185), xytext=(-40, 185),
                arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=-0.5"))
    ax.text(0, 205, "rotation", ha="center")
    for ang, label, col in [(-46, "Ga effusion cell", BLUE), (46, "N plasma source", GREEN)]:
        t = np.radians(ang)
        d = np.array([np.sin(t), -np.cos(t)])
        p = np.array([0, 124]) + 350 * d
        perp = np.array([d[1], -d[0]])
        body = [p + 22 * perp, p - 22 * perp, p - 22 * perp + 90 * d, p + 22 * perp + 90 * d]
        ax.add_patch(Polygon(body, fc=col, alpha=0.8))
        cone = [p, np.array([-100, 120]), np.array([100, 120])]
        ax.add_patch(Polygon(cone, fc=col, alpha=0.12, ec="none"))
        ax.text(*(p + 130 * d), label, ha="center", va="center", color=col, weight="bold")
    ax.plot([0, 0], [124, -250], ls=":", c=GREY)
    t = np.radians(-46)
    ax.plot([0, 350 * np.sin(t)], [124, 124 - 350 * np.cos(t)], ls="--", c=BLUE, lw=1)
    arc = np.radians(np.linspace(-90, -90 - 46, 30))
    ax.plot(90 * np.cos(arc), 124 + 90 * np.sin(arc), c=GREY)
    ax.text(-45, 5, "46°", color=GREY, ha="center")
    ax.text(-165, -20, "350 mm", color=BLUE, rotation=44, ha="center")
    ax.set_xlim(-440, 440)
    ax.set_ylim(-440, 440)
    fig.savefig(OUT / "chamber.png")
    plt.close(fig)


def clip_below(poly, y0):
    """Part of a convex polygon with y <= y0 (Sutherland-Hodgman, one edge)."""
    out = []
    for i, p in enumerate(poly):
        q = poly[(i + 1) % len(poly)]
        pin, qin = p[1] <= y0, q[1] <= y0
        if pin:
            out.append(p)
        if pin != qin:
            s = (y0 - p[1]) / (q[1] - p[1])
            out.append(p + s * (q - p))
    return out


def level_melt():
    """A tilted cylindrical crucible holds a level melt: full cups spill, empty ones sit deep."""
    R, L, tilt = 35.75, 170.0, np.radians(46)
    a = np.array([np.sin(tilt), np.cos(tilt)])   # axis, lip end up toward the wafer
    n = np.array([np.cos(tilt), -np.sin(tilt)])  # across the bore
    lip = np.zeros(2)
    cup = [lip + R * n, lip - R * n, lip - R * n - L * a, lip + R * n - L * a]
    fig, axes = plt.subplots(1, 3, figsize=(9, 3.6))
    cases = [(25, "too full: spills over the lip", RED), (40, "fresh charge (40 mm)", BLUE),
             (120, "nearly empty (120 mm)", BLUE)]
    for ax, (recess, title, col) in zip(axes, cases):
        ax.set_aspect("equal")
        ax.axis("off")
        y0 = (lip - recess * a)[1]
        melt = clip_below(cup, y0)
        ax.add_patch(Polygon(melt, fc="#b4c7e7", ec="none"))
        ax.add_patch(Polygon(cup, fill=False, lw=2))
        ax.plot([-80, 80], [y0, y0], ls="--", c=col, lw=1)
        if recess < R * np.tan(tilt):
            low = lip + R * n  # the lower lip corner: the level melt is above it
            ax.plot(*low, "o", c=RED)
            arrow(ax, low, low + np.array([15, -30]), color=RED)
        beam_end = lip + 70 * a
        arrow(ax, lip, beam_end, color=ORANGE, lw=1.5)
        ax.text(*(beam_end + np.array([4, 0])), "beam\nto wafer", color=ORANGE, fontsize=8)
        ax.set_title(title, fontsize=10, color=col)
        ax.set_xlim(-160, 110)
        ax.set_ylim(-150, 70)
    fig.suptitle("Crucible tilted 46°, liquid gallium stays level (schematic; recess measured "
                 "along the axis)", fontsize=10)
    fig.savefig(OUT / "level_melt.png")
    plt.close(fig)


def r07():
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.4), sharey=True)
    for ax, case in zip(axes, ["0.35", "3.5", "11"]):
        o = load(f"sparta_r07/uq2_batch/{case}_base.json")
        x = np.array(o["x_mm"])
        fm = np.array(o["free_molecular_flux"])
        ax.plot(x, o["r07_profile"], "k-", lw=2, label="measured (1991)")
        ax.errorbar(x, o["profile"], yerr=o["profile_stderr"], fmt="o", ms=3, c=BLUE,
                    label="model with collisions")
        ax.plot(x, fm / fm[0], "--", c=ORANGE, label="model without collisions")
        ax.set_title(f"{case} Å/s  (shape error {100 * o['rms_vs_r07']:.1f} % vs "
                     f"{100 * o['rms_vs_r07_free_molecular']:.0f} %)", fontsize=9)
        ax.set_xlabel("distance from centre (mm)")
    axes[0].set_ylabel("deposit, relative to centre")
    axes[0].legend(fontsize=8, frameon=False)
    fig.suptitle("Bismuth test (R07): faster evaporation narrows the spray; only the collision "
                 "model follows it", fontsize=10)
    fig.savefig(OUT / "r07_validation.png")
    plt.close(fig)


def ga_fill():
    fills = [40, 70, 120]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3.8))
    for f, col in zip(fills, [GREEN, ORANGE, RED]):
        o = load(f"sparta_ga/ga_batch/fill{f:03d}_d8.json")
        r = np.array(o["r_mm"])
        y = np.array(o["dsmc_flux"])
        e = np.array(o["dsmc_flux_stderr"])
        m = np.mean(y)
        ax1.errorbar(r, y / m, yerr=e / m, fmt="o-", ms=3, c=col, label=f"{f} mm recess")
    ax1.set_xlabel("radius on wafer (mm)")
    ax1.set_ylabel("Ga arrival, relative to wafer mean")
    ax1.set_title("Radial Ga profile at 46° (atom size 8 Å)", fontsize=10)
    ax1.legend(frameon=False, fontsize=8)
    fm = [load(f"sparta_ga/ga_batch/fill{f:03d}_d8.json")["metrics_free_molecular"]
          ["range_over_mean_pct"] for f in fills]
    ax2.plot(fills, fm, "k--o", label="no collisions")
    for d, col in [("2.5", GREEN), ("5.68", BLUE), ("8", RED)]:
        vals, errs = [], []
        for f in fills:
            o = load(f"sparta_ga/ga_batch/fill{f:03d}_d{d}.json")
            vals.append(o["metrics_dsmc"]["range_over_mean_pct"])
            errs.append(o["metrics_dsmc_stderr"]["bootstrap"]["range_over_mean_pct"])
        ax2.errorbar(fills, vals, yerr=errs, fmt="o-", c=col, capsize=3, label=f"atom size {d} Å")
    ax2.set_xlabel("how far the melt sits below the lip (mm)\n(fuller cup  ←  →  emptier cup)")
    ax2.set_ylabel("unevenness, range/mean (%)")
    ax2.set_title("Unevenness grows as the cup empties", fontsize=10)
    ax2.legend(frameon=False, fontsize=8)
    fig.savefig(OUT / "ga_fill.png")
    plt.close(fig)


def ga_angle():
    angles = {40: [46, 48], 70: [46, 50, 54, 58], 120: [46, 50, 54, 58, 62]}
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.axvspan(48.2, 64, color=RED, alpha=0.07)
    ax.text(48.5, 10.2, "a fresh 40 mm charge\nspills beyond 48.2°", color=RED, fontsize=8)
    for (f, angs), col in zip(angles.items(), [GREEN, ORANGE, RED]):
        vals, errs, fms = [], [], []
        for a in angs:
            rel = (f"sparta_ga/ga_batch/fill{f:03d}_d8.json" if a == 46
                   else f"sparta_ga/ga_angle/fill{f:03d}_d8_{a}deg.json")
            o = load(rel)
            vals.append(o["metrics_dsmc"]["range_over_mean_pct"])
            errs.append(o["metrics_dsmc_stderr"]["bootstrap"]["range_over_mean_pct"])
            fms.append(o["metrics_free_molecular"]["range_over_mean_pct"])
        ax.errorbar(angs, vals, yerr=errs, fmt="o-", c=col, capsize=3, label=f"{f} mm, with collisions")
        ax.plot(angs, fms, ":", c=col, lw=1)
    ax.plot([], [], "k:", lw=1, label="dotted: no collisions")
    ax.axhspan(0, 1.5, color=GREY, alpha=0.12)
    ax.text(62.3, 0.4, "values below ~1.5 %\nnot yet converged", fontsize=8, color=GREY, ha="right")
    ax.set_xlabel("port angle from the wafer axis (degrees)")
    ax.set_ylabel("unevenness, range/mean (%)")
    ax.set_title("The best port angle depends on how full the cup is (atom size 8 Å)", fontsize=10)
    ax.set_xlim(45, 63)
    ax.set_ylim(0, 11.5)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    fig.savefig(OUT / "ga_angle.png")
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in (chamber, level_melt, r07, ga_fill, ga_angle):
        f()
        print("wrote", f.__name__)


if __name__ == "__main__":
    main()
