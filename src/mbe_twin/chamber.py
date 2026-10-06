"""Chamber definition for the integrated twin: subsystem operators on one radial wafer grid.

A chamber definition is a JSON document (built for the representative chamber by
scripts/twin_chamber.py from the layout comparison's map caches; built by hand in tests). It
holds rotation-averaged arrival maps and their pressure tables, the heater model inputs, the
pumping, the growth-law choice and instrument priors, so that one file plus a recipe determines
a twin run (its canonical hash goes into the run manifest).

Contract (SI; arrays on `rho_m`, the radial grid from the centre to the usable radius):
- ga: `shape` (vacuum arrival shape with the holder lip, centre 1), `att` (P x rho: arrival over
  the vacuum arrival at each `p_grid_Pa` pressure, background attenuation times the scattered-
  arrival factor), `reference` {cell_K, centre_flux_m2_s}: one DSMC record's absolute vacuum centre
  flux at its cell temperature. Other cell temperatures scale it by the Hertz-Knudsen factor
  p_vap(T) / sqrt(T) (Alcock 1984), the free-molecular scaling; the collisional change of the
  crucible transmission with temperature is not included (recorded as a disabled coupling).
- n: `map_per_atom_s` (arrival per unit plate output, m^-2 per atom/s, with the lip), `att`
  (P x rho), `eta` (active-N fraction of the feed's N atoms), `kn_per_sccm` and `kn_valid` (plate
  hole Knudsen number at 1 sccm and the free-molecular validity limit).
- vacuum: effective N2 speed, gas temperature, chamber volume and MFC time constant (priors).
- heater: HeaterGeometry / HeaterProperties keyword arguments, zone power fractions, areal heat
  capacities, element temperature limit.
- growth: droplet-onset law, N-rich decomposition bracket, atoms m^-2 s^-1 per nm/min of GaN.
- sensors: pyrometer, ion gauge, regime spot, thickness-map radii.
- operating_point: wafer_C, ga_cell_K, n2_sccm (what a recipe's "operating_point" resolves to).
"""

import copy
import dataclasses
import json
from pathlib import Path

import numpy as np

from . import thermal_transient
from .heater import HeaterGeometry, HeaterModel, HeaterProperties
from .manifest import canonical_hash
from .vacuum import SCCM_PA_M3_S, T_STD, pressure_from_flow
from .vapour import vapour_pressure

K_B = 1.380649e-23
N_ATOMS_PER_SCCM = 2.0 * SCCM_PA_M3_S / (K_B * T_STD)   # N atoms/s in 1 sccm of N2


def load_definition(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def interp_table(table, p, grid):
    """Ratio profile at pressure p, linear in log between grid pressures (as layout_comparison.att_at)."""
    grid = np.asarray(grid, float)
    if not 0.0 <= p <= grid[-1]:
        raise ValueError(f"pressure {p:.3g} Pa outside the table (0-{grid[-1]:g} Pa)")
    k = int(np.clip(np.searchsorted(grid, p, side="right") - 1, 0, len(grid) - 2))
    u = (p - grid[k]) / (grid[k + 1] - grid[k])
    t = np.asarray(table, float)
    return np.exp((1.0 - u) * np.log(t[k]) + u * np.log(t[k + 1]))


class Chamber:
    """Runtime operators built from a chamber definition."""

    def __init__(self, definition):
        self.definition = copy.deepcopy(definition)
        d = self.definition
        if d.get("schema_version") != "0.1":
            raise ValueError("chamber: schema_version must be '0.1'")
        self.label = d["label"]
        self.rho = np.asarray(d["rho_m"], float)
        self.p_grid = np.asarray(d["p_grid_Pa"], float)
        ga, n = d["ga"], d["n"]
        self.ga_shape = np.asarray(ga["shape"], float)
        self.ga_att = np.asarray(ga["att"], float)
        self.ga_ref_k = float(ga["reference"]["cell_K"])
        self.ga_ref_flux = float(ga["reference"]["centre_flux_m2_s"])
        self.n_map = np.asarray(n["map_per_atom_s"], float)
        self.n_att = np.asarray(n["att"], float)
        self.eta = float(n["eta"])
        self.kn_per_sccm = n.get("kn_per_sccm")
        self.kn_valid = n.get("kn_valid")
        for name, a in (("ga.shape", self.ga_shape), ("n.map_per_atom_s", self.n_map)):
            if a.shape != self.rho.shape:
                raise ValueError(f"chamber: {name} is not on rho_m")
        for name, a in (("ga.att", self.ga_att), ("n.att", self.n_att)):
            if a.shape != (len(self.p_grid), len(self.rho)):
                raise ValueError(f"chamber: {name} must be p_grid x rho")
        v = d["vacuum"]
        self.speed = float(v["effective_speed_m3_s"])
        self.t_gas = float(v["gas_temperature_K"])
        self.volume = float(v["chamber_volume_m3"])
        self.mfc_tau = float(v["mfc_time_constant_s"])
        h = d["heater"]
        self.heater = HeaterModel(HeaterGeometry(**h["geometry"]), HeaterProperties(**h["properties"]))
        self.zone_fractions = np.asarray(h["zone_fractions"], float)
        if len(self.zone_fractions) != self.heater.n_zones or abs(self.zone_fractions.sum() - 1.0) > 1e-9:
            raise ValueError("chamber: zone_fractions must match the zones and sum to 1")
        cap = h["areal_heat_capacity_J_m2K"]
        self.capacity = thermal_transient.capacities(self.heater, cap["heater"], cap["ledge"], cap.get("platen"),
                                                     cap.get("wafer"))
        self.element_limit = float(h["element_limit_K"])
        g = d["growth"]
        self.droplet_law = g["droplet_law"]
        self.n_rich_decomposition = g.get("n_rich_decomposition", "vacuum")
        self.k_atoms = float(g["atoms_per_m2_s_per_nm_min"])
        self.sensors = d["sensors"]
        self.operating_point = d.get("operating_point", {})
        self._ff = None

    def sha256(self):
        return canonical_hash(self.definition)

    # ---- sources and gas -------------------------------------------------------------------------
    def ga_centre_vacuum(self, cell_k):
        """Absolute vacuum centre Ga flux (m^-2 s^-1) at a cell temperature (Hertz-Knudsen scaling)."""
        hk = vapour_pressure("Ga", cell_k) / np.sqrt(cell_k)
        hk0 = vapour_pressure("Ga", self.ga_ref_k) / np.sqrt(self.ga_ref_k)
        return self.ga_ref_flux * float(hk / hk0)

    def ga_cell_for_centre_vacuum(self, flux):
        """Inverse of ga_centre_vacuum by bisection (monotonic in T)."""
        lo, hi = 600.0, 1600.0
        for _ in range(100):
            mid = 0.5 * (lo + hi)
            lo, hi = (mid, hi) if self.ga_centre_vacuum(mid) < flux else (lo, mid)
        return 0.5 * (lo + hi)

    def ga_flux(self, cell_k, pressure):
        return self.ga_centre_vacuum(cell_k) * self.ga_shape * interp_table(self.ga_att, pressure, self.p_grid)

    def n_output(self, flow_sccm):
        """Active-N atoms/s leaving the plate with the plasma on."""
        return self.eta * N_ATOMS_PER_SCCM * flow_sccm

    def n_flux(self, flow_sccm, pressure):
        return self.n_output(flow_sccm) * self.n_map * interp_table(self.n_att, pressure, self.p_grid)

    def pressure_eq(self, flow_sccm):
        return pressure_from_flow(flow_sccm, self.speed, self.t_gas)

    # ---- heater ------------------------------------------------------------------------------
    def zone_power(self, total_w):
        return total_w * self.zone_fractions

    def wafer_on_grid(self, t_nodes):
        h = self.heater
        return np.interp(self.rho, h.rw, np.asarray(t_nodes)[h.iw])

    def spot_mean(self, t_wafer_grid, spot_radius):
        from .sensors import ring_weights
        w = ring_weights(self.rho, spot_radius)
        return float(np.sum(w * t_wafer_grid) / w.sum())

    def feedforward_table(self, n=48):
        """Steady pyrometer-spot temperature and element maximum versus total heater power (model-based
        calibration table, as a real machine has from its power-temperature calibration)."""
        if self._ff is None:
            spot = self.sensors["pyrometer"]["spot_radius_m"]
            # power that puts the hottest element ring at its limit: bisection on the steady model
            lo, hi = 0.0, 500.0
            while self.heater.solve(heater_power=self.zone_power(hi))["t_heater"].max() < self.element_limit:
                lo, hi = hi, 2.0 * hi
            for _ in range(50):
                mid = 0.5 * (lo + hi)
                if self.heater.solve(heater_power=self.zone_power(mid))["t_heater"].max() < self.element_limit:
                    lo = mid
                else:
                    hi = mid
            p_lim = lo
            powers = p_lim * np.linspace(0.0, 1.0, n) ** 2
            temps, elem = [], []
            for p in powers:
                r = self.heater.solve(heater_power=self.zone_power(p), t0=600.0)
                temps.append(self.spot_mean(self.wafer_on_grid(_nodes(self.heater, r)), spot))
                elem.append(float(r["t_heater"].max()))
            self._ff = {"power_W": powers, "spot_K": np.array(temps), "element_K": np.array(elem), "p_limit_W": p_lim}
        return self._ff

    def feedforward_power(self, spot_k):
        ff = self.feedforward_table()
        return float(np.interp(spot_k, ff["spot_K"], ff["power_W"]))


def _nodes(model, r):
    """Full temperature vector from a HeaterModel result (heater | wafer | ledge | platen)."""
    parts = [r["t_heater"], r["t_wafer"], r["t_ledge"]]
    if model.npl:
        parts.append(r["t_platen"])
    return np.concatenate(parts)


def heater_definition(geometry, properties):
    """Keyword dictionaries of a heater geometry and properties, for a chamber definition."""
    g = dataclasses.asdict(geometry)
    g["zone_edges"] = list(g["zone_edges"])
    return g, dataclasses.asdict(properties)
