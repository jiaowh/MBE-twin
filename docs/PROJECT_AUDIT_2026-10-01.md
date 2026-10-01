# Project audit — 2026-10-01

**Verdict: on track for representative-chamber design research; not ready for design freeze or a claim that two layouts are physically viable.** The latest milestone is substantial, but the operating constraints and control protocol need corrections before its rankings support a hardware decision.

Reviewed HEAD `161f74b`, including `6aca3b3`, against the governing Phase-1 plan, implementation, tests, design envelope and recorded studies. No physics implementation or recorded results were changed by this audit.

## Evidence checked

- Independently ran the full suite: **182 passed in 53.09 s**, using the existing `rheed` Python environment and a temporary project-local pytest installation. Passing tests establish the tested behaviors, not the physical conclusions below.
- All 10 explicitly listed source hashes in `layout_comparison.json` and all four in `layout_feasibility.json` match the checkout after LF normalization.
- Recomputed the designed-density heater at 740 C with the 1473.15 K nominal limit, then evaluated B and C using the existing cached beam maps. Reproduced their nominal thickness values exactly: **0.8349235211%** and **0.3481260952%**, and their nominal active-N demands: **4.242933793e18/s** and **5.819591552e18/s**.
- Inspected the uncertainty construction and mechanical checks. Did not regenerate the full Monte Carlo maps, run the complete mechanical study, or independently validate the underlying literature or hardware geometry.
- Local branch is 32 commits ahead of its locally recorded upstream tracking ref. Both cited commits exist. No remote fetch was performed, so this is not a live remote-status check.

## Findings, in decision-priority order

### 1. High: nitrogen demand and pressure describe an impossible combined operating point

The headline comparison uses 2 sccm N2 into 2 m3/s while independently scaling active-N output to deliver 1 um/h. With the repository's own standard-flow convention:

`N atoms/s per sccm = 2 * 1.68875e-3 / (k_B * 273.15) = 8.956e17`.

Thus **2 sccm contains at most 1.791e18 N atoms/s**, before incomplete dissociation, recombination or other losses. Every layout's nominal demand exceeds this atom budget. This is stronger than an unknown vendor capability.

| Layout | Required active N (/s) | Minimum N2 feed, even at 100% conversion (sccm) |
|---|---:|---:|
| A | 3.725e18 | 4.16 |
| B | 4.243e18 | 4.74 |
| C / C-Ga54 | 5.820e18 | 6.50 |
| R0 | 7.361e18 | 8.22 |
| D | 5.275e18 | 5.89 |

These are lower bounds evaluated at the old pressure, not self-consistent new operating points. Raising flow changes attenuation and potentially the hole-flow regime and angular distribution. At 2 m3/s, even B/C's lower-bound feeds imply about 0.0044/0.0060 Pa under the current pressure model, before iterating the increased nitrogen demand.

**Required correction:** couple feed, active fraction, plate output, effective pumping, attenuation and hole Knudsen validity. Reject states that violate the atom budget. Solve for achievable rate or a feasible flow/pumping requirement; rerun the layout comparison there. Retain B/C as candidates, not established viable layouts.

Code: `scripts/layout_comparison.py:evaluate/main`, `src/mbe_twin/vacuum.py:pressure_from_flow`.

### 2. High: the claimed fixed Ga centre flux actually follows nitrogen

The documented protocol says nominal Ga calibration is held across uncertainty states. In `evaluate`, however:

```python
j_ga = r0 * j_n[..., :1] * ga[None, :, None, :, :]
```

uses each state's newly scaled N centre flux. It holds the centre Ga/N ratio, not the nominal absolute Ga centre flux. A controlled audit example changing only N profile shape changed the computed Ga centre from **26.49075 to 24.02502 nm/min-equivalent**, despite the stated hold.

**Required correction:** use the nominal calibrated Ga centre amplitude for a fixed-flux protocol, or explicitly define a controller that retunes Ga with N. Test the distinction and recompute window margins, state fractions and any affected thickness rankings. The nominal Ga-rich thickness results can remain correct while the robustness interpretation is wrong.

Code: `scripts/layout_comparison.py:208`; the existing equal-rate test does not assert Ga-flux invariance.

### 3. High: the heater limit is nominal-only; the emissivity explanation is reversed

`heater_states` constrains the nominal optimizer, then calls unconstrained `hz.at_mean` for perturbed states. These states remain in the reported uncertainty grid, without a heater-feasibility mask. Holding the target temperature beyond the element rating does not establish operation under that rating.

For B/C at 740 C and a 1473.15 K limit, the recorded and reproduced sequence is:

| Wafer emissivity | Maximum element temperature |
|---|---:|
| 0.70 nominal | 1473.108 K |
| 0.63, 10% lower | 1450.207 K |
| 0.77, 10% higher | 1494.792 K |

The progress note and comparison document attribute the over-limit result to **lower** emissivity; the actual output assigns it to **higher** emissivity. The roughly 22 K headroom issue is real, but its explanation needs correction.

**Required correction:** either flag these states infeasible at the target temperature, or cap power/element temperature and compute the achieved wafer temperature and growth. Report thermal feasibility alongside growth-window feasibility.

Code: `scripts/layout_comparison.py:heater_states`, `scripts/heater_zones.py:at_mean`.

### 4. Medium: mechanical screening is useful, but does not certify all clearances

`pair_clearances` checks body/body, sampled flange/flange, shutter/body and shutter/shutter with the other shutter at its end positions. It does not cover every cross-type pair such as flange/body, or both shutters moving through their sweeps simultaneously. Disk samples are finite; positive separation between sampled points does not prove separation of the continuous disks. Bodies-as-capsules is conservative, but that conservatism does not extend to all other checks.

No actual collision was demonstrated by this audit. The conclusion should be **“no conflict found in the modeled checks with assumed dimensions,”** rather than “manufacturable” or a completed mechanical sign-off.

**Required correction:** use continuous solid distances or demonstrated sampling bounds, cover relevant component pairs and motion states, then check the actual drawings and the already acknowledged shroud/diagnostic/service interfaces.

Code: `scripts/layout_feasibility.py:pair_clearances/holder_clearance`, `src/mbe_twin/layout.py:disk_to_disk`.

### 5. Medium: matching source hashes do not yet establish complete run provenance

The comparison selects the latest available Ga records dynamically, but its manifest does not identify/hash those consumed records or cached NPZ files. It also omits directly relevant dependencies including `crucible.py` and `profile_fit.py` from its explicit source list. Cache names encode only a subset of inputs: N aspect/port/aim or Ga port/fill. Reusing a cache after changing pressure cases, sampling, throw or other inputs can silently use stale arrays.

This does not prove the current results are stale; the reproduced nominal values agree. It means the assertion that the committed code completely identifies the computation is too strong.

**Required correction:** record selected input paths and hashes, all numerical dependencies, and validated cache keys covering the full generating inputs and code. Fail on incompatible caches instead of accepting them by filename.

Code: `scripts/layout_comparison.py:ga_record`, cache reads in `main`, and the final `build_manifest` call.

### 6. Medium: “all uncertainties combined” and “fails” exceed the declared scope

The ensemble combines pointing, Ga state, lip, droplet law and a heater-category axis. The seven heater categories perturb emissivity, contact and power separately; they do not combine those three errors with one another. Other uncertain inputs, including N profile and scattering assumptions, are not part of this grid. The documentation correctly says grid fractions are not probabilities, but the broader progress wording should be narrowed.

There is also no agreed numerical uniformity acceptance target: the intake ledger leaves it null. A is clearly much worse in the sampled model; “every layout fails” at high pressure nevertheless needs an explicit acceptance criterion. Grid win shares establish no stable B/C winner under that sampling, not statistical equivalence or real-world probabilities.

**Required correction:** define the feasible-set constraints and target before counting pass/fail; name the included uncertainty axes precisely and assess missing combinations where decision-relevant.

## Secondary numerical/reporting issues

- `area_mean` uses equally spaced point weights proportional to radius, including a full endpoint weight. For the exact test profile `(r/R)^2`, its 39-point grid returns **0.5131579**, versus the analytic disk mean **0.5**. Use radial quadrature or annular areas and show resolution convergence. This is not the dominant feasibility problem.
- The governing plan asks for area-weighted standard deviation alongside thickness half-range/mean; the layout summary does not provide that companion metric.
- One ideal wafer-mean feedback value in the thermal study is not an implemented single-spot temperature observation model. Sensor observability remains a separate design gate.

## Project direction and next milestone

The work remains aligned with the primary goal: reducing measured wafer-thickness nonuniformity. The common mask, explicit assumed/missing inputs, complete candidate configurations, combined-state screening, and calibration/validation separation are meaningful improvements. Keeping B as a provisional working candidate is reasonable; freezing B or discarding C is premature.

Stage A remains incomplete against the governing plan: R03 reproduction is deferred without a completed replacement acceptance gate; active-N delivery is not bounded by a feasible source operating point; transients/shutter-event inventories and the complete laptop workflow benchmark remain open. AlN and the integrated machine twin are later work, not delivered by this milestone. Nothing here demonstrates measured wafer improvement. Calendar schedule health cannot be inferred from code progress alone.

**Next milestone: a physically feasible B/C comparison with a corrected operating protocol.**

1. Correct Ga hold and per-state heater constraints, with regression checks; fix the emissivity wording.
2. Close the nitrogen atom/flow/pressure balance and reassess plate-flow validity, including achievable-rate scenarios if 1 um/h is unsupported.
3. Regenerate results with complete input/cache provenance, numerical-resolution checks and explicit acceptance constraints.
4. Obtain the source output-versus-flow/power envelope, plate drawing, port/mount/holder drawings and heater rating. Qualify mechanical clearance against these inputs.
5. Hold a documented Stage-A gate review before adding further optimization sweeps or treating a layout as ready for fabrication.
