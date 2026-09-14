# Machine data, calibration and acceptance plan

Revision 2026-09-13. These are planned acquisitions and protocols; no machine measurements or successful validation runs are supplied in this repository.

## Intake and provenance

Start with [machine_requirements.json](../data/intake/machine_requirements.json). Each input needs units, coordinate frame or reference state, revision, source location, applicable conditions and uncertainty. Classify it as proposal target, measured, literature, digitized, fitted, prior, synthetic or derived. Record correlations and calibration history. Keep raw measurements immutable and store transformations separately.

| Data group | Required contents | Use and first owner role |
|---|---|---|
| CAD and dimensions | STEP/drawings; wafer/holder/heater/source/shutter/port poses and tolerances; contacts, apertures and cooling paths | Mechanical lead; common geometry for heat, transport and visualization |
| Wafer/template | Actual diameter/thickness, orientation, polarity, layer stack, backside coating/roughness, incoming bow and temperature history | Process lead; thermal/optical/mechanical and surface initial conditions |
| Materials | Density, heat capacity, tensor conductivity, optical properties, expansion/elasticity versus temperature; sample form and uncertainty | Materials/modeling lead; no transfer of bulk ceramic properties to films without justification |
| Heater and cells | Voltage/current/power, sensor location/calibration, zone coupling, power limits, ramps; cell fill/charge/lip geometry and shutter timing | Equipment/controls leads; power response and source output |
| Nitrogen | Source model/geometry, N2 purity/flow standard, forward/reflected power, ignition/state, aperture output diagnostics and source age | Source/process leads; active-species map and gas load |
| Vacuum | Pump curves by species, port/valve geometry, volume, leak/outgassing/bake state, cryopump loading, gauge/RGA calibration | Vacuum lead; actual effective speed and observation model |
| Metrology | Spatial/spectral/temporal resolution, spot/path, raw spectra/images, calibration, uncertainty, detection limit and registration | Metrology lead; predicted signal versus observed signal |
| Recipes/telemetry | Commanded and actual states, timestamps, shutters, rotation phase, missing/stale/quality flags and maintenance events | Controls lead; reproducible event histories and replay |

No named person is assigned without team confirmation. A public component brochure can constrain an envelope but cannot fill missing installed geometry or machine calibration.

## Initial experimental campaigns

The counts below are planning minima for feasibility, not a statistically justified final sample size. Pilot variance and parameter identifiability determine the eventual design. Reserve validation runs before fitting, and split by complete physical run/wafer rather than pixels or adjacent time samples.

| Campaign | Initial design | Independent check and failure interpretation |
|---|---|---|
| Thermal | At least 3 safe steady power levels; independent zone perturbations; heating/cooling segments; center, intermediate and edge observations where feasible | Hold out a combined zone-power setting and a ramp/rotation condition. Center agreement with edge failure indicates missing coupling/optics or insufficient observability. |
| Ga and Al, separately | At least 3 setpoints across intended range, mapped at wafer plane; opening/closing waveforms; repeated reference condition; record fill/geometry | Hold out a setpoint and a later fill/state. Fit absolute scale separately from spatial shape where identifiable. |
| Vacuum | Gas off/on/off at several calibrated flows, valve/pump states and repeated conditions; preserve RGA and gauge response | Hold out a flow/configuration and compare transient plus steady signals. Do not tune a base-pressure constant to the acceptance target. |
| Active nitrogen | Power-flow grid within vendor/commissioned limits, with diagnostic output and pressure recorded; repeat source reference state | Hold out interior and boundary points. An initial 3×3 grid is only a feasibility design; expand for nonlinearity, ignition boundaries or non-identifiability. |
| GaN growth | Separate temperature/metal/N conditions across relevant growth regimes with thickness and AFM/RHEED observations | Blind whole-wafer recipe predictions, including an interruption. Failure in morphology despite correct thickness limits the validated scope. |
| AlN growth | Independent regime series and Al cell calibration; confirmed temperature scale/polarity and substrate | Hold out AlN runs; GaN agreement does not validate AlN. Include adlayer/droplet or desorption observations where available. |
| Binary stack | GaN/AlN transitions and dwell/shutter events after single-material calibration | Hold out complete stacks; check interface depth, material removal and memory rather than only total thickness. |

Select all physical operating points with the equipment/process team and approved machine limits. This document is not a chamber operating recipe. Add at least three repeats of a reference condition early to estimate repeatability; use that estimate to design adequate replication and uncertainty intervals. Experimental access may constrain spatial temperature observations; record resulting observability limits explicitly.

## Parameter estimation and identifiability

Legacy data intake must retain dependency chains. The supplied legacy growth-rate benchmark is explicitly derived from desorption data and the assumed effective-flux law; its representative TDD series is not a direct machine measurement. These can support software checks or plausibility studies, but cannot be counted as independent physical validation. Verify claimed digitized datasets against their original figures and record their use in fitting before reserving holdouts. See [the legacy review](LEGACY_SIM_REVIEW.md).

Fit geometry only to dimensional evidence when available. Fit thermal contacts/optics to multiple spatial and transient observations. Fit beam distributions to beam data and kinetics to growth data. Jointly propagate influential cross-subsystem covariance rather than refitting every parameter against final thickness.

Examples of degeneracy: emissivity, contact and heater power can compensate at one temperature spot; N sticking and arriving flux can compensate in a growth-rate fit; source emission and gauge sensitivity can compensate in BEP. Add independent observations or report identifiable combinations and wider uncertainty. More points from the same signal do not necessarily resolve missing physics.

Use literature functions only within their reported material form, temperature, polarity and surface regimes. A digitized plot must store figure/page, axes and units, digitization method/error and original file hash. An author preprint's upload date is distinct from the article's publication year. Do not turn a source-specific result into a universal kinetic constant.

## Metrics and acceptance

For registered samples with physical area weights `w_i`:

```text
mean(q) = sum(w_i*q_i)/sum(w_i)
RMSE = sqrt(sum(w_i*(prediction_i-measurement_i)^2)/sum(w_i))
normalized_RMSE = RMSE/abs(mean(measurement))
thickness_half_range_percent = 100*(h_max-h_min)/(2*mean(h))
```

Also report maximum local error, bias, center/edge values and time-dependent features relevant to the decision. Uniformity is a property of a map, not a measure of model accuracy: two equally uniform maps can have different absolute thickness. State edge exclusion, sample support and alignment. Use absolute units near zero or for thin interfaces.

Predeclare tolerances, dataset IDs, uncertainty handling, fitting bounds, exclusions and pass/fail logic before opening held-out results. Account for spatial/time correlation. Prediction intervals must have useful width as well as coverage; very wide intervals cannot turn an inaccurate model into an accepted one. Use the initial goals in [the Phase-1 plan](../PHASE1_CHAMBER_PLAN.md) only until measurement capability and process sensitivity establish final ones.

## Numerical and laptop verification

Execute the V01–V15 verification cases in [the master plan](../mbe_twin.md) as applicable. Refine mesh, timestep, angle, Monte Carlo sample count and coupling tolerance separately, then test the combined workflow. Compare local fields and conserved totals. Record stochastic uncertainty and independent-seed checks.

Use the same input/parameter versions for reference and accelerated cases. Hold out recipe conditions from reduced-model construction. Record errors at regime transitions and shutter events, not just smooth steady states. Accept only if reference numerical error and added acceleration error fit their allocations and the complete prediction passes physical validation.

Record laptop CPU, installed/free RAM, GPU/VRAM/power limit, operating system, solver versions, threads, mesh/particle counts, warm/cold cache, wall time and peak memory. Separate actual observations from projected performance. Confirm complete-run behavior under sustained load and checkpoint/restart reproducibility.

## Run and data contracts

Use SI internally and explicit conversion boundaries. For sccm, store standard pressure/temperature and convert to particle rate; actual gas-volume throughput depends on gas temperature. Declare whether flux counts atoms, N2 molecules or growth-active equivalents. State the monolayer definition separately for each material/orientation.

The first implementation must validate input schemas and write a run manifest including machine/CAD hashes, parameter provenance, software versions, source IDs, recipe events, seeds, coordinates, disabled couplings, solver failures and validation status. Missing required data blocks a machine-specific run; an explicit exploratory mode may accept labeled priors. No exploratory result may be relabeled validated by the UI.

## Data still needed

Public references cannot provide the final CAD, installed dimensions, actual emissivity/contact state, source fill/aging, nitrogen species output, optical calibration or independent wafers for this custom chamber. The initial reference library therefore supports model selection and priors, while these machine-specific acquisitions remain part of the build plan.
