# Layout comparison at equal growth rate, with uncertainty and failure conditions

Status: 2026-10-01, `representative_chamber`. These are model comparisons on a typical 200 mm RIBER/Veeco-class geometry, not predictions for the proposed machine. No nitrogen map, heater result or growth model here is validated against a measurement. The purpose is to say which source layout to carry into design freeze, over what operating range it works, and which measurement could overturn that choice.

Inputs: [design envelope](../data/design/design_envelope.json) (each input marked known, assumed or missing). Records: [layout_feasibility.json](../data/runs/studies/layout_feasibility.json) and [layout_comparison.json](../data/runs/studies/layout_comparison.json). Commands: [REPRODUCE.md](REPRODUCE.md).

## 1. Summary

- **A finite-hole nitrogen plate must be aimed off-centre.** Aimed at the wafer centre (layout A), the shallow-hole plate gives 11 % thickness half-range/mean. Nothing else in the layout changes that, and at 700 C its Ga/N spread closes the growth window in two thirds of the uncertainty states. This conclusion holds in every uncertainty state at every pressure up to 7.4e-3 Pa.
- **Two manufacturable off-centre layouts remain, and the model cannot rank them.** B aims the shallow-hole plate from the common 46 deg cell cone at +105 mm. C uses a steep 65 deg port aimed at +75 mm. At 740 C, with a 1200 C element limit and 2 sccm into 2 m^3/s:

  | | B (46 deg, +105 mm) | C (65 deg, +75 mm) |
  |---|---|---|
  | Thickness, nominal | 0.83 % | 0.35 % |
  | Worst state, pointing within +/-0.8 deg | 2.1 % | 3.1 % |
  | Worst state, pointing within +/-1.6 deg | 3.0 % | 4.6 % |
  | Active-N output needed for 1 um/h | 4.2e18 atoms/s | 5.8e18 atoms/s (1.37x B) |
  | Port and mounting | Port machined 14.9 deg off the centre line | Port 6.4 deg off; extra flange position |
  | Clearance | 9 mm | 21 mm |

  C is thinner in 51 % of the matched uncertainty states and B in 49 % (45-57 % across all temperatures, heater limits and pressures up to 7.4e-3 Pa). C is better nominally and when the source tilts about the plate centre. B is better when the source tilts about its mounting flange by more than 0.8 deg, or when the holder lip is 3 mm high. B also needs 27 % less active nitrogen.
- **Recommendation for design freeze:** carry **B as the leading layout** and C as the alternative. B fits on the existing cell cone, and it has the smaller worst case and the lower nitrogen demand. Its single risk is mechanical: the plasma-source port must be machined to the off-centre aim, because a tilt adapter cannot supply 15 deg. Switch to C if the source pivot and pointing can be held to +/-0.8 deg about the plate centre, the lip is at most 2 mm, and the source can supply the extra 37 % active nitrogen.
- **Deep holes (L/r 5.8, layout D) are worse on every metric except nitrogen demand** (3.3 % worst at +/-0.8 deg). Keep them only if the source hardware forces a thick plate. A thin plate (R0, L/r 0) is the best map (1.05 % worst at +/-0.8 deg) but is an ideal reference, and it needs twice the active nitrogen of A.
- **Growth temperature decides the Ga side.** At 740 C every candidate stays in the Ga-rich window in every state. At 700 C, 4-23 % of the +/-0.8 deg states leave it, and the Ga port angle matters: a 54 deg Ga port (C-Ga54) keeps 96 % of the +/-0.8 deg states in the window, against 85 % at 46 deg. It does not change thickness.
- **The heater limit is binding but not decisive for thickness.** The unconstrained designed-density heater runs its element at 1652 K (1379 C), above both interpretations of the 1200 C rating. Held to 1473 K, its wafer range rises from 1.7 to 3.0 K and candidate thickness by at most 0.1 point (0.15 point at 1373 K). A wafer whose emissivity is 10 % lower then needs about 1495 K at the element to hold the mean, so specify at least about 25 K of element headroom above the operating point.
- **Pressure range.** Up to about 2e-3 Pa (2 sccm into 2 m^3/s) the background-gas attenuation moves the results by at most 0.2 point. At 7e-3 Pa the nominal maps worsen by 0.2-0.9 point and the aims would have to be re-optimized. At 3.7e-2 Pa every layout fails: at least 2.2 % thickness and three times the nitrogen output.
- **Nitrogen supply is the largest open feasibility question.** 1 um/h on the usable 188 mm needs 3.7-7.4e18 active N atoms/s leaving the plate. That is the atom content of 4-8 sccm of N2 at full dissociation. No vendor output figure is in hand.

## 2. Design envelope

The baseline and the alternatives are defined in [data/design/design_envelope.json](../data/design/design_envelope.json). Every input there carries a status. The ones that decide the comparison:

| Input | Value used | Status |
|---|---|---|
| Net growth rate | 1 um/h, wafer mean, the same for all layouts | assumed (no project rate requirement) |
| Growth temperature | 700 and 740 C on the source labs' scales | missing (machine scale and target) |
| Uniformity mask | r <= 94 mm for every layout (3 mm holder overlap + 3 mm edge exclusion) | assumed (edge exclusion missing) |
| Sources | 10 cell positions: 3 Ga, 3 Al, Si, Mg, 2 spare, plus one RF nitrogen source | known (proposal) |
| Cell cone, throw | 46 deg, 350 mm | assumed |
| Bodies and flanges | Ga CF150 (body radius 60 mm), Al and N CF100 (45 mm), Si / Mg / spare CF63 (32 mm), 300 mm long; rotary shutters | Ga flange class known (H03); the rest assumed; drawings missing |
| Nitrogen plate | shallow holes L/r 2.9 (lead), L/r 0 (reference), L/r 5.8 (alternative), 20 mm active radius, uniform output | missing (vendor plate drawing) |
| Pointing | axis tilt up to 0.8 deg (and 1.6 deg) in any direction, about the plate centre or the mounting flange 0.30 m behind it | assumed; adjuster range missing |
| Heater | 3 uniform zones (3 mm overlap) or designed density (1 mm overlap); element limit 1473 K (1200 C as the element rating) or 1373 K (with 100 K life margin) | rating known (proposal), its object missing |
| Holder lip | 2 mm proud of the wafer face (1-3 mm) | assumed |
| Background pressure | 0 (regression), 4.6e-4, 1.9e-3, 7.4e-3, 3.7e-2 Pa from 0.5-10 sccm into 0.5-2 m^3/s at 300 K | flow and effective speed missing |
| Active-N output capability | not set; required output reported | missing |

Layouts:

| Layout | Ga port | Nitrogen | Heater |
|---|---|---|---|
| A (baseline) | 46 deg | L/r 2.9 on the 46 deg cone, aimed at the centre | 3 zones, 3 mm overlap |
| B | 46 deg | L/r 2.9 on the 46 deg cone, aimed +105 mm | designed density, 1 mm overlap |
| C | 46 deg | L/r 2.9 on a 65 deg port, aimed +75 mm | designed density |
| C-Ga54 | 54 deg (fills 70-120 mm only) | as C | designed density |
| R0 (ideal reference) | 46 deg | L/r 0, 45 deg, +55 mm | designed density |
| D (deep-hole alternative) | 46 deg | L/r 5.8, 65 deg, +110 mm | designed density |

The nitrogen aims are the earlier free-molecular optima (B: the second valley of the L/r 2.9 scan at 45 deg, which keeps the source on the cell cone).

## 3. Mechanical feasibility

`scripts/layout_feasibility.py` places all eleven sources as solids: body cylinders to the flange, flanges, and shutter blades over their whole opening sweep. Neighbours are spaced in azimuth by body size, and each shutter's swing side is chosen to maximize the smallest gap. It then checks the clearances, the beam shadowing in the growth state (Ga and N shutters open, the others closed) and the nitrogen adjustment.

| Layout | Smallest gap | N tilt off a centre-pointing port | Aim shift per 0.8 deg: plate pivot / flange pivot | Shadowing inside 94 mm |
|---|---|---|---|---|
| A | 9.0 mm (Ga-Al) | 0 deg | 4.9-7.1 / 9.1-13.3 mm | none |
| B | 9.0 mm (Ga-Al) | 14.9 deg | 4.0-4.7 / 8.2-9.6 mm | the N source's own open shutter clips 0.2 % of its beam |
| C, D | 20.6 mm | 6.4 / 10.5 deg | 4.0-7.8 / 8.2-16.0 mm (C) | none |
| C-Ga54 | 13.2 mm (N-Ga) | 6.4 deg | as C | none |
| R0 | 9.0 mm | 7.1 deg | 4.4-5.6 / 8.6-11.0 mm | none |

What this establishes, with the assumed dimensions:
- **Every layout fits**, at a 5 mm margin. Eleven sources on one 46 deg cone (A, B, R0) leave about 9 mm between a Ga and an Al cell. That is tight enough that the real cell and shutter drawings decide it. Moving the nitrogen source to a 65 deg port frees the cone (21 mm). The steep port's flange sits 573 mm out and 304 mm below the wafer plane, which the chamber drawing must accommodate.
- **The off-centre aim must be built into the port.** B needs its axis 14.9 deg off the line to the wafer centre, C 6.4 deg and D 10.5 deg. A tilting adapter, assumed to give +/-2 deg, can only trim. So the port axis has to be machined to the aim, with the adapter used for alignment.
- **How the source pivots matters as much as the tolerance.** A tilt about the mounting flange also moves the plate sideways. That doubles the aim shift per degree: 8-16 mm per 0.8 deg at C's port, against 4-8 mm about the plate. The earlier tolerance study (`nitrogen_aim_tolerance.py`) assumed the plate-centre pivot.
- **The holder lip does not shadow the usable area** at 2 mm height: the shadow band is h tan(angle), 4.3 mm at 65 deg, so it ends at 94.7 mm with the 99 mm opening. A 3 mm lip at 65 deg reaches 92.6 mm, inside the mask (section 4).
- **Not checked:** the cryoshroud, RHEED and pyrometer lines of sight, the main shutter, real cell lengths and the manipulator. These need the chamber drawing.

## 4. Comparison under combined uncertainty

`scripts/layout_comparison.py` chains the Ga DSMC records (centre-flux-held where available), the free-molecular nitrogen plate, the heater model under its limit and the growth model, on the 94 mm mask.

**Protocol.**
- In every state the nitrogen output is set so that the wafer-mean net growth rate is 1 um/h (equal growth rate). The output this needs is reported, and so is the rate that a fixed output, calibrated in the nominal state, would give instead.
- The centre Ga/N ratio is set to the middle of the nominal state's Ga-rich window under the same droplet law and pressure, then held (centre-flux hold).
- The window margin is the smallest distance, over the mask, to N-rich growth or to droplets, as a fraction of the local N flux. A negative margin means part of the wafer leaves the window.

**Uncertainty grid.** All combinations are evaluated, 18 522 states per layout and condition (fewer for the 54 deg Ga port). This is a grid, not a probability distribution.
- Pointing: 0.8 and 1.6 deg in 12 directions, about either pivot (49 maps).
- Ga: fill 40 / 70 / 120 mm and diameter 5.68 / 8 A.
- Heater: the nominal optimum held at its zone ratios, with the wafer mean held by one reading. Perturbations: emissivity 0.63 / 0.77, contact 50 / 1000 W m^-2 K^-1, and +/-2 % in the worst zone.
- Holder lip: 1 / 2 / 3 mm.
- Droplet law: three literature scenarios.

**Results at 2 sccm / 2 m^3/s (1.9e-3 Pa), 1473 K element limit.** Thickness half-range/mean on r <= 94 mm. The 0.8 deg column covers all other uncertainties too. The last column is the share of +/-0.8 deg states that stay in the Ga-rich window.

| Layout | 740 C nominal | 740 C, +/-0.8 deg worst | 740 C, +/-1.6 deg worst | N output (1e18 /s) | Rate at fixed output (nm/min, target 16.7) | 700 C nominal | 700 C, +/-0.8 deg worst | 700 C in window |
|---|---|---|---|---|---|---|---|---|
| A | 11.3 % | 12.6 % | 12.6 % | 3.7 | 16.4-16.8 | 11.1 % | 11.8 % | 33 % |
| B | 0.83 % | 2.1 % | 3.0 % | 4.2 (3.9-4.7) | 15.0-18.2 | 0.67 % | 1.7 % | 84 % |
| C | 0.35 % | 3.1 % | 4.6 % | 5.8 (5.4-6.4) | 15.1-17.9 | 0.20 % | 2.6 % | 85 % |
| C-Ga54 | 0.35 % | 3.1 % | 4.6 % | 5.8 | 15.1-17.9 | 0.20 % | 2.6 % | 96 % |
| R0 | 0.34 % | 1.05 % | 1.30 % | 7.4 | 16.1-17.2 | 0.19 % | 1.1 % | 89 % |
| D | 0.89 % | 3.3 % | 5.9 % | 5.3 (4.6-6.3) | 13.9-19.3 | 0.73 % | 2.8 % | 77 % |

**Which factor drives each candidate.** Worst thickness at 740 C when only one factor varies (nominal 0.83 / 0.35 %):

| Factor | B | C | D |
|---|---|---|---|
| Pointing +/-0.8 deg about the plate | 1.20 % | 0.87 % | 1.78 % |
| Pointing +/-0.8 deg about the flange | 1.64 % | 1.47 % | 2.64 % |
| Pointing +/-1.6 deg about the flange | 2.38 % | 2.93 % | 4.22 % |
| Holder lip 1-3 mm | 0.83 % | 1.32 % | 1.38 % |
| Heater perturbations | 1.29 % | 0.79 % | 1.38 % |
| Ga fill and diameter, droplet law | no change | no change | no change |

No single factor takes B or C past about 1.6 % at +/-0.8 deg. The combinations reach 2-3 %, because pointing, heater and lip errors add on the same wafer edge. The separate radial and sideways checks of the earlier tolerance study understated this.

**Ranking survival** (matched states: same tilt, Ga state, heater category, lip and droplet law, over the 70 and 120 mm fills that every layout admits):
- Every off-centre layout beats A in every state up to 7.4e-3 Pa (C still in 93-96 % at 3.7e-2 Pa).
- R0 is the best layout in 82-91 % of states.
- B against C: B is thinner in 45-57 % of states, across both temperatures, all three heater limits and pressures up to 7.4e-3 Pa (49 % at 740 C, 1473 K, 1.9e-3 Pa). At 700 C, counting only states that also stay in the window, B wins 45 % and C 32 % (1.9e-3 Pa). At 3.7e-2 Pa B wins 91-100 %.
- B beats D in 83-87 % of states; C beats D in 77-99 %.
- So the order A < {B, C} < R0 and B, C > D holds over every condition up to 7.4e-3 Pa; the order between B and C does not.

**Pressure** (740 C, 1473 K limit, nominal / +/-0.8 deg worst):

| Pressure | B | C | R0 | N output, B |
|---|---|---|---|---|
| 0 (exact regression) | 0.70 / 2.0 % | 0.22 / 3.3 % | 0.27 / 0.98 % | 4.0e18 |
| 4.6e-4 Pa | 0.73 / 2.0 % | 0.25 / 3.2 % | 0.29 / 1.0 % | 4.1e18 |
| 1.9e-3 Pa | 0.83 / 2.1 % | 0.35 / 3.1 % | 0.34 / 1.05 % | 4.2e18 |
| 7.4e-3 Pa | 1.25 / 2.6 % | 0.98 / 2.8 % | 0.57 / 1.3 % | 5.1e18 |
| 3.7e-2 Pa | 4.0 / 5.6 % | 5.6 / 7.5 % | 2.3 / 3.2 % | 13.2e18 |

This is direct-beam attenuation only: scattered atoms are removed, not redeposited. At 7.4e-3 Pa, C's nominal map worsens while its worst case improves. This shows that the best aim moves with pressure.

## 5. Failure conditions

Each layout fails, in the model, under these conditions. The measurement listed would show whether the condition holds on the real machine.

| Condition | Effect | Layouts affected | Measurement that decides it |
|---|---|---|---|
| Nitrogen aimed at the wafer centre with any finite-hole plate | 11-13 % thickness; window lost at 700 C | A | N-limited thickness map of the real plate |
| Real plate beams more than L/r 2.9 (thicker plate, smaller holes) | worst +/-0.8 deg rises from 2-3 % to 3.3 % (L/r 5.8) and about 8-9 % (L/r 11.7-19.7, earlier study) | all | vendor plate drawing; N-limited thickness map |
| Pointing worse than +/-0.8 deg, or tilts about the mounting flange | C passes B above about +/-0.8 deg about the flange; worst case 3-4.6 % at +/-1.6 deg | B, C, D | repeatability of the aim with the actual mount, measured as an aim-point shift |
| Holder lip 3 mm high at a 65 deg port | shadow reaches 92.6 mm; C nominal 0.35 to 1.3 % | C, D | holder drawing (lip height, opening) |
| Active-N output below about 4.2e18 atoms/s (B) or 5.8e18 atoms/s (C) at the plate | 1 um/h not reachable; the rate scales down with the output | all, C and R0 first | Ga-rich growth rate at the wafer centre versus power and flow (commissioning source matrix) |
| Growth at 700 C (source-lab scale) with the 46 deg Ga port | 15-23 % of the +/-0.8 deg states leave the Ga-rich window | B, C, D | droplet onset and N-rich boundary (RHEED) on the machine's temperature scale |
| Element limit lower than the designed-density optimum needs (1652 K) | wafer range 1.7 to 3.0 K (1473 K) or 3.9 K (1373 K); thickness +0.1-0.15 point | designed-density layouts | vendor element rating and the selected unit's lifetime in active N |
| Wafer emissivity 10 % low with no element headroom | needs about 1495 K at the element to hold the mean at a 1473 K limit | designed-density layouts | heater power at the operating point; wafer temperature at more than one radius |
| Growth pressure at or above about 7e-3 Pa | +0.2-0.9 point nominal; aims must be re-optimized | all | growth pressure and effective N2 pumping speed |
| Growth pressure about 4e-2 Pa | all layouts at or above 2.2 %; three times the N output | all | as above |
| Eleven sources on one 46 deg cone with larger bodies than assumed | 9 mm gap closes | A, B, R0 | cell, shutter and port drawings |

## 6. What this does not establish

- The nitrogen plate is free-molecular, with straight holes and uniform output. Hole-wall recombination, tilted holes and the ion fraction are not modelled, and nothing is measured.
- Attenuation and lip shadow enter as ratio profiles at the nominal pose. Scattered atoms are not redeposited. Pointing errors of the Ga cell are not included.
- The heater is the reduced axisymmetric model. Its wafer range is optimized over the whole wafer, while thickness is evaluated on 94 mm.
- The growth model is steady state, with literature constants on the source labs' temperature scales.
- The uncertainty grid spans assumed brackets. Its extremes are not confidence limits.
- An improvement is demonstrated only by measured wafers under the [improvement protocol](DATA_AND_VALIDATION_PLAN.md#demonstrating-wafer-uniformity-improvement).

## 7. Measurements to plan with the hardware team

Calibration and validation are kept separate. Commissioning data that set model parameters are not reused to test them.

**Calibration (fits model inputs):**
1. Wafer temperature maps at two or more heater settings, with per-zone power and element temperature. These set the heater properties: emissivity, contact and edge support.
2. Ga-limited (N-rich) thickness maps at two or more fills. These set the Ga collision size and the fill drift.
3. Growth pressure and effective N2 speed at two or more flows, and beam flux with the plasma gas on and off. These set the attenuation.
4. Ga-rich growth rate at the wafer centre versus source power and flow. This sets the absolute active-N output and checks the 4-6e18 atoms/s requirement.
5. The aim point and its repeatability after remounting, measured on the mount actually used. This sets the pointing scatter and the pivot.

**Independent validation (not used in any fit):**
1. N-limited (Ga-rich) thickness maps with the chosen plate at its design aim, and at one deliberately offset aim (for example +/-1 deg). This tests the nitrogen map and the pointing sensitivity predicted here.
2. Repeated reference runs, at least three, at the design point. This is the run-to-run scatter that any predicted improvement must exceed.
3. One growth temperature not used in the heater calibration. This tests the decomposition and window predictions.
