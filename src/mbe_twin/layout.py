"""Source placement in the growth chamber: bodies, shutters, tilt pivot and clearances.

Simplified solid geometry for the design-freeze feasibility check
(scripts/layout_feasibility.py). Every source is placed like `beam.source_on_cone`: its lip
(effusion cell) or plate centre (plasma source) at `throw` from the wafer centre, at a port
angle from the wafer normal and an azimuth, with its axis aimed `aim_offset` from the wafer
centre along the source's own azimuth. Solids:

- body: a solid cylinder of `body_radius` from the lip back along the axis to the mounting
  flange (`body_length`); the flange itself is a disk of `flange_radius` there;
- shutter: a disk blade of `shutter_radius`, `shutter_standoff` in front of the lip, on an arm
  that rotates about a pivot axis parallel to the source axis at `shutter_arm` from it. Open
  is the blade rotated by `shutter_open_deg` about that pivot towards `shutter_side`
  (+1 / -1: either sideways direction);
- the wafer holder: the lip ring around the wafer opening (`beam.HolderLip`) and the heater /
  manipulator assembly behind the wafer, a solid cylinder.

Pointing error and adjustment are tilts of the whole source about a pivot `pivot_back` behind
the lip along the axis: 0 tilts about the plate or lip centre (the assumption of
scripts/nitrogen_aim_tolerance.py), the flange distance tilts about the mounting flange, as a
tilting adapter or a flange machining error does, which also moves the plate sideways.

The dimensions are design inputs (data/design/design_envelope.json); none comes from a
drawing of the proposed machine.
"""

import heapq
import itertools
from dataclasses import dataclass, replace

import numpy as np
from scipy.spatial import cKDTree

from .beam import CylinderOccluder, DiskOccluder, EffusionSource, Wafer, source_on_cone


def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def rotate(v, axis, angle):
    """Rodrigues rotation of vector(s) v about unit `axis` by `angle` (rad)."""
    k = _unit(axis)
    v = np.asarray(v, float)
    c, s = np.cos(angle), np.sin(angle)
    return v * c + np.cross(k, v) * s + np.outer(v @ k, k).reshape(v.shape) * (1.0 - c)


@dataclass(frozen=True)
class SourcePort:
    name: str
    polar_deg: float
    azimuth_deg: float
    throw: float
    aim_offset: float = 0.0
    lip_radius: float = 0.0358       # beam-defining opening (crucible lip or active plate radius)
    body_radius: float = 0.060
    body_length: float = 0.30
    flange_radius: float = 0.1015    # CF150 outer radius
    shutter_radius: float = 0.045
    shutter_standoff: float = 0.025
    shutter_arm: float = 0.065
    shutter_open_deg: float = 90.0
    shutter_side: int = 1
    pivot_back: float = 0.0
    tilt: tuple = (0.0, 0.0, 0.0)    # rotation vector (rad) applied about the pivot

    def nominal(self, wafer):
        """Lip centre and aimed axis before any tilt."""
        src = source_on_cone(self.name, wafer, throw=self.throw, polar_angle=np.radians(self.polar_deg),
                             azimuth=np.radians(self.azimuth_deg), emission_rate=1.0, aim_offset=self.aim_offset)
        return np.asarray(src.position, float), np.asarray(src.axis, float)

    def frame(self, wafer):
        """Nominal axis, in-plane direction (perpendicular to the axis, away from the wafer
        centre's side of the plane of incidence: 'outwards') and sideways direction."""
        _, a0 = self.nominal(wafer)
        n = _unit(wafer.normal)
        e1, e2 = wafer.basis
        az = np.radians(self.azimuth_deg)
        radial = np.cos(az) * e1 + np.sin(az) * e2
        side = _unit(np.cross(n, radial))
        out = radial - (radial @ a0) * a0
        return a0, _unit(out), side

    def tilted(self, direction, angle_rad):
        """The same port with an extra tilt of `angle_rad` that turns the axis towards `direction`
        (a unit vector perpendicular to the nominal axis)."""
        return replace(self, tilt=tuple(np.asarray(self.tilt, float) + angle_rad * np.asarray(direction, float)))

    def pose(self, wafer):
        """Lip centre and axis after the tilt about the pivot."""
        pos, a0 = self.nominal(wafer)
        rv = np.asarray(self.tilt, float)
        ang = np.linalg.norm(rv)
        if ang == 0.0:
            return pos, a0
        # the tilt vector holds angle * direction; rotate about axis x direction
        k = np.cross(a0, rv / ang)
        pivot = pos - self.pivot_back * a0
        return pivot + rotate(pos - pivot, k, ang), _unit(rotate(a0, k, ang))

    def aim_point(self, wafer):
        """Where the axis meets the wafer plane (chamber coordinates)."""
        pos, a = self.pose(wafer)
        c, n = np.asarray(wafer.center, float), _unit(wafer.normal)
        return pos + ((c - pos) @ n) / (a @ n) * a

    def body(self, wafer):
        pos, a = self.pose(wafer)
        return CylinderOccluder(tuple(pos - self.body_length * a), tuple(a), self.body_radius, self.body_length,
                                name=f"{self.name} body")

    def flange_centre(self, wafer):
        pos, a = self.pose(wafer)
        return pos - self.body_length * a

    def _shutter_pivot(self, wafer):
        pos, a = self.pose(wafer)
        a0, out, side = self.frame(wafer)
        u = _unit(side - (side @ a) * a) * self.shutter_side
        return pos + self.shutter_standoff * a + self.shutter_arm * u, a, u

    def shutter(self, wafer, opening_deg=None):
        """Shutter blade at `opening_deg` (0 closed; default fully open)."""
        open_deg = self.shutter_open_deg if opening_deg is None else opening_deg
        pivot, a, u = self._shutter_pivot(wafer)
        centre = pivot + rotate(-self.shutter_arm * u, a, np.radians(open_deg) * self.shutter_side)
        return DiskOccluder(tuple(centre), tuple(a), self.shutter_radius, name=f"{self.name} shutter")

    def beam_source(self, wafer, cosine_exponent=1.0, emission_rate=1.0, **quadrature):
        """A flat cos^n emitter at the lip (for line-of-sight checks)."""
        pos, a = self.pose(wafer)
        return EffusionSource(self.name, tuple(pos), tuple(a), emission_rate, cosine_exponent, self.lip_radius,
                              **quadrature)


def segment_distance(p0, p1, q0, q1):
    """Minimum distance between segments p0-p1 and q0-q1 (sampled-free closed form)."""
    p0, p1, q0, q1 = (np.asarray(x, float) for x in (p0, p1, q0, q1))
    d1, d2, r = p1 - p0, q1 - q0, p0 - q0
    a, e, f = d1 @ d1, d2 @ d2, d2 @ r
    c, b = d1 @ r, d1 @ d2
    denom = a * e - b * b
    s = np.clip((b * f - c * e) / denom, 0.0, 1.0) if denom > 1e-18 else 0.0
    t = (b * s + f) / e
    if t < 0.0:
        t, s = 0.0, np.clip(-c / a, 0.0, 1.0)
    elif t > 1.0:
        t, s = 1.0, np.clip((b - c) / a, 0.0, 1.0)
    return float(np.linalg.norm((p0 + s * d1) - (q0 + t * d2)))


def disk_points(centre, normal, radius, n_r=8, n_phi=48):
    """Sample points over a disk (centre, rings, rim)."""
    n = _unit(normal)
    helper = np.array([1.0, 0.0, 0.0]) if abs(n[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    e1 = _unit(helper - (helper @ n) * n)
    e2 = np.cross(n, e1)
    r = radius * np.linspace(0.0, 1.0, n_r + 1)[1:]
    phi = np.linspace(0.0, 2 * np.pi, n_phi, endpoint=False)
    pts = [np.asarray(centre, float)[None, :]]
    for ri in r:
        pts.append(np.asarray(centre, float) + ri * (np.cos(phi)[:, None] * e1 + np.sin(phi)[:, None] * e2))
    return np.concatenate(pts)


def cylinder_clearance(c1, c2):
    """Gap between two `CylinderOccluder`s treated as capsules (a lower bound on the true gap)."""
    a1, a2 = _unit(c1.axis), _unit(c2.axis)
    b1, b2 = np.asarray(c1.base, float), np.asarray(c2.base, float)
    return segment_distance(b1, b1 + c1.length * a1, b2, b2 + c2.length * a2) - c1.radius - c2.radius


def point_to_cylinder(points, cyl):
    """Distance (m) from points to a solid finite cylinder (0 inside)."""
    a = _unit(cyl.axis)
    q = np.atleast_2d(points) - np.asarray(cyl.base, float)
    h = q @ a
    r = np.linalg.norm(q - h[:, None] * a, axis=1)
    dh = np.maximum(np.maximum(-h, h - cyl.length), 0.0)
    dr = np.maximum(r - cyl.radius, 0.0)
    return np.hypot(dh, dr)


def disk_to_cylinder(disk, cyl, **kw):
    return float(point_to_cylinder(disk_points(disk.center, disk.normal, disk.radius, **kw), cyl).min())


def disk_to_disk(d1, d2, **kw):
    p = disk_points(d1.center, d1.normal, d1.radius, **kw)
    q = disk_points(d2.center, d2.normal, d2.radius, **kw)
    return float(cKDTree(q).query(p, k=1)[0].min())


def disk_cover_radius(radius, n_r=8, n_phi=48):
    """Largest distance from any point of the disk to its nearest `disk_points` sample.

    Rings are R/n_r apart (a point is at most R/(2 n_r) from one) and samples on a ring at most
    2 r sin(pi / (2 n_phi)) apart along it, so the triangle inequality bounds the gap.
    """
    return radius / (2 * n_r) + 2 * radius * np.sin(np.pi / (2 * n_phi))


def disk_to_cylinder_bounds(disk, cyl, n_r=3, n_phi=24):
    """(certified lower bound, sampled value) of the distance between a disk and a solid cylinder."""
    s = disk_to_cylinder(disk, cyl, n_r=n_r, n_phi=n_phi)
    return s - disk_cover_radius(disk.radius, n_r, n_phi), s


def disk_to_disk_bounds(d1, d2, n_r=3, n_phi=24):
    """(certified lower bound, sampled value) of the distance between two disks."""
    s = disk_to_disk(d1, d2, n_r=n_r, n_phi=n_phi)
    return s - disk_cover_radius(d1.radius, n_r, n_phi) - disk_cover_radius(d2.radius, n_r, n_phi), s


def shutter_sweep(port, wafer, steps=10):
    """Blade positions from closed to fully open (samples only: see swept_lower_bound for the motion between)."""
    return [port.shutter(wafer, port.shutter_open_deg * k / steps) for k in range(steps + 1)]


def shutter_reach(port):
    """Largest distance of a blade point from the shutter's pivot axis: the arm plus the blade radius (the blade
    lies in a plane normal to that axis)."""
    return port.shutter_arm + port.shutter_radius


def sweep_step_bound(reach, step_rad):
    """Largest distance from a blade point, at any angle inside an arm rotation of `step_rad`, to the same point
    at the nearer end of the step. A point `reach` from the pivot axis moves on a circle, so it is at most the
    chord of half the step away: 2 reach sin(step / 4)."""
    return 2.0 * reach * np.sin(0.25 * step_rad)


def swept_lower_bound(gap, reaches, spans_deg, initial_steps=6, tol=2.5e-4, floor=np.inf, max_evals=3000):
    """Certified lower bound on a clearance over continuous shutter motion (one or two moving blades).

    gap(angles_deg) -> (certified lower bound, sampled value) of the clearance with blade k at angles_deg[k]
    (0 closed .. spans_deg[k] open); reaches[k] is shutter_reach of blade k. Over a box of angles every blade
    is within sweep_step_bound(reach, box width) of its pose at the corner nearest in each angle, so the
    clearance anywhere in the box is at least min(corner bounds) - sum of those distances. Branch and bound
    from an initial grid: the box with the lowest bound is split (every angle halved) until that bound is
    within `tol` of the lowest corner bound evaluated, reaches `floor` (a clearance large enough not to
    matter), or `max_evals` gap evaluations are spent; the bound reported is certified in every case.

    Returns dict: lower (certified over the whole motion), sampled (smallest sampled value at an evaluated
    pose: an upper estimate of the same minimum), at_deg (angles of that pose), evals, converged.
    """
    reaches = np.asarray(reaches, float)
    spans = np.asarray(spans_deg, float)
    dim = len(spans)
    cache = {}

    def at(angles):
        key = tuple(round(float(a), 9) for a in angles)
        if key not in cache:
            cache[key] = gap(key)
        return cache[key]

    def box_bound(lo, hi):
        corners = [at(c) for c in itertools.product(*zip(lo, hi))]
        slack = sum(sweep_step_bound(r, np.radians(h - l)) for r, l, h in zip(reaches, lo, hi))
        return min(c[0] for c in corners) - slack

    heap, k = [], 0
    edges = [np.linspace(0.0, s, initial_steps + 1) for s in spans]
    for idx in itertools.product(range(initial_steps), repeat=dim):
        lo = tuple(edges[d][i] for d, i in enumerate(idx))
        hi = tuple(edges[d][i + 1] for d, i in enumerate(idx))
        heapq.heappush(heap, (box_bound(lo, hi), k, lo, hi))
        k += 1
    converged = False
    while True:
        bound, _, lo, hi = heap[0]
        best = min(v[0] for v in cache.values())
        if bound >= best - tol or bound >= floor:
            converged = True
            break
        if len(cache) >= max_evals:
            break
        heapq.heappop(heap)
        mid = tuple(0.5 * (a + b) for a, b in zip(lo, hi))
        for half in itertools.product((0, 1), repeat=dim):
            clo = tuple(lo[d] if h == 0 else mid[d] for d, h in enumerate(half))
            chi = tuple(mid[d] if h == 0 else hi[d] for d, h in enumerate(half))
            heapq.heappush(heap, (box_bound(clo, chi), k, clo, chi))
            k += 1
    pose = min(cache, key=lambda a: cache[a][1])
    return {"lower": float(heap[0][0]), "sampled": float(cache[pose][1]), "at_deg": list(pose), "evals": len(cache),
            "converged": converged}


def holder_assembly(wafer, radius, depth, lip_height):
    """Heater and manipulator behind the wafer as one solid cylinder (from the lip face back)."""
    n = _unit(wafer.normal)
    base = np.asarray(wafer.center, float) + lip_height * n
    return CylinderOccluder(tuple(base), tuple(-n), radius, depth + lip_height, name="holder/heater assembly")


def wafer_frame():
    """The chamber frame used by all layout studies: wafer at the origin facing -z."""
    return Wafer(radius=0.100)
