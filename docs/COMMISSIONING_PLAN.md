# Commissioning plan for the twin: calibrate at growth conditions, then test on held-out runs

Status: 2026-10-03 (revised after the same day's audit: nitrogen identifiability with flow-dependent conversion, and a temperature and Ga calibration rehearsal), draft for the hardware and process teams. Representative chamber; no measurement on the proposed machine exists yet.

This plan turns the general data plan ([DATA_AND_VALIDATION_PLAN.md](DATA_AND_VALIDATION_PLAN.md)) and the commissioning mapping of [PHASE1_CHAMBER_PLAN.md, section 6.1](../PHASE1_CHAMBER_PLAN.md#61-commissioning-as-the-primary-calibration-source) into a sequence for the working operating point: 1 um/h at about 720 C, Ga steered from a wafer-centre temperature reading ([LAYOUT_COMPARISON.md](LAYOUT_COMPARISON.md), section 8). Each step names the model input it fixes, the measurement, and the decision it can change. Most steps are tests the hardware programme runs anyway; they need only to be logged as described.

It does not choose recipes or machine limits. Operating points, flows and powers are set with the equipment team inside the approved limits.

## 1. Rules

1. **Calibration and validation are separate runs, declared before fitting.** Validation runs are whole wafers (or whole runs), never pixels or time samples from a calibration run. Section 6 lists the validation set. Its runs are named in the log before any calibration fit, and their results are not opened until the model is locked.
2. **Calibrate at growth conditions.** The background gas changes both beams at growth pressure, and the machine runs there. Fluxes, temperatures and maps are calibrated with the plasma on at the working flow, not in vacuum.
3. **One unknown per measurement where possible.** Several model inputs can compensate for each other in a single number (section 7). The sequence measures them in an order that breaks those pairs: vacuum first, then temperature, then Ga, then active nitrogen.
4. **Lock the model, then predict.** Before each validation run, the twin's prediction (map, rate, window margin) is archived with its model version (git commit and input hashes). The comparison is made afterwards against that archived prediction.
5. **Repeatability first.** Three repeats of one reference condition early in commissioning give the run-to-run scatter. Every later agreement or disagreement is judged against it.
6. **Calibrate the growth window on the machine's own reading.** The window the Ga is steered into is measured against the pyrometer reading (steps 2 and 6), not looked up from literature laws at an absolute temperature. The literature laws and the source labs' temperature scales are too uncertain for the +/-3 K budget (section 6.2); a window measured on the machine's reading does not need an absolute temperature.

## 2. What the twin needs from the machine

| Model input | Now in the twin | Measurement | Decision it can change |
|---|---|---|---|
| Effective N2 pumping speed | bracket 0.5 / 2 / 4 m^3/s | chamber pressure at two or more N2 flows, plasma off and on | whether 1 um/h is reachable; growth pressure; how much both beams scatter |
| Active-N conversion eta | scenarios 1 / 0.3 / 0.1; literature 0.06-0.57 | Ga-rich growth rate at the wafer centre versus flow and RF power | layout (B-L or B-p), feed, reachable rate |
| Decomposition against the reading | G02's law on G02's scale (fitted 720-805 C) | in-situ GaN decomposition rate at three or more readings | the decomposition added back to the N calibration; the twin's temperature scale for comparison with the literature (to 15-60 K only, section 6.2) |
| Wafer temperature map | heater model, not validated | temperature at more than one radius (multi-spot pyrometry or an instrumented wafer) at two or more settings | heater zone ratios; how much temperature spread becomes thickness spread |
| Pyrometer reproducibility during growth | +/-2 K assumed | the reading against the same physical event (droplet onset, decomposition rate) on a thin and a thick GaN layer, and wafer to wafer | whether steering Ga from the reading works (section 5) |
| Ga flux at growth pressure | crucible model and DSMC, Ga atom size 6-8 A | N-rich growth rate (rate set by Ga) at the working flow, plasma on | the Ga cell set point; the Ga/N ratio map |
| Ga map | DSMC at fills 40 / 70 / 120 mm | thickness map of an N-rich (Ga-limited) layer at two fills | the fill range a port angle tolerates |
| N map and aim | plate model, pointing ensemble +/-0.8 deg | thickness map of a Ga-rich (N-limited) layer at the design aim | the aim offset; the plate |
| Aim repeatability | +/-0.8 / 1.6 deg ensembles | the N-limited map after remounting the source | whether the mount needs an adjustment |
| Droplet onset (Ga-rich window) | three literature laws, up to 3-4x apart at 700 C | Ga droplet onset (RHEED, post-growth microscopy) at two or more readings bracketing the operating one, to about 5 % in flux | the Ga set point inside the window; the cold limit |
| Ga/N ratio at the working point | exact in the twin | the stoichiometric Ga flux at the working N flux and reading (growth-rate knee or RHEED), or N-rich and Ga-rich rates to about 0.5 % | where the Ga sits inside the window |

## 3. Sequence

### Step 1. Vacuum, before any growth (FAT and SAT)

- Log the chamber pressure at three or more N2 flows covering the planned range (for example 2, 10, 25 sccm), with the cryoshroud cold, plasma off and then on.
- Fit the effective N2 speed S = Q / p from the plasma-off points. The plasma-on points show how much the hot discharge gas changes the pressure.
- Record the gauge type, its position and its N2 correction factor. A gauge near a cold shroud reads differently from the gas the beams cross.

Output: S, and the growth pressure at each flow. This replaces the 0.5 / 2 / 4 m^3/s bracket.

### Step 2. Temperature scale

The growth model's rates and the Ga-rich window are on the temperature scales of the labs whose data it uses: decomposition from G02, the droplet onset from three other sources. These scales are not known to agree with each other or with a true temperature, and the decomposition activation energy itself is uncertain (3.1-3.6 eV in the literature). Matching the machine's decomposition rate to the twin's law therefore transfers G02's scale under G02's law. It does not measure the true temperature, and it says nothing about the scale of the droplet law. The rehearsal of section 6.2 puts the resulting error at the operating point at 15-60 K (95 %), depending on how far apart the labs' scales are; adding a Si(111) anchor does not reduce it.

The plan therefore does not depend on an absolute temperature. Every temperature-dependent quantity the Ga steering uses is measured against the machine's own reading:

1. **Decomposition against the reading.** On a GaN layer, with the Ga and N shutters closed and the N2 flow at the working value, measure the thickness loss rate (laser reflectometry, or RHEED/QMS signals) at three or more readings around and above the operating one. The fit of rate against reading is what the N calibration adds back (step 4). It is also the twin's estimate of how the machine's reading relates to G02's scale, but only to the accuracy above.
2. **Droplet onset against the reading** (step 6). This, not an absolute temperature, places the window's upper edge.
3. **Si(111) 7x7 to 1x1 transition** on a bare wafer before growth (literature values 830-870 C). An independent absolute check, useful for comparing the machine with published recipes, but its own spread (about +/-10 K) is too large to calibrate the window with. If an absolute temperature to a few K is needed for another purpose, it needs a sharper anchor: a eutectic on a test wafer (Al-Si at 577 C) or band-edge thermometry of the substrate.
4. Record the pyrometer reading (and heater powers and thermocouple readings) at each of these. Repeat one of them through a thick GaN layer: the difference is the reading's drift with layer thickness, which counts against the budget of step 5.
5. Map the wafer temperature at two or more heater settings (multi-spot pyrometry, or an instrumented wafer at FAT). Fit the heater model's contact and emissivity to the maps, not to a single spot (one spot cannot separate contact, emissivity and power). The maps need temperature differences across the wafer, not absolute values.

### Step 3. Ga flux at growth pressure

- With the plasma on at the working flow and power, grow under N-rich conditions (Ga-limited). The growth rate then gives the Ga flux that actually reaches the wafer at growth pressure, including whatever the background gas scatters.
- Repeat at two or three cell temperatures to fit the cell's flux against temperature at growth pressure.
- Do not use a beam-flux gauge reading taken with N2 flowing as the calibration. The gauge also sees the N2, and its position is not the wafer's.
- Grow one Ga-limited layer at each of two crucible fills (early and late in the charge) and map its thickness. This tests the twin's Ga map and its fill dependence.

The twin's estimate of gas scattering (section 10 of [LAYOUT_COMPARISON.md](LAYOUT_COMPARISON.md)) says that most scattered Ga still reaches the wafer. A vacuum calibration would therefore be wrong by about 10 % rather than the 50-70 % the direct-beam model implied. Calibrating at growth pressure removes the question either way.

**Precision.** For the Ga set point, what matters is the excess Ga - N at the working point, not the Ga flux alone. The window is narrow: its half-width at 720 C is 2.1-4.8 nm/min (by droplet law) against an N flux of about 17 nm/min. Separate N-rich and Ga-rich rate calibrations with 1 % noise each put the excess off by the equivalent of 2.8-4.4 K of reading error (95 %), and with 2 % by 5.4-8.1 K (section 6.2). Either both rates are measured to about 0.5 % (repeats at the working point), or the stoichiometric Ga flux is measured directly at the working N flux and reading (the knee of growth rate against Ga flux, or the RHEED adlayer signature), and the Ga is set relative to that point.

### Step 4. Active nitrogen

- **Throttle series first (C6b).** At the working flow and RF power, grow Ga-rich (N-limited) at the wafer centre with the pumping throttled in four or five steps (for example to 1, 0.7, 0.5, 0.35 and 0.25 of full speed, with a gate valve that can be set reproducibly). The flow, and hence the discharge and eta, stay fixed while the chamber pressure rises up to four times. The rate against the measured pressure tests the scattered-atom model, including whether the walls return N atoms, independently of eta (section 6.1).
- Then grow Ga-rich at the wafer centre at four or more flows (including the working flow) and two or more RF powers inside the bright-mode range. With the scattering model fixed by the throttle series, these give eta(flow, power). Without the throttle series they cannot test the scattering model: a conversion that changes with flow absorbs the difference (section 6.1).
- At the working flow and power, grow one N-limited layer at the design aim and map its thickness. That map tests the plate model and the aim.
- Remount or re-aim the source once and repeat the map. This measures the pointing repeatability that the +/-0.8 deg ensemble stands in for.

eta and the active-N map are degenerate in a single centre growth rate: a different map shape with a different eta gives the same centre rate. The full-wafer map in this step breaks that.

The throttle series assumes that the discharge does not feel the chamber pressure at fixed flow and power. The pressure behind the plate is hundreds of times the chamber pressure, so this is expected, but log the discharge's optical emission at each throttle step to check it.

### Step 5. Ga steered from the temperature reading

The working operating point relies on correcting the Ga supply from a wafer-centre reading: the Ga-rich window moves with temperature, and a fixed Ga supply leaves it when the wafer runs warmer or colder than planned.

- Implement the correction as the twin computes it: Ga set point = window middle at the reading, from the calibrated droplet onset (step 6) and the measured active-N flux.
- Test it by deliberately offsetting the heater (for example +/-10 K) and checking with RHEED that the surface stays in the Ga-rich (adlayer) regime without droplets.
- **The budget is about +/-3 K of equivalent reading error in total** (section 8), and the reading is only one part of it. The other parts are the window calibration (the droplet onset, step 6) and the Ga/N ratio (step 3), each converted to the reading error that would shift the Ga set point by the same amount (section 6.2). With the onset found to 5 % (1.6-2.9 K) and the Ga/N excess as good as 0.5 % rate calibrations (1.6-2.6 K), only about 1-2 K is left for the reading. That is a reproducibility requirement, between the calibration runs and production and from wafer to wafer, through the growing layer; an absolute accuracy is not needed (rule 6).
- GaN on Si changes the apparent emissivity as the layer thickens (thin-film interference), and a single-wavelength pyrometer without correction can drift by much more than this. Specify an emissivity-corrected (reflectance-compensated) pyrometer or band-edge thermometry of the substrate, and check its drift through a thick GaN layer against a fixed physical event (step 2, item 4). [Section 8](#8-sensitivity-to-the-pyrometer-error) gives the twin's sensitivity to this error.

### Step 6. Growth window

- At two or more readings that bracket the operating reading (for example 700 and 740 C), find the Ga flux at which droplets start, at the working N flux: RHEED during growth and microscopy afterwards. Interpolate to the operating reading; do not extrapolate.
- Each onset needs to be found to about 5 % in Ga flux. At 10 % the window edge alone uses 3.1-6.1 K of the budget (section 6.2), at 20 % 6-12 K.
- This replaces the three literature droplet laws, which disagree by up to 3-4 times at 700 C, by the machine's own onset on the machine's own reading.

## 4. Calibration set

| # | Run | Fits |
|---|---|---|
| C1 | Pressure versus flow, plasma off and on | effective speed S |
| C2 | Decomposition rate at three or more readings; Si(111) transition; one point repeated through a thick GaN layer | decomposition against the reading; the reading's drift with layer thickness; absolute scale (roughly) |
| C3 | Temperature maps at two settings | heater contact and emissivity |
| C4 | N-rich growth rate at two or three cell temperatures, plasma on; the stoichiometric Ga flux at the working point | Ga flux versus cell temperature at growth pressure; the Ga/N ratio |
| C5 | Ga-limited thickness maps at two fills | Ga map shape and fill dependence |
| C6b | Ga-rich centre growth rate at the working flow and power, pumping throttled in four or five steps | the scattered-atom model, including N wall return |
| C6 | Ga-rich centre growth rate versus flow (including the working flow) and power | eta(flow, power), given C6b |
| C7 | N-limited thickness map at the design aim | active-N map shape |
| C8 | Droplet onset at two or more readings bracketing the operating one | the window's upper edge against the reading |
| C9 | Three repeats of one reference condition | run-to-run scatter |

## 5. Validation set (held out, declared before fitting)

| # | Run | Tests |
|---|---|---|
| V1 | N-limited map at one deliberately offset aim (for example 10-15 mm) | the plate and pointing model away from its calibration point |
| V2 | Full growth at one temperature not used in C2-C3 and C8 (for example 720 C) | temperature scale, decomposition and window together |
| V3 | Full growth at a second flow inside the calibrated flow range (different pressure) | the pressure dependence: attenuation and scattered atoms |
| V4 | One wafer with the heater deliberately offset and Ga steered from the reading | the steering protocol (step 5) |
| V5 | A later run late in the Ga charge (fill not used in C5) | Ga depletion and the fill dependence |

The twin passes a validation run if the measured half-range/mean and the centre rate fall inside its prediction interval. The interval combines the twin's own uncertainty with the C9 scatter. Pass/fail tolerances are set from C9 before V1-V5 are opened.

## 6. Synthetic rehearsal (can be done now)

Before the machine exists, the plan can be tested on the twin itself:
1. Choose "true" values for the unknowns (S, eta, temperature offset, contact, emissivity, Ga atom size, droplet law) away from the twin's nominal ones.
2. Generate the C1-C9 measurements from the twin with those values, with realistic noise (the C9 scatter is not known yet; use 1-3 %).
3. Run the calibration fits on them and check which unknowns come back, and which only come back as combinations.
4. Predict V1-V5 with the fitted twin and compare with the "true" twin.

This shows whether the measurement list is enough before any wafer is spent.

### 6.1 Nitrogen supply

Script `scripts/commissioning_rehearsal.py`, record [commissioning_rehearsal.json](../data/runs/studies/commissioning_rehearsal.json). Setup:
- **True machines:** B-L at eta 0.3 and 4 m^3/s, and B-p at eta 1 and 2 m^3/s. The scattered atoms follow gamma = 1 or 0.1. The true eta is either constant with flow or falling as (Q_working / Q)^0.25, about 1.5 times higher at the lowest calibration flow. That trend is plausible at fixed power, not measured.
- **Measurements:**
  - C1 and C6 at four or five flows, with 3 % gauge noise and 2 % rate noise, and with or without a common +10 % gauge-factor error;
  - C6b at the working flow, with the pumping throttled to 1, 0.7, 0.5, 0.35 and 0.25 of full speed.
- **Fits:** 2000 noise draws, each fitted with three scattered-atom models (direct beam only, gamma 1, gamma 0.1) and five designs.

Share of draws in which a candidate model is rejected (chi^2 above its 95 % point), over both machines, both true scattering models and both gauge cases. "Wrong" is the range over the two wrong models; "true" is how often the true model is rejected:

| Design | True eta constant: wrong / true | True eta falling: wrong / true | eta at the working flow, true model |
|---|---|---|---|
| Flows, one constant eta (the first rehearsal) | 11-100 % / 4-7 % | 100 % / 100 % | +16-18 % when eta falls |
| Flows, eta linear in flow | 4-6 % / 4-6 % | 65-99 % / 82-98 % | -4 to -6 % when eta falls |
| Flows, eta quadratic in flow | 4-6 % / 4-6 % | 8-26 % / 10-21 % | within 0-4 % |
| Throttle series (C6b), one eta | 100 % / 6-20 % | 100 % / 6-18 % | within 0-3 % |
| Throttle series + flows, eta quadratic in flow | 100 % / 6-17 % | 100 % / 10-24 % | within 0-3 % |

- **The audit was right: flows alone cannot test the scattered-atom model.** The earlier result (direct-only rejected in 90-100 % of draws) holds only if eta is constant with flow. Once eta may change with flow, as the plan's C6 fit allows, no model is rejected more often than chance, or the true one is rejected as often as the wrong ones. The fitted eta then differs between the models by a factor of 1.5-3.
- **The throttle series (C6b) separates all three models,** in every draw and for both eta trends. That includes whether the walls return N atoms, which the flow series could not separate even with constant eta (11-67 % last night). At fixed flow the discharge and eta stay fixed, and the pressure reaches four times the working value, where the models differ most. eta at the working flow comes back within 0-3 %.
- **Extrapolating eta in flow is the remaining risk.** With eta falling, the rate predicted at a held-out flow beyond the calibrated range (35 sccm for B-L, 10 sccm for B-p) is off by 3-17 % even with the right model, but within about 1 % at a held-out flow inside the range (throttle series plus flows). The calibration flows should therefore span the working flow and any validation flow (V3).
- **The true model is rejected somewhat more often than the nominal 5 %** (up to 24 %). This comes from the +10 % gauge-factor error and from the quadratic's misfit to the true eta trend. It does not affect which model wins, but the chi^2 threshold should come from the C9 repeats, not the textbook value.
- **Fits are robust to the gauge.** A 10 % gauge-factor error moves eta by 1-3 %.

### 6.2 Temperature and Ga

Script `scripts/temperature_ga_rehearsal.py`, record [temperature_ga_rehearsal.json](../data/runs/studies/temperature_ga_rehearsal.json), 20000 draws per case.

**Common currency.** The cold-limit study (section 8) biases the reading by b. The Ga is steered to the window middle the reading implies, so the droplet edge moves by dF_crit/dT x b. Any calibration error is expressed as the reading error b_eq that would shift the Ga set point by the same amount, at 1 um/h and 720 C. The window half-width there is 2.1, 3.4 and 4.8 nm/min for the three droplet laws.

**True machine, per draw:**
- the reading is off by an offset (+/-30 K) and a slope (5 K per 100 K);
- the decomposition energy lies anywhere in the literature's 3.1-3.6 eV;
- the decomposition and droplet laws each sit on their source lab's scale, off the true temperature by an independent normal error (sd 5, 10 or 20 K);
- each of the three droplet laws is the truth in turn.

**Measurement noise:**
- decomposition rate 5 %;
- Si(111) transition 830 C +/- 10 K, read to 2 K;
- droplet onset 5, 10 or 20 % in flux;
- growth rates 0.5, 1 or 2 %.

| Route to the Ga set point | b_eq, 95 %, by lab-scale sd 5 / 10 / 20 K |
|---|---|
| A. Literature droplet law at a temperature from decomposition alone | 16 / 30 / 58-59 K |
| B. As A, plus the Si(111) anchor | 18-19 / 33 / 60-61 K |
| C. Onset measured at two readings (C8), 10 % noise, interpolated | 3.2-5.8 / 3.4-6.1 / 3.9-7.2 K |
| C with 5 % / 20 % onset noise | 1.6-2.9 / 6.3-12 K (lab sd 5 K) |
| Ga/N from N-rich and Ga-rich rates, 0.5 / 1 / 2 % each | 1.6-2.6 / 2.8-4.4 / 5.4-8.1 K (lab sd 5-10 K) |

- **Decomposition does not calibrate the temperature for the window.** It transfers G02's scale under an energy that is uncertain by 0.5 eV, and says nothing about the droplet laws' own scales. The absolute temperature it gives at the operating point is off by 13-43 K (95 %). The Si anchor, with its own +/-10 K spread, does not help. The audit's point stands, and the plan no longer relies on it (rule 6, step 2).
- **Measuring the onset on the machine's reading removes the scale question.** What remains is the onset's own measurement noise. That is within budget only at about 5 %.
- **The Ga/N ratio is as demanding as the temperature.** Two rate calibrations at 2 % each use 5-8 K of equivalent reading error; at 0.5 % they use 1.6-2.6 K.
- **The +/-3 K of section 8 is therefore a total budget, not a pyrometer accuracy.** Onset at 5 % plus Ga/N at 0.5 % comes to about 2.3-4.0 K root-sum-square before any reading drift. Holding the working point at 720 C needs all three near their best, and the reading reproducible to about 1-2 K. Otherwise the operating point moves to 730 C or above (section 8).

Not rehearsed:
- the heater maps (C3);
- cell drift between calibration and growth;
- a direct measurement of the stoichiometric point.

Cell drift adds to the Ga/N term one for one. A direct stoichiometric measurement could replace the two rate calibrations if it resolves the point to better than 1 %.

## 7. Pairs that one number cannot separate

| Pair | Why they compensate | Broken by |
|---|---|---|
| eta and the active-N map shape | the same centre rate from a peaked map and low eta, or a flat map and high eta | the full N-limited map (C7) |
| eta(flow) and N scattering | a higher flow raises the pressure, which scatters more N; a conversion that falls with flow does the same to the rate | the throttle series (C6b): pressure changed at fixed flow and eta (section 6.1). Rates at several flows alone do not separate them |
| eta and N wall recombination | walls that return N atoms raise the arrival at every flow, as a higher eta does | the throttle series (C6b), in the rehearsal (section 6.1); the full N-limited map (C7) as a check |
| Heater contact and wafer emissivity | both shift the wafer temperature at one spot | maps at two settings (C3) |
| Temperature offset and decomposition law | both move the decomposition rate at a fixed reading; the law's energy (3.1-3.6 eV) and its lab's scale are uncertain | not broken by decomposition (section 6.2). Not needed: the window is measured against the reading (C8). An absolute temperature needs a sharp independent anchor (a eutectic, band-edge thermometry) |
| Ga flux and the Ga atom size | at growth pressure both change the arriving Ga | calibrating Ga at growth pressure (C4) makes the size irrelevant to the set point |
| Droplet law and temperature scale | both move the window edge | droplet onset measured against the reading, at readings bracketing the operating one (C8) |
| Reading drift and window calibration | a reading that drifts with layer thickness looks like a shifted window | one fixed event (decomposition or onset) measured on a thin and a thick layer (C2) |

## 8. Sensitivity to the pyrometer error

The twin was re-run with the centre pyrometer biased by -b, 0 and +b K. Each case uses the combined heater errors, the +/-0.8 deg pointing ensemble, the Ga fills, atom sizes and droplet laws, and the scattered atoms and plume (scripts/operating_cold_limit.py --pyrometer-bias; [LAYOUT_COMPARISON.md](LAYOUT_COMPARISON.md), section 8):

| Reading error | Best share of states in the growth window | Coldest temperature for 1 um/h |
|---|---|---|
| +/-2 K | 98-99 % | 720 C |
| +/-3 K | 96-97 % | 720-730 C |
| +/-4 K | 95-96 % | 730 C at eta = 1; none for the large plate at eta = 0.3 |
| +/-5 K | 94 % | none up to 790 C |
| +/-10 K | 89 % | none up to 790 C |

The requirement is therefore a reading accurate to about +/-3 K during growth, through the growing layer, on the calibrated scale of step 2. A reading error does not average out with time: the heater holds the wrong temperature, and the Ga is steered for it.

## 9. Hardware implications

- A pyrometer (or other sensor) that sees the wafer centre during growth and stays accurate through a growing GaN layer on Si, as in step 5. This is the one sensor the operating point depends on.
- Logging of per-zone heater voltage and current, the pyrometer reading, gauge readings, flows and RF power at a common clock (PHASE1_CHAMBER_PLAN section 6.1).
- If possible at FAT: an instrumented wafer or multi-spot temperature access at more than one radius (C3).
- A mount for the nitrogen source whose aim can be checked and repeated (step 4, V1).
- Pumping that can be throttled reproducibly in a few steps down to about a quarter of full speed (a gate valve with position readout, or a throttle valve), for the C6b series that separates the nitrogen scattering model from the conversion.
- Optical emission monitoring of the nitrogen discharge, to check that throttling does not change it.
- Ga droplet-onset detection fine enough to find the onset to about 5 % in Ga flux (RHEED with fine Ga flux steps), and a Ga cell stable to well under 1 % over a run.
