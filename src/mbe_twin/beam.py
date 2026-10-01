"""Direct (line-of-sight) molecular-beam flux from effusion sources onto a rotating wafer.

Model scope (mbe_twin.md section 8.2): each source is a flat circular aperture, or a point
when its radius is zero. Each aperture area element emits
    d2N/(dOmega dA) = (Q/A) * (n+1)/(2*pi) * cos(theta)**n
where theta is measured from the source axis and Q is the total emission rate in
particles/s. With n = 1 this is ideal Lambertian (Knudsen) effusion. The exponent is a
fitted shape parameter for real crucibles, not a vendor constant.

Arrival flux at a target point with unit normal m (pointing from the growth face toward
the sources) is
    J = sum over elements of I * cos(psi) / r**2
in particles m^-2 s^-1. Occluders block any segment that crosses them: disks (shutters),
solid cylinders (source bodies) and the wafer holder's lip. Scattered, re-emitted and
gas-collision contributions are outside this kernel.

Background gas (optional `mean_free_path`): a beam particle that collides with the chamber's
background gas leaves the direct beam, so each path of length s is weighted by exp(-s / lambda).
This is direct-beam attenuation only; where the scattered particles arrive is not modelled.
Without a mean free path (the default, or an infinite one) the result is exactly unattenuated.

Deterministic quadrature is used instead of Monte Carlo: the direct beam has no
statistical noise to converge (see the audit, 2026-09-28).
"""

from dataclasses import dataclass, field

import numpy as np

# Keeps the (targets x aperture points x 3) work arrays to roughly 50 MB.
_CHUNK_ELEMENTS = 2_000_000


def _unit(v):
    v = np.asarray(v, dtype=float)
    n = np.linalg.norm(v)
    if n == 0.0:
        raise ValueError("zero-length direction vector")
    return v / n


def _plane_basis(normal):
    """Deterministic orthonormal in-plane basis (e1, e2) with e1 x e2 = normal."""
    normal = _unit(normal)
    helper = np.array([1.0, 0.0, 0.0]) if abs(normal[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    e1 = _unit(helper - helper.dot(normal) * normal)
    e2 = np.cross(normal, e1)
    return e1, e2


@dataclass(frozen=True)
class Wafer:
    """Flat circular wafer. `normal` points from the growth face toward the sources.

    Rotation is right-handed about `normal`: angle(t) = phase0 + rotation_rate * t (rad).
    """

    radius: float
    center: tuple = (0.0, 0.0, 0.0)
    normal: tuple = (0.0, 0.0, -1.0)
    rotation_rate: float = 0.0
    phase0: float = 0.0

    def __post_init__(self):
        if self.radius <= 0.0:
            raise ValueError("wafer radius must be positive")

    @property
    def basis(self):
        return _plane_basis(self.normal)

    def points(self, rho, phi, angle=0.0):
        """Chamber-frame positions of material points (rho, phi) at rotation angle `angle`."""
        rho, phi = np.broadcast_arrays(np.asarray(rho, float), np.asarray(phi, float))
        e1, e2 = self.basis
        a = phi + angle
        return (np.asarray(self.center, float)
                + rho[..., None] * (np.cos(a)[..., None] * e1 + np.sin(a)[..., None] * e2))

    def angle_at(self, t):
        return self.phase0 + self.rotation_rate * np.asarray(t, float)


@dataclass(frozen=True)
class EffusionSource:
    """Circular emitting aperture (radius 0 = point source)."""

    name: str
    position: tuple
    axis: tuple
    emission_rate: float
    cosine_exponent: float = 1.0
    aperture_radius: float = 0.0
    radial_nodes: int = 8
    azimuthal_nodes: int = 24

    def __post_init__(self):
        if self.emission_rate < 0.0:
            raise ValueError("emission rate must be non-negative")
        if self.cosine_exponent < 0.0:
            raise ValueError("cosine exponent must be non-negative")
        if self.aperture_radius < 0.0:
            raise ValueError("aperture radius must be non-negative")

    def quadrature(self):
        """Emitting points (M, 3) and weights (M,) that sum to 1."""
        pos = np.asarray(self.position, float)
        if self.aperture_radius == 0.0:
            return pos[None, :], np.ones(1)
        x, w = np.polynomial.legendre.leggauss(self.radial_nodes)
        a = self.aperture_radius
        rho = 0.5 * a * (x + 1.0)
        w_rho = 0.5 * a * w * rho  # integrates rho d(rho)
        phi = 2.0 * np.pi * np.arange(self.azimuthal_nodes) / self.azimuthal_nodes
        w_phi = 2.0 * np.pi / self.azimuthal_nodes  # spectrally accurate for periodic integrands
        e1, e2 = _plane_basis(self.axis)
        R, P = np.meshgrid(rho, phi, indexing="ij")
        pts = pos + R[..., None] * (np.cos(P)[..., None] * e1 + np.sin(P)[..., None] * e2)
        weights = (w_rho[:, None] * w_phi) * np.ones_like(P)
        return pts.reshape(-1, 3), (weights / weights.sum()).ravel()


def source_on_cone(name, wafer, *, throw, polar_angle, azimuth, emission_rate,
                   cosine_exponent=1.0, aperture_radius=0.0, aim_offset=0.0, **quadrature):
    """Place a source at `throw` metres from the wafer centre on a cone about the wafer normal.

    `polar_angle` is measured from the wafer normal and `azimuth` in the wafer's in-plane
    basis at zero rotation. The source axis points at the wafer centre shifted by
    `aim_offset` metres along the source's own azimuth direction.
    """
    c = np.asarray(wafer.center, float)
    n = _unit(wafer.normal)
    e1, e2 = wafer.basis
    radial = np.cos(azimuth) * e1 + np.sin(azimuth) * e2
    pos = c + throw * (np.sin(polar_angle) * radial + np.cos(polar_angle) * n)
    aim = c + aim_offset * radial
    return EffusionSource(name=name, position=tuple(pos), axis=tuple(_unit(aim - pos)),
                          emission_rate=emission_rate, cosine_exponent=cosine_exponent,
                          aperture_radius=aperture_radius, **quadrature)


@dataclass(frozen=True)
class DiskOccluder:
    """Opaque disk, e.g. a closed shutter blade."""

    center: tuple
    normal: tuple
    radius: float
    name: str = field(default="shutter")

    def blocks(self, starts, ends):
        """Boolean mask: does the open segment start->end cross this disk?"""
        c = np.asarray(self.center, float)
        n = _unit(self.normal)
        d = ends - starts
        denom = d @ n
        with np.errstate(divide="ignore", invalid="ignore"):
            s = ((c - starts) @ n) / denom
        hit = (np.abs(denom) > 1e-300) & (s > 0.0) & (s < 1.0)
        cross = starts + np.where(hit, s, 0.0)[..., None] * d
        return hit & (np.linalg.norm(cross - c, axis=-1) <= self.radius)


def _cylinder_interval(starts, ends, base, axis, radius):
    """Parameter interval (s_in, s_out) where segment start->end lies inside the infinite
    cylinder of `radius` about the line base + t * axis (empty when s_in >= s_out)."""
    d = ends - starts
    w = starts - base
    d_perp = d - (d @ axis)[..., None] * axis
    w_perp = w - (w @ axis)[..., None] * axis
    a = np.einsum("...k,...k->...", d_perp, d_perp)
    b = 2.0 * np.einsum("...k,...k->...", d_perp, w_perp)
    c = np.einsum("...k,...k->...", w_perp, w_perp) - radius ** 2
    disc = b * b - 4.0 * a * c
    parallel = a <= 1e-30
    with np.errstate(divide="ignore", invalid="ignore"):
        root = np.sqrt(np.where(disc > 0.0, disc, 0.0))
        s_in = np.where(parallel, np.where(c < 0.0, -np.inf, np.inf), (-b - root) / (2.0 * a))
        s_out = np.where(parallel, np.where(c < 0.0, np.inf, -np.inf), (-b + root) / (2.0 * a))
    miss = ~parallel & (disc <= 0.0)
    return np.where(miss, np.inf, s_in), np.where(miss, -np.inf, s_out)


@dataclass(frozen=True)
class CylinderOccluder:
    """Opaque solid cylinder from `base` along `axis` for `length`, e.g. a source body."""

    base: tuple
    axis: tuple
    radius: float
    length: float
    name: str = field(default="body")

    def blocks(self, starts, ends):
        a = _unit(self.axis)
        base = np.asarray(self.base, float)
        s_in, s_out = _cylinder_interval(starts, ends, base, a, self.radius)
        # slab 0 <= (P - base) . a <= length along the segment
        h0 = (starts - base) @ a
        dh = (ends - starts) @ a
        with np.errstate(divide="ignore", invalid="ignore"):
            t1, t2 = (0.0 - h0) / dh, (self.length - h0) / dh
        flat = np.abs(dh) <= 1e-300
        inside_slab = (h0 >= 0.0) & (h0 <= self.length)
        lo = np.where(flat, np.where(inside_slab, -np.inf, np.inf), np.minimum(t1, t2))
        hi = np.where(flat, np.where(inside_slab, np.inf, -np.inf), np.maximum(t1, t2))
        lo = np.maximum(np.maximum(lo, s_in), 0.0)
        hi = np.minimum(np.minimum(hi, s_out), 1.0)
        return hi > lo


@dataclass(frozen=True)
class HolderLip:
    """The wafer holder's lip: an opaque ring from `inner_radius` outwards that stands
    `height` proud of the wafer's growth face, towards the sources (along the wafer normal).

    A face-down wafer rests on this ledge, so its front surface lies `height` behind the lip.
    Grazing beams are shadowed just inside the opening. Wafer points under the lip
    (radius >= inner_radius) are covered and always blocked.
    """

    center: tuple
    normal: tuple
    inner_radius: float
    height: float
    name: str = field(default="holder lip")

    def blocks(self, starts, ends):
        n = _unit(self.normal)
        c = np.asarray(self.center, float)
        s_in, s_out = _cylinder_interval(starts, ends, c, n, self.inner_radius)
        d = ends - starts
        z0, dz = (starts - c) @ n, d @ n
        blocked = np.zeros(np.shape(z0), bool)
        for s in (s_in, s_out):  # crossings of the opening's wall
            ok = np.isfinite(s) & (s > 0.0) & (s < 1.0)
            z = z0 + np.where(ok, s, 0.0) * dz
            blocked |= ok & (z >= 0.0) & (z < self.height)
        for p in (starts, ends):  # an end point inside the ring itself (covered wafer)
            q = p - c
            z = q @ n
            r = np.linalg.norm(q - z[..., None] * n, axis=-1)
            blocked |= (r >= self.inner_radius) & (z >= -1e-12) & (z < self.height)
        return blocked


def _attenuation_length(mean_free_path, src):
    """Background-gas mean free path (m) for `src`, or None for no attenuation."""
    lam = mean_free_path(src) if callable(mean_free_path) else mean_free_path
    if lam is None or np.isinf(lam):
        return None
    if lam <= 0.0:
        raise ValueError("mean free path must be positive")
    return float(lam)


@dataclass(frozen=True, eq=False)
class CrucibleSource:
    """Effusion cell described by a simulated crucible (see `mbe_twin.crucible`).

    `lip_center` is the centre of the orifice plane and `axis` the outward crucible axis.
    `emission_rate` counts particles leaving the melt surface per second; the cell's net
    output is emission_rate * events.transmission.
    """

    name: str
    lip_center: tuple
    axis: tuple
    emission_rate: float
    events: object  # crucible.CrucibleEvents

    @property
    def _frame(self):
        e1, e2 = _plane_basis(self.axis)
        return np.stack([e1, e2, _unit(self.axis)])  # rows: local axes in chamber coordinates

    def to_local(self, points):
        return (np.asarray(points, float) - np.asarray(self.lip_center, float)) @ self._frame.T

    def to_chamber(self, local):
        return np.asarray(self.lip_center, float) + np.asarray(local, float) @ self._frame

    def flux(self, points, normal, occluders=(), subset=None):
        from .crucible import next_event_flux

        visibility = None
        if occluders:
            def visibility(starts, ends):
                s, e = self.to_chamber(starts), self.to_chamber(ends)
                blocked = np.zeros(s.shape[:-1], bool)
                for occ in occluders:
                    blocked |= occ.blocks(s, e)
                return blocked
        local_normal = _unit(normal) @ self._frame.T
        return self.emission_rate * next_event_flux(self.events, self.to_local(points), local_normal,
                                                    subset=subset, extra_visibility=visibility)


def level_melt_normal(axis, up=(0.0, 0.0, 1.0)):
    """Melt normal, in CrucibleSource's local frame, of a liquid charge that stays level.

    `axis` is the crucible axis and `up` the direction opposite to gravity, both in chamber
    coordinates. Use it as `Crucible(melt_normal=...)` before simulating that source's events.
    """
    e1, e2 = _plane_basis(axis)
    u = _unit(up)
    return (float(u @ e1), float(u @ e2), float(u @ _unit(axis)))


def crucible_source_on_cone(name, wafer, events, *, throw, polar_angle, azimuth, emission_rate,
                            aim_offset=0.0):
    """CrucibleSource with its orifice centre placed like `source_on_cone`."""
    ref = source_on_cone(name, wafer, throw=throw, polar_angle=polar_angle, azimuth=azimuth,
                         emission_rate=emission_rate, aim_offset=aim_offset)
    return CrucibleSource(name, ref.position, ref.axis, emission_rate, events)


def arrival_flux(sources, points, normal, occluders=(), mean_free_path=None):
    """Direct-beam arrival flux (particles m^-2 s^-1) at `points` (..., 3) with unit `normal`.

    `mean_free_path` (m): background-gas attenuation exp(-path / lambda), as one number for all
    sources or a callable source -> lambda; None or inf for none. Crucible sources take the path
    from the lip centre.
    """
    points = np.asarray(points, float)
    shape = points.shape[:-1]
    tgt = points.reshape(-1, 3)
    m = _unit(normal)
    total = np.zeros(len(tgt))
    for src in sources:
        if src.emission_rate == 0.0:
            continue
        lam = _attenuation_length(mean_free_path, src)
        if isinstance(src, CrucibleSource):
            f = src.flux(tgt, m, occluders)
            if lam is not None:
                f = f * np.exp(-np.linalg.norm(tgt - np.asarray(src.lip_center, float), axis=1) / lam)
            total += f
            continue
        emit, w = src.quadrature()
        axis = _unit(src.axis)
        n_exp = src.cosine_exponent
        prefactor = src.emission_rate * (n_exp + 1.0) / (2.0 * np.pi)
        step = max(1, _CHUNK_ELEMENTS // len(emit))
        for i in range(0, len(tgt), step):
            t = tgt[i:i + step]
            d = t[:, None, :] - emit[None, :, :]
            r2 = np.einsum("ijk,ijk->ij", d, d)
            r = np.sqrt(r2)
            cos_theta = (d @ axis) / r
            cos_psi = -(d @ m) / r
            ok = (cos_theta > 0.0) & (cos_psi > 0.0)
            if occluders:
                starts = np.broadcast_to(emit[None, :, :], d.shape)
                ends = np.broadcast_to(t[:, None, :], d.shape)
                for occ in occluders:
                    ok &= ~occ.blocks(starts, ends)
            contrib = np.where(ok, w * np.clip(cos_theta, 0.0, None) ** n_exp * cos_psi / r2, 0.0)
            if lam is not None:
                contrib = contrib * np.exp(-r / lam)
            total[i:i + step] += prefactor * contrib.sum(axis=1)
    return total.reshape(shape)


def wafer_flux(sources, wafer, rho, phi, angle=0.0, occluders=(), mean_free_path=None):
    """Instantaneous flux at material points (rho, phi) when the wafer is at `angle`."""
    return arrival_flux(sources, wafer.points(rho, phi, angle), wafer.normal, occluders, mean_free_path)


def rotation_averaged_flux(sources, wafer, rho, n_angles=360, occluders=(), mean_free_path=None):
    """Flux averaged over one full uniform rotation, as a function of radius.

    Uses equally spaced angles, which is spectrally accurate for this periodic integrand.
    Valid for dose only over whole revolutions with unchanged sources and shutters.
    """
    rho = np.asarray(rho, float)
    angles = 2.0 * np.pi * np.arange(n_angles) / n_angles
    analytic = [s for s in sources if not isinstance(s, CrucibleSource)]
    R, A = np.meshgrid(rho, angles, indexing="ij")
    total = wafer_flux(analytic, wafer, R, 0.0, A, occluders, mean_free_path).mean(axis=1)
    for src in sources:
        if isinstance(src, CrucibleSource) and src.emission_rate != 0.0:
            # Stratified estimator: event i is evaluated only at angle i mod n_angles. Its
            # expectation over events equals the average over all angles, at 1/n_angles the cost.
            n_events = len(src.events.positions)
            for k, angle in enumerate(angles):
                subset = np.arange(k, n_events, n_angles)
                pts = wafer.points(rho, 0.0, angle)
                f = src.flux(pts, wafer.normal, occluders, subset)
                lam = _attenuation_length(mean_free_path, src)
                if lam is not None:
                    f = f * np.exp(-np.linalg.norm(pts - np.asarray(src.lip_center, float), axis=-1) / lam)
                total += f
    return total


def dose(sources, wafer, rho, phi, t_start, t_end, samples_per_revolution=360, occluders=(), mean_free_path=None):
    """Arrived particles per m^2 at material points over [t_start, t_end] (midpoint rule in time).

    Sources and occluders are held fixed over the interval; split intervals at shutter events.
    """
    duration = t_end - t_start
    if duration < 0.0:
        raise ValueError("t_end precedes t_start")
    revolutions = abs(wafer.rotation_rate) * duration / (2.0 * np.pi)
    n = max(1, int(np.ceil(revolutions * samples_per_revolution)))
    times = t_start + (np.arange(n) + 0.5) * duration / n
    rho, phi = np.broadcast_arrays(np.asarray(rho, float), np.asarray(phi, float))
    acc = np.zeros(rho.shape)
    for angle in wafer.angle_at(times):
        acc += wafer_flux(sources, wafer, rho, phi, angle, occluders, mean_free_path)
    return acc * duration / n
