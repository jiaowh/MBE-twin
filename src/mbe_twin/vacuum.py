"""Growth-time background gas: chamber pressure from the nitrogen flow and the beam mean free path.

First piece of the vacuum package (planned in mbe_twin.md). Steady single-species balance
p = Q / S_eff, with Q the gas throughput at the chamber gas temperature: a flow in sccm
(standard 273.15 K, 101325 Pa) gives 1.68875e-3 Pa m^3/s at 273.15 K, multiplied by
T_gas / 273.15 at the chamber temperature (ref/notes/HARDWARE_EVIDENCE.md, correction 5).
Other gas loads, cryopanel-cooled gas and pressure gradients across the chamber are not
included.

The beam mean free path is the hard-sphere one for a fast beam in a stationary-distribution
gas: lambda = v_b / (n sigma <v_rel>), with sigma = pi ((d_beam + d_gas) / 2)^2 and
<v_rel> = sqrt(v_b^2 + v_gas^2) from the mean speeds. A total scattering cross-section is
larger than the hard-sphere one, so this underestimates attenuation (ref/notes/REFERENCE_CHAMBER.md).
"""

import numpy as np

K_B = 1.380649e-23
AMU = 1.66053907e-27
T_STD = 273.15
SCCM_PA_M3_S = 1.68875e-3  # 1 sccm at 273.15 K, 101325 Pa
D_N2 = 3.7e-10             # m, hard-sphere N2 (kinetic diameter)
M_N2 = 28.0134


def mean_speed(t_k, m_amu):
    return np.sqrt(8.0 * K_B * t_k / (np.pi * m_amu * AMU))


def pressure_from_flow(sccm, effective_speed_m3_s, t_gas=300.0):
    """Chamber pressure (Pa) for a flow in sccm and an effective pumping speed in m^3/s."""
    if effective_speed_m3_s <= 0.0:
        raise ValueError("effective pumping speed must be positive")
    return sccm * SCCM_PA_M3_S * (t_gas / T_STD) / effective_speed_m3_s


def beam_mean_free_path(pressure_pa, d_beam, m_beam_amu, t_beam, t_gas=300.0, d_gas=D_N2, m_gas=M_N2):
    """Mean free path (m) of a beam particle in background gas; inf at zero pressure."""
    if pressure_pa < 0.0:
        raise ValueError("pressure must be non-negative")
    if pressure_pa == 0.0:
        return np.inf
    n = pressure_pa / (K_B * t_gas)
    sigma = np.pi * (0.5 * (d_beam + d_gas)) ** 2
    v_b, v_g = mean_speed(t_beam, m_beam_amu), mean_speed(t_gas, m_gas)
    return float(v_b / (n * sigma * np.sqrt(v_b ** 2 + v_g ** 2)))
