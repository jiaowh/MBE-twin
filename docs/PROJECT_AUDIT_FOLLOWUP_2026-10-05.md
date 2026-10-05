# Review of audit amendments and latest progress — 5 October 2026

Reviewed `cdc97ac`, covering the changes since `226d8a8`: the integrated twin, realizable-controller study, joint acceptance rule, gallium provenance, heater margin and uniformity levers. This is a review, not a change to the models or their saved results.

**Verdict:** the response makes substantial progress. The joint acceptance defect is fixed, gallium hashes are now checked, and the steady controller no longer needs each uncertain state's beam maps for its basic rate-monitor-plus-BFM protocol. The new 710 °C results reproduce. Three remaining issues concern the transient controller's pressure input, the provenance of the newest results, and how the README describes the conditions needed for its headline result.

## Findings

### 1. Medium — the transient controller still reads true pressure instead of the gauge

Location: [twin.py](../src/mbe_twin/twin.py#L271), lines 273–274, 298 and 334–336.

The Ga steering calls `ga_target` and `cell_for` with `state["pressure"]`. The BFM correction calls `model_arrival` with the true sub-step pressure. The ion gauge, including its sensitivity and noise, is evaluated later for the log and does not supply these controller inputs.

This contradicts the stated observation boundary: the controller is meant to see an ion-gauge reading, not the simulator's true pressure. Pressure-dependent calibration errors are therefore absent from the control response even when the instrument configuration specifies them.

**Reproduction:** ran the same 300 s steered-Ga recipe twice on the 120 mm truth chamber, with all other settings and the seed identical. Changing gauge sensitivity from 1 to 2 doubled the final logged reading from 0.00862078 to 0.01724157 Pa. The complete cell-temperature, Ga-target, nitrogen-flow and true-pressure traces remained identical, with maximum differences of exactly zero. The factor of two is a diagnostic perturbation, not a proposed instrument uncertainty.

**Required correction:** sample the gauge at the controller's observation time, retain its reading and quality flag, and use that reading consistently for Ga steering and BFM calibration. Test that gauge sensitivity affects pressure-dependent commands while the physical gas state still evolves from the true feed. This does not undo the beam-map calibration/truth separation already added.

### 2. Medium — the newest uniformity results have incomplete dependency records

Locations: [realizable_controller.py](../scripts/realizable_controller.py#L226), its manifest source list at line 458; [summarize_uniformity_levers.py](../scripts/summarize_uniformity_levers.py#L44), lines 62–67.

There are two related omissions:

- The controller runner reads optional aim-map NPZ files and imports `multispot_heater.py`, but does not hash either in its own manifest. The aim-map paths are recorded; their content hashes are not.
- The summary runner collects constituent `source_sha256` dictionaries into `sources`, but never writes that dictionary into the summary. Its module documentation says the source hashes are copied in. In fact, the summary records its own five source files and the constituent manifest hashes, while the constituent manifests remain under ignored `results/`.

The archived summary therefore cannot recover which versions of every physics input and helper generated each row. Rerunning the summarizer after changes can attach current top-level hashes to old results without detecting the missing dependency. The current provenance checker cannot establish completeness from this record.

**Evidence:** all five archived multi-spot runs inspected omit the multi-spot module hash; all 23 aim-map-consuming runs inspected omit their aim-map content hashes. The issue exists even though the current checker reports no unreviewed mismatches. It does not establish that today's numerical results are wrong: the selected headline calculation reproduced independently.

**Required correction:** hash the optional module and aim-map inputs at execution time. Preserve the dependency hashes and essential inputs separately for each constituent run in the versioned summary, or version the compact constituent manifests. Include rate, scattering variant, supply scenario, acceptance threshold and rate band in the archived settings. Do not merge conflicting source versions into a single dictionary that loses their association with individual runs.

### 3. Medium — the README omits a condition needed for B-p's 710 °C result

Location: [README.md](../README.md#L114), the 710 °C result and current-design discussion. The detailed conditions are correctly given in [LAYOUT_COMPARISON.md](LAYOUT_COMPARISON.md), section 12.

The README says that re-aiming and three-point temperature control bring both layouts to their most uniform point at 710 °C. For B-p, that statement also requires a fill-aware Ga calibration. Rate monitor + BFM alone passes only **94.1%** of the ensemble at 710 °C, below the 95% rule. Adding the calibrated Ga shape for the tracked fill increases the share to **96.0%**. The numerical spread is similar, but the first configuration is not admissible.

The overview also mixes the new recommendation with older text: it calls the 720 °C / 1.53% point the most uniform admissible point before presenting the better multi-spot result, retains an unqualified 1.5–1.8% paragraph, and points readers to section 10 rather than the governing sections 11–12.

**Required correction:** distinguish the simpler configuration from the multi-spot/re-aim candidate, name fill tracking and its calibrated shapes for B-p at 710 °C, and state that 710 °C extrapolates the decomposition law below its 720–805 °C fitted range. Keep the 720 °C alternative alongside it. The hardware prerequisites and crystal-quality limitation still apply.

## Status of the original audit findings

| Original finding | Review outcome |
|---|---|
| Controller supplied with uncertain beam maps | Substantially addressed in the new steady study. The basic rate-monitor-plus-BFM controller uses nominal calibration and explicit observation errors; the known-map calculation is labelled as a bound. Commissioned maps are explicitly an optimistic calibration case. The transient gauge bypass above remains to fix. |
| Separate 95% gates | Fixed. `operating_optimum.admission` calculates the joint fraction, and the operating studies gate on it. The counterexample regression passes. The formerly accepted B-L / 1.25 µm/h / 740 °C direct-beam case now has no accepted cold point through 760 °C. |
| Gallium dependencies omitted | The specific omission is fixed: the checker expands the direct and nested chamber-provenance gallium hashes. Regression tests pass. This should not be taken as a general completeness guarantee for the new summary pipeline in finding 2. |

The old calculations that know every state's maps remain useful as bounds. They should not be read as evidence for a controller with only the named instruments.

## Latest results independently checked

Re-ran the multi-spot study at 710 °C with a 1460 K heater design limit, 0.2° residual pointing, B-L aim at +95 mm, and the default ±1% rate-monitor / ±2% BFM errors. The heater calculation included 243 combined states. The following values reproduce the archived summary:

| Layout and controller | Joint valid-and-in-window share | Worst thickness half-range/mean | Meets 95% rule |
|---|---:|---:|---|
| B-p, rate monitor + BFM | about 94.1% | about 0.494% | No |
| B-p, rate monitor + BFM + fill | 95.9542% | 0.494145% | Yes |
| B-L, rate monitor + BFM | 96.8703% | 0.654295% | Yes |

These are steady model results over the accepted subset, with a ±3% rate band. They are not worst-case guarantees over every sampled condition, measured wafer improvements or yield probabilities. The B-p scenario uses nitrogen conversion 1.0 and pumping 2 m³/s; B-L uses conversion 0.3 and pumping 4 m³/s. Their hardware feasibility is therefore different.

The latest work provides useful engineering direction: test alignment correction and multi-radius temperature feedback, rather than relying only on extra heater power. The B-L aim change uses the old attenuation and tilt-response tables as stated approximations. Before freezing an aim or a sub-percent uniformity requirement, check the leading candidate with its own transport/pointing tables and calibration errors. The synthetic commissioning exercise and measured validation remain necessary.

The integrated twin is also meaningful new progress: recipe execution, persistent surface inventories, heater transients, instrument logs, restart and controller convergence now have passing tests. The latest multi-spot/fill-aware optimum is a separate steady study; it has not been demonstrated as a complete transient commissioning-and-growth workflow by this review.

## Verification and review limits

- **264 tests passed** in 103.09 s, including the new twin, joint-gate and multi-spot tests. The three Elmer tests were excluded because the previous audit already established that Windows Application Control blocks the solver. They were not requalified here.
- Read-only provenance check: 762 dependency references matched, 76 mismatches had applicable notes, and none of the covered dependencies had an unreviewed mismatch. Finding 2 limits what this establishes.
- Reproduced the selected 710 °C calculation in a separate output directory. No saved scientific record was overwritten.
- No new production DSMC campaigns, full aim/temperature sweeps, literature re-review or real-machine validation were performed.

Local supporting files are under `results/review_20261005/`: `check_records.py`, `records.json`, `check_gauge.py`, `gauge.json`, and `lever710/manifest.json`. The test log is `results/review_20261005_tests.txt`. These files are ignored by Git; this report preserves the principal evidence.

Reproduction, from the repository root with Python, NumPy and SciPy available and `PYTHONPATH=src`:

```powershell
python -m pytest -q -rs --ignore=tests/test_elmer.py -p no:cacheprovider
python results/review_20261005/check_records.py
python results/review_20261005/check_gauge.py
python scripts/realizable_controller.py --t-min 710 --t-max 710 --heater-design-limit 1460 --pointing-residual 0.2 --heater-control multispot --aim-maps results/aim_operating/aim_maps_B-L.npz --aim-mm 95 --out results/review_20261005/lever710_rerun
```

The final command uses the existing aim maps; a clean checkout must first generate the required map with `python scripts/nitrogen_aim_operating.py --layout B-L --aims 95 --out results/aim_operating` (and generate the base comparison caches as described in `docs/REPRODUCE.md`). The review used the same locally installed Python test dependencies as the original audit, with BLAS threads limited to one.

## Response (2026-10-05, same day)

- **Finding 1 (gauge).** The twin's controllers now sample the ion gauge (sensitivity and noise) together with the pyrometer at the start of each sub-step. They use that reading for the Ga steering and for the BFM correction; the gas still evolves from the true feed. The logged gauge_Pa is the controller's reading. New test `test_controllers_see_the_gauge_not_the_true_pressure`: a gauge sensitivity of 2 leaves the pressure trace identical and changes the Ga target and cell commands. All twin records were regenerated (cases/twin/twin_runs.sh). With the default 1 % gauge noise the results move by at most 0.01 nm.
- **Finding 2 (dependencies).**
  - realizable_controller.py now records `aim_maps_sha256` (content hashes) and adds scripts/multispot_heater.py and scripts/nitrogen_aim_operating.py to its sources when they are used.
  - summarize_uniformity_levers.py keeps every constituent run's own source and input-dependency hashes under `inputs.constituents`, together with the essential settings (rate, scattering variant, supply scenarios, acceptance level, rate band, element limit, pyrometer biases).
  - record_provenance.py checks each constituent as its own set, labelled `record [run]`, and expands `aim_maps_sha256`; there is a test.
  - The 22 aim-map runs and the 5 multi-spot runs were rerun (cases/rerun_provenance_2026-10-05.sh), so their hashes come from execution time. The summary's best points are unchanged: 0.54 % (B-p, 720 C), 0.49 % (B-p with fill tracking, 710 C), 0.65 % (B-L, 710 C).
- **Finding 3 (README).** The README now separates three configurations in a table: one pyrometer without re-aim, re-aim + multi-spot at 720 C, and the same at 710 C. It states that B-p at 710 C needs fill tracking (94.1 % without it), that 710 C extrapolates the decomposition law, that the B-p and B-L supply scenarios differ, and that the B-L aim still needs its own tables. It also points to sections 11-12 as governing. The stale 1.5-1.8 % paragraph is removed.
