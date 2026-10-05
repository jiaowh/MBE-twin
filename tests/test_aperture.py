"""Aperture-plate source (mbe_twin.aperture)."""

import numpy as np
import pytest

from mbe_twin.aperture import aperture_plate_sources, hex_holes
from mbe_twin.beam import Wafer, arrival_flux, crucible_source_on_cone, source_on_cone
from mbe_twin.crucible import Crucible, simulate

WAFER = Wafer(radius=0.1)
ANGLE = np.radians(35.0)


def test_hex_holes_are_inside_and_evenly_spaced():
    xy = hex_holes(0.02, 0.002)
    assert np.all(np.hypot(xy[:, 0], xy[:, 1]) <= 0.02 + 1e-15)
    d = np.linalg.norm(xy[:, None, :] - xy[None, :, :], axis=-1)
    np.fill_diagonal(d, np.inf)
    assert d.min() == pytest.approx(0.002)
    # hexagonal packing: about (pi R^2) / (sqrt(3)/2 p^2) holes
    assert len(xy) == pytest.approx(np.pi * 0.02 ** 2 / (np.sqrt(3) / 2 * 0.002 ** 2), rel=0.1)


def test_single_hole_plate_equals_crucible_source():
    ev = simulate(Crucible(0.0005, 0.001), 20_000, rng=1)
    plate = aperture_plate_sources("N", WAFER, ev, [[0.0, 0.0]], throw=0.3, polar_angle=ANGLE,
                                   azimuth=0.0, total_rate=1e18)
    ref = crucible_source_on_cone("N", WAFER, ev, throw=0.3, polar_angle=ANGLE, azimuth=0.0,
                                  emission_rate=1e18 / ev.transmission)
    pts = WAFER.points(np.linspace(0.0, 0.1, 5), 0.3)
    assert arrival_flux(plate, pts, WAFER.normal) == pytest.approx(arrival_flux([ref], pts, WAFER.normal),
                                                                   rel=1e-12)


def test_thin_plate_of_uniform_holes_approaches_lambertian_disk():
    # Zero-thickness holes are Lambertian point-like emitters; a dense uniform pattern over
    # radius R then equals a Lambertian disk of radius R with the same total output.
    ev = simulate(Crucible(0.0002, 0.0), 2_000, rng=2)
    assert ev.transmission == 1.0
    xy = hex_holes(0.02, 0.002)
    plate = aperture_plate_sources("N", WAFER, ev, xy, throw=0.25, polar_angle=ANGLE, azimuth=0.0,
                                   total_rate=1.0)
    disk = source_on_cone("N", WAFER, throw=0.25, polar_angle=ANGLE, azimuth=0.0, emission_rate=1.0,
                          aperture_radius=0.02, radial_nodes=12, azimuthal_nodes=48)
    pts = WAFER.points(np.linspace(0.0, 0.1, 6), np.linspace(0.0, 2.0, 6))
    assert arrival_flux(plate, pts, WAFER.normal) == pytest.approx(arrival_flux([disk], pts, WAFER.normal),
                                                                   rel=2e-3)


def test_profile_weights_are_normalized():
    ev = simulate(Crucible(0.0002, 0.0), 1_000, rng=3)
    xy = hex_holes(0.01, 0.002)
    plate = aperture_plate_sources("N", WAFER, ev, xy, throw=0.25, polar_angle=ANGLE, azimuth=0.0,
                                   total_rate=5.0, profile=lambda r: 1.0 - 0.5 * (r / 0.01) ** 2)
    assert sum(s.emission_rate * ev.transmission for s in plate) == pytest.approx(5.0)
    with pytest.raises(ValueError):
        aperture_plate_sources("N", WAFER, ev, xy, throw=0.25, polar_angle=ANGLE, azimuth=0.0,
                               total_rate=1.0, profile=lambda r: -np.ones_like(r))


def test_axis_override_is_a_pointing_error_about_the_plate_centre():
    # The nominal axis reproduces the aimed plate; tilting the axis in the plane of incidence
    # equals re-aiming at the point where the tilted axis meets the wafer.
    ev = simulate(Crucible(0.0001, 0.0003), 2_000, rng=4)
    xy = hex_holes(0.01, 0.005)
    kw = dict(throw=0.35, polar_angle=np.radians(65.0), azimuth=0.0, total_rate=1.0)
    aimed = aperture_plate_sources("N", WAFER, ev, xy, aim_offset=0.075, **kw)
    pos = np.asarray(aimed[0].lip_center) - (aimed[0]._frame[:2].T @ xy[0])
    a0 = np.asarray(aimed[0].axis)
    pts = WAFER.points(np.linspace(0.0, 0.1, 5), np.linspace(0.0, 2.0, 5))
    same = aperture_plate_sources("N", WAFER, ev, xy, aim_offset=0.075, axis=a0, **kw)
    assert arrival_flux(same, pts, WAFER.normal) == pytest.approx(arrival_flux(aimed, pts, WAFER.normal), rel=1e-12)
    e1 = np.asarray(WAFER.basis[0])
    out = e1 - (e1 @ a0) * a0
    tilted = np.cos(np.radians(0.8)) * a0 + np.sin(np.radians(0.8)) * out / np.linalg.norm(out)
    n = np.asarray(WAFER.normal, float)
    hit = pos + ((np.asarray(WAFER.center) - pos) @ n) / (tilted @ n) * tilted
    shift = float((hit - np.asarray(WAFER.center)) @ e1)
    assert shift - 0.075 == pytest.approx(0.00743, abs=1e-4)  # not 0.35 m x 0.8 deg = 4.9 mm
    tilt = aperture_plate_sources("N", WAFER, ev, xy, aim_offset=0.075, axis=tilted, **kw)
    moved = aperture_plate_sources("N", WAFER, ev, xy, aim_offset=shift, **kw)
    assert arrival_flux(tilt, pts, WAFER.normal) == pytest.approx(arrival_flux(moved, pts, WAFER.normal), rel=1e-9)


def test_centre_override_moves_every_hole_with_the_plate():
    ev = simulate(Crucible(0.0005, 0.001), 2000, rng=2)
    holes = hex_holes(0.01, 0.005)
    kw = dict(throw=0.3, polar_angle=ANGLE, azimuth=0.0, total_rate=1.0)
    base = aperture_plate_sources("N", WAFER, ev, holes, **kw)
    shift = np.array([0.003, -0.002, 0.001])
    moved = aperture_plate_sources("N", WAFER, ev, holes, centre=np.asarray(base[0].lip_center) - np.asarray(
        base[0].lip_center) + np.asarray(aperture_plate_sources("N", WAFER, ev, [[0.0, 0.0]], **kw)[0].lip_center) + shift,
        **kw)
    for a, b in zip(base, moved):
        assert np.allclose(np.asarray(b.lip_center) - np.asarray(a.lip_center), shift, atol=1e-15)
        assert np.allclose(b.axis, a.axis)
