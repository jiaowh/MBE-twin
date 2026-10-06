# Audit of the overnight scattered-table work

Audited commits: `602cedd` and `9bcae33`, against `22a46ed`.

The archived averaging arithmetic and quoted main controller results check out. The remaining issues concern the strength of the statistical conclusions, misleading summary rows, and safeguards in the new command-line workflow. No production code or archived results were changed during this audit.

## Findings

### P2: The averaged-result uncertainties and convergence claim are not established

Locations: `docs/LAYOUT_COMPARISON.md:700-701`, `:726`, `:731`; `scripts/summarize_scatter_noise.py:68-76`.

The stated approximately 0.04 and 0.07 percentage-point uncertainties are numerically the single-table worst-case standard deviations divided by sqrt(10). That estimates uncertainty in the mean of the single-table worst cases. The reported result instead evaluates the controller on the mean factor table. Those are different estimators: the controller is nonlinear, selects a worst state, and changes the set of passing states with the table (`realizable_controller.py:471-480`). No bootstrap of averaged tables, repeated independent averaged-table estimates, or local sensitivity validation is recorded.

The quoted scales can be retained as heuristic estimates if labelled that way. They do not establish convergence, equivalence, or the categorical assertion that B-L is no worse. Agreement with an artificially flat factor profile is also not a convergence test of the physical profile. The current evidence supports saying that these point estimates do not resolve a layout ranking. Likewise, the aim scan is conditional on transferring the 95 mm factor table to other aims, as section 14 itself acknowledges.

Recommended follow-up: resample the existing seed tables, average each resample, and rerun the controller, recording both worst-case thickness and admission fraction. This needs controller evaluations, not another overnight Monte Carlo campaign. Assess uncertainty in the layout difference and the admission margin before strengthening the conclusions.

### P2: Summary records count unchanged layouts as independent noise trials

Location: `scripts/summarize_scatter_noise.py:58-76`.

Each controller invocation evaluates both layouts, while `--n-tables` and `--n-scatter` replace only the selected layout. The summarizer nevertheless aggregates every output row as a seed trial. Consequently:

- `scatter_noise_BL95.json` reports ten B-p trials with zero standard deviation; all ten actually reuse the same old B-p table.
- `scatter_noise_Bp.json` reports ten B-L trials with zero standard deviation; all ten reuse the same old B-L table.
- The unchanged layout is also included under the averaged, flat, and aim-scan labels, even though those interventions were not applied to it.

The prose currently selects the intended layout, so this does not invalidate the headline numbers. It does make the machine-readable results misleading and unsafe for downstream automated comparisons. Restrict summaries to the layout actually changed, or explicitly label unchanged rows as controls and exclude them from noise statistics.

### P2: The reproduction script can archive stale results after a failed run

Locations: `cases/scatter_seeds_2026-10-06.sh:22-24`, `:53-67`.

The `run` function ends a failed Python command with a successful `echo "FAILED ..."`. There is no failure propagation from the background jobs, and the script proceeds to summarize and copy manifests from persistent output directories. If a controller fails while an older manifest remains, the old result can be summarized and archived, followed by an `all done` message. Averaging and summary commands are not checked either.

Track and check every child process status, return a nonzero status on failure, check sequential commands, and publish only after all required outputs succeed. Fresh run directories would avoid confusing previous results with new ones. Merely adding `set -e` is insufficient while the failure branch returns success and background statuses are not checked.

### P2: Scattering overrides can be silently ignored without matching aim tables

Locations: `scripts/realizable_controller.py:248-249`, `:274-294`, `:528-529`.

The new scattering override is applied only inside the loop over `args.n_tables`. Supplying `--n-scatter` without `--n-tables` therefore runs the original tables while recording the supplied scattering files in the manifest. The same applies to `--scatter-flat` and `--scatter-from-aim` when accompanied by `--n-scatter` but no aim tables. Unmatched layouts are likewise not overridden.

Require appropriate aim tables and validate which supplied overrides were consumed. The overnight commands do supply the needed tables, so this is a workflow defect rather than an explanation for their numerical results.

## Independently checked

- Recomputed every factor-array mean in the three archived averaged records from the local constituent manifests: agreement to absolute tolerance 1e-14. The runs use distinct seeds and none uses `--extend`.
- Verified every constituent controller manifest against the SHA-256 stored in the two noise summaries. Also verified their source, aim-table and explicit scattering-table dependency hashes against the local files: no mismatches.
- Ran `scripts/record_provenance.py --check`: passed, without changing the tracked provenance document.
- Ran the full test suite with the existing test dependencies: **274 passed in 88.87 seconds**, including Elmer. The previously reported three Elmer failures did not recur in this execution context.
- Read the raw averaged-controller outputs: B-L is 0.526372% at 710 C and 0.583292% at 720 C; B-p is 0.566069% and 0.621966%.
- B-p's 710 C joint fraction is 95.000457% without fill tracking and 96.794798% with it. Thus "exactly 95.0%" is rounded, but the practical lack of margin is real.
- Rebuilt the B-p average excluding seed 10 as a sensitivity diagnostic, and reran the 710 C controller with otherwise identical settings. Its worst case is 0.512680%, versus 0.566069% with all ten seeds: seed 10 moves it by 0.053390 percentage points. This supports keeping and investigating that seed; it is not grounds for discarding it. The message's 0.52% exclusion figure should be approximately 0.51% for this nine-seed rerun.

Diagnostic rerun artifacts are in `tmp/overnight_Bp_leave10/` and `tmp/overnight_ctl_Bp_leave10/`. These are audit outputs, not replacements for the archived ten-seed results.

This audit did not rerun the multi-hour particle simulations or estimate a bootstrap confidence interval. The headline numbers are verified against the saved run outputs; the stronger statistical claims remain unverified.
