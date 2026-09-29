"""V06, V08 and V09 for the direct-beam kernel, against closed-form or independent results."""

import numpy as np
import pytest
from scipy import integrate

from mbe_twin.beam import (DiskOccluder, EffusionSource, Wafer, arrival_flux, dose,
                           rotation_averaged_flux, source_on_cone, wafer_flux)

H = 0.4  # m, source-to-wafer distance for coaxial cases
Q = 1e18  # particles/s


def coaxial(n=1.0, aperture_radius=0.0, **kw):
    """Source at the origin emitting along +z toward a wafer at z = H facing down."""
    wafer = Wafer(radius=0.1, center=(0.0, 0.0, H), normal=(0.0, 0.0, -1.0))
    src = EffusionSource("Ga1", position=(0.0, 0.0, 0.0), axis=(0.0, 0.0, 1.0),
                         emission_rate=Q, cosine_exponent=n, aperture_radius=aperture_radius, **kw)
    return wafer, src


def point_source_flux(rho, n):
    r = np.hypot(rho, H)
    return Q * (n + 1.0) / (2.0 * np.pi) * H ** (n + 1.0) / r ** (n + 3.0)


def integrate_over_disk(wafer, sources, radius, nodes=64, occluders=()):
    """Area integral of an axisymmetric flux over a disk, by Gauss-Legendre in radius."""
    x, w = np.polynomial.legendre.leggauss(nodes)
    rho = 0.5 * radius * (x + 1.0)
    j = wafer_flux(sources, wafer, rho, 0.0, occluders=occluders)
    return np.sum(0.5 * radius * w * 2.0 * np.pi * rho * j)


@pytest.mark.parametrize("n", [1.0, 2.0, 3.5])
def test_point_source_matches_closed_form(n):
    wafer, src = coaxial(n)
    rho = np.linspace(0.0, 0.1, 11)
    assert np.allclose(wafer_flux([src], wafer, rho, 0.3), point_source_flux(rho, n),
                       rtol=1e-12, atol=0.0)


def test_inverse_square_on_axis():
    _, src = coaxial()
    near = arrival_flux([src], [0.0, 0.0, H], (0.0, 0.0, -1.0))
    far = arrival_flux([src], [0.0, 0.0, 2 * H], (0.0, 0.0, -1.0))
    assert near / far == pytest.approx(4.0, rel=1e-12)


@pytest.mark.parametrize("n", [1.0, 2.0])
def test_captured_fraction_conserves_particles(n):
    wafer, src = coaxial(n)
    radius = 0.3
    expected = Q * (1.0 - (H / np.hypot(H, radius)) ** (n + 1.0))
    assert integrate_over_disk(wafer, [src], radius) == pytest.approx(expected, rel=1e-10)


def test_finite_lambertian_disk_matches_view_factor():
    a1, a2 = 0.02, 0.1
    wafer, src = coaxial(1.0, aperture_radius=a1, radial_nodes=16, azimuthal_nodes=64)
    r1, r2 = a1 / H, a2 / H
    x = 1.0 + (1.0 + r2 ** 2) / r1 ** 2
    view_factor = 0.5 * (x - np.sqrt(x ** 2 - 4.0 * (r2 / r1) ** 2))
    assert integrate_over_disk(wafer, [src], a2) == pytest.approx(Q * view_factor, rel=1e-8)


def test_small_aperture_approaches_point_source():
    wafer, point = coaxial(2.0)
    _, small = coaxial(2.0, aperture_radius=1e-4)
    rho = np.linspace(0.0, 0.1, 6)
    assert np.allclose(wafer_flux([small], wafer, rho, 0.0),
                       wafer_flux([point], wafer, rho, 0.0), rtol=1e-6)


def test_no_flux_behind_source_or_onto_back_face():
    _, src = coaxial()
    assert arrival_flux([src], [0.0, 0.0, -H], (0.0, 0.0, 1.0)) == 0.0
    assert arrival_flux([src], [0.0, 0.0, H], (0.0, 0.0, 1.0)) == 0.0


def test_closed_shutter_blocks_everything():
    wafer, src = coaxial(aperture_radius=0.01)
    shutter = DiskOccluder(center=(0.0, 0.0, 0.05), normal=(0.0, 0.0, 1.0), radius=0.05)
    rho = np.linspace(0.0, 0.1, 21)
    assert np.all(wafer_flux([src], wafer, rho, 0.0, occluders=[shutter]) == 0.0)


def test_partial_shadow_has_geometric_edge():
    # A disk of radius s halfway to the wafer shadows rho < 2 s for a point source.
    wafer, src = coaxial()
    s = 0.02
    shutter = DiskOccluder(center=(0.0, 0.0, H / 2), normal=(0.0, 0.0, 1.0), radius=s)
    rho = np.array([0.0, 0.03, 0.039, 0.041, 0.06, 0.1])
    open_ = wafer_flux([src], wafer, rho, 0.0)
    shaded = wafer_flux([src], wafer, rho, 0.0, occluders=[shutter])
    inside = rho < 2 * s
    assert np.all(shaded[inside] == 0.0)
    assert np.array_equal(shaded[~inside], open_[~inside])


def test_occluder_behind_wafer_does_not_shadow():
    wafer, src = coaxial()
    behind = DiskOccluder(center=(0.0, 0.0, 2 * H), normal=(0.0, 0.0, 1.0), radius=1.0)
    rho = np.linspace(0.0, 0.1, 5)
    assert np.array_equal(wafer_flux([src], wafer, rho, 0.0, occluders=[behind]),
                          wafer_flux([src], wafer, rho, 0.0))


def test_rotation_is_right_handed_about_wafer_normal():
    wafer = Wafer(radius=0.1, center=(0.0, 0.0, H), normal=(0.0, 0.0, -1.0))
    e1, e2 = wafer.basis
    assert np.allclose(np.cross(e1, e2), wafer.normal)
    quarter_turn = wafer.points(0.05, 0.0, np.pi / 2)
    assert np.allclose(quarter_turn, np.asarray(wafer.center) + 0.05 * e2)


def tilted(azimuth=0.0, **kw):
    wafer = Wafer(radius=0.1, rotation_rate=2.0 * np.pi)
    src = source_on_cone("Ga", wafer, throw=0.4, polar_angle=np.radians(35.0), azimuth=azimuth,
                         emission_rate=Q, cosine_exponent=2.0, **kw)
    return wafer, src


def test_source_on_cone_geometry():
    wafer, src = tilted(aim_offset=0.0)
    pos = np.asarray(src.position)
    assert np.linalg.norm(pos - np.asarray(wafer.center)) == pytest.approx(0.4)
    assert np.dot(src.axis, -pos / np.linalg.norm(pos)) == pytest.approx(1.0)
    cos_polar = np.dot(pos, wafer.normal) / 0.4
    assert cos_polar == pytest.approx(np.cos(np.radians(35.0)))


def test_rotation_average_matches_independent_quadrature():
    wafer, src = tilted()
    rho = np.array([0.0, 0.05, 0.1])
    fast = rotation_averaged_flux([src], wafer, rho, n_angles=360)
    for r, value in zip(rho, fast):
        ref, _ = integrate.quad(lambda a: float(wafer_flux([src], wafer, r, 0.0, a)),
                                0.0, 2.0 * np.pi, epsabs=0.0, epsrel=1e-12, limit=200)
        assert value == pytest.approx(ref / (2.0 * np.pi), rel=1e-9)


def test_identical_sources_at_other_azimuths_do_not_change_radial_shape():
    # V08: rotation-averaged profiles of azimuth-shifted identical sources coincide,
    # so three of them triple the flux without flattening the normalised profile.
    rho = np.linspace(0.0, 0.1, 21)
    profiles = []
    for az in (0.0, 2.0 * np.pi / 3.0, 4.0 * np.pi / 3.0):
        wafer, src = tilted(azimuth=az)
        profiles.append(rotation_averaged_flux([src], wafer, rho, n_angles=360))
    for p in profiles[1:]:
        assert np.allclose(p, profiles[0], rtol=1e-12)
    wafer, _ = tilted()
    three = [tilted(azimuth=az)[1] for az in (0.0, 2.0 * np.pi / 3.0, 4.0 * np.pi / 3.0)]
    combined = rotation_averaged_flux(three, wafer, rho, n_angles=360)
    assert np.allclose(combined, 3.0 * profiles[0], rtol=1e-12)
    assert np.allclose(combined / combined[0], profiles[0] / profiles[0][0], rtol=1e-12)


def test_static_dose_is_flux_times_time():
    wafer, src = coaxial()
    rho = np.array([0.0, 0.07])
    expected = wafer_flux([src], wafer, rho, 0.0) * 123.4
    assert np.allclose(dose([src], wafer, rho, 0.0, 10.0, 133.4), expected, rtol=1e-12)


def test_whole_revolution_dose_equals_rotation_average():
    wafer, src = tilted()
    rho = np.array([0.02, 0.09])
    got = dose([src], wafer, rho, 1.3, 0.0, 5.0)  # five revolutions at 1 rev/s
    expected = rotation_averaged_flux([src], wafer, rho, n_angles=720) * 5.0
    assert np.allclose(got, expected, rtol=1e-9)


def test_input_validation():
    with pytest.raises(ValueError):
        Wafer(radius=0.0)
    with pytest.raises(ValueError):
        EffusionSource("x", (0, 0, 0), (0, 0, 1), emission_rate=-1.0)
    zero_axis = EffusionSource("x", (0, 0, 0), (0, 0, 0), emission_rate=1.0)
    with pytest.raises(ValueError):
        arrival_flux([zero_axis], [0, 0, 1], (0, 0, -1))
