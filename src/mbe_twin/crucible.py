"""Free-molecular emission from an effusion-cell crucible (mbe_twin.md section 8.2).

The crucible interior is a frustum whose radius does not decrease toward the orifice
(cylinders and conical crucibles opening toward the orifice). That interior is convex, so a
straight path from any interior point leaves through the orifice or not at all. In the local
frame the orifice lies in the plane z = 0 with the axis along +z. The melt is the planar
section of the crucible through the axis point at depth `melt_depth`, with normal
`melt_normal`: (0, 0, 1) is perpendicular to the axis, and a liquid in an inclined crucible
stays level, so its normal is the local "up" direction. The melt emits a Lambertian flux
uniformly over its area. The region above the melt is still convex. Walls re-emit
every arriving particle diffusely (hot walls, no condensation). Particles returning to the melt
are absorbed. Intermolecular collisions are neglected: R07 shows that they reshape the beam
above roughly 0.2 A/s, so this model represents the low-rate (free-molecular) limit.

Flux outside the crucible uses a next-event (point) estimator: every emission event from the
melt or a wall contributes cos(theta_e) cos(psi) / (pi r^2) to each visible target point. This
gives smooth wafer maps from modest particle counts. The random walk supplies the event
positions and the Clausing transmission probability.
"""

from dataclasses import dataclass

import numpy as np

_CHUNK_ELEMENTS = 2_000_000


@dataclass(frozen=True)
class Crucible:
    """Frustum crucible. The taper is set by `taper_half_angle` (rad) or, equivalently for an
    untilted melt, by `melt_radius` (the wall radius at depth `melt_depth`); a cylinder has
    neither."""

    lip_radius: float
    melt_depth: float  # axial depth below the orifice where the axis meets the melt surface
    melt_radius: float | None = None
    taper_half_angle: float = 0.0
    melt_normal: tuple = (0.0, 0.0, 1.0)

    def __post_init__(self):
        if self.lip_radius <= 0.0 or self.melt_depth < 0.0:
            raise ValueError("lip radius must be positive and melt depth non-negative")
        if self.melt_radius is not None and self.taper_half_angle != 0.0:
            raise ValueError("give either melt_radius or taper_half_angle, not both")
        if self.melt_radius is not None and not 0.0 < self.melt_radius <= self.lip_radius:
            raise ValueError("melt radius must be positive and not exceed the lip radius "
                             "(non-convex crucibles such as necked ones are not supported)")
        if not 0.0 <= self.taper_half_angle < np.pi / 2:
            raise ValueError("taper half-angle must be in [0, 90) degrees (opening toward the orifice)")
        n = np.asarray(self.melt_normal, float)
        if n.shape != (3,) or np.linalg.norm(n) == 0.0 or n[2] <= 0.0:
            raise ValueError("melt normal must be a 3-vector with a positive axial component")
        z = self.melt_boundary()[:, 2]
        if np.any(z > 1e-12 * self.lip_radius):
            raise ValueError("melt surface reaches above the orifice plane (the charge would spill)")

    @property
    def slope(self):
        """dr/dz of the wall; zero for a cylinder, positive when opening toward the orifice."""
        if self.melt_radius is not None:
            return 0.0 if self.melt_depth == 0.0 else (self.lip_radius - self.melt_radius) / self.melt_depth
        return float(np.tan(self.taper_half_angle))

    @property
    def unit_melt_normal(self):
        n = np.asarray(self.melt_normal, float)
        return n / np.linalg.norm(n)

    @property
    def melt_origin(self):
        return np.array([0.0, 0.0, -self.melt_depth])

    @property
    def radius_at_melt(self):
        return self.lip_radius - self.slope * self.melt_depth

    def melt_boundary(self, n_points=720):
        """Points where the melt plane meets the wall, (n_points, 3)."""
        a, s, h = self.lip_radius, self.slope, self.melt_depth
        n = self.unit_melt_normal
        phi = 2.0 * np.pi * np.arange(n_points) / n_points
        c = n[0] * np.cos(phi) + n[1] * np.sin(phi)
        denom = s * c + n[2]
        if np.any(denom <= 0.0):
            raise ValueError("melt plane too steep for this taper")
        z = -(a * c + h * n[2]) / denom
        r = a + s * z
        if np.any(r <= 0.0):
            raise ValueError("melt plane passes below the frustum apex")
        return np.stack([r * np.cos(phi), r * np.sin(phi), z], axis=1)

    def sample_melt(self, n, rng):
        """Uniform points on the melt section (n, 3)."""
        nm, p0 = self.unit_melt_normal, self.melt_origin
        helper = np.array([1.0, 0.0, 0.0]) if abs(nm[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
        u = helper - helper.dot(nm) * nm
        u /= np.linalg.norm(u)
        v = np.cross(nm, u)
        bound = 1.001 * np.max(np.linalg.norm(self.melt_boundary() - p0, axis=1))
        out, have = [], 0
        while have < n:
            m = max(1024, int(1.5 * (n - have)))
            r = bound * np.sqrt(rng.random(m))
            ang = 2.0 * np.pi * rng.random(m)
            p = p0 + (r * np.cos(ang))[:, None] * u + (r * np.sin(ang))[:, None] * v
            inside = (np.hypot(p[:, 0], p[:, 1]) <= self.lip_radius + self.slope * p[:, 2]) & (p[:, 2] <= 0.0)
            out.append(p[inside])
            have += int(inside.sum())
        return np.concatenate(out)[:n]


@dataclass(frozen=True)
class CrucibleEvents:
    """Emission events from a random-walk simulation, in the crucible frame."""

    positions: np.ndarray  # (M, 3)
    normals: np.ndarray  # (M, 3) unit normals pointing into the crucible volume
    n_particles: int
    n_transmitted: int
    crucible: Crucible

    @property
    def transmission(self):
        return self.n_transmitted / self.n_particles

    @property
    def transmission_std(self):
        p = self.transmission
        return np.sqrt(p * (1.0 - p) / self.n_particles)


def _cosine_directions(normals, rng):
    """Lambertian (cosine-weighted) directions about each unit normal."""
    n = normals
    helper = np.where(np.abs(n[:, :1]) < 0.9, [[1.0, 0.0, 0.0]], [[0.0, 1.0, 0.0]])
    t1 = helper - np.sum(helper * n, axis=1, keepdims=True) * n
    t1 /= np.linalg.norm(t1, axis=1, keepdims=True)
    t2 = np.cross(n, t1)
    u1, u2 = rng.random(len(n)), rng.random(len(n))
    sin_t, phi = np.sqrt(u1), 2.0 * np.pi * u2
    cos_t = np.sqrt(1.0 - u1)
    return (sin_t * np.cos(phi))[:, None] * t1 + (sin_t * np.sin(phi))[:, None] * t2 + cos_t[:, None] * n


def _wall_normals(points, slope):
    r = np.hypot(points[:, 0], points[:, 1])
    outward = np.stack([points[:, 0], points[:, 1], -slope * r], axis=1)
    return -outward / np.linalg.norm(outward, axis=1, keepdims=True)


def _wall_hit(p, d, c, eps):
    """Smallest t > eps where p + t d meets the wall r = a + s z between melt and orifice."""
    a, s = c.lip_radius, c.slope
    nm, p0 = c.unit_melt_normal, c.melt_origin
    rz = a + s * p[:, 2]
    A = d[:, 0] ** 2 + d[:, 1] ** 2 - s * s * d[:, 2] ** 2
    B = 2.0 * (p[:, 0] * d[:, 0] + p[:, 1] * d[:, 1] - s * rz * d[:, 2])
    C = p[:, 0] ** 2 + p[:, 1] ** 2 - rz ** 2
    disc = B * B - 4.0 * A * C
    best = np.full(len(p), np.inf)
    ok = disc >= 0.0
    sq = np.sqrt(np.where(ok, disc, 0.0))
    with np.errstate(divide="ignore", invalid="ignore"):
        for t in ((-B - sq) / (2.0 * A), (-B + sq) / (2.0 * A)):
            hit = p + t[:, None] * d
            z = hit[:, 2]
            above_melt = (hit - p0) @ nm >= -eps
            valid = ok & np.isfinite(t) & (t > eps) & above_melt & (z <= eps) & (a + s * z > 0.0)
            best = np.where(valid & (t < best), t, best)
    return best


def simulate(crucible, n_particles, rng=None, max_bounces=100_000, record_events=True):
    """Random walk of `n_particles` Lambertian melt emissions through the crucible.

    With record_events=False only the transmission count is kept (long tubes produce many
    wall events).
    """
    rng = np.random.default_rng(rng)
    c = crucible
    eps = 1e-12 * c.lip_radius
    nm, p0 = c.unit_melt_normal, c.melt_origin
    has_walls = np.any(c.melt_boundary()[:, 2] < -eps)
    p = c.sample_melt(n_particles, rng)
    melt_normals = np.tile(nm, (n_particles, 1))
    d = _cosine_directions(melt_normals, rng)
    positions, normals = [p.copy()], [melt_normals]
    transmitted = 0
    for _ in range(max_bounces):
        if len(p) == 0:
            break
        t_wall = _wall_hit(p, d, c, eps) if has_walls else np.full(len(p), np.inf)
        dn = d @ nm
        with np.errstate(divide="ignore", invalid="ignore"):
            t_lip = np.where(d[:, 2] > 0.0, -p[:, 2] / d[:, 2], np.inf)
            t_melt = np.where(dn < 0.0, -((p - p0) @ nm) / dn, np.inf)
        exits = (t_lip <= t_wall) & (t_lip <= t_melt)
        wall = (t_wall < t_lip) & (t_wall <= t_melt)
        transmitted += int(exits.sum())
        p = p[wall] + t_wall[wall, None] * d[wall]
        n = _wall_normals(p, c.slope)
        d = _cosine_directions(n, rng)
        if record_events:
            positions.append(p.copy())
            normals.append(n)
    else:
        raise RuntimeError("random walk did not terminate; increase max_bounces")
    if not record_events:
        positions, normals = [np.empty((0, 3))], [np.empty((0, 3))]
    return CrucibleEvents(np.concatenate(positions), np.concatenate(normals), n_particles,
                          transmitted, crucible)


def next_event_flux(events, points, target_normal, *, subset=None, extra_visibility=None):
    """Arrival flux per emitted melt particle at local-frame `points` (N, 3), z > 0.

    `subset` restricts the sum to selected events (still normalised by all particles).
    `extra_visibility(starts, ends)` may return a boolean mask of blocked segments (for
    example, shutters) in the same frame.
    """
    pts = np.atleast_2d(np.asarray(points, float))
    m = np.asarray(target_normal, float)
    m = np.broadcast_to(m / np.linalg.norm(m, axis=-1, keepdims=True), pts.shape)
    e, nrm = events.positions, events.normals
    if subset is not None:
        e, nrm = e[subset], nrm[subset]
    a = events.crucible.lip_radius
    out = np.zeros(len(pts))
    step = max(1, _CHUNK_ELEMENTS // len(pts))
    for j in range(0, len(e), step):
        E, N = e[j:j + step], nrm[j:j + step]
        d = pts[None, :, :] - E[:, None, :]
        r2 = np.einsum("ijk,ijk->ij", d, d)
        r = np.sqrt(r2)
        cos_e = np.einsum("ijk,ik->ij", d, N) / r
        cos_t = -np.einsum("ijk,jk->ij", d, m) / r
        with np.errstate(divide="ignore", invalid="ignore"):
            s = -E[:, None, 2] / d[..., 2]  # parameter where the path crosses the orifice plane
        cross = E[:, None, :2] + s[..., None] * d[..., :2]
        vis = (d[..., 2] > 0.0) & (np.einsum("ijk,ijk->ij", cross, cross) <= a * a)
        vis &= (cos_e > 0.0) & (cos_t > 0.0)
        if extra_visibility is not None:
            vis &= ~extra_visibility(np.broadcast_to(E[:, None, :], d.shape),
                                     np.broadcast_to(pts[None, :, :], d.shape))
        out += np.where(vis, cos_e * cos_t / (np.pi * r2), 0.0).sum(axis=0)
    return out / events.n_particles
