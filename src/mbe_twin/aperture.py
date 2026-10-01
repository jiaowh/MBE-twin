"""Aperture-plate source (plasma cell): a pattern of short-tube holes emitting onto the wafer.

Representative model for the active-N boundary (ref/notes/NITROGEN_BOUNDARY.md). Each hole is
a cylindrical tube through the plate. Gas inside the source is taken as isotropic at the
plate's inner face, so the tube inlet emits a cosine-law flux (a `crucible.Crucible` whose
"melt" is the inlet at depth = plate thickness). Walls re-emit diffusely. Hole-wall
recombination of atoms is not modelled yet. Holes share one set of random-walk events and
differ only in position and weight; the weight carries a radial output profile across the
plate (discharge non-uniformity), a parameter to be bracketed, not a sourced value.
"""

import numpy as np

from .beam import CrucibleSource, crucible_source_on_cone


def hex_holes(plate_radius, pitch):
    """Hole centres (N, 2) on a hexagonal grid of `pitch`, all within plate_radius."""
    n = int(np.ceil(plate_radius / pitch)) + 1
    i, j = np.meshgrid(np.arange(-n, n + 1), np.arange(-n, n + 1), indexing="ij")
    x = pitch * (i + 0.5 * j)
    y = pitch * (np.sqrt(3.0) / 2.0) * j
    keep = np.hypot(x, y) <= plate_radius + 1e-12 * pitch
    return np.stack([x[keep], y[keep]], 1)


def aperture_plate_sources(name, wafer, hole_events, holes_xy, *, throw, polar_angle, azimuth,
                           total_rate, profile=None, aim_offset=0.0, axis=None):
    """One `CrucibleSource` per hole, with the plate centred where `crucible_source_on_cone`
    would put an orifice.

    total_rate is the net output of the plate (particles/s leaving the holes). profile(r),
    with r the hole's distance from the plate centre, sets relative output per hole
    (default uniform). Hole positions are in the plate plane, in the source frame's first two
    axes. `axis`, if given, replaces the aimed plate normal (e.g. to apply a pointing error);
    the plate centre stays where the cone puts it.
    """
    ref = crucible_source_on_cone(name, wafer, hole_events, throw=throw, polar_angle=polar_angle,
                                  azimuth=azimuth, emission_rate=1.0, aim_offset=aim_offset)
    if axis is not None:
        ref = CrucibleSource(name, ref.lip_center, tuple(np.asarray(axis, float) / np.linalg.norm(axis)),
                             1.0, hole_events)
    xy = np.asarray(holes_xy, float)
    w = np.ones(len(xy)) if profile is None else np.asarray(profile(np.hypot(xy[:, 0], xy[:, 1])), float)
    if np.any(w < 0.0) or w.sum() <= 0.0:
        raise ValueError("hole weights must be non-negative with a positive sum")
    w = w / w.sum()
    frame = ref._frame
    centre = np.asarray(ref.lip_center, float)
    per_inlet = total_rate / hole_events.transmission  # inlet emissions per net particle
    return [CrucibleSource(f"{name}[{k}]", tuple(centre + x * frame[0] + y * frame[1]), ref.axis,
                           per_inlet * wk, hole_events)
            for k, ((x, y), wk) in enumerate(zip(xy, w)) if wk > 0.0]
