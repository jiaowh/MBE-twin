# Physics data for the open Stage A questions: 30 September 2026

This search followed the morning's [validation-reference search](VALIDATION_REFERENCE_SEARCH_2026-09-30.md). It targeted the questions the Ga study left open: the Ga collision size, the R07 absolute-rate deficit, nitrogen plate geometry, crucible shapes that resist depletion, and radiative properties for the heater model. Eleven records, R21-R31, are in [the reference manifest](../reference/sources.json), and R05 was upgraded to full text. The user saved the sources that blocked automated download (R05, R23, R26, R28, R30, R31) from a browser the same day. Reading them corrected two earlier statements, marked below. The numbers below come from `scripts/vapour_species.py` (tests in `tests/test_vapour_species.py`). No simulation settings were changed.

## Summary

| Question | Finding | Status |
|---|---|---|
| R07 centre rates 7-15 % low | Bi vapour is 29-34 % Bi2 (Kubaschewski). At R07's stated pressures that raises the arriving atom flux 12-13 %, enough to close the deficit. | Confirmed in DSMC (2026-10-01): rates -6.5 to +4.7 % at d = 8 A; zero-bias d moves to 8.0 A (section 1) |
| Ga collision diameter | Dispersion scaling, tested on Ne-Xe to within 5 %, gives 3.9-4.1 A for Ga at 1245 K. The R07-fitted Bi value is 1.8-2.4x its own dispersion value. The same ratio gives 7.5-9.6 A for Ga. | Argued scenario range (4-9.6 A), not a bound; see section 2 |
| Is Ga vapour monatomic? | Ga2 is 3e-5 to 8e-4 mole fraction at cell conditions, anchored on R23's measured equilibria. | Yes; model assumption justified |
| Nitrogen plate | Second concrete plate: Veeco UNI-Bulb, about 2000 holes of 0.343 mm (R30, not R26 as first recorded). Thickness is still unknown, and the R13/R26/R30 conductance statements do not reconcile. | Gap narrowed, not closed |
| Crucible shape | Dimensioned SUMO-type crucible (R24). A computed Riber/VG production case: 0.4 % over 190 mm and 0.05 % rate change over the fill range (R25). | Inputs for next action 3 |
| Heater | PBN spectral emissivity at 390-1050 C (R27). Si total emissivity 0.7 +/- 10 % above 650 C (R28), spectral data (R31). R05 full text: measured mechanisms, not a reconstructible case. | Inputs and qualitative checks for the 200 mm heater model |

## 1. Bi2 and the R07 rate deficit

The NEA handbook (R21, Table 2.8.2) reproduces Kubaschewski's separate correlations for Bi and Bi2 over the liquid. At R07's three states:

| R07 state | x(Bi2) | Atom-flux gain at fixed p | R07 p / Kubaschewski total | R07 p / NEA recommended |
|---|---|---|---|---|
| 573 C, 0.35 A/s | 0.324 | 1.134 | 1.73 | 1.62 |
| 666 C, 3.5 A/s | 0.300 | 1.124 | 1.63 | 1.46 |
| 723 C, 11 A/s | 0.286 | 1.118 | 1.58 | 1.38 |

At a fixed total pressure, a dimer carries two atoms at 1/sqrt(2) of the monomer speed. So the arriving atom flux is (p1 + sqrt(2) p2)/(p1 + p2) times what the monatomic model assumes. Applied to the measured deficits (8-9 %, 15 %, 7-8 %), the corrected centre rates would be about 96-104 % of R07's.

Caveats before this goes into the model:
- **R07's pressures are 1.4-1.7x the compilations.** Published Bi vapour pressures scatter by up to 40 % (R21). If R07 derived its stated pressures from its own deposition rates, they are effective values, and the rate comparison is partly circular.
- **The Bi/Bi2 split is uncertain.** Kubaschewski gives no uncertainty. A harmonic-oscillator estimate from a D0 of about 2 eV gives x(Bi2) of about 0.5, not 0.3; those spectroscopic constants were recalled rather than sourced, so this is only a consistency check. Either value makes the dimer effect at least as large as the deficit.
- **Dimers also change the collisions.** Bi2 is heavier and larger. The fitted d = 8.0-10.3 A partly absorbs that, which is one reason it is about 2x the dispersion value (section 2).
- **The evaporation coefficient cannot explain it.** A coefficient below 1 lowers the model's flux further, and the model is already low.

**Interpretation of the pressure basis** (added after review 3, 2026-09-30). The comparison of centre rates tests R07's stated p(T) together with the evaporation coefficient and the vapour composition; it cannot separate them.
- *If the compilations are right at R07's stated temperatures*, the model at compilation pressures would be about 35-45 % low even with Bi2. A coefficient below 1 only lowers it further. On R07's own Clausius-Clapeyron line (Delta H about 183 kJ/mol, dln p/dT = 0.025 /K at 666 C), a factor 1.4-1.7 in pressure is a melt 14-21 K hotter than stated, a plausible thermocouple offset for an effusion cell. Alternatively R07's pressures are effective values derived from deposition. The data cannot distinguish these.
- *What this does to the fitted diameter.* The collisional change of the profile shape depends on the Knudsen number, lambda/D proportional to 1/(n d^2). The deposit measures how much vapour actually leaves, so the density that matters is the one reproducing the measured rate, whatever the tables say. A model rate low by delta means the model density is low by about delta, which the fit compensates with d larger by sqrt(1 + delta). For the 7-15 % deficit, the monatomic fit overstates d by 3-7 % (9.1 A -> about 8.5-8.8 A for the bias zero crossing), inside the 8.0-10.3 A sensitivity interval. The interval is therefore robust to the pressure basis at that level. It is not robust to the vapour composition, which the two-species run tests.
- *What does not transfer to Ga.* The fitted d absorbs Bi2, R07's density basis and any lip effects. It stays an effective Bi parameter.

**Two-species R07 runs** (2026-10-01; `cases/sparta_r07/r07_bi2.json`, records `data/runs/sparta_r07/r07_bi2/`, table by `scripts/summarize_bi2.py`).
- *Set-up.* R07's stated total pressures, with the Kubaschewski dimer fractions (0.324 / 0.300 / 0.286). Assumptions: Bi2 diameter 2^(1/3) d, 2 rotational degrees of freedom with relaxation number 5, no vibration. Numerics as the high-statistics monatomic benchmarks, except 0.5 mm cells at 11 A/s.
- *Results.* Rate error is the centre rate against R07; RMS is noise-corrected. Monatomic values at the same d are in brackets.

| Case | d | Rate error | Profile RMS | Bias | Atoms arriving as Bi2 |
|---|---|---|---|---|---|
| 0.35 A/s, x 0.324 | 8 A | +3.0 % (-8.2 %) | 0.020 (0.023) | -0.017 (-0.018) | 41 % |
| 0.35 A/s, x 0.324 | 9 A | +0.5 % | 0.012 | -0.007 | 40 % |
| 3.5 A/s, x 0.300 | 7 / 8 / 9 / 10 A | -3.4 / -6.5 / -9.4 / -10.5 % (-10.7 / -15.3 / -16.6 / -19.0 %) | 0.013 / 0.012 / 0.024 / 0.031 | -0.010 / +0.000 / +0.011 / +0.014 | 39-41 % |
| 3.5 A/s, x 0.5 | 8 / 9 A | -2.0 / -3.5 % | 0.015 / 0.025 | +0.006 / +0.011 | 61 % |
| 11 A/s, x 0.286 | 8 A | +4.7 % (-6.8 %) | 0.004 (0.015) | -0.004 (-0.015) | 42 % |

- *The dimer hypothesis holds.* With the compiled dimer fractions and d = 8 A, the centre rates at the three R07 rates are -6.5 to +4.7 %, against -7 to -15 % for the monatomic model. The profile fits are as good or better, except where d is too large for the mixture (9-10 A at 3.5 A/s). The rate deficit was therefore mainly missing Bi2, not a numerical or geometric error.
- *What moves.*
  - At x = 0.30 the zero-bias diameter at 3.5 A/s moves from 9.1 A to 8.0 A. Its sensitivity interval moves from 8.0-10.2 A to 6.6-9.4 A (same tolerance construction as the monatomic interval).
  - At x = 0.5 the bias is positive at 8 and 9 A, so the zero crossing is below 8 A (about 6.5 A by extrapolation from two points), and the 3.5 A/s rate error falls to -2 %.
  - The dimer fraction and the Bi collision size trade off; R07's data cannot separate them.
- *Still open.*
  - At 3.5 A/s the rate stays 3-9 % low at x = 0.30. A larger dimer share or a small error in R07's interpolated 666 C pressure (1.05 Pa) could account for it.
  - At 0.35 A/s the profile residual, model slightly narrower than R07, persists with or without dimers. It is therefore not a collision effect.
  - The Bi2 diameter, rotational relaxation and missing vibration are assumptions that also enter the trade-off.
- *Consequence for Ga.* The Bi effective diameter, once Bi2 is represented, is about 6.5-8 A (6.6-9.4 A interval). That is 1.5-1.9x its dispersion value (4.2-4.4 A), down from 1.8-2.4x. Transferred to Ga (dispersion value 3.9-4.1 A), the scenario range becomes about 6-8 A (widest 6-9 A). The existing Ga runs at 5.68 and 8 A bracket it well; 2.5 A is now clearly a low outlier, and 9.6 A is generous. No Ga rerun is needed for the scenario set. A 4 A run (the dispersion-only floor) would complete the low side if a bound is wanted.

## 2. Ga collision diameter

**Method.** For an r^-6 dispersion attraction, the classical transport cross-section scales as (C6/kT)^(1/3), so the hard-sphere diameter scales as (C6/kT)^(1/6). C6 values are from R22 (Gould and Bucko 2016). Hard-sphere diameters at 273.15 K come from NIST viscosities (R29): Ne 2.57, Ar 3.64, Kr 4.16, Xe 4.90 A. Anchored on any of Ar, Kr or Xe, the scaling reproduces all four within 5 %.

**Result.**

| Species (T) | Dispersion-only d |
|---|---|
| Ga (1245 K, 1 um/h cell) | 3.9-4.1 A |
| Al (1380 K) | 3.9-4.1 A |
| Bi (939 K, R07 3.5 A/s) | 4.2-4.4 A |

The R07-fitted Bi diameter, 8.0-10.3 A, is 1.8-2.4x the Bi dispersion value. Noble gases are closed-shell; Ga and Bi atoms bond (D0 about 1.15 eV for Ga2, R23), and the Bi fit also absorbs the neglected Bi2. So:
- **Low scenario:** about 4 A, the dispersion-only value. Bonding attraction should make the real transport cross-section larger, but the dispersion scaling itself is only tested on closed-shell atoms (to 5 %), and neither the C6 extrapolation to a reactive open-shell atom nor the neglected short-range repulsion is quantified. 4 A is therefore a plausible low scenario, not a lower bound; 2.5 A is less plausible but is not excluded by evidence.
- **High scenario:** about 9.6 A, if Ga carried Bi's full enhancement. The Bi enhancement also absorbs Bi2 and R07's density basis (section 1), and Ga vapour has no dimers (section 3), so this is probably generous, again without a quantified bound.
- **Scenario set (revised after review 3):** 4 / 6 / 9.6 A are exploratory scenarios that span the argued range; they are not a confidence interval. Existing runs at 5.68 and 8 A lie inside the range and stay valid as scenario points. Rerunning the Ga study at 4 / 6 / 9.6 A waits until the two-species R07 runs show how much of the Bi enhancement is Bi2.

No measured Ga vapour viscosity or Ga-Ga potential was found, confirming the morning search. A defensible value needs a gas-phase Ga-Ga potential (ground and low-lying Ga2 states) and a transport-integral calculation.

## 3. Ga2 in the Ga cell

R23 (Balducci, Gigli and Meloni 1998; first recorded here under the wrong authors) gives D0(Ga2) = 110.8 +/- 4.9 kJ/mol, and its thermal functions use Re = 0.272 nm and omega_e = 180 cm^-1. Its Table I lists the measured Ga+ and Ga2+ ion currents at 1446-1632 K, so the equilibrium constant can be recomputed directly:
- Across the 20 points with both ions, the measured K_p is 6.4-19 times (median 7.8) the rigid-rotor/harmonic value with electronic factor 1. That fits a degenerate ground state (3Pi_u, 6-fold) plus low-lying states.
- With that factor, x(Ga2) = 3e-5 to 8e-4 at 1245 K and 1-10 Pa, extrapolating 200-400 K below the measurements with the model's temperature dependence.
- The first estimate (4e-6 to 3e-4, degeneracy bracketed 1-6) was slightly low at its upper end. The conclusion stands: Ga2 is below 0.1 %, and unlike Bi, Ga can be treated as monatomic.

## 4. Nitrogen plate geometry

Correction: the "2000 holes, #80 drill" plate was first attributed to R26 from a search excerpt. The full texts place it in R30.

- **R30 (Clinton et al. 2019):** a Veeco UNI-Bulb plate with about 2000 holes drilled with a #80 bit (0.343 mm). It is stated to be "roughly half the total conductance" of the plate behind the 9.8 um/h result.
- **R26 (Gunning et al. 2015):** that 9.8 um/h plate is a custom aperture of 5.6x the original conductance; hole count and size are not stated. It reached 9.8 um/h with N2/Ar at 600 W, with 2 % thickness standard deviation over 2 inches.
- **R13 (US 10,526,723, same Georgia Tech group):** 712 versus 4000 holes of 0.203 mm, a 5.6x conductance change. That matches R26's factor.
- **The three do not reconcile.** If R26's plate is R13's 4000 x 0.203 mm, R30's 2000 x 0.343 mm plate should have 1.4x (thin plate, conductance ~ N d^2) to 2.4x (long holes, ~ N d^3) R26's conductance, not half. At equal plate thickness, both the per-hole area and the transmission favour the larger holes. Either R26's plate is not R13's, or one statement is loose. Do not use the R30/R26 ratio as a constraint.
- **Still missing:** none gives the plate thickness or the hole pattern. The hole aspect L/r dominates the 200 mm N map ([NITROGEN_BOUNDARY.md](NITROGEN_BOUNDARY.md)), so the model should bracket L over a plausible range for machined PBN plates (for example 0.5-2 mm). It should be run for both hole sizes (0.203 and 0.343 mm), not wait for a drawing.

## 5. Crucible shapes that resist depletion

- **R24 (Chorus/Veeco unibody "SUMO" patents):** fully dimensioned. The reservoir is 35 mm by 73 mm. A 45 deg re-entrant wall leads to a 15 mm inner orifice, then a 58 mm exit cone at 9 deg to a 38 mm mouth. Because the orifice, not the melt, sets the emitting area, depletion effects are claimed to be small. No numbers are given.
- **R25 (US 6,053,981; Coherent/VG, now Riber):** a computed production case. A frustro-conical 170 cc crucible with a 14 deg taper and an elliptical 25.5 by 20.3 mm aperture sits at 36 deg and 410 mm, facing a rotating 190 mm substrate. The patent reports 0.4 % thickness variation at 130 cc, 0.05 % centre-rate change from 170 to 70 cc, and about 10x worse variation with a plain circular mouth. This geometry is close to the 200 mm case. It is a good code-to-code check for the free-molecular model, and a precedent for the "better-shaped cup" idea.
- **Tilted melt caution:** neither patent addresses a tilted cell or a level melt. The spill limit (37 mm recess at 46 deg in the 71.5 mm bore) must be rechecked for any reservoir shape.

## 6. Radiative properties for the heater model

- **R27:** PBN normal spectral emissivity, 4-16 um, 390-1050 C. A total emissivity needs extension below 4 um, where much of the 1000 C Planck spectrum lies.
- **R28 (Timans 1993, full text):** the total hemispherical emissivity of a 390 um lightly doped Si specimen rises from 0.12 at 280 C to a limit of about 0.7 at 650 C, with about 10 % uncertainty. A 725 um 200 mm wafer absorbs more and reaches the limit at a lower temperature, so at GaN growth temperature the Si substrate is at about 0.7. GaN-on-Si stacks and rough backsides still need data.
- **R31 (Ravindra et al. 2001):** spectral Si emissivity, 1-20 um, with corrections to Sato's data. Use it to cross-check R28 when building a spectral wafer model.
- **R05 (Rogers et al. 2009, full text):** BandiT maps of 6-inch GaAs wafers on a 7x6-inch Veeco Gen 2000 platen. It is not reconstructible, because the heater geometry, absolute spacings, emissivities and measurement uncertainty are not given. It does give measured effects that the 200 mm heater model must reproduce qualitatively:
  - **Backing ring:** its ID should be 1-2 mm smaller than the ledge ID, to offset conduction from the hotter platen into the wafer edge.
  - **Platen reflectivity:** reflected heater power left a centre-wafer valley of over 20 C on a clean Mo platen. It fell below 11 C after GaAs coated the platen's underside, and to 6.5 C on a well-used platen.
  - **Heater gap:** increasing the heater-to-platen gap by about 0.75 in brought the valley below 2 C.
  - **Zone power ratio:** cutting the outer-zone share from 8 % to 4.3 % lowered the standard deviation from 2.79 to 2.06 C.
  - **Caveat:** GaAs is semi-transparent to the heater; hot Si is not, so the reflected-power mechanism will differ.
- **No reconstructible spatial heater benchmark exists yet.** R03 and R05 are both qualitative or weak tests.

## Access limits

OSTI, the University of San Francisco repository, NJIT and PyPI refused automated connections from this machine. The user saved R05, R23, R26, R28, R30 and R31 from a browser, and all six are now full-text reviewed. That review corrected R23's authors and moved the 2000-hole plate from R26 to R30. The NIST WebBook replaced CoolProp for noble-gas viscosities. R29 is the only remaining online-only record.

The NEA handbook is 950 pages (30 MB). Only its title pages and section 2.8 are kept locally; the manifest records the full file's hash and URL.

## Recommended actions, in order

1. Done (2026-10-01): two-species Bi + Bi2 R07 runs; the rate deficit closes to -6.5 to +4.7 % and d moves to about 8 A (section 1).
2. Decided: the Ga scenario range is about 6-8 A (widest 6-9 A); the existing 5.68 and 8 A runs bracket it, so no rerun. Optional: a 4 A run for the dispersion-only floor.
3. Bracket the N plate thickness with the R13 and R30 hole sizes.
4. Reproduce R25's computed case with the free-molecular crucible model, then study an R24-type reservoir in the 200 mm geometry, respecting the spill limit.
5. Build total emissivities for PBN (R27, extended) and Si (R28, R31) for the heater model. Design the 200 mm heater model so it can show R05's mechanisms: backing-ring overlap, platen reflectivity, heater gap and zone ratio.
