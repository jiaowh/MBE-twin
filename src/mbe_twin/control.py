"""What the twin's realizable controllers know: a calibration frozen on the nominal state.

The controller model holds the calibration state's N and Ga arrival maps and pressure tables, the Ga
cell's calibrated flux-versus-temperature model and the centre-to-mean ratio of the net rate. It
never reads the truth chamber; its inputs are instrument readings (pyrometer, ion gauge, growth-rate
monitor, beam-flux monitor). Same protocol as scripts/realizable_controller.py:

- centre rate target: the wafer-mean target times the calibrated centre-to-mean ratio; the rate
  monitor re-sets the feed until the measured centre rate equals it;
- centre N flux estimate: the centre rate target plus the decomposition modelled at the reading;
- Ga target: the middle of the Ga/N window computed from the calibrated shapes (at the gauge
  pressure) and the droplet onset at the reading, times the N estimate;
- Ga cell: the calibrated Hertz-Knudsen model inverted for that arrival, divided by a correction
  factor kappa that the last BFM reading set (kappa = model arrival / measured arrival; 1 before any).
"""

import numpy as np

from .chamber import interp_table
from .vapour import vapour_pressure


def window_mid(n_shape, g_shape, n_centre, fcrit):
    """Middle of the centre Ga/N window for N = n_centre x n_shape and a Ga arrival shape (both centre 1)."""
    lo = float(np.max(n_shape / g_shape))
    hi = float(np.min((n_shape * n_centre + fcrit) / (n_centre * g_shape)))
    return 0.5 * (lo + hi) if hi > lo else lo * 1.02


class ControllerModel:
    def __init__(self, definition, chamber, params):
        cm = definition["controller_model"]
        self.p_grid = chamber.p_grid
        self.n_map = np.asarray(cm["n_map_per_atom_s"], float)
        self.n_att = np.asarray(cm["n_att"], float)
        self.ga_shape = np.asarray(cm["ga_shape"], float)
        self.ga_att = np.asarray(cm["ga_att"], float)
        self.ga_ref_k = float(cm["ga_reference"]["cell_K"])
        self.ga_ref_flux = float(cm["ga_reference"]["centre_flux_m2_s"])
        self.c_ratio = float(cm["centre_over_mean_rate"])
        self.rate_target = 1000.0 * float(cm["rate_target_um_h"]) / 60.0     # nm/min, wafer mean
        self.law = chamber.droplet_law
        self.k_atoms = chamber.k_atoms
        self.params = params

    def centre_rate_target(self):
        return self.rate_target * self.c_ratio

    def n_estimate(self, reading_k):
        return self.centre_rate_target() + float(self.params.decomposition(reading_k))

    def ga_target(self, reading_k, pressure):
        """Centre Ga arrival (nm/min) the controller aims for at a pyrometer reading and gauge pressure."""
        n_shape = self.n_map * interp_table(self.n_att, pressure, self.p_grid)
        g_shape = self.ga_shape * interp_table(self.ga_att, pressure, self.p_grid)
        n_est = self.n_estimate(reading_k)
        fcrit = float(self.params.critical_excess(self.law, reading_k))
        return window_mid(n_shape / n_shape[0], g_shape / g_shape[0], n_est, fcrit) * n_est

    def model_arrival(self, cell_k, pressure):
        """Centre Ga arrival (nm/min) the calibrated model predicts at a cell temperature."""
        hk = vapour_pressure("Ga", cell_k) / np.sqrt(cell_k)
        hk0 = vapour_pressure("Ga", self.ga_ref_k) / np.sqrt(self.ga_ref_k)
        vac = self.ga_ref_flux * float(hk / hk0)
        return vac * self.ga_shape[0] * float(interp_table(self.ga_att, pressure, self.p_grid)[0]) / self.k_atoms

    def cell_for(self, arrival, pressure, kappa=1.0):
        """Cell temperature whose model arrival divided by kappa equals `arrival`."""
        lo, hi = 600.0, 1600.0
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            lo, hi = (mid, hi) if self.model_arrival(mid, pressure) / kappa < arrival else (lo, mid)
        return 0.5 * (lo + hi)
