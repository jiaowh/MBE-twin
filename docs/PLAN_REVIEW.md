# Review of the chamber proposal and inherited simulation plans

Reviewed 2026-09-11. This is an engineering planning review, not a chamber qualification or a solver validation report.

## Decision

Follow-up: the user subsequently supplied the sibling legacy simulator. The initial statement below about files absent from this checkout remains historical; the external code has now been inspected in [LEGACY_SIM_REVIEW.md](LEGACY_SIM_REVIEW.md). The active implementation plan incorporates those code-backed lessons without changing the legacy project.

Retain the proposed growth-chamber architecture and develop a GaN/AlN twin in stages. Replace the old implementation schedule and asserted results with machine-specific inputs, numerical verification, independent measurements and a laptop performance gate. The architecture in [mbe_twin.md](../mbe_twin.md) is a useful foundation; the updated [Phase-1 plan](../PHASE1_CHAMBER_PLAN.md) defines the current scope and work order.

The original PowerPoint remains the source proposal. The review covers its engineering text, including tables, extracted from all 19 slides in [SLIDE_TEXT.md](../ref/proposal/SLIDE_TEXT.md). Illustrations have not been treated as dimensioned CAD. Original Markdown files are preserved in [ref/archive](../ref/archive/). No source code, test suite, CAD, vendor purchase specification or machine measurements existed in this checkout at review start.

## Proposal traceability and proposed edits

Slide numbers below are physical slide positions, since some printed slide numbers differ. Replacement wording is intended for the engineering plan and any later revision of the proposal deck.

| Slides | Finding | Required change or replacement wording |
|---|---|---|
| 1, 7, 17, 19 | The hardware project includes growth and anneal modules. The initial twin should concentrate on the growth chamber. | “Phase 1 hardware includes the growth and anneal modules. The first twin release covers the growth chamber, with measured incoming-wafer and vacuum-interface conditions representing adjacent modules.” The user confirmed this exclusion of transfer and anneal modules from the twin on 2026-09-07. |
| 7, 8, 12, 19 | “8-inch” does not specify 200 mm versus exactly 203.2 mm. | State the actual nominal wafer and platen dimensions, tolerances and edge exclusion. Keep 200 mm and 203.2 mm as different configuration candidates until drawings resolve this. |
| 8 | Heater capability is described as 1200 °C in reactive gas without defining the measured object. | “Confirm whether 1200 °C is a wafer, holder or element rating, including atmosphere, dwell time, uniformity, power and service-life limits.” Do not convert this to a guaranteed 1473 K wafer boundary. |
| 8, 11 | Multi-zone heat balancing lacks a zone design and sensor layout. | Specify zone geometry, independent power channels, electrical/thermal coupling, sensor locations and calibration. A single spot cannot independently verify an entire wafer map. Test observability and cross-coupling before controller design. |
| 8 | Three Ga and three Al sources plus Si and Mg account for eight of ten positions. | Define the two spare positions, shutters, service clearances and actual source model for each occupied port. Distinguish port count from simultaneously installed/operable sources. |
| 8 | PBN is listed generically for all cells. | Confirm each crucible grade, lip geometry, fill range and compatibility with its charge. Ga hot-lip and Al cold-lip/cold-neck designs require different models. See [hardware evidence](../ref/notes/HARDWARE_EVIDENCE.md). |
| 8, 11 | 600 W and 13.56 MHz describe a source input, not an active-N flux or uniformity specification. | Specify forward/reflected/absorbed power conventions, gas-flow reference state, source aperture, species/energy/angular output maps and the wafer-plane calibration. Treat “ion-free” as a verification requirement with a detector threshold. |
| 8, 19 | Base pressure is a target; nominal turbo speed does not establish chamber pressure. | Specify species-dependent effective speed at the chamber, port conductance, background load, bake configuration, gauge location and detection limit. Separately report base and plasma-on conditions. |
| 5 | Low growth temperature and the absence of intentional hydrogen precursors do not guarantee clean interfaces or activated p-type material. | “PAMBE enables a process-dependent thermal budget without intentional NH3/H2 feed. Interface contamination and dopant activation require independent characterization.” GaN and AlN need separate growth windows. |
| 5 | “Regrown crystal inherits every defect” and guaranteed monolayer-abrupt n+ regions overstate what diagnostics establish. | “Initial damage, contamination, polarity and template defects influence regrowth. RHEED provides surface-sensitive observations; abruptness and electrical quality require additional measurements.” |
| 5 | “NIST 2024” is an incomplete citation. | A related verified NIST-authored contamination study is Blanchard et al., *Crystals* (2018), DOI 10.3390/cryst8040178. It examines nanowire interfaces and Al/O contamination. Do not silently substitute it as evidence for all planar-device or Si-contamination claims. See the [growth evidence](../ref/notes/GROWTH_EVIDENCE.md). |
| 2–4 | Device demonstrations are motivation, not chamber calibration datasets. | Record full DOI, device structure, growth method and measurement conditions before using a paper. Treat incomplete author/year fragments as unresolved citations. |
| 12, 16, 19 | First epitaxy, MQW and regrowth milestones lack quantitative acceptance definitions. | Define temperature/flux/thickness maps, material stack, morphology, defect/composition measurements, repeatability and measurement uncertainty before accepting each milestone. GaN/AlN layers are the first twin scope. InGaN MQWs require an identified In source and a new kinetics validation campaign. |
| 8, 17 | Handling/robotics appear in the specification but 12-inch hub/robotics are deferred in the budget. | Create an interface drawing and scope matrix identifying Phase-1 handling, transfer valve and pumping hardware. Reserve sufficient geometry and utilities for Phase 2 without claiming a validated 300 mm growth process. |
| 15, 17, 18 | Hardware budgets and schedule do not identify a twin development or calibration-data allocation. | Add named owners and work for drawings, source maps, spatial thermometry, material characterization, software, uncertainty analysis and independent validation wafers. Estimate cost/time after the first solver and data-access demonstrations. Existing proposal targets remain targets. |

The commercial, market-share, export-control, patent, staffing and procurement claims in the deck were not independently audited. They must not become simulation inputs or evidence of physical feasibility. No supplier was contacted and no purchase was made.

## Corrections to the inherited chamber plan

The archived September 7 plan proposes edits to an absent `mbe_sim` codebase. Its “measured with current code” tables, 10/30 ms timings, 8–10 session estimate, line counts and asserted test results cannot be reproduced in this repository. They have been removed from the active implementation plan.

| Old assumption | Correction and consequence |
|---|---|
| A nitrogen-limited rate has no thermal dependence | Even the proposed expression retains `J_N - R_dec(T)`. Surface coverage, decomposition and morphology can vary with temperature. Validate a regime-specific law rather than flattening thickness by construction. |
| Al-rich AlN is not standard, so set a universal N-rich default | AlN literature includes Al-rich growth windows and metal adlayer effects. Do not transplant a GaN recipe or choose a universal V/III value. Separate material, polarity, substrate and growth mode. |
| Three identical azimuthally separated Ga sources flatten the rotation-averaged radial shape | Under complete uniform rotation, each identical source has the same radial average. Added sources scale amplitude and can reduce instantaneous azimuthal modulation. A radial shape change requires different geometry/distributions. |
| A fixed 5 s beam cache or averaged rotation preserves the answer | Key caches by all relevant geometry, shutter, temperature/fill and surface states. Resolve events and nonlinear surface memory. Compare time/angle resolutions on local maps and interfaces. |
| Zone conduction may simply be ignored | Shared plates, supports and radiative exchange couple zones. Use a full reference model and demonstrate a small error before removing a path. |
| Every cell obeys approximate unverified vapor coefficients and prescribed time constants | Audit phase, temperature range, pressure units and original coefficients. Measure cell/charge thermal behavior and wafer-plane flux. A fitted cell calibration is not a vapor-pressure standard. |
| Plasma power can be normalized so that 600 W always achieves the intended rate | Determine active-N delivery independently. The source may fail the proposed rate or uniformity target. The model must be allowed to predict that failure. |
| Pump speeds add directly; cryopumps pump H2 poorly | Use species-dependent conductance and actual pump curves, cryosorption/loading and regeneration state. Broad rules cannot replace the selected pump specification. |
| Base pressure after bake is assigned to the proposal target | Predict from leak/outgassing/pumping or use an explicitly measured boundary. A target value is not a successful validation. |
| BFM insertion pauses deposition everywhere | Resolve the actual obstruction and operating procedure. Partial shading and ongoing unblocked deposition are possible. |
| Band-edge thermometry reads true substrate temperature plus random noise | Identify the optical measurement and calibrated layer/temperature range. Fit uncertainty, signal quality, reflections, film stack and viewport condition belong in the observation model. |
| An N-on interruption removes exactly no material | Track finite metal inventories and signed material evolution. Active nitrogen can suppress decomposition without establishing zero loss. |
| Subtracting thickness is sufficient to remove a multilayer | Remove the exposed layer with its composition, stress and inventory. Recompute geometry/history consistently. |
| Dopant concentration equals flux divided by growth velocity and site density | Flux/velocity gives concentration; division by site density gives a dimensionless fraction. Electrical activation is a different model and remains deferred. |
| Template GaN means zero stress and a simple diffusion-derived TDD is predictive | A template can retain strain, dislocations and contamination. Growth stress, relaxation and defect evolution require independent models and data. |
| A 12-inch model is only a larger radius | Reassess heater, holder, flux, pumping, sensing, bow and validation. Also distinguish 300 mm from exactly 304.8 mm. |
| Calibration can be the final work package | Acquire and reserve data before fitting; validate each subsystem and the coupled result on held-out physical runs. |

The [master physics plan](../mbe_twin.md) supplies equations and verification cases. The [reference index](../ref/README.md) identifies source scope, access status and local copies. Literature values are priors until applicability to the actual build is established.

## Missing engineering inputs before machine-specific predictions

1. Dimensioned chamber and source/wafer/holder/heater/shutter drawings in one coordinate system, including tolerances and service configuration.
2. Exact wafer stack, polarity, orientation, diameter, thickness, backside finish/coating, clips/contact regions and incoming bow.
3. Temperature-dependent material and optical properties with applicable sample form and uncertainty. Bulk ceramic AlN values cannot silently stand in for epitaxial films.
4. Electrical power and time histories for every heater/source channel, plus cooling temperatures and zone coupling.
5. Absolute Ga, Al and active-N maps with instrument response, repeatability, source fill, shutters and rotation state recorded.
6. Pump curves, duct/valve geometry, leak/outgassing estimates, gas purity, MFC calibration, pressure/RGA response and cryopump loading.
7. Recipe events, actuator delays, rotation phase and instrument timestamps on a shared time basis.
8. Separate calibration and validation wafers with registered thickness/temperature/roughness maps and measurement uncertainty.

These gaps do not prevent benchmark development. They prevent claiming that a generic geometry or literature-calibrated model predicts this particular chamber accurately.
