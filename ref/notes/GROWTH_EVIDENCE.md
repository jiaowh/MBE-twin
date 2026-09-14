# GaN/AlN growth evidence and plan corrections

Compiled 2026-09-13. Literature and downloads were first accessed on 2026-09-11; the local files and selected metadata were checked again on 2026-09-13. This is a planning evidence review, not a calibrated material database or chamber validation.

The collection contains **12 source records, including 9 downloaded PDFs**. Complete titles, authors, publication years, DOI/URLs, source locators, applicability limits and file hashes are in [sources.json](../growth/sources.json). [file_verification.json](../growth/file_verification.json) records PDF page counts, sizes, SHA-256 checks and first-page inspection. G03 is a bibliographic acquisition lead; G05 and G06 have reviewed primary web text but no local PDF. Download logs are retained separately so a failed first attempt is not mistaken for the final acquisition status.

## What the papers establish

| ID | Evidence useful to this twin | Where to start | Important limit |
|---|---|---|---|
| [G01](https://doi.org/10.1103/PhysRevB.67.165419) | Ga adsorption has distinct coverage and droplet regimes. | Experimental procedure, Figs. 1-5, Table I | Ga-polar adsorption experiment; intensity itself is not a universal coverage meter. |
| [G02](https://doi.org/10.1063/1.2968442) | GaN loss and recapture depend on active-N excess and growth regime. | Figs. 3-6; Conclusions | Effective decomposition during growth cannot be represented by a universal vacuum rate alone. |
| [G03](https://doi.org/10.1063/1.1575929) | Foundational AlN heteroepitaxy growth-diagram paper to acquire. | G11 reference 33 | Original full text not acquired; no constants extracted. |
| [G04](https://doi.org/10.1063/1.2734390) | Atomic-N delivery can be measured independently from incorporation. | Figs. 2-4 | The source geometry, species fractions and measured efficiency are specific to the experiment. |
| [G05](https://pmc.ncbi.nlm.nih.gov/articles/PMC5226270/) | Practical repeated BFM calibration, shutter sequencing and rotation-triggered RHEED. | Protocol calibration and Ga desorption sections | Use measurement methods; its N-polar InAlN recipe does not expand project scope. |
| [G06](https://doi.org/10.1016/j.jcrysgro.2013.10.013) | Source/aperture changes alter rate; active-N maps require measured power/flow response. | Publisher growth-rate and source-improvement sections | Flow response need not be monotonic. Source rating does not fix wafer delivery. |
| [G07](https://doi.org/10.1103/PhysRevB.72.075209) | Measured crystalline GaN heat capacity spans 20-1400 K. | Sec. IV and Figs. 4-5 | Distinguish measured Cp from calculated Cv and from substrate properties. |
| [G08](https://doi.org/10.1063/1.5097172) | Measured AlN conductivity depends on material quality; film-size effects require attention. | Fig. 4, Fig. 5, supplement | Measurements are 100-400 K; higher-temperature and film curves include modeling. |
| [G09](https://arxiv.org/abs/1910.05440) | First-principles conductivity model resolves temperature and crystal direction. | Figs. 1-3, property tables | 2019 preprint; 100-1000 K calculations are not high-temperature chamber measurements. |
| [G10](https://doi.org/10.1126/sciadv.abo6408) | Surface preparation can determine whether N-polar AlN homoepitaxy preserves polarity. | Paired specimens with/without cleaning | A surface-state and polarity problem, not proof of a universal cleaning recipe. |
| [G11](https://doi.org/10.1063/5.0010813) | Al-polar AlN requires its own growth/desorption map and temperature calibration. | Figs. 2-3 and 5 | Bulk impurity levels and nucleation-interface peaks must be distinguished. |
| [G12](https://doi.org/10.3390/cryst8040178) | Nanowire regrowth contamination correlates with inversion domains. | Table 1; discussion of APT mass ambiguities | This is a 2018 paper, not 2024; nanowire correlations are not planar leakage laws. |

## Corrections required before implementation

1. **Make GaN and AlN separate surface models.** Specify crystal phase, surface orientation, polarity, miscut, substrate/template and surface preparation in each material/recipe record. Neither a material name alone nor a nominal III/V ratio determines morphology. G01, G10 and G11 establish why surface inventory and initial condition matter.

2. **Track metal inventories and signed growth.** Distinguish incident atoms, adsorbed Ga/Al, material incorporated into the solid, droplets, desorbed species and material removed from the exposed layer. A piecewise `min(metal, nitrogen)` law is a useful limiting benchmark. It is not a complete transient growth law near desorption, droplet formation or interruption. G01 provides coverage evidence; G02 motivates an effective-loss model with active-N recapture. Do not double-count desorption and decomposition.

3. **Remove the nitrogen-on equals zero-loss rule.** G02 shows reduced net loss under active-N excess, with regime dependence. Fit and test interruption loss under the actual temperature, polarity, flux and surface condition. Preserve exposed-layer identity when removing material from a multilayer stack.

4. **Remove universal RF scaling and monotonicity requirements.** Replace the proposed power-law/saturating expression with a measured source response or a separately validated plasma model. G04 and G06 justify retaining power, reflected power or matching state where available, flow, aperture condition, species and commissioning history. An ion-free vendor claim needs a detection limit and operating range. A conventional chamber RGA is not automatically a calibrated atomic-N or ion-energy measurement.

5. **Use actual wafer temperature in kinetics.** Thermocouple, heater element and wafer surface temperature must remain distinct variables with instrument forward models. G11 explicitly notes differences between machines and mounting arrangements. Its AlN diagrams must not be relabeled as universal true-surface-temperature maps. The proposal's lower-temperature GaN advantage does not establish the same thermal envelope for AlN growth, cleaning, masks or existing device layers.

6. **Keep concentrations dimensionally correct.** With incorporated dopant flux `J` in atoms/cm²/s and film normal velocity `v` in cm/s, bulk dopant concentration is `J/v` in atoms/cm³. Dividing by a cation-site density converts concentration to a site fraction. The old plan's extra division cannot produce concentration. At zero or negative growth, do not divide by velocity: evolve the surface inventory and record no deposited-volume concentration. Carrier activation, compensation and mobility need independent evidence; they are not implied by incorporation.

7. **Downgrade unsupported morphology and device outputs.** A generic diffusion-length/step-density law cannot validate threading-dislocation density, contact resistance, leakage or polarity inversion. First validate the quantities it actually predicts. G12's contamination correlation and qualitative EDS limits are unsuitable as a universal defect-production coefficient.

8. **Audit material properties by state and temperature.** G07 is useful for GaN Cp; G08 and G09 are useful for conductivity uncertainty and model comparisons. They do not provide the entire chamber property database. Preserve anisotropy where consequential, film thickness/defect dependence, temperature range, and Cp/Cv distinction. Do not silently extrapolate a 400 K measurement or 1000 K calculation to a 1473 K wafer.

9. **Correct the proposal's contamination narrative.** Base UHV and absence of intentional NH3/H2 precursors do not guarantee zero hydrogen, active p-type material or a clean regrowth interface. G11 shows impurity peaks at nucleation even when the grown layer has low impurity levels. G12's study year is 2018; PMC archival availability in 2025 is not a new publication. Neither paper establishes that every planar device interface is clean.

## Model and units contract to add to the plan

These are proposed engineering requirements, not numerical results extracted from the papers.

- Store primary delivered fluxes in atoms/m²/s, separately for each element and active species. Keep raw gauge readings and sensitivity/calibration records. BEP is an instrument reading until converted through an explicit calibration.
- Define every use of monolayer: the relevant surface-site density, whether a cation plane or formula-unit bilayer is meant, and the layer-normal spacing for the orientation. Ga adlayer coverage normalized to GaN sites is not necessarily the number of geometrical metallic layers.
- Express the growth state per wafer location as at least surface material/polarity, Ga and Al inventory, droplet inventory when present, exposed solid stack and signed net incorporation/removal. Introduce more states only when supported by observability and validation.
- Close atom balances over source delivery, reflection/sticking, surface accumulation, incorporation, decomposition and desorption. Check positivity for inventories and conservation through shutter events.
- Store parameters with source ID, source locator, units, value/uncertainty, applicable surface and range, and evidence status: measured on this machine, fitted to external literature, theoretical prior or unfilled requirement. No fitted constants have been created in this reference collection.

## Commissioning measurements needed

| Measurement campaign | Data to retain | What it identifies | Independent check |
|---|---|---|---|
| Per-cell flux calibration and stability | Raw BFM signal, background, sensitivity, cell/thermocouple temperatures, fill level, shutter timing; several wafer-plane positions | Absolute source normalization, spatial delivery and shutter drift | Growth-limited RHEED calibration where applicable plus ex-situ thickness mapping |
| Nitrogen source matrix | Power/flow/matching states, pressure, active-species diagnostic signals, aperture revision; repeated points and hysteresis tests | Delivered reactive flux and state-dependent source response | Metal-excess growth plateau with decomposition accounted for, checked by independent thickness |
| GaN regime and interruption matrix | Temperature calibration, both fluxes, RHEED/QMS traces, hold times and surface preparation | Adlayer/desorption transitions, effective decomposition, restart transients | Hold out temperatures and recipes; compare thickness loss and morphology |
| AlN-specific matrix | Same records plus polarity, nucleation template and cleaning history | AlN growth/desorption regimes and transient inventory | AFM with declared scan size and metric, XRD/STEM where required, independent thickness |
| Regrowth contamination | Preparation history, mask material, exposure times, RGA history, SIMS or APT/EDS detection limits | Surface/near-interface state and contamination uncertainty | Paired preparation controls; device tests only for a separately validated device model |

Do not use the same film-thickness map to both determine active-N flux and claim an independent thickness validation. Spatial holdout points alone do not test a new operating regime. Lock the parameter fit, then run withheld recipes and repeats with sensor uncertainty propagated.

## Laptop feasibility without concealing accuracy loss

A local surface inventory model coupled to resolved wafer temperature and flux is a candidate for the laptop execution path. It saves computation by representing measured surface kinetics at the scale of the requested thickness/coverage observables. It must be tested against the time-dependent regimes above; small error away from a transition does not establish accuracy at the transition. Do not promise that reduction has exactly zero effect.

Atomistic calculations and kinetic Monte Carlo can supply selected mechanisms or reference cases offline. They should not be required for every atom on an 8-inch wafer. When morphology, pattern loading or interface reconstruction is an output, introduce validated feature-scale models and account for their uncertainty. Neither atomistic detail nor a detailed 3D chamber scene establishes predictive accuracy by itself.

Accept any reduction only after declaring its observable, operating range, discrepancy budget and independent comparison. If it fails, refine the model, run the expensive case offline or mark that operating point unsupported. Do not replace missing evidence with smaller uncertainty bars to fit an RTX 5050 laptop budget.

## Remaining evidence gaps

- Actual source/wafer geometry, source charge and aperture revisions, calibration records, thermometry optical stack, wafer/holder contact and emissivity, and chamber material states remain machine-specific inputs.
- The collection does not yet establish Ga/Al cell vapor-pressure coefficients over their operating ranges; cell thermocouple readings require empirical delivery calibration even when a vapor-pressure fit is available.
- High-temperature AlN Cp, optical properties/emissivity of real growing stacks, temperature-dependent substrate/holder data, and validated thermal boundary/contact behavior still require acquisition or measurement.
- AlN decomposition/removal and GaN/AlN interface exchange over the intended mixed-material recipe are not established by the GaN decomposition paper. Doping, activation, compensation and mobility require separate source selection if reintroduced after the undoped GaN/AlN baseline.
- G03 needs original full text; G05/G06 need local full text if numerical extraction is required. No figures have been digitized into numerical calibration datasets. G11 explicitly makes supporting data available from the author on request; contact requires separate user authorization.

All nine saved PDFs parsed and their titles/page counts were checked. Selected G11 Fig. 3 and G12 Fig. 1/Table 1 pages were rendered and visually inspected; their axes, temperature type and sample limitations were verified. Some publisher files emitted recoverable PDF object-table warnings during parsing; the originals were preserved without rewriting. G09's filename includes 2020, but the manifest correctly records the 2019 preprint.

The final attempt on 2026-09-11 to retrieve remaining Crossref metadata and the PMC open-access file locator was rejected by automatic approval review because the account usage limit had been reached. That retrieval was not bypassed. The available files and already reviewed primary evidence were sufficient to finish this planning note; the three missing PDFs remain explicit acquisition gaps.
