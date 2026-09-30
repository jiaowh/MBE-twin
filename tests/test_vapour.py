"""Vapour pressure, evaporation flux and mean free path (mbe_twin.vapour)."""

import numpy as np
import pytest

from mbe_twin.units import K_B
from mbe_twin.vapour import (atomic_mass_kg, cross_section_from_knudsen, evaporation_flux,
                             mean_free_path, temperature_for_pressure, vapour_pressure)


@pytest.mark.parametrize("element, t_1pa, t_10pa", [("Ga", 1310.0, 1448.0), ("Al", 1482.0, 1632.0)])
def test_alcock_liquid_matches_tabulated_temperatures(element, t_1pa, t_10pa):
    # Temperatures for 1 and 10 Pa from the Wikipedia table "Vapor pressures of the elements",
    # compiled separately and rounded to 1 K. The equations sit 2-3 K (about 5 %) off it,
    # within their stated +/-5 % accuracy; this is a transcription check (a wrong digit in
    # A or B shifts p by far more).
    assert vapour_pressure(element, t_1pa) == pytest.approx(1.0, rel=0.06)
    assert vapour_pressure(element, t_10pa) == pytest.approx(10.0, rel=0.06)


def test_temperature_for_pressure_inverts_vapour_pressure():
    for element, t in (("Ga", 1223.15), ("Al", 1373.15)):
        assert temperature_for_pressure(element, vapour_pressure(element, t)) == pytest.approx(t, abs=1e-6)


def test_vapour_pressure_rejects_temperatures_above_range():
    with pytest.raises(ValueError):
        vapour_pressure("Ga", 1700.0)


def test_evaporation_flux_equals_kinetic_wall_flux():
    # Hertz-Knudsen p / sqrt(2 pi m k T) equals n <v> / 4 with n = p / kT, <v> = sqrt(8kT/(pi m)).
    p, t, m = 0.2, 1223.15, atomic_mass_kg("Ga")
    n = p / (K_B * t)
    v_mean = np.sqrt(8.0 * K_B * t / (np.pi * m))
    assert evaporation_flux(p, t, m) == pytest.approx(n * v_mean / 4.0, rel=1e-12)


def test_mean_free_path_and_cross_section_are_inverse():
    sigma = cross_section_from_knudsen(12.0, 0.0165, 0.04, 823.15)
    assert mean_free_path(0.04, 823.15, sigma) / 0.0165 == pytest.approx(12.0, rel=1e-12)
    # 1 / (sqrt(2) n sigma) with n = p / kT.
    assert mean_free_path(0.04, 823.15, sigma) == pytest.approx(
        1.0 / (np.sqrt(2.0) * (0.04 / (K_B * 823.15)) * sigma), rel=1e-12)
