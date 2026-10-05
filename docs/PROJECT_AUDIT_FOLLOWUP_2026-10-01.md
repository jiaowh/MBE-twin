# Follow-up review of the latest work

Reviewed committed revision `353cf47` and the working-tree drafts present on 2026-10-01. Verdict: substantial progress on the audit corrections; retain B as provisional, but the robustness comparison is not yet a fully feasible operating-envelope assessment.

## Verification

- Independently ran the current suite: **196 passed in 78.58 seconds**.
- With the recorded keyed beam caches and a fresh heater solve, reproduced the 740 C, eta=1, 2 m3/s, nominal 1 um/h results exactly: B **1.0558052779%**, C **0.9412307570%** half-range/mean.
- Confirmed absolute Ga-centre hold, per-state heater capping, corrected emissivity direction, annulus-weighted mean/std, selected Ga-record hashes and keyed map caches.
- The comparison record's only listed source mismatch is the uncommitted addition of unused disk-distance bound helpers to `layout.py`. The nominal reproduction still agrees. The nitrogen-rate-limit and heater-robustness records' listed source hashes match.
- Did not regenerate the complete beam ensemble, run external DSMC jobs, or independently verify the new literature extraction. Source and artifact inspection is distinguished below from experimental validation.

## Remaining findings

### High — pressure/feed consistency is still nominal-only

`layout_comparison.py` solves a coupled nominal operating point, then builds every uncertain N map at that pressure (line 536). `evaluate` independently resets output for each state and caps against the maximum feed, while pressure and the nominal plate-validity flag remain fixed.

At fixed eta, changing output changes feed and pressure. At eta=1, an increase cannot instead come from improving conversion at fixed feed. The approximation is acknowledged in the text but needs a bounded error before calling the grid physically achievable.

For the +/-0.8-degree, 740 C, eta=1, 2 m3/s, 1 um/h grid:

| Layout | Nominal feed | Feed implied by state outputs |
|---|---:|---:|
| B | 5.219 sccm | 4.919–5.481 sccm |
| C | 7.694 sccm | 7.297–8.053 sccm |

Re-evaluating attenuation at the implied feeds, keeping the reported outputs, gives N-limited rates of approximately **0.992–1.009 um/h** at B's two output extrema and **0.989–1.012 um/h** at C's. These are diagnostic spot checks, not corrected whole-grid limits; Ga transport and margins also need recomputation.

Required: solve feed/pressure/attenuation and plate validity per state, or define a fixed-feed, variable-conversion controller with a measured conversion range. Rank only states meeting the declared rate and validity constraints.

### High — an out-of-domain C result still supports the headline ranking

C's nominal 1 um/h point is correctly flagged `plate_free_molecular=false`. It requires 7.69 sccm, above the approximately 5.9 sccm validity ceiling used for this plate. Nevertheless, it enters the headline B/C rankings without a validity filter. The extrapolation is disclosed, but “B wins at 1 um/h” remains stronger than the supported comparison.

Required: separate within-domain results from exploratory extrapolations. Qualify transitional-hole transport or change the plate before using C's 1 um/h result for selection. B remains the sensible provisional candidate; neither is a hardware-qualified pass.

### Medium — the 70% win share uses a broader pointing ensemble than the nearby table

The ranking loop at `layout_comparison.py:592` retains all 49 pointing maps, including +/-1.6 degrees. The table places that share alongside +/-0.8-degree worst cases without specifying the different ensemble.

Independent recomputation: **B wins 70.36% across the full ensemble, but 62.29% within +/-0.8 degrees** at the headline operating point. State the tolerance explicitly or report both shares. This changes the strength of the claimed preference, not its direction in this sampled model.

### Draft gate — the hole-flow simulation needs a numerical reference check first

`results/sparta_hole/manifest.json` matches its listed source hashes. Its Kn=100 near-free-molecular case reports transmission 0.42493 against 0.42688 for the free-molecular reference, which is close. However, the decision metric differs substantially:

| Map | Free-molecular reference | Kn=100 DSMC |
|---|---:|---:|
| B thickness half-range/mean | 0.560% | 1.069% |
| C thickness half-range/mean | 0.145% | 1.787% |

The cause is not established by this review. Converge particle statistics, angular estimation, timestep/grid and the collisionless limit, and quantify metric error before attributing low-Kn differences to collisions. A neutral N2 hole study is also not yet an active-N species-validation result.

### Draft gate — nitrogen-evidence output is stale and contains impossible scenarios

`results/nitrogen_output_evidence/manifest.json` does not match the current `scripts/nitrogen_output_evidence.py`. The stored output includes inferred eta up to **1.379** and propagates it into 200 mm rate predictions. Eta above one rejects that geometry/model/measurement combination; it cannot be an achievable source scenario.

The current script adds joint geometry constraints and an eta<=1 filter. Regenerate and inspect the result before quoting it. Keep inferred eta conditional on unpublished geometry and plate-model applicability; this is not a vendor specification or a measurement of source conversion.

### Draft gate — combined heater errors add useful information but remain limited

The new recorded heater-robustness study reports an element requirement up to **1499.87 K** at 740 C for the nominally 1473.15 K design: approximately **26.7 K headroom**, versus the earlier single-error estimate of 22 K. Its temperature-corrected Ga protocol stays in-window in all sampled 740 C cases, but only **77.8%** at 700 C under the 1473 K limit.

These are recorded model results, not an independently rerun controller validation. They use nominal pointing/fill/lip and ideal knowledge of wafer mean temperature; they do not yet close the full combined uncertainty or sensor-observation gate. The new mechanical distance-bound helpers are likewise not yet wired into the feasibility script.

## Next acceptance gate

1. Close the per-state nitrogen/feed/pressure balance, including plate validity and achievable rate.
2. Regenerate rankings with explicit pointing tolerance and separate valid/extrapolated results.
3. Qualify the hole-flow reference and regenerate the corrected nitrogen-evidence output before relying on either.
4. Incorporate combined heater and actual sensor assumptions, and connect/test the mechanical bounds.

No implementation or existing recorded result was changed in this review. The review helper and temporary test dependencies are under ignored `results/`; this note is the only new review document.
