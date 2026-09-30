# Representative chamber and published test cases

Compiled 2026-09-28. The proposed 8-inch machine is not built, and no partner machine's drawings or run data are accessible. No public source gives both geometry and run data for a 200 mm nitride MBE tool. The twin therefore starts from a **representative chamber**, and each subsystem model is checked against a **published simulation-versus-measurement case** on whatever machine that study used. Source records are in [reference/sources.json](../reference/sources.json).

## What this can and cannot claim

The project goal is to reduce wafer nonuniformity, initially measured through grown-layer thickness. These studies support that goal by identifying promising changes and the uncertainties that prevent a reliable choice. Temperature, metal flux and Ga/N uniformity are intermediate metrics; a representative design comparison is not a demonstrated improvement on a physical wafer. Use the [project outcome contract](../../PHASE1_CHAMBER_PLAN.md#11-project-success-and-design-decisions) when ranking candidates and planning commissioning comparisons.

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
- **Numerical uncertainty** (revised 2026-09-30 after review; `cases/sparta_r07/uq_batch.json`, summaries in `data/runs/sparta_r07/uq_batch/`, table by `scripts/summarize_uq.py`). The first-pass calibration and held-out figures are withdrawn (see below).
  - Earlier check, kept: moving the sampling slab from 3 D to 4.5 D shifts the bias by +0.015, and beyond 4.5 D it scatters without trend. Runs sample at 5-5.5 D.
  - With 2e5 particles and 16000 sampling steps, the per-bin statistical error of the normalized profile is about 0.02 (batch means over 8 time blocks). That is as large as the model-data misfit. The profile RMS is inflated by this noise (RMS^2 is about misfit^2 + noise^2), and three seeds at 3.5 A/s gave RMS 0.016, 0.018 and 0.037. Seeds, halved timestep and finer cells (11 A/s: 0.6 to 0.45 mm) all change the RMS by no more than this noise.
  - The first-pass headline figures (3.5 A/s RMS 0.009-0.015; 0.35 A/s 0.018 with 5e5 particles; 11 A/s 0.014) are single draws at this noise level. They do not establish agreement better than about 0.02-0.03, and the earlier statement that particle count "changes the RMS by less than 0.01" was not resolved either.
  - First-pass diameter scan at that noise level (bias -0.007 to +0.013 over 7-9 A) could not resolve d. Its linear-fit interval, 6.0-10.8 A, is superseded below.
  - **High-statistics repeat** (`uq2_batch.json`, 1e6 particles and 48000 sampling steps; 1.2e6 and 72000 at 11 A/s; these are now the default benchmark settings). Per-bin noise is 0.004-0.007. Noise-corrected profile RMS against R07 (d = 8 A):

| Case | Noise-corrected RMS (bias) | Seed / timestep / cell checks | Free-molecular RMS | Centre rate vs R07 |
|---|---|---|---|---|
| 0.35 A/s | 0.019-0.023 (-0.013 to -0.018) | two seeds | 0.042 | -8 to -9 % |
| 3.5 A/s | 0.009-0.011 (-0.005 to -0.010) | seed 0.011, half timestep 0.009, 0.7 mm cells 0.013 | 0.136 | -15 % |
| 11 A/s | 0.004-0.015 (-0.004 to -0.015) | two seeds (spread larger than batch-means errors; the seed spread is the uncertainty) | 0.201 | -7 to -8 % |

  - Numerical effects (seed, halved timestep, finer cells) change the 3.5 A/s bias by at most 0.005 and the rates by at most 1.3 %.
  - The 0.35 A/s case keeps a resolved residual of about 0.02 (model slightly narrower than R07), half the free-molecular error.
  - **Diameter** (3.5 A/s, noise-corrected RMS): 0.029 at 7 A, 0.009 at 8 A, 0.010 at 8.5 A, 0.015 at 9 A, 0.021 at 10 A, 0.033 at 11 A. Bias is -0.025, -0.005, -0.006, -0.005, +0.008 and +0.021. A linear fit of bias crosses zero at 9.1 A. Allowing |bias| up to the combined tolerance of digitization (0.009), statistics (0.006) and numerics (0.005), 0.012 in quadrature, gives **d = 8.0-10.3 A**. The RMS minimum lies at 8-8.5 A. This is a sensitivity interval, not a confidence interval. It replaces "8 +/- 0.5 A", which had no stated construction. The working value stays 8 A.
  - **Centre rates** (not fitted) are low in every run: 8-9 % at 0.35 A/s, 15 % at 3.5 A/s and 7-8 % at 11 A/s. Numerics move them by at most 1.3 %, so the deficit is systematic. Possible causes (R07's partly interpolated pressures, Bi2 in the vapour, the evaporation coefficient) are not quantified, so the absolute rate is uncertain by about 15 %. Update 2026-09-30: Kubaschewski's correlations (R21) put Bi2 at 29-34 mol % here, which at R07's stated pressures raises the arriving atom flux by 12-13 %. That would bring the centre rates to 96-104 %, but R07's pressures are 1.4-1.7x the compilations, so this is a lead, not a fix. See [PHYSICS_DATA_SEARCH_2026-09-30.md](PHYSICS_DATA_SEARCH_2026-09-30.md).
- **What the R07 comparison supports.** Across the tested Bi rate series (0.35-11 A/s, one crucible, L/D = 4), the collisional model reproduces the profile shape to 0.004-0.023 RMS (noise-corrected). The free-molecular model is off by 0.04-0.20 at the same rates. That is 2-20x better, and within about 2x the digitization error except at 0.35 A/s. The comparison does not establish absolute flux better than about 15 %, transfer to Ga, or transfer to other fills and tilts.
- **Limits.** One material (Bi), one crucible (L/D = 4), and profiles only to 45 mm. d is an effective hard-sphere parameter for Bi vapour, not a molecular property, and does not transfer to Ga or Al.

**Ga source on the 200 mm wafer, DSMC** (`src/mbe_twin/sparta_source.py`, `scripts/sparta_ga.py`, job files in `cases/sparta_ga/`, summaries in `data/runs/sparta_ga/`; revised 2026-09-30 after the second review. All values are recomputed with the corrected estimator; the earlier tables, including 11.56 % free-molecular at 120 mm, a 0.23 % angle minimum, "0.2-0.4 point" uncertainty and "holding the rate needs +8.5 K", are withdrawn.)

- **Set-up.**
  - Geometry: R14's 71.5 mm cylindrical bore at 350 mm, aimed at the wafer centre, with a level (horizontal) melt at admissible fills of 40, 70 and 120 mm recess.
  - Pressure: Ga saturation pressure from Alcock (R15).
  - Temperature: in "hold" mode, set per fill and angle by the **free-molecular** mass balance for the wafer-centre flux of 1 um/h GaN at Ga/N = 1. This is a schedule, not a delivered-flux control (see "Delivered flux").
  - Collisions: Ga diameter bracketed at 2.5, 5.68 and 8 A (unsourced; a literature search on 2026-09-30 found no verified neutral Ga-Ga transport cross-section).
  - Numerics: cells D/16, 6e5 particles, 24000 sampling steps. Particles are sampled at 3.0-3.5 D and carried ballistically to the rotating wafer.
- **Uniformity estimator.** Range/mean over the whole 200 mm wafer comes from a polynomial of order 4 in (r/R)^2 whose annulus averages match the 20 DSMC bins (`src/mbe_twin/profile_fit.py`). `scripts/check_uniformity_estimator.py` checks it against dense free-molecular reference profiles, using the noise recorded in the runs.
  - With that noise, the estimator's bias is at most 0.2 points and its scatter 0.28-0.52 points.
  - The former point-quartic fit overstated the 120 mm / 46 deg case by 1.1 points; raw bins understate it.
  - Each DSMC value below carries a parametric-bootstrap scatter (+/-). The spread across fit orders 3 and 5 is recorded per run.
- **Verification.** Collisionless SPARTA against dense `crucible.py` profiles: 2.41 +/- 0.29 vs 2.14 % (40 mm), 6.03 +/- 0.30 vs 5.38 % (70 mm), 10.34 +/- 0.54 vs 10.31 % (120 mm). The 70 mm difference, about 2 sigma, is unexplained; candidates are the 64-facet bore and the finite sampling slab.

Range/mean at 46 deg, 1 um/h (free-molecular temperature schedule):

| Fill (recess) | Free-molecular (dense) | d = 2.5 A | d = 5.68 A | d = 8 A |
|---|---|---|---|---|
| 40 mm | 2.14 % | 2.28 +/- 0.18 % | 1.97 +/- 0.24 % | 2.38 +/- 0.29 % |
| 70 mm | 5.38 % | 5.42 +/- 0.32 % | 5.38 +/- 0.28 % | 5.01 +/- 0.41 % |
| 120 mm | 10.31 % | 9.90 +/- 0.51 % | 8.59 +/- 0.44 % | 7.74 +/- 0.40 % |

- **Collisions matter mainly for a nearly empty cup.** At 40 and 70 mm the collisional values agree with the free-molecular ones within the scatter. At 120 mm, range/mean falls from 10.3 % to 8.6 % (d = 5.68 A) and 7.7 % (d = 8 A); d = 2.5 A is indistinguishable from collisionless. Over the admissible fills, non-uniformity at a fixed 46 deg port grows roughly 3.5-5x. The unsourced Ga diameter is the largest physical uncertainty at deep fill.
- **Observed changes in the tested checks** (120 mm, 46 deg, d = 8 A; base 7.74 +/- 0.40 %). These are one-state sensitivities, not discretization-error bounds.
  - Second seed: 7.17 +/- 0.55 %.
  - Sampling slab moved to 2.5-3.0 D: 7.65 +/- 0.57 %.
  - Cells D/24 (with 2x particles and a 2/3 timestep, changed together): 8.25 +/- 0.49 %.
- **Other states** (d = 5.68 A, 120 mm, 46 deg):
  - At 0.5 um/h: 9.83 +/- 0.46 % vs 8.59 % at 1 um/h. Uniformity depends on the rate as well as the fill.
  - At fixed temperature (953.6 C, the 40 mm schedule value): 8.86 +/- 0.42 %.
- **Port angle with collisions** (`cases/sparta_ga/ga_angle.json`), range/mean for d = 5.68 / 8 A, with the dense free-molecular value in brackets:

| Fill | 46 deg | 48 deg | 50 deg | 54 deg | 58 deg | 62 deg |
|---|---|---|---|---|---|---|
| 40 mm (spill limit 48.2 deg) | 1.97 / 2.38 (2.14) | 0.60 / 0.85 (1.01) | inadmissible | inadmissible | inadmissible | inadmissible |
| 70 mm | 5.38 / 5.01 (5.38) | - | 3.00 / 2.27 (2.97) | 0.96 / 0.69 (1.02) | 3.82 / 4.44 (3.32) | - |
| 120 mm | 8.59 / 7.74 (10.31) | - | 7.20 / 5.32 (7.75) | 4.00 / 2.18 (5.15) | 1.09 / 0.92 (2.55) | 2.37 / 2.94 (1.66) |

  The bootstrap scatter is 0.16-0.49 points.
  - Collisions move the 120 mm optimum from 62 deg or beyond (free-molecular) to about 58 deg. At 70 mm the optimum stays near 54 deg.
  - **Minima are about 1 % (70 mm) and about 1.5-2 % (120 mm), not converged.** Numerical checks at two optima (d = 8 A, `cases/sparta_ga/ga_checks.json`, one setting changed per check; +/- is the bootstrap scatter; all 8 checks completed 2026-09-30):

    | Check | 70 mm / 54 deg | 120 mm / 58 deg |
    |---|---|---|
    | Base | 0.69 +/- 0.26 | 0.92 +/- 0.28 |
    | Second seed | 0.87 +/- 0.30 | 1.47 +/- 0.40 |
    | Half timestep | 1.35 +/- 0.31 | 1.83 +/- 0.38 |
    | Cells D/24 | 0.86 +/- 0.23 | 1.29 +/- 0.39 |
    | 2x particles | 1.04 +/- 0.18 | 1.93 +/- 0.32 |

    - At 70 mm the checks span 0.69-1.35 %. Only the half-timestep value lies clearly above the base.
    - At 120 mm every check exceeds the base, and the half-timestep and 2x-particle values do so by about 1 point (about 2.3 sigma each). The base looks like a low draw, or both settings are under-resolved; one-setting checks cannot distinguish these.
    - Report the optima as about 1 % (70 mm) and about 1.5-2 % (120 mm). Sub-percent values are not established.
    - Neither check moves the optimum angle. That would need a finer angle scan at converged settings.
    - Delivered/target centre flux in these runs: 1.08-1.09 at 70 mm / 54 deg and 1.00-1.03 at 120 mm / 58 deg (free-molecular schedule).
  - **A fixed port cannot follow the optimum.** A fresh 40 mm fill spills above 48.2 deg, while the depleted charge prefers 54-58 deg.
- **Delivered flux.** Under the free-molecular temperature schedule, DSMC delivers 0.96-1.09 of the target centre flux, depending on d, fill and angle. Every comparison above is therefore at approximately, not exactly, constant flux. The temperature rise needed to hold the rate is known only for the free-molecular schedule: 953.6 to 962.1 C from 40 to 120 mm at 46 deg, and up to 979.5 C at 62 deg. A **centre-flux hold** was queued on 2026-09-30 but did not start: the job file had been parked, and the queue failed with a missing-file error. It was restarted at 22:03 that night (after the R07 two-species batch in the same queue). `sparta_ga.py --mode dsmc-hold` corrects the temperature from a previous run's delivered centre flux, and `scripts/ga_flux_hold.py` repeats the correction until delivered/target is within +/-1.5 %; it exits non-zero unless every state meets that tolerance. What is held is the Ga arrival at the wafer centre (r < 10 mm), expressed as the Ga flux of 1 um/h GaN at Ga/N = 1. It is not a growth rate, which also needs the N supply and incorporation/desorption, and not the wafer-average flux; each run now records both centre and wafer-mean delivered/target. Only states meeting the tolerance will be called centre-flux-held.
- **What this supports.** A representative-chamber sensitivity study with a verified collisional model, a validated uniformity estimator with stated scatter, recorded one-state numerical sensitivities, and a bracketed physical unknown (d). It is not a thickness prediction. In Ga-rich PAMBE, thickness follows the active-N map ([nitrogen boundary](NITROGEN_BOUNDARY.md)); the Ga map sets the Ga/N-ratio margin across the wafer.

## Next actions

Revised 2026-09-30 (night) after the third review round and its audit. Prediction accuracy stays the first outcome; wafer-uniformity improvement follows once the relevant predictions are qualified. Order: fix completion reporting and the flux/growth distinction (done), resolve the R07 pressure and species interpretation, finish a bounded centre-flux-hold comparison, then move the main effort to nitrogen and thermal prediction accuracy and a first growth model. Further angle refinement, crucible shapes and adjustable sources wait.

1. Done: run isolation and recorded configurations; named R07 benchmarks; frozen batch files; versioned summaries; manifests with source hashes ([REPRODUCE](../../docs/REPRODUCE.md)).
2. Done: numerical uncertainty of the R07 benchmarks (seeds, timestep, cells, time blocks, high-statistics repeat); d = 8.0-10.3 A, an effective-parameter sensitivity interval. The 7-15 % absolute-rate deficit remains open; Bi2 in the vapour is the lead ([physics-data note](PHYSICS_DATA_SEARCH_2026-09-30.md), section 1), and two-species R07 runs (`cases/sparta_r07/r07_bi2.json`) started on 2026-09-30. The pressure-basis question moves d by at most 3-7 % (same note).
3. Done: level-melt SPARTA geometry and transport to the inclined, rotating wafer, verified collisionless against `crucible.py`; uniformity estimator validated against dense references and applied to all Ga records.
4. Done: numerical checks at the angle optima (8 of 8; see "Minima" above). Optima are about 1 % (70 mm) and about 1.5-2 % (120 mm), not converged. A converged optimum would need a combined finer-timestep, more-particle run, which is deferred because each takes about 2 h on the laptop.
5. Running since 2026-09-30 22:03 (after the R07 two-species batch): centre-flux hold (`ga_dsmchold.json`, then `ga_flux_hold.py --iterate` to +/-1.5 %; exit status fails on any missing or unconverged state) for the 46 deg fill series and the angle optima at d = 5.68 and 8 A. Afterwards, restate the temperature rise needed to hold the centre Ga flux and the angle comparison at held centre flux, with wafer-mean flux alongside.
6. Then: a representative aperture-plate geometry (R13 patent Figs. 7-8 are the current lead; see [validation reference search](VALIDATION_REFERENCE_SEARCH_2026-09-30.md)), and a defensible Ga collision cross-section. None was found. The dispersion argument gives an exploratory scenario range of about 4-9.6 A, not a bound ([physics-data note](PHYSICS_DATA_SEARCH_2026-09-30.md), section 2); whether new Ga batches use 4 / 6 / 9.6 A waits for the two-species R07 result. The nitrogen plate model needs hole diameter, thickness and count scenarios (R13: 712/4000 x 0.203 mm; R30: about 2000 x 0.343 mm) and a flow-regime check before those plates can be run.
7. Later: crucible-shape study to reduce fill drift (after 4-6).
8. Thermal: diffuse-gray radiation verified in Elmer (V03). R03 data recorded in `data/benchmarks/r03_wu2025.json`: radial temperature differences from the Fig. 14 panel labels (test 2.4-6.0 K over 863-1163 K; R03 simulation 2.5-6.6 K), materials, emissivities and final dimensions. Each profile runs across one off-axis 6-inch GaAs substrate on a 4x6-inch platen, so a reproduction is 3-D. R03's own model misplaces the profile maxima, and the measured differences (2-6 K) are close to its +/-2 K error. A full R03 reconstruction stays deferred. R05 has been screened (full text): not reconstructible, but its measured mechanisms (backing-ring overlap, platen reflectivity, heater gap, zone ratio) are qualitative checks the 200 mm heater model must show. R16 can inform transient validation but does not establish radial accuracy.
9. Nitrogen: boundary and measurement access planned ([nitrogen boundary](NITROGEN_BOUNDARY.md)); aperture-plate sensitivity done (hole aspect dominates); hole Knudsen number 0.2-250 depending on open area, so the plate drawing decides between the free-molecular model and DSMC.
10. Still wanted: full text of R04 (R05 obtained 2026-09-30), the RIBER MBE 49 technical PDF, and a representative aperture-plate drawing.

### Exploratory (non-essential)

Not on the critical path. Run only when the laptop is otherwise idle, and after items 4-5.

- **Adjustable Ga source over a campaign** (added 2026-09-30). The collisional optimum port angle moves from about 48 deg (40 mm recess) to about 54 deg (70 mm) and 58 deg (120 mm). The spill limit only constrains the full cup, so a source that steepens as the charge depletes never violates it. The angle study above relocates the cell on the 350 mm sphere, always aimed at the wafer centre. A realistic mechanism (a bellows/gimbal pivot at the port flange) mainly shifts the aim point and changes the polar angle little, so that study does not describe it. Compare over a 40 -> 120 mm campaign, against the fixed 46 deg port:
  - (a) a cell pivoting about its flange by +/-5-10 deg, with the aim point allowed to move;
  - (b) two Ga cells at different angles with a fill-dependent flux split (no moving parts);
  - (c) a fixed port with a shaped crucible (overlaps item 7).

  Method: free-molecular screening with `crucible.py` first; DSMC (d bracket) only for the promising cases. Engineering caveats to record with any result: vacuum-compatible tilt with heater, thermocouple and shroud feedthroughs; shutter alignment; Ga creep or spitting at the lip when a hot cell is tilted (adjust between runs, not during growth); flux recalibration after each move. No production system re-aiming cells for uniformity is known to us; multiple same-species cells and large-volume depletion-tolerant crucibles are the usual industrial answers.
