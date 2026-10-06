# Research-gap search, 2026-10-06 (R32-R41)

This search covers the open inputs that limit the twin now that the transport, heater and controller models are in place. It is not a validation.

The earlier searches (R16-R31) closed the Ga collision diameter, Bi2, Ga2, the plate-hole data, the crucible patents and the emissivities. The remaining gaps, and what this search found for each:

| Gap | Why it matters in the twin | Found | Status |
|---|---|---|---|
| Ga droplet onset near 710 C | Sets the Ga-rich edge of the growth window. The three scenarios disagree by 3-4x. | R32: adlayer desorption measured at 676-708 C | **New evidence**; see below |
| BFM and rate-monitor accuracy (priors 2 % and 1 %) | The BFM is the most important instrument for staying in the window (section 12) | R32: relative Ga flux to better than 2 % with a retractable ion gauge; R34: no accuracy stated | **2 % prior now has one literature basis** (relative flux, one lab) |
| Pyrometer reading error (budget 1-2 K) | Above about 3 K in total, the working point moves | R32: about 0.5 C step from reflected Ga-cell radiation at shutter operation, plus adlayer emissivity changes | **Quantified error terms**; not yet in the budget |
| N wall recombination (gamma) | Commissioning cannot separate gamma from eta (factor 1.4-1.6) | R36: 0.07 on stainless steel under ion bombardment; R37: about 1e-3 on nitrided iron and 2e-5 on quartz without it | **Bracketed far below the twin's cases**; see below |
| Active-N output and eta | eta 0.06-0.57 decides B-p versus B-L | R41: eta at the source exit 0.40 falling to 0.10 as source pressure rises; R40: 0.86 um/h from 2 x 4 sccm on a Gen20A | **eta = 1 not supported**; see below |
| Crystal quality at 710-720 C | The real cold limit; not modelled | R39: plasma GaN at 700-720 C is smooth but leaves >1e10 cm^-2 dislocations with that buffer | **Quality cost confirmed**, buffer-dependent |
| Wafer bow on 200 mm GaN-on-Si | Changes the heater view and pyrometer spot | R38: radiatively heated wafers do not change temperature with bow up to 0.3 m^-1 | **Neglect supported** (50 mm evidence) |
| Rotation rate | The twin uses rotation-averaged maps | R33: about 1 ML per rotation or less was needed for a uniform 2-inch wafer | **New condition**; see below |
| What uniformity is achievable | Context for the +/-0.5 % results | R35: best of 9 vendors' 75 mm wafers 0.5 % sd, 1.3 % TTV | **Context** |
| N-source spatial distribution (UNI-Bulb, Riber 49 source) | Pointing is the largest worst-case driver | Nothing published beyond R13/R26/R30; Riber/CRHEA state only that the source was optimized for uniformity | **Still a gap**; commissioning measurement |
| Thickness-map precision (0.1-0.3 % assumed for the re-aim) | Sets the re-aim residual | Tool vendors and 200 mm GaN papers report uniformity, not repeatability | **Still a gap**; ask the metrology supplier |

## R32: Ga adlayer desorption at the working temperatures

- **Conditions:** Zhang et al. (Paul-Drude-Institut, arXiv May 2026) dosed Ga onto GaN(0001) without nitrogen. They watched the adlayer with RHEED, laser reflectometry, line-of-sight QMS and a pyrometer at once.
- **Result:** the adlayer desorption rate constant is 0.118 / 0.068 / 0.04 s^-1 at 708 / 693 / 676 C, with a maximum adlayer of 2.4 ML. The activation energy is 2.87 +/- 0.04 eV.
- **Against the twin's scenarios** (`data/parameters/gan_growth.json`, droplet_onset):

| T | R32 max adlayer desorption flux | G01_adsorption (5.1 eV) | Heying_growth (4.8 eV) | Ref14_growth (2.8 eV) |
|---|---|---|---|---|
| 708 C | 0.28 ML/s | 0.13 | 0.22 | 0.41 |
| 693 C | 0.16 | 0.05 | 0.09 | 0.25 |
| 676 C | 0.10 | 0.02 | 0.03 | 0.14 |

- **Reading:** at 708 C R32 lies inside the existing scenario range, between Heying and Ref14. Its temperature dependence agrees only with Ref14 (2.8 eV). The two 4.8-5.1 eV scenarios fall 1.3-5x below it over 676-708 C.
- **Caveat on temperature:** R32 measures temperature with a pyrometer that sees a Ti-coated back side through the GaN, at an assumed emissivity of 0.55. Its absolute temperatures can be offset by several kelvin. The slope (2.87 eV) is more robust than the level.
- **Caveat on N:** R32 has no N flux. The twin's scenarios include growth-condition onsets. G01's scenario was also measured without N.
- **Decided 2026-10-06:** R32 is recorded as a cross-check in `data/parameters/gan_growth.json` (droplet_onset.cross_check_R32), not as a fourth scenario. It lies inside the existing range at 708 C, has no N flux, and adding it would not move the worst case. The machine's own droplet onset stays a commissioning measurement.

R32 also bears on the instruments:
- **BFM:** relative Ga flux to better than 2 % with a retractable ion gauge, and absolute flux to 5 % from thickness. That is the first literature basis for the twin's 2 % BFM prior, as a relative-flux precision in one lab.
- **Pyrometer:** opening or closing the Ga shutter steps the reading by about 0.5 C, from reflected cell radiation. The cell's radiation also really heats the wafer, and the adlayer changes the emissivity. These terms belong in the 1-2 K reading budget. The twin's pyrometer bias states are static.
- **Laser reflectometry (650 nm)** responds to the adlayer and droplets as well as to thickness. A rate monitor of that kind needs the transients separated from the thickness signal.

## R33: rotation rate

At 520 nm/h, rotating at 20 rpm (about 2 ML per rotation) left most of a quarter 2-inch wafer without the intended 2D hole gas. At 30 rpm (about 1 ML per rotation) a full 2-inch wafer was uniform.

The twin treats the wafer as rotation-averaged. At 1 um/h (1.07 ML/s), 1 ML per rotation needs about 64 rpm, more than many production manipulators run. This is a growth-quality observation, not a thickness one. It is now a question in the manipulator request (HARDWARE_REQUESTS section 5) and a caveat on the rotation-averaged maps.

## R35: what uniformity is achievable

FBH's ESA benchmarking of nine vendors' AlGaN/GaN wafers on 75 mm SiC found GaN buffer thickness standard deviations of 0.5 % (TTV 1.3 %) for one of the best and 3.2 % (TTV 9 %) for a moderate one.

The twin's worst-case half-range of +/-0.53 % at 200 mm compares with about +/-0.65 % (TTV/2) for the best 75 mm wafers. It is a demanding target at four times the area. The twin's figure is a worst case over modelled states, not a measured spread.

## Full-text review of R36-R41 (saved by the user, 2026-10-06)

All six were read in full. Two provisional statements were wrong: R37 measures quartz versus temperature and iron only at room temperature, not "various surfaces versus temperature"; and the "stainless steel 1.8e-3" figure in the first search's results came from neither paper.

**Nitrogen wall loss (R36, R37) reverses how the twin's gamma cases read.**
- In the twin, gamma is the chance that an N atom hitting the chamber wall is lost (`src/mbe_twin/scattering.py`). Baseline 1; 0.1 is labelled the upper "walls return N" case.
- R36 measured 0.07 +/- 0.02 on stainless steel inside an N2 plasma, that is, with ion bombardment, and expects that to be about 30 % high. It warns that gamma may differ without ions and depends on the wall's history.
- R37 found 6.7e-4 on iron that had nitrided with no sputtering, and about 2e-5 on quartz (weakly temperature dependent, Eley-Rideal). Literature values for one material scatter by 100x with surface state.
- MBE walls see no ion bombardment and are nitride- or Ga-coated cryopanels near 77 K, which no source covers. Ga-coated areas could consume N by forming GaN, which would act like a high gamma.
- **Consequence:** gamma = 1 is not a supported baseline, and 0.1 is not an upper case: much lower values (1e-3) are plausible. **Implemented 2026-10-06:** `scattering.track` has an optional pump that removes wall-returned atoms (loss per wall hit gamma + (1 - gamma) S / (A <v> / 4)), and a gamma 1e-3 bracket for B-L was run (LAYOUT_COMPARISON section 10). The arrival factor at the operating pressure rises from 1.15 to 3.8. The worst case for passing states is unchanged in that one case. The nitrogen needed for 1 um/h falls from about 19 to 5.6 sccm. The throttle series in COMMISSIONING_PLAN.md (C6b) is designed to separate gamma from eta and becomes more important.

**Source efficiency (R41, R40).**
- R41 measured an SVTA RF 4.5 (single 2.8 mm aperture) directly. The dissociation fraction, which equals eta at the source exit, is 0.40 at 0.07 Torr source pressure and falls to about 0.10 at 0.50 Torr (500 W). The atom flux peaks at 0.85e18 s^-1. The low-pressure end corresponds to roughly 1-2 sccm.
- So eta = 1 (the B-p scenario) is not supported by any measured source. What sets eta is the bulb pressure, which a high-conductance plate keeps low at high flow. That is the B-L plate's design logic. An older single-aperture source is not a UNI-Bulb, so the numbers are indicative.
- R40 (Fraunhofer IAF, Veeco Gen20A) grew N-limited GaN at 0.86 um/h with two UNI-Bulb sources at 400 W and 4 sccm each. Rate per flow from the sources so far:

| Source | Machine | Rate / flow | um/h per sccm |
|---|---|---|---|
| R40 | Veeco Gen20A (4-inch), 2 UNI-Bulb | 0.86 um/h / 8 sccm | 0.11 |
| R33 | Veeco Gen10 | 0.52 / 2 | 0.26 |
| R39 | Riber Compact 21, Addon RF | 0.5 / 1.8 | 0.28 |
| R26 | Riber 32, UNI-Bulb, high-conductance plate | 6.1 / 15 | 0.41 |
| R13 | patent example | 1.3 / 1.3 | 1.0 |

The throws differ and are mostly unpublished, so these are not etas. The production-type Gen20A sits lowest, as a longer throw would. The twin's B-L working point (1 um/h at about 19 sccm, 0.05 um/h per sccm at a 200 mm throw) is the same order.

**Wafer bow and pyrometry (R38).**
- CRHEA found that radiatively heated wafers in MBE do not change temperature as they bow, up to 0.3 m^-1 (unlike MOCVD). On a 200 mm wafer that curvature is about 1.5 mm of sag. This supports the twin's neglect of bow. The evidence is from 50 mm wafers.
- A plain IR pyrometer (0.91-0.97 um) showed +/-20 C oscillations from GaN thin-film interference and about 20 C absolute offset. An emissivity-corrected instrument (EpiTT) removed them, and its optical head cut parasitic source radiation to about 2 K. The twin's 1-2 K reading budget presumes such a corrected instrument, and source radiation alone can use most of it. With R32's 0.5 C shutter step, this is now a specification in HARDWARE_REQUESTS (section 4): emissivity-corrected, with source-radiation rejection.

**Crystal quality at the working temperature (R39, R40).**
- CRHEA grew plasma GaN at 700-720 C (1.8 sccm, 400 W, Ga-rich, 0.5 um/h). The growth front was flat, but dislocations turned vertical and were filtered poorly: above 1e10 cm^-2. The better ammonia-grown 800 C layers reached below 5e9 cm^-2 and 2000 cm^2/Vs.
- The low temperature kept more compressive stress, which helps against cracking on cooling.
- R40 shows that a buffer which fully compensates the strain gives both the flattest wafer and among the lowest dislocation densities. Its growth temperature is not stated in this paper.
- **Consequence:** the twin's uniformity optimum at 710 C may carry a crystal-quality cost that depends on the buffer design. The cold limit should be a growth-quality decision informed by these, not only the growth window. The twin does not model it.
