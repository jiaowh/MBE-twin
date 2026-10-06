"""Test-particle scattering (mbe_twin.scattering)."""

import numpy as np
import pytest

from mbe_twin.scattering import (AMU, K_B, Chamber, Gas, Plume, Source, collide, mean_speed, radial_arrival, track,
                                 fit_even)


def test_collision_conserves_momentum_and_energy():
    rng = np.random.default_rng(1)
    v = rng.normal(0, 500, (1000, 3))
    u = rng.normal(0, 300, (1000, 3))
    m, mg = 69.72, 28.0134
    w = collide(v, u, m, mg, rng)
    u_after = (m * v + mg * u - m * w) / mg
    assert np.allclose(m * v + mg * u, m * w + mg * u_after)
    e0 = m * np.sum(v * v, 1) + mg * np.sum(u * u, 1)
    e1 = m * np.sum(w * w, 1) + mg * np.sum(u_after * u_after, 1)
    assert np.allclose(e0, e1, rtol=1e-9)


def test_heavy_atom_on_light_gas_is_deflected_less_than_the_kinematic_limit():
    rng = np.random.default_rng(2)
    v = np.tile([[700.0, 0.0, 0.0]], (20000, 1))
    w = collide(v, np.zeros_like(v), 69.72, 28.0134, rng)   # target at rest
    ang = np.degrees(np.arccos(np.clip(w[:, 0] / np.linalg.norm(w, axis=1), -1, 1)))
    assert ang.max() <= np.degrees(np.arcsin(28.0134 / 69.72)) + 1e-6


def test_vacuum_point_source_hits_the_expected_solid_angle_and_never_scatters():
    rng = np.random.default_rng(3)
    h, a = 0.3, 0.1
    src = Source((0.0, 0.0, -h), (0.0, 0.0, 1.0), n_cos=0)   # isotropic over the hemisphere
    n = 200_000
    r, ind, counts = track(rng, n, src, mass_amu=69.72, temperature=1200.0, diameter=8e-10,
                           chamber=Chamber(holder_radius=a, wafer_radius=a))
    expected = 1 - h / np.hypot(h, a)
    assert len(r) / n == pytest.approx(expected, rel=0.02)
    assert not ind.any() and counts == {"gas": 0, "plume": 0}


def test_direct_survival_through_static_gas_is_exponential():
    rng = np.random.default_rng(4)
    h, n = 0.3, 100_000
    gas = Gas(density=1e18, temperature=1.0, mass_amu=1e6)   # effectively static, infinitely heavy targets
    src = Source((0.0, 0.0, -h), (0.0, 0.0, 1.0), n_cos=5000)  # a pencil beam to the wafer centre
    r, ind, _ = track(rng, n, src, mass_amu=14.0, temperature=600.0, diameter=3e-10, gas=gas)
    sigma = np.pi * ((3e-10 + 3.7e-10) / 2) ** 2
    assert np.sum(~ind) / n == pytest.approx(np.exp(-1e18 * sigma * h), rel=0.02)


def test_lambertian_plume_density_on_axis_matches_the_disk_solid_angle():
    pl = Plume(centre=(0.0, 0.0, 0.0), normal=(0.0, 0.0, 1.0), radius=0.03, flux=1e21, temperature=300.0, n_cos=1)
    z = np.array([0.02, 0.05, 0.2])
    n = pl.density(np.stack([np.zeros(3), np.zeros(3), z], 1))
    omega = 2 * np.pi * (1 - z / np.hypot(z, 0.03))
    assert n == pytest.approx(1e21 / (np.pi * mean_speed(300.0, 28.0134)) * omega, rel=0.01)
    # the bound holds everywhere in front of the disk
    pts = np.random.default_rng(5).uniform(-0.1, 0.1, (500, 3)) * [1, 1, 0.5] + [0, 0, 0.051]
    assert np.all(pl.density(pts) <= pl.density_bound(np.linalg.norm(pts, axis=1)) * (1 + 1e-12))


def brute_force_density(pl, x, n=1200):
    # fine area quadrature over the disk (midpoint grid), valid away from the plate surface
    g = (np.arange(n) + 0.5) / n * 2 - 1
    X, Y = np.meshgrid(g * pl.radius, g * pl.radius)
    keep = X * X + Y * Y <= pl.radius ** 2
    pts = np.stack([X[keep], Y[keep], np.zeros(keep.sum())], 1)
    da = (2 * pl.radius / n) ** 2
    d = x[None] - pts
    r2 = np.sum(d * d, 1)
    return pl.prefactor() * np.sum((d[:, 2] / np.sqrt(r2)) ** pl.n_cos * da / r2)


@pytest.mark.parametrize("n_cos", [1, 3, 4])
def test_plume_density_off_axis_matches_a_fine_area_quadrature(n_cos):
    pl = Plume(centre=(0.0, 0.0, 0.0), normal=(0.0, 0.0, 1.0), radius=0.03, flux=1e21, n_cos=n_cos)
    for x in ([0.01, 0.0, 0.01], [0.04, 0.01, 0.02], [0.05, -0.03, 0.1], [0.0, 0.2, 0.3]):
        x = np.array(x)
        assert pl.density(x[None])[0] == pytest.approx(brute_force_density(pl, x, n=2400), rel=0.01)


def test_plume_scatters_atoms_and_plane_surface_density_is_half_space():
    pl = Plume(centre=(0.0, 0.0, -0.3), normal=(0.0, 0.0, 1.0), radius=0.03, flux=1e21, n_cos=1)
    # just in front of a wide plate's centre, the density approaches 2 Phi / <v> (half-space effusion)
    assert pl.density(np.array([[0.0, 0.0, -0.3 + 1e-4]]))[0] == pytest.approx(
        2e21 / mean_speed(300.0, 28.0134), rel=0.05)
    rng = np.random.default_rng(6)
    src = Source((0.0, 0.0, -0.3), (0.0, 0.0, 1.0), n_cos=3, radius=0.03)
    _, ind, counts = track(rng, 20_000, src, mass_amu=14.007, temperature=600.0, diameter=3e-10, plume=pl)
    assert counts["plume"] > 0 and counts["gas"] == 0 and ind.any()


def test_radial_arrival_and_even_fit():
    edges = np.array([0.0, 0.05, 0.1])
    d, s = radial_arrival(np.array([0.01, 0.06, 0.07]), np.array([False, False, True]), 10, edges)
    assert d == pytest.approx([1 / (np.pi * 0.05 ** 2) / 10, 1 / (np.pi * (0.01 - 0.0025)) / 10])
    rb = np.linspace(0.01, 0.1, 10)
    y = 1 + 0.2 * (rb / 0.1) ** 2
    assert fit_even(rb, y, np.ones(10), [0.0, 0.1]) == pytest.approx([1.0, 1.2])


def test_constants():
    assert K_B == pytest.approx(1.380649e-23) and AMU == pytest.approx(1.66053907e-27)


@pytest.mark.parametrize("n_cos", [1, 4])
def test_plume_partner_directions_follow_the_local_distribution(n_cos):
    # just above a wide plate the gas directions follow cos^(n-1) dOmega over the hemisphere: <cos> = n / (n + 1)
    pl = Plume(centre=(0.0, 0.0, 0.0), normal=(0.0, 0.0, 1.0), radius=1.0, flux=1e21, n_cos=n_cos)
    x = np.tile([[0.0, 0.0, 1e-4]], (40_000, 1))
    _, u = pl.sample_partners(np.random.default_rng(7), x)
    cos_t = u[:, 2] / np.linalg.norm(u, axis=1)
    assert cos_t.min() >= 0.0
    assert cos_t.mean() == pytest.approx(n_cos / (n_cos + 1), abs=0.005)


def test_vacuum_arrival_matches_the_deterministic_direct_flux_absolutely():
    from mbe_twin.scattering import binned_direct_flux
    th = np.radians(46.0)
    pos = np.array([0.35 * np.sin(th), 0.0, -0.35 * np.cos(th)])
    src = Source(tuple(pos), tuple(np.array([0.09, 0.0, 0.0]) - pos), 2.9, radius=0.03)
    edges = 0.094 * np.sqrt(np.arange(6) / 5)
    n = 400_000
    r, ind, _ = track(np.random.default_rng(8), n, src, mass_amu=14.0, temperature=600.0, diameter=3e-10)
    d, _ = radial_arrival(r, ind, n, edges)
    assert d == pytest.approx(binned_direct_flux(src, edges), rel=0.03)


def test_wall_loss_adds_the_pump_share_of_the_wall_collision_rate():
    # 2026-10-06: the pump removes wall-returned atoms at S / (A <v> / 4) per wall hit; no pump keeps gamma
    from mbe_twin.scattering import wall_loss
    ch = Chamber()
    assert wall_loss(0.1, 0.0, ch, 14.007) == 0.1
    assert wall_loss(1.0, 4.0, ch, 14.007) == 1.0
    v = np.sqrt(8 * K_B * ch.wall_temperature / (np.pi * 14.007 * AMU))
    p = 4.0 / (4 * np.pi * ch.radius ** 2 * v / 4)
    assert wall_loss(1e-3, 4.0, ch, 14.007) == pytest.approx(1e-3 + (1 - 1e-3) * p)
    assert 0.008 < wall_loss(1e-3, 4.0, ch, 14.007) < 0.009


def test_pumping_removes_wall_returned_atoms():
    # with no wall loss, only the pump ends an atom's life: more pumping, fewer returned arrivals
    src = Source((0.2, 0.0, -0.2), (-0.2, 0.0, 0.2), 3.0, radius=0.02)
    hits = [len(track(np.random.default_rng(3), 4000, src, mass_amu=14.0, temperature=600.0, diameter=3e-10,
                      gamma=0.0, pump_speed=s)[0]) for s in (20.0, 200.0)]
    assert hits[0] > 1.5 * hits[1]
