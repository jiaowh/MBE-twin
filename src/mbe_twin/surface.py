"""Surface state of the growing wafer through a recipe: film thickness, droplet inventory and atom ledgers.

Wraps the steady-state regime model (mbe_twin.growth.steady_state) in a time-stepped state that
persists across shutter events, as the integrated twin needs (mbe_twin.md section 10.1). Per wafer
point, in nm of GaN (Ga inventory as nm of GaN-equivalent):

- thickness: net solid GaN. Decomposition may etch it (signed growth), down to zero; below zero the
  substrate (Si, with its nucleation layer) is exposed and does not decompose. The decomposition
  the film could not supply is recorded (`etch_limited`), so the ledgers stay exact.
- droplets: Ga accumulated above the droplet onset. It persists when the shutters close. Under
  N-rich conditions it is consumed into GaN at the rate the unused active N allows (min of the
  inventory over the step and the unused N flux): a prior, chosen because droplet consumption by an
  N flux is the standard recovery step; its kinetics are not sourced here. Droplet evaporation at
  the wafer temperature is not included (its area fraction is unknown); recorded as a disabled
  coupling by the twin.
- Ga adlayer: steady (no inventory). R20 reports steady state within 10-20 s of a step, so every
  shutter or flux step carries an unresolved 10-20 s transient, which the twin flags.

Ga ledger per point and in total: Ga arriving + Ga from droplets + Ga released by decomposition =
Ga incorporated + Ga desorbed + Ga into droplets. N ledger: active N arriving = N incorporated +
N unused (returns to the gas, as N2 or atoms). Both close to rounding; `ledger_residuals` returns
them.
"""

from dataclasses import dataclass, field

import numpy as np

from .growth import steady_state

LEDGER_KEYS = ("ga_in", "ga_from_droplets", "ga_released", "ga_incorporated", "ga_desorbed", "ga_into_droplets",
               "n_in", "n_incorporated", "n_unused", "decomposed", "etch_limited")


@dataclass
class SurfaceState:
    thickness: np.ndarray                       # nm GaN
    droplets: np.ndarray                        # nm GaN-equivalent Ga
    ledger: dict = field(default_factory=dict)  # nm (GaN-equivalent) per point, integrated over time

    @classmethod
    def bare(cls, n_points):
        z = np.zeros(n_points)
        return cls(z.copy(), z.copy(), {k: z.copy() for k in LEDGER_KEYS})

    def to_dict(self):
        return {"thickness": self.thickness.tolist(), "droplets": self.droplets.tolist(),
                "ledger": {k: v.tolist() for k, v in self.ledger.items()}}

    @classmethod
    def from_dict(cls, d):
        return cls(np.asarray(d["thickness"], float), np.asarray(d["droplets"], float),
                   {k: np.asarray(d["ledger"][k], float) for k in LEDGER_KEYS})


def advance(state, j_ga, j_n, t_k, dt_s, params, droplet_law, n_rich_decomposition="vacuum"):
    """Advance the surface over dt_s with fluxes (nm/min GaN-equivalent) and temperatures held over the step.

    Returns (new state, step dict with the regime and rates at each point)."""
    if dt_s <= 0.0:
        raise ValueError("dt must be positive")
    minutes = dt_s / 60.0
    j_ga, j_n, t_k = np.broadcast_arrays(np.asarray(j_ga, float), np.asarray(j_n, float), np.asarray(t_k, float))
    # droplet Ga consumed by the active N that the arriving Ga leaves unused
    spare_n = np.maximum(j_n - j_ga, 0.0)
    from_drops = np.minimum(state.droplets / minutes, spare_n)
    supply = j_ga + from_drops
    with np.errstate(divide="ignore", invalid="ignore"):   # margins are undefined where no N arrives
        st = steady_state(supply, j_n, t_k, params, droplet_law, n_rich_decomposition)
    dec = st["decomposition"]
    growth = (st["incorporated"] - dec) * minutes
    new_h = state.thickness + growth
    # the film cannot decompose below zero: the missing decomposition did not happen
    short = np.where(new_h < 0.0, -new_h, 0.0)
    new_h = np.maximum(new_h, 0.0)
    dec_done = dec * minutes - short
    new_d = state.droplets - from_drops * minutes + st["into_droplets"] * minutes
    # decomposition releases Ga that desorbs (G02); where it was cut short, less Ga desorbed
    desorbed = st["desorbed_ga"] * minutes - short
    led = dict(state.ledger)
    add = {"ga_in": j_ga * minutes, "ga_from_droplets": from_drops * minutes, "ga_released": dec_done,
           "ga_incorporated": st["incorporated"] * minutes, "ga_desorbed": desorbed,
           "ga_into_droplets": st["into_droplets"] * minutes, "n_in": j_n * minutes,
           "n_incorporated": st["incorporated"] * minutes, "n_unused": st["unused_n"] * minutes,
           "decomposed": dec_done, "etch_limited": short}
    for k, v in add.items():
        led[k] = led[k] + v
    regime = np.where(from_drops > 0.0, "droplet-consumption", st["regime"])
    return SurfaceState(new_h, np.maximum(new_d, 0.0), led), {
        "regime": regime, "net_growth": (new_h - state.thickness) / minutes, "from_droplets": from_drops,
        "margin_to_n_rich": st["margin_to_n_rich"], "margin_to_droplets": st["margin_to_droplets"]}


def ledger_residuals(state, initial=None):
    """Ga, N and solid balances (nm per point) relative to `initial` (bare wafer if None); zero to rounding."""
    l = state.ledger
    d0 = 0.0 if initial is None else initial.droplets
    h0 = 0.0 if initial is None else initial.thickness
    ga = (l["ga_in"] + l["ga_from_droplets"] + l["ga_released"]
          - l["ga_incorporated"] - l["ga_desorbed"] - l["ga_into_droplets"])
    drops = (state.droplets - d0) - (l["ga_into_droplets"] - l["ga_from_droplets"])
    n = l["n_in"] - l["n_incorporated"] - l["n_unused"]
    solid = (state.thickness - h0) - (l["n_incorporated"] - l["decomposed"])
    return {"ga": ga, "droplets": drops, "n": n, "solid": solid}
