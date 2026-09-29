# Reproducing Stage A results

Every result quoted in [REFERENCE_CHAMBER.md](../ref/notes/REFERENCE_CHAMBER.md) and the README status table can be regenerated from a clean checkout with the commands below. Bulky solver output (SPARTA particle dumps, Elmer meshes) goes to `results/`, which git ignores. Compact summaries that back the quoted numbers are versioned under `data/runs/`. Each one holds the complete run configuration, the profiles and their uncertainties, the git commit, SHA-256 hashes of the source files that ran, and the SPARTA commit.

## Environment

- Python 3.11+ with numpy; tests also need pytest and scipy; the R07 digitizer needs PyMuPDF.
- Elmer 26.1 (see README) with `ELMER_HOME` set; SPARTA commit `e071055` built with `make serial` in WSL at `~/sparta/src/spa_serial`.
- Run everything from the repository root with `PYTHONPATH=src` (PowerShell: `$env:PYTHONPATH = "src"`).
- Python sources are kept with LF line endings on every checkout (`.gitattributes`), so the recorded source hashes match a fresh clone.

## Verification

| Claim | Command | Reference |
|---|---|---|
| Beam, crucible, metrics, manifest, SPARTA and Elmer checks | `python -m pytest -q` | Closed-form solutions, deterministic ring transmission, point-source slab propagation, SPARTA collisionless pipeline, Elmer V02 conduction and V03 radiation |
| Elmer diffuse-gray radiation (V03) | `python -m pytest -q tests/test_elmer.py` | Exact black-disk result and independent ring radiosity (`mbe_twin.radiation`); Elmer is 0.22-0.25 K (0.02 %) low, independent of mesh |

## Beam and crucible studies (free-molecular)

| Result | Command | Output |
|---|---|---|
| R07 fill-level, rate, tilt and distance comparisons | `python scripts/compare_r07.py` | `results/r07_comparison/manifest.json` |
| R14 code-to-code comparison | `python scripts/compare_r14.py` | `results/r14_comparison/manifest.json` |
| Knudsen regime of production Ga/Al cells | `python scripts/crucible_knudsen.py` | `results/crucible_knudsen/manifest.json` |
| Free-molecular fill-level sensitivity study (axis-normal and level melts) | `python scripts/fill_level_fm.py` | `results/fill_level_fm/manifest.json` |
| Aperture-plate active-N map sensitivity | `python scripts/nitrogen_plate.py` | `results/nitrogen_plate/manifest.json` |

## SPARTA (DSMC)

Named benchmark configurations live in `scripts/sparta_r07.py` (`BENCHMARKS`). A run refuses a non-empty directory. It writes `config.json` before SPARTA starts, and `--reuse DIR` post-processes from that file alone.

| Result | Command | Versioned summary |
|---|---|---|
| R07 benchmarks and numerical uncertainty (seeds, timestep, cells, diameter scan) | `python scripts/sparta_batch.py cases/sparta_r07/uq_batch.json` | `data/runs/sparta_r07/uq_batch/*.json` |
| One benchmark by name | `python scripts/sparta_r07.py r07_11 --out results/my_run` | (add `--record NAME`) |
| Ga source on the 200 mm wafer | `python scripts/sparta_batch.py cases/sparta_ga/ga_batch.json` | `data/runs/sparta_ga/ga_batch/*.json` |

Run times on the development laptop (4 WSL cores, serial SPARTA, four jobs in parallel): about 15 min for a 1 mm-cell R07 case, about 1 h at 0.6 mm cells, a few hours for the whole uncertainty batch.

Runs made before 2026-09-29 (under `results/sparta_r07/` with names such as `cal_*`, `conv_*`, `pred_*`) have no recorded configuration and are superseded by the batch above; they are kept only as history.
