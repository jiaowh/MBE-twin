"""Integrated chamber twin, first slice: a recipe run through heater, sources, gas, surface and instruments.

Couples the Stage A subsystem operators in time on one radial wafer grid (mbe_twin.md section 12;
PHASE1_CHAMBER_PLAN.md "integrated thickness and conserved inventories through a shutter event"):

    recipe -> setpoints -> controllers (see readings only) -> heater power, cell temperature, N2 feed
    heater transient (thermal_transient) -> wafer temperature map
    feed -> MFC lag -> chamber pressure (well-mixed, V/S) -> attenuation / scattering tables
    cell temperature, pressure, shutters -> Ga and active-N arrival maps (chamber.Chamber)
    arrival + temperature -> surface state (surface.advance): thickness, droplets, atom ledgers
    true state -> observation operators (sensors) -> readings, logged with quality flags

Time stepping: each recipe step is divided into equal sub-steps no longer than dt_max, so shutter
and setpoint events fall on step boundaries and are never stepped across. The heater uses implicit
Euler; the MFC and the pressure are first-order systems integrated exactly over a sub-step (the
pressure with the sub-step's mean feed); the Ga cell follows its setpoint ramp; arrival is
evaluated with the sub-step's mean feed and pressure and the cell at mid-step; the surface uses
the wafer temperature at the end of the sub-step. The heater controller acts on the pyrometer
reading sampled at the start of the sub-step (zero-order hold).

Heater control. "power" holds a total power; "feedforward" applies the power the steady model
gives for the target spot temperature (a model-based calibration table); "pyrometer" adds a PI
trim on the pyrometer reading to that feedforward. The PI gains are a hypothesis: internal-model
tuning of the lumped first-order plant around the operating point (gain dT/dP from the table, time
constant = total heat capacity x gain, closed-loop time constant half of it), not identified plant
dynamics. The total power is clamped to the steady power that puts the hottest element ring at
its limit; because the heater network is cooperative (more power never cools a ring), a clamped
power keeps the element below its limit at all times when it starts colder.

Realizable Ga and N control (recipe "ga_cell": {"target_K": "steered"}, "n2_sccm": "rate_monitor", "bfm"
steps; control.ControllerModel): the controllers know only the calibration state frozen in the chamber's
controller_model and instrument readings. The rate monitor measures the centre net rate over
`sensors.rate_monitor.window_s` of growth (relative error and noise) and scales the commanded feed by
(target + modelled decomposition) / (measured + modelled decomposition); the Ga cell follows the window
middle at the reading through the calibrated model, corrected by the last BFM reading. The controllers
read the chamber pressure only through the ion gauge (sensors.ion_gauge, with its sensitivity and noise),
sampled at the start of each sub-step together with the pyrometer; the gas itself evolves from the true
feed. The logged gauge_Pa is that controller reading (audit follow-up 2026-10-05, finding 1).

Disabled couplings (estimated effects in the run manifest): Ga cell dynamics and the shutter flux
transient; collisional change of the Ga crucible transmission with cell temperature; adlayer
transients (10-20 s, R20); droplet evaporation; growing-film optics in the pyrometer and the
heater (R16); film and wall feedback into the gas; plasma ignition and output dynamics; hot cells
and the plasma source as heat loads on the wafer; azimuthal dose structure (maps are rotation-
averaged; partial revolutions at shutter events are flagged, not resolved).
"""

import copy
import math
import time

import numpy as np

from . import recipe as recipe_mod
from . import sensors, surface, thermal_transient
from .control import ControllerModel
from .growth import load_parameters

DISABLED_COUPLINGS = [
    {"coupling": "Ga cell thermal dynamics and shutter flux transient",
     "effect": "Cell assumed to follow its setpoint; real cells show a flux transient of a few percent for minutes "
               "after the shutter opens (machine-specific, measured at commissioning). Changes the first nm of a layer."},
    {"coupling": "Collisional crucible transmission versus cell temperature",
     "effect": "Ga flux scales with p_vap/sqrt(T) from one DSMC record; DSMC held flux within 1.5 % over +11.5-13 K, "
               "so small within a few K of the reference."},
    {"coupling": "Ga adlayer transients", "effect": "10-20 s after each step (R20); flagged at each event."},
    {"coupling": "Droplet evaporation", "effect": "Area fraction unknown; droplets persist until consumed by N."},
    {"coupling": "Growing-film optics (pyrometer reading, wafer absorption)",
     "effect": "R16: reading moved by >100 K at fixed thermocouple in an extreme case; not modelled."},
    {"coupling": "Surface/wall re-emission into the gas", "effect": "Desorbing Ga and unused N not returned to transport."},
    {"coupling": "Plasma ignition and output dynamics", "effect": "Active-N output follows the feed through the MFC lag only."},
    {"coupling": "Hot cells and plasma source as wafer heat loads", "effect": "Not in the heater model (steady model neither)."},
    {"coupling": "Azimuthal dose structure", "effect": "Rotation-averaged maps; partial revolutions at shutter events flagged."},
]

TIMESERIES_KEYS = ("t_s", "step", "heater_setpoint_K", "pyrometer_K", "pyrometer_ok", "wafer_centre_K", "wafer_mean_K",
                   "wafer_range_K", "element_max_K", "power_W", "power_clamped", "ga_cell_K", "n2_sccm", "pressure_Pa",
                   "gauge_Pa", "shutter_ga", "shutter_n", "plasma", "ga_centre_nm_min", "n_centre_nm_min",
                   "thickness_centre_nm", "thickness_mean_nm", "thickness_edge_nm", "droplets_mean_nm",
                   "growth_rate_mean_nm_min", "regime_centre", "window_fraction", "feed_command_sccm",
                   "ga_target_nm_min", "rate_monitor_nm_min", "bfm_kappa")


def area_weights(rho):
    w = sensors.ring_weights(rho, rho[-1])
    return w / w.sum()


def pi_gains(chamber, target_k):
    """Internal-model PI gains (W/K, W/K/s) of the lumped first-order heater plant at target_k."""
    ff = chamber.feedforward_table()
    t, p = ff["spot_K"], ff["power_W"]
    i = int(np.clip(np.searchsorted(t, target_k), 1, len(t) - 1))
    gain = (t[i] - t[i - 1]) / (p[i] - p[i - 1])          # K/W
    tau = float(chamber.capacity.sum()) * gain              # s
    lam = 0.5 * tau
    kp = tau / (gain * lam)
    return kp, kp / tau, {"gain_K_per_W": gain, "tau_s": tau, "closed_loop_tau_s": lam}


def _ramped(start, target, rate_per_min, elapsed_s):
    if rate_per_min is None or start is None:
        return target
    step = rate_per_min / 60.0 * elapsed_s
    return min(target, start + step) if target >= start else max(target, start - step)


class Twin:
    """One recipe run on one chamber. `run` advances to the end or to a stop point; `checkpoint` / `restore`
    serialize the full state so a resumed run is identical to an uninterrupted one."""

    def __init__(self, chamber, recipe, *, dt_max=1.0, sample_s=10.0, seed=0, params=None):
        self.chamber = chamber
        self.initial, self.steps, self.recipe_raw = recipe_mod.load(recipe, chamber.operating_point)
        self.dt_max = float(dt_max)
        self.sample_s = float(sample_s)
        self.seed = int(seed)
        self.params = params or load_parameters()
        self.rng = np.random.default_rng(self.seed)
        self.weights = area_weights(chamber.rho)
        c = chamber
        self.cm = ControllerModel(c.definition, c, self.params) if "controller_model" in c.definition else None
        if self.cm is None and any(st.n2_sccm == "rate_monitor" or st.ga_cell["target_K"] == "steered" or st.bfm
                                   for st in self.steps):
            raise ValueError("recipe uses realizable controllers, but the chamber has no controller_model")
        n_nodes = c.heater.nh + c.heater.nw + c.heater.nl + c.heater.npl
        t0 = self.initial["wafer_K"]
        self.state = {
            "t": 0.0, "step": 0, "sub": 0, "heater_T": [t0] * n_nodes, "integral_W": 0.0,
            "heater_sp_K": None, "step_heater_sp0": None, "cell_K": self.initial["ga_cell_K"], "step_cell0": None,
            "flow": 0.0, "pressure": 0.0, "power_W": 0.0, "next_sample": 0.0,
            "energy": {"in_J": 0.0, "loss_J": 0.0}, "heater_T0": [t0] * n_nodes,
            "surface": surface.SurfaceState.bare(len(c.rho)).to_dict(),
            "exposure_s": {"ga": 0.0, "n": 0.0, "growth": 0.0},
            "feed_cmd": None, "kappa": 1.0, "rate_win": None, "rate_meas": None, "ga_target": None,
        }
        self.log = {k: [] for k in TIMESERIES_KEYS}
        self.events, self.warnings = [], []
        self._last = None
        self._gains = {}
        self.wall_s = 0.0

    # ---- serialization ---------------------------------------------------------------------------
    def checkpoint(self):
        s = dict(self.state)
        return {"state": _jsonable(s), "rng": self.rng.bit_generator.state, "log": _jsonable(self.log),
                "events": list(self.events), "warnings": list(self.warnings), "last": _jsonable(self._last)}

    def restore(self, ckpt):
        self.state = copy.deepcopy(ckpt["state"])
        self.rng.bit_generator.state = ckpt["rng"]
        self.log = {k: list(v) for k, v in ckpt["log"].items()}
        self.events, self.warnings = list(ckpt["events"]), list(ckpt["warnings"])
        self._last = copy.deepcopy(ckpt["last"])

    # ---- stepping ----------------------------------------------------------------------------------
    def n_sub(self, step):
        return max(1, math.ceil(step.duration_s / self.dt_max - 1e-9))

    def run(self, stop_at=None):
        """Advance to the end of the recipe, or until (step index, sub-step index) == stop_at."""
        t_wall = time.perf_counter()
        while self.state["step"] < len(self.steps):
            if stop_at is not None and (self.state["step"], self.state["sub"]) == tuple(stop_at):
                break
            step = self.steps[self.state["step"]]
            if self.state["sub"] == 0:
                self._enter(step)
            self._advance(step)
            self.state["sub"] += 1
            if self.state["sub"] == self.n_sub(step):
                self.state["step"] += 1
                self.state["sub"] = 0
        self.wall_s += time.perf_counter() - t_wall
        return self

    def _enter(self, step):
        """Step boundary: record the event and its flags; fix the ramp start points."""
        s = self.state
        prev = self.steps[step.index - 1] if step.index > 0 else None
        s["step_heater_sp0"] = s["heater_sp_K"]
        s["step_cell0"] = s["cell_K"]
        changes = []
        if prev is None or prev.shutters != step.shutters:
            changes.append(f"shutters {step.shutters}")
        if prev is None or prev.plasma != step.plasma:
            changes.append(f"plasma {'on' if step.plasma else 'off'}")
        self.events.append({"t_s": s["t"], "step": step.index, "name": step.name, "changes": changes})
        growing = step.shutters["ga"] or (step.shutters["n"] and step.plasma)
        was = prev is not None and (prev.shutters["ga"] or (prev.shutters["n"] and prev.plasma))
        if growing != was or (growing and prev is not None and prev.shutters != step.shutters):
            self.warnings.append(f"t = {s['t']:.0f} s ({step.name}): surface step change; the 10-20 s adlayer "
                                 "transient (R20) is not resolved")
        if growing and step.duration_s < 60.0:
            self.warnings.append(f"{step.name}: {step.duration_s:g} s exposure < 60 s; transients matter")
        if step.shutters["ga"] or step.shutters["n"]:
            if step.rotation_rpm <= 0.0:
                self.warnings.append(f"{step.name}: shutter open without rotation; the rotation-averaged maps do not apply")
            else:
                revs = step.duration_s * step.rotation_rpm / 60.0
                if revs < 100.0:
                    self.warnings.append(f"{step.name}: {revs:.1f} revolutions with a shutter open; a partial revolution "
                                         "leaves azimuthal dose structure up to 1/revs of the layer, not resolved")
        c = self.chamber
        if step.bfm and not step.shutters["ga"]:
            raise ValueError(f"{step.name}: a BFM step needs the Ga shutter open")
        if step.plasma and isinstance(step.n2_sccm, float) and step.n2_sccm > 0 and c.kn_per_sccm is not None and c.kn_per_sccm / step.n2_sccm < c.kn_valid:
            self.warnings.append(f"{step.name}: plate hole Kn {c.kn_per_sccm / step.n2_sccm:.1f} < {c.kn_valid:g}; the "
                                 "free-molecular N map is outside its validity")

    def gains(self, target_k):
        if target_k not in self._gains:
            self._gains[target_k] = pi_gains(self.chamber, target_k)
        return self._gains[target_k]

    def _setpoints(self, step, elapsed):
        s = self.state
        h = step.heater
        sp = None
        if h["mode"] in ("feedforward", "pyrometer"):
            target = h["target_C"] + 273.15
            start = s["step_heater_sp0"]
            if start is None:   # first closed-loop step: ramp from the current spot temperature
                start = self.chamber.spot_mean(self.chamber.wafer_on_grid(np.asarray(s["heater_T"])),
                                               self.chamber.sensors["pyrometer"]["spot_radius_m"])
                s["step_heater_sp0"] = start
            sp = _ramped(start, target, h.get("ramp_K_per_min"), elapsed)
        g = step.ga_cell
        if g["target_K"] == "steered":
            return sp, s["cell_K"]
        cell = _ramped(s["step_cell0"], g["target_K"], g.get("ramp_K_per_min"), elapsed)
        return sp, cell

    def _advance(self, step):
        c, s = self.chamber, self.state
        n = self.n_sub(step)
        dt = step.duration_s / n
        t0_in = s["sub"] * dt
        sp_end, cell_end = self._setpoints(step, t0_in + dt)
        _, cell_mid = self._setpoints(step, t0_in + 0.5 * dt)
        t_nodes = np.asarray(s["heater_T"], float)
        py = c.sensors["pyrometer"]
        # ---- controller on the reading at the start of the sub-step ----
        reading, flag = sensors.pyrometer(c.rho, c.wafer_on_grid(t_nodes), self.rng, spot_radius=py["spot_radius_m"],
                                          bias_k=py.get("bias_K", 0.0), noise_k=py.get("noise_K", 0.0),
                                          valid_min_k=py.get("valid_min_K", 873.0))
        gauge = c.sensors.get("ion_gauge", {})
        g_read, g_flag = sensors.ion_gauge(s["pressure"], self.rng, sensitivity=gauge.get("sensitivity", 1.0),
                                           noise_rel=gauge.get("noise_rel", 0.0))
        h = step.heater
        if h["mode"] == "power":
            demand = h["power_W"]
            s["integral_W"] = 0.0
        else:
            demand = c.feedforward_power(sp_end)
            if h["mode"] == "pyrometer":
                if flag != "ok":
                    raise RuntimeError(f"{step.name}: pyrometer control with the reading {flag} at t = {s['t']:.0f} s")
                kp, ki, _ = self.gains(h["target_C"] + 273.15)
                err = sp_end - reading
                trial = demand + kp * err + s["integral_W"] + ki * err * dt
                p_lim = c.feedforward_table()["p_limit_W"]
                if 0.0 <= trial <= p_lim or (trial > p_lim and err < 0) or (trial < 0 and err > 0):
                    s["integral_W"] += ki * err * dt       # no windup while saturated in the error's direction
                demand = demand + kp * err + s["integral_W"]
            else:
                s["integral_W"] = 0.0
        p_lim = c.feedforward_table()["p_limit_W"]
        power = float(np.clip(demand, 0.0, p_lim))
        clamped = demand > p_lim
        zp = c.zone_power(power)
        t_new = thermal_transient.step(c.heater, t_nodes, dt, c.capacity, zp)
        fr = thermal_transient.fields(c.heater, t_new, zp)
        s["energy"]["in_J"] += power * dt
        s["energy"]["loss_J"] += dt * (fr["front_loss"] + fr["rim_loss"])
        # ---- realizable Ga steering on the readings at the start of the sub-step ----
        if step.ga_cell["target_K"] == "steered" and flag == "ok":
            s["ga_target"] = self.cm.ga_target(reading, g_read)
            cell_mid = cell_end = self.cm.cell_for(s["ga_target"], g_read, s["kappa"])
        # ---- feed and pressure (exact first-order over the sub-step) ----
        if step.n2_sccm == "rate_monitor":
            if s["feed_cmd"] is None:
                s["feed_cmd"] = float(c.operating_point["n2_sccm"])
            target_flow = s["feed_cmd"]
        else:
            target_flow = step.n2_sccm
        a = math.exp(-dt / c.mfc_tau) if c.mfc_tau > 0 else 0.0
        flow_mean = target_flow + (s["flow"] - target_flow) * (c.mfc_tau / dt * (1.0 - a) if c.mfc_tau > 0 else 0.0)
        flow_end = target_flow + (s["flow"] - target_flow) * a
        p_eq = c.pressure_eq(flow_mean)
        tau_p = c.volume / c.speed
        b = math.exp(-dt / tau_p)
        p_mean = p_eq + (s["pressure"] - p_eq) * tau_p / dt * (1.0 - b)
        p_end = p_eq + (s["pressure"] - p_eq) * b
        # ---- arrival and surface ----
        j_ga = (c.ga_flux(cell_mid, p_mean) / c.k_atoms if step.shutters["ga"] and not step.bfm
                else np.zeros_like(c.rho))
        if step.bfm:   # the monitor at the wafer position reads the centre arrival; the wafer is out of the beam
            bf = c.sensors.get("bfm", {})
            true_arr = float(c.ga_flux(cell_mid, p_mean)[0]) / c.k_atoms
            noise = float(self.rng.normal(0.0, bf["noise_rel"])) if bf.get("noise_rel", 0.0) > 0 else 0.0
            measured = true_arr * (1.0 + bf.get("error_rel", 0.0)) * (1.0 + noise)
            s["kappa"] = self.cm.model_arrival(cell_mid, g_read) / measured
        j_n = (c.n_flux(flow_mean, p_mean) / c.k_atoms if (step.shutters["n"] and step.plasma)
               else np.zeros_like(c.rho))
        t_wafer = c.wafer_on_grid(t_new)
        surf = surface.SurfaceState.from_dict(s["surface"])
        surf_new, info = surface.advance(surf, j_ga, j_n, t_wafer, dt, self.params, c.droplet_law,
                                         c.n_rich_decomposition)
        growing = step.shutters["ga"] and not step.bfm and step.shutters["n"] and step.plasma
        if step.n2_sccm == "rate_monitor" and growing:
            rm = c.sensors.get("rate_monitor", {})
            if s["rate_win"] is None:
                s["rate_win"] = {"t0": s["t"], "h0": float(surf.thickness[0])}
            elapsed = s["t"] + dt - s["rate_win"]["t0"]
            if elapsed >= rm.get("window_s", 600.0) - 1e-9:
                noise = float(self.rng.normal(0.0, rm["noise_rel"])) if rm.get("noise_rel", 0.0) > 0 else 0.0
                meas = ((float(surf_new.thickness[0]) - s["rate_win"]["h0"]) / (elapsed / 60.0)
                        * (1.0 + rm.get("error_rel", 0.0)) * (1.0 + noise))
                dec = float(self.params.decomposition(reading)) if flag == "ok" else 0.0
                r_star = self.cm.centre_rate_target()
                cap = float(c.definition["vacuum"].get("feed_limit_sccm", np.inf))
                s["feed_cmd"] = float(np.clip(s["feed_cmd"] * (r_star + dec) / max(meas + dec, 1e-9), 0.0, cap))
                s["rate_meas"] = meas
                s["rate_win"] = {"t0": s["t"] + dt, "h0": float(surf_new.thickness[0])}
        elif not growing:
            s["rate_win"] = None
        # ---- commit ----
        s.update({"t": s["t"] + dt, "heater_T": t_new.tolist(), "heater_sp_K": sp_end, "cell_K": cell_end,
                  "flow": flow_end, "pressure": p_end, "power_W": power, "surface": surf_new.to_dict()})
        if step.shutters["ga"]:
            s["exposure_s"]["ga"] += dt
        if step.shutters["n"] and step.plasma:
            s["exposure_s"]["n"] += dt
        last_of_step = s["sub"] == n - 1
        if s["t"] >= s["next_sample"] - 1e-9 or last_of_step:
            if s["t"] >= s["next_sample"] - 1e-9:
                s["next_sample"] += self.sample_s * max(1, math.floor((s["t"] - s["next_sample"]) / self.sample_s) + 1)
            regime, _ = sensors.regime_indicator(c.rho, info["regime"], c.sensors.get("regime_spot_radius_m", 0.01))
            w = self.weights
            in_window = (info["regime"] == "Ga-adlayer")
            row = {"t_s": s["t"], "step": step.index, "heater_setpoint_K": np.nan if sp_end is None else sp_end,
                   "pyrometer_K": reading, "pyrometer_ok": flag == "ok", "wafer_centre_K": float(t_wafer[0]),
                   "wafer_mean_K": float(np.sum(w * t_wafer)), "wafer_range_K": float(t_wafer.max() - t_wafer.min()),
                   "element_max_K": float(fr["t_heater"].max()), "power_W": power, "power_clamped": bool(clamped),
                   "ga_cell_K": cell_end, "n2_sccm": flow_end, "pressure_Pa": p_end, "gauge_Pa": g_read,
                   "shutter_ga": step.shutters["ga"], "shutter_n": step.shutters["n"], "plasma": step.plasma,
                   "ga_centre_nm_min": float(j_ga[0]), "n_centre_nm_min": float(j_n[0]),
                   "thickness_centre_nm": float(surf_new.thickness[0]),
                   "thickness_mean_nm": float(np.sum(w * surf_new.thickness)),
                   "thickness_edge_nm": float(surf_new.thickness[-1]),
                   "droplets_mean_nm": float(np.sum(w * surf_new.droplets)),
                   "growth_rate_mean_nm_min": float(np.sum(w * info["net_growth"])), "regime_centre": regime,
                   "window_fraction": float(np.sum(w * in_window)),
                   "feed_command_sccm": np.nan if s["feed_cmd"] is None else s["feed_cmd"],
                   "ga_target_nm_min": np.nan if s["ga_target"] is None else s["ga_target"],
                   "rate_monitor_nm_min": np.nan if s["rate_meas"] is None else s["rate_meas"],
                   "bfm_kappa": s["kappa"]}
            for k in TIMESERIES_KEYS:
                self.log[k].append(row[k])
        self._last = {"t_wafer": t_wafer.tolist(), "regime": info["regime"].tolist(),
                      "net_growth": info["net_growth"].tolist()}

    # ---- results ----------------------------------------------------------------------------------
    def results(self):
        c, s = self.chamber, self.state
        surf = surface.SurfaceState.from_dict(s["surface"])
        w = self.weights
        h = surf.thickness
        mean_h = float(np.sum(w * h))
        res = surface.ledger_residuals(surf)
        led = surf.ledger
        scale = max(float(np.max(led["ga_in"] + led["ga_released"])), 1e-30)
        t_nodes = np.asarray(s["heater_T"])
        stored = float(np.sum(c.capacity * (t_nodes - np.asarray(s["heater_T0"]))))
        e_res = s["energy"]["in_J"] - s["energy"]["loss_J"] - stored
        mp = c.sensors.get("thickness_map_radii_m")
        measured = sensors.thickness_map(c.rho, h, mp)[0].tolist() if mp else None
        out = {
            "t_end_s": s["t"], "complete": s["step"] >= len(self.steps),
            "thickness_mean_nm": mean_h,
            "thickness_half_range_pct": 100.0 * (h.max() - h.min()) / (2.0 * mean_h) if mean_h > 0 else None,
            "thickness_std_pct": 100.0 * float(np.sqrt(np.sum(w * (h - mean_h) ** 2))) / mean_h if mean_h > 0 else None,
            "droplets_max_nm": float(surf.droplets.max()), "droplets_mean_nm": float(np.sum(w * surf.droplets)),
            "exposure_s": dict(s["exposure_s"]),
            "conservation": {
                "ga_max_abs_rel": float(np.max(np.abs(res["ga"]))) / scale,
                "droplets_max_abs_rel": float(np.max(np.abs(res["droplets"]))) / scale,
                "n_max_abs_rel": float(np.max(np.abs(res["n"]))) / max(float(np.max(led["n_in"])), 1e-30),
                "solid_max_abs_rel": float(np.max(np.abs(res["solid"]))) / max(float(np.max(h)), 1e-30),
                "heater_energy_rel": e_res / max(s["energy"]["in_J"], 1e-30),
                "etch_limited_max_nm": float(led["etch_limited"].max()),
            },
            "ledger_area_mean_nm": {k: float(np.sum(w * v)) for k, v in led.items()},
            "wall_s": self.wall_s,
        }
        maps = {"rho_m": c.rho.tolist(), "thickness_nm": h.tolist(), "droplets_nm": surf.droplets.tolist(),
                "t_wafer_K": self._last["t_wafer"] if self._last else None, "thickness_map_measured_nm": measured,
                "thickness_map_radii_m": mp}
        return out, maps

    def timeseries(self):
        return {k: np.asarray(v) for k, v in self.log.items()}


def _jsonable(x):
    if isinstance(x, dict):
        return {k: _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, np.generic):
        return x.item()
    return x
