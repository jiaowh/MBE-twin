# Reference library

New search, 2026-09-30: [references for predictive validation](notes/VALIDATION_REFERENCE_SEARCH_2026-09-30.md), including sources R16-R20, access limits and follow-ups. These are reference acquisitions, not completed validation cases.

Second search, 2026-09-30: [physics data for the open Stage A questions](notes/PHYSICS_DATA_SEARCH_2026-09-30.md), sources R21-R31 and the R05 full text: Bi2 and the R07 rate deficit, a Ga collision-diameter bracket, Ga2, nitrogen plate holes, depletion-resistant crucibles, emissivities and heater-uniformity mechanisms.

Compiled 2026-09-13. This is an acquired evidence collection for the GaN/AlN chamber plan. Literature and comparator specifications do not validate this custom chamber.

Read the annotated reviews: [growth/materials](notes/GROWTH_EVIDENCE.md), [hardware](notes/HARDWARE_EVIDENCE.md), and [solver/fidelity](notes/SOLVER_AND_FIDELITY.md) and [representative chamber](notes/REFERENCE_CHAMBER.md). The [combined manifest](sources.json) preserves the detailed source records; [integrity report](integrity_report.json) records file checks. Original-source copyright and license terms remain applicable.

The [proposal text](proposal/SLIDE_TEXT.md) comes from all 19 supplied slides. [Archived plans](archive/) preserve the pre-review drafts. These are project inputs, separate from externally acquired evidence.

## Papers and material properties

| ID | Source | Local copy or access status |
|---|---|---|
| G01 | [Gallium adsorption on (0001) GaN surfaces](https://doi.org/10.1103/PhysRevB.67.165419) (2003) | [PDF](growth/G01_Adelmann_2003_Ga_adsorption.pdf) |
| G02 | [In situ GaN decomposition analysis by quadrupole mass spectrometry and reflection high-energy electron diffraction](https://doi.org/10.1063/1.2968442) (2008) | [PDF](growth/G02_Fernandez_Garrido_2008_GaN_decomposition.pdf) |
| G03 | [Growth diagram and morphologies of AlN thin films grown by molecular beam epitaxy](https://doi.org/10.1063/1.1575929) (2003) | URL only / local source unavailable; see detailed manifest |
| G04 | [Role of atomic nitrogen during GaN growth by plasma-assisted molecular beam epitaxy revealed by appearance mass spectrometry](https://doi.org/10.1063/1.2734390) (2007) | [PDF](growth/G04_Osaka_2007_atomic_N.pdf) |
| G05 | [Plasma-assisted Molecular Beam Epitaxy of N-polar InAlN-barrier High-electron-mobility Transistors](https://pmc.ncbi.nlm.nih.gov/articles/PMC5226270/) (2016) | URL only / local source unavailable; see detailed manifest |
| G06 | [Plasma assisted molecular beam epitaxy of GaN with growth rates >2.6 µm/h](https://www.sciencedirect.com/science/article/pii/S0022024813006751) (2014) | URL only / local source unavailable; see detailed manifest |
| G07 | [Heat capacity of alpha-GaN: Isotope effects](https://arxiv.org/abs/cond-mat/0503522) (2005) | [PDF](growth/G07_Kremer_2005_GaN_heat_capacity.pdf) |
| G08 | [Thermal conductivity of crystalline AlN and the influence of atomic-scale defects](https://arxiv.org/abs/1904.00345) (2019) | [PDF](growth/G08_Xu_2019_AlN_thermal_conductivity.pdf) |
| G09 | [Thermal conductivity of AlN, GaN, and AlxGa1-xN alloys as a function of composition, temperature, crystallographic direction, and isotope disorder from first principles](https://arxiv.org/abs/1910.05440) (2019) | [PDF](growth/G09_Dagli_2020_nitride_thermal_conductivity.pdf) |
| G10 | [Molecular beam homoepitaxy of N-polar AlN: Enabling role of aluminum-assisted surface cleaning](https://doi.org/10.1126/sciadv.abo6408) (2022) | [PDF](growth/G10_Zhang_2022_Npolar_AlN_cleaning.pdf) |
| G11 | [Surface control and MBE growth diagram for homoepitaxy on single-crystal AlN substrates](https://doi.org/10.1063/5.0010813) (2020) | [PDF](growth/G11_Lee_2020_AlN_growth_diagram.pdf) |
| G12 | [Characterization of Sub-Monolayer Contaminants at the Regrowth Interface in GaN Nanowires Grown by Selective-Area Molecular Beam Epitaxy](https://www.mdpi.com/2073-4352/8/4/178) (2018) | [PDF](growth/G12_Blanchard_2018_regrowth_contaminants.pdf) |

Details: [growth/sources.json](growth/sources.json).

## Chamber and component specifications

| ID | Source | Local copy or access status |
|---|---|---|
| H01 | [MBE 49 production system](https://www.riber.com/product/mbe-49/) (RIBER) | [HTML](hardware/H01_RIBER_MBE49_product.html), [PDF](hardware/H01_RIBER_MBE49_legacy_brochure.pdf) |
| H02 | [RF-6.02 Plasma Source](https://www.svta.com/uploads/documents/RF_6.0.pdf) (SVT Associates) | URL only / local source unavailable; see detailed manifest |
| H03 | [Heated insert cell for Ga & In — ABI](https://www.riber.com/product/heated-insert-cell-for-ga-in-abi/) (RIBER) | [PDF](hardware/H03_RIBER_Ga_ABI.pdf), [HTML](hardware/H03_RIBER_Ga_ABI_product.html) |
| H04 | [Aluminum source ABN BF CL & CN](https://www.riber.cn/wp-content/uploads/2023/05/RIBER_Aluminum-source-ABN-BF-CL-CN.pdf) (RIBER) | URL only / local source unavailable; see detailed manifest |
| H05 | [Substrate manipulators / deposition stages SH](https://www.mbe-komponenten.de/pdf/data-sheet-sh.pdf) (Dr. Eberl MBE-Komponenten) | [PDF](hardware/H05_Eberl_substrate_manipulator_SH.pdf) |
| H06 | [kSA GaN BandiT Temperature Monitor application note](https://www.k-space.com/wp-content/uploads/kSA_BandiT_for_GaN-1.pdf) (k-Space Associates) | [PDF](hardware/H06_kSA_BandiT_GaN.pdf) |
| H07 | [MAG integra operating instructions](https://fr.shop.leybold.com/medias/300324726-002-Instructions.pdf?attachment=true&context=bWFzdGVyfHJvb3R8MzM0NjEwOHxhcHBsaWNhdGlvbi9wZGZ8YUdZM0wyZzVZUzg0TnpBMk1UWXdNRFk1T0RNNU9DOHpNREF6TWpRM01qWmZNREF5WDBsdWMzUnlkV04wYVc5dWN5NXdaR1l8MTNiNDk2ZjE1NzkxMzczMjRkMzZiMDMwYjcwZjg0MmM1NTkzMWIwNmY1OTY2YmY3NjY2MDc3Nzk2Y2FlZWY2Yw) (Leybold) | [PDF](hardware/H07_Leybold_MAG_integra.pdf) |
| H08 | [CTI-Cryogenics Cryo-Torr Cryopumps line catalogue](https://www.edwardsvacuum.com/content/dam/brands/edwards-vacuum/edwards-website-assets/our-markets/chamber-solutions/cti-datasheets/Edwards%20CTI-Cryogenics%20Cryo-Torr%20Cryopumps%20Line%20Catalogue.pdf) (Edwards) | [PDF](hardware/H08_Edwards_CryoTorr_catalogue.pdf) |
| H09 | [RHEED-30 electron source](https://staibinstruments.com/rheed-30/) (STAIB Instruments) | [HTML](hardware/H09_STAIB_RHEED30.html) |
| H10 | [Beam Flux Monitor](https://svta.com/components/real-time-monitoring/beam-flux-monitor/) (SVT Associates) | URL only / local source unavailable; see detailed manifest |
| H11 | [Transpector MPH Operating Manual](https://www.inficon.com/media/4281/download/074-555-P1C-Transpector-MPH-Operating-Manual.pdf?inline=true&language=en&v=1) (INFICON) | URL only / local source unavailable; see detailed manifest |
| H12 | [UHV Pumps — full line catalogue](https://www.leybold.com/content/dam/brands/leybold/downloads/catalogue-chapters-pdf/110_EN_UHV%20Pumps.pdf) (Leybold / Gamma Vacuum) | [PDF](hardware/H12_Leybold_UHV_pumps.pdf) |

Details: [hardware/sources.json](hardware/sources.json).

## Solvers and numerical methods

| ID | Source | Local copy or access status |
|---|---|---|
| M01 | [GeForce RTX 50 Series Laptop GPUs: specifications](https://www.nvidia.com/en-us/geforce/laptops/50-series/) (NVIDIA) | [HTML](methods/M01_nvidia_rtx50_laptop_specs.html) |
| M02 | [Gmsh Reference Manual](https://gmsh.info/doc/texinfo/gmsh.pdf) (Gmsh project) | [PDF](methods/M02_gmsh_reference.pdf) |
| M03 | [Elmer Models Manual](https://www.nic.funet.fi/index/elmer/doc/ElmerModelsManual.pdf) (CSC - IT Center for Science) | [PDF](methods/M03_elmer_models_manual.pdf) |
| M04 | [Molflow 2.6 algorithm](https://molflow.docs.cern.ch/guide/molflow/general/attachments/molflow_algorithm.pdf) (CERN) | [PDF](methods/M04_molflow_algorithm.pdf) |
| M05 | [SPARTA manual: Accelerating SPARTA performance](https://sparta.github.io/doc/Section_accelerate.html) (SPARTA project) | [HTML](methods/M05_sparta_acceleration.html) |
| M06 | [COMSOL 6.4: The Molecular Flow Module Physics Interface Guide](https://doc.comsol.com/6.4/doc/com.comsol.help.molec/molec_introduction.2.03.html) (COMSOL) | [HTML](methods/M06_comsol_molecular_interfaces.html) |
| M07 | [The Plasma Module User's Guide](https://doc.comsol.com/6.4/doc/com.comsol.help.plasma/PlasmaModuleUsersGuide.pdf) (COMSOL) | [PDF](methods/M07_comsol_plasma_6_4_manual.pdf) |
| M08 | [Reduced-Basis Approximations and A Posteriori Error Bounds for Nonaffine and Nonlinear Partial Differential Equations: Application to Inverse Analysis](https://www.mit.edu/~cuongng/publication/pub31/pub31.pdf) (Singapore-MIT Alliance) | [PDF](methods/M08_nguyen_reduced_basis_thesis.pdf) |
| M09 | [Examining Spatial (Grid) Convergence](https://www.grc.nasa.gov/www/wind/valid/tutorial/spatconv.html) (NASA Glenn / NPARC Alliance) | [HTML](methods/M09_nasa_grid_convergence.html) |
| M10 | [SPARTA Features](https://sparta.github.io/features.html) (SPARTA project) | [HTML](methods/M10_sparta_features.html) |

Details: [methods/sources.json](methods/sources.json).

## Representative chamber and published test cases

| ID | Source | Local copy or access status |
|---|---|---|
| R21 | [Handbook on Lead-bismuth Eutectic Alloy and Lead Properties, Materials Compatibility, Thermal-hydraulics and Technologies, 2015 edition (section 2.8, saturation vapour pressure)](https://www.oecd-nea.org/jcms/pl_14972/handbook-on-lead-bismuth-eutectic-alloy-and-lead-properties-materials-compatibility-thermal-hydraulics-and-technologies-2015-edition) (2015) | [PDF](reference/R21_NEA_2015_LBE_handbook_s2.8_vapour_pressure.pdf) |
| R22 | [C6 coefficients and dipole polarizabilities for all atoms and many ions in rows 1-6 of the periodic table](https://doi.org/10.1021/acs.jctc.6b00361) (2016) | [PDF](reference/R22_Gould_Bucko_2016_C6_polarizabilities.pdf) |
| R23 | [Dissociation energies of the Ga2, In2, and GaIn molecules](https://pubs.aip.org/aip/jcp/article-abstract/109/11/4384/1018967/Dissociation-energies-of-the-Ga2-In2-and-GaIn) (1998) | [PDF](reference/R23_Balducci_1998_Ga2_In2_GaIn_dissociation.pdf) |
| R24 | [Unibody crucible and effusion source employing such a crucible (US 5,827,371; parent US 5,820,681)](https://patents.google.com/patent/US5827371A/en) (1998) | [PDF](reference/R24_US5827371_unibody_crucible.pdf), [PDF](reference/R24_US5820681_unibody_crucible.pdf) |
| R25 | [Effusion cell and method of use in molecular beam epitaxy (US 6,053,981)](https://patents.google.com/patent/US6053981A/en) (2000) | [PDF](reference/R25_US6053981_effusion_cell_VG.pdf) |
| R26 | [Control of ion content and nitrogen species using a mixed chemistry plasma for GaN grown at extremely high growth rates >9 um/h by plasma-assisted molecular beam epitaxy](https://pubs.aip.org/aip/jap/article-abstract/118/15/155302/140376) (2015) | [PDF](reference/R26_Gunning_2015_high_rate_PAMBE.pdf) |
| R27 | [Mid-infrared optical properties of pyrolytic boron nitride in the 390-1050 C temperature range using spectral emissivity measurements](https://ui.adsabs.harvard.edu/abs/2017JQSRT.194....1G/abstract) (2017) | [PDF](reference/R27_Gonzalez_de_Arrieta_2017_PBN_emissivity.pdf) |
| R28 | [Emissivity of silicon at elevated temperatures](https://pubs.aip.org/aip/jap/article/74/10/6353/177953/Emissivity-of-silicon-at-elevated-temperatures) (1993) | [PDF](reference/R28_Timans_1993_Si_emissivity.pdf) |
| R29 | [NIST Chemistry WebBook, SRD 69: thermophysical properties of fluid systems (Ne, Ar, Kr, Xe viscosity)](https://webbook.nist.gov/chemistry/fluid/) (2026) | URL only / local source unavailable; see detailed manifest |
| R30 | [Observation and mitigation of RF-plasma-induced damage to III-nitrides grown by molecular beam epitaxy](https://pubs.aip.org/aip/jap/article/126/1/015705/155766/Observation-and-mitigation-of-RF-plasma-induced) (2019) | [PDF](reference/R30_Clinton_2019_RF_plasma_damage.pdf) |
| R31 | [Emissivity measurements and modeling of silicon-related materials: an overview](https://web.njit.edu/~sirenko/PapersNJIT/Ravi_IJTh_2001.pdf) (2001) | [PDF](reference/R31_Ravindra_2001_Si_emissivity_overview.pdf) |
| R16 | [Growth-induced temperature changes during transition metal nitride epitaxy on transparent SiC substrates](https://doi.org/10.1116/6.0000063) (2020) | [PDF](reference/R16_Katzer_2019_NAMBE_abstract.pdf) |
| R17 | [Optical in-situ temperature management for high-quality ZnO molecular beam epitaxy](https://doi.org/10.1016/j.jcrysgro.2020.126009) (2021) | URL only / local source unavailable; see detailed manifest |
| R18 | [Characterisation of an RF atomic nitrogen plasma source](https://doi.org/10.1016/S0022-0248(98)01361-X) (1999) | URL only / local source unavailable; see detailed manifest |
| R19 | [Active nitrogen species dependence on radiofrequency plasma source operating parameters and their role in GaN growth](https://doi.org/10.1016/j.jcrysgro.2005.01.013) (2005) | URL only / local source unavailable; see detailed manifest |
| R20 | [In situ investigation of growth modes during plasma-assisted molecular beam epitaxy of (0001)GaN](https://doi.org/10.1063/1.2789691) (2007) | [PDF](reference/R20_Koblmuller_2007_GaN_growth_modes.pdf) |
| R01 | [RIBER MBE 49 GaN: plasma-assisted GaN production system for 200 mm GaN-on-Si](https://www.semiconductor-today.com/news_items/2023/oct/riber-171023.shtml) (2023) | URL only / local source unavailable; see detailed manifest |
| R02 | [MBE Nitride Components & Systems brochure (GEN20, GEN200, UNI-Bulb RF nitrogen source, SUMO cells, valved Mg source)](https://www.semiconductor-today.com/images/adverts/veeco_brochure_nitrides.pdf) (2006) | [PDF](reference/R02_Veeco_nitride_MBE_brochure_2006.pdf) |
| R03 | [Simulation and experiment of a dual-temperature zone MBE heater](https://www.sciencedirect.com/science/article/abs/pii/S0020740325008926) (2025) | [PDF](reference/R03_Wu_2025_dual_zone_MBE_heater.pdf) |
| R04 | [Design and optimization of a multi-temperature zone heater for enhanced substrate temperature uniformity in large-sized molecular beam epitaxy systems](https://www.sciencedirect.com/science/article/abs/pii/S1359431125014565) (2025) | URL only / local source unavailable; see detailed manifest |
| R05 | [Design elements affecting wafer temperature uniformity in multi-wafer production MBE systems](https://www.sciencedirect.com/science/article/abs/pii/S0022024808009913) (2009) | [PDF](reference/R05_Rogers_2009_wafer_temperature_uniformity.pdf) |
| R06 | [Thermal imaging of wafer temperature in MBE using a digital camera](https://www.sciencedirect.com/science/article/abs/pii/S0022024806015727) (2007) | URL only / local source unavailable; see detailed manifest |
| R07 | [A detailed study of the molecular beam flux distribution of MBE effusion sources](https://www.sciencedirect.com/science/article/abs/pii/0042207X91901323) (1991) | [PDF](reference/R07_Gericke_1991_effusion_flux_distribution.pdf) |
| R08 | [Molecular beam epitaxy beam flux modeling](https://pubs.aip.org/avs/jvb/article-pdf/3/2/531/12021852/531_1_online.pdf) (1985) | URL only / local source unavailable; see detailed manifest |
| R09 | [Monte Carlo calculations of the beam flux distribution from molecular-beam epitaxy sources](https://www.researchgate.net/publication/222096092_Monte_Carlo_calculations_of_the_beam_flux_distribution_from_molecular-beam_epitaxy_sources) (unverified) | URL only / local source unavailable; see detailed manifest |
| R10 | [High active nitrogen flux growth of GaN by plasma assisted molecular beam epitaxy](https://pubs.aip.org/avs/jva/article-abstract/33/5/05E128/245187/High-active-nitrogen-flux-growth-of-GaN-by-plasma) (2015) | URL only / local source unavailable; see detailed manifest |
| R11 | [Development and diagnostic study of the RF nitrogen atom source](https://www.sciencedirect.com/science/article/abs/pii/S0042207X24008662) (2024) | URL only / local source unavailable; see detailed manifest |
| R12 | [Active nitrogen flux measurement during GaN growth based on the transmitted signal detected with a pyrometer](https://arxiv.org/abs/2412.15710) (2024) | [PDF](reference/R12_Canciani_2024_active_N_pyrometer.pdf) |
| R13 | [System and method for increasing III-nitride semiconductor growth rate and reducing damaging ion flux (US 10,526,723)](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/10526723) (2020) | [PDF](reference/R13_US10526723_plasma_aperture.pdf) |
| R14 | [Simulation of the uniformity influence of effusion cell structure and layout in molecular beam epitaxy](https://doi.org/10.13922/j.cnki.cjvst.202502013) (2025) | [PDF](reference/R14_Tao_2025_effusion_cell_layout_8inch.pdf) |
| R15 | [Vapour pressure equations for the metallic elements: 298-2500 K (CRC Handbook reprint, 'Vapor pressure of the metallic elements')](https://www.tandfonline.com/doi/abs/10.1179/cmq.1984.23.3.309) (1984) | [PDF](reference/R15_Alcock_1984_vapour_pressure_CRC.pdf) |

Details: [reference/sources.json](reference/sources.json).

## Remaining evidence gaps

G03 is a bibliographic lead without reviewed original full text. G05/G06 have reviewed online content but no local paper. H02/H04/H10/H11 have incomplete local source access. Most R-series records were reviewed from abstracts or index entries only; check their numbers against full texts before use. HTML challenge responses are retained only as failed-download diagnostics and excluded from usable-source counts. Consult source-level status before extracting data.

The library includes no actual machine CAD or calibration dataset. Obtain wafer/template specifications, optical/contact properties, source output maps, selected pump/diagnostic data and independent GaN/AlN wafers through the [data plan](../docs/DATA_AND_VALIDATION_PLAN.md). No digitized dataset or fitted parameter has been fabricated from these papers.

Rerun `python scripts/audit_references.py` from the repository with pypdf installed to check the collection. This checks file integrity and document structure, not physical correctness, browser availability of every external URL, or simulation accuracy.
