# GaN/AlN MBE chamber twin: Phase-1 implementation plan

Revision: 2026-09-28, adding the representative-chamber stage and commissioning-based calibration; previous revision 2026-09-14. Status: reviewed design and evidence intake. No simulator has been implemented or experimentally validated in this repository.

This revision governs the initial implementation and replaces the [archived September 7 plan](ref/archive/PHASE1_CHAMBER_PLAN_2026-09-07_original.md). Use [mbe_twin.md](mbe_twin.md) for detailed physics, [the review](docs/PLAN_REVIEW.md) for proposal corrections, [the data plan](docs/DATA_AND_VALIDATION_PLAN.md) for measurement requirements, and [ref](ref/README.md) for retrieved evidence.

## 1. Required outcome

Build an offline, reproducible GaN/AlN growth-chamber simulator that runs on the user's RTX 5050-class laptop. Represent the proposed machine through versioned geometry, materials, source states, recipes and instruments. Release predictions with numerical error, parameter uncertainty, calibration domain and experimental validation status.

First outputs: wafer temperature histories/maps, absolute arriving Ga/Al/N species fluxes, pressure/gauge histories, signed net growth and thickness/interface maps. The functional application must support recipe input, parameter validation, batch execution, pause/restart, field inspection, exported results and a run manifest. All views and reports consume the same versioned results.

The present delivery is a plan and reference library. It does not establish a functioning twin, measured laptop runtime or a qualified chamber design.

## 2. Scope and machine baseline

Use the supplied [proposal](MBE_Phase1_Proposal_v1.2.pptx), particularly slides 8, 11 and 19, as requirements evidence. Vendor specifications are comparators until actual components are selected.

The proposed machine is not yet built, and no partner machine's drawings or run data are accessible. Work therefore starts on a **representative 200 mm plasma-GaN chamber** with the envelope of the RIBER MBE 49 GaN and Veeco GEN200. Its subsystem models are checked against published simulation-versus-measurement cases ([representative chamber](ref/notes/REFERENCE_CHAMBER.md)). Representative results support design comparisons for the proposed tool before design freeze; they do not validate it. The table below remains the target that commissioning data will replace.

| Item | Proposal requirement | Implementation treatment |
|---|---|---|
| Wafer | 8-inch growth, future larger platens | Decided 2026-09-28: 200 mm GaN-on-Si(111). Template stack, thickness, polarity and backside remain mandatory inputs. |
| Heater | Solid SiC, 1200 °C, multi-zone control | Confirm rating location and atmosphere. Model electrical power, zone coupling, holder contacts, radiation and sensing. Zone count and geometry remain unknown. |
| Source bank | Ten positions: 3 Ga, 3 Al, Si, Mg and spares | Named poses and shutters. First material models use Ga and Al; retain installed dopant-cell geometry/thermal effects even when doping is deferred. |
| Nitrogen | RF 600 W, 13.56 MHz | Measured or explicitly uncertain species-output boundary initially. Active-N flux, distribution and ion content require evidence. |
| Vacuum | Turbo ≥2000 L/s plus cryo and ion/TSP; 10^-11 mbar base target | Species-dependent pump curves, conductance, loads and gauge model. Base target is distinct from growth pressure. |
| Cooling | LN2 shrouds | Actual temperatures, coverage, contacts and evolving coatings. |
| Instruments | 30 keV RHEED, band-edge thermometer, BFM, RGA | Exact models, paths, calibration and timestamps. Quantitative RHEED images require a separately validated diffraction model. |
| Controls | Open software, interlocks/logging | Offline actuator/controller simulation and replay. Physical equipment protection remains with machine controls. |

Initial geometric scope is the growth chamber and its wafer, holder, sources, shutters, heater, shrouds, pumps and diagnostic interfaces. Incoming-wafer and vacuum boundaries represent anneal/handling modules. The user excluded the transfer and anneal modules from the twin on 2026-09-07; the hardware proposal still includes an anneal module.

GaN and AlN require separate kinetics/material cards; support sequential binary layers first. AlGaN alloys, Si/Mg incorporation and activation, InGaN MQWs, patterned-feature growth, defect evolution and device predictions follow separate gates. Include thin-film optical, thermal-interface and stress effects where sensitivity warrants them. An InGaN model requires an identified In source, which the proposal inventory does not establish.

## 3. Accuracy contract

Zero model error or zero accuracy loss from every approximation cannot be guaranteed. Preserve the accuracy objective by rejecting accelerations that exceed their declared error allowance or fail independent validation. Narrow a supported operating envelope explicitly; never silently extrapolate.

These are **proposed engineering acceptance goals**, not achieved accuracy or vendor guarantees. Final tolerances must reflect process sensitivity and measurement capability. Register maps and predeclare spatial sampling and edge exclusions.

| Quantity | Initial planning goal | Required evidence |
|---|---|---|
| Wafer temperature | Map RMSE ≤3 K; separately report local maximum errors, gradients and transients | Spatial observations and held-out zone-power/ramp cases with measurement uncertainty |
| Ga/Al arrival flux | Area mean error ≤3%; map normalized RMSE ≤5% | Absolute calibration and held-out temperature/fill/pose conditions |
| Active-N equivalent flux | Mean/map error goal 5% where independently measurable | Species interpretation and diagnostic uncertainty; growth alone confounds sticking and arrival flux |
| Thickness | Mean error ≤3%; map normalized RMSE ≤5% for sufficiently thick test layers | Whole held-out GaN and AlN wafers; absolute nm criteria for thin/near-zero layers |
| Shutter/interface transients | Set absolute timing and deposited/removed thickness tolerances before tests | Measured shutter waveform, source response and instrument resolution |
| Pressure | Initially ≤10% calibrated-signal error where well above detection limit, with combined uncertainty reported | Gas-on/off, pump-down, gauge species response and repeatability |
| Bow/curvature | Set from gap sensitivity and metrology | Held-out thermal/film stacks; no slip/cracking/TDD claim from bow alone |

For each tolerance `T_q`, allocate initially no more than `0.20*T_q` to reference numerical error and `0.10*T_q` to added reduction error in the matching metric. Include local extrema when decision-relevant. Combine correlated or biased contributions conservatively, rather than assuming cancellation. Parameter and model-form errors must still satisfy total experimental acceptance. Unknown uncertainty is not zero.

Temperature accuracy must be tightened where growth kinetics demand it. A correct mean thickness cannot conceal incorrect local temperature, regime or morphology. Declare unsupported observables rather than manufacturing confident maps.

## 4. Laptop architecture and justified tradeoffs

Confirmed 2026-09-28 on the development laptop: NVIDIA RTX 5050 Laptop GPU with 8 GB VRAM, AMD Ryzen 7 260 (8 cores, 16 threads), 15.3 GB RAM, Windows 11. For now this laptop is the only compute, including reference runs; more hardware is expected later. Size the first thermal and transport models to it. RAM, not the GPU, is the binding limit for FEM radiation and molecular-flow work; GPU memory is not host memory. The official GPU family specification is sourced in [methods evidence](ref/notes/SOLVER_AND_FIDELITY.md).

Two execution modes share physics, parameters and output contracts:

1. **Reference mode:** converged three-dimensional thermal/transport cases and calibrated surface kinetics. Permit long local jobs, checkpoints and sequential subsystem execution.
2. **Accelerated mode:** validated operator reuse, adapted meshes, reduced thermal states or interpolation within a tested domain. Revert to local reference execution or explicitly report that the requested case exceeds the supported envelope.

External compute may assist reference generation, but it remains optional for the released laptop workflow. A cloud dependency cannot silently replace the laptop requirement.

| Choice | Why consider it | Accuracy gate and invalidation |
|---|---|---|
| Sparse solvers, compiled libraries, checkpointing | Reduce memory/runtime while retaining intended equations | Residual, convergence and precision comparisons; record determinism limits |
| Reuse radiation/transport operators | Static geometry repeats across timesteps | Key caches by relevant geometry, optical/wall/source distributions and shutter state; invalidate on changes; verify conservation and normalization |
| Adaptive/local meshes | Fine physics occupies limited regions | Refinement/error estimates and local checks; preserve shadows, contacts and gaps |
| Thin film/shell representations | Avoid chamber-wide nanometre volume resolution | Compare resolved local limits for thermal resistance, stress, temperature and bow |
| Rotation averaging | Long exposures may sample many turns | Compare resolved material-point histories near shutter events and surface regime changes; disable where nonlinear memory matters |
| Different subsystem timesteps | Gas, heaters, shutters and surface states have different timescales | Event-aware stepping; separate macro/substep convergence and integrated balance checks |
| Measured plasma output map | Internal source physics can be expensive and underconstrained | Held-out operating points, source-aging checks and uncertainty; source redesign needs new evidence |
| Reduced thermal states/interpolation | Reuse reference solutions for recipes | Held-out reference and physical cases; domain checks, conservation and complete-workflow error assessment |
| Mean-field kinetics plus selected surface patches | Full-wafer atomistics is impractical | Validate named thickness/regime outputs; morphology/defect predictions require separate evidence |
| Optional GPU kernels | Suitable workloads may accelerate | Benchmark actual runtime, VRAM, precision and stochastic errors; no blanket CUDA benefit claim |
| Coarser display sampling | Keep interaction responsive | Store/export full solver fields and disclose display sampling; no change to integration |

**Performance gate:** benchmark a 60-minute recipe with three heater zones as a synthetic load case, Ga/Al/N boundaries, shutter events and rotation. Actual zone count remains a hardware input. Initial usability goals: accelerated completion within 60 minutes, reference completion within 12 hours, peak host RAM below 70% of installed memory and GPU use below 75% of available VRAM when used. These are unmeasured targets, never reasons to relax accuracy. Run a 10-minute pilot, then the complete case and a repeat under sustained load. Record preprocessing, solve, uncertainty ensemble and visualization time separately. If targets fail, optimize or explicitly narrow the workload; do not relabel an unconverged solution as accurate.

## 5. Tool choices and access

Candidate baseline: FreeCAD/STEP for geometry, Gmsh for tagged meshes, Elmer for thermal/mechanical reference solves, Molflow+ for collisionless vacuum/transport, Python with numerical libraries for coupling/calibration, and ParaView for inspection. Require small capability demonstrations before adoption and pin exact versions/licenses afterward. Standard-library-only Python is not a requirement.

Assess collisionless assumptions under plasma-on conditions and near apertures. A Knudsen-number classification is not itself a bound on beam-flux error. If collisions matter, consider SPARTA for the affected neutral domain. Charged-particle fields require additional plasma physics.

No commercial license is required for initial implementation. An optional commercial comparison would use **COMSOL Multiphysics with Heat Transfer Module**, **Molecular Flow Module** for suitable neutral cases and **Plasma Module** for a separately scoped source model. Three-dimensional inductively coupled plasma modeling can also require **AC/DC Module**; verify the selected interface/version. A 13.56 MHz input alone does not make RF Module necessary. Structural Mechanics depends on the mechanical scope. See [official-document evidence](ref/notes/SOLVER_AND_FIDELITY.md).

Most urgent access: drawings, selected part numbers, thermal/source measurements and actual laptop specifications. COMSOL cannot replace those inputs. This planning delivery installs no solver, purchases no license and sends no supplier messages.

## 6. Work packages and release gates

This is the project's single roadmap. Implementation is by the user and Claude; Stage A (section 7) must finish before the hardware design freeze. [mbe_twin.md](mbe_twin.md) supplies physics and verification detail for these packages but defines no separate stages.

Each package produces reproducible inputs, outputs and an evidence report. Numerical verification may pass while experimental validation remains pending; these statuses must be distinct.

| WP | Deliverables | Dependencies | Exit gate |
|---|---|---|---|
| 0: Requirements/data | Wafer/stack decision, machine ledger, tolerances, source register, data split, laptop inventory; representative-chamber envelope with design-variable ranges; full texts of the published test cases | This review | Critical unknowns labeled; common coordinates and first benchmark defined; each first-slice subsystem has a named published test case or a recorded gap |
| 1: Solver pilots | Conduction/radiation, finite-source, conductance and unit cases; pinned environment; timing/RAM | WP0 benchmark | Analytical/independent checks and numerical budgets pass; automation demonstrated |
| 2: Geometry/properties | CAD, contacts, source/shutter poses, property functions/uncertainties, simplification record | WP0, overlaps WP1 | Dimensional evidence, geometry checks and omitted-feature sensitivity |
| 3: Thermal/sensing | Power-driven zones, holder/wafer/shrouds, transients, optical observation, significant bow feedback | WP1–2 | Balance/convergence and held-out power/ramp/rotation evidence; unobserved-state uncertainty |
| 4: Sources/vacuum/N | Separate Ga/Al response, finite-source transport, pressure/RGA, shutters/rotation, N boundary | WP1–2 | Flux/particle balance, conductance/collision checks and held-out conditions |
| 5: Binary surface growth | Separate GaN/AlN and polarity cards, adlayers, incorporation/desorption, signed interruptions, layer ledger | WP3–4 | Conservation/limit checks and independent thickness/regime evidence for both materials |
| 6: Coupled laptop release | SI/time/field contracts, recipes, actuator/controller models, restart, exports, both modes | WP3–5 | Coupling and combined reduction error pass; complete laptop benchmark and held-out predictions |
| 7: Connected shadow | Read-only telemetry/replay, residuals, quality flags and drift/version handling | WP6 | Clock/units/missing-data tests; equivalent offline replay; no machine command authority |
| 8: Extended physics | Selected alloys/doping, patterned features, resolved plasma source, film-stress history with full mechanical feedback, defects or electrical behavior; optional operator view (e.g. Omniverse) consuming the same outputs | Relevant base outputs | Separate scope, datasets, performance and quantity-specific validation; a display adds no substitute physics |

WP3 and WP4 can proceed in parallel. Data acquisition starts in WP0. Measured-boundary nitrogen work (WP4) can begin early; resolved plasma modeling (WP8) proceeds independently if evidence makes it necessary. WP8 alloy/doping/pattern work is not a prerequisite for the thermal/flux twin, but it is required before claiming validated doping or regrowth predictions. WP7 must not turn an unvalidated offline model into an apparently authoritative live display. Validation is continuous; do not estimate this research by code line counts or conversation sessions.

### 6.1 Commissioning as the primary calibration source

The machine does not yet exist, and the budget holds few spare wafers or tool days. Calibration data should therefore come mainly from tests the hardware programme already runs (proposal slide 12), instrumented and logged so they also serve the twin. Dedicated twin runs fill only gaps that this mapping leaves.

| Hardware stage | Tests the programme already runs | Twin dataset it yields, if logged | Required action |
|---|---|---|---|
| Design freeze (M0–M6) | Design review, long-lead orders | None; this is the last cheap point to make later tests useful | Specify per-zone heater V/I logging, temperature access at more than one radius (viewports/multi-spot thermometry), BFM wafer-plane positions, raw-data/clock logging and whether a thermocouple/instrumented test wafer can be mounted |
| FAT in Jiangsu (M6–M12) | Leak check, bake-out, pump-down, heater and cell bench tests | Vacuum: pump-down, bake and gas-on/off traces at several N2 flows, gauge/RGA response. Thermal: heater power steps and zone combinations. Sources: cell degas and BEP versus cell temperature | Log to the run/data contract; tag as factory configuration |
| SAT and commissioning at MRDI (M12–M18) | Reinstallation, UHV integration, interlocks, first plasma, first GaN epitaxy | Repeat of a FAT subset in the installed configuration (transfer/drift check); plasma power/flow response; growth-rate calibrations in metal-limited (absolute metal flux) and N-limited (operational active-N) regimes; thickness maps of calibration wafers | Declare holdouts before fitting; record reassembly changes to contacts and alignments |
| Process development (M18–M24) | Regrowth, epitaxy and MQW runs, characterization | Whole-wafer thickness and structure maps from recipes the twin did not see | Predict before the run where possible; these are the validation cases |

FAT data comes from a factory configuration; reassembly can change contacts, alignment and facility boundaries. Use it for calibration, and use SAT repeats to test transfer rather than assuming it. Commissioning recipes are chosen for the machine, not for identifiability. Before fitting, compare the resulting coverage with the campaigns in [DATA_AND_VALIDATION_PLAN.md](docs/DATA_AND_VALIDATION_PLAN.md) and request dedicated runs only for identified gaps. The proposal's month-18/month-22 milestones do not establish twin validation dates.

## 7. First implementation slice

The slice runs in two stages with the same code and output contracts.

**Stage A: representative chamber (now, before design freeze).**
1. Reproduce the published dual-zone heater case (R03) in the thermal model, within that study's measurement uncertainty.
2. Reproduce the published effusion-source thickness distributions (R07) with the direct-beam kernel and Molflow crucible emission.
3. Build the representative 200 mm chamber with one Ga source, one heater/holder/wafer stack (GaN-on-Si(111) unless decided otherwise), and a nitrogen boundary. The nitrogen boundary combines an aperture-plate transport model with a total active-N range bounded by R10–R12.
4. Grow a GaN test layer in the N-limited and metal-limited regimes.
5. Run the design studies that must finish before freeze: heater zone count and geometry, temperature-sensor count and placement (observability), and source throw, aim and aperture layout for 200 mm uniformity. Report each as a comparison between options with its sensitivity, not as an absolute prediction for the proposed machine.

All Stage A outputs carry the `representative_chamber` label. The published-case reproductions are the only validation claims made in this stage. See [REFERENCE_CHAMBER.md](ref/notes/REFERENCE_CHAMBER.md).

**Stage B: proposed machine (from design freeze onward).** Replace representative geometry with the frozen drawings, and calibrate with commissioning data (section 6.1). Then repeat the GaN workflow and extend it with AlN-specific data and a separate Al cell. Provisional geometry may exercise software but stays labeled synthetic.

Across both stages, deliver executable unit/physics benchmarks; a thermal and absolute flux map on the same registered wafer; integrated thickness and conserved inventories through a shutter event; a sensor-space measurement comparison or explicit data gap; a laptop report and reference-versus-accelerated difference map; and a run bundle containing input/source/geometry hashes, versions, settings, seeds, warnings and outputs.

Scaling to every source or adding an elaborate rendered chamber follows basic conservation, units and reference checks.

## 8. Data and outstanding decisions

Use [DATA_AND_VALIDATION_PLAN.md](docs/DATA_AND_VALIDATION_PLAN.md) and [machine_requirements.json](data/intake/machine_requirements.json). The largest gaps are wafer/stack, heater/sensors, source geometry/output, effective pumping, optical/thermal properties and independent growth maps. For Stage A, the gaps are full texts of the published test cases and any public wafer-plane nitrogen distribution at 200 mm, for which none was found.

For each parameter record value, unit, provenance, source/locator, uncertainty, validity conditions and revision. Missing values stay null. Do not create apparently verified geometry, sticking probabilities or barriers from generic examples.

The present release is a concept with sourced requirements. Implementation, numerical verification, calibration, experimental validation and connection remain separate milestones.

## 9. Lessons from the supplied legacy simulator

The sibling `MBE sim` project was inspected after the initial planning delivery. Its main thermal, source, process, surface-engine, RHEED and benchmark paths substantiate several risks previously identified in the plan. See [the code-backed review](docs/LEGACY_SIM_REVIEW.md) for source locations and scope. The legacy project remains unchanged and is not a required runtime dependency.

Retain it as a comparison model. Consider recipes, reporting, parameter handling and analytical limiting cases for selective reuse after review. Replace or independently qualify the chamber-specific physics; do not make the new twin a larger version of the legacy dashboard with the same unsupported closures.

The following additions are mandatory exit checks for the relevant work packages:

| Package | Additional gate learned from legacy code |
|---|---|
| WP0: evidence intake | Classify every inherited benchmark as measured/digitized, derived, representative or synthetic. Record parent datasets and fitting use. A curve generated using the same growth law cannot independently validate that law. Audit file contents rather than inheriting `[FIXED]` or “validated” labels. |
| WP1: numerical pilots | Preserve reduced disk/source formulas as limiting-case comparisons, not machine truth. Check timestep accuracy separately from implicit-solver stability. Reused code needs its own version/hash and targeted checks. |
| WP3–4: chamber physics | Demonstrate power-driven zone/holder/shroud behavior, individual absolute source delivery and independent nitrogen/gas-load inputs. Center-normalized flux and recipe-sized nitrogen cannot establish absolute machine capability. |
| WP5: surface growth | Test metal shutter closed with N on, N off with metal present, both off, reopening after a dwell and removal across a GaN/AlN interface. Advance surface state even when incorporation is zero; account for incoming, stored, incorporated and outgoing atoms. Permit measured/supported loss rather than forcing zero or positive growth. |
| WP6: reporting | Every output has provenance and maturity. A synthetic surface or illustrative diffraction pattern is visibly labeled and cannot become a calibration observation or a validated prediction. Missing validated morphology/TDD is reported as unavailable. |
| WP6: acceleration | Forbid unqualified scaling of thermally activated event rates while leaving deposition unchanged. It changes kinetic competition. Any kMC acceleration needs a justified method and small unaccelerated comparisons across its proposed regime. This gate applies if kMC is adopted; kMC is not required for the initial wafer model. |
| WP8: morphology/defects | Require independent AFM/diffraction/defect observations appropriate to each claim. A monotonic roughness formula, tuned TDD range or plausible RHEED image is insufficient evidence. |

Acceptance therefore depends on predictive evidence, not output count or graphical realism. A reduced model may be retained where its error is demonstrated for the actual quantity and envelope; detailed models are not automatically more accurate.
