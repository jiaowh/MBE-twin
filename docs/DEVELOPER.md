# Developer guide

Technical overview of the repository: status by subsystem, documents, code, external solvers and checks. The plain-language overview is the [README](../README.md).

The proposed machine is not built. The code runs on a representative 200 mm chamber and is checked subsystem by subsystem against published cases. No result here is a validated prediction for the proposed machine.

The project goal is to reduce wafer nonuniformity, first in grown-layer thickness and subsequently in separately validated material properties. Predictive accuracy, reproducibility and laptop execution enable that outcome. Prioritize development by which uncertainty or design decision it resolves for wafer improvement; source, thermal and nitrogen maps are intermediate evidence, not a substitute for measured growth outcomes. Use the [governing outcome contract](../PHASE1_CHAMBER_PLAN.md#11-project-success-and-design-decisions) and [baseline-to-candidate measurement protocol](DATA_AND_VALIDATION_PLAN.md#demonstrating-wafer-uniformity-improvement).

## Status

| Area | Status (2026-10-01) |
|---|---|
| Direct beam and free-molecular crucible emission | Implemented; verified against closed-form and deterministic references; reproduces R07's measured fill-level profiles (Bi) |
| Collisional crucible (SPARTA DSMC) | One fitted parameter (Bi hard-sphere diameter, effective-parameter sensitivity interval 8.0-10.3 A) reproduces R07's profile shapes at 0.35-11 A/s to 0.004-0.023 RMS, noise-corrected, with seed, timestep and cell checks (free-molecular: 0.04-0.20). Absolute centre rates are 7-15 % low in the monatomic model; with Bi2 in the vapour (`r07_bi2`, compiled dimer fractions) they are -6.5 to +4.7 % at d = 8 A, and the zero-bias diameter moves to 8.0 A (6.6-9.4 A). Dimer fraction and d trade off |
| Production Ga transport (200 mm, level melt) | Sensitivity study. At 46 deg, collisional range/mean (annulus-fit estimator, checked against dense references) is about 2 % at 40 mm recess, 5.0-5.4 % at 70 mm and 7.7-9.9 % at 120 mm, against 10.3 % free-molecular. Estimator scatter is 0.2-0.6 points. Angle optima from one-setting checks (seed, half timestep, D/24 cells, 2x particles): 0.69-1.35 % at 70 mm / 54 deg, and 0.92-1.93 % at 120 mm / 58 deg, where every check exceeds the base. Report these as about 1 % and about 1.5-2 %; not converged. The temperature schedule is free-molecular, so delivered flux is 0.96-1.09 of target. Centre-flux hold complete: all 12 states within 1.5 % (+11.5-13 K to hold the flux from 40 to 120 mm at 46 deg; held-flux range/mean about 2 to 8.3 % at 46 deg, about 1 to 2 % at the optima). Not a thickness prediction |
| Heater and wafer thermal (Elmer; reduced model) | Conduction (V02) and diffuse-gray radiation (V03) verified; R03 data recorded, reproduction deferred (weak discrimination); axisymmetric 200 mm heater model verified against the V03 reference and used for the zone study; zone optimization under element-temperature, zone power-density and total-power limits (the unconstrained designed-density optimum runs the element at 1652 K at 740 C) |
| Nitrogen | Published plates (R13, R30): hole Knudsen number (free-molecular at 0.5 sccm except the 712-hole plate in 2 mm, Kn 6.4-26; at 3 sccm only thin many-hole plates, while 2 mm plates reach Kn 6-8 and the 712-hole plate Kn 1-12), free-molecular maps, and aim-offset / port-angle optima below 1 % up to L/r 11.7 (3.5 % for R13 in 2 mm, L/r 19.7, at the steepest 65 deg port scanned) with angular pointing-tolerance costs ([nitrogen boundary](../ref/notes/NITROGEN_BOUNDARY.md)). Not validated; total active-N output not modelled |
| Growth chemistry | First steady-state GaN regime model from literature constants (G01, G02, R20), closed Ga balance; growth window and thickness on the wafer ([growth note](../ref/notes/GROWTH_EVIDENCE.md)). No transients, AlN or morphology; not validated |
| Vacuum | Growth pressure from N2 flow and effective speed, and background-gas attenuation of the direct beam (`vacuum.py`, `beam.py mean_free_path`; exact regression at zero pressure). Gas-scattered arrival and the nitrogen plate's plume: `scattering.py` (test-particle Monte Carlo through fixed gas fields; hard spheres, isotropic in the centre-of-mass frame; exact per-azimuth plume density; tests/test_scattering.py). Factor tables on the comparison's pressure grid (`scripts/scattered_tables.py`, `merge_scattered_tables.py`, `scattered_plume_tables.py`) enter `layout_comparison.py --scattered` and the studies that read it (the plume tables must cover the grid pressures bracketing their 35 sccm feed limit, checked by `scatter_factors`; studies list the tables they read via `scatter_sources`); cos^n surrogate sources, spherical stand-in chamber, N wall recombination bracketed (gamma 1 / 0.1). Both table scripts take `--aim-mm` (tables at another aim) and `--seed`; `scripts/average_scattered_seeds.py` averages independent-seed runs (one 8e6-atom table moves a uniformity worst case by about +/-0.1 point; section 14 of the layout comparison). Pump curves and gas loads not implemented |
| Layout feasibility and comparison | Design envelope with known / assumed / missing inputs. Certified clearance bounds over the continuous shutter motion (B family 6.1 mm, C family 10.7 mm). Layouts B, C, B-p, C-p (re-aimed at the operating pressure) and B-L (a large high-conductance plate designed here) compared with a per-state N2 feed / pressure / attenuation balance, plate-validity and supply filters, absolute Ga hold and heater limits in every state, over 18 522 states per scenario ([layout comparison](LAYOUT_COMPARISON.md)). 1 um/h inside the model's validity needs eta >= 0.8-0.9 with the published-type plate, >= 0.22 with B-L at 4 m^3/s; published growth rates imply eta 0.06-0.57 at high flow. B-p: 0.43 / 1.75 % nominal / +/-0.8 deg worst at 1 um/h. No target agreed |
| Integrated chamber twin | First slice (2026-10-05): a recipe runs through the transient heater (implicit Euler on the steady model's terms), the Ga cell, the MFC and well-mixed pressure, arrival with the comparison's scattered-arrival tables, a persistent surface state (thickness, droplets, Ga/N ledgers) and observation operators. Controllers see readings only. Verified (V07, V09, V13, V14, ledgers, time-step convergence, steady operating point reproduced to 1e-9). The settings are calibrated on the nominal state and frozen, and the maps can come from any perturbed truth state. A 146 min recipe runs in 12-20 s. Settings frozen at 720 C do not hold for a 120 mm Ga charge (38 % of the area in the window), and the heater has no power margin at 720 C ([integrated twin](INTEGRATED_TWIN.md)). Realizable controllers (`control.py`: rate monitor, BFM, Ga steered through the frozen calibration) converge to the steady realizable solution and recover the deep charge. Not validated |
| Realizable controller and heater margin | `scripts/realizable_controller.py`: Ga steering from a frozen calibration plus named observations with errors (rate monitor, BFM, fill, commissioned maps) over the full uncertainty grid; reproduces the earlier known-maps bound exactly. Every 1 um/h point needs rate monitor + BFM; most uniform: B-p at 720 C with 3.7 % heater headroom (1.53 %), B-L at 730 C (1.67 %) (`scripts/heater_margin.py`) ([layout comparison](LAYOUT_COMPARISON.md) section 11). The joint 95 % gate (`operating_optimum.admission`) is used everywhere |
| Uniformity levers | `scripts/worst_case_drivers.py` ranks the factors behind the worst case (pointing, then heater). Levers in `realizable_controller.py`: `--pointing-residual` (commissioning re-aim), `--aim-maps/--aim-mm` (`scripts/nitrogen_aim_operating.py`), `--heater-control multispot` (`scripts/multispot_heater.py`). Most uniform: 0.49 % (B-p) / 0.65 % (B-L) at 710 C (record uniformity_levers.json; [layout comparison](LAYOUT_COMPARISON.md) section 12). Checks (section 13): `scripts/commissioning_reaim.py` (synthetic re-aim rehearsal: mount 0.05 deg, three wafers mapped to 0.1-0.3 % reach the 0.2 deg level) and `scripts/aim_tables.py` with `realizable_controller.py --n-tables` (B-L 95 mm with its own tables: 0.64 % at 710 C). Section 14: `--n-scatter GAS PLUME` adds the aim's own (seed-averaged) scattered-atom tables, `--scatter-flat` the shape-free limit, `--scatter-from-aim` one table set at other aims; `scripts/summarize_scatter_noise.py` collects single-seed, averaged, flat and aim-scan runs (cases/scatter_seeds_2026-10-06.sh). With averaged tables: B-L 95 mm 0.53 %, B-p 0.52 % at 710 C |

How to reproduce each result: [REPRODUCE.md](REPRODUCE.md).

## Documents

Start with [PHASE1_CHAMBER_PLAN.md](../PHASE1_CHAMBER_PLAN.md): scope, accuracy requirements, justified accelerations, laptop performance gates, tool choices and implementation order.

- [Representative chamber](../ref/notes/REFERENCE_CHAMBER.md): the evidence note behind every Stage A result; test case per subsystem; next actions.
- [Nitrogen boundary](../ref/notes/NITROGEN_BOUNDARY.md): active-N boundary model, measurement access, Ga/N ratio.
- [Integrated twin](INTEGRATED_TWIN.md): recipe-driven coupled run, chamber-definition contract, calibration/truth split, verification and first results.
- [Layout comparison](LAYOUT_COMPARISON.md): candidate layouts at equal growth rate with uncertainty ranges and failure conditions; inputs in the [design envelope](../data/design/design_envelope.json).
- [Proposal and plan review](PLAN_REVIEW.md): engineering gaps, unsupported assumptions and proposed slide wording.
- [Physics architecture](../mbe_twin.md): equations, data contracts, observation models and verification cases.
- [Data and validation plan](DATA_AND_VALIDATION_PLAN.md): measurements, calibration/holdout design and acceptance criteria.
- [Machine intake ledger](../data/intake/machine_requirements.json): proposal targets and unresolved machine inputs, without invented defaults.
- [Reference library](../ref/README.md): papers, manufacturer documents, solver manuals and annotated source records.

The original [PowerPoint proposal](../MBE_Phase1_Proposal_v1.2.pptx) is preserved. Its engineering edits are captured in the review and the revised Markdown plans; the PPTX itself has not been edited. The original Markdown drafts are in [ref/archive](../ref/archive/).

Commercial solver access is optional. For Stage A, the published test cases R03, R07 and R14 are in hand. Still wanted: R04, R05 and the RIBER MBE 49 technical PDF. The proposed machine later needs dimensioned drawings, selected component specifications, the template stack and calibration measurements. Accuracy and runtime are qualification requirements, not achieved results.

## Code (Stage A, started 2026-09-28)

Python 3.11+ with numpy 2.0+; the tests also need pytest and scipy, and the digitizer needs PyMuPDF. Run from the repository root with `PYTHONPATH=src`.

**Beam and crucible (free-molecular)**
- `src/mbe_twin/beam.py`: direct-beam flux (finite effusion apertures, cos^n emission, shutter shadowing, wafer rotation and dose).
- `crucible.py`: free-molecular crucible emission, verified against Clausing transmission.
- `metrics.py`: area-weighted uniformity metrics.
- `manifest.py`: run manifest.
- `vapour.py`: sourced Ga/Al vapour-pressure equations (Alcock 1984).

**Integrated twin** ([INTEGRATED_TWIN.md](INTEGRATED_TWIN.md))
- `src/mbe_twin/twin.py`: the time integrator (recipe steps, controllers, coupling, sampling, checkpoints, results).
- `chamber.py`: chamber-definition contract and runtime operators (Ga Hertz-Knudsen scaling, N output, pressure, heater feedforward table).
- `recipe.py`: recipe schema (inheritance, explicit units, `operating_point` references).
- `surface.py`: persistent surface state around `growth.steady_state` (signed growth, droplet consumption, atom ledgers).
- `sensors.py`: observation operators (pyrometer, ion gauge, regime indicator, thickness map).
- `thermal_transient.py`: implicit-Euler transient of `HeaterModel` (heater.py itself is unchanged).
- `control.py`: what the realizable controllers know (calibration state, Ga cell model, window middle at the reading).
- `scripts/twin_chamber.py` builds a definition from the comparison caches (`--truth-tilt/--truth-fill/--truth-d`), and `scripts/twin_run.py` writes the bundle in `results/twin/` and the record in `data/runs/studies/twin_*.json`.

**Collisional (DSMC) sources**
- `sparta.py` and `scripts/sparta_r07.py`: SPARTA (DSMC) crucible runs, calibrated on R07's 3.5 A/s profile and tested on its 0.35 and 11 A/s profiles.
- `sparta_source.py` and `scripts/sparta_ga.py`: a level melt in a tilted crucible and transport onto the rotating 200 mm wafer.
- `profile_fit.py`: the annulus-fit uniformity estimator, checked by `scripts/check_uniformity_estimator.py`.
- `scripts/sparta_batch.py`: runs frozen job files from `cases/`. It has a memory guard and reports failed or incomplete jobs. Admission control: `--min-free-gb` (Windows), `--min-free-wsl-gb` and `--max-wsl-load` (WSL is shared with other projects; a WSL out-of-memory kill takes the largest process, which may not be ours) and `--no-start-after`. Overnight queues on the shared laptop use `--workers 1`.
- `scripts/ga_flux_hold.py`: centre-flux hold of the Ga source (first correction plus iterations); exit status 0 only if every state is within tolerance.
- `src/mbe_twin/growth.py`: steady-state GaN growth regime (N-rich / Ga adlayer / droplets), net growth with G02 decomposition, closed Ga balance; parameters with sources in `data/parameters/gan_growth.json`. `scripts/growth_window.py` applies it on the wafer.
- `scripts/nitrogen_plate_scenarios.py`, `scripts/nitrogen_aim_study.py`: published N plates (flow regime, maps) and the aim-offset / port-angle scan.
- `src/mbe_twin/heater.py`: axisymmetric heater-ledge-wafer radiation and conduction (power- or temperature-driven zones, Newton solve); `scripts/heater_zones.py` optimizes zone powers by sequential linear programming. Set `OPENBLAS_NUM_THREADS=1` for such small dense solves: on the shared laptop multithreaded BLAS made a 130x130 solve 1000x slower.
- `scripts/sparta_r07.py --set x_dimer=X`: R07 with a Bi + Bi2 vapour; x_dimer = 0 writes exactly the monatomic input.

**Layout feasibility and comparison**
- `src/mbe_twin/layout.py`: source placement (`SourcePort`): lip or plate pose on the port cone, aim offset, tilt about a pivot behind the plate (plate centre or mounting flange), body cylinder, flange, rotary shutter blade; clearance helpers.
- `src/mbe_twin/beam.py` occluders: `CylinderOccluder` (source bodies), `HolderLip` (the holder ledge proud of the wafer face); optional `mean_free_path` for background-gas attenuation of the direct beam (exactly unattenuated without one).
- `src/mbe_twin/vacuum.py`: growth pressure from N2 flow and effective pumping speed (with the T_gas/273.15 K correction), hard-sphere beam mean free path.
- `data/design/design_envelope.json`: the design envelope: operating point, mask, chamber, source bodies, plate, pointing, heater limits, vacuum cases and the candidate layouts, each input marked known / assumed / missing.
- `scripts/layout_feasibility.py`: clearances (bodies, flanges, shutter blades over their continuous motion, holder assembly), shadowing and nitrogen adjustment per layout.
- `scripts/layout_comparison.py`: layouts at a coupled operating point (`operating_point`), then a per-state balance (`solve_states`: each pointing / heater / lip state's own feed, pressure and attenuation, lowest feed reaching the rate by grid and bisection, supply-limited states at their best feed), plate validity per state (`--kn-valid`, default 10), on-target filter (the rate actually grown with the held Ga, `RATE_TOL`), Ga cell output held with per-state attenuation, heater held to the element limit (`heater_zones.at_limit`); rankings over matched valid states for the +/-0.8 deg and +/-1.6 deg ensembles; keyed map caches (`load_or_build`).
- `scripts/nitrogen_rate_limits.py`: minimum active-N conversion per target rate and the highest reachable rate per feed ceiling, including the plate's free-molecular limit; rates at the literature eta range.
- `scripts/nitrogen_output_evidence.py` with `data/parameters/nitrogen_output_evidence.json`: eta back-calculated from published N-limited growth rates under bracketed geometry, with a joint same-chamber constraint.
- `scripts/nitrogen_plate_design.py`: plates (hole count, diameter, thickness, active radius) that stay free-molecular at a given feed, with machinability and the bright-mode evidence.
- `scripts/nitrogen_aim_pressure.py`: aim and port-angle scan at the pressure the feed creates (options for plate and operating point).
- `scripts/sparta_hole.py`: 2d axisymmetric SPARTA DSMC of one plate hole at Kn 100-0.3; transmission, angular intensity and the resulting B / B-p / C maps without attenuation and at the operating pressure of each Kn, with block errors and a Kn 100 reference; `--variant` (fine_cell, half_dt, big_reservoir) for discretization and boundary checks, `--convergence` to compare them.
- `scripts/heater_robustness.py`: combined heater errors, element headroom, and Ga protocols (fixed, temperature-corrected, ideal) under a mean controller and a centre pyrometer with bias (heater re-solved holding the reading, `heater_zones.at_reading`), with the comparison's per-state feed / pressure / attenuation balance over B-p's, B's and B-L's +/-0.8 deg ensembles.
- `scripts/operating_optimum.py`: Pareto fronts in (worst-case thickness, rate, temperature) per supply scenario, over layout, temperature 680-780 C and rate 0.25-2 um/h, with temperature-corrected Ga and the per-state nitrogen balance; `scripts/operating_cold_limit.py`: the coldest temperature that keeps the growth window at each rate under combined heater errors and a biased centre pyrometer.
- `scripts/layout_resolution_check.py`: radial resolution and direct-versus-ratio-profile check of the nominal state.
- `scripts/layout_feasibility.py` with `mbe_twin.layout.disk_to_disk_bounds` / `disk_to_cylinder_bounds` and `swept_lower_bound`: certified clearance lower bounds over continuous shutter motion (chord bound per angular step, branch and bound on the steps).
- `scripts/heater_zones.py` `optimize(..., limits=...)`: heater element temperature, zone power density and total power limits (soft-constrained sequential LP; without limits the unconstrained iteration, bit for bit).
- `scripts/record_provenance.py`: writes `data/runs/studies/PROVENANCE.md` (which commit each study record ran, what changed since, and whether it matters). Each impact note is pinned to the file version it reviewed (and optionally to records), so a later edit is "not reviewed" until re-reviewed; `--hashes` prints the current pins. Besides the sources, it checks the data tables a record names only under inputs (`scattered_tables_sha256`, `scattered_plume_tables_sha256`) and, for gas+plume records that did not record the plume tables, traces them through the comparison record they read (`recorded_hashes`).
- `scripts/commissioning_rehearsal.py` and `scripts/temperature_ga_rehearsal.py`: synthetic commissioning rehearsals (docs/COMMISSIONING_PLAN.md section 6): nitrogen identifiability with flow-dependent conversion and the throttle series; temperature and Ga calibration routes in equivalent reading error.

**Nitrogen, radiation and studies**
- `aperture.py`: the nitrogen aperture-plate source.
- `radiation.py`: the coaxial-disk radiation reference for the Elmer V03 benchmark.
- Study scripts: `scripts/crucible_knudsen.py`, `fill_level_fm.py`, `nitrogen_plate.py`, `nitrogen_knudsen.py`, `ga_n_ratio.py`, `compare_r14.py`, `vapour_species.py` (Bi2 fraction, dispersion-scaled diameters, Ga2; see `ref/notes/PHYSICS_DATA_SEARCH_2026-09-30.md`).
- `scripts/digitize_r07.py` and `compare_r07.py`: digitize R07's measured profiles and compare them with the crucible model.

## External solvers

**Elmer FEM** is pinned to the rel26.1 Windows build (`ElmerFEM-gui-nompi-Windows-AMD64-rel26.1.zip`; banner "Version 9.0, compiled 2026-01-20"). Set `ELMER_HOME` to the unpacked folder that contains `bin/`. `src/mbe_twin/elmer.py` runs cases. `cases/verification/elmer_v02_slab` (conduction) and `elmer_v03_disks` (radiation) are its benchmarks. The Elmer tests are skipped when Elmer is absent.

**SPARTA (DSMC)** runs inside WSL (Ubuntu 24.04): `git clone https://github.com/sparta/sparta ~/sparta`, check out commit `e071055`, then `cd ~/sparta/src && make serial`. `src/mbe_twin/sparta.py` calls `~/sparta/src/spa_serial` through `wsl.exe`. The SPARTA test is skipped when it is absent.

**Memory.** The laptop has 15 GB of RAM, and WSL can take up to half. Post-processing streams particle snapshots, and batches default to 3 workers and start a job only with 3 GB free. Do not run several post-processing jobs outside the batch runner in parallel.

## Checks

```powershell
python -m pytest -q
$env:PYTHONPATH = "src"; python scripts/stage_a_beam_scan.py
```

The tests check the models against closed-form solutions and independent references. Examples: point and finite-disk sources, particle conservation, shutter shadows, rotation symmetry, deterministic transmission, a stored dense beam profile, the SPARTA collisionless pipeline, and the Elmer conduction and radiation benchmarks. Outputs go to `results/`, which git ignores; compact summaries behind quoted numbers are versioned in `data/runs/`.

## Reference audit

The reference-integrity check can be rerun with Python and `pypdf`:

```powershell
python scripts/audit_references.py
```

It regenerates the combined source index and checks local hashes, file formats, PDF readability, Markdown links and planning JSON. It does not run or validate a physics model.
