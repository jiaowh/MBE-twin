"""Axisymmetric heater-holder-wafer thermal model (representative 200 mm substrate heater).

Reduced model for zone-count and temperature-uniformity studies (Stage A, section 7 item 5).
A rotating wafer sees the heater azimuthally averaged, so the model is axisymmetric:

- Heater: a gray disk facing the wafer across a gap, divided into rings grouped into zones.
  Each zone is power-driven (W, uniform per unit area within the zone), or held at a set
  temperature (for verification). Its back is adiabatic (reflector stack assumed perfect).
- Lower plane of the gap, at the same gap: the wafer's back face for r < ledge_inner, and the
  holder ledge's back face from ledge_inner to ledge_outer. The ledge carries the wafer rim:
  wafer rings between ledge_inner and the wafer radius sit on ledge rings at the same radii,
  coupled by a gap conductance h_contact (W m^-2 K^-1; radiation across the thin gap plus any
  contact). Ledge rings beyond the wafer radius face the chamber.
- Radiation in the gap: diffuse-gray ring radiosity between the two coaxial planes
  (mbe_twin.radiation.ring_exchange, verified against Elmer in V03), open at the rim to black
  surroundings at t_rim.
- Front faces (wafer, exposed ledge) radiate to black surroundings at t_env (cryoshroud or
  chamber wall). Hot effusion cells and the plasma source are not included.
- Lateral conduction in the wafer (k_wafer, thickness) and the ledge (k_ledge, thickness);
  finite volumes on the rings.

The radiosity system is linear in the emissive powers sigma T^4, so the net radiative gain per
ring is q = M (sigma T^4) + c, precomputed once; the energy balance is solved by Newton's
method. Parameters that no repository source fixes are inputs to be bracketed, not values:
see scripts/heater_zones.py.
"""

from dataclasses import dataclass, field

import numpy as np

from .radiation import SIGMA, ring_exchange


@dataclass
class HeaterGeometry:
    wafer_radius: float = 0.100
    wafer_thickness: float = 725e-6
    heater_radius: float = 0.115
    gap: float = 0.010
    ledge_inner: float = 0.097
    ledge_outer: float = 0.115
    ledge_thickness: float = 2e-3
    zone_edges: tuple = (0.0, 0.115)          # heater zone boundaries (m), from 0 to heater_radius
    n_heater: int = 60
    n_wafer: int = 50                         # wafer rings inside ledge_inner
    n_over: int = 6                           # wafer rings over the ledge
    n_outer: int = 8                          # ledge rings beyond the wafer


@dataclass
class HeaterProperties:
    eps_heater: float = 0.85
    eps_wafer: float = 0.7                    # Si above ~650 C, R28 (Timans 1993), +/-10 %
    eps_ledge: float = 0.3
    k_wafer: float = 30.0                     # W/m/K; bracket, not sourced in the repository
    k_ledge: float = 100.0
    h_contact: float = 200.0                  # W/m^2/K between wafer rim and ledge
    t_env: float = 300.0
    t_rim: float = 300.0
    eps_wafer_front: float = None             # front-face emissivities (default: as the back)
    eps_ledge_front: float = None

    def front(self):
        return (self.eps_wafer if self.eps_wafer_front is None else self.eps_wafer_front,
                self.eps_ledge if self.eps_ledge_front is None else self.eps_ledge_front)


@dataclass
class HeaterModel:
    geometry: HeaterGeometry = field(default_factory=HeaterGeometry)
    props: HeaterProperties = field(default_factory=HeaterProperties)

    def __post_init__(self):
        g, p = self.geometry, self.props
        if not (0 < g.ledge_inner < g.wafer_radius < g.ledge_outer):
            raise ValueError("need 0 < ledge_inner < wafer_radius < ledge_outer")
        self.eh = np.linspace(0.0, g.heater_radius, g.n_heater + 1)
        ew_in = np.linspace(0.0, g.ledge_inner, g.n_wafer + 1)
        e_over = np.linspace(g.ledge_inner, g.wafer_radius, g.n_over + 1)
        e_out = np.linspace(g.wafer_radius, g.ledge_outer, g.n_outer + 1)
        self.ew = np.concatenate([ew_in, e_over[1:]])            # all wafer rings
        self.el = np.concatenate([e_over, e_out[1:]])            # all ledge rings
        self.ep = np.concatenate([ew_in, e_over[1:], e_out[1:]])  # lower plane of the gap
        nh, nw, nl = g.n_heater, len(self.ew) - 1, len(self.el) - 1
        self.nh, self.nw, self.nl = nh, nw, nl
        self.n_in = g.n_wafer
        # unknown vector: heater rings | wafer rings | ledge rings
        self.ih = np.arange(nh)
        self.iw = nh + np.arange(nw)
        self.il = nh + nw + np.arange(nl)
        # gap surfaces: heater rings, then the lower plane (wafer inner rings, then all ledge rings)
        a1, a2, f12, f21 = ring_exchange(self.eh, self.ep, g.gap)
        n1, n2 = len(a1), len(a2)
        f = np.block([[np.zeros((n1, n1)), f12], [f21, np.zeros((n2, n2))]])
        eps = np.concatenate([np.full(n1, p.eps_heater), np.full(self.n_in, p.eps_wafer),
                              np.full(nl, p.eps_ledge)])
        self.gap_area = np.concatenate([a1, a2])
        self.gap_eps = eps
        self.gap_open = 1.0 - f.sum(axis=1)
        ext = SIGMA * p.t_rim ** 4 * self.gap_open
        a = np.eye(n1 + n2) - (1.0 - eps)[:, None] * f
        ainv = np.linalg.inv(a)
        # J = ainv (eps Eb + (1-eps) ext); q = eps (F J + ext - Eb) per area
        self._m = eps[:, None] * (f @ ainv @ np.diag(eps) - np.eye(n1 + n2))
        self._c = eps * (f @ ainv @ ((1.0 - eps) * ext) + ext)
        self._ainv, self._f, self._ext = ainv, f, ext
        # map gap surfaces to unknowns
        self.gap_index = np.concatenate([self.ih, self.iw[:self.n_in], self.il])
        self.area_h = np.pi * np.diff(self.eh ** 2)
        self.area_w = np.pi * np.diff(self.ew ** 2)
        self.area_l = np.pi * np.diff(self.el ** 2)
        self.rw = 0.5 * (self.ew[1:] + self.ew[:-1])
        self.rl = 0.5 * (self.el[1:] + self.el[:-1])
        self.rh = 0.5 * (self.eh[1:] + self.eh[:-1])
        z = np.asarray(g.zone_edges, float)
        if z[0] != 0.0 or abs(z[-1] - g.heater_radius) > 1e-12:
            raise ValueError("zone_edges must run from 0 to heater_radius")
        self.zone_of = np.clip(np.searchsorted(z, self.rh, side="right") - 1, 0, len(z) - 2)
        self.n_zones = len(z) - 1
        self.zone_area = np.array([self.area_h[self.zone_of == k].sum() for k in range(self.n_zones)])

    def _conduction(self, t):
        """Net conductive gain (W) per unknown, and its (constant) Jacobian."""
        g, p = self.geometry, self.props
        n = len(t)
        jac = np.zeros((n, n))

        def chain(idx, radii, k, thick):
            for a, b, ra, rb in zip(idx[:-1], idx[1:], radii[:-1], radii[1:]):
                cond = 2 * np.pi * k * thick / np.log(rb / ra)
                jac[a, a] -= cond
                jac[a, b] += cond
                jac[b, b] -= cond
                jac[b, a] += cond

        chain(self.iw, self.rw, p.k_wafer, g.wafer_thickness)
        chain(self.il, self.rl, p.k_ledge, g.ledge_thickness)
        # wafer rings over the ledge <-> ledge rings at the same radii
        for j in range(g.n_over):
            w, l = self.iw[self.n_in + j], self.il[j]
            h = p.h_contact * self.area_l[j]
            jac[w, w] -= h
            jac[w, l] += h
            jac[l, l] -= h
            jac[l, w] += h
        return jac @ t, jac

    def residual(self, t, heater_power=None, heater_temperature=None):
        """Energy balance residual (W) per unknown, and its Jacobian."""
        p = self.props
        n = len(t)
        res, jac = self._conduction(t)
        eb = SIGMA * t[self.gap_index] ** 4
        q = self._m @ eb + self._c
        area = self.gap_area
        res = res.copy()
        res[self.gap_index] += area * q
        jac[np.ix_(self.gap_index, self.gap_index)] += area[:, None] * self._m * (4 * SIGMA * t[self.gap_index] ** 3)[None, :]
        # front faces to the chamber
        front = np.concatenate([self.iw, self.il[self.geometry.n_over:]])
        ew_f, el_f = p.front()
        eps_f = np.concatenate([np.full(self.nw, ew_f), np.full(self.nl - self.geometry.n_over, el_f)])
        a_f = np.concatenate([self.area_w, self.area_l[self.geometry.n_over:]])
        res[front] -= a_f * eps_f * SIGMA * (t[front] ** 4 - p.t_env ** 4)
        jac[front, front] -= a_f * eps_f * 4 * SIGMA * t[front] ** 3
        if heater_temperature is not None:
            th = np.asarray(heater_temperature, float)[self.zone_of]
            res[self.ih] = t[self.ih] - th
            jac[self.ih, :] = 0.0
            jac[self.ih, self.ih] = 1.0
        else:
            per_area = np.asarray(heater_power, float) / self.zone_area
            res[self.ih] += per_area[self.zone_of] * self.area_h
        return res, jac

    def solve(self, heater_power=None, heater_temperature=None, t0=1000.0, step_tol=1e-5, max_iter=100):
        """Steady temperatures. Give heater_power (W per zone) or heater_temperature (K per zone)."""
        if (heater_power is None) == (heater_temperature is None):
            raise ValueError("give exactly one of heater_power and heater_temperature")
        n = self.nh + self.nw + self.nl
        t = np.full(n, float(t0))
        for _ in range(max_iter):
            r, j = self.residual(t, heater_power, heater_temperature)
            dt = np.linalg.solve(j, -r)
            step = np.clip(dt, -0.3 * t, 0.3 * t)
            t = np.maximum(t + step, 50.0)
            if np.max(np.abs(step)) < step_tol:  # Newton converges quadratically to round-off
                break
        else:
            raise RuntimeError("heater model did not converge")
        return self._result(t, heater_power, heater_temperature)

    def _result(self, t, heater_power, heater_temperature):
        p = self.props
        eb = SIGMA * t[self.gap_index] ** 4
        j = self._ainv @ (self.gap_eps * eb + (1.0 - self.gap_eps) * self._ext)
        rim_loss = float(np.sum(self.gap_area * self.gap_open * (j - SIGMA * p.t_rim ** 4)))
        front = np.concatenate([self.iw, self.il[self.geometry.n_over:]])
        ew_f, el_f = p.front()
        eps_f = np.concatenate([np.full(self.nw, ew_f), np.full(self.nl - self.geometry.n_over, el_f)])
        a_f = np.concatenate([self.area_w, self.area_l[self.geometry.n_over:]])
        front_loss = float(np.sum(a_f * eps_f * SIGMA * (t[front] ** 4 - p.t_env ** 4)))
        if heater_power is not None:
            power = np.asarray(heater_power, float)
        else:  # heater net output per zone from its balance
            q = self._m @ eb + self._c
            out = -(self.gap_area * q)[:self.nh]
            power = np.array([out[self.zone_of == k].sum() for k in range(self.n_zones)])
        tw = t[self.iw]
        return {"r_wafer": self.rw, "t_wafer": tw, "area_wafer": self.area_w, "r_heater": self.rh,
                "t_heater": t[self.ih], "r_ledge": self.rl, "t_ledge": t[self.il], "zone_power": power,
                "rim_loss": rim_loss, "front_loss": front_loss,
                "energy_residual": float(power.sum() - rim_loss - front_loss),
                "wafer_mean": float(np.sum(self.area_w * tw) / self.area_w.sum()),
                "wafer_range": float(tw.max() - tw.min())}
