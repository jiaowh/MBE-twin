"""Axisymmetric heater model: independent radiation reference and energy conservation."""

import pytest

from mbe_twin.heater import HeaterGeometry, HeaterModel, HeaterProperties
from mbe_twin.radiation import floating_disk_temperature

COARSE = dict(n_heater=30, n_wafer=25, n_over=3, n_outer=4)


@pytest.mark.parametrize("eps_h, eps_w", [(1.0, 1.0), (0.85, 0.7), (0.5, 0.3)])
def test_isothermal_limit_matches_ring_radiosity_reference(eps_h, eps_w):
    # Very conductive wafer and ledge, insulated fronts, heater at a set temperature: the lower
    # plane is one floating disk facing an isothermal disk (the Elmer V03 reference).
    g = HeaterGeometry(**COARSE)
    p = HeaterProperties(eps_heater=eps_h, eps_wafer=eps_w, eps_ledge=eps_w, k_wafer=1e7, k_ledge=1e7,
                         h_contact=1e9, eps_wafer_front=0.0, eps_ledge_front=0.0)
    r = HeaterModel(g, p).solve(heater_temperature=[1200.0])
    ref = floating_disk_temperature(g.ledge_outer, g.gap, 1200.0, 300.0, eps_h, eps_w)
    # coarse test rings: 0.14 K discretization error at eps 0.5/0.3 (0.03 K with the default rings,
    # 0.008 K with twice those), converging to the reference
    assert r["wafer_mean"] == pytest.approx(ref, abs=0.2)
    assert r["wafer_range"] < 0.05


def test_energy_balance_closes_in_both_modes():
    g = HeaterGeometry(zone_edges=(0.0, 0.06, 0.115), **COARSE)
    m = HeaterModel(g, HeaterProperties())
    r = m.solve(heater_power=[800.0, 1500.0])
    assert abs(r["energy_residual"]) < 1e-6 * r["zone_power"].sum()
    # temperature mode: the zone powers are derived from the heater balance and must close too
    rt = m.solve(heater_temperature=[1250.0, 1300.0])
    assert rt["zone_power"].min() > 0.0
    assert abs(rt["energy_residual"]) < 1e-6 * rt["zone_power"].sum()


def test_more_power_to_the_edge_zone_raises_the_wafer_edge():
    g = HeaterGeometry(zone_edges=(0.0, 0.08, 0.115), **COARSE)
    m = HeaterModel(g, HeaterProperties())
    a = m.solve(heater_power=[1500.0, 1000.0])
    b = m.solve(heater_power=[1500.0, 1500.0])
    assert b["t_wafer"][-1] - a["t_wafer"][-1] > b["t_wafer"][0] - a["t_wafer"][0] > 0.0


def test_platen_energy_balance_and_smoothing():
    g = HeaterGeometry(zone_edges=(0.0, 0.08, 0.115), platen=True, **COARSE)
    m = HeaterModel(g, HeaterProperties())
    r = m.solve(heater_power=[1500.0, 1200.0])
    assert abs(r["energy_residual"]) < 1e-6 * r["zone_power"].sum()
    rt = m.solve(heater_temperature=[1300.0, 1350.0])
    assert abs(rt["energy_residual"]) < 1e-6 * rt["zone_power"].sum()
    # the platen sits between heater and wafer in temperature
    assert r["t_heater"].min() > r["t_platen"].min() > r["t_wafer"].min()
