"""Source placement geometry (mbe_twin.layout) and the background-gas helpers (mbe_twin.vacuum)."""

import numpy as np
import pytest

from mbe_twin.beam import Wafer
from mbe_twin.layout import (SourcePort, cylinder_clearance, disk_to_disk, point_to_cylinder, rotate,
                             segment_distance)
from mbe_twin.vacuum import beam_mean_free_path, mean_speed, pressure_from_flow

WAFER = Wafer(radius=0.1)


def test_segment_distance_closed_forms():
    assert segment_distance((0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0)) == pytest.approx(1.0)  # parallel
    assert segment_distance((0, 0, 0), (1, 0, 0), (0.5, -1, 2), (0.5, 1, 2)) == pytest.approx(2.0)  # skew
    assert segment_distance((0, 0, 0), (1, 0, 0), (2, 0, 0), (3, 0, 0)) == pytest.approx(1.0)  # collinear gap
    assert segment_distance((0, 0, 0), (1, 0, 0), (3, 1, 0), (3, 2, 0)) == pytest.approx(np.hypot(2, 1))


def test_rotate_matches_rodrigues_special_cases():
    assert np.allclose(rotate([1.0, 0, 0], [0, 0, 1.0], np.pi / 2), [0, 1, 0])
    v = np.array([[1.0, 0, 0], [0, 0, 1.0]])
    assert np.allclose(rotate(v, [0, 0, 1.0], np.pi), [[-1, 0, 0], [0, 0, 1]])


def test_nominal_aim_and_untilted_pose():
    port = SourcePort("N", polar_deg=60.0, azimuth_deg=30.0, throw=0.35, aim_offset=0.08)
    aim = port.aim_point(WAFER)
    az = np.radians(30.0)
    e1, e2 = WAFER.basis
    assert np.allclose(aim, 0.08 * (np.cos(az) * e1 + np.sin(az) * e2), atol=1e-12)
    pos, a = port.pose(WAFER)
    assert np.linalg.norm(pos) == pytest.approx(0.35)


def test_tilt_about_the_lip_matches_axis_rotation_and_flange_pivot_moves_the_lip():
    port = SourcePort("N", polar_deg=65.0, azimuth_deg=0.0, throw=0.35, aim_offset=0.075)
    a0, out, side = port.frame(WAFER)
    t = np.radians(0.8)
    pos0, _ = port.pose(WAFER)
    pos, a = port.tilted(out, t).pose(WAFER)
    assert np.allclose(pos, pos0, atol=1e-15)
    assert np.allclose(a, np.cos(t) * a0 + np.sin(t) * out, atol=1e-12)  # nitrogen_aim_tolerance.tilted_axis
    flange = SourcePort("N", polar_deg=65.0, azimuth_deg=0.0, throw=0.35, aim_offset=0.075, pivot_back=0.30)
    pos_f, a_f = flange.tilted(out, t).pose(WAFER)
    assert np.allclose(a_f, a, atol=1e-12)
    assert np.linalg.norm(pos_f - pos0) == pytest.approx(2 * 0.30 * np.sin(t / 2), rel=1e-9)
    # the flange pivot moves the aim point further than the lip pivot does
    shift_lip = np.linalg.norm(port.tilted(out, t).aim_point(WAFER) - port.aim_point(WAFER))
    shift_flange = np.linalg.norm(flange.tilted(out, t).aim_point(WAFER) - flange.aim_point(WAFER))
    assert shift_flange > 1.5 * shift_lip


def test_shutter_closed_on_axis_and_open_clear_of_the_beam():
    port = SourcePort("Ga", polar_deg=46.0, azimuth_deg=0.0, throw=0.35)
    pos, a = port.pose(WAFER)
    closed = port.shutter(WAFER, 0.0)
    assert np.allclose(closed.center, pos + port.shutter_standoff * a, atol=1e-12)
    opened = port.shutter(WAFER)
    off_axis = np.asarray(opened.center) - pos
    off_axis -= (off_axis @ a) * a
    assert np.linalg.norm(off_axis) == pytest.approx(np.sqrt(2) * port.shutter_arm)
    # open blade clear of the lip cylinder; centre-to-centre distance of the two blade positions
    assert np.linalg.norm(off_axis) - port.shutter_radius > port.lip_radius
    assert disk_to_disk(closed, opened) == pytest.approx(np.sqrt(2) * port.shutter_arm - 2 * port.shutter_radius,
                                                         abs=2e-3)  # sampled rims


def test_cylinder_distances():
    port1 = SourcePort("a", polar_deg=40.0, azimuth_deg=0.0, throw=0.35, body_radius=0.05)
    port2 = SourcePort("b", polar_deg=40.0, azimuth_deg=180.0, throw=0.35, body_radius=0.05)
    gap = cylinder_clearance(port1.body(WAFER), port2.body(WAFER))
    assert gap == pytest.approx(2 * 0.35 * np.sin(np.radians(40.0)) - 0.1, rel=1e-9)  # nearest at the lips
    body = port1.body(WAFER)
    pos, a = port1.pose(WAFER)
    assert point_to_cylinder(pos - 0.1 * a, body)[0] == 0.0
    assert point_to_cylinder(pos + 0.02 * a, body)[0] == pytest.approx(0.02)


def test_pressure_and_mean_free_path():
    # HARDWARE_EVIDENCE correction 5: 1 sccm at 2000 L/s, gas at 273.15 K -> 8.44e-4 Pa (8.44e-6 mbar)
    assert pressure_from_flow(1.0, 2.0, t_gas=273.15) == pytest.approx(8.44375e-4, rel=1e-6)
    assert pressure_from_flow(1.0, 2.0, t_gas=300.0) == pytest.approx(8.44375e-4 * 300 / 273.15, rel=1e-9)
    assert beam_mean_free_path(0.0, 8e-10, 69.72, 1235.0) == np.inf
    # a stationary-gas limit: v_gas -> 0 gives lambda = 1 / (n sigma)
    lam = beam_mean_free_path(1e-3, 3.7e-10, 28.0134, 300.0, t_gas=300.0)
    n, sigma = 1e-3 / (1.380649e-23 * 300.0), np.pi * (3.7e-10) ** 2
    assert lam == pytest.approx(1.0 / (n * sigma * np.sqrt(2.0)), rel=1e-12)  # equal speeds: sqrt(2)
    assert mean_speed(300.0, 28.0134) == pytest.approx(476.2, rel=1e-3)


def test_disk_distance_bounds_bracket_the_exact_distance():
    from mbe_twin.beam import DiskOccluder
    from mbe_twin.layout import disk_cover_radius, disk_to_cylinder_bounds, disk_to_disk_bounds
    from mbe_twin.beam import CylinderOccluder
    # coplanar disks: exact gap = centre distance - radii; offset in angle so no sample sits on the closest points
    d1 = DiskOccluder((0.0, 0.0, 0.0), (0.0, 0.0, 1.0), 0.03)
    for ang in (0.0, 0.037, 0.11):
        c = 0.075 * np.array([np.cos(ang), np.sin(ang), 0.0])
        d2 = DiskOccluder(tuple(c), (0.0, 0.0, 1.0), 0.02)
        exact = 0.075 - 0.05
        lo, sampled = disk_to_disk_bounds(d1, d2, n_r=3, n_phi=24)
        assert lo <= exact + 1e-12 <= sampled + 1e-12
        assert sampled - lo == pytest.approx(disk_cover_radius(0.03, 3, 24) + disk_cover_radius(0.02, 3, 24))
    # disk facing a cylinder end: exact gap is the axial distance
    cyl = CylinderOccluder((0.0, 0.0, 0.02), (0.0, 0.0, 1.0), 0.01, 0.1)
    lo, sampled = disk_to_cylinder_bounds(d1, cyl, n_r=3, n_phi=24)
    assert lo <= 0.02 <= sampled + 1e-12
    # the covering radius really covers: no point of the disk is farther than it from a sample
    from mbe_twin.layout import disk_points
    pts = disk_points((0, 0, 0), (0, 0, 1), 0.03, n_r=3, n_phi=24)
    rng = np.random.default_rng(1)
    r = 0.03 * np.sqrt(rng.random(4000))
    t = 2 * np.pi * rng.random(4000)
    q = np.stack([r * np.cos(t), r * np.sin(t), np.zeros_like(r)], 1)
    nearest = np.min(np.linalg.norm(q[:, None] - pts[None], axis=-1), axis=1)
    assert nearest.max() <= disk_cover_radius(0.03, 3, 24)


def test_sweep_step_bound_is_the_half_step_chord():
    from mbe_twin.layout import sweep_step_bound
    reach, step = 0.111, np.radians(15.0)
    t = np.linspace(0.0, step, 2001)
    # distance of a point on the circle at angle t to the same point at the nearer end of the step
    moved = 2 * reach * np.sin(0.5 * np.minimum(t, step - t))
    assert moved.max() == pytest.approx(sweep_step_bound(reach, step), rel=1e-6)


def test_swept_bound_catches_a_minimum_between_sampled_shutter_angles():
    """A thin post next to the blade's outer rim at 7.5 deg, halfway between the 0 and 15 deg samples of a
    6-step sweep: the sampled poses miss the closest approach, the swept bound does not."""
    from mbe_twin.beam import CylinderOccluder
    from mbe_twin.layout import disk_cover_radius, disk_to_cylinder_bounds, shutter_reach, swept_lower_bound
    port = SourcePort("Ga", polar_deg=46.0, azimuth_deg=0.0, throw=0.35, shutter_radius=0.045, shutter_arm=0.065)
    pivot, a, u = port._shutter_pivot(WAFER)
    reach = shutter_reach(port)
    rim = pivot + rotate(-reach * u, a, np.radians(7.5) * port.shutter_side)       # outer rim point at 7.5 deg
    radial = (rim - pivot) / np.linalg.norm(rim - pivot)
    post = CylinderOccluder(tuple(rim + 0.003 * radial - 0.02 * a), tuple(a), 0.001, 0.04)  # 2 mm from the rim at 7.5 deg
    smp = {"n_r": 16, "n_phi": 256}

    def gap(ang):
        return disk_to_cylinder_bounds(port.shutter(WAFER, ang[0]), post, **smp)
    dense = np.linspace(0.0, 90.0, 721)
    true_min = min(gap((x,))[1] for x in dense)
    at = dense[int(np.argmin([gap((x,))[1] for x in dense]))]
    assert at == pytest.approx(7.5, abs=0.5)
    assert true_min == pytest.approx(0.002, abs=3e-4)
    sampled_poses = min(gap((x,))[1] for x in np.linspace(0.0, 90.0, 7))
    assert sampled_poses > true_min + 1e-3                    # the 7 sampled poses over-state the gap
    sw = swept_lower_bound(gap, [reach], [90.0], initial_steps=6, tol=1e-4)
    assert sw["converged"]
    assert sw["lower"] <= true_min                            # certified over the whole motion
    # refined near the minimum: within the disk samples' covering radius (the pose-level bound) and tol
    assert sw["lower"] >= true_min - disk_cover_radius(port.shutter_radius, 16, 256) - 2e-4
    assert sw["sampled"] == pytest.approx(true_min, abs=2e-4)


def test_swept_bound_with_two_moving_blades():
    """Two blades whose closest approach needs both at intermediate angles: the bound stays below every
    sampled pair and below the dense two-angle scan."""
    from mbe_twin.beam import DiskOccluder
    from mbe_twin.layout import disk_cover_radius, disk_to_disk_bounds, swept_lower_bound

    def blade(c, ang):
        t = np.radians(ang)
        return DiskOccluder((c[0] + 0.065 * np.cos(t), c[1] + 0.065 * np.sin(t), 0.0), (0.0, 0.0, 1.0), 0.02)
    c1, c2 = (0.0, 0.0), (0.0, 0.18)
    smp = {"n_r": 8, "n_phi": 96}

    def gap(ang):
        return disk_to_disk_bounds(blade(c1, 37.0 + ang[0]), blade(c2, 323.0 - ang[1]), **smp)
    grid = np.linspace(0.0, 90.0, 61)
    dense = min(gap((x, y))[1] for x in grid for y in grid)
    sw = swept_lower_bound(gap, [0.085, 0.085], [90.0, 90.0], initial_steps=6, tol=2e-4)
    assert sw["lower"] <= dense
    assert dense > 0.005
    assert sw["sampled"] == pytest.approx(dense, abs=5e-4)
    assert sw["lower"] >= dense - 2 * disk_cover_radius(0.02, 8, 96) - 5e-4
