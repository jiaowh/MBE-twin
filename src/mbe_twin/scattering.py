"""Test-particle transport of beam atoms through background gas: where do scattered atoms land?

The beam is a trace species in the chamber gas, so each atom is followed independently through
fixed gas fields (no DSMC needed):
- a uniform Maxwellian background (the chamber's N2 at p = Q / S);
- optionally the free-molecular plume in front of the nitrogen aperture plate: molecules leave
  the plate's active disk with a uniform areal rate and cos^n emission about the plate normal,
  so the density at x is n(x) = Phi (n + 1) / (2 pi <v>) * sum over the disk of
  cos^n(theta) dA / r^2 (Phi molecules m^-2 s^-1, <v> the mean speed, theta the emission angle),
  with velocities directed from the disk element and Maxwellian speeds (density-weighted).
  The plume is not modified by its own collisions (first order in its Knudsen number).

Collisions are hard spheres, isotropic in the centre-of-mass frame, sampled by the null-collision
method: candidates at a majorant rate n_max sigma g_max, accepted with probability
n(x) g / (n_max g_max). For the plume the majorant is bounded by the solid angle of the ball that
contains the disk, over a step that is limited so the bound stays valid.

Geometry (as scripts/background_scattering.py): wafer centre at the origin, growth face down
(normal -z), sources below (z < 0). The holder is an absorbing disk of radius holder_radius in
the plane z = 0 (wafer r <= wafer_radius); the chamber wall is a sphere of radius
chamber_radius about the wafer centre. On the wall, atoms are lost with probability gamma
(sticking, recombination), otherwise re-emitted diffusely at the wall temperature. With a pumping
speed S for the atoms, a wall-returned atom is also removed with the probability S / (A <v> / 4)
that the pump's aperture takes of the wall's collision rate (A the sphere's area, <v> the mean speed
at the wall temperature), so the loss per wall hit is gamma + (1 - gamma) S / (A <v> / 4). Without a
pump (the default) wall-returned atoms are removed only by gamma.
"""

from dataclasses import dataclass

import numpy as np

K_B = 1.380649e-23
AMU = 1.66053907e-27
M_N2_AMU = 28.0134
D_N2 = 3.7e-10


def unit(v):
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def _frame(normals):
    """Two unit vectors perpendicular to each row of normals (N, 3)."""
    t = np.where(np.abs(normals[:, :1]) < 0.9, np.array([[1.0, 0.0, 0.0]]), np.array([[0.0, 1.0, 0.0]]))
    e1 = unit(np.cross(normals, t))
    return e1, np.cross(normals, e1)


def cos_n_directions(rng, normals, n_cos):
    """Directions distributed as cos^n about each row of normals (N, 3)."""
    normals = np.atleast_2d(normals)
    e1, e2 = _frame(normals)
    c = rng.random(len(normals)) ** (1.0 / (n_cos + 1))
    s = np.sqrt(1 - c * c)
    ph = 2 * np.pi * rng.random(len(normals))
    return c[:, None] * normals + (s * np.cos(ph))[:, None] * e1 + (s * np.sin(ph))[:, None] * e2


def flux_speeds(rng, n, t, m_amu):
    """Speeds of a flux-weighted Maxwellian (v^3 exp(-m v^2 / 2 k T))."""
    return np.sqrt(2 * K_B * t / (m_amu * AMU) * rng.gamma(2.0, 1.0, n))


def maxwell_speeds(rng, n, t, m_amu):
    """Speeds of a (density-weighted) Maxwellian."""
    return np.sqrt(K_B * t / (m_amu * AMU)) * np.linalg.norm(rng.normal(size=(n, 3)), axis=1)


def mean_speed(t, m_amu):
    return np.sqrt(8 * K_B * t / (np.pi * m_amu * AMU))


def collide(v, u, m, mg, rng):
    """Hard-sphere elastic collision, isotropic in the centre-of-mass frame. Returns the test atom's new velocity."""
    g = np.linalg.norm(v - u, axis=1)
    vcm = (m * v + mg * u) / (m + mg)
    ct = 2 * rng.random(len(v)) - 1
    st = np.sqrt(1 - ct * ct)
    ph = 2 * np.pi * rng.random(len(v))
    gdir = np.stack([st * np.cos(ph), st * np.sin(ph), ct], 1)
    return vcm + (mg / (m + mg)) * g[:, None] * gdir


@dataclass(frozen=True)
class Gas:
    """Uniform Maxwellian background."""
    density: float                 # m^-3
    temperature: float = 300.0
    mass_amu: float = M_N2_AMU


@dataclass(frozen=True)
class Plume:
    """Free-molecular plume of a disk emitting cos^n about its normal (normal points into the chamber).

    Density at x: prefactor x integral of cos^(n-1)(theta) dOmega over the directions theta, phi (gas moving
    away from the plate) whose rays back from x land inside the disk. For each azimuth phi the landing
    condition |L - h tan(theta) e_phi| <= R is an interval in tan(theta) (L: lateral offset of x from the disk
    centre, h: height above the plate), so the theta integral is exact, (cos^n theta_1 - cos^n theta_2) / n,
    and only phi is integrated numerically (n_phi midpoints)."""
    centre: tuple
    normal: tuple
    radius: float
    flux: float                    # molecules m^-2 s^-1 leaving the disk
    temperature: float = 300.0
    n_cos: float = 1.0
    mass_amu: float = M_N2_AMU
    n_phi: int = 256

    def prefactor(self):
        return self.flux * (self.n_cos + 1) / (2 * np.pi * mean_speed(self.temperature, self.mass_amu))

    def density_bound(self, dist):
        """Upper bound of the density at any point at distance >= dist from the disk centre: the disk lies in the
        ball of its radius, and cos^n <= cos for n >= 1, so the integral is at most that ball's solid angle."""
        dist = np.asarray(dist, float)
        q = np.clip(self.radius / np.maximum(dist, 1e-300), 0.0, 1.0)
        omega = np.where(dist <= self.radius, 2 * np.pi, 2 * np.pi * (1 - np.sqrt(1 - q * q)))
        return self.prefactor() * omega

    def _frame(self):
        nrm = unit(np.asarray(self.normal, float))
        e1, e2 = (q[0] for q in _frame(nrm[None]))
        return np.asarray(self.centre, float), nrm, e1, e2

    def azimuth_weights(self, x):
        """Per-azimuth density contributions at x (M, 3): (M, n_phi), and cos(theta) at both ends of each interval."""
        c, nrm, e1, e2 = self._frame()
        rel = x - c
        h = rel @ nrm
        l1, l2 = rel @ e1, rel @ e2
        ph = (np.arange(self.n_phi) + 0.5) * 2 * np.pi / self.n_phi
        b = l1[:, None] * np.cos(ph)[None] + l2[:, None] * np.sin(ph)[None]    # L . e_phi
        disc = b * b - (l1 * l1 + l2 * l2)[:, None] + self.radius ** 2
        ok = (disc >= 0) & (h[:, None] > 0)
        sq = np.sqrt(np.where(ok, disc, 0.0))
        hh = np.where(h > 0, h, 1.0)[:, None]
        t1 = np.clip((b - sq) / hh, 0.0, None)
        t2 = (b + sq) / hh
        ok &= t2 > 0
        c1, c2 = 1 / np.sqrt(1 + t1 * t1), 1 / np.sqrt(1 + np.clip(t2, 0.0, None) ** 2)
        w = np.where(ok, (c1 ** self.n_cos - c2 ** self.n_cos) / self.n_cos, 0.0) * (2 * np.pi / self.n_phi)
        return self.prefactor() * w, c1, c2, ph

    def density(self, x):
        x = np.atleast_2d(np.asarray(x, float))
        dist = np.linalg.norm(x - np.asarray(self.centre, float), axis=1)
        return np.minimum(self.azimuth_weights(x)[0].sum(1), self.density_bound(dist))

    def sample_partners(self, rng, x):
        """Local plume density at x (M, 3) and one partner velocity per point from the local distribution."""
        _, nrm, e1, e2 = self._frame()
        w, c1, c2, ph = self.azimuth_weights(x)
        tot = w.sum(1)
        cdf = np.cumsum(w, 1)
        k = np.argmax(cdf >= (rng.random(len(x)) * np.where(tot > 0, tot, 1.0))[:, None], 1)
        rows = np.arange(len(x))
        a, b = c2[rows, k] ** self.n_cos, c1[rows, k] ** self.n_cos
        ct = (a + rng.random(len(x)) * (b - a)) ** (1.0 / self.n_cos)     # density cos^(n-1) sin on [theta_1, theta_2]
        st = np.sqrt(np.clip(1 - ct * ct, 0.0, None))
        d = ct[:, None] * nrm + (st * np.cos(ph[k]))[:, None] * e1 + (st * np.sin(ph[k]))[:, None] * e2
        u = d * maxwell_speeds(rng, len(x), self.temperature, self.mass_amu)[:, None]
        dist = np.linalg.norm(x - np.asarray(self.centre, float), axis=1)
        return np.minimum(tot, self.density_bound(dist)), u


@dataclass(frozen=True)
class Chamber:
    radius: float = 0.5
    holder_radius: float = 0.13
    wafer_radius: float = 0.10
    wall_temperature: float = 300.0


@dataclass(frozen=True)
class Source:
    """Emitter: a point (radius 0) or a disk of the given radius, cos^n about axis."""
    position: tuple
    axis: tuple
    n_cos: float
    radius: float = 0.0

    def emit(self, rng, n):
        ax = unit(np.asarray(self.axis, float))
        x = np.repeat(np.asarray(self.position, float)[None], n, 0)
        if self.radius > 0:
            e1, e2 = (q[0] for q in _frame(ax[None]))
            r = self.radius * np.sqrt(rng.random(n))
            ph = 2 * np.pi * rng.random(n)
            x = x + (r * np.cos(ph))[:, None] * e1 + (r * np.sin(ph))[:, None] * e2 + 1e-6 * ax
        return x, cos_n_directions(rng, np.repeat(ax[None], n, 0), self.n_cos)


def wall_loss(gamma, pump_speed, chamber, mass_amu):
    """Loss probability per wall hit: gamma, plus the pump's share of the wall collision rate for the rest."""
    if pump_speed <= 0:
        return gamma
    v_mean = np.sqrt(8 * K_B * chamber.wall_temperature / (np.pi * mass_amu * AMU))
    p_pump = min(1.0, pump_speed / (4 * np.pi * chamber.radius ** 2 * v_mean / 4))
    return gamma + (1 - gamma) * p_pump


def track(rng, n, source, *, mass_amu, temperature, diameter, gas=None, plume=None, chamber=Chamber(), gamma=1.0,
          pump_speed=0.0, gas_diameter=D_N2, chunk=4000, max_iter=100_000):
    """Follow n atoms from source; return wafer-hit radii, an 'indirect' flag per hit (collided or wall-returned),
    and counts of gas and plume collisions. pump_speed (m^3/s, for these atoms) adds the pump's removal of
    wall-returned atoms (wall_loss); 0 reproduces the earlier tracker exactly."""
    m = mass_amu
    p_loss = wall_loss(gamma, pump_speed, chamber, m)
    sigma = np.pi * ((diameter + gas_diameter) / 2) ** 2
    x, d = source.emit(rng, n)
    v = d * flux_speeds(rng, n, temperature, m)[:, None]
    indirect = np.zeros(n, bool)
    alive = np.ones(n, bool)
    out_r, out_ind = [], []
    counts = {"gas": 0, "plume": 0}
    n_gas = gas.density if gas is not None else 0.0
    sig_g = np.sqrt(K_B * gas.temperature / (gas.mass_amu * AMU)) if gas is not None else 0.0
    if plume is not None:
        pc = np.asarray(plume.centre, float)
        u_cap_p = 5.0 * np.sqrt(2 * K_B * plume.temperature / (plume.mass_amu * AMU))
    for _ in range(max_iter):
        idx = np.flatnonzero(alive)
        if idx.size == 0:
            break
        xi, vi = x[idx], v[idx]
        speed = np.linalg.norm(vi, axis=1)
        g_max_g = speed + 6.0 * np.sqrt(3.0) * sig_g
        rate_g = n_gas * sigma * g_max_g
        t_lim = np.full(idx.size, np.inf)
        rate_p = np.zeros(idx.size)
        if plume is not None:
            dist = np.linalg.norm(xi - pc, axis=1)
            step = np.maximum(0.005, 0.5 * dist)
            n_maj = plume.density_bound(np.maximum(dist - step, 0.0))
            g_max_p = speed + u_cap_p
            rate_p = n_maj * sigma * g_max_p
            t_lim = step / speed
        rate = rate_g + rate_p
        with np.errstate(divide="ignore"):
            t_coll = np.where(rate > 0, -np.log(rng.random(idx.size)) / np.where(rate > 0, rate, 1.0), np.inf)
        # wafer plane
        with np.errstate(divide="ignore", invalid="ignore"):
            t_pl = -xi[:, 2] / vi[:, 2]
        t_pl = np.where((t_pl > 1e-12) & np.isfinite(t_pl), t_pl, np.inf)
        p_pl = xi + vi * np.where(np.isfinite(t_pl), t_pl, 0.0)[:, None]
        r_pl = np.hypot(p_pl[:, 0], p_pl[:, 1])
        t_pl = np.where(r_pl < chamber.holder_radius, t_pl, np.inf)
        # chamber sphere
        b = np.sum(xi * vi, 1)
        cc = np.sum(xi * xi, 1) - chamber.radius ** 2
        t_sp = (-b + np.sqrt(np.maximum(b * b - speed ** 2 * cc, 0.0))) / speed ** 2
        t_min = np.minimum.reduce([t_coll, t_pl, t_sp, t_lim])
        ev_pl = t_pl <= t_min
        ev_sp = ~ev_pl & (t_sp <= t_min)
        ev_co = ~ev_pl & ~ev_sp & (t_coll <= t_min)
        x[idx] = xi + vi * t_min[:, None]
        # holder / wafer
        j = idx[ev_pl]
        r_hit = r_pl[ev_pl]
        keep = (vi[ev_pl, 2] > 0) & (r_hit <= chamber.wafer_radius)
        out_r.append(r_hit[keep])
        out_ind.append(indirect[j][keep])
        alive[j] = False
        # wall
        j = idx[ev_sp]
        if j.size:
            lost = rng.random(j.size) < p_loss
            alive[j[lost]] = False
            jr = j[~lost]
            if jr.size:
                nrm = -unit(x[jr])
                x[jr] = -nrm * chamber.radius * (1 - 1e-9)
                v[jr] = cos_n_directions(rng, nrm, 1) * flux_speeds(rng, jr.size, chamber.wall_temperature, m)[:, None]
                indirect[jr] = True
        # collision candidates
        sel = np.flatnonzero(ev_co)
        if sel.size:
            j = idx[sel]
            from_gas = rng.random(sel.size) * rate[sel] < rate_g[sel]
            acc = np.zeros(sel.size, bool)
            u = np.zeros((sel.size, 3))
            kg = np.flatnonzero(from_gas)
            if kg.size:
                u[kg] = rng.normal(0.0, sig_g, (kg.size, 3))
                g = np.linalg.norm(v[j[kg]] - u[kg], axis=1)
                acc[kg] = rng.random(kg.size) * g_max_g[sel[kg]] < g
            kp = np.flatnonzero(~from_gas)
            for s0 in range(0, kp.size, chunk):
                kk = kp[s0:s0 + chunk]
                n_here, u[kk] = plume.sample_partners(rng, x[j[kk]])
                g = np.linalg.norm(v[j[kk]] - u[kk], axis=1)
                acc[kk] = rng.random(kk.size) * n_maj[sel[kk]] * g_max_p[sel[kk]] < n_here * g
            ja = j[acc]
            if ja.size:
                mg = np.where(from_gas[acc], gas.mass_amu if gas is not None else 1.0,
                              plume.mass_amu if plume is not None else 1.0)[:, None]
                v[ja] = collide(v[ja], u[acc], m, mg, rng)
                indirect[ja] = True
                counts["gas"] += int(np.sum(from_gas[acc]))
                counts["plume"] += int(np.sum(~from_gas[acc]))
    else:
        raise RuntimeError("scattering.track: particles still alive after max_iter")
    return np.concatenate(out_r), np.concatenate(out_ind), counts


def radial_arrival(r, indirect, n, edges):
    """Rotation-averaged arrivals per emitted atom per m^2 in radial bins: (direct, indirect)."""
    area = np.pi * np.diff(edges ** 2)
    return (np.histogram(r[~indirect], edges)[0] / area / n, np.histogram(r[indirect], edges)[0] / area / n)


def fit_even(r_bins, y, y_err, rho, r_ref=0.1, degree=2):
    """Weighted least-squares fit of y(r) as a polynomial in (r / r_ref)^2, evaluated at rho."""
    u = (np.asarray(r_bins) / r_ref) ** 2
    a = np.vander(u, degree + 1, increasing=True)
    w = 1.0 / np.maximum(np.asarray(y_err), 1e-12)
    coef, *_ = np.linalg.lstsq(a * w[:, None], np.asarray(y) * w, rcond=None)
    return np.vander((np.asarray(rho) / r_ref) ** 2, degree + 1, increasing=True) @ coef


def tube_cos_n(l_over_r, n_particles=200_000, seed=5):
    """cos^n exponent with the on-axis peaking of a free-molecular tube of the given L/r: a tube of transmission W
    sends Ndot / (pi W) per steradian on axis, cos^n sends Ndot (n + 1) / (2 pi), so n = 2 / W - 1."""
    from mbe_twin.crucible import Crucible, simulate
    w = simulate(Crucible(1.0, l_over_r), n_particles, rng=seed, record_events=False).transmission
    return 2.0 / w - 1.0


def direct_flux(source, rho, mean_free_path=np.inf, n_phi=90, n_ring=8, n_ring_phi=16):
    """Deterministic rotation-averaged direct flux per emitted atom (m^-2) at wafer radii rho, attenuated by
    exp(-s / mean_free_path) along each path (the layout comparison's direct-beam model). Disk sources are
    sampled on n_ring equal-area rings of n_ring_phi points."""
    ax = unit(np.asarray(source.axis, float))
    if source.radius > 0:
        e1, e2 = (q[0] for q in _frame(ax[None]))
        edges = source.radius * np.sqrt(np.arange(n_ring + 1) / n_ring)
        rr = np.sqrt((edges[:-1] ** 2 + edges[1:] ** 2) / 2)
        ph = (np.arange(n_ring_phi) + 0.5) * 2 * np.pi / n_ring_phi
        R, P = np.meshgrid(rr, ph, indexing="ij")
        src = np.asarray(source.position, float) + (R * np.cos(P)).reshape(-1, 1) * e1 + (R * np.sin(P)).reshape(-1, 1) * e2
    else:
        src = np.asarray(source.position, float)[None]
    phi = (np.arange(n_phi) + 0.5) * 2 * np.pi / n_phi
    rho = np.asarray(rho, float)
    pts = np.stack([rho[:, None] * np.cos(phi)[None], rho[:, None] * np.sin(phi)[None], np.zeros((len(rho), n_phi))], -1)
    d = pts[:, :, None, :] - src[None, None]
    s = np.linalg.norm(d, axis=-1)
    cos_t = np.clip((d @ ax) / s, 0.0, None)
    cos_i = np.clip(d[..., 2] / s, 0.0, None)          # growth face down: arrivals move towards +z
    f = (source.n_cos + 1) / (2 * np.pi) * cos_t ** source.n_cos * cos_i / s ** 2
    if np.isfinite(mean_free_path):
        f = f * np.exp(-s / mean_free_path)
    return f.mean(axis=(1, 2))


def binned_direct_flux(source, edges, mean_free_path=np.inf, sub=8, **kw):
    """direct_flux averaged over the area of each radial bin (sub equal-area sub-rings per bin)."""
    out = []
    for a, b in zip(edges[:-1], edges[1:]):
        e = np.sqrt(a * a + (b * b - a * a) * np.arange(sub + 1) / sub)
        out.append(direct_flux(source, np.sqrt((e[:-1] ** 2 + e[1:] ** 2) / 2), mean_free_path, **kw).mean())
    return np.array(out)
