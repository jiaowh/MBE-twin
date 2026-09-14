# GaN/AlN MBE digital twin

This repository currently contains a reviewed engineering plan and a source library for a laptop-runnable MBE chamber twin. Simulation implementation and experimental validation are the next stages.

Start with [PHASE1_CHAMBER_PLAN.md](PHASE1_CHAMBER_PLAN.md): scope, accuracy requirements, justified accelerations, laptop performance gates, tool choices and implementation order.

- [Proposal and plan review](docs/PLAN_REVIEW.md): engineering gaps, unsupported assumptions and proposed slide wording.
- [Physics architecture](mbe_twin.md): equations, data contracts, observation models and verification cases.
- [Data and validation plan](docs/DATA_AND_VALIDATION_PLAN.md): measurements, calibration/holdout design and acceptance criteria.
- [Machine intake ledger](data/intake/machine_requirements.json): proposal targets and unresolved machine inputs, without invented defaults.
- [Reference library](ref/README.md): papers, manufacturer documents, solver manuals and annotated source records.

The original [PowerPoint proposal](MBE_Phase1_Proposal_v1.2.pptx) is preserved. Its engineering edits are captured in the review and revised Markdown plans; the PPTX itself has not been edited. The original Markdown drafts are in [ref/archive](ref/archive/).

Commercial solver access is optional. The immediate inputs needed are dimensioned drawings, selected component specifications, the wafer/template stack, calibration measurements and confirmed laptop hardware. Accuracy and runtime are qualification requirements, not achieved results.

The reference-integrity check can be rerun with Python and `pypdf`:

```powershell
python scripts/audit_references.py
```

It regenerates the combined source index and checks local hashes, file formats, PDF readability, Markdown links and planning JSON. It does not run or validate a physics model.
