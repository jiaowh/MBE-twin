"""Draw the README figures (docs/figures/*.png) from the recorded run summaries.

Schematics (chamber, level melt) are illustrations, not to scale. Data figures read only
data/runs/ records and, for the growth window, the sourced constants in data/parameters/, so
they change only when those records change.

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
    for f, a, dx in [(70, 54, 0.35), (120, 58, 0.35)]:  # spread of the one-setting checks
        checks = sorted((RUNS / "sparta_ga/ga_checks").glob(f"fill{f:03d}_d8_{a}deg_*.json"))
        vals = [load(p.relative_to(RUNS))["metrics_dsmc"]["range_over_mean_pct"] for p in checks]
        vals.append(load(f"sparta_ga/ga_angle/fill{f:03d}_d8_{a}deg.json")["metrics_dsmc"]
                    ["range_over_mean_pct"])
        ax.plot([a + dx] * 2, [min(vals), max(vals)], c=GREY, lw=4, alpha=0.7, solid_capstyle="butt")
    ax.plot([], [], c=GREY, lw=4, alpha=0.7, label="spread of repeat checks")
    ax.axhspan(0, 2.0, color=GREY, alpha=0.12)
    ax.text(62.3, 0.4, "values below ~2 %\nnot yet converged", fontsize=8, color=GREY, ha="right")
    ax.set_xlabel("port angle from the wafer axis (degrees)")
    ax.set_ylabel("unevenness, range/mean (%)")
    ax.set_title("The best port angle depends on how full the cup is (atom size 8 Å)", fontsize=10)
    ax.set_xlim(45, 63)
    ax.set_ylim(0, 11.5)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    fig.savefig(OUT / "ga_angle.png")
    plt.close(fig)


def growth_window():
    """Growth window and temperature sensitivity from the sourced kinetics (data/parameters)."""
    import sys
    sys.path.insert(0, str(ROOT / "src"))
    from mbe_twin.growth import load_parameters
    p = load_parameters()
    j_n = 1000.0 / 60.0  # 1 um/h
    t_c = np.linspace(680.0, 800.0, 121)
    t_k = t_c + 273.15
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3.8))
    ax1.axhspan(0.5, 1.0, color=GREY, alpha=0.15)
    ax1.text(682, 0.8, "too little gallium: rough growth", fontsize=8, color="black")
    labels = {"G01_adsorption": "droplets start (G01)", "Heying_growth": "droplets start (Heying)",
              "Ref14_growth": "droplets start (Ref. 14)"}
    for (sc, lab), col, ls in zip(labels.items(), [BLUE, ORANGE, GREEN], ["-", "--", "-."]):
        upper = 1.0 + p.critical_excess(sc, t_k) / j_n
        ax1.plot(t_c, upper, c=col, ls=ls, lw=2, label=lab)
    ax1.set_yscale("log")
    ax1.set_ylim(0.5, 20)
    ax1.set_yticks([0.5, 1, 2, 5, 10, 20])
    ax1.set_yticklabels(["0.5", "1", "2", "5", "10", "20"])
    ax1.text(745, 1.25, "usable window:\nsmooth growth", fontsize=8)
    ax1.set_xlabel("growth temperature (°C, as measured in the source labs)")
    ax1.set_ylabel("gallium-to-nitrogen supply ratio")
    ax1.set_title("The usable window widens with temperature", fontsize=10)
    ax1.legend(frameon=False, fontsize=8, loc="upper left", title="above a line: gallium droplets",
               title_fontsize=8, alignment="left")
    d = p.decomposition
    change = 100 * (d(t_k + 10.0) - d(t_k)) / (j_n - d(t_k))
    ax2.plot(t_c, change, c=RED, lw=2)
    ax2.set_xlabel("growth temperature (°C, as measured in the source labs)")
    ax2.set_ylabel("thickness change, % of the layer")
    ax2.set_title("Effect of a 10 °C hotter wafer edge on thickness", fontsize=10)
    ax2.set_ylim(0, None)
    fig.savefig(OUT / "growth_window.png")
    plt.close(fig)


def n_aim():
    """Nitrogen map uniformity against aim offset, from data/runs/studies/nitrogen_aim_study*.json."""
    first = load("studies/nitrogen_aim_study.json")["rows"]
    ext = {r["L_over_r"]: r for r in load("studies/nitrogen_aim_study_ext.json")["rows"]}
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    names = {0.0: "thin plate", 2.92: "holes 3x deeper than wide", 5.83: "6x", 11.66: "12x"}
    for r, col, mk in zip(first, [GREY, BLUE, ORANGE, GREEN], ["s", "o", "^", "D"]):
        a = r["L_over_r"]
        k45 = r["angles_deg"].index(45.0)
        v45 = [row[k45] for row in r["range_over_mean_pct"]]
        ax.plot(r["offsets_mm"], v45, ls=":", c=col, marker=mk, ms=4, lw=1.5)
        if a in ext:
            e = ext[a]
            k65 = e["angles_deg"].index(65.0)
            ax.plot(e["offsets_mm"], [row[k65] for row in e["range_over_mean_pct"]], ls="-", c=col, marker=mk,
                    ms=4, lw=2, label=names[a])
        else:
            ax.plot([], [], ls=":", c=col, marker=mk, label=names[a])
    ax.plot([], [], "k:", lw=1.5, label="dotted: port at 45°")
    ax.plot([], [], "k-", lw=2, label="solid: port at 65°")
    ax.axvline(0, c=GREY, lw=0.8)
    ax.text(2, 150, "aimed at\nwafer centre", fontsize=8, color="black")
    ax.axvspan(100, 150, color=GREY, alpha=0.1)
    ax.text(125, 0.13, "aim point beyond\nthe wafer edge", fontsize=8, ha="center")
    ax.set_yscale("log")
    ax.set_ylim(0.1, 300)
    ax.set_yticks([0.1, 0.3, 1, 3, 10, 30, 100, 300])
    ax.set_yticklabels(["0.1", "0.3", "1", "3", "10", "30", "100", "300"])
    ax.set_xlabel("aim point, mm from the wafer centre towards the source")
    ax.set_ylabel("nitrogen unevenness, range/mean (%)")
    ax.set_title("Aiming the nitrogen source off-centre evens out its jet (model, straight holes)", fontsize=10)
    ax.legend(frameon=False, fontsize=8, loc="lower left", ncol=2)
    fig.savefig(OUT / "n_aim.png")
    plt.close(fig)


def layouts():
    """Growth rate the nitrogen supply can reach, and uniformity at the reachable rates, for the leading layouts."""
    o = load("studies/layout_comparison_bc.json")
    ev_path = RUNS / "studies/nitrogen_output_evidence.json"
    eta_lit = json.loads(ev_path.read_text(encoding="utf-8"))["outputs"].get("eta_high_flow_joint") if ev_path.exists() else None
    colours = {"B": GREY, "B-p": BLUE, "B-L": GREEN}
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.2))
    if eta_lit:
        ax1.axvspan(eta_lit[0], eta_lit[1], color=ORANGE, alpha=0.15, lw=0)
        ax1.text(np.sqrt(eta_lit[0] * eta_lit[1]), 0.04, "published\nhigh-flow\nrange", ha="center", fontsize=7, color=ORANGE)
    for name in ("B-p", "B-L"):
        for (speed, feed), ls in (((2.0, 10.0), "--"), ((4.0, 35.0), "-")):
            pts = [r for r in o["operating_surface"] if r["layout"] == name and r["S_eff_m3_s"] == speed
                   and r["feed_limit_sccm"] == feed and r["target_um_h"] == 1.0]
            eta = np.array([r["eta"] for r in pts])
            rate = np.array([max(r["rate_nm_min"] * 0.06, 0.0) for r in pts])
            valid = np.array([r["kn_min"] >= 10.0 for r in pts])
            ax1.plot(eta, np.where(valid, rate, np.nan), ls, c=colours[name], lw=2,
                     label=f"{name}: {speed:g} m$^3$/s, up to {feed:g} sccm")
            ax1.plot(eta, np.where(~valid, rate, np.nan), ":", c=colours[name], lw=1)
    ax1.set_xscale("log")
    ax1.axhline(1.0, c=GREY, ls=":", lw=1)
    ax1.set_xlabel("fraction of the feed's N atoms leaving as active N")
    ax1.set_ylabel("growth rate reached (µm/h)")
    ax1.set_title("Rate (dotted: plate holes outside the model's range)", fontsize=9)
    ax1.legend(frameon=False, fontsize=7, loc="upper left")
    rows = [r for r in o["rows"] if r["evaluated"] and r["eta"] == 1.0 and r["S_eff_m3_s"] == 2.0 and r["feed_limit_sccm"] == 10.0
            and r["T0_C"] == 740.0 and r["target"] != "max"]
    for k, name in enumerate(colours):
        rr = sorted((r for r in rows if r["layout"] == name), key=lambda r: float(r["target"]))
        x = np.array([float(r["target"]) for r in rr]) * (1 + 0.035 * (k - 1))
        top = [r["grid_0.8deg"]["valid_thickness_pct_max"] for r in rr]
        ax2.vlines(x, [r["nominal"]["thickness_pct"] for r in rr], top, colors=colours[name], lw=5, alpha=0.45)
        ax2.plot(x, [r["nominal"]["thickness_pct"] for r in rr], "o", c=colours[name], ms=5,
                 label=f"{name}: as designed (dot) to worst within 0.8° (bar top)")
    ax2.set_xlabel("growth rate (µm/h)")
    ax2.set_ylabel("thickness half-range / mean (%), r <= 94 mm")
    ax2.set_title("Uniformity at reachable rates (all feed atoms active, 2 m$^3$/s)", fontsize=9)
    ax2.legend(frameon=False, fontsize=7, loc="upper right")
    fig.suptitle("Nitrogen supply and uniformity, 740 °C, 1200 °C element limit (representative chamber)", fontsize=10)
    fig.savefig(OUT / "layouts.png")
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in (chamber, level_melt, r07, ga_fill, ga_angle, growth_window, n_aim, layouts):
        f()
        print("wrote", f.__name__)


if __name__ == "__main__":
    main()
