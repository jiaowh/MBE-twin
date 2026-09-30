# Provisional source-layout guidance for design freeze

Status: provisional, 2026-10-01. Every result below is `representative_chamber`: a typical 200 mm RIBER/Veeco-class geometry built from published dimensions, not the proposed machine. The subsystem models are checked only against published cases on other machines. Nothing here is a validated prediction or a demonstrated wafer improvement. It is written to inform choices that must be fixed before design freeze, and to say which measurements would settle them. The evidence is in [the reference-chamber note](../ref/notes/REFERENCE_CHAMBER.md), [the nitrogen note](../ref/notes/NITROGEN_BOUNDARY.md) and [the growth note](../ref/notes/GROWTH_EVIDENCE.md).

Metric: range/mean of the rotation-averaged map over the whole 200 mm wafer. The project's primary outcome metric, thickness half-range/mean, is half of this.

## 1. What decides thickness uniformity

In Ga-rich plasma-assisted growth, the usual GaN regime, the layer grows as fast as active nitrogen arrives. The twin's first growth model (sourced constants only) gives:

- **Thickness follows the nitrogen map and the wafer temperature.** The Ga map does not enter, as long as every point stays in the Ga-rich (adlayer) window.
- **The Ga map decides whether every point stays in that window.** The window lies between N-rich growth (rough, 3D) and Ga droplets.
- **Wafer temperature enters twice.** GaN decomposition (3.1 eV) changes the net rate, and the droplet onset (2.8-5.1 eV) changes the window width.

The source layout therefore has to be judged on the N map, the Ga/N ratio spread and the temperature map together, not on the Ga map alone.

## 2. Decisions and provisional guidance

| Decision | Provisional guidance | Confidence | What would change it |
|---|---|---|---|
| Growth temperature regime (sets the heater requirement) | Around 700 C (source-lab scale) thickness is insensitive to temperature (about 0.03 %/K range/mean), but the Ga window is narrow (0-0.29 in centre Ga/N, closing for a depleted charge at 46 deg under the tightest droplet law). At 780 C the window is wide, but thickness moves about 0.5 %/K. | Medium for trends, low for absolute temperatures | The proposed machine's temperature scale (commissioning pyrometry/thermocouple calibration); the droplet onset on that machine |
| Heater and temperature-sensor specification | Size the allowed wafer temperature range from the intended growth temperature. At 740 C, +/-5 K costs 0.6-0.7 % and +/-10 K 1.1-1.6 % thickness range/mean through decomposition alone. In the representative heater model the edge support (overlap, contact) and the radial power-density design matter as much as the zone count. 3 uniform zones reach about 7-23 K, and a designed density profile reaches about 2-10 K (0.4-14 K across the wafer-ledge contact bracket). A same-size platen (diffuser) between heater and wafer made the achievable range worse (3 zones: 17 to 23-32 K), because it removes the edge boost the wafer needs. A 5 % error in one zone's power adds 6-10 K, so specify zone power accuracy of about 1-2 % or wafer temperature sensing at more than one radius. Wafer emissivity (0.7 +/- 10 %) alone moves an unsensed wafer by about 18 K, so plan at least one wafer-temperature sensor per heater zone. In the model, one sensor corrects the mean but not the profile; one per zone recovers close to the best profile the zones allow. | Low-medium (reduced model, no heater benchmark) | The vendor's heater and holder drawings; a measured wafer temperature map |
| N plate hole geometry | Prefer a thin plate or shallow holes (L/r up to about 3): with a +/-0.8 deg pointing tolerance they keep the N map near 1-1.5 %, while L/r 5.8 and 11.7 reach 3-9 %. A beaming plate (L/r 5-12 with the published 0.2-0.34 mm holes in a 1-2 mm plate) can be evened out only by precise off-centre aiming. | Medium (free-molecular model, self-consistent at 0.5-3 sccm for many-hole plates) | Plate thickness, hole pattern and tilt from the vendor; a measured N-limited thickness map |
| N source aim and port angle | Aim the plate off-centre, near the wafer edge (+55 to +105 mm on the source side), at 45-65 deg. Best found per plate: about 1 % or below (0.3-0.6 % thin and L/r 2.9, 0.4-0.9 % L/r 5.8, 0.9-1.4 % L/r 11.7; Monte Carlo scatter 0.3-0.5 points), insensitive to a +/-50 % radial output profile. Specify pointing to better than about +/-0.8 deg (+/-5 mm at the wafer) for beaming plates; +/-10 mm costs up to 2 / 4 / 10 points for L/r 2.9 / 5.8 / 11.7. | Medium for the trend, low for the numbers | Real plate output profile and hole tilt; port clearance with the Ga cell and shutters (not checked) |
| Ga port angle | No fixed angle is best over a campaign: the collisional optimum moves from about 48 deg (fresh charge, spill limit 48.2 deg) to 54-58 deg (depleted). At 46 deg the Ga map spread grows from about 2 % to 8-10 % as the charge is consumed. It matters for thickness only through the window, and mainly at low growth temperature. | Medium (DSMC validated on R07 shape; Ga collision size unsourced) | Centre-flux-hold runs (running); Ga collision size; the droplet onset on the machine |
| Ga crucible and campaign strategy | Keep the charge within a fill range that keeps the Ga spread inside the window at the chosen temperature, or use depletion-tolerant crucibles (R24/R25 designs). Adjustable-angle sources are unproven. | Low | Crucible-shape study (not done) |

## 2a. Rough thickness budget

These are contributions to thickness range/mean in Ga-rich growth at 1 um/h, from the separate studies. They are added as a rough upper bound; real profiles can partly cancel or compound.

| Contribution | 700 C | 740 C | 780 C |
|---|---|---|---|
| N map at the best aim (thin plate to L/r 11.7) | 0.3-1.0 % | 0.3-1.0 % | 0.3-1.1 % |
| N map worst case within a pointing error of +/-5 mm (+/-0.8 deg); +/-10 mm in brackets | 0.4 % thin, 1.2-1.6 % (2.1-2.5) L/r 2.9, 2.7-3.5 % (4.4-5.7) L/r 5.8, 6.7-8.9 % (10.5-12.3) L/r 11.7 | same | same |
| Wafer temperature, 3 uniform zones with one sensor per zone (17 K nominal, up to 26 K on perturbed holders) | 0.5-0.8 % | 1.9-4.2 % | 7.6-17 % |
| Wafer temperature, designed power density (about 6 K nominal) | about 0.2 % | 0.7-1.0 % | 2.7-3.8 % |
| Ga map, inside the Ga-rich window | none | none | none |
| Ga map, window margin (centre Ga/N) | 0-0.29: the fill and port angle matter | about 1 | several |

The per-kelvin factors behind the temperature rows come from G02 decomposition (0.03 / 0.11-0.16 / 0.45-0.64 % per K of wafer range at 700 / 740 / 780 C). They are shape-independent to first order.

Reading the table:
- **Around 700 C** (source-lab scale), the N map and N pointing dominate. Temperature matters little for thickness, but the Ga window is narrow, so the Ga fill range and port angle matter for staying out of droplets and N-rich growth.
- **Around 740 C**, the heater and the N source contribute comparably. A 3-zone heater with uniform zones is the largest single term unless the edge support and power-density design are good.
- **Around 780 C**, the heater dominates everything.

The growth temperature of the proposed machine, on its own calibrated scale, is therefore the first thing that decides which subsystem the design effort should go to.

## 2b. Predicted baseline and candidate maps

`scripts/wafer_outcome.py` (record `results/wafer_outcome/manifest.json`) chains the models: Ga DSMC record, N plate map, optimized heater temperature map, then the growth model at the middle of the Ga-rich window. It reports the protocol's primary metric, thickness half-range/mean, with area-weighted std in brackets.

Each subsystem has a baseline and a candidate option, and all combinations are evaluated so that no improvement is credited to the wrong change:
- Ga: 46 deg port with a depleted 120 mm charge, or the 58 deg optimum.
- N: plate aimed at the wafer centre at 45 deg, or at its aim optimum.
- Heater: 3 uniform zones on a 3 mm overlap, or a designed power density on a 1 mm overlap.

| Plate, growth temperature | All baseline | N aim only | Heater only | All candidate |
|---|---|---|---|---|
| L/r 5.8 (R30-type holes, 1 mm plate), 700 C | 27.5 % (15.2), Ga window empty | 0.62 % (0.35) | 27.8 %, window empty | 0.48 % (0.30) |
| L/r 5.8, 740 C | 27.4 % (15.7) | 1.51 % (0.86) | 28.7 % (15.8) | 0.57 % (0.36) |
| Thin plate, 700 C | 0.51 % (0.36) | 0.35 % (0.20) | 0.49 % (0.31) | 0.14 % (0.08) |
| Thin plate, 740 C | 1.36 % (0.85) | 1.23 % (0.81) | 0.46 % (0.29) | 0.23 % (0.12) |

- **For a beaming plate, the N aim is the decisive change**; nothing else matters until it is fixed. With the centre-aimed beaming plate at 700 C, no Ga/N setting keeps the whole wafer in the Ga-rich window.
- **For a thin plate the baseline is already good.** The heater is the main lever at 740 C, and the N aim at 700 C.
- **The Ga port option never changes the thickness.** It widens the Ga-rich window, for example from 0.18 to 0.22 in centre Ga/N at 700 C with the thin plate.
- **Nonuniformities interact.** With the centre-aimed beaming plate, a flatter heater made thickness worse (27.4 to 28.7 %): the colder edge had been partly offsetting the centre-peaked N map. A layout must be judged on the combined map, and relying on such cancellation is fragile.
- **Not included:** N pointing errors and heater parameter perturbations. Their separate effects are in section 2, and both enlarge the candidate numbers. These are predicted differences on a representative chamber, and the improvement protocol requires measured wafers.

## 3. Open gates

1. **Centre-flux hold (running).** The Ga comparisons are at approximately, not exactly, constant centre flux; runs holding it to +/-1.5 % finish on 2026-10-01.
2. **Bi2 and the R07 rate (done).** With the compiled dimer fractions the R07 rates are -6.5 to +4.7 % (monatomic: -7 to -15 %), and the fitted Bi collision size moves from 9.1 to 8.0 A. The Ga scenario range becomes about 6-8 A, bracketed by the existing runs.
3. **Ga collision size.** Unsourced; about 6-8 A (widest 6-9 A) is an argued scenario range after the Bi2 result, not a bound. It matters mainly for a depleted charge.
4. **N plate.** Thickness, pattern, hole tilt, active radius and output profile unknown; transitional hole flow above about 3 sccm or with few holes is not modelled; total active-N output is not modelled.
5. **Temperature scale and droplet onset.** The literature disagrees by up to a factor 3-4 at 700 C; each lab's temperature scale differs.
6. **Heater.** No reconstructible published heater benchmark. The reduced axisymmetric model (2026-10-01) has no platen, shields or semi-transparent optics, and it disagrees qualitatively with R05 on the effect of the heater gap. R05's mechanism, reflected power through GaAs, is not in the model.

## 4. Measurements to specify at design freeze

These make commissioning tests (FAT/SAT) serve as calibration ([Phase-1 plan, section 6.1](../PHASE1_CHAMBER_PLAN.md#61-commissioning-as-the-primary-calibration-source)):

- **N-limited (Ga-rich) thickness maps** of calibration wafers at two or more growth temperatures and N source settings, with the N source aim recorded. This is the only direct test of the N map, which the studies above identify as the most uncertain and most consequential input.
- **Ga-limited (N-rich) thickness maps** at two or more fill levels over a campaign. They measure the Ga map and its drift.
- **Wafer temperature at more than one radius** (multi-spot pyrometry or an instrumented wafer), logged with per-zone heater power.
- **N source alignment** with a mechanical reference that allows the aim to be measured and adjusted, and the plate drawing (thickness, pattern, tilt) from the vendor.
- **Droplet onset and N-rich boundary** (RHEED/QMS) at the operating temperatures, on the machine's own temperature scale.

## 5. What this does not claim

- These are comparisons on a representative chamber with stated uncertainties, not predictions for the proposed machine.
- Agreement with published cases is limited to the Ga beam shape (R07) and literature kinetics. No N map and no heater result is validated.
- A flatter Ga or N map in the model is not a measured thickness improvement. Success is judged by the [improvement protocol](DATA_AND_VALIDATION_PLAN.md#demonstrating-wafer-uniformity-improvement).
