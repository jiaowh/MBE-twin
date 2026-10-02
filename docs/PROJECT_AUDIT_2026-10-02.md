Review of `d0f136d`, performed 2026-10-02 against the working tree and the supplied ending notes.

**Verdict: keep B-p as a provisional modelling choice, but do not close every review gate.** The headline B/B-p comparison reproduces, and the main comparison now solves nitrogen feed and pressure per state. Four remaining findings affect the mechanical guarantee, equal-rate rankings, heater-controller evidence and the scope of the hole-flow conclusion.

**1. High — the clearance bounds do not cover continuous shutter motion.**

Locations: [layout_feasibility.py:85](../scripts/layout_feasibility.py#L85), [layout_feasibility.py:122](../scripts/layout_feasibility.py#L122), [layout.py:215](../src/mbe_twin/layout.py#L215).

`SWEEP_STEPS = 6` samples seven positions across a 90-degree opening. The disk covering-radius subtraction bounds the surface at each sampled position; it does not bound positions between those angles. Taking the minimum over those seven positions, or over their 49 blade/blade combinations, therefore does not certify the whole sweep. Increasing `REFINED` only refines the disk surface, not the angular sampling. The holder check has the same omission.

For the assumed 66 mm Ga shutter arm, a point halfway between sampled angles can be 8.63 mm from its nearest sampled blade position. That is larger than the reported 1.32 mm excess over the 5 mm clearance requirement. This does not establish a collision: an independent 0.25-degree scan of Ga1's blade against Al1's body retained the 8.886 mm sampled minimum at 90 degrees. It establishes that the claimed guarantee has not been proved for every checked solid and motion.

Required: bound the motion between samples (including both moving blades), with adaptive angular refinement near the margin, or use a certified continuous minimum. Until then, replace the full-sweep guarantee in the design document, README and hardware request with a sampled-motion result. Add a test whose minimum occurs between sampled shutter angles.

**2. Medium — states below the actual growth-rate target still enter equal-rate rankings.**

Locations: [layout_comparison.py:453](../scripts/layout_comparison.py#L453), [layout_comparison.py:701](../scripts/layout_comparison.py#L701).

`solve_states` achieves the nitrogen-limited target. After `steady_state` includes the fixed Ga supply, `mean_h` can be smaller because some radii become Ga-limited. Nevertheless, `valid = (~limited) & (kn >= KN_VALID)` never checks `mean_h`. The ranking intersects those validity masks, so its supposedly equal-rate population includes slower-growing states.

Independent reproduction at 700 C, eta=1, 2 m3/s, 10 sccm, 1 um/h, within +/-0.8 degrees:

| Layout / droplet law | States marked valid but below target | Lowest actual rate |
|---|---:|---:|
| B / G01_adsorption | 468 of 3150 | 0.984360 um/h |
| B-p / G01_adsorption | 363 of 3150 | 0.987097 um/h |
| B-L / G01_adsorption | 225 of 3150 | 0.990993 um/h |

The test used a relative rate tolerance of 1e-6; these are not bisection residuals. No below-target states were found in the reproduced 740 C headline cases. The separately reported valid-and-in-window threshold shares already reject the N-rich cases via their margin, so this finding primarily affects validity labels and pairwise rankings.

Required: distinguish nitrogen-supply feasibility, actual target achievement and growth-window membership. Require actual target achievement for an equal-rate ranking; if a rate tolerance is intended, declare and test it. Retain slower cases as explicitly labelled off-target results.

**3. Medium — the heater-controller study still holds pressure at one nominal operating point.**

Locations: [heater_robustness.py:116](../scripts/heater_robustness.py#L116), [heater_robustness.py:140](../scripts/heater_robustness.py#L140), [heater_robustness.py:150](../scripts/heater_robustness.py#L150).

The script selects B's 740 C nominal pressure once, attenuates the N and Ga maps at that pressure, and reuses those shapes for both growth temperatures and every combined heater/sensor state. It subsequently rescales N to compensate each state's decomposition, including after the pyrometer shift. At fixed eta this changes feed and pressure, but neither beam's attenuation is recomputed. The thickness branch similarly fixes each layout's nominal pressure while rescaling N across heater states.

Thus the main comparison's per-state pressure correction has not propagated into the study supporting “91-100% with a centre pyrometer.” That percentage remains a result of the fixed-pressure approximation. It is also for original B at nominal pointing/fill/lip, rather than a controller assessment of B-p's full uncertainty ensemble. The script documents a uniform-temperature-shift approximation for the pyrometer; it does not re-solve heater power and element temperature for that control action.

Required: reuse the coupled feed/pressure solve in the combined-heater and sensor cases, preserve absolute Ga output for the fixed protocol, and evaluate the corrected protocol at the same state's transport conditions. Recompute the sensor-controlled heater equilibrium and limit, or bound the error of the uniform-shift approximation. Regenerate the controller percentages for the intended layout before using them as its design evidence.

**4. Medium — original B's hole-flow result is generalized to the B family without the matching calculation.**

Locations: [sparta_hole.py:81](../scripts/sparta_hole.py#L81), [LAYOUT_COMPARISON.md:200](LAYOUT_COMPARISON.md#L200).

The recorded hole study evaluates only B (+105 mm) and C (+75 mm), without background attenuation, holder lip or Ga. The design document extends its “no detectable change down to Kn 0.3” result to the B family, including B-p (+97.5 mm). Projecting the saved whole-run intensity fits through the same map function at B-p's aim gives:

| Aim | Kn=100 reference | Kn=3 | Kn=0.3 |
|---|---:|---:|---:|
| B (+105 mm) | 0.5210% | 0.5314% | 0.4748% |
| B-p (+97.5 mm) | 0.5523% | 0.5608% | 0.7697% |

B-p's whole-run point estimate changes by +0.2174 percentage points at Kn=0.3. This audit did not recompute B-p block uncertainties, so it does not assign statistical significance to that difference. It does show that the original B result cannot simply stand in for B-p. The Kn=3 point estimate is close to the reference and remains encouraging.

The prior request for timestep/grid/reservoir convergence is also not closed by the stored evidence: the hole record contains one cell size, timestep and reservoir geometry. Improving the Kn=100 reference and reporting time-block uncertainty addresses part of that gate, but does not establish discretization or boundary convergence. Subtracting a common Kn=100 setup does not prove its boundary error is independent of Kn.

Required: evaluate B-p with per-block errors and at its operating pressure; perform numerical/boundary convergence checks before qualifying a relaxed validity limit. Keep neutral, single-hole and no-neighbour-interaction limitations explicit. Archive the relaxed-Kn operating comparison and an executable reproduction command: the current comparison hard-codes `KN_VALID = 10`, and REPRODUCE.md does not provide a Kn=3 run matching the quoted 0.73/2.11% result.

**What independently checked out.**

- `python -m pytest -q -p no:cacheprovider --basetemp results/audit_20261002_pytest`: **200 passed in 76.52 seconds**. Runtime: Python 3.12, NumPy 2.5.1, SciPy 1.18.0; archived studies used NumPy 2.4.4.
- `python scripts/record_provenance.py --check`: exit 0. Direct LF-normalized source-hash checks found no mismatch for the active layout comparison, feasibility, heater robustness, nitrogen evidence, rate limits or hole-flow records.
- With the recorded keyed N/Ga caches and fresh heater solves, all three droplet laws reproduced the 740 C headline nominal and +/-0.8-degree worst cases:

| Layout | Nominal | Worst |
|---|---:|---:|
| B | 1.055805% | 2.402927% |
| B-p | 0.425270% | 1.749628% |
| B-L | 0.640333% | 1.740010% |

- The main evaluator computes per-state feed, pressure, N attenuation, Ga attenuation and hole Kn. Its validity filter excludes out-of-domain C states, and pairwise reports explicitly separate the two pointing ensembles.
- The nitrogen-evidence script applies eta<=1 to its admissible and joint ranges. Raw rejected cases remain in diagnostic fields, which is appropriate; they are not admitted into the quoted joint range.
- The mechanical surface-distance bounds are connected and tested. The remaining gap is the continuous motion bound, not the disk covering-radius formula.

**Limits of the provenance result.** The check means “no mismatch without a filename-level explanation,” not “every record exactly matches HEAD.” `IMPACT.get(path)` accepts a general note for any mismatch of that file. In particular, the aim studies still have mismatches, and the large-plate aim record includes source hashes with no matching committed version. The clean active-record hashes above were checked separately. Future hardening should tie exceptions to the recorded/current hash pair and the particular record, so an unrelated later edit cannot inherit a stale approval note.

**Scope and ending-note corrections.**

The audit inspected the governing documents, changed modelling/study paths, tests, stored records and prior review. It reran the full unit suite and selected layout calculations. It did not rerun SPARTA/Elmer, regenerate every Monte Carlo map or independently re-extract every cited paper. The literature's 6-57% interval remains a model-conditioned inference, not a measured hardware conversion specification. The existing open hardware and project requirements remain open.

The supported ending note is: **B-p remains the provisional working layout; its headline figures reproduce and all 200 tests pass. The main pressure and pointing-ranking fixes are present, and impossible eta cases are excluded from the admissible evidence. Full-motion mechanical certification, actual-rate ranking filters, a coupled heater-controller assessment, and qualification of the relaxed hole-flow limit remain to be completed.**

Audit helpers and detailed numerical output are in ignored `results/audit_20261002*`. No model implementation, recorded scientific result or governing recommendation was changed by this review. The provenance generator's incidental rewrite was restored to its pre-audit content. Pre-existing untracked files were left untouched. This report is not committed or pushed.
