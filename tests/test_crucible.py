"""Crucible emission model: Clausing transmission, exact disk limits and estimator consistency."""

import numpy as np
import pytest

from mbe_twin.beam import (CrucibleSource, EffusionSource, Wafer, rotation_averaged_flux,
                           wafer_flux)
from mbe_twin.crucible import Crucible, _cosine_directions, next_event_flux, simulate

A = 0.01  # m, lip radius


def _disk_vf(s, r=1.0):
    """View factor between coaxial equal disks of radius r separated by s."""
    s = np.asarray(s, float)
    return 1.0 + s * s / (2 * r * r) - s / (2 * r * r) * np.sqrt(s * s + 4 * r * r)


def ring_exchange(l_over_r, n=200):
    """Deterministic Clausing transmission: the tube wall is split into n rings with analytic
    ring/disk view factors (angular-coefficient method), independent of the random walk.
    Returns (transmission, ring view-factor matrix, ring->outlet, ring->melt, ring areas)."""
    z = np.linspace(0.0, l_over_r, n + 1)
    lo, hi, dz = z[:-1], z[1:], np.diff(z)
    to_out = (1 / (2 * dz)) * (_disk_vf(l_over_r - hi) - _disk_vf(l_over_r - lo))
    to_melt = (1 / (2 * dz)) * (_disk_vf(lo) - _disk_vf(hi))
    up = lambda i, zz: (1 / (2 * dz[i])) * (_disk_vf(zz - hi[i]) - _disk_vf(zz - lo[i]))
    dn = lambda i, zz: (1 / (2 * dz[i])) * (_disk_vf(lo[i] - zz) - _disk_vf(hi[i] - zz))
    m = np.empty((n, n))
    for i in range(n):
        for j in range(n):
            if j > i:
                m[i, j] = up(i, lo[j]) - up(i, hi[j])
            elif j < i:
                m[i, j] = dn(i, hi[j]) - dn(i, lo[j])
            else:
                m[i, j] = 1 - (1 / dz[i]) * (1 - _disk_vf(dz[i]))
    b = np.linalg.solve(np.eye(n) - m.T, _disk_vf(lo) - _disk_vf(hi))
    return float(_disk_vf(l_over_r) + b @ to_out), m, to_out, to_melt, 2 * np.pi * dz


def test_ring_reference_is_self_consistent():
    w, m, to_out, to_melt, area = ring_exchange(4.0, n=100)
    assert np.allclose(m.sum(axis=1) + to_out + to_melt, 1.0, atol=1e-12)
    assert np.allclose(area[:, None] * m, (area[:, None] * m).T, atol=1e-14)
    assert ring_exchange(4.0, n=200)[0] == pytest.approx(ring_exchange(4.0, n=400)[0], rel=1e-4)
    # Clausing's L/R = 1 value (0.672) as a literature sanity check.
    assert ring_exchange(1.0)[0] == pytest.approx(0.672, abs=5e-4)


def test_cosine_sampling_is_lambertian():
    rng = np.random.default_rng(1)
    n = np.tile([0.0, 0.0, 1.0], (400_000, 1))
    cos_t = _cosine_directions(n, rng)[:, 2]
    assert cos_t.min() >= 0.0
    assert cos_t.mean() == pytest.approx(2.0 / 3.0, abs=4 * np.sqrt(1 / 18 / 400_000))
    assert np.mean(cos_t ** 2) == pytest.approx(0.5, abs=0.002)


@pytest.mark.parametrize("l_over_r", [1.0, 2.0, 4.0, 10.0])
def test_cylinder_transmission_matches_ring_reference(l_over_r):
    ev = simulate(Crucible(A, l_over_r * A), 400_000, rng=7, record_events=False)
    reference = ring_exchange(l_over_r)[0]
    assert ev.transmission == pytest.approx(reference, abs=4 * ev.transmission_std + 2e-4)


def test_zero_depth_transmits_everything():
    ev = simulate(Crucible(A, 0.0), 10_000, rng=3)
    assert ev.transmission == 1.0
    assert len(ev.positions) == 10_000


def test_widening_crucible_transmits_more_than_cylinder():
    cyl = simulate(Crucible(A, 2 * A), 200_000, rng=5, record_events=False)
    cone = simulate(Crucible(A, 2 * A, melt_radius=0.6 * A), 200_000, rng=5, record_events=False)
    assert cone.transmission > cyl.transmission + 5 * cyl.transmission_std


def test_necked_crucible_rejected():
    with pytest.raises(ValueError):
        Crucible(A, 0.02, melt_radius=2 * A)


def lambertian_disk_view_factor(z, rho, a):
    """Differential element parallel to a disk of radius a, at height z and offset rho."""
    s = z * z + rho * rho + a * a
    return 0.5 * (1.0 - (z * z + rho * rho - a * a) / np.sqrt(s * s - 4.0 * a * a * rho * rho))


def test_flat_orifice_matches_exact_lambertian_disk():
    ev = simulate(Crucible(A, 0.0), 400_000, rng=11)
    z = 0.05
    rho = np.array([0.0, 0.01, 0.03, 0.08])
    pts = np.stack([rho, np.zeros_like(rho), np.full_like(rho, z)], axis=1)
    got = next_event_flux(ev, pts, (0.0, 0.0, -1.0))
    exact = lambertian_disk_view_factor(z, rho, A) / (np.pi * A * A)
    assert np.allclose(got, exact, rtol=0.01)


def test_next_event_estimator_conserves_transmitted_particles():
    # Flux integrated over a distant hemisphere equals the random-walk transmission.
    ev = simulate(Crucible(A, 2 * A), 40_000, rng=13)
    radius = 200 * A
    x, w = np.polynomial.legendre.leggauss(48)
    theta = 0.25 * np.pi * (x + 1.0)
    pts = radius * np.stack([np.sin(theta), np.zeros_like(theta), np.cos(theta)], axis=1)
    normals = -pts / radius
    flux = np.array([next_event_flux(ev, p[None], n)[0] for p, n in zip(pts, normals)])
    captured = np.sum(0.25 * np.pi * w * flux * radius ** 2 * 2 * np.pi * np.sin(theta))
    assert captured == pytest.approx(ev.transmission, rel=0.01)


def test_crucible_source_flat_orifice_agrees_with_deterministic_disk():
    wafer = Wafer(radius=0.1, center=(0.0, 0.0, 0.3), normal=(0.0, 0.0, -1.0))
    ev = simulate(Crucible(A, 0.0), 200_000, rng=17)
    mc = CrucibleSource("Ga", (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), 1e18, ev)
    det = EffusionSource("Ga", (0.0, 0.0, 0.0), (0.0, 0.0, 1.0), 1e18, 1.0, A,
                         radial_nodes=16, azimuthal_nodes=64)
    rho = np.linspace(0.0, 0.1, 6)
    assert np.allclose(wafer_flux([mc], wafer, rho, 0.0), wafer_flux([det], wafer, rho, 0.0),
                       rtol=0.005)


def test_crucible_rotation_average_matches_brute_force():
    wafer = Wafer(radius=0.1)
    from mbe_twin.beam import crucible_source_on_cone
    ev = simulate(Crucible(A, 2 * A), 20_000, rng=19)
    src = crucible_source_on_cone("Ga", wafer, ev, throw=0.3, polar_angle=np.radians(40.0),
                                  azimuth=0.0, emission_rate=1.0)
    rho = np.array([0.0, 0.05, 0.1])
    fast = rotation_averaged_flux([src], wafer, rho, n_angles=36)
    angles = 2 * np.pi * np.arange(36) / 36
    brute = np.mean([wafer_flux([src], wafer, rho, 0.0, a) for a in angles], axis=0)
    assert np.allclose(fast, brute, rtol=0.02)


def tilted_normal(deg, azimuth_deg=0.0):
    t, p = np.radians(deg), np.radians(azimuth_deg)
    return (np.sin(t) * np.cos(p), np.sin(t) * np.sin(p), np.cos(t))


def test_tilted_melt_samples_lie_on_plane_inside_cylinder():
    c = Crucible(A, 4 * A, melt_normal=tilted_normal(60.0))
    pts = c.sample_melt(200_000, np.random.default_rng(23))
    assert np.allclose((pts - c.melt_origin) @ c.unit_melt_normal, 0.0, atol=1e-15)
    assert np.all(np.hypot(pts[:, 0], pts[:, 1]) <= A * (1 + 1e-12))
    # The section of a cylinder projects onto its full cross-section, uniformly.
    assert np.mean(pts[:, 0] ** 2 + pts[:, 1] ** 2) == pytest.approx(A * A / 2, rel=0.01)


def test_melt_that_would_spill_is_rejected():
    with pytest.raises(ValueError, match="spill"):
        Crucible(A, 0.5 * A, melt_normal=tilted_normal(60.0))
    Crucible(A, 2.0 * A, melt_normal=tilted_normal(60.0))  # tan(60 deg) * A < 2 A: fits


def test_mirrored_tilt_gives_mirrored_flux():
    plus = simulate(Crucible(A, 3 * A, melt_normal=tilted_normal(40.0, 0.0)), 150_000, rng=29)
    minus = simulate(Crucible(A, 3 * A, melt_normal=tilted_normal(40.0, 180.0)), 150_000, rng=31)
    x = np.array([-0.04, -0.02, 0.02, 0.04])
    pts = np.stack([x, np.zeros_like(x), np.full_like(x, 0.1)], axis=1)
    mirrored = pts * np.array([-1.0, 1.0, 1.0])
    f_plus = next_event_flux(plus, pts, (0.0, 0.0, -1.0))
    f_minus = next_event_flux(minus, mirrored, (0.0, 0.0, -1.0))
    assert np.allclose(f_plus, f_minus, rtol=0.02)
    assert abs(f_plus[0] / f_plus[-1] - 1.0) > 0.02  # tilt makes the beam asymmetric (4.5 % here)


def test_tilted_melt_conserves_transmitted_particles():
    ev = simulate(Crucible(A, 3 * A, taper_half_angle=np.radians(2.6),
                           melt_normal=tilted_normal(50.0)), 40_000, rng=37)
    radius = 200 * A
    x, w = np.polynomial.legendre.leggauss(32)
    theta = 0.25 * np.pi * (x + 1.0)
    phi = 2 * np.pi * np.arange(24) / 24
    total = 0.0
    for th, wt in zip(theta, w):
        pts = radius * np.stack([np.sin(th) * np.cos(phi), np.sin(th) * np.sin(phi),
                                 np.full_like(phi, np.cos(th))], axis=1)
        flux = np.array([next_event_flux(ev, p[None], -p / radius)[0] for p in pts])
        total += 0.25 * np.pi * wt * flux.mean() * radius ** 2 * 2 * np.pi * np.sin(th)
    assert total == pytest.approx(ev.transmission, rel=0.015)


def test_level_melt_normal_is_gravity_in_the_source_frame():
    from mbe_twin.beam import level_melt_normal, source_on_cone

    wafer = Wafer(radius=0.1)  # faces down (normal -z); gravity along -z
    ref = source_on_cone("Ga", wafer, throw=0.3, polar_angle=np.radians(40.0), azimuth=0.7,
                         emission_rate=1.0)
    n = np.array(level_melt_normal(ref.axis))
    assert np.linalg.norm(n) == pytest.approx(1.0)
    assert n[2] == pytest.approx(np.cos(np.radians(40.0)))  # tilt from the axis = port angle
    src = CrucibleSource("Ga", ref.position, ref.axis, 1.0, simulate(Crucible(A, 0.0), 10, rng=1))
    up_local = src.to_local(np.array([0.0, 0.0, 1.0]) + np.asarray(ref.position))
    assert np.allclose(up_local, n)
