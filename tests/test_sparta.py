"""SPARTA crucible geometry and slab post-processing (mbe_twin.sparta)."""

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from mbe_twin.sparta import (LIP, MELT, WALL, crucible_surface, edge_use, propagate_slab,
                             sparta_available, write_surf)

ROOT = Path(__file__).resolve().parents[1]

W = 0.02


@pytest.fixture(scope="module")
def mesh():
    return crucible_surface(0.00825, 0.066, W, taper_half_angle=np.radians(2.6), n_segments=64)


def test_surface_is_watertight_except_in_box_faces(mesh):
    p = mesh.points
    for (a, b), n in edge_use(mesh).items():
        if n == 1:  # open edges are allowed only inside one box face
            assert any(p[a, i] == p[b, i] and abs(p[a, i]) == W for i in (0, 1))
        else:
            assert n == 2


def test_orientation_is_consistent(mesh):
    directed = set()
    for tri in mesh.triangles:
        for e in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
            assert e not in directed  # a shared edge must be traversed once each way
            directed.add(e)


def test_normals_point_into_the_flow(mesh):
    n = mesh.normals()
    centre = mesh.points[mesh.triangles].mean(axis=1)
    assert np.allclose(n[mesh.types == MELT], [0, 0, 1])
    assert np.allclose(n[mesh.types == LIP], [0, 0, 1])
    radial = np.einsum("ij,ij->i", n[mesh.types == WALL][:, :2], centre[mesh.types == WALL][:, :2])
    assert np.all(radial < 0.0)  # bore wall faces the axis


def test_areas_match_polygonal_geometry(mesh):
    k, a = 64, mesh.areas()
    melt_r = 0.00825 - 0.066 * np.tan(np.radians(2.6))
    poly = lambda r: 0.5 * k * np.sin(2 * np.pi / k) * r * r
    assert a[mesh.types == MELT].sum() == pytest.approx(poly(melt_r), rel=1e-12)
    assert a[mesh.types == LIP].sum() == pytest.approx(4 * W * W - poly(0.00825), rel=1e-12)


def test_write_surf_layout(mesh, tmp_path):
    f = tmp_path / "surf.crucible"
    write_surf(mesh, f)
    lines = f.read_text().splitlines()
    assert f"{len(mesh.points)} points" in lines and f"{len(mesh.triangles)} triangles" in lines
    tri = lines[lines.index("Triangles") + 2].split()
    assert tri[0] == "1" and int(tri[1]) == mesh.types[0] and len(tri) == 5


def test_propagate_slab_recovers_point_source_flux():
    # Cosine-law point source at the origin, N emissions per unit time at random times; a
    # snapshot at time T of the particles inside the slab must give N cos^4(theta)/(pi R^2).
    rng = np.random.default_rng(3)
    n_total, t_end = 4_000_000, 1.0
    t0 = rng.uniform(0.0, t_end, n_total)
    cos_t = np.sqrt(rng.uniform(size=n_total))
    phi = rng.uniform(0.0, 2 * np.pi, n_total)
    speed = rng.uniform(0.5, 1.5, n_total) * 20.0
    sin_t = np.sqrt(1.0 - cos_t ** 2)
    v = speed[:, None] * np.stack([sin_t * np.cos(phi), sin_t * np.sin(phi), cos_t], 1)
    pos = v * (t_end - t0)[:, None]
    # The estimator is unbiased for any slab thickness in steady state; a thick slab keeps
    # many samples. Flow is developed where z1 / v_z < T: v_z >= 10 * 0.6 at cos >= 0.6,
    # i.e. radius <= 3.75 on the plane, so z1 / v_z <= 0.17 < T.
    slab, plane = (0.5, 1.0), 5.0
    edges = np.linspace(0.0, 3.75, 6)
    flux, _ = propagate_slab(pos, v, slab, plane, edges)
    rate = n_total / t_end
    exact = np.array([  # exact annulus average of rate cos^4 / (pi R^2) = rate R^2 / (pi r^4)
        rate * plane ** 2 * (1 / (plane ** 2 + a * a) - 1 / (plane ** 2 + b * b)) / (b * b - a * a)
        for a, b in zip(edges[:-1], edges[1:])]) / np.pi
    # Over 8 seeds the bin errors average within 0.7 % (unbiased) with up to 1.9 % scatter
    # (smallest annulus); the tolerance is 3 sigma.
    assert flux == pytest.approx(exact, rel=0.06)


@pytest.mark.skipif(not sparta_available(), reason="SPARTA (WSL) not installed")
def test_collisionless_sparta_matches_free_molecular_model(tmp_path):
    # Short collisionless run of the R07 L/D = 4 crucible (scripts/sparta_r07.py case fm).
    # Long runs agree with crucible.py to 1-2 % in absolute flux; this is a coarse check of
    # the whole pipeline: flux integrated inside 20 mm within 5 %.
    out = tmp_path / "fm"
    subprocess.run([sys.executable, str(ROOT / "scripts/sparta_r07.py"), "fm", "--steps-eq", "4000",
                    "--steps-sample", "6000", "--particles", "1e5", "--out", str(out)],
                   check=True, capture_output=True, env={**os.environ, "PYTHONPATH": str(ROOT / "src")})
    m = json.loads((out / "manifest.json").read_text())["outputs"]
    area = np.diff(np.linspace(0.0, 48.0, 25) ** 2)
    inner = np.array(m["x_mm"]) <= 20.0
    s, f = np.array(m["sparta_flux"]), np.array(m["free_molecular_flux"])
    assert np.sum((s * area)[inner]) / np.sum((f * area)[inner]) == pytest.approx(1.0, abs=0.05)
