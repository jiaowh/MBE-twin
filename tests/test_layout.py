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
