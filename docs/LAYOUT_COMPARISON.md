# Layouts B and C at physically achievable operating points

Status: 2026-10-01 (second revision, after the [project audit](PROJECT_AUDIT_2026-10-01.md)), `representative_chamber`. These are model comparisons on a typical 200 mm RIBER/Veeco-class geometry, not predictions for the proposed machine. No nitrogen map, heater result or growth model here is validated against a measurement.

**Question this document answers:** under what physically achievable conditions does layout B or layout C meet the project's requirements?
**Short answer:** neither can be called a pass yet, because two requirements are not agreed: the uniformity target and the minimum growth rate. What the model can say is which conditions each layout needs, and what it trades. Section 1 gives those conditions; section 7 lists the hardware inputs that decide them.

Records:
- Inputs: the [design envelope](../data/design/design_envelope.json), where every input is marked known, assumed or missing.
- [layout_comparison_bc.json](../data/runs/studies/layout_comparison_bc.json): the uncertainty grid at each operating point.
- [nitrogen_rate_limits.json](../data/runs/studies/nitrogen_rate_limits.json): conversion thresholds and maximum rates.
- [layout_resolution_check.json](../data/runs/studies/layout_resolution_check.json): radial resolution.
- [layout_feasibility.json](../data/runs/studies/layout_feasibility.json): mechanical checks.

Commands are in [REPRODUCE.md](REPRODUCE.md).

## 1. Summary

**Nitrogen supply decides the growth rate before uniformity does.** 1 sccm of N2 carries at most 8.96e17 N atoms/s. Only a fraction eta of these leaves the plate as growth-active N, and the repository has no source for eta for any RF source. More feed raises the growth pressure, which attenuates both beams. Solving feed, pressure and attenuation together:

| 740 C, 1200 C element limit | B (46 deg, +105 mm) | C (65 deg, +75 mm) |
|---|---|---|
| Active N for 1 um/h at the self-consistent pressure (2 m^3/s) | 4.7e18 /s (4.2-5.2e18 over the grid) | 6.9e18 /s (6.3-7.6e18) |
| N2 feed for 1 um/h if every feed atom were active (eta = 1) | 5.2 sccm, 4.8e-3 Pa | 7.7 sccm, 7.1e-3 Pa |
| Smallest eta for 1 / 0.5 / 0.25 um/h within the 10 sccm feed limit, 2 m^3/s | 0.60 / 0.31 / 0.17 | 0.82 / 0.43 / 0.23 |
| The same, 0.5 m^3/s | unreachable / 0.75 / 0.40 | unreachable / unreachable / 0.54 |
| Highest rate at eta = 1: 2 / 0.5 m^3/s | 1.68 / 0.68 um/h | 1.22 / 0.49 um/h |
| Highest rate at eta = 1 with the plate holes free-molecular (feed <= 5.9 sccm) | 1.12 um/h (needs eta >= 0.90 for 1 um/h) | 0.81 um/h (1 um/h not reachable) |

- At 0.5 m^3/s effective pumping, neither layout reaches 1 um/h at any conversion. Attenuation caps the rate at about 8.4 sccm, where more feed starts lowering it.
- At 2 m^3/s, 1 um/h needs at least 60 % (B) or 82 % (C) of the feed's atoms to leave the plate as active N. The model has no evidence that an RF source reaches this. If eta is about 0.3, the ceiling is 0.48 um/h (B) and 0.34 um/h (C).
- With the leading plate (R30 hole set, 2000 x 0.343 mm in 0.5 mm), the holes leave the free-molecular regime above 5.9 sccm (smallest Kn = 10). Every map behind these results assumes free-molecular holes. C at 1 um/h needs 7.7 sccm, outside the plate model's validity. B at 5.2 sccm is inside it.

**Uniformity at the operating points that can be reached** (740 C, 1473 K element limit, 2 m^3/s, eta = 1 unless stated; thickness half-range/mean on r <= 94 mm, area-weighted std/mean in brackets):

| Rate | B nominal | B worst, +/-0.8 deg pointing and all other grid factors | C nominal | C worst, +/-0.8 deg | B thinner in matched states |
|---|---|---|---|---|---|
| 1 um/h | 1.06 % (0.58) | 2.38 % (1.43) | 0.94 % (0.62) | 2.76 % (1.69) | 70 % |
| 0.5 um/h | 1.07 % (0.57) | 2.88 % | 0.68 % (0.44) | 2.98 % | 49 % |
| 0.25 um/h | 1.39 % (0.74) | 4.22 % | 0.90 % (0.57) | 4.07 % | 42 % |
| 0.25 um/h at eta = 0.3 | 1.65 % | 4.49 % | 1.44 % | 4.75 % | 58 % |
| 1 um/h at 700 C | 0.87 % (0.49) | 1.82 % (1.07) | 0.79 % (0.51) | 2.19 % (1.30) | 71 % |

- **At 1 um/h, B is now ahead.** It is thinner in 70 % of matched states. Counting only states that also stay in the growth window, B wins 64 % and C 27 %. C's nominal advantage over the earlier comparison shrank (0.35 to 0.94 %), because the pressure its own feed creates (7.1e-3 Pa) degrades its vacuum-optimized aim more than B's.
- **At lower rates, B and C are unranked** (42-58 %). C is better nominally, and their worst cases are within 0.15 points of each other.
- **At 740 C, a lower rate does not buy uniformity.** Decomposition is then a larger share of the net rate, so the temperature map imprints more, and the worst case grows from 2.4 to 4.2 % (B) as the rate falls from 1 to 0.25 um/h. At 700 C the worst case is flat (1.8-2.0 %).
- **Shares of the +/-0.8 deg states that are in the window and within a threshold** (1 um/h, 740 C):

  | Threshold | B | C |
  |---|---|---|
  | 1 % | 36 % | 30 % |
  | 2 % | 89 % | 80 % |
  | 3 % | 90 % | 90 % |

  These are grid shares, not probabilities. The ceiling of 90 % is set by the heater (next point).
- **The heater limit now applies in every state.** The designed-density optimum runs the element at the 1473 K limit. A wafer whose emissivity is 10 % **higher** (0.77, not lower) loses more from its growth face and needs 1494.8 K to hold 740 C. Capped at the limit, it runs 14.5 K cold. Because the Ga flux is held fixed, the cold state leaves the Ga-rich window, by forming droplets, in two thirds of its combinations at 740 C and almost all at 700 C. This alone removes about 10 % of all states. The fix is about 22 K of element headroom, or a Ga-flux correction tied to the measured wafer temperature.
- **Ga flux is now held absolute.** The earlier comparison let the Ga centre flux follow each state's re-set nitrogen. Holding it fixed lowers the in-window share at 700 C from 84-85 % to 75-76 %. At 740 C, all states without the capped heater stay in the window.

**Recommendation.** Keep **B as the provisional working candidate** and C as the alternative. B needs 32 % less active nitrogen, reaches 1 um/h inside the plate model's validity and wins at 1 um/h. C's case rests on lower target rates and better pointing control. Neither is ready for design freeze until:
1. the uniformity target and minimum growth rate are agreed;
2. eta, or the source's output versus flow and power, is known: it decides whether 1 um/h exists at all;
3. the effective N2 pumping speed is known: 0.5 m^3/s rules out 1 um/h for both layouts;
4. the heater's element rating and headroom are confirmed.

## 2. Design envelope

Inputs that decide the comparison (full list in [design_envelope.json](../data/design/design_envelope.json)):

| Input | Value used | Status |
|---|---|---|
| Uniformity target | none; shares within 1 / 2 / 3 / 5 % reported | missing |
| Minimum growth rate | none; 1 / 0.5 / 0.25 um/h and the highest reachable rate reported | missing |
| Active-N fraction of the feed atoms, eta | scenarios 1 (bound) / 0.3 / 0.1 / 0.03; thresholds solved exactly | missing (no source in the repository) |
| N2 feed limit | 10 sccm | missing (H02 lists 0.1-10 sccm; the selected source's range is not specified) |
| Effective N2 pumping speed | 0.5 and 2 m^3/s | missing (2000 L/s nameplate known) |
| Nitrogen plate | R30 hole set, 2000 x 0.343 mm, 0.5 mm thick (L/r 2.92), 20 mm active radius, uniform output | assumed (thickness and pattern unpublished) |
| Growth temperature | 700 and 740 C, source labs' scales | missing |
| Heater element limit | 1473 K (1200 C as the element rating) and 1373 K (100 K life margin) | rating known, its object missing |
| Uniformity mask | r <= 94 mm for both layouts | assumed (edge exclusion missing) |
| Throw, cell cone | 350 mm, 46 deg | assumed |

## 3. Mechanical screening

`scripts/layout_feasibility.py` places all eleven sources as solids, using typical dimensions for the stated flange classes. Recorded results:
- smallest gap: 9.0 mm (B, Ga to Al cell) and 20.6 mm (C);
- off-centre port axis: 14.9 deg (B) and 6.4 deg (C);
- aim shift per 0.8 deg of tilt: 4-8 mm about the plate, 8-16 mm about the mounting flange.

**What this establishes:** no conflict was found in the modelled checks, with assumed dimensions. It is not a mechanical sign-off. The checks cover body/body, sampled flange/flange, shutter/body, and shutter/shutter with the other shutter at its end positions. They do not cover:
- every cross-type pair (for example flange/body);
- both shutters moving through their sweeps at once;
- the distance between continuous disks, which sampled points do not bound.

The cryoshroud, RHEED and pyrometer lines of sight, the main shutter and the manipulator need the chamber drawing. B's 9 mm Ga-Al gap is tight enough that the real cell and shutter drawings decide it.

The off-centre aim must be machined into the port (a tilt adapter of about +/-2 deg can only trim). A tilt about the mounting flange doubles the aim shift per degree.

## 4. Method

`scripts/layout_comparison.py` chains:
- the Ga DSMC records (centre-flux-held);
- the free-molecular nitrogen plate;
- the heater model under its element limit;
- the growth model, on the 94 mm mask.

**Operating point (one per layout and scenario).**
- Active-N output is q = eta x 2 x feed.
- Pressure is p = feed / S_eff, counting the whole feed as N2 because atoms recombine on the walls. Other gas loads are not included.
- Direct-beam attenuation of N and Ga at p is interpolated, in log, from tables computed on a grid of 0-0.05 Pa.
- The feed for the target rate is a fixed point. If it needs more than the feed limit, or does not exist, the row runs at the highest reachable rate.
- The hole Knudsen number at that feed is reported. Kn < 10 means the plate model is outside its validity.

**Protocol over the uncertainty grid.**
- **Nitrogen:** the output is re-set in each state for the operating rate, up to the output that the feed limit gives. Where the rate peaks below the feed limit, the peak feed is the cap. A state needing more grows slower and is counted as supply-limited.
- **Ga:** a fixed absolute centre flux, set once in the nominal state (70 mm fill, d = 8 A, nominal pointing, heater and 2 mm lip) to the middle of its Ga-rich window. Because N is re-set per state, the centre Ga/N ratio moves with it.
- **Heater:** zone ratios optimized for the nominal holder under the element limit, with the mean held by one wafer reading. A state needing more than the limit is capped there and grown at the temperature it reaches.

**Uncertainty grid** (all combinations; a grid, not a probability distribution):
- **N pointing:** 0.8 and 1.6 deg in 12 directions, about the plate centre or the mounting flange (49 maps).
- **Ga:** fill 40 / 70 / 120 mm and collision diameter 5.68 / 8 A.
- **Heater:** seven categories, each perturbed alone and **not combined with each other**: nominal; emissivity 0.63 / 0.77; contact 50 / 1000 W m^-2 K^-1; +/-2 % in the worst zone.
- **Holder lip:** 1 / 2 / 3 mm.
- **Droplet-onset law:** three literature scenarios.

**Not in the grid:**
- N plate output profile and plate geometry;
- scattered-beam redeposition;
- Ga cell pointing;
- combined heater errors;
- per-state pressure (the pressure stays at the operating point's).

**Scenarios** (not uncertainties): eta, S_eff, growth temperature, element limit and target rate. B and C are ranked only at equal target rates.

**Numerical checks.**
- Area means use annulus weights. On 39 radii they reproduce the exact disk mean of (r/R)^2 to within 1e-3.
- On 39 / 77 / 153 radii, the nominal thickness is 1.055 / 1.059 / 1.066 % (B) and 0.941 / 0.941 / 0.946 % (C).
- Computing attenuation and lip shadow directly, rather than as ratio profiles, agrees with the record to 0.001 points.
- Map caches carry a hash of their inputs and generating code, and a mismatched cache stops the run. The Ga records consumed are listed with their hashes.

## 5. Failure conditions

| Condition | Effect in the model | Layouts | Measurement or input that decides it |
|---|---|---|---|
| eta below 0.60 (B) or 0.82 (C) at 10 sccm and 2 m^3/s | 1 um/h not reachable; the rate scales with eta (0.3: 0.48 / 0.34 um/h) | both, C first | active-N output versus flow and power (vendor), then the Ga-rich growth rate at commissioning |
| Effective N2 speed about 0.5 m^3/s | 1 um/h not reachable at any eta; nominal 3.5 % (B) at the rate peak | both | effective speed at the chamber with the shroud cold; growth pressure at two or more flows |
| Feed above 5.9 sccm with the R30-like plate | holes transitional, so the N maps are outside the model's validity | C at 1 um/h; both when feed-limited | plate drawing (hole count, diameter, thickness); a plate with more or larger holes moves this limit |
| Element limit with no headroom above the designed-density optimum | the emissivity-0.77 state runs 14.5 K cold; with Ga held, about 10 % of states make droplets | both | vendor element rating and its object; heater power at the operating point; wafer temperature at more than one radius |
| Pointing worse than +/-0.8 deg, or tilt about the mounting flange | worst case 2.4-2.8 % (+/-0.8 deg) and 3.2-3.9 % (+/-1.6 deg) at 1 um/h | both, C more | aim-point repeatability on the actual mount |
| Holder lip 3 mm at C's 65 deg port | C nominal 0.94 to 1.25 % at 1 um/h | C | holder drawing |
| Growth at 700 C (source-lab scale) | 24-25 % of +/-0.8 deg states leave the Ga-rich window | both | droplet onset and N-rich boundary (RHEED) on the machine's scale |
| Low rate at 740 C | decomposition share imprints the temperature map: worst 4.1-4.2 % at 0.25 um/h | both | growth temperature and rate decision |
| Eleven sources on one 46 deg cone with larger bodies than assumed | B's 9 mm gap closes | B | cell, shutter and port drawings |

## 6. What this does not establish

- That any RF source reaches the eta that 1 um/h needs. No conversion figure is in hand.
- Hole flow above Kn 10, hole-wall recombination, tilted holes and the ion fraction. The plate model is free-molecular with straight holes and uniform output.
- Where scattered atoms land. Attenuation only removes direct beam, so at high pressure the delivered fraction is a lower bound and its shape is uncertain.
- Combined heater errors, the N output profile and Ga cell pointing, which are not in the grid.
- A uniformity pass or fail. No target is agreed, and grid shares are not probabilities.
- Mechanical clearance beyond the modelled checks (section 3).
- An improvement on real wafers, which only measured wafers can show, under the [improvement protocol](DATA_AND_VALIDATION_PLAN.md#demonstrating-wafer-uniformity-improvement).

## 7. Hardware inputs requested

Each request is tied to the threshold in this document that it decides.

| Input | What is needed | What it decides |
|---|---|---|
| Nitrogen source output | Active-N output (atoms/s), or the Ga-rich growth rate on a stated geometry, versus N2 flow (2-10 sccm) and RF power (up to 600 W), for the plate to be fitted; flow range and MFC calibration standard | Whether eta reaches 0.60 (B) / 0.82 (C) for 1 um/h; otherwise the achievable rate |
| Plate drawing | Hole count, diameter, plate thickness, pattern and active radius; hole tilt if any | Hole Knudsen limit (5.9 sccm for the R30-like plate); the N map shape (L/r) |
| Pumping | Effective N2 speed at the chamber with the cryoshroud cold; pump model and conductance | 0.5 versus 2 m^3/s: whether 1 um/h exists for either layout |
| Heater | Element temperature limit and what the 1200 C rating refers to; zone power capacity; lifetime in active N | Whether the designed-density heater has the about 22 K headroom the 0.77-emissivity state needs |
| Source mount and port | Port schedule and machining tolerance; mount type, tilt pivot and repeatability | Pointing tolerance (+/-0.8 or 1.6 deg) and pivot (plate or flange) |
| Holder | Lip height, opening radius, contact design | Lip shadow at C's 65 deg port; heater edge support |
| Chamber drawing | Port and flange schedule, cryoshroud, RHEED and pyrometer lines of sight, cell and shutter drawings | Mechanical clearance beyond the modelled checks; B's 9 mm Ga-Al gap |

## 8. Decisions needed from the project

1. **Uniformity target** (half-range/mean on the agreed mask). At 1 um/h and 740 C: a 2 % target keeps 89 % (B) and 80 % (C) of the +/-0.8 deg states. A 1 % target keeps 36 % and 30 %.
2. **Minimum growth rate.** If 0.5 um/h is acceptable, the conversion needed falls to 0.31 (B) / 0.43 (C), and B and C become unranked.
3. **Growth temperature** on the machine's scale. 700 C makes thickness insensitive to the heater but narrows the Ga-rich window.

## 9. Measurements to plan with the hardware team

Calibration and validation are kept separate: commissioning data that set model parameters are not reused to test them.

**Calibration (fits model inputs):**
1. Ga-rich growth rate at the wafer centre versus source power and flow. This sets eta, the most decisive unknown here.
2. Growth pressure and effective N2 speed at two or more flows, and beam flux with the plasma gas on and off. These set the attenuation.
3. Wafer temperature maps at two or more heater settings, with per-zone power and element temperature. These set the emissivity, contact and edge support.
4. Ga-limited (N-rich) thickness maps at two or more fills. These set the Ga collision size and the fill drift.
5. The aim point and its repeatability after remounting.

**Independent validation (not used in any fit):**
1. N-limited thickness maps with the chosen plate at its design aim and at one deliberately offset aim (+/-1 deg).
2. At least three repeated reference runs at the design point, to measure run-to-run scatter.
3. One growth temperature not used in the heater calibration.

## Appendix: earlier six-layout screening (superseded protocol)

The first comparison (record [layout_comparison.json](../data/runs/studies/layout_comparison.json), commit 6aca3b3) evaluated six layouts at fixed pressures. Its Ga flux followed each state's nitrogen, its perturbed heater states were not held to the limit, and its pressures did not follow the feed that the growth rate needs. Two kinds of result survive, because in Ga-rich growth thickness follows the N map:
- **map-shape conclusions:** the centre-aimed shallow-hole plate (A) gives about 11 % whatever else is done; deep holes (D, L/r 5.8) are worse than B and C; a thin plate (R0) has the best map but needs about twice A's nitrogen;
- **active-N ratios between layouts.**

Its window margins, heater-limited states and absolute nitrogen demands are superseded by this document.
