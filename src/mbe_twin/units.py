"""SI constants and boundary unit conversions (verification case V01).

Everything inside the model is SI. Convert only where data enters or leaves.
"""

K_B = 1.380649e-23  # J/K, exact since the 2019 SI redefinition
N_A = 6.02214076e23  # 1/mol, exact

ATM_PA = 101325.0
TORR_PA = ATM_PA / 760.0
MBAR_PA = 100.0
ZERO_CELSIUS_K = 273.15


def mbar_to_pa(p):
    return p * MBAR_PA


def pa_to_mbar(p):
    return p / MBAR_PA


def torr_to_pa(p):
    return p * TORR_PA


def pa_to_torr(p):
    return p / TORR_PA


def celsius_to_kelvin(t):
    return t + ZERO_CELSIUS_K


def kelvin_to_celsius(t):
    return t - ZERO_CELSIUS_K


def l_per_s_to_m3_per_s(s):
    return s * 1e-3


def per_cm3_to_per_m3(c):
    return c * 1e6


def per_m3_to_per_cm3(c):
    return c * 1e-6


def per_cm2_s_to_per_m2_s(j):
    return j * 1e4


def sccm_to_particles_per_s(sccm, *, standard_pressure_pa, standard_temperature_k):
    """Particle rate for a mass-flow reading.

    The standard state is required because MFC vendors differ (0 C versus 20 C or 25 C).
    """
    volume_m3_per_s = sccm * 1e-6 / 60.0
    return standard_pressure_pa * volume_m3_per_s / (K_B * standard_temperature_k)


def pressure_from_throughput(particle_rate, *, gas_temperature_k, effective_speed_m3_s):
    """Well-mixed steady pressure P = N_dot k_B T / S (a benchmark, not a chamber model)."""
    return particle_rate * K_B * gas_temperature_k / effective_speed_m3_s


def thickness_from_dose(dose_per_m2, volume_per_unit_m3):
    """Film thickness from an incorporated dose of formula units.

    `volume_per_unit_m3` must come from a provenance-tracked material card; no default is
    supplied because it depends on material, polytype and strain state.
    """
    return dose_per_m2 * volume_per_unit_m3
