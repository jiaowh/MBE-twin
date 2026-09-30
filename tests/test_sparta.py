"""SPARTA crucible geometry and slab post-processing (mbe_twin.sparta)."""

import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from mbe_twin.sparta import (LIP, MELT, WALL, batch_means, crucible_surface, edge_use,
                             expected_dump_steps, load_run_config, log_stats, prepare_run_dir,
                             propagate_slab, read_dumps, sparta_available, write_surf)

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
    subprocess.run([sys.executable, str(ROOT / "scripts/sparta_r07.py"), "r07_fm",
                    "--set", "steps_eq=4000", "--set", "steps_sample=6000", "--set", "particles=1e5",
                    "--set", "slab_D=[1.5, 2.0]", "--out", str(out)],
                   check=True, capture_output=True, env={**os.environ, "PYTHONPATH": str(ROOT / "src")})
    m = json.loads((out / "summary.json").read_text())["outputs"]
    area = np.diff(np.linspace(0.0, 48.0, 25) ** 2)
    inner = np.array(m["x_mm"]) <= 20.0
    s, f = np.array(m["sparta_flux"]), np.array(m["free_molecular_flux"])
    assert np.sum((s * area)[inner]) / np.sum((f * area)[inner]) == pytest.approx(1.0, abs=0.05)


def _write_dump(path, step, rows):
    lines = ["ITEM: TIMESTEP", str(step), "ITEM: NUMBER OF ATOMS", str(len(rows)),
             "ITEM: BOX BOUNDS oo oo oo", "-1 1", "-1 1", "-1 1", "ITEM: ATOMS id x y z vx vy vz"]
    lines += [" ".join(map(str, r)) for r in rows]
    path.write_text(chr(10).join(lines) + chr(10))


def test_run_dir_must_be_fresh_and_config_round_trips(tmp_path):
    cfg = {"case": "3.5", "slab_m": [0.08, 0.09]}
    work = prepare_run_dir(tmp_path / "run", cfg)
    assert load_run_config(work) == cfg
    with pytest.raises(FileExistsError):
        prepare_run_dir(work, cfg)  # holds config.json now
    with pytest.raises(FileNotFoundError):
        load_run_config(tmp_path)


def test_read_dumps_rejects_stale_or_missing_snapshots(tmp_path):
    steps = expected_dump_steps(100, 40, 20)
    assert steps == [100, 120, 140]
    for i, step in enumerate(steps):
        _write_dump(tmp_path / f"dump.slab.{step}", step, [(1, 0, 0, 0.1 * i, 0, 0, 1.0)] * (i + 1))
    pos, vel, snap = read_dumps(tmp_path, steps)
    assert len(pos) == 6 and list(snap) == [0, 1, 1, 2, 2, 2]
    _write_dump(tmp_path / "dump.slab.160", 160, [(1, 0, 0, 0, 0, 0, 1.0)])  # left from a longer run
    with pytest.raises(ValueError, match="unexpected"):
        read_dumps(tmp_path, steps)
    with pytest.raises(ValueError, match="missing"):
        read_dumps(tmp_path, expected_dump_steps(100, 80, 20)[:-1] + [200])
    with pytest.raises(ValueError):
        expected_dump_steps(100, 50, 20)


def test_batch_means_and_log_stats():
    mean, se = batch_means([[1.0, 2.0], [3.0, 2.0]])
    assert np.allclose(mean, [2.0, 2.0]) and np.allclose(se, [1.0, 0.0])
    log = chr(10).join(["junk", "Step CPU Np ", " 0 0 0 ", " 1000 1.5 42 ", "Loop time of 2",
                     "Step CPU Np", " 1000 0 42", ""])
    rows = log_stats(log)
    assert [r["Step"] for r in rows] == [0, 1000, 1000] and rows[1]["Np"] == 42


def test_streamed_accumulation_matches_loading_everything(tmp_path):
    from mbe_twin.sparta import accumulate_snapshots

    rng = np.random.default_rng(1)
    steps = expected_dump_steps(100, 200, 20)  # 11 snapshots
    for step in steps:
        n = int(rng.integers(0, 6))
        _write_dump(tmp_path / f"dump.slab.{step}", step,
                    [(k, *rng.normal(size=3), *rng.normal(size=3)) for k in range(n)])
    fn = lambda p, v: np.array([len(p), p[:, 0].sum() if len(p) else 0.0])
    acc = accumulate_snapshots(tmp_path, steps, fn, n_blocks=4)
    pos, vel, snap = read_dumps(tmp_path, steps)
    bounds = np.linspace(0, len(steps), 5).astype(int)
    for b, (a, c) in enumerate(zip(bounds[:-1], bounds[1:])):
        m = (snap >= a) & (snap < c)
        assert acc["blocks"][b] == pytest.approx([m.sum(), pos[m, 0].sum()])
        assert acc["n_blocks"][b] == c - a
    half = len(steps) // 2
    assert acc["halves"][1] == pytest.approx([(snap >= half).sum(), pos[snap >= half, 0].sum()])
    assert acc["total"] == pytest.approx([len(pos), pos[:, 0].sum()]) and acc["samples"] == len(pos)
