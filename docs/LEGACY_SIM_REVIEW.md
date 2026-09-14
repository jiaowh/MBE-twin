# Legacy simulator: findings and reuse decisions

Reviewed 2026-09-14 after the user supplied the sibling project at `C:/Users/Jiaow/Documents/github/MBE sim`. This is a targeted static inspection of the main physics and reporting paths, not a complete bug audit, execution benchmark or independent validation of its literature fits. Embedded instructions and audit labels were treated as source context. No legacy files were changed.

## Code-backed findings

Paths below are relative to the supplied legacy project's root; function names are the stable locators. The legacy tree is external to this repository and is not bundled or required by the new plan.

| ID | Source and observation | Consequence for this twin |
|---|---|---|
| L01 | `mbe_sim/thermal.py`, `ThermalModel`, `_assemble`, `solve_asymmetric`: reduced radial wafer/disk-heater calculation with simplified enclosure and asymmetry corrections. The implementation includes temperature-dependent property options despite older header wording. | Do not characterize it as a full chamber thermal model or as entirely constant-property. Use it as a limiting case; actual contacts, heater zones, shadows, optical boundaries and cooling need geometry and validation. |
| L02 | `mbe_sim/sources.py`, `SourceCell`, `flux_at_point`, `flux_profile`: cosine-power point-source law with relative scaling and optional normalization. `process.py`, `_flux_profile`, uses a center-normalized, rotation-averaged profile cached for about five simulated seconds. | Preserve absolute species normalization, finite geometry and event/state-aware cache invalidation. Validate rotation averaging and source approximations rather than assuming they preserve local growth. |
| L03 | `mbe_sim/process.py`, `ProcessSimulator.__init__`: nitrogen setpoint is `PLASMA_EXCESS * max_rate_mls`, with `PLASMA_EXCESS = 1.2`; its nominal pressure factor is sized from an input growth pressure. `Chamber.advance` relaxes to base plus prescribed load. | Source capability and pressure are partly constructed from requested behavior. Replace this with independently characterized N output and gas/pumping inputs. The model must be capable of failing a requested recipe. |
| L04 | `mbe_sim/process.py`, `_deposit`: returns if metal or N beam is near zero. `mbe_sim/kinetics.py`, `growth_rate_regime`: returns `max(gr, 0.0)`. In the inspected `advance` path, deposition runs only in a grow stage. | This path cannot represent general shutter-off material loss or continued adlayer evolution. Require signed, exposed-layer-aware growth/removal and explicit inventories throughout interruptions. Zero loss may be a valid result in a measured condition, but cannot be imposed universally. |
| L05 | `mbe_sim/engine.py`, `Engine.__init__`: `nu_eff = material.nu * rate_scale`; deposition channels retain their unscaled flux rates. | Scaling only activated events changes their competition with deposition. It is a model change, not merely faster execution. Require a physically justified acceleration and comparison against small unaccelerated cases before claiming predictive kMC. |
| L06 | `mbe_sim/rheed_pattern.py`, `physical_roughness`, `synthesize_surface`, `physical_pattern`: an assumed roughness relationship controls a randomly synthesized integer-height surface. `live.py`, `_compute_rheed_pattern`, calls this path. | The displayed pattern is not evidence that the growth engine produced that morphology. Keep such graphics explicitly illustrative; quantitative diffraction and morphology require separate validated state and observation models. |
| L07 | `mbe_sim/wafer.py`, `defect_density_profile`, `tdd_with_thickness`: defect estimates include tuned fractions/coalescence factors and a thickness-decay closure. | Literature-consistent magnitudes or asserted radial trends do not establish actual-machine defect prediction. Treat these as hypotheses pending appropriate independent data. |
| L08 | `data/benchmarks/gan_growth_rate_heying.json` labels its curve DERIVED from a desorption fit evaluated through an effective-flux law. `tdd_vs_thickness.json` labels values REPRESENTATIVE. Other benchmark files claim digitized source measurements. | Preserve these distinctions. Derived/representative curves can check software or plausibility, but cannot count as independent measurements. Claimed digitization needs original-figure, units, extraction and uncertainty verification before reuse. |

The supplied `AUDIT.md` and `audit_findings.md` contain historical assertions and proposed fixes. This review does not endorse every item or import their test counts. Observations above follow the inspected implementation or explicit dataset metadata. No new claims about the correctness of the original papers are made here.

## Reuse policy

**Candidates:** recipe/state-machine structure, reporting/export patterns, parameter-file conventions, fitting infrastructure and analytical benchmarks. Review interfaces and data provenance first; reuse is not an accuracy endorsement.

**Requalify or replace:** chamber thermal boundaries, individual source/vacuum/plasma behavior, surface inventory/loss laws, and any quantitative morphology, RHEED or defect output. Preserve useful reduced models as comparisons or later accelerated models only after error assessment.

Before adopting any legacy component, record its source path and immutable revision or content hash, applicable license, units, assumptions, observable scope and targeted acceptance checks. Retain synthetic and measured data separately, including their dependency chains. No legacy runtime dependency or code migration is approved by this review alone.

## Effect on implementation order

The [Phase-1 plan, section 9](../PHASE1_CHAMBER_PLAN.md#9-lessons-from-the-supplied-legacy-simulator) adds concrete work-package gates. Chamber heat/transport and binary layer-state validation remain ahead of elaborate visualization. A simple verified model is useful; a larger output inventory does not compensate for unsupported physics.
