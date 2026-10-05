"""Observation operators: what the machine's instruments would read from the twin's true state (mbe_twin.md 11.1).

Each operator takes true fields and returns a reading plus a quality flag; the twin's controllers
see only readings, never the true fields (11.2). All instrument parameters are priors until the
selected instruments are specified; they are listed in the chamber definition.

- Pyrometer: area-weighted mean of the true wafer temperature over a centred spot, plus a fixed
  bias (emissivity setting, window transmission) and Gaussian noise. Below its valid range (Si is
  partly transparent at pyrometer wavelengths when cold) the reading is NaN with flag
  "below_range". Spectral response, reflected heater radiation and film interference (which moves
  the reading as the GaN layer grows, R16) are not modelled.
- Ion gauge: N2-equivalent pressure, times a relative sensitivity, plus relative Gaussian noise.
- Regime indicator (RHEED-like): the surface regime at the centre spot. Idealized: a real RHEED
  pattern needs calibration to identify the adlayer and droplet onsets.
- Thickness map: the final thickness on the usable radius at the mapping tool's radii, with an
  optional relative calibration error. Edge exclusion is the chamber's usable radius.
"""

import numpy as np


def ring_weights(rho, radius):
    """Area weights of radial samples restricted to r <= radius (samples own the ring between midpoints)."""
    rho = np.asarray(rho, float)
    mid = np.concatenate([[0.0], 0.5 * (rho[1:] + rho[:-1]), [rho[-1]]])
    lo, hi = np.minimum(mid[:-1], radius), np.minimum(mid[1:], radius)
    return np.pi * (hi ** 2 - lo ** 2)


def pyrometer(rho, t_wafer, rng, *, spot_radius, bias_k=0.0, noise_k=0.0, valid_min_k=873.0):
    """Centre-spot pyrometer reading (K) and quality flag."""
    w = ring_weights(rho, spot_radius)
    if w.sum() <= 0.0:
        raise ValueError("pyrometer spot contains no sample")
    true = float(np.sum(w * t_wafer) / w.sum())
    noise = float(rng.normal(0.0, noise_k)) if noise_k > 0.0 else 0.0
    if true < valid_min_k:
        return float("nan"), "below_range"
    return true + bias_k + noise, "ok"


def ion_gauge(pressure_pa, rng, *, sensitivity=1.0, noise_rel=0.0):
    noise = float(rng.normal(0.0, noise_rel)) if noise_rel > 0.0 else 0.0
    return pressure_pa * sensitivity * (1.0 + noise), "ok"


def regime_indicator(rho, regime, spot_radius):
    """Most common regime within the spot (ties go to the innermost sample)."""
    inside = np.asarray(rho) <= spot_radius
    values, counts = np.unique(np.asarray(regime)[inside], return_counts=True)
    return str(values[np.argmax(counts)]), "idealized"


def thickness_map(rho, thickness, map_radii, *, scale_error=0.0):
    """Thickness at the mapping tool's radii (nm), linearly interpolated from the twin's radial grid."""
    return np.interp(np.asarray(map_radii, float), rho, thickness) * (1.0 + scale_error), "ok"
