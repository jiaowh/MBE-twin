# Developer guide

Technical overview of the repository: status by subsystem, documents, code, external solvers and checks. The plain-language overview is the [README](../README.md).

The proposed machine is not built. The code runs on a representative 200 mm chamber and is checked subsystem by subsystem against published cases. No result here is a validated prediction for the proposed machine.

The project goal is to reduce wafer nonuniformity, first in grown-layer thickness and subsequently in separately validated material properties. Predictive accuracy, reproducibility and laptop execution enable that outcome. Prioritize development by which uncertainty or design decision it resolves for wafer improvement; source, thermal and nitrogen maps are intermediate evidence, not a substitute for measured growth outcomes. Use the [governing outcome contract](../PHASE1_CHAMBER_PLAN.md#11-project-success-and-design-decisions) and [baseline-to-candidate measurement protocol](DATA_AND_VALIDATION_PLAN.md#demonstrating-wafer-uniformity-improvement).

## Status

| Area | Status (2026-10-01) |
|---|---|
| Direct beam and free-molecular crucible emission | Implemented; verified against closed-form and deterministic references; reproduces R07's measured fill-level profiles (Bi) |
| Collisional crucible (SPARTA DSMC) | One fitted parameter (Bi hard-sphere diameter, effective-parameter sensitivity interval 8.0-10.3 A) reproduces R07's profile shapes at 0.35-11 A/s to 0.004-0.023 RMS, noise-corrected, with seed, timestep and cell checks (free-molecular: 0.04-0.20). Absolute centre rates are 7-15 % low in the monatomic model; with Bi2 in the vapour (running, `r07_bi2`) the 11 A/s rate is +4.7 % and the 3.5 A/s rate -6.5 % at d = 8 A, and the zero-bias diameter moves towards 8 A |
| Production Ga transport (200 mm, level melt) | Sensitivity study. At 46 deg, collisional range/mean (annulus-fit estimator, checked against dense references) is about 2 % at 40 mm recess, 5.0-5.4 % at 70 mm and 7.7-9.9 % at 120 mm, against 10.3 % free-molecular. Estimator scatter is 0.2-0.6 points. Angle optima from one-setting checks (seed, half timestep, D/24 cells, 2x particles): 0.69-1.35 % at 70 mm / 54 deg, and 0.92-1.93 % at 120 mm / 58 deg, where every check exceeds the base. Report these as about 1 % and about 1.5-2 %; not converged. The temperature schedule is free-molecular, so delivered flux is 0.96-1.09 of target. Centre-flux-hold runs, iterated to +/-1.5 %, are running (queued after the R07 Bi2 batch). Not a thickness prediction |
| Heater and wafer thermal (Elmer; reduced model) | Conduction (V02) and diffuse-gray radiation (V03) verified; R03 data recorded, reproduction deferred (weak discrimination); axisymmetric 200 mm heater model verified against the V03 reference and used for the zone study |
| Nitrogen | Published plates (R13, R30): hole Knudsen number (free-molecular at 0.5-3 sccm for many-hole plates), free-molecular maps, and aim-offset / port-angle optima below 1 % with pointing-tolerance costs ([nitrogen boundary](../ref/notes/NITROGEN_BOUNDARY.md)). Not validated; total active-N output not modelled |
| Growth chemistry | First steady-state GaN regime model from literature constants (G01, G02, R20), closed Ga balance; growth window and thickness on the wafer ([growth note](../ref/notes/GROWTH_EVIDENCE.md)). No transients, AlN or morphology; not validated |
| Vacuum | Planned; not implemented |
| Integrated chamber twin | Not implemented |

How to reproduce each result: [REPRODUCE.md](REPRODUCE.md).

## Documents

Start with [PHASE1_CHAMBER_PLAN.md](../PHASE1_CHAMBER_PLAN.md): scope, accuracy requirements, justified accelerations, laptop performance gates, tool choices and implementation order.

- [Representative chamber](../ref/notes/REFERENCE_CHAMBER.md): the evidence note behind every Stage A result; test case per subsystem; next actions.
- [Nitrogen boundary](../ref/notes/NITROGEN_BOUNDARY.md): active-N boundary model, measurement access, Ga/N ratio.
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
