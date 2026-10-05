# Reproducing Stage A results

This guide lists the command behind each result quoted in [REFERENCE_CHAMBER.md](../ref/notes/REFERENCE_CHAMBER.md), [NITROGEN_BOUNDARY.md](../ref/notes/NITROGEN_BOUNDARY.md) and the status table of the [developer guide](DEVELOPER.md). A result that is not listed here is not yet reproducible from this repository, and should not be quoted as if it were.

Bulky solver output (SPARTA particle dumps, Elmer meshes) goes to `results/`, which git ignores. Compact summaries behind the quoted DSMC numbers are versioned under `data/runs/`. Each summary holds:
- the complete run configuration and the profiles with their uncertainties;
- the git commit and SHA-256 hashes of the source files that ran;
- the SPARTA commit.

What "reproduce" means differs by method:
- Deterministic scripts (Elmer, view factors, Knudsen estimates) give the same numbers.
- Monte Carlo scripts with fixed seeds (`crucible.py`) give the same numbers on the same numpy version.
- SPARTA runs with a fixed seed repeat to within their stated statistical uncertainty. They are not guaranteed bit-identical across builds.

## Environment

- Python 3.11+ with numpy 2.0+; tests also need pytest and scipy; the R07 digitizer needs PyMuPDF.
- Elmer 26.1 (see README) with `ELMER_HOME` set. SPARTA commit `e071055`, built with `make serial` in WSL at `~/sparta/src/spa_serial`.
- Run every command from the repository root with `PYTHONPATH=src` (PowerShell: `$env:PYTHONPATH = "src"`). The flux-hold batch refers to earlier runs by paths relative to the root.
- Python sources keep LF line endings on every checkout (`.gitattributes`). Since 2026-09-30, source hashes are taken after normalizing CRLF to LF, and `config.json` also records `source_sha256_at_start`, the hashes of the code that wrote the inputs. Earlier manifests hashed raw bytes at the end of post-processing. Checked against the commits:
  - `uq_batch` records match commit `cef2a3b`.
  - `ga_batch` records matched `cef2a3b`, with two exceptions. `scripts/sparta_ga.py` and `src/mbe_twin/vapour.py` were CRLF on disk, so they match only after CRLF conversion. `src/mbe_twin/sparta.py` matches `0c2ea63`; the runs' inputs were written by the `cef2a3b` version, a difference below 1e-10 relative. These records have since been re-post-processed (below), so their manifests now hash the post-processing code of commit `cdd4d18`. The run inputs are unchanged.

## Batches: settings are frozen in the job files

Every job in `cases/**/*.json` lists all numerical settings explicitly (`--set ...`). They are taken from the archived record where one exists. Changing a script's defaults (for example the R07 benchmark statistics, raised on 2026-09-30) therefore cannot change what a job file reproduces.

The batch runner treats a job as complete only when its directory holds `summary.json`. It reports incomplete directories rather than skipping them, and exits with status 1 if any job failed or is incomplete. `--retry-incomplete` moves incomplete directories aside and reruns them.

| Result | Command | Versioned summaries |
|---|---|---|
| R07 first uncertainty pass (2e5 particles, 16000 sampling steps; noise ~0.02 per bin) | `python scripts/sparta_batch.py cases/sparta_r07/uq_batch.json` | `data/runs/sparta_r07/uq_batch/` (`3.5_cell07` failed and has no record) |
| R07 high-statistics benchmarks: seeds, timestep, cells, diameter 7 / 8 / 9 A | `python scripts/sparta_batch.py cases/sparta_r07/uq2_batch.json` | `data/runs/sparta_r07/uq2_batch/` |
| R07 diameter scan extension (8.5 / 10 / 11 A) | for each job in `cases/sparta_r07/uq2_dscan.json`: `python scripts/sparta_r07.py <args> --out results/uq2_batch/<name> --record uq2_batch/<name>` | `data/runs/sparta_r07/uq2_batch/3.5_d*.json` |
| Nitrogen: published plates (R13, R30), hole Knudsen number, geometry, free-molecular wafer maps (about 1 h) | `python scripts/nitrogen_plate_scenarios.py` | `results/nitrogen_plate_scenarios/manifest.json` |
| Nitrogen: aim offset and port angle per hole aspect (default grid, then extended grid) | `python scripts/nitrogen_aim_study.py`; `python scripts/nitrogen_aim_study.py --aspects 2.92 5.83 11.66 --offsets 60 75 90 105 120 135 150 --angles 40 45 50 55 60 65 --out results/nitrogen_aim_study_ext` | `results/nitrogen_aim_study*/manifest.json` |
| Growth window with centre-flux-held Ga maps | `python scripts/growth_window.py --held --aim results/nitrogen_aim_study/manifest.json results/nitrogen_aim_study_ext/manifest.json --out results/growth_window_held` | `data/runs/studies/growth_window_held.json` |
| Ga-rich growth window and thickness uniformity from Ga, N and temperature maps | `python scripts/growth_window.py --aim results/nitrogen_aim_study/manifest.json results/nitrogen_aim_study_ext/manifest.json` | `results/growth_window/manifest.json` |
| Source-layout feasibility: clearances certified over the continuous shutter motion, shadowing, nitrogen adjustment (about 6 min) | `python scripts/layout_feasibility.py --layouts B C B-p C-p B-L --out results/layout_feasibility_bc` | `data/runs/studies/layout_feasibility_bc.json` (the six-layout `layout_feasibility.json` is superseded) |
| Layouts B, C, B-p, C-p and B-L at operating points the nitrogen feed, pumping and heater can supply, under combined uncertainty (about 25 min on the shared laptop with empty caches; keyed map files in `--out` are reused, and a file whose key does not match stops the run) | `python scripts/layout_comparison.py` (defaults: `--layouts B C B-p C-p B-L --out results/layout_comparison_bc`) | `data/runs/studies/layout_comparison_bc.json`; the earlier six-layout record `layout_comparison.json` (6aca3b3) is superseded |
| The same with the plate-validity criterion relaxed to hole Kn >= 3 (the scenario behind B-p's 0.73 / 2.11 % at eta = 0.3, 4 m^3/s, 35 sccm; conditional on the hole-flow DSMC; about 3 min, reusing the maps) | `python scripts/layout_comparison.py --kn-valid 3 --maps results/layout_comparison_bc --out results/layout_comparison_bc_kn3` | `data/runs/studies/layout_comparison_bc_kn3.json` |
| Minimum active-N conversion for 1 / 0.5 / 0.25 um/h and the highest reachable rate, per layout, temperature, pumping speed and feed ceiling (reads the comparison record and its keyed map files; about 2 min) | `python scripts/nitrogen_rate_limits.py` | `data/runs/studies/nitrogen_rate_limits.json` |
| Radial resolution (39 / 77 / 153 radii) and ratio-profile check of the comparison's nominal state | `python scripts/layout_resolution_check.py` | `data/runs/studies/layout_resolution_check.json` |
| Active-N conversion inferred from published growth rates (joint geometry constraint; about 45 min) | `python scripts/nitrogen_output_evidence.py` | `data/runs/studies/nitrogen_output_evidence.json` |
| Aperture plates that stay free-molecular up to a given feed | `python scripts/nitrogen_plate_design.py` | `results/nitrogen_plate_design/manifest.json` |
| Aim and port angle at the operating pressure (three processes of two angles, then combine; about 1 h each) | `python scripts/nitrogen_aim_pressure.py --angles 40 46 --out results/nitrogen_aim_pressure_a` (and `50 55`, `60 65`); `python scripts/nitrogen_aim_pressure.py --combine results/nitrogen_aim_pressure_a results/nitrogen_aim_pressure_b results/nitrogen_aim_pressure_c --out results/nitrogen_aim_pressure` | `data/runs/studies/nitrogen_aim_pressure.json` |
| The same for the large plate | `--angles 46` and `--angles 65` with `--aspect 2.0 --plate-radius 0.03`, combined with `--aspect 2.0 --plate-radius 0.03 --eta 0.3 --speed 4 --feed-max 35` | `data/runs/studies/nitrogen_aim_bigplate.json` |
| Combined heater errors, mean and centre-pyrometer controllers, and Ga protocols with the per-state nitrogen balance for B-p, B and B-L (reads the comparison record and its keyed map files; about 3 min) | `python scripts/heater_robustness.py` | `data/runs/studies/heater_robustness.json` |
| Hole-scale DSMC (SPARTA in WSL, one worker, waits for the shared machine; about 30 min per Kn; `--reuse` re-analyses saved dumps) | `python scripts/sparta_hole.py` | `data/runs/studies/sparta_hole.json` |
| Hole DSMC discretization and boundary variants (half cell about 30 min, half timestep about 55 min, larger reservoir about 75 min per Kn), then their comparison with the base runs | `python scripts/sparta_hole.py --variant fine_cell --kn 100 3 0.3` (likewise `half_dt`, `big_reservoir`); `python scripts/sparta_hole.py --convergence` | `data/runs/studies/sparta_hole_<variant>.json`, `sparta_hole_convergence.json` |
| Operating point for the goals as uniform / as fast / as cold as possible: Pareto fronts per supply scenario (reads the comparison record and its keyed map files; about 10 min) | `python scripts/operating_optimum.py` | `data/runs/studies/operating_optimum.json` |
| Coldest temperature that keeps the growth window at each rate, with combined heater errors and a centre pyrometer (about 10 min) | `python scripts/operating_cold_limit.py` | `data/runs/studies/operating_cold_limit.json` |
| Provenance of the study records (source hashes against the git history) | `python scripts/record_provenance.py --check` | `data/runs/studies/PROVENANCE.md` |
| Heater zones: wafer temperature range at 740 C by zone count and bracketed holder parameters | `python scripts/heater_zones.py` | `results/heater_zones/manifest.json` |
| Wafer temperature sensor count and placement for 3-zone control | `python scripts/heater_sensors.py` | `results/heater_sensors/manifest.json` |
| Baseline versus candidate layouts: thickness half-range/mean from the chained models (8 combinations, two plates, 700 / 740 C) | `python scripts/wafer_outcome.py` | `results/wafer_outcome/manifest.json` |
| Nitrogen pointing tolerance: 5 mm aim scans at 55-65 deg per plate, then the worst case with the source axis tilted by up to +/-0.8 / +/-1.6 deg (reads the versioned scans; fails if any is missing; the L/r 19.7 record came from a separate `--plates 19.69` run) | `python scripts/nitrogen_aim_study.py --aspects A --offsets ... --angles 55 60 65 --out results/nitrogen_aim_fine_A` (offset lists in the records); `python scripts/nitrogen_aim_tolerance.py` | `data/runs/studies/nitrogen_aim_fine_*.json`, `nitrogen_aim_tolerance.json` |
| Beam attenuation by background N2 (estimate) | `python scripts/background_scattering.py` | (printed) |
| Where the scattered Ga and N atoms land, with the nitrogen plume (test-particle Monte Carlo, 12 x 1e6 atoms per case, about 2 h on one core) | `python scripts/scattered_redeposition.py --particles 1000000 --batches 12` | `data/runs/studies/scattered_redeposition.json` |
| Scattered-arrival factor tables for the comparison (N per layout, gamma 1 and 0.1; Ga). Run in parts in parallel (each about 2-3 h), then merged | `python scripts/scattered_tables.py --layouts B --ga-particles 16000 --out results/scattered_tables_part_N_B` (likewise B-p, B-L); `python scripts/scattered_tables.py --layouts B --n-particles 16000 --ga-particles 4000000 --out results/scattered_tables_part_Ga4M`; `python scripts/merge_scattered_tables.py --parts results/scattered_tables_part_N_B results/scattered_tables_part_N_B-p results/scattered_tables_part_N_B-L results/scattered_tables_part_Ga4M` | `data/runs/studies/scattered_tables.json` |
| Plume factor tables per pumping speed (one process per layout, about 3-4 h each) | `python scripts/scattered_plume_tables.py --layouts B-L --seed 20261007 --out results/scattered_plume_tables_B-L` (B: seed 20261005, B-p: 20261006) | intermediate: `results/scattered_plume_tables_<layout>/manifest.json` |
| Plume tables extended to bracket 35 sccm (2026-10-03 audit; one process per layout, about 1-2 h) | `python scripts/scattered_plume_tables.py --layouts B-L --seed 20261017 --extend results/scattered_plume_tables_B-L/manifest.json --out results/scattered_plume_tables_B-L_ext` (B: seed 20261015, B-p: 20261016) | `data/runs/studies/scattered_plume_tables_<layout>.json` |
| The comparison with scattered atoms (about 10 min each, reusing the maps) | `python scripts/layout_comparison.py --layouts B B-p B-L --scattered gas+plume --maps results/layout_comparison_bc --out results/layout_comparison_bc_sc_plume` (likewise `--scattered gas` to `_sc`, `gas-gamma0.1` to `_sc_gamma0.1`) | `data/runs/studies/layout_comparison_bc_sc*.json` |
| Downstream studies on a scattered variant (read that variant's comparison record) | `python scripts/operating_optimum.py --scattered gas+plume --out results/operating_optimum_sc_plume`; `python scripts/heater_robustness.py --scattered gas+plume --out results/heater_robustness_sc_plume`; `python scripts/operating_cold_limit.py --scattered gas+plume --pyrometer-bias B --t-max 790 --out results/operating_cold_limit_sc_plume_biasB` (B = 2, 3, 4, 5, 10); `python scripts/operating_cold_limit.py --scattered gas` (and gas-gamma0.1); `python scripts/nitrogen_rate_limits.py --record data/runs/studies/layout_comparison_bc_sc_plume.json --out results/nitrogen_rate_limits_sc_plume` | the matching `data/runs/studies/*_sc*.json`, `operating_cold_limit_*.json` records |
| Pyrometer-bias sensitivity on the direct-beam model | `python scripts/operating_cold_limit.py --pyrometer-bias 5 --t-max 790 --out results/operating_cold_limit_bias5` (and 10) | `data/runs/studies/operating_cold_limit_bias{5,10}.json` |
| Aims re-evaluated with scattered atoms (reuses the saved aim scans; seconds) | `python scripts/nitrogen_aim_pressure.py --combine results/nitrogen_aim_pressure_a results/nitrogen_aim_pressure_b results/nitrogen_aim_pressure_c --scattered gas+plume --factor-layout B-p --out results/nitrogen_aim_pressure_sc_plume`; the large plate likewise with `--aspect 2.0 --plate-radius 0.03 --eta 0.3 --speed 4 --feed-max 35 --factor-layout B-L` | `data/runs/studies/nitrogen_aim_{pressure,bigplate}_sc_plume.json` |
| Synthetic commissioning rehearsal for the nitrogen supply, with flow-dependent conversion and the throttle series (minutes) | `python scripts/commissioning_rehearsal.py` | `data/runs/studies/commissioning_rehearsal.json` |
| Synthetic rehearsal of the temperature and Ga calibrations (seconds) | `python scripts/temperature_ga_rehearsal.py` | `data/runs/studies/temperature_ga_rehearsal.json` |
| Nitrogen aim robustness (output profile, plate radius) | `python scripts/nitrogen_aim_robustness.py` | `results/nitrogen_aim_robustness/manifest.json` |
| R07 Bi + Bi2 against monatomic runs; diameter scans | `python scripts/summarize_bi2.py` | (printed) |
| R07 with Bi + Bi2 vapour (Kubaschewski fractions, x = 0.5 check, d scan at 3.5 A/s) | `python scripts/sparta_batch.py cases/sparta_r07/r07_bi2.json` | `data/runs/sparta_r07/r07_bi2/` |
| R07 tables, noise-corrected RMS, diameter interval | `python scripts/summarize_uq.py --dir data/runs/sparta_r07/uq2_batch` | (printed) |
| Ga on 200 mm at 46 deg: fills, diameter bracket, fixed T, 0.5 um/h, seed / cell / slab checks | `python scripts/sparta_batch.py cases/sparta_ga/ga_batch.json` | `data/runs/sparta_ga/ga_batch/` |
| Ga port angle per fill | `python scripts/sparta_batch.py cases/sparta_ga/ga_angle.json` | `data/runs/sparta_ga/ga_angle/` |
| Ga numerical checks at angle optima (one setting changed per check) | `python scripts/sparta_batch.py cases/sparta_ga/ga_checks.json` | `data/runs/sparta_ga/ga_checks/` |
| Ga at held centre Ga flux (first correction and iterations to +/-1.5 %; exit 1 unless every state is held; table: `python scripts/summarize_flux_hold.py`) | `python scripts/ga_flux_hold.py --iterate` (after `ga_batch` and `ga_angle`; runs `ga_dsmchold.json`, then generated `cases/sparta_ga/iterations/ga_dsmchold.json`) | `data/runs/sparta_ga/ga_dsmchold/` |
| Any single run by name | `python scripts/sparta_r07.py r07_11 --out results/my_run`; `python scripts/sparta_ga.py --fill 0.12 --diameter 8e-10 --angle 58` | (add `--record NAME`) |

**Post-processing only.** `python scripts/sparta_ga.py --reuse results/<batch>/<name> --record <batch>/<name>` recomputes a Ga summary from the stored dumps and `config.json`. On 2026-09-30 all Ga records were regenerated this way with the revised uniformity estimator (next section). The dumps and inputs were not rerun.

## Uniformity estimator (Ga study)

| Result | Command | Output |
|---|---|---|
| Estimator check against dense free-molecular profiles, noise-free and with each run's recorded noise | `python scripts/check_uniformity_estimator.py` | printed table; writes `tests/data/fm_profile_120mm_46deg.json` |
| README figures (schematics, and plots from the `data/runs/` records) | `python scripts/make_readme_figures.py` | `docs/figures/*.png` |

## Free-molecular and analytical studies

| Result | Command | Output |
|---|---|---|
| R07 fill-level, rate, tilt and distance comparisons | `python scripts/compare_r07.py` | `results/r07_comparison/manifest.json` |
| R14 code-to-code comparison | `python scripts/compare_r14.py` | `results/r14_comparison/manifest.json` |
| Knudsen regime of production Ga/Al cells | `python scripts/crucible_knudsen.py` | `results/crucible_knudsen/manifest.json` |
| Free-molecular fill-level sensitivity (axis-normal and level melts) | `python scripts/fill_level_fm.py` | `results/fill_level_fm/manifest.json` |
| Aperture-plate active-N map sensitivity | `python scripts/nitrogen_plate.py` (about 1 h) | `results/nitrogen_plate/manifest.json` |
| Hole Knudsen number of the N aperture plate | `python scripts/nitrogen_knudsen.py` | (printed) |
| Ga/N ratio spread across the wafer | `python scripts/ga_n_ratio.py` (reads `data/runs/sparta_ga/ga_batch/`) | (printed) |

## Verification

| Claim | Command | Reference |
|---|---|---|
| Beam, crucible, metrics, manifest, estimator, scripts, SPARTA and Elmer checks | `python -m pytest -q` | Closed-form solutions, deterministic ring transmission, point-source slab propagation, stored dense profile, SPARTA collisionless pipeline, Elmer V02 conduction and V03 radiation |
| Elmer diffuse-gray radiation (V03) | `python -m pytest -q tests/test_elmer.py` | Exact black-disk result and independent ring radiosity (`mbe_twin.radiation`); Elmer is 0.22-0.25 K (0.02 %) low, independent of mesh |

## Integrated twin

Chamber definitions (`cases/twin/`, committed) are built from the gas+plume comparison's map caches in `results/layout_comparison_bc` (rebuild them with `scripts/layout_comparison.py --scattered gas+plume` if absent):

```bash
PYTHONPATH=src python scripts/twin_chamber.py                              # nominal truth
PYTHONPATH=src python scripts/twin_chamber.py --truth-fill 120             # also --truth-fill 40
PYTHONPATH=src python scripts/twin_chamber.py --truth-tilt flange 0.8 0    # also direction 180
PYTHONPATH=src python scripts/twin_run.py --chamber cases/twin/chamber_B-L_720C.json   # one per definition
PYTHONPATH=src python scripts/twin_run.py --pyrometer-bias 2                # and -2
```

Realizable recipe: `--recipe cases/twin/gan_1um_720C_realizable.json` on the same definitions (also `--bfm-error 0.02` and `--rate-error 0.01` on the 120 mm one); heater margin: `scripts/twin_chamber.py --heater-design-limit 1425`, then the frozen recipe at pyrometer bias -2 / 0 / +2 K. `cases/twin/twin_runs.sh` lists the full set. Each run takes 12-30 s. The records are `data/runs/studies/twin_gan_1um_720C_B-L_720C*.json`; the figure is `make_readme_figures.py` (`twin`).

## Realizable controller and heater margin (2026-10-05)

```bash
PYTHONPATH=src python scripts/realizable_controller.py                              # about 15 min
PYTHONPATH=src python scripts/realizable_controller.py --heater-design-limit 1425 \
    --out results/realizable_controller_sc_plume_heater1425
PYTHONPATH=src python scripts/realizable_controller.py --t-min 720 --t-max 720 --rate-error R --bfm-error B   # error budget
PYTHONPATH=src python scripts/heater_margin.py                                      # about 5 min
```

Records: `data/runs/studies/realizable_controller_sc_plume*.json`, `heater_margin.json`. The joint-gate reruns of 2026-10-05 (operating_optimum*, operating_cold_limit*) used the commands above in this file unchanged; `cases/rerun_gate_2026-10-05.sh` lists them.

## Uniformity levers (2026-10-05)

Worst-case drivers: `realizable_controller.py ... --dump-t T` then `python scripts/worst_case_drivers.py <out>/states_<layout>_<T>C.npz`. Residual-pointing sweep: `cases/reaim_sweep_2026-10-05.sh`. Aim maps: `python scripts/nitrogen_aim_operating.py --layout B-L --aims 75 80 85 90 95 100 105` (and `--aims 92.5 97.5 --out results/aim_operating_fine`; B-p 87.5-107.5), then `cases/aim_sweep_2026-10-05.sh`. Multi-spot heater: `cases/multispot_sweep_2026-10-05.sh` (about 20 min per temperature), and the 690-710 C run `realizable_controller.py --t-min 690 --t-max 710 --heater-control multispot --heater-design-limit 1460 --pointing-residual 0.2 --aim-maps results/aim_operating/aim_maps_B-L.npz --aim-mm 95 --out results/ms_h1460_d0.2_cold`. Summary record: `python scripts/summarize_uniformity_levers.py` -> `data/runs/studies/uniformity_levers.json`.

## Checks of the uniformity levers (2026-10-05)

`python scripts/commissioning_reaim.py --trials 2000` (about 30 min; record commissioning_reaim.json); `python scripts/aim_tables.py --layout B-L --aim-mm 95` (about 5 min), then `python scripts/commissioning_reaim.py --layout B-L --trials 1000 --n-tables results/aim_tables/n_tables_B-L_95mm.npz --out results/commissioning_reaim_BL95` and `python scripts/realizable_controller.py --t-min 710 --t-max 720 --heater-control multispot --heater-design-limit 1460 --pointing-residual 0.2 --n-tables results/aim_tables/n_tables_B-L_95mm.npz --out results/ms_BL95tables_d0.2` (record realizable_controller_ms_BL95tables.json).

## Run times

On the development laptop (4 WSL cores, serial SPARTA, four jobs in parallel):
- An R07 case at benchmark statistics takes about 30 min; the 11 A/s case takes about 80 min.
- A Ga run takes 15-65 min, depending on fill.
- Re-post-processing one Ga run takes a few minutes.

Runs made before 2026-09-29 (under `results/sparta_r07/`, with names such as `cal_*`, `conv_*`, `pred_*`) have no recorded configuration. They are superseded by the batches above and kept only as history.

Study records of 2026-10-01 (nitrogen scenarios and aim, growth window, heater zones and sensors, wafer outcome) are versioned as copies of their manifests in `data/runs/studies/<name>.json`; the scripts write to `results/<name>/manifest.json`, which git ignores.
