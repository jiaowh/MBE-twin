"""Level-melt SPARTA geometry and inclined-wafer transport (mbe_twin.sparta_source)."""

import numpy as np
import pytest

from mbe_twin import sparta
from mbe_twin.beam import (EffusionSource, Wafer, crucible_source_on_cone, level_melt_normal,
                           rotation_averaged_flux)
from mbe_twin.crucible import Crucible
from mbe_twin.sparta import LIP, MELT, WALL, edge_use
from mbe_twin.sparta_source import SourceRun, crucible_surface, wafer_profile

R, W = 0.03575, 0.1
ANGLE = np.radians(46.0)


def level_crucible(recess, angle=ANGLE):
    wafer = Wafer(radius=0.1)
    src = crucible_source_on_cone("Ga", wafer, None, throw=0.35, polar_angle=angle, azimuth=0.0,
                                  emission_rate=1.0)
    return Crucible(R, recess, melt_normal=level_melt_normal(src.axis, up=(0.0, 0.0, 1.0)))


def test_axis_normal_mesh_equals_benchmark_mesh():
    a = crucible_surface(Crucible(0.00825, 0.066, taper_half_angle=np.radians(2.6)), 0.02)
    b = sparta.crucible_surface(0.00825, 0.066, 0.02, taper_half_angle=np.radians(2.6))
    assert np.allclose(a.points, b.points, rtol=0, atol=1e-15)
    assert np.array_equal(a.triangles, b.triangles) and np.array_equal(a.types, b.types)


@pytest.mark.parametrize("recess", [0.040, 0.070, 0.120])
def test_level_melt_mesh_is_closed_oriented_and_level(recess):
    c = level_crucible(recess)
    mesh = crucible_surface(c, W)
    p = mesh.points
    directed = set()
    for (a, b), n in edge_use(mesh).items():
        if n == 1:
            assert any(p[a, i] == p[b, i] and abs(p[a, i]) == W for i in (0, 1))
        else:
            assert n == 2
    for tri in mesh.triangles:
        for e in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
            assert e not in directed
            directed.add(e)
    nrm = mesh.normals()
    assert np.allclose(nrm[mesh.types == MELT], c.unit_melt_normal)
    centre = p[mesh.triangles].mean(axis=1)
    wall = mesh.types == WALL
    assert np.all(np.einsum("ij,ij->i", nrm[wall][:, :2], centre[wall][:, :2]) < 0.0)
    assert np.allclose(nrm[mesh.types == LIP], [0, 0, 1])
    # cylinder cut by a plane tilted by 46 deg: ellipse of area pi R^2 / cos(46 deg)
    k = 64
    poly = 0.5 * k * np.sin(2 * np.pi / k) * R * R / np.cos(ANGLE)
    assert mesh.areas()[mesh.types == MELT].sum() == pytest.approx(poly, rel=1e-9)


def test_level_melt_below_spill_limit_is_rejected():
    with pytest.raises(ValueError, match="spill"):
        level_crucible(0.036)  # R tan 46 deg = 37.0 mm


def test_gas_volume_of_cylinder_is_independent_of_melt_tilt():
    run = SourceRun(level_crucible(0.07), "Ga", 1e-25, 1200.0, 1.0, 5e-10, 0.005)
    flat = SourceRun(Crucible(R, 0.07), "Ga", 1e-25, 1200.0, 1.0, 5e-10, 0.005)
    exact = np.pi * R * R * 0.07
    assert flat.gas_volume == pytest.approx(exact, rel=2e-3)
    assert run.gas_volume == pytest.approx(exact, rel=5e-3)


def test_wafer_profile_matches_rotating_point_source():
    # Lambertian point source at the orifice centre, sampled as in a DSMC slab snapshot.
    wafer = Wafer(radius=0.1)
    src = crucible_source_on_cone("x", wafer, None, throw=0.35, polar_angle=ANGLE, azimuth=0.0,
                                  emission_rate=1.0)
    # Only emissions within 30 deg of the axis are generated (the wafer subtends less than
    # about 22 deg); they carry the full source's rate n_total / (t_end sin^2 30 deg). The
    # slab ends at 0.02 m, crossed by any such particle (v_z >= 8.7) within 0.0023 s < t_end,
    # so the slab population is in steady state.
    rng = np.random.default_rng(5)
    n_total, t_end = 2_000_000, 0.004
    t0 = rng.uniform(0.0, t_end, n_total)
    cos_t = np.sqrt(rng.uniform(np.cos(np.radians(30.0)) ** 2, 1.0, n_total))
    phi = rng.uniform(0.0, 2 * np.pi, n_total)
    speed = rng.uniform(0.5, 1.5, n_total) * 20.0
    sin_t = np.sqrt(1.0 - cos_t ** 2)
    v = speed[:, None] * np.stack([sin_t * np.cos(phi), sin_t * np.sin(phi), cos_t], 1)
    pos = v * (t_end - t0)[:, None]
    edges = np.linspace(0.0, 0.1, 6)
    flux, _ = wafer_profile(pos, v, (0.01, 0.02), src, wafer, edges)
    ref = EffusionSource("x", src.lip_center, src.axis,
                         emission_rate=n_total / t_end / np.sin(np.radians(30.0)) ** 2)
    rho = np.linspace(0.0, 0.1, 201)
    exact_pts = rotation_averaged_flux([ref], wafer, rho, n_angles=180)
    mid = 0.5 * (rho[1:] + rho[:-1])
    fm = 0.5 * (exact_pts[1:] + exact_pts[:-1])
    exact = [np.sum((fm * mid)[(mid >= a) & (mid < b)]) / np.sum(mid[(mid >= a) & (mid < b)])
             for a, b in zip(edges[:-1], edges[1:])]
    assert flux == pytest.approx(exact, rel=0.03)
