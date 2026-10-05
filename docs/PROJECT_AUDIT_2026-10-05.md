# Project audit — 5 October 2026

**Verdict:** the representative-chamber studies remain useful for comparing designs, but the evidence does not yet establish that a temperature-based controller can maintain the proposed 1 µm/h, 720 °C operating point. The saved calculations reproduce. The main problem is the information supplied to the simulated controller. Two additional issues affect operating-point acceptance and provenance checking.

Reviewed physics/study code at `1a40ba0`, with the rewritten README committed as `226d8a8` during the audit. The intervening commit changes only the README. New untracked integration modules and `tests/test_twin.py` were being added during the review; they were inspected briefly but are **not qualified by this audit**. The test run explicitly selected the tracked test files. This report does not change model code, saved scientific results or design recommendations.

## Findings

### 1. High — the temperature-based gallium controller also receives the true uncertain beam maps

Locations: [operating_optimum.py](../scripts/operating_optimum.py#L102), particularly lines 117–120; [heater_robustness.py](../scripts/heater_robustness.py#L198); [operating_cold_limit.py](../scripts/operating_cold_limit.py#L112).

The temperature-corrected protocol computes the lower and upper gallium limits separately for every uncertain case, using that case's full nitrogen map and gallium shape. It then places the gallium supply at the middle of that case's window. Only the temperature map is replaced by a uniform temperature inferred from the reading.

Consequently, the controller knows the effects of nitrogen misalignment, crucible fill, assumed gallium collision diameter and pressure on the spatial maps. These inputs are part of the uncertainty ensemble; they are not observations from the centre pyrometer. A calibration could supply some of this information, but a separate, effectively exact spatial calibration for each uncertain state is a stronger assumption than the documented temperature-based correction.

**Numerical check.** At 1 µm/h and 720 °C, with scattered atoms and the plume, the current implementation reproduced these saved values exactly:

| Scenario | Cases in the growth window | Worst thickness half-range/mean |
|---|---:|---:|
| B-p; nitrogen conversion 1.0; pumping 2 m³/s | 96.192% | 1.532013% |
| B-L; nitrogen conversion 0.3; pumping 4 m³/s | 97.311% | 1.525686% |

Both had 100% model/rate validity, so their joint valid-and-in-window fractions equal the window fractions above.

A diagnostic calculation kept the controller's spatial calibration at nominal nitrogen pointing and the 70 mm / 8 Å gallium case. It still granted the controller exact knowledge of the actual centre nitrogen flux and pressure, retained the same temperature readings, and used the actual perturbed maps to evaluate growth. The in-window shares fell to **88.359% for B-p and 86.181% for B-L**. This is an illustrative sensitivity check, not a proposed replacement controller or a prediction of manufacturing yield. It demonstrates that the additional map knowledge materially affects the claimed robustness.

At the same nominal zero-bias temperature reading, the current implementation also chooses source settings spanning about 5.4–5.7% for B-p and 6.3–6.6% for B-L across the uncertain beam cases, depending on the droplet law. A temperature-only lookup cannot select among these without additional calibration or observations.

**Impact:** the cold-temperature limit, claimed 95% compliance and approximately 3 °C equivalent calibration budget are conditional on this additional knowledge. The working point may still be achievable, but the existing study does not demonstrate it with the stated observations. The rewritten README carries forward the operating-point claim and should qualify this assumption too.

**Required correction:** define what the controller can observe and what is calibrated in advance. Freeze the fitted calibration before evaluating uncertain or held-out cases. If fill, pressure, flux or alignment measurements are available, provide them explicitly with errors. Keep the present calculation as a bound with known beam maps, and rerun the cold-limit and calibration-budget studies with the realizable controller.

### 2. Medium — separate 95% checks admit cases that fail the documented joint requirement

Locations: [operating_cold_limit.py](../scripts/operating_cold_limit.py#L118) and [operating_optimum.py](../scripts/operating_optimum.py#L209). The stated requirement is in [LAYOUT_COMPARISON.md](LAYOUT_COMPARISON.md#L298).

The implementation accepts an operating point when both `mean(valid) >= 0.95` and `mean(in_window) >= 0.95`. The documentation requires at least 95% of cases to satisfy both conditions. If the failing sets differ, the current tests can accept a joint fraction as low as 90%.

**This occurs in a recorded result.** The direct-beam cold-limit study accepts B-L at 1.25 µm/h, 740 °C, conversion 0.3, pumping 4 m³/s and a 35 sccm feed cap. Recalculation gave:

| Check | Fraction |
|---|---:|
| Model/rate valid | 97.7284% |
| In the growth window | 95.1303% |
| Both | **92.8587%** |

This reproduces the separate fractions stored in `operating_cold_limit.json`, but the accepted point fails the documented joint 95% requirement. It is the saved coldest pyrometer-controlled point for that direct-beam scenario, rather than only an unused intermediate calculation.

The two 720 °C gas-plus-plume cases checked in finding 1 have validity of 100%, so this particular logic error does not invalidate those two points. Their controller-information issue remains separate.

**Required correction:** record and gate on `mean(valid & (margin >= 0))`, retaining the separate fractions for diagnosis. Add a test with different invalid and out-of-window cases, regenerate the operating fronts and cold-limit records, and update affected tables. Keep the existing heater-temperature condition explicit.

### 3. Medium — the provenance checker omits the saved gallium-result dependencies

Locations: [record_provenance.py](../scripts/record_provenance.py#L148) and [layout_comparison.py](../scripts/layout_comparison.py#L823).

The layout comparison records the hashes of the gallium DSMC summaries it reads under `inputs.ga_records_sha256`. The provenance checker expands the scattered-gas and plume input hashes, but does not expand this gallium field. It can therefore report no unreviewed mismatch after a consumed gallium result changes.

Across the 61 study records, the audit found **30 recorded gallium dependency references omitted from the checker**. An independent hash check found that all 30 currently match their files. This is a missing guard, not evidence that existing gallium results are stale.

**Required correction:** include `ga_records_sha256` in dependency expansion, resolving its paths under `data/runs/sparta_ga/`, and test that a changed or missing gallium summary is reported. Downstream studies that reload those summaries should also verify the parent record's hashes before using them.

## What checked out

- **237 tests passed.** The three failures were all Elmer integration checks: Windows Application Control blocked `ElmerSolver.exe` with `WinError 4551` before it ran. A focused rerun confirmed the same cause. This audit does not provide a fresh Elmer numerical result.
- The two selected 720 °C calculations reproduced the saved growth-window shares and worst thickness values exactly, using saved beam maps and freshly solved combined heater states.
- The earlier continuous shutter-motion bounds, actual-growth-rate validity filter, plume table coverage checks and version-pinned provenance notes are present. Their tracked regression tests passed. Full hardware clearance certification still requires actual geometry.
- The read-only equivalent of the provenance checker examined **61 records**: 382 dependency references matched directly, 95 mismatches had applicable review notes, and none of the dependencies it covers had an unreviewed mismatch. That result must be read with finding 3; it does not mean every dependency was checked or every result was regenerated.
- The README correctly distinguishes the representative chamber from the proposed machine, the implemented GaN model from planned AlN work, numerical verification from experimental validation, and full-range from half-range uniformity. Its main remaining evidence issue is the controller assumption in finding 1.

## Project state and next acceptance steps

B-p remains a reasonable provisional layout to investigate. This audit found no basis to declare a different layout superior. It also found no basis to promote the present operating-point results into a demonstrated control capability or a machine-performance guarantee.

The immediate software priorities are to make the controller's inputs realistic, enforce the joint acceptance rule and cover gallium data dependencies in provenance. Then rerun the affected studies before refining the recommended temperature or sensor budget.

The hardware priorities remain active-nitrogen output, outlet-plate geometry and operating range, effective pumping speed, heater ratings, temperature measurement and actual mechanical drawings. Experimental validation of nitrogen maps, wafer heating and growth is still outstanding. Agreement on thickness, rate and material-quality acceptance criteria is also outstanding.

The new integration code needs a separate review once its implementation and tests are stable. In particular, a transient simulator must not inherit the steady-state controller's knowledge of unobserved parameters without making that assumption explicit.

## Reproduction and scope

Audit scripts and numerical outputs are saved locally under `results/audit_20261005/`:

- `check_records.py` and `provenance.json`: read-only dependency audit and gate counterexample.
- `check_controller.py`, `controller.json` and `controller_log.txt`: working-point reproduction and fixed-spatial-calibration sensitivity.
- `check_joint.py` and `joint_actual.json`: the accepted case with only 92.8587% joint compliance.
- `joint_candidates.json`: saved admitted entries where both separate fractions are below one.

The test log is `results/audit_20261005_tests.txt`. These supporting files are in the ignored results directory; the findings and key numerical evidence are preserved in this report.

The environment used Python 3.12, NumPy 2.5.3, SciPy 1.18.1 and pytest 9.1.1, with BLAS threads limited to one. Dependencies were installed into `results/audit_20261005_deps/`. With Python and these dependencies available, run from the repository root:

```powershell
$env:PYTHONPATH = "$PWD\results\audit_20261005_deps;$PWD\src"
$env:OPENBLAS_NUM_THREADS = '1'
$env:OMP_NUM_THREADS = '1'
$env:MKL_NUM_THREADS = '1'
$auditTests = @(git ls-files 'tests/test_*.py')
python -m pytest -q -rs -p no:cacheprovider --basetemp results/audit_20261005_rerun @auditTests
python results/audit_20261005/check_records.py
python results/audit_20261005/check_controller.py
python results/audit_20261005/check_joint.py
```

The test selection above refers to tracked files at review time; later commits can change it. Python was invoked through the installed runtime's full path on this machine because it was not on `PATH`.

The audit reviewed implementation and internal evidence, ran tracked tests and selected numerical reproductions. It did not rerun the expensive production DSMC or scattering-table campaigns, repeat the literature review, or validate against real-machine measurements. It did not modify the in-progress integration work, commit or push changes.
