# References for predictive validation: 30 September 2026

The immediate main outcome is predictive accuracy for named observables and an operating envelope, established through verification and independent measurements. Wafer-uniformity improvement follows qualification of the relevant predictions. This search prioritizes evidence for that first outcome.

Five new records, R16-R20, are in [the reference manifest](../reference/sources.json) and [combined index](../sources.json). Existing R04, R05 and R13 were revisited rather than duplicated. Access was through publisher, author-institution and author-deposited pages. Three PDFs were subsequently acquired, parsed and visually inspected on relevant pages; their sizes and SHA-256 hashes are in the manifest. Abstracts and exposed section excerpts are explicitly distinguished from full-text review. No simulation settings were changed.

## Acquired material and immediate findings

The reference audit completed on 2026-09-30: 54 source records, 30 usable PDFs, 8 usable HTML artifacts, zero integrity or link issues. This verifies the library, not the physics or benchmark suitability.

- [R13 patent PDF](../reference/R13_US10526723_plasma_aperture.pdf), 18 pages. PDF page 9 contains aperture calculation tables, not dimensioned drawings: 712 versus 4000 holes, diameter 0.008 inch (0.2032 mm). Plate thickness and spatial pattern remain unknown. This supplies concrete hole-count and diameter cases without closing the plate-geometry gap.
- [R16 conference supplement](../reference/R16_Katzer_2019_NAMBE_abstract.pdf), 2 pages. This is the 2019 conference material, not the 2020 journal article. Its temperature/power plot explicitly marks loss of band-edge measurement reliability as the film grows; a benchmark must not treat the entire optical trace as ground truth.
- [R20 author manuscript](../reference/R20_Koblmuller_2007_GaN_growth_modes.pdf), 19 pages. Methods and Fig. 3 inspected. The map is conditional on N flux 4.8 nm/min and template miscut below 0.5 degrees. Successive experiments used one template, so points are not independent wafers. These restrictions must accompany any later benchmark extraction.

## New references and proposed use

| Priority | Reference | Project use | Evidence still needed |
|---|---|---|---|
| High | R16: Katzer et al. (2020), [Growth-induced temperature changes during transition metal nitride epitaxy on transparent SiC substrates](https://doi.org/10.1116/6.0000063) | Candidate test of thermal transients and the difference between sensor readings and substrate temperature. Publisher HTML includes measured signals and radiative interpretation. | Extract conditions, geometry and measurement uncertainty before defining a benchmark. This is a different substrate/film system, not a 200 mm radial-map validation. |
| High | R18: Voulot et al. (1999), [Characterisation of an RF atomic nitrogen plasma source](https://doi.org/10.1016/S0022-0248(98)01361-X) | Absolute nitrogen-output calibration method. Exposed sections describe source and throughput measurements. | Obtain complete figures and error estimates. A single-aperture source does not supply the required multi-hole wafer map. |
| High | R19: Iliopoulos et al. (2005), [Active nitrogen species dependence on radiofrequency plasma source operating parameters and their role in GaN growth](https://doi.org/10.1016/j.jcrysgro.2005.01.013) | Evidence to challenge the assumption that all growth-active nitrogen can be represented by ground-state atomic N. | Read with G04 and R12; resolve differences in source conditions and diagnostics. OES trends alone do not set absolute arriving flux. |
| Medium | R17: Albert, Golla and Meier (2021), [Optical in-situ temperature management for high-quality ZnO molecular beam epitaxy](https://doi.org/10.1016/j.jcrysgro.2020.126009) | Thermometry and FEM comparison lead for the observation model. [Institutional metadata](https://ris.uni-paderborn.de/record/20900) confirms authors and publication. | Full text unavailable in the institutional record. Do not select it as the replacement for R03 until geometry, observations and uncertainties are inspected. |
| Medium | R20: Koblmuller et al. (2007), [In situ investigation of growth modes during plasma-assisted molecular beam epitaxy of (0001)GaN](https://doi.org/10.1063/1.2789691) | Candidate growth-regime test against temperature and Ga/N predictions. | Manuscript acquired; assess shared-template dependence and overlap with calibration sources before reserving holdouts. The 2024 repository deposit is not the publication year. |

These priorities are project judgments, not claims that the papers already constitute usable validation datasets. Each candidate needs a reconstruction check: input geometry, boundary conditions, measured observable, measurement error and independence from calibration.

## Useful progress on existing leads

- **R13, aperture geometry:** the [patent text](https://patents.google.com/patent/US10526723B2/en) and PDF were acquired. Figures 7 and 8 tabulate original and modified apertures, with a reported 5.6-fold conductance change. Their hole counts and diameter support representative inputs, but do not establish a complete plate drawing or independent validation.
- **R05, thermal edge effects:** the [publisher page](https://doi.org/10.1016/j.jcrysgro.2008.09.204) describes experimental temperature maps while varying backing rings, platen spacing and emissivity. This remains a useful spatial-thermal candidate, but the complete geometry and uncertainty are needed before committing to reconstruction.
- **R04, multizone heater:** the [publisher page](https://www.sciencedirect.com/science/article/pii/S1359431125014565) identifies a 7 x 6-inch system. It should not be treated as a single-wafer 200 mm alternative merely because it studies uniformity. Full-text acquisition remains open.

## What this search did not resolve

**Neutral Ga-Ga collisions.** Searches for gallium vapor collision cross-sections, transport cross-sections and interatomic potentials did not yield a verified neutral Ga-Ga transport model at the source temperatures. Electron-Ga scattering, ion/cluster cross-sections, and solid/liquid potentials are not direct replacements for the DSMC diameter. Keep the existing bracket explicitly unsourced. A future potential-based calculation would itself need a justified gas-phase potential, scattering calculation and transport-model fit.

**Complete thermal benchmark.** R16 adds a promising transient case and R17 a measurement-method lead; neither currently closes the need for a reconstructible 200 mm spatial benchmark. R03 has not been replaced by this search.

**200 mm nitrogen map.** R18 improves absolute-output evidence and R13 provides hole counts and diameter, but no independently measured 200 mm active-N map with matching plate geometry was acquired.

## Recommended acquisition and validation order

1. Screen R16 and R05 for reconstructible thermal conditions and usable uncertainty; choose the observable before building geometry.
2. Use R13's verified hole counts and diameter as candidate inputs while seeking thickness and pattern; obtain R18 full figures. Keep source-output calibration separate from wafer-plane distribution validation.
3. Reconcile R19 with the existing nitrogen evidence before extending the boundary species model.
4. Extract R20's conditional growth map and decide which cases can remain independent tests of the growth-regime model.
5. Continue the Ga transport-data search without substituting an unrelated cross-section. Propagate that uncertainty into every Ga prediction meanwhile.
