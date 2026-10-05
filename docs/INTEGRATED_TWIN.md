# Integrated twin, first slice (2026-10-05; realizable controllers and heater margin added the same day)

The integrated twin runs a growth recipe through the Stage A subsystem models, coupled in time on one radial wafer grid. It covers heater and wafer temperature, the Ga cell, the N2 feed and plasma source, chamber pressure, beam arrival, the growing surface and the instruments. It delivers the PHASE1 item "integrated thickness and conserved inventories through a shutter event", a sensor-space log and a run bundle. It is a `representative_chamber` result: these are not predictions for the proposed machine, and nothing here is validated against machine data.

Modules: [twin.py](../src/mbe_twin/twin.py), [chamber.py](../src/mbe_twin/chamber.py), [control.py](../src/mbe_twin/control.py), [recipe.py](../src/mbe_twin/recipe.py), [surface.py](../src/mbe_twin/surface.py), [sensors.py](../src/mbe_twin/sensors.py), [thermal_transient.py](../src/mbe_twin/thermal_transient.py). Scripts: [twin_chamber.py](../scripts/twin_chamber.py) builds a chamber definition, and [twin_run.py](../scripts/twin_run.py) runs a recipe. Tests: [test_twin.py](../tests/test_twin.py).

## 1. What is coupled

```text
recipe -> setpoints -> controllers (see readings only) -> heater power, Ga cell temperature, N2 feed
heater power -> transient heater/holder/wafer model -> wafer temperature map
N2 feed -> MFC lag -> well-mixed chamber pressure (V/S) -> attenuation and scattered-arrival tables
cell temperature, pressure, shutters, plasma -> Ga and active-N arrival maps
arrival + wafer temperature -> surface state (thickness, droplets, atom ledgers)
true state -> pyrometer, ion gauge, regime indicator, thickness map (readings with quality flags)
```

- **Heater transient.** Implicit Euler on C dT/dt = net gain(T). The net gain and its Jacobian come from `HeaterModel.residual`, so the transient and the steady model share every radiation and conduction term. Heat capacities are lumped per ring. The wafer is Si at 900 J/kg/K. The element and ledge capacities are priors.
- **Heater control.** The power modes are:
  - `power`: holds a total power.
  - `feedforward`: applies the steady power for a target spot temperature, from a model-based table. This plays the role of thermocouple control before the pyrometer reads.
  - `pyrometer`: adds a PI trim on the reading.

  The PI gains are a hypothesis: internal-model tuning of the lumped plant (gain dT/dP from the table, time constant = total heat capacity × gain, closed loop at half of it), not identified dynamics. Power is clamped to the steady power that puts the hottest element ring at its limit. The heater network is cooperative, so a heater that starts colder never exceeds the limit under that clamp.
- **Sources and gas.**
  - **Ga:** the vacuum centre flux comes from one DSMC record (its absolute flux at its cell temperature), scaled by the Hertz-Knudsen factor p_vap(T)/sqrt(T).
  - **Active N:** output = eta × 2 × feed molecules/s, through the MFC lag (first order, exact over a sub-step).
  - **Pressure:** p = Q/S with time constant V/S, integrated exactly with the sub-step's mean feed.
  - **Arrival:** shape × the comparison's pressure tables (background attenuation times the scattered-arrival factor, including the plate plume).
- **Surface.** `growth.steady_state` per sub-step, wrapped in a persistent state:
  - **Thickness:** signed growth. Decomposition may etch the layer down to zero, and the decomposition the film cannot supply is recorded.
  - **Droplets:** droplet Ga persists across shutter closures. Under N-rich conditions it is consumed at the rate the unused N allows (a prior; the kinetics are unsourced).
  - **Ledgers:** atom ledgers for Ga and N.
- **Instruments.**
  - Pyrometer: area-weighted centre spot plus bias and noise; NaN with flag `below_range` below 600 C.
  - Ion gauge: sensitivity and noise.
  - Regime indicator: RHEED-like and idealized.
  - Thickness map: at the mapping radii.

  The controllers see readings only.
- **Time stepping.** Each recipe step is split into equal sub-steps of at most `dt_max`, so shutter and setpoint events fall on step boundaries and are never stepped across. The Ga cell is evaluated at mid-step, and the surface uses the end-of-step wafer temperature. The controller acts on the reading at the start of the sub-step (zero-order hold).
- **Realizable Ga and N control** ([control.py](../src/mbe_twin/control.py); recipe [gan_1um_720C_realizable.json](../cases/twin/gan_1um_720C_realizable.json)). The controllers know only the chamber's `controller_model`, which is the calibration state's maps, the Ga cell model and the centre-to-mean rate ratio, plus instrument readings.
  - `"n2_sccm": "rate_monitor"`: an in-situ growth-rate monitor measures the centre net rate over each 10 min of growth (`sensors.rate_monitor`: window, error, noise) and scales the commanded feed by (target + modelled decomposition) / (measured + modelled decomposition).
  - `"ga_cell": {"target_K": "steered"}`: the cell follows the window middle at the pyrometer reading through the calibrated model.
  - `"bfm": true` step: a beam-flux monitor at the wafer position reads the centre arrival while the wafer is out of the beam. The reading sets the model's correction factor.

  The protocol is that of the steady ensemble study (scripts/realizable_controller.py, [LAYOUT_COMPARISON.md](LAYOUT_COMPARISON.md) section 11).
- **Checkpoints.** `Twin.checkpoint()` / `restore()` serialize the full state, including the RNG. A run resumed at a shutter event is identical to an uninterrupted one (V13).

## 2. Chamber definition and the calibration/truth split

A chamber definition is one JSON file (contract in [chamber.py](../src/mbe_twin/chamber.py)). Its canonical hash goes into every run manifest. [twin_chamber.py](../scripts/twin_chamber.py) builds it from the layout comparison's keyed map caches:

- **Layout and supply:** layout B-L, eta 0.3, 4 m³/s, 35 sccm feed limit.
- **Arrival:** gas + plume arrival tables, 2 mm lip.
- **Heater:** the designed-density heater with zone fractions optimized at 720 C under the 1473 K element limit.

**Calibration and truth are separate.** The audit of 2026-10-05 (finding 1) showed that the steady studies' Ga steering also knew each uncertain state's maps. The twin avoids that by keeping two states apart:

- **Calibration state.** The operating point (pyrometer setpoint, N2 feed, Ga cell temperature) is solved once on the nominal pose with the 70 mm / 8 A Ga record, and then frozen. This mirrors a commissioning calibration.
- **Truth state.** The maps in the definition belong to the truth state, chosen with `--truth-tilt`, `--truth-fill` or `--truth-d`. The truth Ga reference is that record's own absolute flux, so a deeper charge at the frozen cell temperature delivers its depleted flux.

A perturbed-truth run therefore shows what the frozen settings grow when the machine differs from its calibration. The controllers observe only the pyrometer and the gauge.

Operating point (calibration state):

| Quantity | Value |
|---|---|
| Pyrometer spot setpoint | 720 C (993.15 K); true wafer mean 992.5 K, range 2.4 K |
| N2 feed / pressure | 18.6 sccm / 8.6e-3 Pa; plate Kn 22 |
| Ga cell | 1243.8 K (+16.2 K over the 70 mm record's 1227.6 K) |
| Centre Ga/N | 1.214, window 1.025-1.402 (Heying droplet law) |
| Heater power | 2382 W; element limit reached at 2387 W |

Priors written into the definition:
- chamber volume 0.5 m³ (sets only V/S = 0.125 s);
- MFC time constant 2 s;
- areal heat capacity of the element 3700 J/m²/K and of the Mo ledge 5700 J/m²/K;
- pyrometer spot 10 mm, noise 0.2 K, valid above 873 K;
- gauge noise 1 %.

## 3. Verification ([test_twin.py](../tests/test_twin.py), 15 tests)

| Case | Check | Result |
|---|---|---|
| Heater transient | Long-time limit equals the steady solve; per-step energy balance | < 1e-3 K; < 1e-6 of P dt |
| Heater transient | First order in time | Error ratio 2.33 for 4/2 s steps against 0.5 s, as expected |
| V09 | Constant flux, exact integrated thickness | 1e-12 relative |
| Surface ledgers | Ga, droplets, N, solid through droplet formation, consumption and etching to the substrate | < 1e-9 nm |
| V14 | Pyrometer reads the area-weighted spot of a prescribed field | exact; 0.05 K from the analytic mean |
| V07 | Pump-down and fill against the well-mixed solution | 1e-10 relative |
| Shutters closed | Nothing grows; the controller holds the reading | < 0.05 K |
| Shutter events | Atoms conserved; thickness = steady rate × exposure + consumed droplets − decomposition | 1e-12; 0.2 % |
| V13 | Restart at the shutter opening identical to the uninterrupted run | bitwise |
| Time step | Integrated thickness converges | < 1e-3 relative change at 2.5 s |
| Representative chamber | The twin's steady growth map equals the studies' steady chain at the operating point; 1 um/h; whole wafer in the adlayer regime | 1e-9; 0.2 % |
| Realizable controllers | On the tilted-source and 120 mm truth chambers, the rate monitor and BFM converge to the steady realizable solution (feed, Ga arrival) computed independently | 0.2 % |

On the representative chamber, a 0.5 s step gives the same 997.9 nm as the 1 s production step.

## 4. First results (records `data/runs/studies/twin_*.json`)

Recipe [gan_1um_720C.json](../cases/twin/gan_1um_720C.json), 146 min in total:
- 35 min open-loop heat-up to 650 C, with the Ga cell ramped at 15 K/min;
- 10 min pyrometer ramp to 720 C with the plasma on;
- 5 min stabilization;
- 60 min growth with both shutters open;
- 5 min N only;
- plasma off, then cool-down.

![Integrated twin run and frozen-setting sensitivity](figures/twin.png)

| Truth state (settings frozen from calibration) | Layer (nm) | Half-range / mean | Rate in growth (um/h) | Share of area in window |
|---|---:|---:|---:|---:|
| As calibrated | 997.9 | 0.57 % | 1.0000 | 100 % |
| Ga charge 40 mm (shallower) | 997.9 | 0.57 % | 1.0000 | 100 % |
| Ga charge 120 mm (deeper) | 985.0 | **2.53 %** | 0.987 | **38 %** |
| N source tilted 0.8 deg about the flange, direction 0 | 963.3 | 0.66 % | 0.966 | 100 % |
| N source tilted 0.8 deg about the flange, direction 180 | 1030.5 | 1.22 % | 1.033 | 100 % |
| Pyrometer bias +2 K | 999.2 | 0.57 % | 1.001 | 100 % |
| Pyrometer bias -2 K | 997.5 | 0.57 % | 1.000 | 100 % |

Same truth states with the realizable recipe (2 min BFM measurement before growth, Ga steered from the reading, rate monitor re-setting the feed every 10 min of growth), and the heater designed with a power margin:

| Truth state | Layer (nm) | Half-range / mean | Rate at the end of growth (um/h) | Share of area in window |
|---|---:|---:|---:|---:|
| Realizable: as calibrated | 997.9 | 0.57 % | 1.000 | 100 % |
| Realizable: Ga charge 40 mm | 997.9 | 0.57 % | 1.000 | 100 % |
| Realizable: Ga charge 120 mm | 997.9 | 0.57 % | 1.000 | **100 %** |
| Realizable: 120 mm, BFM reading 2 % high | 997.9 | 0.57 % | 1.000 | 100 % |
| Realizable: 120 mm, rate monitor 1 % high | 989.7 | 0.56 % | 0.990 | 100 % |
| Realizable: tilt 0.8 deg, direction 0 | 997.8 | 0.70 % | 1.009 | 100 % |
| Realizable: tilt 0.8 deg, direction 180 | 996.8 | 1.21 % | 0.991 | 100 % |
| Frozen recipe, heater zones designed to 1425 K | 997.9 | 0.64 % | 1.000 | 100 % |
| Same, pyrometer bias -2 K | 996.4 | 0.64 % | 0.999 | 100 % (no clamping) |
| Same, pyrometer bias +2 K | 999.2 | 0.63 % | 1.001 | 100 % |

Atom ledgers close to about 1e-13 and the heater energy balance to 2e-13 in every run. Wall time is 12-20 s for the 146 min recipe, against the PHASE1 gate of 60 min for a 60 min recipe.

What the runs show:
- **A depleting Ga charge is the first thing the frozen settings cannot absorb.**
  - At 120 mm the frozen cell temperature delivers 16 % less Ga (centre Ga/N 1.015 against 1.214), so the outer wafer turns N-rich.
  - At 40 mm it delivers 10 % more Ga (Ga/N 1.33), still inside the window. In Ga-rich growth the layer is set by N alone, so the thickness is unchanged.
  - This is the realizable-controller version of audit finding 1. Without a Ga flux measurement (BFM) or a fill-tracking schedule across the campaign, the 720 C point does not hold over the whole charge.
- **A 0.8 deg N pointing error moves the rate by -3.5 / +3.3 % at a frozen feed**, and the half-range by up to 0.65 points. The steady studies re-set the feed in each state (the rate is calibrated in the state the machine is in). In the twin that takes a growth-rate measurement.
- **There is no heater headroom at 720 C.**
  - The zone fractions optimized under the element limit put the hottest ring on the limit at the operating power (2382 of 2387 W).
  - With a reading 2 K low, the controller asks for more power and is clamped: the wafer stays at 993.17 K instead of the requested 995.15 K (470 clamped samples).
  - With a reading 2 K high, the wafer runs 2 K cold, as commanded.
  - Any disturbance that needs more power (emissivity, contact, film optics) would leave the wafer cold. The heater design needs a power margin at the operating point; the steady studies counted this case as "capped".
- **The realizable controllers recover the deep charge.**
  - The BFM step corrects the cell for the depleted flux, so the 120 mm charge grows like the calibrated machine.
  - A 2 % BFM error stays inside the window for this state.
  - The rate monitor pulls the centre N back to its calibration after a pointing error within about four windows. The mean rate then settles within 1 %, because one centre monitor cannot see the tilted map's centre-to-mean change.
  - A 1 % rate-monitor error passes straight into the rate.
- **Zones designed to 1425 K (14 % headroom) remove the clamp.** A reading 2 K low now gets the power it asks for (wafer mean 994.4 K). The nominal spread rises from 0.57 to 0.64 %.
- The steady ensemble over all states with these controllers is in [LAYOUT_COMPARISON.md](LAYOUT_COMPARISON.md) section 11. With rate monitor + BFM, the most uniform admissible points are B-p at 720 C with 3.7 % heater headroom (1.53 %) and B-L at 730 C with the current heater (1.67 %).

## 5. Disabled couplings and limits

These are recorded in every manifest (`disabled_physics`):

- Ga cell dynamics and the shutter flux transient (a few % for minutes on real cells).
- Collisional crucible transmission versus temperature.
- Adlayer transients (10-20 s, R20; flagged at each event).
- Droplet evaporation.
- Growing-film optics in the pyrometer and the heater (R16).
- Surface and wall re-emission into the gas.
- Plasma ignition dynamics.
- Hot cells and the plasma source as heat loads on the wafer.
- Azimuthal dose structure: the maps are rotation-averaged, and partial revolutions at shutter events are flagged.

The PI gains, the droplet-consumption rate and the heat capacities are hypotheses or priors. Growth is the steady GaN model of `growth.py`: no AlN, morphology or crystal quality.

## 6. Next steps for the twin

1. **Campaign simulation.** Run consecutive growths as the charge depletes, with a BFM check every n runs, to set how often the flux must be re-measured (done in the steady study only per state; the drift between measurements is a twin question).
2. **Commissioning dry run.** Generate synthetic commissioning data from a hidden truth chamber and check that the planned calibration sequence recovers the controller model.
3. **Sensor placement.** Compare one centre pyrometer with multi-spot or emissivity-corrected pyrometry under growing-film optics drift.
4. **Measured inputs.** Replace the priors (heat capacities, controller dynamics, cell transient) as vendor data and commissioning measurements arrive. Add the Al cell and AlN chemistry when the AlN model exists.
