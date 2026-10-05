"""Growth recipes for the integrated twin: validated, resolved steps with explicit units.

A recipe is JSON: {"schema_version": "0.1", "name", "initial": {...}, "steps": [...]}. Each step
has a name and duration_s; every other field is optional and inherits the previous step's value,
so a step lists only what it changes:

- heater: {"mode": "power", "power_W": P} (total power, zone ratios fixed by the chamber),
  {"mode": "feedforward", "target_C": T} (the steady power that puts the pyrometer reading at T,
  open loop, as a heater-thermocouple controller would be used before the pyrometer reads), or
  {"mode": "pyrometer", "target_C": T} (closed loop on the pyrometer reading). "ramp_K_per_min"
  ramps the setpoint linearly from the previous one.
- ga_cell: {"target_K": T, "ramp_K_per_min": r}; the cell follows its setpoint ramp exactly (cell
  dynamics are not modelled; see the twin's disabled couplings).
- n2_sccm: N2 feed through the plasma source; plasma: true / false (active N leaves the plate only
  with the plasma on); shutters: {"ga": bool, "n": bool}; rotation_rpm.

"operating_point" in place of a number takes the chamber definition's value (wafer_C, ga_cell_K
or n2_sccm). Initial state: {"wafer_C", "ga_cell_K"} (the wafer and holder start isothermal at
wafer_C). Units are in the key names; anything else is rejected.
"""

import copy
import json
from dataclasses import dataclass
from pathlib import Path

STEP_KEYS = {"name", "duration_s", "heater", "ga_cell", "n2_sccm", "plasma", "shutters", "rotation_rpm", "note"}
HEATER_MODES = {"power": {"power_W"}, "feedforward": {"target_C"}, "pyrometer": {"target_C"}}
DEFAULTS = {"heater": {"mode": "power", "power_W": 0.0}, "ga_cell": {"target_K": None, "ramp_K_per_min": None},
            "n2_sccm": 0.0, "plasma": False, "shutters": {"ga": False, "n": False}, "rotation_rpm": 0.0}


@dataclass(frozen=True)
class Step:
    index: int
    name: str
    duration_s: float
    heater: dict
    ga_cell: dict
    n2_sccm: float
    plasma: bool
    shutters: dict
    rotation_rpm: float


def _op(value, key, op):
    if value == "operating_point":
        if op is None or key not in op:
            raise ValueError(f"recipe: 'operating_point' for {key}, but the chamber gives no {key}")
        return float(op[key])
    return value


def _number(x, what, minimum=None):
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise ValueError(f"recipe: {what} must be a number, got {x!r}")
    if minimum is not None and x < minimum:
        raise ValueError(f"recipe: {what} must be >= {minimum}, got {x}")
    return float(x)


def load(recipe, operating_point=None):
    """Validate and resolve a recipe (path or dict). Returns (initial dict in K, list of Step, raw recipe)."""
    if isinstance(recipe, (str, Path)):
        raw = json.loads(Path(recipe).read_text(encoding="utf-8"))
    else:
        raw = copy.deepcopy(recipe)
    if raw.get("schema_version") != "0.1":
        raise ValueError("recipe: schema_version must be '0.1'")
    unknown = set(raw) - {"schema_version", "name", "description", "initial", "steps"}
    if unknown:
        raise ValueError(f"recipe: unknown top-level keys {sorted(unknown)}")
    ini = raw.get("initial", {})
    if set(ini) - {"wafer_C", "ga_cell_K"}:
        raise ValueError(f"recipe: unknown initial keys {sorted(set(ini) - {'wafer_C', 'ga_cell_K'})}")
    initial = {"wafer_K": _number(ini.get("wafer_C", 25.0), "initial wafer_C", -273.15) + 273.15,
               "ga_cell_K": _number(_op(ini.get("ga_cell_K", 300.0), "ga_cell_K", operating_point), "initial ga_cell_K", 0.0)}
    if not raw.get("steps"):
        raise ValueError("recipe: no steps")
    cur = copy.deepcopy(DEFAULTS)
    cur["ga_cell"]["target_K"] = initial["ga_cell_K"]
    steps = []
    for i, s in enumerate(raw["steps"]):
        bad = set(s) - STEP_KEYS
        if bad:
            raise ValueError(f"recipe step {i}: unknown keys {sorted(bad)}")
        name = s.get("name", f"step {i}")
        dur = _number(s.get("duration_s"), f"step {i} duration_s")
        if dur <= 0.0:
            raise ValueError(f"recipe step {i}: duration_s must be positive")
        if "heater" in s:
            h = dict(s["heater"])
            mode = h.get("mode")
            if mode not in HEATER_MODES:
                raise ValueError(f"recipe step {i}: heater mode must be one of {sorted(HEATER_MODES)}")
            allowed = HEATER_MODES[mode] | {"mode", "ramp_K_per_min"}
            if set(h) - allowed or not HEATER_MODES[mode] <= set(h):
                raise ValueError(f"recipe step {i}: heater mode {mode} takes {sorted(allowed)}")
            if "target_C" in h:
                h["target_C"] = _number(_op(h["target_C"], "wafer_C", operating_point), f"step {i} target_C")
            if "power_W" in h:
                h["power_W"] = _number(h["power_W"], f"step {i} power_W", 0.0)
            if "ramp_K_per_min" in h:
                h["ramp_K_per_min"] = _number(h["ramp_K_per_min"], f"step {i} heater ramp", 0.0)
                if h["ramp_K_per_min"] == 0.0:
                    raise ValueError(f"recipe step {i}: a ramp rate must be positive (omit it for a step change)")
            cur["heater"] = h
        if "ga_cell" in s:
            g = dict(s["ga_cell"])
            if set(g) - {"target_K", "ramp_K_per_min"} or "target_K" not in g:
                raise ValueError(f"recipe step {i}: ga_cell takes target_K and optional ramp_K_per_min")
            g["target_K"] = _number(_op(g["target_K"], "ga_cell_K", operating_point), f"step {i} ga_cell target_K", 0.0)
            g["ramp_K_per_min"] = (_number(g["ramp_K_per_min"], f"step {i} ga_cell ramp", 0.0)
                                   if g.get("ramp_K_per_min") is not None else None)
            if g["ramp_K_per_min"] == 0.0:
                raise ValueError(f"recipe step {i}: a ramp rate must be positive (omit it for a step change)")
            cur["ga_cell"] = g
        if "n2_sccm" in s:
            cur["n2_sccm"] = _number(_op(s["n2_sccm"], "n2_sccm", operating_point), f"step {i} n2_sccm", 0.0)
        if "plasma" in s:
            if not isinstance(s["plasma"], bool):
                raise ValueError(f"recipe step {i}: plasma must be true or false")
            cur["plasma"] = s["plasma"]
        if "shutters" in s:
            sh = s["shutters"]
            if set(sh) - {"ga", "n"} or not all(isinstance(v, bool) for v in sh.values()):
                raise ValueError(f"recipe step {i}: shutters takes ga / n booleans")
            cur["shutters"] = {**cur["shutters"], **sh}
        if "rotation_rpm" in s:
            cur["rotation_rpm"] = _number(s["rotation_rpm"], f"step {i} rotation_rpm", 0.0)
        steps.append(Step(i, name, dur, copy.deepcopy(cur["heater"]), copy.deepcopy(cur["ga_cell"]), cur["n2_sccm"],
                          cur["plasma"], dict(cur["shutters"]), cur["rotation_rpm"]))
    return initial, steps, raw
