# Source layouts at physically achievable operating points

Status: 2026-10-06 (ninth revision: section 14 regenerates the scattered-atom tables at the frozen aims and averages seeds; eighth revision: section 13 checks the section 12 assumptions; seventh revision: section 12 ranks the worst-case drivers and adds three levers against them; sixth revision: section 11 replaces the Ga steering with a realizable controller and adds a heater power margin; fifth revision: section 10 adds the gas-scattered atoms and the nitrogen plume; sections 1-8 are the direct-beam model and stay as recorded; fourth revision after the [project audit](PROJECT_AUDIT_2026-10-01.md), its [follow-up](PROJECT_AUDIT_FOLLOWUP_2026-10-01.md) and the [2026-10-02 audit](PROJECT_AUDIT_2026-10-02.md)), `representative_chamber`. These are model comparisons on a typical 200 mm RIBER/Veeco-class geometry, not predictions for the proposed machine. No nitrogen map, heater result or growth model here is validated against a measurement.

**The question:** under what physically achievable conditions does a layout meet the project's requirements?

**The short answer:** no layout can be called a pass, because neither a uniformity target nor a minimum growth rate is agreed (section 8). The model can, however, say which conditions each layout needs, and where its results are inside the model's validity. Two conditions dominate:
- **Nitrogen supply sets the reachable growth rate.** That rate depends on a source conversion fraction nobody has published. The literature implies it lies between 6 and 57 % at high flow.
- **The aperture plate must stay free-molecular at the flow that rate needs.** With the published-type plate, it stops being free-molecular above about 6 sccm.

**Update 2026-10-06 (section 14).** The scattered-atom tables were regenerated at B-L's +95 mm aim and averaged over independent seeds; B-p's were averaged too. The factor hardly depends on the aim, but one table's Monte Carlo noise moves the worst case by about +/-0.1 point. With averaged tables, **B-L at +95 mm gives 0.53 +/- 0.04 % at 710 C (0.58 % at 720 C) and B-p 0.57 +/- 0.09 % (0.62 %)** (bootstrap of the averaged tables; table noise only). The layout difference, 0.04 point in B-L's favour, is not resolved: B-L is ahead in 75 % of resamples. The aim scan favours +95 mm (optimum 95-97.5 mm, conditional on transferring the 95 mm factors to the other aims), so the aim can be frozen. B-p's figures assume eta = 1, which no measured source reaches (ref/notes/RESEARCH_GAP_SEARCH_2026-10-06.md): **B-L is now the provisional layout**.

**Update 2026-10-05 (section 13).** A commissioning rehearsal shows the 0.2 deg re-aim is reachable with a mount repeatable to about 0.05 deg and three wafers mapped to 0.1-0.3 %. B-L at +95 mm with its own pointing and attenuation tables gives 0.64 % at 710 C, confirming section 12. The 710 C decomposition extrapolation is a small effect on thickness.

**Update 2026-10-05 (section 12, uniformity first).** N pointing sets most of the worst case, then the heater. Three levers together reduce the worst case at 1 um/h to **0.49 % (B-p) / 0.65 % (B-L) at 710 C**:
1. Re-aim the N source at commissioning to 0.2 deg.
2. Aim B-L at +95 mm.
3. Use multi-spot pyrometry with three heater zone groups.

Section 11's 1.53 / 1.67 % are the single-pyrometer, no-re-aim values.

**Update 2026-10-05 (section 11).** The Ga steering of sections 8 and 10 knew every uncertain state's maps (audit 2026-10-05). With a controller that knows only a frozen calibration and real instruments:
- Every admissible 1 um/h point needs a Ga beam-flux monitor and an in-situ growth-rate monitor. Without the beam-flux monitor, no temperature qualifies.
- Chosen for the best worst-case uniformity (the project's priority, 2026-10-05):
  - **B-p:** 720 C, with the heater zones designed for an element 13 K below its rating (3.7 % power headroom); worst case 1.53 %.
  - **B-L:** 730 C with the current heater; worst case 1.67 %.
- More heater headroom lowers B-L's cold limit to 720 C but widens the spread.
- The joint 95 % rule now applies everywhere. It removes one recorded point (B-L at 1.25 um/h, 740 C).

**Update 2026-10-03 (section 10).** Atoms scattered by the chamber gas are now followed instead of dropped, and the nitrogen plate's own plume is added:
- Most scattered Ga still reaches the wafer, and 13-21 % more N arrives.
- 1 um/h with the large plate needs eta >= 0.18 instead of 0.23 (4 m^3/s, 35 sccm).
- The growth-pressure Ga failure mode largely disappears.
- Worst-case spreads rise by 0.1-0.5 points.
- The aims and the working operating point (1 um/h at 720 C) are unchanged.
- Whether the chamber walls return N atoms is a new deciding unknown, and commissioning has to measure it.

Records (all in `data/runs/studies/`):
- [layout_comparison_bc.json](../data/runs/studies/layout_comparison_bc.json): uncertainty grid with a per-state nitrogen balance.
- [nitrogen_rate_limits.json](../data/runs/studies/nitrogen_rate_limits.json): minimum conversion fractions and the highest reachable rates.
- [nitrogen_output_evidence.json](../data/runs/studies/nitrogen_output_evidence.json): conversion fractions inferred from the literature.
- [nitrogen_aim_pressure.json](../data/runs/studies/nitrogen_aim_pressure.json) and [nitrogen_aim_bigplate.json](../data/runs/studies/nitrogen_aim_bigplate.json): aims re-optimized at the operating pressure.
- [heater_robustness.json](../data/runs/studies/heater_robustness.json): combined heater errors and Ga control.
- [layout_feasibility_bc.json](../data/runs/studies/layout_feasibility_bc.json): certified clearances.
- [layout_resolution_check.json](../data/runs/studies/layout_resolution_check.json): radial resolution.
- [sparta_hole.json](../data/runs/studies/sparta_hole.json), its grid / timestep / reservoir variants and [sparta_hole_convergence.json](../data/runs/studies/sparta_hole_convergence.json): hole-scale DSMC (section 6).
- [layout_comparison_bc_kn3.json](../data/runs/studies/layout_comparison_bc_kn3.json): the comparison with the plate criterion relaxed to Kn >= 3.
- Scattered atoms and the plume (section 10):
  - [scattered_redeposition.json](../data/runs/studies/scattered_redeposition.json), [scattered_tables.json](../data/runs/studies/scattered_tables.json) and scattered_plume_tables_*.json;
  - the comparison with them: layout_comparison_bc_sc.json, _sc_plume.json and _sc_gamma0.1.json;
  - the downstream studies on them: nitrogen_rate_limits_sc*.json, operating_cold_limit_*.json, operating_optimum_sc_plume.json, heater_robustness_sc_plume.json, nitrogen_aim_*_sc_plume.json;
  - [commissioning_rehearsal.json](../data/runs/studies/commissioning_rehearsal.json).
- Seed-averaged tables at the frozen aims (section 14): scattered_tables_B-L_95mm.json, scattered_plume_tables_B-L_95mm.json, scattered_plume_tables_B-p_97.5mm.json; realizable_controller_ms_BL95scatter.json, realizable_controller_ms_Bp97scatter.json, scatter_noise_BL95.json, scatter_noise_Bp.json (with the bootstrap of the averaged tables and the paired layout difference).

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
- **With the published-type plate, 1 um/h on 200 mm is reachable within the strict validity criterion (hole Kn >= 10) only if eta >= 0.8-0.9.** That lies above the literature range. Hole-scale DSMC (section 6) shows that B-p's map does not change detectably down to hole Kn 3, in every grid, timestep and reservoir check; at Kn 0.3 it changes by +0.13 to +0.22 points. With Kn >= 3 as the criterion, B-p reaches 1 um/h at eta = 0.3 with 4 m^3/s and 35 sccm: about 20 sccm, 0.73 % nominal, 2.11 % worst within +/-0.8 deg (1.41 % over the 77 % of states that keep Kn >= 3).
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

  A Ga correction driven by one centre pyrometer (+/-2 K bias) keeps 96-97 % of B-p's states in the window at 740 C and 84-86 % at 700 C (1473 / 1373 K element limits). These states combine heater errors with B-p's whole +/-0.8 deg ensemble, and each has its own feed, pressure and attenuation (scripts/heater_robustness.py). With the Ga output fixed, 54-55 % stay in at 740 C and 27-30 % at 700 C. At B-L's operating pressure (1e-2 Pa), a fixed Ga output also leaves the window when the Ga collision diameter differs from the calibrated one, because Ga attenuation then differs. So Ga should be calibrated at growth pressure, not in vacuum.
- **Mechanical:** with certified lower bounds on every modelled clearance over the continuous shutter motion (every angle of each swing, both shutters moving), B, B-p and B-L clear the 5 mm margin at 6.1 mm (Ga-Al, 8.9 mm at the closest evaluated pose), and C, C-p at 10.7 mm (20.6 mm). These are bounds for the modelled solids with assumed dimensions, not a sign-off.

**Recommendation (revised 2026-10-06).** Carry **B-L as the provisional working layout**: B's port and mount with the large plate, aimed +95 mm. B-L is the only layout that reaches 1 um/h inside the model's validity at a conversion inside the measured range (eta >= 0.22; R41 measured at most 0.4 at a source exit, falling with bulb pressure), and with the uniformity levers it is at least as uniform as B-p (section 14). Its plate is not a published design, so the vendor must confirm it can be built and keeps the discharge lit. Keep **B-p** (the published plate, aimed +97.5 mm) as the alternative only if the source is shown to convert at eta >= 0.8-0.9 at low flow, or if the relaxed hole criterion Kn >= 3 is accepted (section 6). Its section 12-14 figures assume eta = 1. Until 2026-10-06 B-p was the provisional layout, as the best layout with a published plate. Drop C and C-p as alternatives unless the plate changes: with this plate they have no valid 1 um/h point. A layout cannot be qualified until:
1. the operating point of section 8 (1 um/h at 720 C, for the goals as uniform, as fast and as cold as possible) is confirmed against crystal quality;
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
  - A state is **N-feasible** if its feed supplies the N-limited rate with its plate free-molecular at that feed.
  - It is **valid** if it is N-feasible and the rate actually grown reaches the operating rate (relative tolerance 1e-6, declared in the script and tested). With the Ga output held, a state whose N map is re-set upward can run short of Ga somewhere on the wafer. That part is Ga-limited and grows slower, so the wafer-mean rate falls below the target although the N supply reaches it.
  - Only valid states enter worst cases and equal-rate rankings. N-feasible states below the rate are kept in the record, labelled off-target (`fraction_feasible_off_target`, `off_target_rate_nm_min_min`).
  - Off-target states occur only at 700 C. At 1 um/h (eta = 1, 2 m^3/s, +/-0.8 deg) they are 6.0 % of B's states (lowest 0.984 um/h), 4.5 % of B-p's (0.987 um/h) and 2.6 % of B-L's (0.991 um/h); none at 740 C. All of them are outside the growth window, so the shares within a threshold do not change. The 700 C rankings move by up to 3 points (B-p thinner than B at 1 um/h: 68 % of matched valid states within +/-0.8 deg, 70 % before the filter).
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

**Combined heater errors and Ga control** (heater_robustness.py, record heater_robustness.json, 1 um/h at eta = 1, 2 m^3/s, 10 sccm):
- Heater states: emissivity 0.63 / 0.70 / 0.77 x contact 50 / 200 / 1000 W m^-2 K^-1 x zone error 0 / +/-2 % (27).
- Two controllers:
  - mean: one reading holds the wafer mean;
  - centre pyrometer with a bias of -2 / 0 / +2 K: the heater model is re-solved holding that reading, with the element capped at its limit.
- The earlier uniform-shift approximation of the pyrometer case was off by up to 1.9 K at 740 C and 2.5 K at 700 C in element-capped states, and by 0.2 K otherwise.
- Element: with the mean controller up to 1500 K is needed (27 K above the 1473 K limit). With a pyrometer that reads 2 K low, up to 1509 K. About half of the states are capped and run up to 18 K cold.
- The Ga protocols are evaluated for B-p, B and B-L over each layout's +/-0.8 deg pointing ensemble, Ga fills and diameters, and droplet laws (lip 2 mm). Every heater state has its own feed, pressure, and N and Ga attenuation, as in the comparison (4.4-5.0e-3 Pa for B-p). The fixed protocol holds the absolute Ga cell output, so its arrival follows each state's attenuation. The corrected protocol re-sets it from the controller's reading, with the state's own maps.

| B-p, share of states in the growth window | 740 C, 1473 K | 740 C, 1373 K | 700 C, 1473 K | 700 C, 1373 K |
|---|---|---|---|---|
| mean controller, Ga fixed | 68 % | 69 % | 30 % | 33 % |
| mean controller, Ga temperature-corrected | 100 % | 100 % | 86 % | 88 % |
| centre pyrometer +/-2 K, Ga fixed | 55 % | 54 % | 27 % | 30 % |
| centre pyrometer +/-2 K, Ga corrected | 97 % (100 / 100 / 92 % for -2 / 0 / +2 K) | 96 % | 84 % | 86 % |
| ideal correction (true window, a bound) | 100 % | 100 % | 89 % | 91 % |

- B and B-L behave alike: at 740 C, 1473 K, the pyrometer-corrected share is 98 % (B) and 97 % (B-L); at 700 C it is 79 % and 87 %.
- A pyrometer that reads high (+2 K) is the worst case, because the wafer is then colder than the Ga table assumes.
- At 700 C even the ideal correction leaves 9-11 % of B-p's states out: pointing changes the N map shape, which a single Ga flux cannot follow.
- Thickness with the corrected protocol, nominal maps: B-p 0.43-0.98 % at 740 C and 0.37-0.53 % at 700 C over the heater states (B 0.62-1.63 %). Over the whole ensemble: B-p at most 1.88 % at 740 C and 1.45 % at 700 C.

**Mechanical feasibility** (layout_feasibility.py, record layout_feasibility_bc.json):
- Clearances are certified lower bounds: capsule bodies, plus disk flanges and blades whose sampled distances are reduced by the samples' covering radius, refined where near the margin.
- The bound covers the continuous shutter motion, not only sampled angles. Within an angular step every blade point stays within the chord of half the step of where it is at the nearer end (at most 2 x reach x sin(step/4), reach = arm + blade radius). The bound at the step ends minus that distance therefore holds for every angle in between. Steps are halved where the bound is lowest until it is within 0.25 mm of the lowest pose bound (mbe_twin.layout.swept_lower_bound). A test places the minimum between the sampled angles of a 6-step sweep.
- Pairs checked: body/body, flange/flange, flange/body, flange/blade and blade/body over each blade's whole swing, and blade/blade over every combination of the two blades' angles (moving together or one at a time); every solid against the holder assembly.
- B, B-p, B-L: 6.1 mm certified (8.9 mm at the closest evaluated pose), Ga1-Al1. C, C-p: 10.7 mm certified (20.6 mm), Ga3-Al3. Holder assembly: 190-208 mm.
- B-L is checked with the same assumed nitrogen source body (CF100, 45 mm radius). Its 30 mm active plate fits inside that body, but a real large-plate source may be larger.
- Off-centre port axis: B / B-p about 15 deg; C / C-p 6.4 / 5.6 deg.
- Aim shift per 0.8 deg: 4-8 mm about the plate, 8-17 mm about the flange.
- Not checked: cryoshroud, RHEED and pyrometer lines of sight, main shutter, real drawings.

## 6. Hole flow beyond the free-molecular range

scripts/sparta_hole.py runs SPARTA (2d axisymmetric DSMC, neutral N2 at 300 K) on one hole of the R30 set in a 0.5 mm plate:
- fed from a wide reservoir at Kn 100, 10, 3, 1 and 0.3;
- giving the transmission and the angular intensity I(theta);
- I(theta) is fitted as the free-molecular table times a smooth ratio;
- the B, B-p and C maps are rebuilt from it, with errors from 8 time blocks;
- each map is evaluated twice:
  - without attenuation (shape only);
  - at the operating pressure of that hole Kn: the feed that puts the layouts' plate at that Kn (300 K, nominal N2 diameter, the DSMC's definition), pumped at 4 m^3/s. That gives 4.7e-4 / 4.7e-3 / 1.6e-2 / 4.7e-2 / 0.16 Pa at Kn 100 / 10 / 3 / 1 / 0.3. Both intensities of a difference are taken at the same pressure.

**Validation at Kn 100.**
- Transmission 0.434 against 0.427 free-molecular, after normalizing by the feed face's coverage.
- B's map: -0.04 +/- 0.07 points from free-molecular; B-p's: +0.01 +/- 0.01.
- C's map differs by +0.46 +/- 0.14 points with the base cell, and by +0.16 +/- 0.06 with half the cell size. C's nominal map responds strongly to the beam shape near the axis.

Lower-Kn results are therefore read against the Kn 100 DSMC run of the same set-up.

Against the Kn 100 run, base set-up, without attenuation (record [sparta_hole.json](../data/runs/studies/sparta_hole.json)):

| Hole Kn (reservoir) | Transmission | Beam on axis vs free-molecular | B map change | B-p map change | C map change |
|---|---|---|---|---|---|
| 110 (reference) | 0.434 +/- 0.004 | 0.98 +/- 0.03 | - | - | - |
| 11 | 0.433 +/- 0.007 | 0.98 +/- 0.03 | +0.01 +/- 0.09 points | +0.00 +/- 0.01 | -0.06 +/- 0.17 |
| 3.2 | 0.436 +/- 0.003 | 0.99 +/- 0.02 | +0.01 +/- 0.08 | +0.00 +/- 0.01 | -0.12 +/- 0.18 |
| 1.05 | 0.443 +/- 0.003 | 0.95 +/- 0.03 | -0.10 +/- 0.09 | +0.03 +/- 0.01 | +0.35 +/- 0.28 |
| 0.31 | 0.479 +/- 0.004 | 0.79 +/- 0.02 | -0.02 +/- 0.09 | **+0.22 +/- 0.04** | **+2.2 +/- 0.3** |

**Numerical and boundary checks.** Each variant changes one thing and repeats Kn 100, 3 and 0.3. Records: sparta_hole_fine_cell.json, sparta_hole_half_dt.json, sparta_hole_big_reservoir.json and [sparta_hole_convergence.json](../data/runs/studies/sparta_hole_convergence.json).

| Map change against Kn 100, without attenuation | B-p, Kn 3 | B-p, Kn 0.3 | C, Kn 0.3 | Transmission, Kn 3 / 0.3 |
|---|---|---|---|---|
| base (cell 0.04 mm, dt 2e-8 s, reservoir 3 x 0.5 mm) | +0.00 +/- 0.01 | +0.22 +/- 0.04 | +2.2 +/- 0.3 | 0.436 / 0.479 |
| half cell | -0.01 +/- 0.01 | +0.15 +/- 0.04 | +2.0 +/- 0.2 | 0.433 / 0.479 |
| half timestep | +0.01 +/- 0.01 | +0.19 +/- 0.03 | +2.2 +/- 0.3 | 0.437 / 0.474 |
| reservoir 4 mm x 1 mm, same particle weight | +0.02 +/- 0.01 | +0.13 +/- 0.02 | +1.9 +/- 0.3 | 0.424 / 0.455 |

- **Grid and timestep:** every variant-minus-base difference is within 2 standard errors at every Kn.
- **Reservoir, Kn 3:** the map changes agree. The larger reservoir lowers the transmission by 0.011 +/- 0.004 (2.5 %), and its gas near the plate is slightly thinner (Kn 3.45 against 3.22).
- **Reservoir, Kn 0.3:** the larger reservoir changes the result beyond the noise. Transmission is 0.024 +/- 0.006 lower; against the base, B's map change differs by -0.22 +/- 0.10 points and B-p's by -0.09 +/- 0.05. At Kn 0.3 the result therefore depends on how the gas is fed: it is a sensitivity, not a converged number.
- These checks vary one parameter at a time. Agreement within the noise does not bound an error smaller than the noise (about 0.01-0.02 points for B-p at Kn 3).

**At the operating pressure** (both intensities attenuated at the pressure of that Kn):
- Kn 3: B-p changes by +0.01 +/- 0.08 points (-0.05 to +0.01 across the variants).
- Kn 1: -0.23 +/- 0.15 points.
- Kn 0.3 (0.16 Pa, beyond any operating point): -1.9 +/- 0.3 points. The attenuation of the long paths and the broader beam then act together, and the sign of the effect reverses.

**What this means:**
- **B-p's map does not change detectably at Kn 3 and above,** with or without attenuation, in every numerical and boundary variant (within +/-0.02 points without attenuation). It does change at Kn 0.3: +0.13 to +0.22 points, depending on the feed boundary. The relaxed criterion Kn >= 3 is supported for B-p's map shape. Kn 1 and below is not: the change there is small but real, and boundary-sensitive.
- **B's map** does not change detectably down to Kn 0.3 without attenuation in the base set-up, but the larger reservoir gives -0.22 +/- 0.10 points at Kn 0.3. B's result does not stand for B-p, which is evaluated separately here.
- **C's map degrades sharply in transitional flow:** +1.9 to +2.2 points at Kn 0.3 in every variant. It depends on the beam shape near the axis.
- **Consequence:** with Kn >= 3 as the criterion, B-p also reaches 1 um/h at eta = 0.3 with 4 m^3/s and a 35 sccm feed (layout_comparison.py `--kn-valid 3`, record [layout_comparison_bc_kn3.json](../data/runs/studies/layout_comparison_bc_kn3.json)).
  - It runs at 18-21 sccm, giving 0.73 % nominal and 2.11 % worst within +/-0.8 deg (3.09 % within +/-1.6 deg).
  - Only 77 % of the +/-0.8 deg states keep Kn >= 3 at their own feed; over those, the worst case is 1.41 %.
  - B-L gives 0.44 / 1.40 / 2.38 % at the same operating point, all inside Kn >= 10.
  - The comparison's Kn is the conservative minimum over 300 / 600 K gas and the N2 diameter x/ 1.3. At B-p's 19.4 sccm it reads 3.1. In the DSMC's definition (300 K, nominal diameter) the same feed is Kn 5.2, between the Kn 10 and Kn 3 runs.
- **Limits:**
  - one hole, neutral N2 at 300 K;
  - no interaction between neighbouring holes' plumes, which at high flow adds collisions downstream;
  - no atoms or hot discharge gas;
  - the B-L plate's holes (L/r 2, 0.5 mm) are not simulated;
  - this is evidence for the B family's sensitivity, not a validation of the plate model.


## 7. Failure conditions

| Condition | Effect in the model | Layouts | What settles it |
|---|---|---|---|
| eta below about 0.8 (published-type plate) or 0.22-0.40 (large plate) | 1 um/h not reachable inside the model's validity; the rate scales with eta | B-p; B-L | source output versus flow (request 1) |
| Effective N2 speed about 0.5 m^3/s | direct-beam model: rate peaks at 0.62-0.69 um/h near 8.4 sccm. With scattered atoms followed (section 10) the ceiling disappears, but 1 um/h then needs about 0.1 Pa, outside the model's validity | all | pumping (request 3) |
| Feed above the plate's free-molecular limit | maps are extrapolations; single-hole DSMC shows no detectable change for B-p down to Kn 3 (grid, timestep and reservoir checked), +0.13 to +0.22 points at Kn 0.3, and +1.9 to +2.2 points for C at Kn 0.3 | B, B-p above 5.9 sccm (strict) or about 20 sccm (Kn 3); C family at any 1 um/h point | plate drawing (request 2); a whole-plate DSMC if the plume matters (its first-order effect is 0.4-0.6 points for B-p at 19 sccm, none measurable for B-L: section 10) |
| Large plate that will not stay lit at low flow | B-L limited to high-flow operation | B-L | vendor discharge data (request 2) |
| Ga calibrated in vacuum, growth at 1e-2 Pa | Ga/N shifted by the unknown Ga scattering; B-L keeps 45 % in window at 1 um/h, eta 0.3 (direct-only model; with scattered Ga kept, the arrival depends far less on the atom size, so this is likely overstated: section 10) | B-L, any high-pressure point | calibrate Ga at growth pressure (RHEED) |
| Element limit with no headroom; Ga not corrected for temperature | up to 18 K cold; with fixed Ga output 32 % of B-p's combined heater and pointing states leave the window at 740 C (45 % with a centre pyrometer) | all | heater rating (request 4); a pyrometer-driven Ga correction |
| Growth at 700 C | 36-40 % of +/-0.8 deg states in window at 1 um/h with fixed Ga | all | growth temperature on the machine's scale |
| Pointing worse than +/-0.8 deg or a flange pivot | worst case 2.7-3.3 % (+/-1.6 deg) at 1 um/h | all | mount repeatability (request 5) |
| Larger cell or shutter bodies than assumed | 6.1 mm certified Ga-Al gap closes | B family | cell and shutter drawings (request 5) |
| Pyrometer error above about 3 K during growth | at 4 K the operating point moves to 730 C, and B-L at eta = 0.3 has none; from 5 K Ga steering keeps at most 94 % of states in the window at any temperature (section 8) | all | an emissivity-corrected reading checked against anchors (COMMISSIONING_PLAN.md, step 5) |
| Chamber walls returning most N atoms (gamma about 0.1, or lower: literature gives 1e-3 or less on nitrided walls without ions; 2026-10-06) | fitted eta 1.4-1.6 times off if assumed otherwise; map shape 0.15-0.3 points off | all | a measurement of N-atom wall loss or background (COMMISSIONING_PLAN.md) |

## 8. Operating point for the project's goals

The project's goals (2026-10-02): as uniform as possible, the highest growth rate, the lowest growth temperature. scripts/operating_optimum.py scans the operating choices:
- layout B-p or B-L;
- growth temperature 680-780 C;
- rate 0.25-2 um/h.

For each supply scenario it reports the points that no other point beats on all three goals (records [operating_optimum.json](../data/runs/studies/operating_optimum.json) and [operating_cold_limit.json](../data/runs/studies/operating_cold_limit.json)). How each point is evaluated:
- Uniformity is the worst-case thickness half-range/mean over the +/-0.8 deg ensemble, not the nominal value.
- Ga is steered from the temperature reading, and each state has its own feed and pressure.
- A point counts only if at least 95 % of its states are inside the model's validity, reach the rate and stay in the growth window, and the heater reaches the temperature under the element limit.

**The goals conflict less than expected:**
- **Colder is also more uniform.** Above about 740 C the spread grows quickly: B-L at 0.25 um/h gives 3.1 % at 740 C and 10.6 % at 780 C. Decomposition follows the wafer's temperature map, so temperature non-uniformity becomes thickness non-uniformity.
- **Faster is also more uniform,** because decomposition then matters less against growth; B-L's aim was also set for a higher-pressure operating point. B-L at 720 C, eta = 1, 2 m^3/s: 2.4 % at 0.25 um/h, 1.6 % at 1 um/h, 1.3 % at 1.5 um/h.
- **The one real conflict is rate against temperature, through the growth window.** The window's absolute width is set by temperature, so at a higher rate it is a smaller fraction of the flux. A faster rate therefore needs a warmer wafer to keep every state in the window.

**Coldest temperature that keeps the window at each rate** (10 K steps; combined heater errors, Ga steered by a centre pyrometer with +/-2 K bias, 1473 K element limit, worst-case thickness in brackets; scripts/operating_cold_limit.py):

| Rate | B-L, eta 0.3, 4 m^3/s, 35 sccm | B-L, eta 1, 2 m^3/s, 10 sccm | B-p, eta 1, 2 m^3/s, 10 sccm |
|---|---|---|---|
| 0.5 um/h | 710 C (1.93 %) | 710 C (2.05 %) | 710 C (1.91 %) |
| **1 um/h** | **720 C (1.39 %)** | **720 C (1.72 %)** | **720 C (1.60 %)** |
| 1.25 um/h | 740 C (1.60 %) | 720 C (1.55 %) | outside plate validity |
| 1.5 um/h | not reachable | 730 C (1.46 %) | outside plate validity |

- With one heater error at a time, the limits are 10-20 K colder (scripts/operating_optimum.py: 1 um/h at 700 C). The combined-error values above are the ones to use.
- With the mean controller the share in the window reaches 100 % from 730 C. With the pyrometer it plateaus at 96-97 % from 720 C upward: the missing states come from the pyrometer's bias, and a reading 2 K high is the worst case (heater_robustness.py). A better-calibrated pyrometer lowers every limit.
- **The pyrometer's accuracy is the binding requirement** (2026-10-03; with scattered atoms and the plume, section 10; `operating_cold_limit.py --pyrometer-bias`, records operating_cold_limit_sc_plume_bias{2,3,4,5,10}.json):

  | Pyrometer bias | Best share in the window at any temperature | Coldest temperature for 1 um/h (worst case) |
  |---|---|---|
  | +/-2 K | 98-99 % | 720 C (1.53-1.80 %) |
  | +/-3 K | 96-97 % | 720 C for B-L, 730 C for B-p (1.53-1.80 %) |
  | +/-4 K | 95-96 % | 730 C at eta = 1 (1.72-1.92 %); none for B-L at eta = 0.3 |
  | +/-5 K | 94 % | none up to 790 C |
  | +/-10 K | 89 % | none up to 790 C |

  The direct-beam model gives the same thresholds (at most 94 % at +/-5 K, 89 % at +/-10 K). A plain single-wavelength pyrometer on GaN-on-Si can err by more than that as the layer grows (thin-film interference), so the reading must be emissivity-corrected and checked against temperature anchors (COMMISSIONING_PLAN.md, steps 2 and 5).

**Working operating point (adopted 2026-10-02, provisional): 1 um/h at 720 C** (on the source labs' temperature scale), with Ga steered from a centre pyrometer. *Revised 2026-10-05 (section 11): with a realizable controller it holds only with a Ga beam-flux monitor, a growth-rate monitor and a heater with about 14 % power headroom; otherwise 730 C. The figures in this section assume the controller knows every state's maps.* It stands until a crystal-quality minimum temperature or the hardware answers (requests 1-3) change it.
- **Why 720 C:** it is the coldest temperature at which 1 um/h keeps the growth window under combined heater errors, in every scenario and layout that reaches 1 um/h. It is also the coldest temperature inside the range the decomposition law was fitted to (720-805 C).
- **Why 1 um/h:**
  - Going faster costs temperature quickly (1.25 um/h needs 740 C at realistic conversion) and gains little uniformity.
  - Going slower allows only 10 K less and is less uniform (0.5 um/h: 710 C, worst 1.9-2.1 %).
- **Uniformity there:** worst case 1.4-1.7 % half-range/mean within +/-0.8 deg pointing; nominal about 0.4-0.8 %.
- **Layout:**
  - B-L at realistic conversion. It is the only layout that reaches 1 um/h inside the model's validity at eta below about 0.8, and it gives the most uniform result there (1.39 %).
  - B-p if the source turns out to convert at eta >= 0.8-0.9, or if Kn >= 3 is accepted (section 6).
- **This replaces 740 C as the working temperature for these goals.** At 740 C the window is wider than needed, the heater runs closer to its element limit, and the spread is larger: in the same study B-p at 1 um/h gives 1.88 % at 740 C against 1.60 % at 720 C, and B-L at eta = 0.3 gives 1.67 % against 1.39 %.

**Limits of this optimum:**
- Crystal quality, morphology and impurity incorporation are not modelled. In practice they also set a lowest temperature; the growth window is the only cold limit here.
- The temperature scale is that of the source labs whose data the growth model uses. The machine needs its own calibration (section 9).
- Conversion, pumping and the plate are unknown inputs (hardware requests 1-3). The B-L plate is not a published design.
- The 95 % admissibility level is a choice. At 90 %, every limit in the table falls by 10 K (by 20 K for B-L at 1.25 um/h and eta = 0.3).
- Grid of states, not probabilities; representative chamber.

**Still for the project to confirm:**
1. that the growth window, not crystal quality, sets the lowest temperature, or a quality-based minimum (for example from the vendor's or the group's growth experience) if one is known;
2. whether to ask the vendor for a high-conductance plate like B-L's.

## 9. Measurements to plan with the hardware team

The full sequence, with the model input each run fixes, the held-out validation runs and the pairs of unknowns one number cannot separate, is in [COMMISSIONING_PLAN.md](COMMISSIONING_PLAN.md). In short, calibration and validation stay separate.

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

## 10. Scattered atoms and the nitrogen plume (2026-10-03)

Sections 2-8 attenuate the direct Ga and N beams by the chamber's N2 and drop every scattered atom. At the leading operating points that removes 50-70 % of the Ga beam and 25-30 % of the N beam. The atoms are now followed to where they land, and the plate's own gas plume is added. Section 8's operating point is re-checked with both.

**Method** (`src/mbe_twin/scattering.py`, tests in `tests/test_scattering.py`):
- **Test-particle transport.** The beam is a trace gas in fixed gas fields, so each atom is followed on its own (no DSMC). It collides as a hard sphere with Maxwellian partners, isotropically in the centre-of-mass frame. Heavy Ga (70 amu) on N2 (28 amu) is therefore deflected little; N (14 amu) scatters broadly.
- **Gas fields.** The chamber's N2 at 300 K and the operating pressure. Optionally also the free-molecular plume of the nitrogen plate: the feed leaving the active disk with the holes' cos^n. Its density is computed exactly per azimuth, and it is not modified by its own collisions (first order).
- **Chamber.** No drawing exists, so a 0.5 m sphere stands in for the cryoshroud, with an absorbing 0.13 m holder disk in the wafer plane. Ga sticks to the walls. N recombines with probability gamma = 1 per wall hit, or 0.1 as an upper case: without a pump, the returned N then accumulates.
- **Literature check (2026-10-06): 0.1 is not an upper case.** N recombines on stainless steel with gamma 0.07 under ion bombardment (R36), but only about 7e-4 on nitrided iron and 2e-5 on quartz without it (R37). MBE walls see no ions and are nitride- or Ga-coated cryopanels, which no source covers; Ga-coated areas may consume N instead. `scattering.track` now has an optional pump that removes wall-returned atoms (loss per wall hit gamma + (1 - gamma) S / (A <v> / 4); 0.0086 at gamma 1e-3 and 4 m^3/s in this chamber). With that loss, returned atoms deliver about twice the direct beam at low pressure, nearly evenly. **Bracket result** (B-L at +95 mm, 4 m^3/s, two seeds of 4e6 atoms; records [scattered_plume_tables_B-L_95mm_lowloss.json](../data/runs/studies/scattered_plume_tables_B-L_95mm_lowloss.json) and [realizable_controller_ms_BL95lowloss.json](../data/runs/studies/realizable_controller_ms_BL95lowloss.json)):

| Pressure | 2.5e-4 Pa | 2e-3 Pa | 1e-2 Pa | 2e-2 Pa |
|---|---|---|---|---|
| N arrival factor, gamma 1 (no pump; scattered_plume_tables_B-L_95mm.json) | 1.00 | 1.03 | 1.15 | 1.36 |
| N arrival factor, gamma 1e-3 + pump | 2.88 | 3.02 | 3.83 | 5.16 |
| Shape (half-range of the factor) | 0.3-0.6 pt | 0.2 pt | 0.1-0.3 pt | 0.3-0.4 pt |

- **Uniformity does not depend on it.** With the section 13 controller settings, B-L's worst case is 0.53 % at 710 C (96.9 % of states) and 0.58 % at 720 C, against 0.53 % / 0.58 % with gamma 1. The returned atoms land almost evenly.
- **The nitrogen needed does.** 1 um/h at eta 0.3 needs 5.5-5.8 sccm instead of 18-19 sccm: the same rate at the old feed would need eta of only about 0.09. B-p's conversion requirement would fall by a similar factor, back into the measured range. So the wall loss bears on the layout choice through nitrogen output, not through uniformity.
- Measured N-limited maps that follow the source geometry would argue against such strong returns. The commissioning N-limited map and throttle series (COMMISSIONING_PLAN.md, C6b-C7) decide it.
- **Sources.** The N atoms leave the plate disk (B-p 20 mm, B-L 30 mm) with the holes' on-axis peaking, cos^n with n = 2/W - 1 (3.70 for L/r 2.92, 2.91 for L/r 2). Ga leaves a point on the 46 deg cone, aimed at the centre, cos^2, with cos^1 and cos^4 as a beam-width check.
- **Checks.**
  - In vacuum the arrival matches the analytic map within 0.52 % per bin, absolutely.
  - Direct survival through static gas is exponential.
  - Collisions conserve momentum and energy, and Ga's deflection stays below the kinematic limit.
  - The plume density matches the disk's solid angle on axis and a fine area quadrature off axis within 1 %.

**Where the atoms land** (record [scattered_redeposition.json](../data/runs/studies/scattered_redeposition.json), 12 x 1e6 atoms per case). Arrival relative to vacuum, as the wafer mean over r <= 94 mm, with the half-range/mean of the arrival-to-vacuum profile in brackets (the shape change; about +/-0.2 points):

| | B-p, 19.4 sccm, 8.2e-3 Pa: direct only | B-p: direct + scattered | B-L, 26 sccm, 1.1e-2 Pa: direct only | B-L: direct + scattered |
|---|---|---|---|---|
| Ga, 8 A | 0.40 (0.99) | 0.89 (0.63) | 0.30 (1.92) | 0.87 (0.50) |
| Ga, 6 A | 0.53 (0.80) | 0.92 (0.65) | 0.43 (1.69) | 0.90 (0.85) |
| Ga, 8 A, beam cos^1 / cos^4 | 0.40 / 0.40 | 0.94 / 0.85 | 0.30 / 0.30 | 0.92 / 0.80 |
| N, gamma 1 | 0.77 (0.47) | 0.87 (0.36) | 0.70 (0.99) | 0.85 (0.76) |
| N, gamma 0.1 | 0.77 (0.85) | 1.30 (0.70) | 0.70 (0.91) | 1.37 (0.85) |
| N, gamma 1, plume at 300 K | 0.66 (1.14) | 0.82 (0.97) | 0.61 (0.82) | 0.81 (0.77) |
| N, gamma 1, plume at 600 K | 0.69 (0.93) | 0.85 (0.77) | 0.64 (1.26) | 0.83 (0.79) |

- **Ga is not lost.** 85-94 % of the vacuum amount arrives, against 30-53 % when scattered atoms are dropped, and the 6 and 8 A atom sizes now differ by only 3-4 %.
- **Scattered N adds 13-21 %** with full wall recombination, and more if the walls return atoms. The scattered part lands almost evenly, so it reduces the shape change the pressure causes.
- **The plume.**
  - In front of the plate its density is 9 times the chamber's for B-p (0.076 Pa equivalent) and 4 times for B-L (0.048 Pa).
  - It costs each N atom 0.09-0.14 collisions, less than a static gas of that density would, because the plume gas moves with the beam.
  - It removes a further 3-6 % of the N.
  - For B-p it adds 0.4-0.6 points of shape change (300 K gas) and 0.4 points (600 K). For B-L it changes the shape by nothing measurable: B-L's plate is larger and its plume thinner.

**In the comparison.** `scripts/scattered_tables.py` tabulates, on the comparison's pressure grid and radii, the factor that adds the scattered atoms to the comparison's own direct-attenuated maps. The factor is the Monte Carlo total arrival divided by the deterministic direct arrival of the same surrogate source, attenuated as the comparison attenuates it:
- per layout for N, with gamma = 1 or 0.1, 8e6 atoms per pressure;
- for Ga, both atom sizes, 4e6 atoms per pressure.

The batch means are fitted as a quadratic in r^2 (median reduced chi^2 1.2). The parts ran in parallel and were merged by `scripts/merge_scattered_tables.py`. `scripts/scattered_plume_tables.py` adds the plume per pumping speed (2 and 4 m^3/s, up to 35 sccm, 300 K gas). `layout_comparison.py --scattered gas | gas+plume | gas-gamma0.1` multiplies its attenuation tables by these factors (records layout_comparison_bc_sc*.json; layouts B, B-p and B-L). With the default `--scattered none`, every earlier record reproduces bit for bit.

740 C, 1 um/h, fixed Ga output (the comparison's protocol). Each cell gives nominal / worst within +/-0.8 deg, then the share of states in the growth window:

| Model | B-p, eta 1, 2 m^3/s | B-L, eta 1, 2 m^3/s | B-L, eta 0.3, 4 m^3/s, 35 sccm |
|---|---|---|---|
| Direct beam only (sections 1-8) | 5.07 sccm; 0.43 / 1.75 %; 87 % | 5.76 sccm; 0.64 / 1.74 %; 85 % | 22.7 sccm, 1.1e-2 Pa; 0.44 / 1.40 %; 45 % |
| + scattered atoms | 4.68 sccm; 0.73 / 2.08 %; 90 % | 5.21 sccm; 0.83 / 1.89 %; 90 % | 18.3 sccm, 8.5e-3 Pa; 0.78 / 1.87 %; 90 % |
| + scattered atoms and plume | 4.76 sccm; 0.39 / 1.83 %; 89 % | 5.27 sccm; 0.73 / 1.82 %; 90 % | 19.0 sccm, 8.8e-3 Pa; 0.64 / 1.54 %; 90 % |
| + scattered atoms, walls return N (gamma 0.1) | 3.19 sccm; 0.55 / 1.90 %; 90 % | 3.33 sccm; 0.74 / 1.85 %; 90 % | 11.3 sccm, 5.2e-3 Pa; 0.50 / 1.73 %; 90 % |

**What changes:**
- **Less feed for the same rate, and fewer constraints from pressure.**
  - With scattered atoms and the plume, the smallest conversion for 1 um/h falls from 0.23 to 0.18 for B-L (4 m^3/s, 35 sccm), and from 0.40 to 0.22 at 2 m^3/s (records nitrogen_rate_limits_sc*.json).
  - With walls that return N (gamma = 0.1) it falls to 0.10-0.12.
  - B-p within its strict plate limit barely moves (0.78-0.82, against 0.80-0.88): the plate, not the pressure, limits it.
- **The growth-pressure Ga failure mode largely disappears.** With a fixed Ga output, B-L at eta = 0.3 keeps 90 % of states in the window instead of 45 %, because the arriving Ga no longer depends strongly on the atom size. Calibrating Ga at growth pressure stays the plan, but the twin no longer predicts a large error if it is not.
- **Uniformity is somewhat worse, and model-dependent by a few tenths of a point.** Keeping the scattered atoms undoes part of the pressure shape the aims were tuned against. Worst cases at 740 C rise by 0.1-0.5 points; the plume brings some of it back. The variants differ by 0.2-0.4 points, comparable to the factor tables' statistical scatter.
- **The aims stay.**
  - Re-optimizing at 46 deg with scattered atoms and the plume (the section 4 aim scans re-evaluated; records nitrogen_aim_pressure_sc_plume.json and nitrogen_aim_bigplate_sc_plume.json) leaves B-p's best aim at +97.5 mm (0.38 %).
  - B-L's best moves half a step, from +90 to between +90 and +97.5 mm (0.64 against 0.60 %, inside the 0.3-0.5 point scatter of single-aim maps).
- **The 0.5 m^3/s ceiling was an artefact of dropping scattered atoms.** Direct-only, the rate peaked at 0.62-0.69 um/h near 8 sccm whatever the conversion. With the scattered atoms followed, the rate keeps rising with feed up to 35 sccm (about 2.9 um/h at eta = 1). That regime, near 0.1 Pa, is outside what this model can vouch for:
  - the beams are diffusive there;
  - the plume is collisional, and is not tabulated for 0.5 m^3/s;
  - the discharge's behaviour at that back pressure is unknown.

  So low pumping is no longer excluded by the model, but it is not shown to work either.

**The operating point** (section 8) is unchanged, re-checked with the combined heater errors and a centre pyrometer (records operating_cold_limit_gas.json, operating_cold_limit_sc_plume_bias2.json, operating_cold_limit_gas-gamma0.1.json). **1 um/h at 720 C** remains the coldest admissible point in every layout and scattered-atom variant. Its worst case is 1.53-1.80 % with scattered atoms and the plume (1.39-1.72 % direct only; 1.53-2.06 % across the variants). Faster growth gets cheaper: B-L at eta = 0.3 reaches 1.25 um/h at 720 C (740 C direct only), and 1.5 um/h at 730 C (not reachable direct only).

**What commissioning must separate** (rehearsal record [commissioning_rehearsal.json](../data/runs/studies/commissioning_rehearsal.json), [COMMISSIONING_PLAN.md](COMMISSIONING_PLAN.md) section 6.1; revised after the 2026-10-03 audit):
- **Growth rates at several flows do not test the scattered-atom model by themselves.** The first rehearsal fitted one conversion for all flows and rejected the direct-only model in 90-100 % of draws. If the conversion may change with flow, as the plan's own fit allows, no model is rejected more often than chance. The fitted eta then differs between the models by a factor of 1.5-3.
- **A throttle series separates them.** Grow at the working flow and power with the pumping throttled to a quarter of full speed: the pressure changes while the discharge, and eta, do not. That rejects every wrong model, including the wrong wall recombination, in 100 % of draws, for constant or flow-dependent eta, and recovers eta at the working flow within 0-3 %. A 10 % gauge-factor error moves eta by 1-3 %.
- **Extrapolating eta in flow stays risky.** At a held-out flow beyond the calibrated ones the predicted rate is off by 3-17 % when eta falls with flow, but by about 1 % inside the calibrated range.

**Limits:**
- cos^n surrogate sources, used only as a ratio on the comparison's own maps;
- a spherical chamber, hard spheres, uniform 300 K chamber gas, no pump;
- the plume is first order and at 300 K (600 K gives about two thirds of its effect), not tabulated for 0.5 m^3/s;
- the plume tables first stopped at 32 sccm, so states between 32 and 35 sccm mixed plume and gas-only factors (2026-10-03 audit). They now cover the grid pressure above 35 sccm at both speeds, and the gas+plume records were rerun. Only feed-ceiling results moved: maximum rates at 35 sccm fell by 1-3 %, worst cases there by up to 0.3 points, and B-L at 1.5 um/h is no longer reachable at 790 C. Every value quoted in this section, the conversion limits and the cold limits at 1 um/h are unchanged;
- the Ga factors at 0.07-0.15 Pa fit the quadratic poorly (beyond any reachable operating point);
- the N wall recombination is not sourced.

The record scattered_redeposition.json hashes `src/mbe_twin/scattering.py` at a version with two functions (`direct_flux`, `binned_direct_flux`) that were added while it ran and that it does not call.

## 11. Realizable controller and heater power margin (2026-10-05)

The [2026-10-05 audit](PROJECT_AUDIT_2026-10-05.md) (finding 1) showed that the temperature-corrected Ga protocol of sections 8 and 10 places the Ga in the middle of each uncertain state's own window, computed from that state's N map, Ga shape and pressure. A centre pyrometer does not observe those maps. scripts/realizable_controller.py replaces that protocol by controllers that know only a calibration frozen on the nominal state, plus named observations with errors. Growth is then evaluated with every state's true maps (records [realizable_controller_sc_plume.json](../data/runs/studies/realizable_controller_sc_plume.json) and [realizable_controller_sc_plume_heater1425.json](../data/runs/studies/realizable_controller_sc_plume_heater1425.json); gas + plume arrival; 1 um/h).

**Setup.**
- **Calibration (commissioning, nominal state, operating temperature).** It fixes four things: the feed for the wafer-mean rate, the Ga cell temperature for the window middle, the nominal N and Ga shapes, and the centre-to-mean ratio of the net rate. The droplet onset is measured at the centre, so each droplet law is a truth scenario with its own calibration.
- **Truth states.** 25 N pointings within +/-0.8 deg. Six Ga records (40 / 70 / 120 mm fill x 5.68 / 8 A), each with its own absolute flux versus cell temperature. 27 combined heater errors x pyrometer bias -2 / 0 / +2 K. Three droplet laws. Observation errors at -e / 0 / +e.
- **Validity.** A state counts if:
  - the plate holes stay free-molecular;
  - the feed is within its limit;
  - the wafer-mean rate is within 3 % of the target (the controllers hold the centre rate, not the mean).

  The gate is the joint 95 % fraction (finding 2, now enforced in every study).

**Controllers.** All of them see the pyrometer and the ion gauge.
- **Known maps (bound):** the earlier protocol. It reproduces the audit's 96.19 % (B-p) and 97.31 % (B-L) at 720 C exactly.
- **Frozen:** the calibrated feed and cell temperature, never re-set.
- **Rate monitor:** an in-situ growth-rate monitor at the centre (laser reflectometry, +/-1 %) re-sets the feed to the calibrated centre rate. The Ga target is the window middle from the calibrated shapes at the reading, applied through the calibrated cell model.
- **+ BFM:** additionally, a beam-flux monitor at the wafer centre sets the Ga arrival (+/-2 %).
- **+ fill:** additionally, the Ga shape of the charge's current fill (known from bookkeeping).
- **+ commissioned maps:** additionally, each state's own N and Ga shapes, as N-limited and Ga-limited thickness maps measured at commissioning would give them. They are taken as exact, which is an optimistic limit.

![Share of uncertain states in the growth window by controller and heater design](figures/controllers.png)

**Share of states valid and in the window, and coldest admissible temperature for 1 um/h** (worst-case thickness half-range/mean there):

| Controller | B-p, 720 C | B-L, 720 C | Coldest, current heater | Coldest, 14 % power margin |
|---|---:|---:|---|---|
| Known maps (bound) | 96.2 % | 97.3 % | 720 C (1.53 %) | 710 C (1.50 / 1.66 %) |
| Frozen | 33.1 % | 37.3 % | none up to 790 C | none |
| Rate monitor | 51.3 % | 51.7 % | none | none |
| Rate monitor + BFM | 88.9 % | 90.8 % | **730 C (1.68 / 1.67 %)** | **720 C (1.69 / 1.85 %)** |
| + fill | 89.9 % | 92.0 % | 730 C | 720 C |
| + commissioned maps | 90.3 % | 92.3 % | 730 C | 720 C |

In the last two columns the pairs are B-p / B-L. With the margin heater, rate monitor + BFM gives 97.0 % (B-p) and 95.7 % (B-L) at 720 C.

**What the controller must observe:**
- **A Ga beam-flux measurement is indispensable.** Without it, a deeper or shallower charge moves the Ga out of the window at the frozen cell temperature: with the rate monitor alone, only 19-43 % of the 40 and 120 mm states pass at 720 C. A rate monitor alone never reaches 95 % at any temperature.
- **The rate monitor is needed for the N side.** It re-sets the feed for pointing and pressure changes, to within the centre-to-mean change of the tilted map (mean rate -2.6 to +2.4 % at 720 C).
- **Knowing the fill or the commissioned maps adds only 1-2 points.** The remaining gap to the bound is the run-to-run part:
  - the instrument errors. With zero rate and BFM error, the commissioned-maps controller reaches 97.1 % for B-L at 720 C, against the bound's 97.3 %. Given the same information, the realizable protocol reproduces the earlier study.
  - the heater state: wafer emissivity, contact, zone error and pyrometer bias.
- **Error budget at 720 C, current heater, B-L / B-p.** The BFM error matters most.

  | Rate monitor / BFM error | Rate monitor + BFM | + commissioned maps |
  |---|---|---|
  | 1 % / 2 % | 90.8 / 88.9 % | 92.3 / 90.3 % |
  | 1 % / 0 | 93.4 / 91.9 % | 95.9 / 94.5 % |
  | 0 / 2 % | 91.2 / 89.1 % | 93.0 / 90.9 % |
  | 0.5 % / 1 % | 93.2 / 91.6 % | 95.6 / 94.1 % |
  | 0 / 0 | 93.6 % (B-L) | 97.1 % (B-L) |

**Heater power margin** (scripts/heater_margin.py, record [heater_margin.json](../data/runs/studies/heater_margin.json)). The zone fractions of the comparison are optimized under the 1473 K element limit, so at the operating point the hottest ring is on the limit (integrated twin: 2382 of 2387 W).
- With those fractions, 46 % of the 81 combined heater/pyrometer states are capped, and their reading falls up to 24 K short.
- Optimizing the zones under a 1425 K design limit leaves 14.2 % power headroom, at a cost of 0.3 K more wafer range (2.51 -> 2.82 K at 720 C). No combined state is capped any more.
- That headroom is what moves the realizable cold limit back to 720 C. It also costs uniformity at higher temperatures, because the wider wafer range raises the worst cases above about 730 C.

| Design limit | Headroom | Wafer range, 720 C | Capped combined states | Largest reading shortfall |
|---|---:|---:|---:|---:|
| 1473 K (current) | 0 % | 2.51 K | 46 % | 24 K |
| 1450 K | 6.6 % | 2.66 K | 32 % | 8 K |
| 1460 K | 3.7 % | 2.60 K | 33 % | 15 K |
| **1425 K** | **14.2 %** | **2.82 K** | **0 %** | 0 |
| 1400 K | 22.6 % | 2.98 K | 0 % | 0 |

The integrated twin confirms both effects in time ([INTEGRATED_TWIN.md](INTEGRATED_TWIN.md), section 4). With the BFM step and the rate monitor, the 120 mm charge grows like the calibrated machine (100 % of the wafer in the window, against 38 % with frozen settings). With the 1425 K design, a pyrometer reading 2 K low is no longer clamped.

**Uniformity-first choice of temperature and heater margin** (the project set uniformity as its priority on 2026-10-05). Rate monitor + BFM, 1 um/h. Each entry is the share of states that pass and the worst case (record realizable_controller_sc_plume_heater1460.json and the design-limit probes of 2026-10-05):

| Zone design limit (headroom) | B-p 720 C | B-p 730 C | B-L 720 C | B-L 730 C |
|---|---|---|---|---|
| 1473 K (0 %) | 88.9 % | **96.0 %, 1.68 %** | 90.8 % | **95.8 %, 1.67 %** |
| 1465 K (2.2 %) | 93.2 % | 97.2 %, 1.67 % | 94.0 % | 96.4 %, 1.76 % |
| **1460 K (3.7 %)** | **95.2 %, 1.53 %** | 97.5 %, 1.67 % | 94.99 % | 96.5 %, 1.82 % |
| 1450 K (6.6 %) | 96.8 %, 1.60 % | 97.5 %, 1.81 % | 95.7 %, 1.76 % | 96.4 %, 1.97 % |
| 1425 K (14.2 %) | 97.0 %, 1.69 % | 97.4 %, 1.95 % | 95.7 %, 1.85 % | 96.3 %, 2.11 % |

More headroom widens the wafer's temperature range, and a warmer wafer turns that range into thickness through decomposition. The most uniform admissible point is therefore the coldest temperature with the least headroom that still passes. 1.25 um/h is no better: B-L reaches 1.74 % at 740 C, and B-p is outside plate validity.

**Revised working point (2026-10-05, uniformity first).**
- **B-p:** 1 um/h at **720 C**, with the heater zones designed for an element about 13 K below its 1473 K rating (3.7 % power headroom). Worst case **1.53 %**, the same as the known-maps bound. It passes the 95 % rule narrowly (95.2 %): a 1450 K design gives more margin (96.8 %) at 1.60 %.
- **B-L:** 1 um/h at **730 C** with the current heater (worst 1.67 %). Its 720 C option needs 6.6 % headroom and gives 1.76 %.
- **Both need:**
  - a Ga beam-flux measurement before growth (+/-2 % or better);
  - an in-situ growth-rate monitor that re-sets the N feed (+/-1 % or better).

  Without the BFM there is no admissible 1 um/h point.
- **Why B-p wins:** B-p is the more uniform layout at this point. It needs the high conversion (eta about 1, 2 m^3/s, 10 sccm scenario); at realistic conversion, B-L is the layout that reaches 1 um/h.

The flux-monitor and rate-monitor error magnitudes are priors until the instruments are selected. The commissioned maps are an optimistic limit (exact map calibration). The grid of states is not a probability distribution.

## 12. What sets the worst case, and three levers against it (2026-10-05, uniformity first)

The project's priority is the worst-case thickness spread (2026-10-05). scripts/worst_case_drivers.py ranks the uncertain factors at an operating point by how much each adds to that worst case. It compares the worst case with the factor held at nominal against the worst case with everything free, using the rate monitor + BFM controller. All runs are summarized in [uniformity_levers.json](../data/runs/studies/uniformity_levers.json); commands are in REPRODUCE.md.

**1. Drivers at the section 11 points.**

| Factor | B-p 720 C (1460 K design), worst 1.53 % | B-L 730 C (current heater), worst 1.67 % |
|---|---|---|
| N pointing (+/-0.8 deg) | adds 0.99 pt | adds 0.72 pt |
| Heater error (emissivity, contact, zone) | adds 0.32 pt | adds 0.45 pt |
| Pyrometer bias, Ga state, rate and BFM errors | at most 0.02 pt | at most 0.01 pt |

- **Pointing dominates.** The worst states are tilts about the mounting flange towards or away from the wafer centre (directions 0 and 180 deg). Sideways tilts matter little.
- **Instrument errors and the Ga state decide whether a state stays in the window, not how uneven it grows.** At these points the layer is set by N and temperature.

**2. Lever 1: re-aim the N source after commissioning.**
- **What changes.** The harmful tilts change the radial thickness profile, so an N-limited (Ga-rich) thickness map at commissioning reveals them. The mount is then trimmed.
- **How it is modelled.** The residual tilt is +/-delta (option --pointing-residual). The maps come from linear interpolation between the nominal and 0.8 deg maps; direct maps at 0.2 and 0.4 deg agree to 0.04-0.07 % in shape.
- **What it needs.** A residual of 0.2 deg changes the N-limited profile by up to 0.42 % (B-p) / 0.29 % (B-L). So the commissioning map must resolve about 0.3 %, and the mount must adjust and repeat to about 0.2 deg (about 1 mm at the 0.3 m flange pivot).

| Residual pointing | B-p 720 C | B-L 720 C |
|---|---|---|
| 0.8 deg (no re-aim) | 1.53 % | not admissible (730 C: 1.67 %) |
| 0.4 deg | 1.00 % | 1.24 % |
| **0.2 deg** | **0.75 %** | **1.08 %** |
| 0.1 deg | 0.64 % | 1.00 % |

Heater designs 1450-1460 K; worst case over states valid and in the window (95-97 %).

**3. Lever 2: aim at the operating point.**
- **Method.** scripts/nitrogen_aim_operating.py computes nominal N maps at other aim offsets. The pointing states keep the tilt response of the current aim, and the attenuation tables are reused (stated approximations).
- **B-p.** Its +97.5 mm aim stays best: 92.5 mm gives 1.20 % and 102.5 mm gives 1.25 % (re-aimed to 0.2 deg, 720 C).
- **B-L.** It improves 5 mm further out, at **+95 mm** (aims 90 to 105 mm checked):
  - after a 0.2 deg re-aim: 0.87 % (against 1.08 % at 90 mm, 0.96 % at 92.5, 0.88 % at 97.5, 1.00 % at 100);
  - without the re-aim: 1.34 % at 720 C (95.1 %), which is admissible where 90 mm was not.
- **Why the old aim is off.** The 90 mm aim was set for the N map at the 740 C pressure. The grown thickness at 720 C also carries the heater map and the scattered-atom tables.

**4. Lever 3: multi-spot pyrometry with zone-group trimming.**
- **The controller** (scripts/multispot_heater.py, --heater-control multispot):
  - three pyrometer spots at 0, 50 and 85 mm, 10 mm each;
  - the 12 heater rings driven as three groups (inner, middle and outer thirds of the heater), solved so that all three spots read their calibrated values;
  - errors: a common bias of -2 / 0 / +2 K and an edge-spot error of -0.5 / 0 / +0.5 K, the same element limit, the same Ga controller (centre reading).
- **Effect on the wafer.** Over the 27 heater errors x bias states at 720 C (1460 K design), the wafer range falls from up to 14.3 K (one centre reading) to at most 6.2 K. Capped states fall from 33 % to 23 %.

| Rate monitor + BFM | B-p | B-L (aim 95 mm) |
|---|---|---|
| Multi-spot, 0.8 deg pointing, 720 C | 1.30 % (100 %) | 1.13 % (100 %) |
| **Multi-spot, 0.2 deg re-aim, 720 C** | **0.54 %** (99.9 %) | **0.72 %** (100 %) |
| Multi-spot, 0.2 deg re-aim, 710 C | 0.49 % (96.0 % with the fill known; 94.1 % without) | **0.65 %** (96.9 %) |
| Multi-spot, 0.2 deg re-aim, 700 C | 71.7 % pass (not admissible) | 78.4 % pass (not admissible) |

The heater design limit hardly matters with multi-spot control. At 720 C: B-p 0.54 % for 1460 / 1450 / 1425 K designs, B-L 0.72 / 0.74 / 0.79 %. After lever 3 the heater adds only 0.02 pt (B-p) / 0.15 pt (B-L). The worst case then sits close to the all-nominal floor of 0.30 % (B-p) / 0.43 % (B-L), and the remaining pointing residual is the largest term.

**5. Most uniform admissible points (uniformity first).**
- **B-p: 710 C, worst 0.49 %.** It needs:
  - an N-source re-aim at commissioning to 0.2 deg;
  - multi-spot pyrometry with three zone groups;
  - a Ga beam-flux monitor and a growth-rate monitor;
  - the Ga fill tracked from charge bookkeeping;
  - heater zones designed for about 1460 K.
- **B-L: 710 C, worst 0.65 %.** Aim +95 mm, with the same instruments; fill tracking is not needed.
- **Caveats.**
  - 710 C uses the decomposition law 10 K below its fitted range (720-805 C). Decomposition is a small term there. The nearest point inside the range is 720 C: 0.54 % (B-p) / 0.72 % (B-L).
  - Crystal quality may set its own lower temperature (not modelled).
  - Commissioned maps and instrument errors are priors.

Compared with section 11, the worst case falls by a factor of three for B-p (1.53 -> 0.49 %) and 2.6 for B-L (1.67 -> 0.65 %).

## 13. Checks of the section 12 assumptions (2026-10-05)

**Commissioning re-aim rehearsal** (scripts/commissioning_reaim.py, record [commissioning_reaim.json](../data/runs/studies/commissioning_reaim.json), `synthetic`).

Setup:
- **Hidden tilt:** drawn uniformly within +/-0.8 deg, about the flange pivot or about the plate centre. Its map is superposed from the comparison's 0 and 90 deg responses; the check against the 30 and 60 deg maps agrees to 0.04-0.07 % in shape.
- **Calibration wafers:** each is an N-limited growth. Its radial thickness profile is sampled at 5 mm pitch with relative map noise. Each wafer gets a random combined heater state, which the fit does not know.
- **Estimate:** the misalignment in the mount's two flange axes is estimated by Bayesian weighted least squares, with a +/-0.8 deg tolerance prior. A sideways tilt hardly changes a radial profile, so an unweighted fit amplifies noise along that axis. The prior leaves that invisible, and nearly harmless, component alone.
- **Correction:** the mount is moved by the opposite of the estimate, with its own repeatability error.
- **Metric:** the half-range of the corrected N profile in excess of the nominal one, at the 95th percentile of 2000 trials. It is compared with the excess a 0.2 deg residual causes in its worst direction.

| Three calibration wafers, one round | B-p (97.5 mm) | B-L (90 mm) | B-L (95 mm, own tables) |
|---|---|---|---|
| No correction | 0.50-0.53 pt | 0.46-0.49 pt | 0.36 pt |
| Map 0.1 %, mount 0.05 deg | **0.110 pt** | **0.139 pt** | **0.096 pt** |
| Map 0.3 %, mount 0.05 deg | 0.126 pt | 0.157 pt | 0.113 pt |
| Map 0.3 %, mount 0.10 deg | 0.158 pt | 0.188 pt | 0.142 pt |
| Reference: 0.2 deg residual, worst direction | 0.126 pt | 0.137 pt | 0.083 pt |

- **The 0.2 deg residual of section 12 is achievable** with a mount repeatable to about 0.05 deg (0.3 mm at the 0.3 m flange pivot) and three mapped wafers. B-p reaches it at 0.1-0.3 % map noise; B-L at 90 mm needs about 0.1 %.
- **A second measure-and-correct round does not help.** The floor is set by the mount's repeatability and the unknown wafer-to-wafer heating, not by map noise.
- **A mount good only to 0.1 deg leaves 25-40 % more.** It corresponds to about a 0.25 deg residual.
- **Plate-centred tilts can only partly be removed through the flange axes,** but they are about 2.5 times less harmful to start with.
- **At B-L's 95 mm aim the map is less sensitive to pointing.** A 0.2 deg residual costs 0.083 pt against 0.137 pt at 90 mm, and the corrected residual is the smallest of the three cases.

**B-L at +95 mm with its own tables** (scripts/aim_tables.py, record aim_tables_B-L_95mm.json).
- **What is recomputed:** the pointing ensemble (49 maps) and the attenuation and lip tables at 95 mm. These replace the 90 mm tilt responses and attenuation that `--aim-maps` reused.
- **What is not:** the gas-scattered and plume factors are still those of the 90 mm aim. That is the remaining approximation.
- **Results:** with multi-spot heater control, a 0.2 deg re-aim, rate monitor + BFM and the 1460 K design (record realizable_controller_ms_BL95tables.json): **0.64 % at 710 C** (96.8 % of states) and **0.70 % at 720 C** (100 %). The approximate --aim-maps run gave 0.65 / 0.72 %, so the B-L result stands. The scattered-atom factors at 95 mm were regenerated and seed-averaged in section 14 (0.53 % at 710 C).

**Decomposition below 720 C.**
- **Grounds for a small effect:** Grandjean et al. (APL 74, 1854, 1999) report GaN decomposition in vacuum as nearly zero below 750 C, with an activation energy of 3.6 eV from laser reflectivity. The law used here (G02) has 3.1 eV, from QMS.
- **Size at 710 C:** the law gives about 0.20 nm/min against 16.7 nm/min of growth. Using 3.6 eV instead of 3.1 eV, anchored at 720 C, changes that by about 6 %.
- **Effect on uniformity:** the decomposition term's radial variation over a 6 K wafer range is about 0.27 % of the rate. A 6 % change in it moves the worst case by well under 0.1 pt (an estimate, not a rerun).
- **Conclusion:** the 710 C extrapolation is a small effect on thickness. What 710 C does to crystal quality is not modelled.

## 14. Scattered-atom tables at the frozen aims, and their Monte Carlo noise (2026-10-06)

Section 13 left one approximation: B-L at +95 mm used the gas-scattered and plume factors of the 90 mm aim. Those tables were regenerated at 95 mm. Doing so showed that the tables' Monte Carlo noise is a larger effect than their aim dependence, so the tables were rerun with several seeds and averaged.

**Method.**
- `scattered_tables.py` and `scattered_plume_tables.py` take `--aim-mm` and `--seed`. Their default runs reproduce the earlier versions bit for bit (checked on a small sample).
- Each run has 8e6 atoms in 8 batches, the settings of the section 10 tables. Independent seeds are averaged with equal weights by `scripts/average_scattered_seeds.py`:
  - B-L at +95 mm, gas (gamma 1 and 0.1): 4 seeds, record [scattered_tables_B-L_95mm.json](../data/runs/studies/scattered_tables_B-L_95mm.json);
  - B-L at +95 mm, with the plume: 4 seeds at S = 2 and 4 m^3/s and 6 more at S = 4 only (the B-L scenario), so 10 at S = 4; record [scattered_plume_tables_B-L_95mm.json](../data/runs/studies/scattered_plume_tables_B-L_95mm.json);
  - B-p at its envelope aim of +97.5 mm, with the plume: 10 seeds at S = 2 (the B-p scenario); record [scattered_plume_tables_B-p_97.5mm.json](../data/runs/studies/scattered_plume_tables_B-p_97.5mm.json).
- `realizable_controller.py --n-scatter` replaces the comparison aim's factors with these tables, for a layout run with `--n-tables`:
  - passing the old 90 mm (B-L) or 97.5 mm (B-p) tables explicitly reproduces the implicit path exactly;
  - `--scatter-flat` replaces each pressure's factor profile by its area-weighted mean, the limit with no radial shape at all;
  - `--scatter-from-aim` applies one set of tables at another aim (used for the aim scan below).
- Controller settings throughout are those of section 13: multi-spot heater, 0.2 deg re-aim, 1460 K heater design, rate monitor + BFM.
- Records:
  - [realizable_controller_ms_BL95scatter.json](../data/runs/studies/realizable_controller_ms_BL95scatter.json): the B-L result;
  - [scatter_noise_BL95.json](../data/runs/studies/scatter_noise_BL95.json) and [scatter_noise_Bp.json](../data/runs/studies/scatter_noise_Bp.json): single-seed, averaged and flat runs, and the B-L aim scan, with each constituent run's dependency hashes.

**The factor hardly depends on the aim.**
- At B-L's operating pressure (19 sccm, 8.8e-3 Pa, S = 4), scattered atoms and the plume add 13.1 % to the N arrival at both aims. The means differ by 0.03 %.
- Between the aims, the factor's radial shape differs by up to 0.2-0.6 %. Two seeds at the same aim differ by just as much (0.3-0.7 %).
- One 8e6-atom table carries 0.1-0.4 points of random half-range per pressure. The 4-seed average leaves 0.07-0.10 points, and the averaged shape is nearly flat for B-L.

**But the worst case is sensitive to table noise.** The worst case is a maximum over states, so random shape in the factor both scatters it and, on average, raises it. B-L at +95 mm, rate monitor + BFM:

| B-L +95 mm | 710 C | 720 C |
|---|---|---|
| Section 13 (90 mm factors, one seed) | 0.64 % | 0.70 % |
| 10 single-seed tables: mean +/- sd [range] | 0.60 +/- 0.12 % [0.48, 0.81] | 0.64 +/- 0.13 % [0.52, 0.85] |
| **10-seed average** | **0.53 %** (96.7 % of states) | **0.58 %** (100 %) |
| No radial shape (--scatter-flat) | 0.54 % | 0.60 % |

- One seed's table moves the B-L worst case by about +/-0.12 points (standard deviation).
- **Uncertainty of the averaged result** (audit 2026-10-06): 40 bootstrap resamples of the seeds, each averaged and rerun through the controller, give a standard deviation of **0.035 points** (5-95 %: 0.47-0.58 % at 710 C, 0.52-0.64 % at 720 C). Their mean lies 0.004 below the averaged value, so residual table noise no longer biases the maximum detectably. The heuristic sd/sqrt(10) (0.04) happened to agree for B-L. Every resample keeps 96.4-96.9 % of states admissible.
- B-L's worst case is therefore **0.53 +/- 0.04 % at 710 C and 0.58 +/- 0.04 % at 720 C** (table noise only, not model uncertainty). The shape-free limit (0.54 %) lies inside that range. That agreement is consistent with the nearly flat averaged shape but is not itself a convergence test.
- The 0.1-point drop from section 13 comes from removing the noise, not from the change of aim.

**B-L's aim, re-scanned with the averaged tables** (the 95 mm tables applied at each aim; record scatter_noise_BL95.json):

| Aim | 90 mm | 92.5 mm | **95 mm** | 97.5 mm | 100 mm |
|---|---|---|---|---|---|
| Worst case at 710 C | 0.79 % | 0.64 % | **0.53 %** | 0.52 % | 0.64 % |
| Worst case at 720 C | 0.83 % | 0.68 % | **0.58 %** | 0.56 % | 0.69 % |
| Joint fraction at 710 C | 97.2 % | 97.0 % | 96.7 % | 96.2 % | 95.7 % |

- The scan applies the 95 mm factor tables at every aim. The factor's aim dependence (0.2-0.6 % in shape between 90 and 95 mm, as large as seed noise) is neglected, so the scan is conditional on that transfer.
- The optimum lies between 95 and 97.5 mm. Those two aims differ by 0.01 points, well inside the 0.035-point table noise, and 95 mm keeps more margin above the 95 % gate.
- **The +95 mm aim can be frozen.** An aim error of 2.5 mm costs about 0.1 point.

**B-p is affected the same way** (+97.5 mm, rate monitor + BFM; record scatter_noise_Bp.json):

| B-p +97.5 mm | 710 C | 720 C |
|---|---|---|
| Section 12 (archived table, one seed) | 0.49 % (needs fill tracking) | 0.54 % |
| 10 new single-seed tables: mean +/- sd [range] | 0.73 +/- 0.23 % [0.56, 1.34] | 0.78 +/- 0.23 % [0.60, 1.39] |
| (the first 4 of them, averaged) | (0.52 %) | (0.57 %) |
| **10-seed average** | **0.57 %**: 95.0 % of states without fill tracking, 96.8 % with | **0.62 %** (100 %) |
| No radial shape (--scatter-flat) | 0.72 % | 0.78 % |

- The archived table's 0.49 % was a favourable draw. Its shape at the operating pressure lies within the new seeds' spread, and the physics code is unchanged (same scattering.py).
- B-p's worst case responds more strongly to table noise than B-L's. One of the ten seeds gives 1.34 %, although its table diagnostics (half-range, chi^2) are ordinary; without it the single-seed sd would be 0.08 points. It is kept: dropping a draw for its result would bias the average (for reference, the nine-seed average without it gives 0.51 %; audit 2026-10-06). The 4-seed value of 0.52 % moved to 0.57 % with the extra seeds.
- **Uncertainty of the averaged result** (40 bootstrap resamples): standard deviation **0.089 points**, 5-95 % range 0.50-0.78 % at 710 C (0.55-0.84 % at 720 C). The resample mean lies 0.03 above the averaged value, so residual noise may still bias B-p's maximum upward slightly. The earlier heuristic (+/-0.07) understated this.
- For B-p, removing the factor's shape makes the worst case worse. The plume genuinely reshapes B-p's N arrival (section 10: 0.4-0.6 points), so the flat limit is not a bracket for B-p.
- Whether B-p is admissible at 710 C also depends on the seed: per seed, 93.2-96.9 % of states pass without fill tracking. With the averaged table 95.0005 % pass, essentially at the gate, and across the bootstrap resamples (94.5-95.8 %) only 45 % pass without fill tracking against 100 % with it. Fill tracking is therefore a firm condition for 710 C.

**What changes.**
- **The point estimates do not rank B-p and B-L on uniformity.**
  - At 710 C B-L reaches 0.53 % and B-p 0.57 % (with fill tracking); at 720 C, 0.58 and 0.62 %.
  - The 0.16-point lead B-p had in section 12 was table noise.
  - Pairing the two layouts' bootstrap resamples gives B-p - B-L = +0.04 +/- 0.10 points (5-95 %: -0.06 to +0.24) at 710 C, and the same at 720 C. B-L is ahead in 75 % of resamples: likely no worse, not established.
- **What separates them is not uniformity:**
  - B-p needs fill tracking at 710 C, and its figures assume full nitrogen conversion (eta = 1) at 2 m^3/s. The one direct measurement of a source's conversion found at most 0.4, falling as bulb pressure rises (R41, 2026-10-06), so eta = 1 is not supported;
  - B-L assumes about 30 % conversion at 4 m^3/s, inside the measured range.
  - On that basis B-L replaces B-p as the provisional layout (section 1).
- **Every earlier scattered-variant worst case carries this noise.**
  - Sections 10-13 used single-seed tables. Their worst cases are uncertain by about +/-0.1 point and likely read high by a few hundredths to a tenth.
  - Comparisons across temperature, controllers and heater designs used the same table, so the noise largely cancels in them.
  - Absolute values, and comparisons between layouts or aims, do not get that cancellation.
- **Practice from here:** quote worst cases from seed-averaged tables. These exist for B-L at 95 mm (10 seeds at S = 4) and B-p at 97.5 mm (10 seeds at S = 2). The section 10 tables for the other layouts and aims remain single-seed.

## Appendix: superseded records

- **layout_comparison.json (6aca3b3)** compared six layouts at fixed pressures, with the Ga flux following N and unconstrained heater states. Its map-shape conclusions stand: centre-aimed shallow holes give about 11 %; deep holes are worse.
- **Earlier versions of layout_comparison_bc.json** held the pressure at the nominal operating point for every state, and ranked C's out-of-domain 1 um/h states.
- **layout_feasibility.json** used sampled, not certified, clearances.
- **Earlier versions of layout_feasibility_bc.json** (6.3 mm for the B family) bounded the clearance at seven sampled shutter angles only, not the motion between them.
