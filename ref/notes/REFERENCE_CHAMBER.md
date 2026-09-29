# Representative chamber and published test cases

Compiled 2026-09-28. The proposed 8-inch machine is not built, and no partner machine's drawings or run data are accessible. No public source gives both geometry and run data for a 200 mm nitride MBE tool. The twin therefore starts from a **representative chamber**, and each subsystem model is checked against a **published simulation-versus-measurement case** on whatever machine that study used. Source records are in [reference/sources.json](../reference/sources.json).

## What this can and cannot claim

A representative-chamber result can support design comparisons for the proposed tool: how many heater zones to use, where to put temperature sensors, and what source throw and aperture layout to choose. A subsystem model that reproduces its published case within that case's measurement uncertainty is *validated for that case*. None of this validates the proposed machine. Absolute predictions for it wait for its own drawings and commissioning data ([Phase-1 plan, section 6.1](../../PHASE1_CHAMBER_PLAN.md#61-commissioning-as-the-primary-calibration-source)). Label every output from this stage `representative_chamber`. The wafer is 200 mm GaN-on-Si(111) (user decision 2026-09-28).

## Envelope

| ID | System | Use |
|---|---|---|
| R01 | RIBER MBE 49 GaN: RF-plasma GaN on 200 mm Si, source tuned with CRHEA for rate and uniformity | Primary comparator: same process and wafer size as the proposal |
| R02 | Veeco GEN200: single 8-inch wafer, RF or NH3 nitride configuration, 1200 C dual-filament heater, UNI-Bulb source with system-specific endplate | Second comparator; confirms that aperture-plate geometry is designed per chamber |

Neither vendor publishes dimensions. Take source angles, throw and heater/wafer gaps as explicit design variables with ranges, not as recovered vendor values. Patents (e.g. R13) and the RIBER technical PDF are the next places to look for geometry.

## Test case per subsystem

| Subsystem | Case | What it checks | Status |
|---|---|---|---|
| Heater and wafer thermal | R03 dual-zone MBE heater, CETC 48 (4x6-inch platen; measured radial profiles at 863-1163 K by calibrated camera, +/-2 K) | Radiation, reflector/insulator stack and zone coupling in the Elmer model | Full text read. Emissivities and key dimensions given; heater meander, platen and hull geometry are not, so reproduction needs stated assumptions. Weak discrimination: measurement +/-2 K against a +/-3 K spread; their model under-predicts the measured surface spread (3.3 vs 5.3 K) |
| Multi-zone design | R04 multi-zone heater (67.3 K to 9.9 K with three zones) | Zone-count and reflector trends | Abstract only |
| Holder edge | R05 backing ring and platen (7x6-inch production system) | Edge conduction and reflected-power boundary conditions | Abstract only |
| Temperature observation | R06 camera imaging; kSA note H06 | Candidate full-wafer thermometry for the design-freeze sensor decision | Abstract only / H06 local |
| Effusion source transport | R07 Gericke 1991: measured Bi profiles vs fill level, rate, 60 deg tilt, crucible shape and distance (115/265 mm), D = 16.5 mm | Crucible emission model; geometric transfer 115 mm to 265 mm; collisionless limit | Full text read; Figs. 3, 4, 5 and 7 digitized (`data/benchmarks/r07_gericke1991.json`, error about 0.006-0.009). Model results below |
| 8-inch source layout | R14 Tao 2025: COMSOL free-molecular simulation, 71.5 mm cylindrical crucible, angle and distance scans for 8-inch | Code-to-code check of crucible emission + rotation on 200 mm: optimum near 46 deg, base 35 deg / 350 mm centre-to-edge about 0.90 | Full text read; simulation only (corroboration, not validation); metric definition and one dimension inconsistent |
| Nitrogen total output | R10 modified RIBER source at 200-600 W; R11 global model; R12 pyrometer method | Active-N versus power and flow; operational active-N definition | R12 full text; others abstract only |
| Nitrogen spatial distribution | None found | Aperture-plate transport model (collisionless neutral N from the hole pattern, wall recombination as a parameter) | **Gap:** no public wafer-plane N map at 200 mm |
| Growth kinetics | G01, G02, G04, G11 and the sibling project's digitized data | Regime law and desorption | See [growth evidence](GROWTH_EVIDENCE.md) |

## Consequence for the beam model (2026-09-29)

R07 and R14 both show that real crucibles are not flat cos^n emitters. A deep bore, the melt recess and diffuse wall re-emission set the angular distribution, which changes with fill level. A crucible emission model was therefore added (`src/mbe_twin/crucible.py`). Its transmission matches an independent deterministic ring (angular-coefficient) solution within Monte Carlo error (L/R = 4: 0.35633 +/- 0.00022 vs 0.35657). A remembered Clausing table value for L/R = 4 (0.3589) turned out to be wrong and was replaced by that solution.

**R14 comparison** (`scripts/compare_r14.py`, 71.5 mm bore, melt 34 mm below the orifice):

| R14 result | Crucible model | Flat Lambertian orifice |
|---|---|---|
| Base 35 deg / 350 mm, centre-to-edge 0.902 (Fig. 10) | 0.904 (second seed 0.905) | 0.938 |
| Best angle 46 deg (Fig. 11) | 54 deg | 46 deg |
| Below 1.4 % beyond 300 mm at 46 deg (Fig. 12) | 5.4 % at 300 mm (range/mean) | 1.2 % |
| Cylindrical 4.36 % at 40 deg / 350 mm (Fig. 14) | 6.9 % | 3.8-3.9 % |

R14's base case agrees with the recessed-crucible model, but its scans agree with a crucible without walls. No single model reproduces both, so R14 is internally inconsistent and our model is not tuned to it. The base-case agreement is the only corroboration claimed.

**Free-molecular fill-level sensitivity study** (`scripts/fill_level_fm.py`; revised 2026-09-29 after review). Definitions: 350 mm throw, axis aimed at the wafer centre, R14's 71.5 mm cylindrical bore, metric range/mean over the whole wafer of the rotation-averaged profile. The first study used an exact 8-inch wafer (101.6 mm radius) and a melt perpendicular to the crucible axis. It gave range/mean at 46 deg of 0.56 % (melt at the orifice), 4.1 % (34 mm recess), 7.6 % (70 mm) and 12.4 % (120 mm); the script reproduces these within Monte Carlo noise (0.54 / 4.04 / 7.55 / 12.27 %).

That melt model is not physical for a liquid at a 46 deg port. A level (horizontal) melt in a bore of radius R stays below the lip only if its recess on the axis is at least R tan(46 deg) = 37.0 mm, so the 0 mm and 34 mm fills are inadmissible. With a level melt over the admissible fills:

| Recess on axis | Transmission | Range/mean 8 inch | Range/mean 200 mm | Std 200 mm | Best angle (8 inch) | Range/mean there |
|---|---|---|---|---|---|---|
| 40 mm | 0.517 | 2.22 % | 2.14 % | 0.66 % | 48 deg (spill limit 48.2 deg) | 1.07 % |
| 50 mm | 0.470 | 3.27 % | 3.15 % | 1.02 % | 50 deg | 0.81 % |
| 70 mm | 0.398 | 5.56 % | 5.36 % | 1.74 % | 54 deg | 1.06 % |
| 95 mm | 0.337 | 8.01 % | 7.69 % | 2.50 % | 58 deg | 1.52 % |
| 120 mm | 0.296 | 10.73 % | 10.28 % | 3.38 % | 60 deg | 1.42 % |

The sub-percent optimum of the first study belongs to a fill that cannot exist at 46 deg. Over the admissible fills, the free-molecular non-uniformity at a fixed 46 deg port grows about 5x as the charge is consumed, and the best angle drifts by about 12 deg, so a layout has to be chosen for the whole campaign. Metric choice matters near the optimum: the 200 mm wafer reads about 4 % lower than 8 inch, and std is about a third of range/mean. This is a free-molecular sensitivity study. Production Ga cells are collisional (below), and collisions can move a geometrically balanced profile either way, so the collisional result must be computed, not bounded (SPARTA Ga study below).

**R07 comparison** (`scripts/compare_r07.py`; conical crucible D = 16.5 mm, 2.6 deg taper, plane at 115 mm; normalized-profile RMS over |x| <= 45 mm; digitization error about 0.006):

| R07 case | Crucible model | Flat Lambertian orifice |
|---|---|---|
| Fig. 3, L/D = 0.5 (~0.35 A/s) | 0.011 | 0.031 |
| Fig. 3, L/D = 1 | 0.011 | 0.058 |
| Fig. 3, L/D = 2 | 0.021 (model narrower) | 0.112 |
| Fig. 3, L/D = 4 | 0.044 (model narrower) | 0.218 |
| Fig. 4, L/D = 4 at 0.35 / 3.5 / 11 A/s | 0.042 / 0.142 / 0.212 | - |
| Fig. 5, 60 deg tilt, L/D = 4, 0.07 A/s, level melt | 0.12-0.14 | - |
| Fig. 7, L/D = 2, 115 mm (10 A/s) / 265 mm (1.9 A/s) | 0.040 (model narrower) / 0.012 (model broader) | - |

- The model reproduces the fill-level dependence: within 1.1 % RMS for L/D <= 1 and 2-4 % for deeper fills. A flat emitter fails. Its residual narrowing grows with fill depth and rate, consistent with collisions inside the crucible, which it neglects. R07 places the free-molecular limit below about 0.2 A/s at this geometry.
- Rate matters strongly. At 3.5 and 11 A/s the measured profiles are much flatter than the free-molecular prediction.
- Fig. 5 is unexplained. At 0.07 A/s it should be the most free-molecular case, yet it is broader than R07's own vertical L/D = 4 data. The model would need an effective L/D of about 2 (RMS 0.036) instead of the stated 4. The level melt improves the fit only slightly (0.12 vs 0.14), so either the fill differed from the caption or physics is missing (for example Bi condensation and re-evaporation near a cooler lip at 499 C). The gravity-melt feature is therefore verified numerically (mirror symmetry, particle conservation) but not validated by R07.
- Fig. 7 (distance transfer, 115 to 265 mm). The 265 mm panel has no x axis of its own; it is read with the 115 mm panel's axis, which the figure's construction lines imply. Scaling the measured 115 mm profile about a point source at the orifice fails (RMS 0.048). Scaling about the taper apex, 182 mm below the orifice as R07 proposes, fits (RMS 0.014); the best-fit depth is 127 mm (RMS 0.005). The free-molecular model is too narrow at 115 mm but slightly too broad at 265 mm: between the planes its half-width grows 1.76-1.87x, the measurement 1.52-1.65x. Collisions cannot give errors of opposite sign from one source at one temperature, and a 5-10 % error in the shared x scale would remove the discrepancy. The shape-transfer result is therefore not separable from the digitization assumption.
- Fig. 7 centre rates are independent of that assumption. The measured 115/265 ratio is 5.26 (5.13-5.41 given rounding of 1.9 A/s), matching 1/R^2 from the orifice (5.31). The free-molecular model gives 4.64, an effective origin about 15 mm below the orifice. At this rate the beam behaves as if emitted from the orifice, consistent with collisions near the aperture. For the twin, scaling a flux measured at one distance (a BFM or sensor) to the wafer with the free-molecular source is off by about 12 % over a 115-to-265 mm change at high rate.
- Fig. 7 caption conflict: 593 C with 10 A/s at 115 mm does not fit Figs. 3-4 (573 C gives 0.35 A/s at L/D = 4). The 115 mm profile is flatter than Fig. 3's low-rate L/D = 2 curve (0.60 vs 0.52 at 45 mm), which supports the stated high rate, so the temperature is the likelier error. Not resolved.

**Consequence for the 8-inch fill-level result.** Practical GaN/AlN growth rates (about 1-3 A/s) lie in the rate range where R07 shows substantial collision flattening. R07 shows collision-induced flattening for its geometry, but that does not make the free-molecular result a bound for a rotating, tilted wafer: broadening can move a balanced profile in either direction. The fill-level result at production rates needs a collisional crucible model (e.g. DSMC with SPARTA) or rate-dependent calibration. Ga differs from Bi in vapour pressure and cross-section, so the threshold must be recomputed with a sourced Ga vapour-pressure curve.

**Collision regime at production rates** (`scripts/crucible_knudsen.py`, 2026-09-29). R07's criterion is lambda/D > 12 for free-molecular behaviour (Bi, 550 C, 4e-2 Pa, D = 16.5 mm). That statement implies a hard-sphere cross-section sigma = 1.0e-18 m^2 (d = 5.7 A). Metal-vapour cross-sections are not sourced, so Ga/Al results are bracketed from sigma down to sigma/5 (d = 2.5 A, a deliberately small atom). Vapour pressures are Alcock et al. 1984 (R15, +/-5 %).

| State | lambda/D (sigma ... sigma/5) | Free-molecular model error vs R07 (L/D = 4) |
|---|---|---|
| R07 Fig. 5, 499 C, 0.07 A/s (p interpolated) | 66 | - |
| R07 onset, 550 C, ~0.2 A/s | 12 | - |
| R07 573 C, 0.35 A/s | 6.2 | RMS 0.04 |
| R07 666 C, 3.5 A/s (p interpolated) | 0.52 | RMS 0.14 |
| R07 723 C, 11 A/s | 0.15 | RMS 0.21 |
| Ga at 950 C (RIBER ABI "Ga @ 1 um/h"), 25-75 mm aperture | 0.8-2.5 ... 4.2-12.6 | - |
| GaN 0.5 um/h, 71.5 mm bore, 350 mm, 46 deg, fill 0-120 mm recess | 1.3-1.7 ... 6.6-8.6 | - |
| GaN 1 um/h, Ga/N flux ratio 1.0-1.5 | 0.45-0.88 ... 2.2-4.4 | - |
| AlN 0.3 um/h | 3.4-4.5 ... 17-22 | - |
| AlN 1 um/h | 1.0-1.4 ... 5.2-6.8 | - |

- R07's three stated (T, p) pairs lie on one Clausius-Clapeyron line within 0.007 decades; unstated pressures are interpolated on it. Its 723 C caption exponent is garbled in the scan; the line confirms 4 Pa.
- The mass balance (free-molecular transmission, evaporation coefficient 1) needs 918-931 C for GaAs at 1 um/h in this geometry. RIBER quotes 950 C for its ABI cells, whose throw and insert geometry are unknown. The vapour-pressure data, crucible model and mass balance are therefore consistent to about 20-30 K.
- Required melt temperatures: GaN 1 um/h 950-984 C, AlN 1 um/h 1102-1117 C, rising 10-15 K as the charge is consumed.
- **Decision.** Ga cells for GaN at 0.5-1 um/h sit at lambda/D = 0.45-8.6. That is below R07's free-molecular limit of 12 even for the smallest cross-section, and in the band where R07 measured model errors of 0.04-0.14 RMS. AlN at 0.3 um/h is the only case that may reach the free-molecular limit, and only for sigma/5. The free-molecular fill-level and angle study is therefore a sensitivity study at production rates, not a prediction or a bound. Quantitative fill-level results need a collisional crucible model (DSMC, e.g. SPARTA under WSL) or a rate-dependent correction calibrated on R07's Fig. 4 series and later on commissioning flux maps.
- Fig. 5 (499 C) is at lambda/D of about 66, so collisions cannot explain its anomaly.

**Collisional crucible model: SPARTA DSMC** (`src/mbe_twin/sparta.py`, `scripts/sparta_r07.py`, 2026-09-29). SPARTA runs serially in WSL Ubuntu 24.04. It is built from github.com/sparta/sparta commit e071055 (banner "SPARTA (27 Aug 2026)"), `make serial`, at `~/sparta/src/spa_serial`.

- **Set-up.** The R07 conical crucible (D = 16.5 mm, 2.6 deg taper, L/D = 4) is triangulated.
  - The melt emits with `fix emit/surf` at the saturation density n = p/kT, and particles returning to it are absorbed. The source code confirms the emission is flux-weighted (cosine law), which makes this Hertz-Knudsen evaporation.
  - The bore wall is diffuse at the source temperature. The orifice plane outside the lip is absorbing, as in the free-molecular model.
  - Bi is modelled as monatomic hard spheres, with one free parameter, the diameter d; Bi2 is neglected.
  - Particles are sampled in a slab above the orifice and propagated ballistically to the 115 mm plane.
  - The grid has two levels: fine cells in and just above the bore, 3x coarser elsewhere.
- **Verification.** With collisions off, SPARTA reproduces `crucible.py` in absolute flux to 1-2 % per bin across 0-48 mm (two seeds, 0.7-1.5 M samples). The slab-to-plane propagation is unbiased against an exact point-source solution (tests/test_sparta.py).
- **Numerical convergence at 3.5 A/s, d = 8 A.**
  - Sampling height: moving the slab from 3 D to 4.5 D shifts the bias by +0.015; beyond 4.5 D (6 D, 8 D) it scatters by +/-0.01 without trend. Production runs sample at 5-5.5 D.
  - Particle count: 5x more particles changes the profile RMS by less than 0.01.
- **Calibration** of d on R07 Fig. 4 at 3.5 A/s: d = 5.68 A (the Knudsen-statement value) gives RMS 0.04-0.06, 7 A gives 0.023, 8 A gives 0.009-0.015 (bias within +/-0.01), 11 A gives 0.040 (bias +0.028). 9 A gives 0.029 (bias +0.024). The bias crosses zero near 8 A (-0.019 at 7 A, about 0 at 8 A, +0.024 at 9 A), so the adopted value is d = 8 +/- 0.5 A.
- **Held-out predictions** (d = 8 A, not refitted):

| R07 case | SPARTA profile RMS (bias) | Free-molecular RMS | Centre rate: SPARTA / free-molecular / R07 (A/s) |
|---|---|---|---|
| 0.35 A/s, 573 C | 0.018 (+0.002) | 0.042 | 0.31 / 0.34 / 0.35 |
| 3.5 A/s (calibration) | 0.009-0.015 | 0.136 | 2.95 / 4.25 / 3.5 |
| 11 A/s, 723 C, 1 mm cells (lambda_sat = 1.2 cells; under-resolved) | 0.033 (-0.029) | 0.201 | 10.4 / 15.7 / 11.0 |
| 11 A/s, 0.6 mm cells (lambda_sat = 2.0 cells, 4.0 M samples) | 0.014 (-0.011) | 0.201 | 10.2 / 15.7 / 11.0 |

- With one fitted parameter, the collisional model reproduces both held-out profiles to RMS 0.014-0.018, 2-3x the digitization error. That cuts the free-molecular error 2x at 0.35 A/s and 14x at 11 A/s. Cell size matters at high rate: the 11 A/s error drops from 0.033 to 0.014 when the fine cells shrink from 1.2 to 2.0 cells per saturation mean free path. Keep fine cells at or below lambda_sat / 2. It also predicts the absolute centre rates within 5-15 % without any flux fitting, where the free-molecular model overstates 11 A/s by 43 %. The rates run 5-15 % low, which is within the uncertainty of R07's (partly interpolated) pressures and the neglected Bi2, but this is not shown.
- **Limits.** One material (Bi), one crucible (L/D = 4), and profiles only to 45 mm. d is an effective hard-sphere parameter for Bi vapour, not a molecular property, and does not transfer to Ga or Al. Applying the method to Ga needs a Ga collision diameter; none is sourced yet, so a Ga production run must bracket d, as the Knudsen estimate did.

## Next actions

1. Done 2026-09-29: full texts of R03, R07 and R14; crucible emission model with deterministic verification; R14 and R07 comparisons; level (gravity) melt; Elmer 26.1 installed and verified (V02 slab benchmark exact to machine precision).
2. Done 2026-09-29: R07 Fig. 7 digitized and compared (above); centre-rate decay supports an orifice-origin beam at high rate; shape transfer limited by the shared-axis assumption.
3. Done 2026-09-29: in-crucible Knudsen number for Ga and Al (above): production Ga cells are collisional. SPARTA DSMC crucible model built, verified against `crucible.py`, calibrated on R07 3.5 A/s and validated on 0.35 and 11 A/s (above). Next in this line: the 200 mm fill-level and angle study for Ga at GaN production rates with SPARTA, bracketing the unsourced Ga collision diameter; then a level (tilted) melt in SPARTA.
4. R03 thermal reproduction in Elmer: digitize Figs. 14-16 (the authors will not be contacted) and state geometric assumptions for the missing heater meander, platen and hull dimensions. Expect weak discrimination (+/-2 K measurement vs +/-3 K spread).
5. Still wanted: full texts of R04 and R05, and the RIBER MBE 49 technical PDF.
6. Then run the 200 mm design studies (zone count, sensor observability, source throw and aperture layout) on the representative chamber.
