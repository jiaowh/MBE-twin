# Solver selection, accuracy controls and RTX 5050 laptop execution

Updated: 2026-09-13. Sources M01-M10 were accessed and archived on 2026-09-11. This is an engineering plan and evidence review, not a benchmark or a validated simulation. The source manifest is [methods/sources.json](../methods/sources.json).

## Decision

Use a local, CPU-first reference workflow for chamber radiation/conduction, species transport and GaN/AlN growth. Add acceleration only after comparing its outputs with that reference. Keep interactive display and recipe editing independent of the physics timestep. A laptop can display previous results while an accurate reference calculation runs for minutes or overnight.

There is no defensible promise of exactly zero accuracy loss from mesh coarsening, averaging, model reduction or omitted physics. The requirement should be: **an acceleration may be enabled only when its additional error is bounded or experimentally assessed within an allocated observable tolerance, and the complete coupled prediction still passes independent physical validation.** If that cannot be shown, retain the reference calculation and accept longer local runtime. If even the reference exceeds the laptop's memory or practical runtime after justified numerical optimization, that capability remains unqualified; remote computation is an optional extension, not an undisclosed requirement.

A detailed atomic simulation of a full wafer, a fully kinetic RF discharge and a chamber calculation need different spatial and temporal resolutions. Their usefulness depends on the requested outputs. Use measured source-boundary distributions and local surface submodels when they accurately answer those outputs. An empirical boundary map cannot claim predictive power for an unmeasured source redesign.

## 1. Candidate architecture and adoption tests

| Component | Candidate | Demonstration required before adoption |
|---|---|---|
| Geometry and mesh | Authoritative CAD plus Gmsh | Import actual dimensions; export complete named boundary/material groups; check normals, units, apertures, gaps and region identities after edits. Refine wafer edges, holder contacts and source apertures independently. |
| Chamber thermal reference | Elmer FEM | Conduction and radiation benchmarks, obstructed enclosure, multi-zone heater including conduction between zones, holder contact uncertainty, temperature-dependent materials, transient energy balance. Assess wafer optical transmission before accepting an opaque gray model. |
| Collisionless vacuum and beams | Molflow+ or a separately verified transport kernel | Finite aperture, measured angular source law, absorbing wafer, shutter shadows, sticking/reflection, pressure and absolute deposited atoms per area per time. Demonstrate source-to-wafer normalization, not only relative maps. |
| Regions with relevant gas collisions | SPARTA DSMC | Compare collisionless limit, then grid/timestep/particle convergence with defensible Ga/Al/N collision data. Match mass and energy across any local DSMC/chamber boundary. |
| RF source | First a measured, bounded species/angle/energy response map; source-resolved plasma model as a separate work package | Independent active-N/ion diagnostics, power and flow response, source pressure, wall losses and drift. For resolved modeling, establish plasma transport closure validity and chemistry before choosing software. |
| Surface and film | Custom GaN/AlN kinetic and layer-state solver | Element conservation, signed growth/decomposition, surface inventory, material-aware removal and separate GaN/AlN parameter provenance. Validate thickness and interface behavior before morphology/defects. |
| Coupling and data | Versioned orchestration and conservative mappings | Restart, unit conversion, event timing, source/wafer coordinate transforms, energy/particle balances and convergence when the exchange interval is reduced. |

Gmsh documents physical groups and export behavior; solver-boundary identity must still survive this project's CAD and import workflow. [M02: Gmsh manual](https://gmsh.info/doc/texinfo/gmsh.pdf)

Elmer documents radiation, radiosity/Gebhart formulations and shadowing controls. Its factor cutoffs, geometry-update thresholds and frozen emissivity settings need their own convergence checks. A documented spectral option is not proof of an arbitrary semitransparent wafer-stack model. [M03: Elmer manual](https://www.nic.funet.fi/index/elmer/doc/ElmerModelsManual.pdf)

Molflow's algorithm omits molecule-molecule collisions and uses independent test-particle histories. The archived algorithm describes version 2.6; demonstrate features against the actual pinned release. Its reported mean wall-flight distance must not be substituted for a gas-collision mean free path. [M04: algorithm](https://molflow.docs.cern.ch/guide/molflow/general/attachments/molflow_algorithm.pdf)

SPARTA offers collisional gas and surface models, but its ambipolar option is not evidence of a general RF discharge/sheath solver. Collision and reaction coefficients remain required inputs. [M10: features](https://sparta.github.io/features.html)

## 2. Free molecular flow is an error question

Calculate local rarefaction from species, temperature, density and collision data along important beam paths, inside the nitrogen source and in pump restrictions. A single chamber base-pressure value is insufficient.

COMSOL's free molecular interface targets Kn > 10 and assumes re-emission directions independent of incidence. Those conditions need checking for the actual surfaces and directional beams. [M06: interface guide](https://doc.comsol.com/6.4/doc/com.comsol.help.molec/molec_introduction.2.03.html)

For a beam trajectory, define collision optical depth as a project calculation:

```text
tau = integral_path [collision_frequency(s) / beam_speed(s)] ds
collision_frequency = sum_j n_j * <sigma_beam,j(v_relative) * v_relative>
P(at least one collision) = 1 - exp(-tau)
```

For a uniform effective collision path length lambda_eff, tau = L/lambda_eff. Thus tau = 0.1 gives approximately 9.52% probability of a collision; this is not a sub-1% beam-error guarantee. A collision is not automatically loss from the wafer: scattering angle, energy transfer, chemistry and the observable determine its effect. Bound that effect or compare a collisional calculation at the highest relevant gas load. Do not assume that a convenient Kn threshold satisfies a tighter flux tolerance.

Use species-resolved source number rates. In a well-mixed steady reference case, ideal-gas accounting gives:

```text
number_rate = p_standard * volume_flow_standard / (k_B * T_standard)
pressure_gas = number_rate * k_B * T_gas / S_effective
```

The standard-temperature convention of every MFC must be recorded. For 1 sccm defined at 101325 Pa and 273.15 K, standard throughput is 1.68875e-3 Pa m^3/s (about 1.2667e-2 Torr L/s). At a different gas temperature, the throughput entering a pressure-speed relation changes by T_gas/T_standard. Nonisothermal chambers require local density/velocity treatment; a gauge also needs its species response. Dissociation changes particle counts, so nitrogen atoms and N2 molecules must not be interchanged.

## 3. Observable and error contract

The master plan should declare numerical values for application tolerances after process sensitivity and measurement capability are known. This note fixes the accounting, without inventing achieved tolerances.

For each observable q, store its operating domain, spatial/time support, units, tolerance T_q, reference solution, uncertainty model and validation dataset. At minimum:

| Observable | Required definition and physical check |
|---|---|
| Wafer temperature | Absolute temperature map, center/edge difference, peak and transient lag; specify actual sensor layer, footprint and bandwidth. Validate more than one spatial location and heater setting. |
| Ga/Al/active-N flux | Absolute species flux, radial/angular map and shutter transient; separate source output, wafer incidence and incorporated fraction. |
| Growth | Thickness map, local net growth rate, GaN/AlN layer identity and interface transition; validate new recipes and interruptions. |
| Chamber environment | Species partial pressures and pumpdown response at named gauge locations with gauge sensitivity. |
| Mechanical response | Bow/curvature at known temperature and stack; separate thickness, stress and support-condition uncertainties. |

Proposed project allocation per q:

- Combined reference numerical error <= 0.20 T_q. This includes mesh, geometry tessellation, radiation quadrature, linear/nonlinear iteration, timestep/coupling and particle-statistics contributions.
- Combined extra error from all approximate accelerations <= 0.10 T_q. This is an aggregate allowance, not a separate 10% for each approximation.
- The final coupled prediction must pass the full T_q validation criterion, including the declared comparison of prediction and measurement uncertainties. The remaining 70% is not automatic permission to assign or hide physical bias.

Numerical bounds are not all independent random variables. Sum conservative deterministic bounds; combine random uncertainties with their covariance or a joint propagation method. If a term cannot be bounded, label the estimate and its empirical coverage rather than calling it certified. Avoid percentage errors near zero net growth or vanishing flux; use an absolute scale. Do not let wafer-average agreement conceal a failed edge pixel or shutter transition.

For deterministic reference calculations use at least three meaningful refinement levels, check the observed order/asymptotic behavior where applicable, and separate iterative from discretization error. Two nearby meshes can agree while both remain wrong. [M09: NASA grid-convergence guidance](https://www.grc.nasa.gov/www/wind/valid/tutorial/spatconv.html)

For particle calculations, retain batch/seed identities, uncertainty per reported bin and covariance of derived maps. Increase histories until the declared confidence interval satisfies its assigned budget; do not use a global hit count as evidence that every low-flux pixel converged. Compare CPU/GPU stochastic results statistically. Check the complete coupled trajectory after individual components pass.

Calibrate with one dataset and lock model/parameters before predicting independent data spanning temperature, flux, rotation and shutter histories. Synthetic recovery tests verify software; literature measurements on another reactor establish plausibility, not machine validation. Failed validation triggers an input/model-form investigation and revalidation on fresh held-out cases.

## 4. Acceleration ledger

Every enabled optimization needs its own record: mechanism, affected observables, tested envelope, memory/runtime benefit, added-error evidence, invalidation trigger and fallback. Test all enabled optimizations together.

| Optimization | Why it may help | Accuracy gate and fallback |
|---|---|---|
| Reuse geometry intersections/view factors | Geometry often stays fixed over many steps | Reuse identical operators only with complete dependency hashes. Recompute after geometry, shutter, wafer bow or relevant optical changes. Distinguish geometric view factors from emissivity-dependent factors. |
| Reuse linear source-transfer kernels | Independent collisionless histories permit source scaling within their assumptions | Keep geometry, angular/energy laws and surface interactions fixed; verify linearity. Recompute when source fill, scattering, sticking or collisions change. |
| Parallel CPU/GPU execution | Reduces elapsed time without intentionally changing equations | Preserve precision and conservation; verify supported kernels. Compare deterministic outputs or stochastic distributions. Return to the accepted CPU path if parity fails. |
| Adaptive meshing and time stepping | Resolve sensitive regions/events more efficiently | Control each relevant observable, including edges and shutter events. Refine locally or reduce step size on failure; do not change tolerance to meet a frame budget. |
| Rotation averaging / symmetry | May eliminate repeated azimuthal work | Compare against resolved rotation for the actual geometry, rotation rate and nonlinear surface kinetics. Averaging incident flux before nonlinear incorporation may change the result. Use resolved angles when it fails. |
| Reduced thermal/source models | Speeds repeated queries over a declared domain | Validate outputs and, where mathematically available, residual-based error bounds. Reject extrapolation, rebuild/enrich the model or run the local reference. |
| Separate rendering from numerical storage | Reduces GUI memory and display cost | Display simplification may change appearance only. Export quantitative results from original solver fields with clear sampling metadata. |

Reduced-basis methods can separate expensive construction from fast evaluation and estimate approximation error for specified equation classes. General nonlinear/nonaffine models do not automatically inherit rigorous certificates. Even a rigorous bound to a discrete model is not physical validation. [M08: Nguyen thesis, sections 3.2-3.5](https://www.mit.edu/~cuongng/publication/pub31/pub31.pdf)

## 5. Laptop performance gate

The NVIDIA page lists the RTX 5050 Laptop GPU with 8 GB GDDR7, 2560 CUDA cores and 384 GB/s memory bandwidth. These are vendor specifications, not measured project performance. Record the exact laptop CPU, physical RAM, available memory, GPU/VRAM, OS, driver, power mode and sustained temperature before sizing cases. Do not infer desktop specifications or useful FP64 throughput from marketing AI throughput. [M01: NVIDIA specs](https://www.nvidia.com/en-us/geforce/laptops/50-series/)

SPARTA's documentation says that Kokkos acceleration depends on hardware, case size and supported commands, and may differ through roundoff and random numbers. Benchmark the complete workload rather than projecting speedup from GPU capability alone. [M05: acceleration guide](https://sparta.github.io/doc/Section_accelerate.html)

Run and save three cases on the target machine: (1) a single-source transport/thermal verification case; (2) the representative full GaN/AlN recipe with rotation and shutter events; (3) the most demanding accepted case, including uncertainty or collisional work when those are in scope. Record degrees of freedom/facets, particles, uncertainty, solver iterations, wall time, peak RAM/VRAM, disk use and checkpoint/restart behavior.

Adoption requires all of the following:

1. Each case meets its numerical and reduction budgets, and the physical validation gate remains separate and visible.
2. The representative case fits the actual laptop's memory with room for the OS and interface. Following the governing Phase-1 plan, the initial engineering target is peak solver RAM < 70% of installed physical RAM and GPU allocations < 75% of available VRAM when used; these are resource reservations, not accuracy settings. Record the available-memory baseline used for the GPU limit.
3. The reference can finish locally with checkpoint/restart. Target an overnight window for the representative reference case, to be measured before promising a duration; sweep jobs may queue over multiple nights.
4. Interactive outputs disclose whether they are validated reduced predictions, in-progress reference calculations, stale results or outside the validated domain.
5. A failed memory/runtime gate prompts profiling, algorithmic improvements and justified domain decomposition. It must not silently lower resolution, precision, particle confidence or modeled physics.

No solver has been installed or timed as part of this evidence review. Laptop feasibility remains an adoption gate. External computation may accelerate large parameter studies or optional research, while the declared baseline must retain a demonstrated local path.

## 6. Tool access and unresolved data

The first implementation demonstrations need a working pinned scripting runtime, Gmsh, Elmer and a collisionless transport implementation; CAD handling and a scientific field viewer are supporting tools. These are candidates pending installation and acceptance, not existing integrations.

COMSOL is optional. If an evaluation becomes useful, request **COMSOL Multiphysics**, with **Heat Transfer** and **Molecular Flow** capabilities for independent thermal/vacuum comparisons; ask the vendor to confirm exact feature licensing. For source-resolved plasma work evaluate **Plasma Module**; the interface-specific 6.4 documentation identifies **AC/DC Module for 3D ICP** and **RF Module for microwave plasma**. A 13.56 MHz source does not by itself establish a need for the RF Module. [M07: Plasma guide, p194 and interface overview](https://doc.comsol.com/6.4/doc/com.comsol.help.plasma/PlasmaModuleUsersGuide.pdf)

The same manual's fluid-validity discussion is a reason to evaluate charged-particle mean paths and nonlocal heating. Its approximate CCP pressure threshold must not be transferred to this MBE ICP source. Commercial access will not supply missing nitrogen chemistry or validate a discharge model.

Required machine evidence is more consequential than a commercial license: revisioned geometry; source apertures/fill and angular flux calibration; heater electrical and contact data; optical/material properties over temperature; species pump curves and gas-flow standard conditions; time-aligned thermometry, pressure, flux and grown-film maps. Until obtained, uncertain values remain named priors, and their outputs remain predictions under assumptions.
