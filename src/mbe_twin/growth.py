"""Local GaN growth regime and net growth rate (Ga-polar (0001) GaN, plasma-assisted MBE).

First growth model (review 3, item 4). Steady state per wafer point from the delivered Ga
flux, the delivered active-N flux and the wafer temperature, with parameters and their
sources in data/parameters/gan_growth.json (no constant is fitted to this machine):

- Incorporation: min(Ga, N). Ga-rich growth is N-limited, N-rich growth is Ga-limited.
- Decomposition (G02): vacuum rate A exp(-E/kT). Under Ga-rich growth the effective loss
  equals the vacuum rate (G02); under N-rich growth it is reduced by an unquantified amount,
  so it is bracketed by `n_rich_decomposition` ("vacuum" or "none").
- Excess Ga desorbs (R20: desorbing Ga equals the excess below the droplet onset) together
  with the Ga released by decomposition (G02). Above the critical excess F_crit(T) (G01
  Table I; three disagreeing sources kept as scenarios) the surplus accumulates as droplets.
- Regimes: "N-rich" (excess < 0; rough 3D growth in R20), "Ga-adlayer" (0 <= excess <=
  F_crit) and "droplets" (excess > F_crit).

Atom balances close exactly: Ga in + Ga released by decomposition = Ga incorporated + Ga
desorbed + Ga into droplets; net solid = incorporated - decomposed.

Not modelled: transients (R20: steady state within 10-20 s of a pulse; segments shorter than
60 s are flagged), droplet consumption by later N-rich growth, adlayer coverage kinetics
(G01's isotherm), polarity, AlN (needs its own model, GROWTH_EVIDENCE correction 1),
morphology. Fluxes are in nm/min of GaN (1 nm/min = 0.064 ML/s); temperatures in K and in
the source labs' substrate-temperature scales, not a calibrated wafer temperature.

Operational active N: a flux calibrated from a Ga-rich growth rate at temperature T_cal is
net of decomposition at T_cal; `active_n_from_ga_rich_rate` adds it back.
"""

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np

K_B_EV = 8.617333262e-5
PARAMETERS = Path(__file__).resolve().parents[2] / "data/parameters/gan_growth.json"


@dataclass(frozen=True)
class Arrhenius:
    prefactor: float
    energy_ev: float
    unit: str
    source: str

    def __call__(self, t_k):
        return self.prefactor * np.exp(-self.energy_ev / (K_B_EV * np.asarray(t_k, float)))


@dataclass(frozen=True)
class GrowthParameters:
    decomposition: Arrhenius          # nm/min
    droplet_onset: dict               # scenario name -> Arrhenius in ML/s
    ml_per_s_per_nm_per_min: float

    def critical_excess(self, scenario, t_k):
        """Critical excess Ga flux (nm/min) at the droplet onset for one scenario."""
        return self.droplet_onset[scenario](t_k) / self.ml_per_s_per_nm_per_min


def load_parameters(path=PARAMETERS):
    p = json.loads(Path(path).read_text(encoding="utf-8"))
    d = p["decomposition"]
    return GrowthParameters(
        decomposition=Arrhenius(d["prefactor"], d["energy_ev"], d["unit"], d["source"]),
        droplet_onset={k: Arrhenius(v["prefactor"], v["energy_ev"], v["unit"], v["source"])
                       for k, v in p["droplet_onset"]["scenarios"].items()},
        ml_per_s_per_nm_per_min=p["units"]["ml_per_s_per_nm_per_min"])


def active_n_from_ga_rich_rate(rate_nm_min, t_cal_k, params):
    """Active-N flux from a Ga-rich (N-limited) growth-rate calibration at t_cal_k."""
    return np.asarray(rate_nm_min, float) + params.decomposition(t_cal_k)


def steady_state(j_ga, j_n, t_k, params, droplet_scenario, n_rich_decomposition="vacuum"):
    """Steady-state regime and rates (nm/min) at each point; inputs broadcast together."""
    if n_rich_decomposition not in ("vacuum", "none"):
        raise ValueError("n_rich_decomposition must be 'vacuum' or 'none'")
    j_ga, j_n, t_k = np.broadcast_arrays(np.asarray(j_ga, float), np.asarray(j_n, float), np.asarray(t_k, float))
    if np.any(j_ga < 0) or np.any(j_n < 0):
        raise ValueError("fluxes must be non-negative")
    dec = params.decomposition(t_k)
    f_crit = params.critical_excess(droplet_scenario, t_k)
    excess = j_ga - j_n
    n_rich = excess < 0
    droplets = excess > f_crit
    d_eff = np.where(n_rich, dec if n_rich_decomposition == "vacuum" else 0.0, dec)
    incorporated = np.minimum(j_ga, j_n)
    into_droplets = np.where(droplets, excess - f_crit, 0.0)
    desorbed_ga = np.where(n_rich, 0.0, np.minimum(excess, f_crit)) + d_eff
    regime = np.where(n_rich, "N-rich", np.where(droplets, "droplets", "Ga-adlayer"))
    return {
        "regime": regime, "net_growth": incorporated - d_eff, "incorporated": incorporated,
        "decomposition": d_eff, "desorbed_ga": desorbed_ga, "into_droplets": into_droplets,
        "unused_n": np.maximum(j_n - j_ga, 0.0), "excess_ga": excess, "critical_excess": f_crit,
        # fractional distance to each regime boundary, in units of the local N flux
        "margin_to_n_rich": excess / j_n, "margin_to_droplets": (f_crit - excess) / j_n,
    }


def ga_balance_residual(state, j_ga):
    """Ga in + released - (incorporated + desorbed + droplets); zero to rounding."""
    return (np.asarray(j_ga, float) + state["decomposition"]
            - state["incorporated"] - state["desorbed_ga"] - state["into_droplets"])


def grow(segments, params, droplet_scenario, n_rich_decomposition="vacuum"):
    """Accumulate a recipe of steady segments at one or more points.

    segments: iterable of dicts with duration_s, j_ga, j_n (nm/min; 0 for a closed shutter) and
    t_k. Returns the net thickness (nm), Ga into droplets (nm GaN-equivalent), the Ga balance
    over the recipe and warnings (segments shorter than 60 s, where transients matter).
    """
    thickness = droplets = ga_in = ga_out = 0.0
    warnings = []
    for i, s in enumerate(segments):
        minutes = s["duration_s"] / 60.0
        st = steady_state(s["j_ga"], s["j_n"], s["t_k"], params, droplet_scenario, n_rich_decomposition)
        if s["duration_s"] < 60.0:
            warnings.append(f"segment {i}: {s['duration_s']:g} s < 60 s; transients (10-20 s, R20) not modelled")
        thickness = thickness + st["net_growth"] * minutes
        droplets = droplets + st["into_droplets"] * minutes
        ga_in = ga_in + (np.asarray(s["j_ga"], float) + st["decomposition"]) * minutes
        ga_out = ga_out + (st["incorporated"] + st["desorbed_ga"] + st["into_droplets"]) * minutes
    return {"thickness_nm": thickness, "droplet_ga_nm": droplets, "ga_balance_residual": ga_in - ga_out,
            "warnings": warnings}
