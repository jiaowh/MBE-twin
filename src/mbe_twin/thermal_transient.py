"""Transient of the axisymmetric heater-holder-wafer model (mbe_twin.heater), for the integrated twin.

C dT/dt = net gain(T), with the net gain (W per ring) and its Jacobian taken from
HeaterModel.residual, so the transient and the steady model share every radiation and
conduction term. Implicit Euler: the step is unconditionally stable, first order in time, and
its discrete energy balance closes to the Newton tolerance,
    sum C (T_new - T_old) = dt (zone power - front loss(T_new) - rim loss(T_new)),
with the losses evaluated independently from the radiosities (HeaterModel._result).

Lumped ring heat capacities. The wafer default is Si (2329 kg/m^3 x 900 J/kg/K x thickness; cp
rises from about 700 J/kg/K at 300 K to about 950 at 1000 K, so 900 is a high-temperature prior).
The heater element, ledge and platen capacities are machine inputs (material and thickness) and
are priors until the vendor supplies them. No thermal mass is assigned to radiation shields,
which the steady model does not contain either.
"""

import numpy as np

SI_DENSITY = 2329.0      # kg/m^3
SI_CP_PRIOR = 900.0      # J/kg/K, high-temperature prior (see module docstring)


def capacities(model, heater_areal, ledge_areal, platen_areal=None, wafer_areal=None):
    """Heat capacity (J/K) of every unknown of `model` from areal heat capacities (J m^-2 K^-1)."""
    g = model.geometry
    if wafer_areal is None:
        wafer_areal = SI_DENSITY * SI_CP_PRIOR * g.wafer_thickness
    n = model.nh + model.nw + model.nl + model.npl
    c = np.zeros(n)
    c[model.ih] = heater_areal * model.area_h
    c[model.iw] = wafer_areal * model.area_w
    c[model.il] = ledge_areal * model.area_l
    if model.npl:
        if platen_areal is None:
            raise ValueError("the platen needs an areal heat capacity")
        c[model.ipl] = platen_areal * model.area_h
    return c


def step(model, t_old, dt, capacity, heater_power, step_tol=1e-7, max_iter=50):
    """One implicit-Euler step under zone powers (W) held over the step; returns the new temperatures (K)."""
    if dt <= 0.0:
        raise ValueError("dt must be positive")
    t_old = np.asarray(t_old, float)
    c_dt = np.asarray(capacity, float) / dt
    t = t_old.copy()
    for _ in range(max_iter):
        r, j = model.residual(t, heater_power)
        f = c_dt * (t - t_old) - r
        jac = -j
        jac[np.diag_indices_from(jac)] += c_dt
        d = np.linalg.solve(jac, -f)
        d = np.clip(d, -0.3 * t, 0.3 * t)
        t = np.maximum(t + d, 50.0)
        if np.max(np.abs(d)) < step_tol:
            return t
    raise RuntimeError("heater transient step did not converge")


def fields(model, t, heater_power):
    """Wafer, heater and loss terms at a temperature vector (HeaterModel's result dictionary)."""
    return model._result(np.asarray(t, float), heater_power, None)


def energy_residual(model, t_old, t_new, dt, capacity, heater_power):
    """sum C dT - dt (power - losses(T_new)) in J; zero to the Newton tolerance for one implicit step."""
    r = fields(model, t_new, heater_power)
    stored = float(np.sum(np.asarray(capacity) * (np.asarray(t_new) - np.asarray(t_old))))
    return stored - dt * (float(np.sum(heater_power)) - r["front_loss"] - r["rim_loss"])
