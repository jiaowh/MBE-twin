# Hardware evidence and build-specification intake

Review completed 2026-09-13. Primary-source web content was inspected on 2026-09-11; local artifacts and hashes were audited on 2026-09-13. Scope is the proposal's growth chamber for GaN/AlN. This is a comparator and requirements register, not a bill of materials or acceptance certificate.

The proposal's slides 8, 11 and 19 were read directly from its slide XML. They state a solid-SiC heater rated 1200°C in reactive gas; multi-zone closed-loop balancing; 600 W at 13.56 MHz RF nitrogen; ten sources (3 Ga, 3 Al, Si, Mg and two spare positions); maglev turbo at least 2000 L/s plus cryo/ion/Ti-sublimation pumping; 30 keV RHEED, band-edge temperature measurement, BFM and RGA; and a post-bake base-pressure target of 1e-11 mbar. None of the vendor references establishes that this proposed assembly meets these targets.

## Reference inventory and what it establishes

The machine-readable [hardware source manifest](../hardware/sources.json) contains per-source URLs, locators, scope limitations, retrieval status and SHA-256 hashes. Dates inferred from upload directories or search-engine estimates are not treated as publication dates. PDF page numbers below are one-based unless described as printed page numbers.

| ID | Primary manufacturer source and locator | Local evidence and use |
|---|---|---|
| H01 | [RIBER MBE49](https://www.riber.com/product/mbe-49/), Presentation; undated | [Product snapshot](../hardware/H01_RIBER_MBE49_product.html), [legacy brochure](../hardware/H01_RIBER_MBE49_legacy_brochure.pdf). Current page establishes a 200 mm/nitride comparator; older GaAs performance does not transfer to GaN. |
| H02 | [SVTA RF-6.02 sheet](https://www.svta.com/uploads/documents/RF_6.0.pdf), p.1, specifications and distribution plot; undated | Online content inspected; local download returned a challenge. Supports large-area source comparison, not a 600 W active-N calibration. |
| H03 | [RIBER ABI Ga/In cell](https://www.riber.com/product/heated-insert-cell-for-ga-in-abi/), Technical information; undated | [Data sheet](../hardware/H03_RIBER_Ga_ABI.pdf), [product snapshot](../hardware/H03_RIBER_Ga_ABI_product.html). Separate insert/crucible controls and powers provide a useful thermal architecture comparator. |
| H04 | [RIBER Al cold-lip/cold-neck cell](https://www.riber.cn/wp-content/uploads/2023/05/RIBER_Aluminum-source-ABN-BF-CL-CN.pdf), Product introduction; undated | Primary search-index content inspected; download timed out. Shows why Al needs its own source architecture. Obtain the actual selected-source drawing and data sheet. |
| H05 | [Eberl SH substrate manipulator](https://www.mbe-komponenten.de/pdf/data-sheet-sh.pdf), pp.1–2; undated | [Data sheet](../hardware/H05_Eberl_substrate_manipulator_SH.pdf). Family supports SiC heating and large substrates; headline and standard-configuration temperature limits differ. |
| H06 | [kSA GaN BandiT application note](https://www.k-space.com/wp-content/uploads/kSA_BandiT_for_GaN-1.pdf), pp.1–2 and 5–7; undated, web version 1.0 | [Application note](../hardware/H06_kSA_BandiT_GaN.pdf). GaN/SiC calibration and optical configuration, including GEN200 MBE demonstration. |
| H07 | [Leybold MAG integra manual](https://fr.shop.leybold.com/medias/300324726-002-Instructions.pdf?attachment=true&context=bWFzdGVyfHJvb3R8MzM0NjEwOHxhcHBsaWNhdGlvbi9wZGZ8YUdZM0wyZzVZUzg0TnpBMk1UWXdNRFk1T0RNNU9DOHpNREF6TWpRM01qWmZNREF5WDBsdWMzUnlkV04wYVc5dWN5NXdaR1l8MTNiNDk2ZjE1NzkxMzczMjRkMzZiMDMwYjcwZjg0MmM1NTkzMWIwNmY1OTY2YmY3NjY2MDc3Nzk2Y2FlZWY2Yw), 300324726_002_C4, Table 2 p.18, footnotes p.19, Fig.6 p.23 | [Manual](../hardware/H07_Leybold_MAG_integra.pdf). Local cover/table extraction verified. W2200 N2 speed is 2100 L/s; species, configuration and throughput conditions apply. |
| H08 | [Edwards Cryo-Torr catalogue](https://www.edwardsvacuum.com/content/dam/brands/edwards-vacuum/edwards-website-assets/our-markets/chamber-solutions/cti-datasheets/Edwards%20CTI-Cryogenics%20Cryo-Torr%20Cryopumps%20Line%20Catalogue.pdf), p.3; ©2021 | [Catalogue](../hardware/H08_Edwards_CryoTorr_catalogue.pdf). Speed, finite capacity and cooldown specifications; the air row is not a pure-N2 calibration. |
| H09 | [STAIB RHEED-30](https://staibinstruments.com/rheed-30/), Key features/Characteristics; undated | [Product snapshot](../hardware/H09_STAIB_RHEED30.html). Gun energy, working distance and differential-pumping constraints. |
| H10 | [SVTA BFM](https://svta.com/components/real-time-monitoring/beam-flux-monitor/), Specifications; undated | Online content inspected; local HTML was only a captcha redirect. BEP gauge and positioning comparator. |
| H11 | [INFICON Transpector MPH manual](https://www.inficon.com/media/4281/download/074-555-P1C-Transpector-MPH-Operating-Manual.pdf?inline=true&language=en&v=1), §1.7 and chapter 4; PN 074-555-P1C, ©2016 | Online manual inspected; local download returned HTML. Fragmentation/sensitivity discussion is at printed pp.4-9 to 4-13, PDF pp.74–78. |
| H12 | [Leybold/Gamma UHV pumps](https://www.leybold.com/content/dam/brands/leybold/downloads/catalogue-chapters-pdf/110_EN_UHV%20Pumps.pdf), ion pump tables and printed pp.16–17; edition 2022 | [Catalogue](../hardware/H12_Leybold_UHV_pumps.pdf). Ion/TSP selection, getter renewal and hardware configuration. |

The corpus contains seven genuine PDF files and three genuine product-page HTML snapshots. H02, H04, H10 and H11 have incomplete local source access. Files named `Hxx_download_response.html` are retained retrieval diagnostics, not literature; they must not be ingested as physics evidence. The manifest marks them `download_failed`. The retry script preserves successful pinned files and rejects the observed challenge formats.

## Corrections and numerical inconsistencies

1. **Resolve 200 mm versus exact 8 inches.** Resolved 2026-09-28: the twin uses 200 mm GaN-on-Si(111). An exact 8-inch wafer is 203.2 mm in diameter, radius 101.6 mm. A 200 mm wafer has radius 100 mm. Substituting the former changes area by 3.2256%. Preserve the proposal's wording but add an explicit nominal diameter in millimetres before geometry, heater sizing, total flux and map masks are fixed. A platen handling limit of 12 inches does not specify the wafer or heater diameter.

2. **Do not interpret 600 W as a growth-rate or uniformity specification.** H02 lists 200–2000 W, 0.1–10 sccm, a typical 10.5-inch throw and coverage up to 8 inches, without a 600 W species-resolved output map. The frequency and power limit in the proposal remain targets. Required characterization must separate forward/reflected/absorbed power, flow, aperture, source pressure, active-neutral output and residual ion output. “Ion-free” needs a quantitative measurement limit at the wafer.

3. **A generic SiC temperature rating does not close heater design.** H05 advertises up to 1200°C across a family but specifies 1000°C as standard. Neither this nor the proposal supplies the selected unit's multi-zone power capacity, active-N lifetime, zone coupling, holder contact or full-wafer uniformity. Distinguish heater-element, thermocouple, wafer-front and wafer-back temperatures. Convert the proposal's 1200°C to 1473.15 K; do not assign it simultaneously to every temperature node.

4. **Multiple sources do not automatically flatten the radial profile.** Three identical source distributions differing only by azimuth have identical radial profiles after complete uniform rotation. Their sum multiplies the dose; it does not improve normalized radial uniformity. A multi-cell design can reduce angular/time variation, and can alter radial uniformity if throw, aim, aperture or relative rates differ. Verify the actual configuration before claiming a three-cell radial-uniformity benefit.

5. **Pressure arithmetic needs effective speed and specified flow convention.** With standard flow defined at 0°C and 1 atm, 1 sccm corresponds to 0.0126667 Torr L/s or 0.0168875 mbar L/s at that same 273.15 K gas temperature. At an illustrative chamber effective speed of 2000 L/s, 1–3 sccm gives 6.33e-6–1.90e-5 Torr (8.44e-6–2.53e-5 mbar), before other loads, if chamber gas is also at 273.15 K. For a different chamber gas temperature, multiply the throughput and these pressure values by `T_gas/T_std`; at 300 K the factor is 300/273.15 = 1.0983. For one series restriction, `1/S_eff = 1/S_pump + 1/C`. These are unit-check examples, not project predictions; the MFC's actual standard temperature and the pump-speed gas-temperature basis must be recorded.

6. **Base and operating vacuum are separate acceptance cases.** The 1e-11 mbar target is post-bake base pressure, not nitrogen-on growth pressure. Record source temperatures, valve/pump states, shroud temperatures, time after bake, leak/outgassing history, gauge location and instrument uncertainty. H10's lower stated BEP range, 3e-11 Torr (about 4e-11 mbar), cannot by itself certify the proposal's base target. A suitable base-pressure metrology chain is missing.

7. **Check diagnostic operating conditions jointly.** The pressure example above overlaps the H09 range where differential pumping is offered. A 30 keV gun specification alone omits its pumping path, incidence angle, field shielding, screen and optical calibration. A nominal spot diameter is conditional on current, energy and distance. The band-edge sensor likewise requires film/substrate-specific optical access and calibration; the GaN demonstration does not establish AlN-on-sapphire performance.

8. **A sensor inventory is not spatial observability.** One centre temperature value cannot independently determine multiple changing heater-zone errors. Specify spatial sampling or qualify model-estimated edge temperatures. Retain spectra, instrument quality flags, acquisition/exposure timing and calibration versions; arbitrary 2 K Gaussian noise is not a measurement model. BFM and RGA readings require their own observation operators, not direct substitution for true flux/species fields.

## Missing build specifications to request from the designers

These requests are concrete intake deliverables for the proposed chamber. Comparator values must remain separate until the designer or supplier adopts them.

| Priority | Required input | Why it changes the simulation |
|---|---|---|
| P0 | Chamber STEP assembly and dimensioned sectional drawings; reference frame, tolerances, port/flange schedule, wafer plane and source axis poses | Establishes view factors, paths, shadows, conductance and coordinate mapping |
| P0 | Exact wafer diameter, substrate material/orientation/polarity, thickness, doping, coatings, notch/flat and initial bow; holder drawings and clamp/contact state | Determines absorption, heat capacity, thermal contact, stress and usable map area |
| P0 | Heater zone geometry, electrical resistance versus temperature, current/voltage/power limits, thermocouple positions, power histories and controller update/ramp limits | Enables power-driven heating and physically achievable setpoints |
| P0 | Per-cell supplier/model, crucible/insert geometry, loaded mass and fill shape, thermal zones, aperture, shutter trajectories and timing | Enables distinct Ga/Al delivery and source-memory/transient models |
| P0 | RF source drawing, aperture/hole map, coil and dielectric geometry, matching-network readings, flow/MFC specification, upstream/downstream pressure and wafer-plane flux maps | Defines actual active-N boundary conditions and gas load |
| P0 | Pump models, species curves, ports/ducts/valves, backing pump and line, throttle states, cryopump stages/capacities and regeneration histories | Determines effective speed and capacity, not merely nameplate speed |
| P0 | LN2 shroud CAD, measured thermal boundary, coverage/material/coating state and coolant operation | Separates radiation boundary and wall capture behavior from dedicated cryopumps |
| P0 | Gauge/BFM/RGA/RHEED/temperature models, serial/configuration details, mounting/line of sight, calibration files, raw data formats and clocks | Defines what is observable and how model predictions are compared with measurements |
| P1 | Bake recipe, material/surface preparation, seals, virtual-volume inventory, leak-test report and outgassing/pump-down traces | Constrains base pressure and contamination |
| P1 | Rotation encoder histories, speed ripple, axial/radial runout and shutter command/position feedback | Determines finite-rotation deposition and thermal modulation |
| P1 | Instrumented commissioning matrix and held-out wafer runs with temperature/flux/thickness maps | Separates calibration from independent physical validation |
| P1 | Interlock cause/effect matrix, fault states, actuator timing and logging/protocol descriptions | Enables faithful replay and a connected read-only shadow before control integration |

## Minimum commissioning evidence for the first twin

Use a single actual holder/wafer configuration and one Ga or Al source first. Acquire heater power steps at several zone combinations with spatial temperature information; absolute and spatial source flux versus cell settings/fill; shutter opening/closing traces; and gas-on/off pressure histories at more than one flow. Characterize the nitrogen source separately at the chosen power/flow/aperture settings. Then compare predicted binary-layer thickness to whole held-out wafer runs, with documented edge exclusions and uncertainty.

Source delivery, sensing and heat-transfer errors can compensate when fitted only to final thickness. Collect subsystem data before fitting growth kinetics. Raw data should retain units, coordinates, calibration/configuration IDs and clocks, and should distinguish setpoints, instrument readings and inferred quantities.

No COMSOL access is required to close this evidence intake. The present blocker is missing actual design and calibration information. A commercial solver could help construct a later reference case, but cannot supply missing boundary conditions or validate the chamber through vendor specifications alone.

## Audit record

On 2026-09-13 the manifest JSON was parsed, each saved artifact's byte count and SHA-256 hash was recomputed, PDF magic bytes were checked, and obvious HTML challenge responses were reclassified. The downloaded HTML product pages were checked for expected content. A subsequently located bundled Python runtime with pypdf parsed all seven local PDFs and confirmed their page counts. H07's local cover confirms revision 300324726_002_C4; Table 2, its operating-condition footnotes and the Fig.6 caption were extracted on pp.18, 19 and 23. See [local PDF text audit](../hardware/pdf_text_audit.json). This is content/provenance checking, not a full PDF rendering audit or physical validation; the plotted pump curves have not been digitized.

The original proposal, vendor files and uncalibrated priors are distinct evidence classes. Do not fit model parameters to a brochure target and then count agreement with that target as successful validation.
