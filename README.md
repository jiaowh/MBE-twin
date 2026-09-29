# GaN/AlN MBE digital twin

This repository holds the engineering plan, the source library and the first simulation code (Stage A) for a laptop-runnable MBE chamber twin. The proposed machine is not built; the code runs on a representative 200 mm chamber and is checked subsystem by subsystem against published cases. No result here is a validated prediction for the proposed machine.

| Area | Status (2026-09-29) |
|---|---|
| Direct beam and free-molecular crucible emission | Implemented; verified against closed-form and deterministic references; reproduces R07's measured fill-level profiles (Bi) |
| Collisional crucible (SPARTA DSMC) | One fitted parameter (Bi hard-sphere diameter, 6.0-10.8 A) matches R07's profile shapes at 0.35-11 A/s to within the current statistical noise (about 0.02-0.04 RMS; free-molecular 0.04-0.20); absolute centre rates 7-15 % low; high-statistics repeat running |
| Production Ga transport (200 mm, level melt) | Sensitivity study: collisional (DSMC) range/mean at 46 deg grows from 2.2-2.3 % (40 mm recess) to 7.9-11.3 % (120 mm) over an unsourced Ga diameter bracket; numerical uncertainty about 0.2-0.4 points; not a thickness prediction |
| Heater and wafer thermal (Elmer) | Conduction (V02) and diffuse-gray radiation (V03) verified; R03 heater reproduction not started |
| Nitrogen, vacuum, growth chemistry | Planned ([nitrogen boundary](ref/notes/NITROGEN_BOUNDARY.md)); not implemented |
| Integrated chamber twin | Not implemented |

How to reproduce each result: [docs/REPRODUCE.md](docs/REPRODUCE.md).

Start with [PHASE1_CHAMBER_PLAN.md](PHASE1_CHAMBER_PLAN.md): scope, accuracy requirements, justified accelerations, laptop performance gates, tool choices and implementation order.

- [Proposal and plan review](docs/PLAN_REVIEW.md): engineering gaps, unsupported assumptions and proposed slide wording.
- [Physics architecture](mbe_twin.md): equations, data contracts, observation models and verification cases.
- [Data and validation plan](docs/DATA_AND_VALIDATION_PLAN.md): measurements, calibration/holdout design and acceptance criteria.
- [Machine intake ledger](data/intake/machine_requirements.json): proposal targets and unresolved machine inputs, without invented defaults.
- [Representative chamber](ref/notes/REFERENCE_CHAMBER.md): because the proposed machine is not built, the first work uses a 200 mm plasma-GaN chamber envelope (RIBER MBE 49 GaN / Veeco GEN200 class), checked subsystem by subsystem against published simulation-versus-measurement cases.
- [Reference library](ref/README.md): papers, manufacturer documents, solver manuals and annotated source records.

The original [PowerPoint proposal](MBE_Phase1_Proposal_v1.2.pptx) is preserved. Its engineering edits are captured in the review and revised Markdown plans; the PPTX itself has not been edited. The original Markdown drafts are in [ref/archive](ref/archive/).

Commercial solver access is optional. For Stage A, the published test cases R03, R07 and R14 are in hand; R04, R05 and the RIBER MBE 49 technical PDF are still wanted. The proposed machine later needs dimensioned drawings, selected component specifications, the template stack and calibration measurements. Accuracy and runtime are qualification requirements, not achieved results.

## Code (Stage A, started 2026-09-28)

`src/mbe_twin` holds the first implementation slice: SI unit conversions, a direct-beam flux model (finite effusion apertures, cos^n emission, shutter shadowing, wafer rotation and dose), a free-molecular crucible emission model (`crucible.py`, verified against Clausing transmission), area-weighted uniformity metrics and a run manifest. `vapour.py` holds sourced Ga/Al vapour-pressure equations (Alcock 1984), and `scripts/crucible_knudsen.py` estimates the in-crucible collision regime at production rates against R07's criterion. `sparta.py` and `scripts/sparta_r07.py` run a collisional (DSMC) crucible model with SPARTA inside WSL, calibrated on R07's 3.5 A/s profile and tested on its 0.35 and 11 A/s profiles; `sparta_source.py` and `scripts/sparta_ga.py` extend it to a level melt in a tilted crucible and transport onto the rotating 200 mm wafer. `scripts/fill_level_fm.py` is the free-molecular fill-level sensitivity study. `radiation.py` holds the coaxial-disk radiation reference for the Elmer V03 benchmark. `scripts/compare_r14.py` runs the code-to-code comparison with the 8-inch layout study R14. `scripts/digitize_r07.py` and `scripts/compare_r07.py` digitize R07's measured profiles and compare them with the crucible model. It needs Python 3.11+ with numpy; the tests also need pytest and scipy, and the digitizer needs PyMuPDF.

Elmer FEM is an external solver, pinned to the rel26.1 Windows build (`ElmerFEM-gui-nompi-Windows-AMD64-rel26.1.zip`; banner "Version 9.0, compiled 2026-01-20"). Set `ELMER_HOME` to the unpacked folder that contains `bin/`. `src/mbe_twin/elmer.py` runs cases, and `cases/verification/elmer_v02_slab` is its conduction benchmark; the Elmer test is skipped when Elmer is absent.

SPARTA (DSMC) is an external solver run inside WSL (Ubuntu 24.04): `git clone https://github.com/sparta/sparta ~/sparta`, check out commit `e071055`, then `cd ~/sparta/src && make serial`. `src/mbe_twin/sparta.py` calls `~/sparta/src/spa_serial` through `wsl.exe`; the SPARTA test is skipped when it is absent.

```powershell
python -m pytest -q
$env:PYTHONPATH = "src"; python scripts/stage_a_beam_scan.py
```

The tests check the model against closed-form solutions: point and finite-disk sources, particle conservation, shutter shadows and rotation symmetry. The scan compares source layouts for a 200 mm wafer and writes to `results/`, which is not tracked by git. Its outputs are representative-chamber design comparisons, not predictions for the proposed machine.

## Reference audit

The reference-integrity check can be rerun with Python and `pypdf`:

```powershell
python scripts/audit_references.py
```

It regenerates the combined source index and checks local hashes, file formats, PDF readability, Markdown links and planning JSON. It does not run or validate a physics model.
