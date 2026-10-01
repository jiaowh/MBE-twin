# Source layouts at physically achievable operating points

Status: 2026-10-02 (third revision, after the [project audit](PROJECT_AUDIT_2026-10-01.md) and its [follow-up](PROJECT_AUDIT_FOLLOWUP_2026-10-01.md)), `representative_chamber`. These are model comparisons on a typical 200 mm RIBER/Veeco-class geometry, not predictions for the proposed machine. No nitrogen map, heater result or growth model here is validated against a measurement.

**The question:** under what physically achievable conditions does a layout meet the project's requirements?

**The short answer:** no layout can be called a pass, because neither a uniformity target nor a minimum growth rate is agreed (section 8). The model can, however, say which conditions each layout needs, and where its results are inside the model's validity. Two conditions dominate:
- **Nitrogen supply sets the reachable growth rate.** That rate depends on a source conversion fraction nobody has published. The literature implies it lies between 6 and 57 % at high flow.
- **The aperture plate must stay free-molecular at the flow that rate needs.** With the published-type plate, it stops being free-molecular above about 6 sccm.

Records (all in `data/runs/studies/`):
- [layout_comparison_bc.json](../data/runs/studies/layout_comparison_bc.json): uncertainty grid with a per-state nitrogen balance.
- [nitrogen_rate_limits.json](../data/runs/studies/nitrogen_rate_limits.json): minimum conversion fractions and the highest reachable rates.
- [nitrogen_output_evidence.json](../data/runs/studies/nitrogen_output_evidence.json): conversion fractions inferred from the literature.
- [nitrogen_aim_pressure.json](../data/runs/studies/nitrogen_aim_pressure.json) and [nitrogen_aim_bigplate.json](../data/runs/studies/nitrogen_aim_bigplate.json): aims re-optimized at the operating pressure.
- [heater_robustness.json](../data/runs/studies/heater_robustness.json): combined heater errors and Ga control.
- [layout_feasibility_bc.json](../data/runs/studies/layout_feasibility_bc.json): certified clearances.
- [layout_resolution_check.json](../data/runs/studies/layout_resolution_check.json): radial resolution.
- `results/sparta_hole/manifest.json`: hole-scale DSMC (section 6).

Inputs are in the [design envelope](../data/design/design_envelope.json); commands are in [REPRODUCE.md](REPRODUCE.md); hardware requests are in [HARDWARE_REQUESTS.md](HARDWARE_REQUESTS.md).

## 1. Summary

**Layouts compared.** All use the same Ga cells (46 deg cone), 350 mm throw, designed-density heater (1 mm holder overlap) and 1200 C element limit.

| Layout | Nitrogen port | Aim | Plate |
|---|---|---|---|
| B | 46 deg (cell cone) | +105 mm (vacuum optimum) | R30 hole set: 2000 x 0.343 mm in 0.5 mm, L/r 2.92, 20 mm active radius |
| C | 65 deg | +75 mm (vacuum optimum) | as B |
| **B-p** | 46 deg | **+97.5 mm** (optimum at the 1 um/h pressure) | as B |
| C-p | 65 deg | +67.5 mm (optimum at the 1 um/h pressure) | as B |
| **B-L** | 46 deg | **+90 mm** (optimum at its operating pressure) | **8000 x 0.5 mm in 0.5 mm, L/r 2.0, 30 mm active radius** (designed here, not a published plate) |

**What each layout needs to reach a rate inside the model's validity** (740 C):

| | B-p | B-L |
|---|---|---|
| Plate holes free-molecular (Kn >= 10) up to | 5.9 sccm | 41.6 sccm |
| Smallest conversion eta for 1 um/h, 2 m^3/s, within that limit | 0.88 | 0.40 (35 sccm feed) |
| Smallest eta for 1 um/h, 4 m^3/s, within that limit | 0.80 | 0.22 |
| Rate at the literature range eta 0.06-0.57, 4 m^3/s, 35 sccm feed | 0.04-0.7 um/h (plate limit) | 0.23-2.5 um/h |

- **Conversion is the deciding unknown.** Published N-limited growth rates from one group's Riber 32 with a Veeco UNI-Bulb (R26, R30, R13), back-calculated with this repository's plate model over the bracketed, unpublished geometry, give eta = 0.06-0.57 at 15-34 sccm, and at most 0.34 at 34 sccm (section 3). That range is too wide to decide the design. The source's output versus flow is the most valuable single input (hardware request 1).
- **With the published-type plate, 1 um/h on 200 mm is reachable within the strict validity criterion (hole Kn >= 10) only if eta >= 0.8-0.9.** That lies above the literature range. Hole-scale DSMC (section 6) shows that B-family maps do not change down to Kn 0.3. With Kn >= 3 as the criterion, B-p reaches 1 um/h at eta = 0.3 with 4 m^3/s and 35 sccm: about 20 sccm, 0.73 % nominal, 2.11 % worst within +/-0.8 deg.
- **A large, high-conductance plate (B-L) is the only layout here that reaches 1 um/h inside the model's validity at a conversion inside the literature range.** It needs eta >= 0.22 with 4 m^3/s effective pumping and a 35 sccm feed (R26 ran a UNI-Bulb at 34 sccm with cryo pumping that implies at least about 4 m^3/s). Whether such a plate keeps the discharge lit at low flow is unknown; it is a vendor question.

**Uniformity where the model is valid** (thickness half-range/mean on r <= 94 mm; the worst case is over every combination of the other uncertainties, with pointing within +/-0.8 deg; only states whose own feed keeps the plate free-molecular and reaches the rate count):

| 740 C, eta = 1, 2 m^3/s, 10 sccm | B | **B-p** | C-p | **B-L** |
|---|---|---|---|---|
| 1 um/h: nominal / worst (+/-0.8 deg) / worst (+/-1.6 deg) | 1.06 / 2.40 / 3.28 % | **0.43 / 1.75 / 2.96 %** | outside validity (Kn 7.4-7.8) | **0.64 / 1.74 / 2.71 %** |
| 0.5 um/h | 1.07 / 2.89 / 3.74 % | 0.59 / 2.24 / 3.52 % | 0.40 / 3.74 / 5.27 % | 0.79 / 2.28 / 3.25 % |
| 0.25 um/h | 1.39 / 4.22 / 5.06 % | 0.92 / 3.53 / 4.48 % | 0.72 / 4.71 / 6.30 % | 0.93 / 3.06 / 4.08 % |
| B-L at eta = 0.3, 4 m^3/s, 35 sccm, 1 um/h | | | | 0.44 / 1.40 / 2.38 % |

- **Re-aiming for the growth pressure is the largest single improvement.** At 1 um/h, B-p beats B in 78 % of matched states within +/-0.8 deg (72 % over the full +/-1.6 deg ensemble). Its worst case falls from 2.40 to 1.75 %. B and B-p use the same port and mount; only the aim differs by 7.5 mm.
- **B-p versus B-L** (eta = 1, 1 um/h): B-p is thinner in 61 % of matched states within +/-0.8 deg and 52 % over the full ensemble. The two are close; B-L wins on validity and supply, B-p on the plate being a published design.
- **The C family has no valid 1 um/h operating point** with this plate at any scenario: its feed, 7.2-8.2 sccm at eta = 1, already exceeds the plate limit. At 0.5 um/h, where both are valid, B-p is thinner than C-p in 55 % of matched states within +/-0.8 deg (67 % over the full ensemble), and C-p's worst case is larger (3.74 % against 2.24 %).
- **Shares within a threshold** (all +/-0.8 deg states that are valid, in the growth window and within the threshold, 740 C, 1 um/h, eta = 1, 2 m^3/s):

  | Layout | within 1 % | within 2 % | within 3 % |
  |---|---|---|---|
  | B | 34 % | 85 % | 87 % |
  | B-p | 64 % | 87 % | 87 % |
  | B-L | 72 % | 85 % | 85 % |

  The 85-90 % ceiling comes from the Ga protocol (next point), not from thickness.
- **Ga control decides the growth window.** With the Ga cell held at fixed output (this grid's protocol), two cases leave the window:
  - the wafer state of higher emissivity, which runs about 14 K cold at the element limit;
  - at 700 C, the per-state change in nitrogen (only 36-40 % of +/-0.8 deg states stay in at 1 um/h).

  A Ga correction driven by one centre pyrometer (+/-2 K) keeps 91-100 % of combined heater-error states in the window at 740 C and 83-85 % at 700 C (scripts/heater_robustness.py, nominal pointing). At B-L's operating pressure (1e-2 Pa), a fixed Ga output also leaves the window when the Ga collision diameter differs from the calibrated one, because Ga attenuation then differs. So Ga should be calibrated at growth pressure, not in vacuum.
- **Mechanical:** with certified lower bounds on every modelled clearance, B, B-p and B-L clear the 5 mm margin at 6.3 mm (Ga-Al, 8.9 mm sampled), and C, C-p at 10.9 mm (20.6 mm sampled). These are bounds for the modelled solids with assumed dimensions, not a sign-off.

**Recommendation.** Carry **B-p as the provisional working layout**: B's port and mount, aimed +97.5 mm. B-p is the best layout with a published plate, and its aim can be trimmed after commissioning. Specify the plate as a decision in its own right: the large plate of B-L is what makes 1 um/h reachable at realistic conversion. Drop C and C-p as alternatives unless the plate changes: with this plate they have no valid 1 um/h point. A layout cannot be qualified until:
1. the uniformity target and the minimum rate are agreed (section 8);
2. the source's output versus flow, and the plate options the vendor can supply, are known (hardware requests 1-2);
3. the effective pumping speed is known (request 3);
4. Ga is calibrated at growth conditions, with a temperature reading that drives the Ga flux.

## 2. Design envelope

| Input | Value used | Status |
|---|---|---|
| Uniformity target, minimum rate | none; shares within 1 / 2 / 3 / 5 % and rates 1 / 0.5 / 0.25 um/h reported | missing |
| Active-N fraction of feed atoms eta | scenarios 1 (bound) / 0.3 / 0.1; thresholds solved exactly; literature inference 0.06-0.57 | missing |
| Feed limit | 10 sccm (H02) and 35 sccm (R26 ran 34 sccm) | missing |
| Effective N2 pumping speed | 0.5 / 2 / 4 m^3/s (4 implied by R26) | missing |
| Plates | as in the table of section 1 | R30 set assumed in 0.5 mm; the large plate designed here |
| Free-molecular criterion | smallest hole Kn >= 10 over 300 / 600 K and N2 diameter x/ 1.3 | method of nitrogen_plate_scenarios.py |
| Growth temperature | 700 and 740 C (source labs' scales) | missing |
| Heater element limit | 1473 K (1200 C as the element rating); 1373 K in heater_robustness.py | rating known, its object missing |
| Mask | r <= 94 mm | assumed |

## 3. Nitrogen supply

**Atom budget.** 1 sccm of N2 carries 8.956e17 N atoms/s. 1 um/h on the 94 mm mask needs 4.5-6.9e18 active N atoms/s leaving the plate at the pressures it creates (B-p 4.5e18, B-L 6.1e18 at eta = 0.3 and 4 m^3/s, C-p 6.8e18).

**Coupled operating point** (scripts/layout_comparison.py `operating_point`, scripts/nitrogen_rate_limits.py):
- The feed gives the output, q = eta x 2 x feed x 4.478e17 /s.
- The feed also gives the pressure, p = feed / S_eff, which attenuates the direct N and Ga beams. Attenuation is interpolated from tables up to 0.15 Pa.
- The rate rises with feed until attenuation grows faster than the feed. At 0.5 m^3/s it peaks near 8.4 sccm at 0.62-0.69 um/h for every layout, so 0.5 m^3/s cannot give 1 um/h at any eta.

**What the literature implies for eta** (scripts/nitrogen_output_evidence.py, evidence file [nitrogen_output_evidence.json](../data/parameters/nitrogen_output_evidence.json)):

| Point | Flow, power | N-limited rate | Inferred eta (admissible geometries) |
|---|---|---|---|
| R26: 4000 x 0.203 mm plate | 15 sccm, 500 W | 6.1 um/h GaN | 0.10-0.56 |
| R26 | 20 sccm, 600 W | 8.2 um/h | 0.10-0.57 |
| R26 | 34 sccm, 500 W | 8.4 um/h | 0.06-0.34 |
| R13: original 712-hole plate | 1.3 sccm | about 1.3 um/h | 0.25-0.98 |
| R30: 2000 x 0.343 mm, InN | 2.5 / 7.5 sccm, 350 W | 2.0 / 4.6 um/h | 0.17-0.75 / 0.13-0.57 |
| R12: Hakuto HDRS, plate unknown | 3 sccm, 300 W | 0.72 um/h | 0.09-0.95 |

- The geometry (throw 0.15-0.27 m, source angle 20-40 deg, plate thickness 0.5-2 mm) is not published. It is bracketed, and a geometry is admitted only if every point from the same chamber gives eta <= 1 (345 of 405 admitted).
- These are inferences under the plate model, not measurements.
- Two direct source measurements bound the absolute scale: Voulot et al. (R18, abstract): at most 0.85e18 atoms/s, with dissociation up to 0.4; and a 2024 source study: 18 % at 400 W, falling with flow.
- Conversion falls with flow: 34 sccm at 500 W gave only 2 % more rate than 20 sccm at 600 W.

## 4. Re-aiming at the operating pressure

The vacuum optima of B and C are not optimal at the pressure their own feed creates (scripts/nitrogen_aim_pressure.py, 6 port angles x 15 offsets).

| At the 1 um/h pressure (eta = 1, 2 m^3/s) | Best aim | Nominal | Current aim |
|---|---|---|---|
| 46 deg (B family) | +97.5 mm | 0.42 % | +105 mm: 1.06 % |
| 65 deg (C family) | +67.5 mm | 0.42 % | +75 mm: 0.94 % |
| 60 deg | +75 mm | 0.35 % | - |

- The optimum moves inward as pressure rises, because attenuation removes more of the long paths to the far edge.
- For the large plate (L/r 2.0, 30 mm), the best aim at its operating pressure (eta = 0.3, 4 m^3/s, 1 um/h, 1.1e-2 Pa) is +90 mm on the 46 deg cone (0.44 %). The 65 deg family's best lies at the scan edge (+45 mm, 2.2 %) and is unresolved.
- Monte Carlo scatter at single aims is about 0.3-0.5 points; the same event sample is used across aims.

## 5. Comparison under combined uncertainty

**Protocol** (scripts/layout_comparison.py):
- **Nitrogen:**
  - In every state the output is re-set for the operating rate, at fixed eta. Each state therefore has its own feed, pressure and attenuation. They are solved together: the lowest feed whose rate reaches the target, on a feed grid refined by bisection.
  - A state that cannot reach the target runs at the feed that maximizes its rate (supply-limited).
  - A state is **valid** if it reaches the rate with its plate free-molecular at its own feed. Only valid states enter worst cases and rankings.
- **Ga:** the cell output is set once, in the nominal state, to the middle of the Ga-rich window, and then held. Arrival in each state follows that state's map shapes and its own attenuation.
- **Heater:** zone ratios optimized under the element limit and held. The mean is held by one reading; a state needing more than the limit is capped and grown at the temperature it reaches.

**Grid** (all combinations; a grid, not a probability distribution):
- **Pointing:** 0.8 and 1.6 deg in 12 directions, about the plate centre or the mounting flange (49 maps).
- **Ga:** fill 40 / 70 / 120 mm and collision diameter 5.68 / 8 A.
- **Heater:** seven categories, not combined. Combined heater errors are evaluated separately below.
- **Lip:** 1 / 2 / 3 mm.
- **Droplet law:** three literature scenarios.

Results are reported for the +/-0.8 deg ensemble and the full +/-1.6 deg ensemble separately.

**Numerical checks.**
- Radial resolution, 39 / 77 / 153 radii: nominal thickness within 0.011 points for every layout. The ratio-profile approximation agrees with direct attenuation to 0.001 points (layout_resolution_check.json).
- Area means use annulus weights.
- Map caches are keyed by inputs and code.

**Combined heater errors** (heater_robustness.py, nominal pointing, 1 um/h):
- States: emissivity 0.63 / 0.70 / 0.77 x contact 50 / 200 / 1000 W m^-2 K^-1 x zone error 0 / +/-2 %.
- About half of the states need the element above 1473 K, up to 1500 K (27 K headroom). Capped, they run up to 18 K cold.
- Thickness rises at most to 1.63 % (B) at 740 C and 1.02 % at 700 C, against the one-error-at-a-time 1.5 %.
- Growth window, 740 C: fixed Ga 75 %; temperature-corrected Ga 100 %; centre pyrometer with +/-2 K bias 91-100 %.
- Growth window, 700 C: 67 % fixed; 78-85 % corrected.

**Mechanical feasibility** (layout_feasibility.py, record layout_feasibility_bc.json):
- Clearances are certified lower bounds: capsule bodies, plus disk flanges and blades whose sampled distances are reduced by the samples' covering radius, refined where near the margin.
- Pairs checked: body/body, flange/flange, flange/body, flange/blade, blade/body over each blade's sweep, and blade/blade with both shutters at every pair of sweep positions.
- B, B-p, B-L: 6.3 mm certified (8.9 mm sampled), Ga1-Al1. C, C-p: 10.9 mm certified (20.6 mm sampled), Ga3-Al3. Holder assembly: 190-208 mm.
- B-L is checked with the same assumed nitrogen source body (CF100, 45 mm radius). Its 30 mm active plate fits inside that body, but a real large-plate source may be larger.
- Off-centre port axis: B / B-p about 15 deg; C / C-p 6.4 / 5.6 deg.
- Aim shift per 0.8 deg: 4-8 mm about the plate, 8-17 mm about the flange.
- Not checked: cryoshroud, RHEED and pyrometer lines of sight, main shutter, real drawings.

## 6. Hole flow beyond the free-molecular range

scripts/sparta_hole.py runs SPARTA (2d axisymmetric DSMC, neutral N2 at 300 K) on one hole of the R30 set in a 0.5 mm plate:
- fed from a wide reservoir at Kn 100, 10, 3, 1 and 0.3;
- giving the transmission and the angular intensity I(theta);
- I(theta) is fitted as the free-molecular table times a smooth ratio;
- the B and C maps are rebuilt from it, with errors from 8 time blocks.

**Validation at Kn 100.**
- Transmission 0.434 against 0.427 free-molecular, after normalizing by the feed face's coverage.
- B's map: -0.04 +/- 0.07 points from free-molecular.
- C's map differs by +0.46 +/- 0.14 points. C's nominal map responds strongly to the beam shape near the axis, and the DSMC feed misses the most grazing inlet directions.

Lower-Kn results are therefore read against the Kn 100 DSMC run, which shares that set-up.

Against the Kn 100 run, with errors from both runs' blocks (record [sparta_hole.json](../data/runs/studies/sparta_hole.json)):

| Hole Kn (reservoir) | Transmission | Beam on axis vs free-molecular | B map change | C map change | B delivered fraction |
|---|---|---|---|---|---|
| 110 (reference) | 0.434 +/- 0.004 | 0.98 +/- 0.03 | - | - | - |
| 11 | 0.433 +/- 0.007 | 0.98 +/- 0.03 | +0.01 +/- 0.09 points | -0.06 +/- 0.17 | 1.00 +/- 0.02 |
| 3.2 | 0.436 +/- 0.003 | 0.99 +/- 0.02 | +0.01 +/- 0.08 | -0.12 +/- 0.18 | 1.01 +/- 0.02 |
| 1.05 | 0.443 +/- 0.003 | 0.95 +/- 0.03 | -0.10 +/- 0.09 | +0.35 +/- 0.28 | 1.00 +/- 0.02 |
| 0.31 | 0.479 +/- 0.004 | 0.79 +/- 0.02 | -0.02 +/- 0.09 | **+2.2 +/- 0.3** | 0.94 +/- 0.02 |

- **B-family maps do not change detectably down to Kn 0.3.** The beam broadens (on-axis intensity -21 % at Kn 0.3), but B's aim spreads the dose over an annulus, and that absorbs it. For the B family, the Kn >= 10 criterion of the layout studies is therefore conservative by a factor of three or more in Kn.
- **C's map degrades sharply in transitional flow** (+2.2 points at Kn 0.3). It depends on the beam shape near the axis.
- **Consequence:** with Kn >= 3 as the criterion, B-p also reaches 1 um/h at eta = 0.3 with 4 m^3/s and a 35 sccm feed. It runs at 18-21 sccm and Kn 2.9-3.1, giving 0.73 % nominal, 2.11 % worst within +/-0.8 deg and 3.09 % within +/-1.6 deg. B-L gives 0.44 / 1.40 / 2.38 % at the same operating point.
- **Limits:**
  - one hole, neutral N2 at 300 K;
  - no interaction between neighbouring holes' plumes, which at high flow adds collisions downstream;
  - no atoms or hot discharge gas;
  - this is evidence for the B family's sensitivity, not a validation of the plate model.


## 7. Failure conditions

| Condition | Effect in the model | Layouts | What settles it |
|---|---|---|---|
| eta below about 0.8 (published-type plate) or 0.22-0.40 (large plate) | 1 um/h not reachable inside the model's validity; the rate scales with eta | B-p; B-L | source output versus flow (request 1) |
| Effective N2 speed about 0.5 m^3/s | rate peaks at 0.62-0.69 um/h near 8.4 sccm | all | pumping (request 3) |
| Feed above the plate's free-molecular limit | maps are extrapolations; single-hole DSMC shows no change for the B family down to Kn 0.3, but +2.2 points for C at Kn 0.3 | B, B-p above 5.9 sccm (strict) or about 20 sccm (Kn 3); C family at any 1 um/h point | plate drawing (request 2); a multi-hole DSMC |
| Large plate that will not stay lit at low flow | B-L limited to high-flow operation | B-L | vendor discharge data (request 2) |
| Ga calibrated in vacuum, growth at 1e-2 Pa | Ga/N shifted by the unknown Ga scattering; B-L keeps 45 % in window at 1 um/h, eta 0.3 | B-L, any high-pressure point | calibrate Ga at growth pressure (RHEED) |
| Element limit with no headroom; Ga not corrected for temperature | up to 18 K cold; 25 % of combined heater states make droplets at 740 C | all | heater rating (request 4); a pyrometer-driven Ga correction |
| Growth at 700 C | 36-40 % of +/-0.8 deg states in window at 1 um/h with fixed Ga | all | growth temperature on the machine's scale |
| Pointing worse than +/-0.8 deg or a flange pivot | worst case 2.7-3.3 % (+/-1.6 deg) at 1 um/h | all | mount repeatability (request 5) |
| Larger cell or shutter bodies than assumed | 6.3 mm certified Ga-Al gap closes | B family | cell and shutter drawings (request 5) |

## 8. Decisions needed from the project

1. **Uniformity target** (half-range/mean or std/mean on the agreed mask). For reference, published MOCVD results report about 1 % (1 sigma) per layer for AlGaN/GaN HEMT stacks on 200 mm Si (single-wafer rotating-disk reactor, J. Mater. Res. stress-engineering study) and 2.1 % (1 sigma) for a 5.3 um LED stack (JJAP 52, 08JB25); these are search-level citations, not yet in the reference manifest. In these results std/mean is about 0.4-0.6 of half-range/mean. The choice decides the layout:
   - a 2 % half-range target is met in 85-87 % of B-p's and B-L's +/-0.8 deg states at 1 um/h;
   - a 1 % target is met in 64 % (B-p) and 72 % (B-L).
2. **Minimum growth rate.** 1 um/h needs the large plate at realistic conversion; 0.25 um/h is reachable with the published-type plate at eta >= 0.2-0.25.
3. **Growth temperature.** 740 C keeps the window with a temperature-corrected Ga flux. 700 C is less sensitive to heater errors in thickness, but its window is narrow.
4. **Plate as a specification.** Whether to ask the vendor for a high-conductance plate like B-L's.

## 9. Measurements to plan with the hardware team

Calibration and validation stay separate.

**Calibration:**
1. Ga-rich growth rate at the wafer centre versus N2 flow and RF power. This sets eta.
2. Growth pressure at two or more flows.
3. Ga flux at growth pressure (RHEED).
4. Temperature maps at two or more heater settings.
5. Ga-limited thickness maps at two fills.
6. The aim point and its repeatability.

**Validation:**
1. N-limited thickness maps at the design aim and at one deliberately offset aim.
2. Three or more repeated reference runs.
3. One growth temperature not used in calibration.

## Appendix: superseded records

- **layout_comparison.json (6aca3b3)** compared six layouts at fixed pressures, with the Ga flux following N and unconstrained heater states. Its map-shape conclusions stand: centre-aimed shallow holes give about 11 %; deep holes are worse.
- **Earlier versions of layout_comparison_bc.json** held the pressure at the nominal operating point for every state, and ranked C's out-of-domain 1 um/h states.
- **layout_feasibility.json** used sampled, not certified, clearances.
