"""Heater states with multi-spot pyrometry and zone-group trimming (sensor-placement option for the realizable controller).

The single-reading controller of heater_robustness holds one centre reading with the zone ratios fixed,
so wafer-to-wafer changes of emissivity and ledge contact pass into the wafer's temperature range. Here the
designed-density heater's 12 rings are driven as three groups (inner rings 1-4, middle 5-8, outer 9-12,
i.e. 0-38 / 38-77 / 77-115 mm of the heater), and three pyrometer spots (default centre, 50 mm and 85 mm,
10 mm spots) are held at the readings the nominal wafer gives at calibration. The three group powers are
solved by Newton's method with a finite-difference Jacobian on the steady heater model; if the hottest
ring would exceed the element limit, the three powers are scaled down together until it sits on the limit
(capped, flagged). Errors: a common bias of all spots (-b / 0 / +b) and a differential error of the edge
spot relative to the others (-d / 0 / +d), so the controller can mistake an edge-spot error for a profile
change. Grid: wafer emissivity x contact x worst +/-2 % zone error, as heater_robustness.
"""

import itertools

import numpy as np

GROUPS = ((0, 4), (4, 8), (8, 12))
SPOTS_M = (0.0, 0.050, 0.085)
SPOT_RADIUS_M = 0.005


def spot_readings(r, spots=SPOTS_M, radius=SPOT_RADIUS_M):
    """Area-weighted spot means (K) of a heater-model result at each spot centre (annular sampling for r > 0)."""
    rw, tw, aw = r["r_wafer"], r["t_wafer"], r["area_wafer"]
    out = []
    for c in spots:
        sel = np.abs(rw - c) <= radius
        out.append(float(np.sum(aw[sel] * tw[sel]) / aw[sel].sum()))
    return np.array(out)


def group_power(frac, g):
    p = np.zeros_like(frac)
    for (a, b), x in zip(GROUPS, g):
        p[a:b] = frac[a:b] * x
    return p


def hold_spots(model, frac, p0, target, offsets, limit, iters=12):
    """Group multipliers that put the biased spot readings on target; capped at the element limit."""
    g = np.full(3, p0)

    def read(gv):
        r = model.solve(heater_power=group_power(frac, gv))
        return r, spot_readings(r) + offsets
    r, y = read(g)
    for _ in range(iters):
        err = y - target
        if np.max(np.abs(err)) < 1e-3:
            break
        jac = np.empty((3, 3))
        for k in range(3):
            dg = g.copy()
            dg[k] *= 1.01
            jac[:, k] = (read(dg)[1] - y) / (dg[k] - g[k])
        g = np.maximum(g - np.linalg.solve(jac, err), 0.05 * p0)
        r, y = read(g)
    capped = bool(r["t_heater"].max() > limit)
    if capped:
        lo, hi = 0.0, 1.0
        for _ in range(50):
            mid = 0.5 * (lo + hi)
            if model.solve(heater_power=group_power(frac, g * mid))["t_heater"].max() > limit:
                hi = mid
            else:
                lo = mid
        g = g * lo
        r, y = read(g)
    return r, capped


def multispot_states(hz, hr, t0_k, rho, design_limit, limit, bias_k=2.0, diff_k=0.5):
    """State dicts (as heater_robustness.combined_states) for the multi-spot, three-group controller."""
    edges, geo = hz.LAYOUTS["12 zones"], {"ledge_inner": hr.OPENING}
    base = hz.make(edges, geo, {})
    r0, frac = hz.optimize(base, t0_k, limits={"t_heater_max": design_limit})
    p0 = float(r0["zone_power"].sum())
    nominal = hz.at_mean(base, frac, t0_k, p0=p0)
    target = spot_readings(nominal)
    states = []
    for eps, h, z in itertools.product(hr.EPS, hr.CONTACT, hr.ZONE):
        m = hz.make(edges, geo, {"eps_wafer": eps, "h_contact": h})
        cands = [frac]
        if z != 0.0:
            cands = []
            for k in range(12):
                c = frac.copy()
                c[k] *= 1 + z
                cands.append(c / c.sum())
        f = max(((hz.at_mean(m, c, t0_k, p0=p0), c) for c in cands), key=lambda x: x[0]["wafer_range"])[1]
        for b, d in itertools.product((-bias_k, 0.0, bias_k), (-diff_k, 0.0, diff_k)):
            offsets = np.array([b, b, b + d])
            r, capped = hold_spots(m, f, p0, target, offsets, limit)
            states.append({"limit": "1473 K element", "eps": eps, "contact": h, "zone_error": z,
                           "controller": f"pyrometer {b:+g} K", "edge_spot_error_K": d, "capped": capped,
                           "reading_K": float(spot_readings(r)[0] + b),
                           "t_map": np.interp(rho, r["r_wafer"], r["t_wafer"]), "wafer_range_K": float(r["wafer_range"])})
    return states, {"target_K": target.tolist(), "nominal_range_K": float(nominal["wafer_range"])}
