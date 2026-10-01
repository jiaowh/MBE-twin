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
| Source-layout feasibility: clearances, shadowing, nitrogen adjustment (about 15 min) | `python scripts/layout_feasibility.py` | `data/runs/studies/layout_feasibility.json` |
| Layouts B and C at operating points the nitrogen feed, pumping and heater can supply, under combined uncertainty (about 20 min on the shared laptop with empty caches; keyed map files in `--out` are reused, and a file whose key does not match stops the run) | `python scripts/layout_comparison.py` (defaults: `--layouts B C --out results/layout_comparison_bc`) | `data/runs/studies/layout_comparison_bc.json`; the earlier six-layout record `layout_comparison.json` (6aca3b3) is superseded |
| Minimum active-N conversion for 1 / 0.5 / 0.25 um/h and the highest reachable rate, per layout, temperature, pumping speed and feed ceiling (reads the comparison record and its keyed map files; about 2 min) | `python scripts/nitrogen_rate_limits.py` | `data/runs/studies/nitrogen_rate_limits.json` |
| Radial resolution (39 / 77 / 153 radii) and ratio-profile check of the comparison's nominal state | `python scripts/layout_resolution_check.py` | `data/runs/studies/layout_resolution_check.json` |
| Provenance of the study records (source hashes against the git history) | `python scripts/record_provenance.py --check` | `data/runs/studies/PROVENANCE.md` |
| Heater zones: wafer temperature range at 740 C by zone count and bracketed holder parameters | `python scripts/heater_zones.py` | `results/heater_zones/manifest.json` |
| Wafer temperature sensor count and placement for 3-zone control | `python scripts/heater_sensors.py` | `results/heater_sensors/manifest.json` |
| Baseline versus candidate layouts: thickness half-range/mean from the chained models (8 combinations, two plates, 700 / 740 C) | `python scripts/wafer_outcome.py` | `results/wafer_outcome/manifest.json` |
| Nitrogen pointing tolerance: 5 mm aim scans at 55-65 deg per plate, then the worst case with the source axis tilted by up to +/-0.8 / +/-1.6 deg (reads the versioned scans; fails if any is missing; the L/r 19.7 record came from a separate `--plates 19.69` run) | `python scripts/nitrogen_aim_study.py --aspects A --offsets ... --angles 55 60 65 --out results/nitrogen_aim_fine_A` (offset lists in the records); `python scripts/nitrogen_aim_tolerance.py` | `data/runs/studies/nitrogen_aim_fine_*.json`, `nitrogen_aim_tolerance.json` |
| Beam attenuation by background N2 (estimate) | `python scripts/background_scattering.py` | (printed) |
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

## Run times

On the development laptop (4 WSL cores, serial SPARTA, four jobs in parallel):
- An R07 case at benchmark statistics takes about 30 min; the 11 A/s case takes about 80 min.
- A Ga run takes 15-65 min, depending on fill.
- Re-post-processing one Ga run takes a few minutes.

Runs made before 2026-09-29 (under `results/sparta_r07/`, with names such as `cal_*`, `conv_*`, `pred_*`) have no recorded configuration. They are superseded by the batches above and kept only as history.

Study records of 2026-10-01 (nitrogen scenarios and aim, growth window, heater zones and sensors, wafer outcome) are versioned as copies of their manifests in `data/runs/studies/<name>.json`; the scripts write to `results/<name>/manifest.json`, which git ignores.
