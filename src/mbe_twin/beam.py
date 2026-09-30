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
in particles m^-2 s^-1. Disk occluders (shutters) block any segment that crosses them.
Scattered, re-emitted and gas-collision contributions are outside this kernel.

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


def arrival_flux(sources, points, normal, occluders=()):
    """Direct-beam arrival flux (particles m^-2 s^-1) at `points` (..., 3) with unit `normal`."""
    points = np.asarray(points, float)
    shape = points.shape[:-1]
    tgt = points.reshape(-1, 3)
    m = _unit(normal)
    total = np.zeros(len(tgt))
    for src in sources:
        if src.emission_rate == 0.0:
            continue
        if isinstance(src, CrucibleSource):
            total += src.flux(tgt, m, occluders)
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
            total[i:i + step] += prefactor * contrib.sum(axis=1)
    return total.reshape(shape)


def wafer_flux(sources, wafer, rho, phi, angle=0.0, occluders=()):
    """Instantaneous flux at material points (rho, phi) when the wafer is at `angle`."""
    return arrival_flux(sources, wafer.points(rho, phi, angle), wafer.normal, occluders)


def rotation_averaged_flux(sources, wafer, rho, n_angles=360, occluders=()):
    """Flux averaged over one full uniform rotation, as a function of radius.

    Uses equally spaced angles, which is spectrally accurate for this periodic integrand.
    Valid for dose only over whole revolutions with unchanged sources and shutters.
    """
    rho = np.asarray(rho, float)
    angles = 2.0 * np.pi * np.arange(n_angles) / n_angles
    analytic = [s for s in sources if not isinstance(s, CrucibleSource)]
    R, A = np.meshgrid(rho, angles, indexing="ij")
    total = wafer_flux(analytic, wafer, R, 0.0, A, occluders).mean(axis=1)
    for src in sources:
        if isinstance(src, CrucibleSource) and src.emission_rate != 0.0:
            # Stratified estimator: event i is evaluated only at angle i mod n_angles. Its
            # expectation over events equals the average over all angles, at 1/n_angles the cost.
            n_events = len(src.events.positions)
            for k, angle in enumerate(angles):
                subset = np.arange(k, n_events, n_angles)
                total += src.flux(wafer.points(rho, 0.0, angle), wafer.normal, occluders, subset)
    return total


def dose(sources, wafer, rho, phi, t_start, t_end, samples_per_revolution=360, occluders=()):
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
        acc += wafer_flux(sources, wafer, rho, phi, angle, occluders)
    return acc * duration / n
