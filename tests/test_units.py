"""V01: unit conversions and the pressure/flow examples quoted in mbe_twin.md section 8.4."""

import pytest

from mbe_twin import units as u


def test_pressure_conversions():
    assert u.mbar_to_pa(1.0) == 100.0
    assert u.torr_to_pa(760.0) == pytest.approx(101325.0, rel=1e-15)
    assert u.pa_to_torr(u.torr_to_pa(1.234e-5)) == pytest.approx(1.234e-5, rel=1e-15)
    assert u.pa_to_mbar(u.mbar_to_pa(3e-11)) == pytest.approx(3e-11, rel=1e-15)


def test_temperature_and_density_conversions():
    assert u.celsius_to_kelvin(1200.0) == pytest.approx(1473.15)
    assert u.kelvin_to_celsius(u.celsius_to_kelvin(700.0)) == pytest.approx(700.0)
    assert u.per_cm3_to_per_m3(1e18) == pytest.approx(1e24)
    assert u.per_m3_to_per_cm3(1e24) == pytest.approx(1e18)
    assert u.per_cm2_s_to_per_m2_s(1e14) == pytest.approx(1e18)
    assert u.l_per_s_to_m3_per_s(2000.0) == pytest.approx(2.0)


def test_sccm_matches_loschmidt_constant():
    # CODATA Loschmidt constant at 273.15 K and 101.325 kPa: 2.686780111e25 m^-3.
    rate = u.sccm_to_particles_per_s(1.0, standard_pressure_pa=101325.0,
                                     standard_temperature_k=273.15)
    assert rate == pytest.approx(2.686780111e25 * 1e-6 / 60.0, rel=1e-9)
    throughput = rate * u.K_B * 273.15
    assert throughput == pytest.approx(1.68875e-3, rel=1e-12)


def test_sccm_requires_standard_state():
    with pytest.raises(TypeError):
        u.sccm_to_particles_per_s(1.0)


def test_pressure_example_from_plan():
    rate = u.sccm_to_particles_per_s(2.0, standard_pressure_pa=101325.0,
                                     standard_temperature_k=273.15)
    p_273 = u.pressure_from_throughput(rate, gas_temperature_k=273.15, effective_speed_m3_s=2.0)
    p_300 = u.pressure_from_throughput(rate, gas_temperature_k=300.0, effective_speed_m3_s=2.0)
    assert u.pa_to_torr(p_273) == pytest.approx(1.2667e-5, rel=1e-4)
    assert u.pa_to_torr(p_300) == pytest.approx(1.3912e-5, rel=1e-4)


def test_thickness_from_constant_dose():
    # V09 conversion step: 1e22 units/m^2 at 2e-29 m^3/unit is 200 nm.
    assert u.thickness_from_dose(1e22, 2e-29) == pytest.approx(200e-9, rel=1e-14)
