# Project direction and end-of-day work audit, 2026-10-06

Scope: current HEAD `204cb6c`, including today's `602cedd`, `9bcae33` and `204cb6c`, against `22a46ed`. Date is Singapore time. This follows the earlier overnight audit; it includes the subsequent fixes, bootstrap results, wall-loss change and revised design direction. Production code and archived study results were not changed during this review.

## Findings

### P2: Extending a table can silently change its declared wall physics

`scripts/scattered_plume_tables.py:102-113` checks particle count, batches, plume temperature, layouts, speeds and aim, but does not check the newly introduced `wall_gamma` or `pump_wall_returned`. Lines 141-145 copy existing results while lines 170-172 label the output using the new command's wall settings.

Reproduced by extending `results/scattered_plume_tables_B-L_95mm_lowloss_s1/manifest.json` with `--gamma 1` and without `--pump`, retaining its layout, aim, speed and particle settings. The command succeeds; every factor is identical to the gamma=0.001, pumped source record, but the new record declares the default absorbing-wall physics. Diagnostic output: `results/audit_20261006_extend_mismatch/manifest.json`.

Reject mismatched wall settings before reusing entries; interpret omitted legacy settings as gamma=1 and no pump. Check the remaining geometry/physics dependencies as part of the same compatibility contract. This reproduction does not establish contamination of the committed low-loss result, which was generated from fresh runs.

### P2: The new low-loss table has an incorrect zero-pressure boundary

`scripts/scattered_plume_tables.py:131` initializes the zero-pressure factor to an all-ones profile for every gamma. That boundary is appropriate for absorbing walls, but returning walls send atoms back to the wafer even without gas or plume collisions. Interpolation between zero and the first pressure point therefore introduces an artificial pressure dependence.

A 20,000-particle diagnostic at B-L's 95 mm aim, with no gas or plume and a 4 m3/s pump, gave 2,006 wafer hits for gamma=1 and 5,719 for gamma=0.001, including 3,713 wall-returned hits. Both collision counts were zero. This is a boundary-condition diagnostic, not a converged radial table.

Compute the collisionless wall-return factor when gamma<1 instead of assigning one. The published 5.5-5.8 sccm working point lies above the first pressure interval, so this finding does not by itself overturn that result; it affects lower-flow use of the new tables.

### P2: Seed averaging can treat reused trajectories as independent samples

`scripts/average_scattered_seeds.py:64-69` checks distinct top-level seeds but explicitly excludes `extends` from compatibility checks. An extension's seed describes newly simulated entries, not inherited entries. Two extensions of the same parent can consequently be accepted as independent trials even when all their factors are identical copies.

Reproduced by extending the same completed low-loss seed record twice, with seeds 991 and 992 and otherwise matching settings, then averaging those two records. The average succeeds, advertises independent seeds, and reports zero spread. Artifacts: `results/audit_20261006_clone991/`, `results/audit_20261006_clone992/` and `results/audit_20261006_false_independence/`.

Reject extended records from independent-seed averaging until per-entry ancestry is tracked, or explicitly account for shared samples. The earlier audit records that today's headline constituent runs did not use `--extend`; this is a reproducible workflow defect, not evidence that their bootstrap is invalid.

### P2: The headline worst-case uniformity omits failing states

`scripts/realizable_controller.py:502-505` intentionally exports two different quantities: `worst_pct` over states that pass the joint gate, and `worst_valid_pct` over all valid states. README's current design summary describes the former as a worst case over the chosen grid without clearly stating this exclusion.

For the archived B-L averaged-table result at 710 C, rate monitor + BFM:

- Passing-state worst case: **0.5264%** half-range/mean.
- Share of grid states passing: **96.6637%**.
- All-valid-state worst case: **2.3014%**.
- Deep-fill subsets pass only **90.93%** and **93.19%** for the two Ga collision diameters.

At 720 C the corresponding values are 0.5833%, 99.9928% and 0.6359%. These are deterministic scenario-grid shares, not probabilities of production success.

Report passing-state spread, admission fraction and all-valid-state spread together. This matters when choosing 710 versus 720 C: the small improvement in the accepted-state optimum comes with a substantially worse failure tail. The gate need not change, but the product/design summary must expose the tradeoff.

## Direction and progress

The project has advanced from source and heater studies to a coupled representative-chamber GaN simulator with recipe execution, instrument-limited controllers, uncertainty grids and synthetic commissioning rehearsals. That is substantial software and numerical progress. It remains Stage A research: actual machine geometry, calibration data, independent wafer validation, agreed acceptance criteria and AlN growth kinetics are missing. A percentage-complete estimate would obscure these distinct gates.

Today's most valuable result is improved decision credibility: independent-seed averages and bootstrap reruns remove the apparent evidence for a precise uniformity ranking. The saved results support B-L 0.53% versus B-p 0.57% at 710 C, with table-noise standard deviations about 0.035 and 0.089 percentage points. The paired 5th-95th percentile interval spans zero. These uncertainties do not include uncertain physics or hardware.

B-L at +95 mm is a defensible provisional design-study baseline because the assumed nitrogen output is more plausible than B-p's eta=1 scenario. This is conditional on source manufacture, stable plasma operation, effective pumping and wall losses. The new low-wall-loss bracket could reopen B-p; it does not justify a final hardware selection. Keep +95 mm as a nominal modelling choice, with the documented aim-transfer approximation, rather than treating it as hardware acceptance.

The wall-loss result is useful sensitivity evidence, but "uniformity does not depend on it" is too general. Only a particular B-L geometry and controller were exercised, with two seeds. The controller multiplies every pointing state's direct attenuation by a shared nominal scattering factor (`realizable_controller.py:320-328`). When returned flux dominates, its dependence on pointing and real chamber/pump geometry needs checking before carrying the conclusion across layouts.

The R32-R41 evidence search identifies useful hardware and growth-quality questions. This review checked its role in the design argument, not the full texts or the physical transferability of every quoted literature result. Several notes still describe the pump change as awaiting a decision although it is now implemented. README's overview date is still 5 October. Update these status statements and the hardware request list alongside the design summary.

## Verification

- Recomputed bootstrap standard deviations from saved per-run values: agreement for both layouts and both temperatures.
- Checked all **108** controller-manifest hashes listed in the two new noise summaries: no mismatches.
- `scripts/record_provenance.py --check`: exit 0. Preserved the original tracked provenance document after the check; output is in `results/audit_20261006_provenance.txt`.
- Reproduced the two extension/averaging defects without new particle campaigns and checked the zero-pressure boundary directly with the tracker.
- Full test suite: **279 passed in 99.01 seconds**, using the existing local test dependencies. Access to those dependency folders required execution outside the sandbox; the test run completed successfully.
- Did not repeat multi-hour particle campaigns or the full bootstrap/controller ensemble. Verified saved outputs and targeted behavior instead.

The previous audit's four issues have substantive follow-up: actual averaged-table bootstraps, exclusion of unchanged layouts, fresh batch directories with child-status checks, and rejection of scattering overrides without matching aim tables. The new findings above concern remaining paths and the interpretation of results.

## Recommended next work

1. Fix the three reproducible workflow/boundary defects and add focused regression coverage. Qualify the headline uniformity with its admission fraction and failure tail.
2. Establish one current decision record: provisional B-L geometry, 710/720 C tradeoff, required instruments, assumptions, and explicit reopening conditions. Align hardware requests with it.
3. Prioritize source output/plate feasibility, pump and wall behavior, three-radius temperature sensing, mount/metrology repeatability, and material-quality requirements. These can change the decision more than another fine aim scan.
4. Use the integrated twin for campaign depletion and beam-flux recalibration cadence; test wall-return sensitivity across pointing states and B-p before claiming layout-independent behavior.
5. Once hardware and data are available, calibrate on designated wafers, validate on separate runs, and demonstrate improvement against an agreed baseline.
