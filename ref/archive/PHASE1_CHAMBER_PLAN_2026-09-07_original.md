# Phase-1 MBE growth-chamber simulation — implementation plan

Drafted 2026-09-07 against `MBE_Phase1_Proposal_v1.2.pptx` (slides 5, 8, 11, 19).
Scope: the 8-inch MBE **growth module only**. The transfer hub, load-lock, robot,
and the in-vacuum anneal module are out of scope by decision of the user.

Companion documents: `AUDIT.md` (physics provenance, findings F1–F17),
`explanation.md` (architecture), memory `proposal-target-machine.md`.

---

## 0. Target machine and the gap it exposes

| Proposal item (slide 8/11/19) | Value | Simulator today | Gap |
|---|---|---|---|
| Wafer | 8 in (R = 101.6 mm), platens to 12 in | R is a menu slider to 150 mm | heater/gap knob bounds (45 mm / 30 mm) make 8 in unreachable |
| Substrate heater | solid SiC, 1200 °C, **multi-zone, closed-loop** | one isothermal disk, open-loop secant setpoint | no zones, no controller, no pyrometer model |
| Effusion cells | 10: 3×Ga, 3×Al, Si, Mg + spares, PBN, PID | one cell geometry shared by Ga/Al/In, first-order flux lag | no per-cell geometry, no dopants, no cell-T/PID |
| N source | RF plasma 600 W @ 13.56 MHz | fixed 1.2× excess over the fastest layer | no power/flow model, no V/III recipe knob (F17) |
| Pumping | maglev turbo ≥2000 L/s + cryo + ion/TSP, 10⁻¹¹ mbar | one time constant, base 5×10⁻¹⁰ Torr | no species, no pump stack, no bake state |
| LN₂ shrouds | yes | single wall temperature 350 K | radiative sink not split shroud / hot cell flange |
| Diagnostics | 30 keV RHEED, band-edge pyrometer, BFM, RGA | RHEED at 15 kV, ideal T readout, BEP per cell | pyrometer + RGA models missing, RHEED energy wrong |
| Control | open stack, interlocks + logging | live knobs, no interlocks, no log | interlocks and run log missing |
| Target process | regrowth on patterned GaN, p-GaN (Mg), n⁺ (Si), MQW | binary + ternary undoped layers on Si(111) | no doping, no growth interrupt stage, one substrate card |

Measured with the current code (GaN, 1010 K wafer centre, 0.25 nm/s, Si(111) card):

| R | heater-radius bound | ΔT centre-edge | thickness spread | slip |
|---|---|---|---|---|
| 25.4 mm | 45 mm | 10.6 K | 7.3 % | no |
| 101.6 mm | 45 mm | 382 K | 67 % | **yes** |
| 101.6 mm | lifted to 160 mm | 14.5 K | 35 % | no |

The last row is the honest single-zone limit at the III-limited Ga-knee operating
point. Two things fix it, and both are in this plan: a multi-zone heater (WP2) and
a Ga-rich, N-limited recipe (WP1).

## 0.1 Design rules carried over (do not break)

1. **Menu == run.** Every prediction the setup menu shows must be computed by the
   same code path the live run deposits with (`wafer.wafer_diagnostics` +
   `kinetics.growth_rate_regime`). New physics goes into the shared law, never into
   one consumer.
2. **Recipe inputs are wafer quantities; machine setpoints are outputs.** Growth
   temperature is an input, heater setpoint is solved. Extend the same rule to
   zone setpoints, cell temperatures and plasma power.
3. **Every new constant is tagged `[PRIOR]` in code, listed in the card that owns
   it, and given a benchmark slot** (`data/benchmarks/*.json` schema) so it can be
   replaced by a fit when the tool produces data.
4. Pure Python, stdlib only. Verification bar: `python -m pytest -q` green,
   default entry `python -m mbe_sim` unchanged.
5. One work package per session; append to `AUDIT.md` section 8, never rewrite
   history.

---

## WP0 — 8-inch envelope and reactor card (unblocks everything)

**Goal.** The default machine the menu opens on is the proposed 8-inch tool, and no
knob bound silently stops the model from covering the wafer.

**Changes.**

- `cards/reactor_phase1_8in.json` (new). Sections:
  - `geometry`: `R 0.1016`, `gap`, `heater_radius` (≥ R, e.g. 0.125), source
    throw for a 10-port flange (offset ~0.18–0.22 m, height ~0.30–0.35 m,
    per-cell azimuths), `T_sur`, `n_nodes` auto.
  - `limits`: heater_radius (0.08, 0.16), gap (0.004, 0.06), source_offset
    (0.08, 0.35), source_height (0.15, 0.60), aim_offset (−0.15, 0.15),
    heater T max (SiC element, `T_heater_max_K`), substrate T max 1473 K.
  - `substrate`: Si(111), thickness **725 µm** (8-inch standard), k, alpha,
    biaxial 229 GPa.
  - `measurements`: empty, with the schema WP7 fills.
- `mbe_sim/optimize.py`: `DEFAULT_KNOBS` stays the research envelope but
  `UniformityProblem.__init__` must **warn when `R > bounds["heater_radius"][1]`**
  and, when no `limits` are passed, auto-widen heater_radius to `(0.5 R, 1.6 R)`
  and gap to `(0.004, 0.06)`. Pinned-knob reporting already exists; keep it.
- `mbe_sim/setup_menu.py`: `PARAM_SPECS` ranges become card-driven (read
  `limits` from the reactor card; fall back to current numbers). Add a
  "Reactor" dropdown (`cards/reactor_*.json`). `STATIC_DEFAULTS["R_mm"]` = 101.6
  when the Phase-1 card is selected.
- `scripts/visualize_wafer_growth.py`, `scripts/wafer_report.py`: `--reactor`
  flag that loads the card and sets radius/geometry/limits defaults from it.
- `mbe_sim/calibrate.py` `PARAM_BOUNDS`: heater_radius upper → 0.20, gap → 0.06,
  source_offset → 0.40, source_height → 0.60.

**Tests.** `tests/test_phase1_card.py`: card loads; optimizer at R = 0.1016 with the
card's limits reports no pinned heater knob and `slips == False`; menu specs
reflect the card limits; the 2-inch defaults are unchanged for the old card.

**Acceptance.** `python -m mbe_sim` with the Phase-1 reactor opens with an 8-inch
wafer, a heater covering it, ΔT < 20 K single-zone, no slip. ~150 LOC.

---

## WP1 — V/III as a recipe parameter, Ga-rich default (audit F17)

**Goal.** The recipe states the arriving N/III ratio per layer; the plasma
setpoint is derived from it; the optimiser and menu score the same regime. This is
what makes 8-inch uniformity numbers meaningful: N-limited growth is flat in T.

**Physics (already in `kinetics.growth_rate_regime`).**
`GR = max(min(J_III − J_evap(T), J_N) − R_dec(T), 0)`. With `J_N < J_III − J_evap`
across the wafer the rate is `J_N` everywhere and the thermal term vanishes.
Add the open item from AUDIT §5: adlayer-coverage-dependent desorption
`J_evap(θ)`, with `θ` from the Ga-excess balance `θ ≈ min(1, (J_III − J_N)/J_evap_max)`
[PRIOR, Koblmüller/Heying bilayer picture]. Under N-rich conditions this lowers
desorption; under Ga-rich it saturates at the digitized γθ_m value already fitted.

**Changes.**

- `wafer.Layer`: new field `v_iii: float = 0.8` (arriving N/metal). Ga-rich
  default for GaN; AlN layers default 1.2 (Al-rich growth is not standard),
  InGaN 1.5.
- `process.ProcessSimulator`: replace the global `plasma_flux_mls =
  PLASMA_EXCESS × max rate` with a **per-layer plasma setpoint**
  `v_iii × Σ cation setpoints` set in `_enter_stage("ramp")`. Keep
  `PLASMA_EXCESS` only as the fallback for layers without `v_iii`.
- `kinetics.growth_rate_regime_profile` and `wafer.wafer_diagnostics`: accept
  `j_n_rel` (already plumbed in the regime law) and pass it from
  `UniformityProblem` (new ctor arg `v_iii`).
- `setup_menu.PARAM_SPECS`: recipe row `("v_iii", "V/III (N/metal)", "", 0.3,
  4.0, 0.05, "recipe", False)`; stack mode shows the critical layer's value.
- `live.py`: the existing N-flux scale slider now displays the resulting
  V/III and the regime label ("N-limited" / "III-limited") next to the growth
  rate readout.
- Cards: `GaN.json` `T_growth` stays 1010 K; add `v_iii_default`.
- `optimize.py`: with N-limited growth the thermal term is ~0; verify the
  optimiser no longer pins all five geometry knobs (F17 symptom).

**Tests.** `test_kinetics`: N-limited rate is flat over ±30 K; coverage law
reduces to the fitted `γθ_m` at Ga-rich. `test_process`: plasma setpoint follows
layer `v_iii`; realised rate equals `J_N × ML_NM` when N-limited. `test_optimize`:
combined nonuniformity at R = 0.1016, `v_iii = 0.8` < 5 % with WP0 card.

**Acceptance.** Menu shows V/III; default GaN run is N-limited; the 8-inch
single-zone thickness spread drops from ~35 % to the flux-geometry number
(~1–4 %). ~250 LOC.

---

## WP2 — Multi-zone SiC heater with closed-loop control (proposal innovation #1)

**Goal.** The heater is N coaxial zones with independent setpoints; a controller
holds the wafer flat using what the tool can actually sense; steady-state and
transient solves both use it; the optimiser solves zone setpoints the way it now
solves the single heater.

**Physics.**

- Zone i is the annulus `[a_{i−1}, a_i]` at temperature `T_h,i`. The differential
  view factor from a wafer element at radius r to an annulus is exactly the
  difference of two coaxial-disk factors already implemented in
  `ThermalModel.view_factor`: `F_i(r) = F_disk(r; a_i) − F_disk(r; a_{i−1})`.
  Source term becomes `Σ_i ε_x σ F_i(r) (T_h,i⁴ − T⁴)`. Off-axis/tilt
  (`view_factor_at`) generalises the same way.
- Heater element limit: `T_h,i ≤ T_heater_max_K` from the reactor card (SiC in
  reactive N: ~1900 K element for 1473 K substrate) [PRIOR].
- Zone-to-zone conduction inside the heater plate is ignored in v1 (zones are
  independent gray annuli). Flag as [PRIOR]; add an inter-zone coupling
  conductance later if calibration demands it.
- Sensing model (`diagnostics.py`, WP5 shares it): band-edge pyrometer returns
  `T(r_spot)` + Gaussian noise σ_T (card, ~2 K) with a 1 s time constant.
  Phase-1 hardware lists one pyrometer; the controller must therefore run in one
  of two modes:
  1. `sense = ["center"]`: single-point PI on the centre; zone ratios fixed from
     the steady-state flat-profile solve (feed-forward + one loop). This is the
     honest Phase-1 configuration.
  2. `sense = [r_1 … r_N]`: one PI per zone on the pyrometer/thermocouple at its
     own radius (what "real-time closed-loop balancing" needs; recommend an
     edge sensor in the design review).
- Controller: discrete PI with anti-windup and heater slew limit
  (`heater_ramp_K_s` already exists), gains from the wafer time constant
  (`ThermalModel.time_constant`) via a Ziegler–Nichols-style rule; card-settable.

**Changes.**

- `thermal.ThermalModel`: `zones: list[float]` of outer radii (default
  `[heater_radius]` → identical to today), `T_zones: list[float]` (default
  `[T_heater]`), `zone_view_factors(r)` cached per grid; `_assemble` sums over
  zones; `T_h` property kept as an alias for zone 0 so all existing callers
  work. `solve_asymmetric` uses per-zone `Fc_m`.
- `wafer.set_heater_for_center_T` unchanged (single zone). New
  `wafer.set_zones_for_profile(model, T_target, sense_radii)`: Newton with
  finite-difference Jacobian (N ≤ 5) on zone temperatures so that
  `T(r_k) = T_target` at the sense radii; clamps to `T_heater_max_K`; returns the
  residual so a wafer that cannot be flattened (too few zones) is reported.
- `process.ProcessSimulator`: `heater_T` → `zone_T` list; `zone_target` from
  the per-layer steady solve; `ZoneController` (new class in `control.py`)
  called in `advance` before `step_transient`; `heater_trim_K` applies to all
  zones. Snapshot adds `zone_T`, `zone_target`, `pyro_T`, `controller_mode`.
- `optimize.UniformityProblem.build`: calls `set_zones_for_profile`; new
  design knob `n_zones` (discrete 1–5; card default 3) exposed via `sweep`
  only; zone radii from the card. The thermal nonuniformity metric now
  reports the **residual after flattening**, and the objective gains a
  `zone_power_penalty` for setpoints at the element limit.
- `setup_menu.py`: "Heater zones" row (1–5), "Sensor" dropdown (centre /
  multi-point). Prediction panel prints per-zone setpoints.
- `live.py`: temperature strip chart gets one trace per zone; readout shows
  pyrometer vs true centre T; a "controller on/off" toggle next to the trim
  slider.
- `azimuthal.py` / `reportview.py`: heater-offset ripple uses the outermost zone.

**Tests.** `test_thermal`: 1-zone model reproduces today's solution to 1e-9;
annulus view factors sum to the disk factor; 3-zone flat-profile solve reaches
ΔT < 2 K at R = 0.1016 within the element limit. `test_control`: PI holds the
centre within ±1 K through a 0.75 K/s ramp; centre-only mode leaves the edge
error the steady solve predicts; noisy pyrometer does not destabilise.
`test_process`: menu zone setpoints == run zone setpoints (menu==run gate).

**Acceptance.** 8-inch, 3 zones, N-limited GaN: ΔT ≤ 3 K, thickness spread set by
flux geometry alone, slip ratio < 0.1. Documented single-sensor limitation.
~600 LOC. Depends on WP0; benefits from WP1.

---

## WP3 — Source bank: per-cell geometry, cell thermal/PID model, dopant cells

**Goal.** Ten cells with real port geometry; flux is the output of a cell
temperature under PID; Si and Mg produce a doping profile across the wafer.

**Physics.**

- Cell flux vs temperature: `J = A_cell · P_vap(T_cell) / √T_cell`, with
  `log10 P_vap[Torr] = B − C/T` (Honig/Alcock constants: Ga B≈8.65, C≈14335;
  Al B≈8.9, C≈16450; In B≈8.2, C≈12300; Si B≈9.3, C≈20900; Mg B≈8.5,
  C≈7550) [PRIOR]. `A_cell` is the per-cell BEP calibration (card). Cell
  thermal response: first-order in `T_cell` with τ_cell (Ga ~60 s, Al ~90 s,
  Si/Mg small cells ~30 s) and a PID on `T_cell`; the shutter transient
  (~10 % flux overshoot on opening, 30 s) as an optional card term.
- Multiple cells of one element: `sources.flux_profile` already sums a list;
  the deposit uses the summed absolute flux(r) of the **open** cells of that
  element. Rotation averaging stays; `azimuthal.py` takes per-cell azimuths from
  the card for the residual ripple.
- Dopant incorporation (mean field, new `doping.py`):
  - Si: unity sticking; `[Si](r) = J_Si(r) / (GR(r) · N_sites)` with
    `N_sites = 4.4×10²² cm⁻³` GaN atom density / 2 cation sites.
  - Mg: sticking `η_Mg(T) = max(1 − J_evap,Mg(T)/J_Mg, 0)` with an effective
    desorption barrier (E ≈ 2.0 eV at ν = 10¹³ [PRIOR, PAMBE p-GaN practice:
    incorporation drops above ~750 °C]); saturation at
    `[Mg]_max ≈ 2×10²⁰ cm⁻³` beyond which excess Mg surface-segregates;
    polarity inversion flag when `[Mg]` > 10²⁰ (informational).
  - Output: per-layer `doping_profile_cm3[(r, n)]`, nonuniformity %, and the
    mean-field sheet-resistance proxy for an n⁺ contact layer
    (`R_sh = 1/(q μ n t)` with a fixed μ(n) table [PRIOR]) since regrown n⁺
    S/D is the slide-2 use case.
  - No compensation, no H (MBE is H-free, slide 5). Documented.
- Element identity of a cell is a card field, so "3×Ga" means three
  `SourceCell(element="Ga")` at three ports.

**Changes.**

- `sources.SourceCell`: add `element`, `name`, `azimuth`, `A_cell`,
  `vapor_B`, `vapor_C`, `tau_cell`, `T_cell_max`.
- Reactor card: `cells: [{name, element, offset, height, azimuth, aim_offset,
  cosine_n, A_cell, tau_cell}]` for the ten ports.
- `process.CellState`: state variable becomes `T_cell`; `flux` is derived;
  `advance` runs the PID; `setpoint` is a flux request converted to a `T_cell`
  target by inverting the vapour law (this keeps recipes in ML/s). Cells keyed
  by **name**; `_elements_for_layer` becomes `_cells_for_layer` choosing the
  card's default cell(s) per element (a layer may name cells explicitly:
  `Layer.cells = ["Ga1", "Ga2"]` for high-rate growth).
- `process._deposit`: `cat_beam` and `flux(r)` from the summed open cells per
  element; `_composition_snapshot` uses per-element summed profiles (this
  wires the unused `cation_sources` hook and removes it).
- `wafer.Layer`: `dopants: dict[str, float]` (dopant flux request in cm⁻² s⁻¹
  or a target concentration, resolved to flux at recipe build).
- `doping.py` (new), snapshot keys `doping_profile_cm3`, `doping_nonuniformity_pct`,
  `sheet_resistance_ohm_sq`.
- `live.py`: flux monitor gets one trace per cell name; readout shows
  `T_cell` and shutter per cell; wafer map gains a "Doping" field.
- `setup_menu.py`: per-cell aim/offset editing is out of scope for the menu;
  the menu exposes the card selection and a "cells per element" count.
- `EXAMPLE_STACKS`: add `"HEMT_regrown_SD"` (GaN buffer → AlGaN barrier
  → n⁺ GaN:Si) and `"pGaN_gate"` (GaN:Mg) using the new fields.

**Tests.** `test_sources`: three Ga cells at 120° azimuths give a flatter
rotation-averaged profile than one and a smaller m=1 residual. `test_cells`:
PID reaches a flux setpoint without overshoot > 10 %; vapour law reproduces
1 ML/s Ga at ~1000 °C-class cell T [PRIOR range]. `test_doping`: Si profile
tracks `J_Si/GR`; Mg incorporation collapses above its onset; saturation
clamps; hotter centre → lower [Mg] centre (radial signal).

**Acceptance.** Ten named cells from the card; doping map on screen; regrown n⁺
stack runs end to end. ~700 LOC. Depends on WP0; WP1 for correct GR.

---

## WP4 — RF plasma source model (600 W @ 13.56 MHz)

**Goal.** Active-nitrogen flux is a function of RF power and N₂ flow with a gas
load that sets chamber pressure; the plasma setpoint requested by WP1 is solved
into (power, flow) like every other machine setpoint.

**Physics** (`plasma.py`, new).

- `Φ_N*(P, Q) = Φ_ref · (P/P_ref)^a · Q/(Q + Q_half)` with `a ≈ 1` at fixed
  flow and flow saturation `Q_half ≈ 1 sccm` [PRIOR; RF-plasma MBE practice:
  rate roughly linear in power, sub-linear in flow]. `Φ_ref` at
  `P_ref = 400 W, Q_ref = 2 sccm` sized so 600 W reaches ~1 µm/h-class GaN
  (≈1.1 ML/s) — the proposal's "enhanced source for high throughput" is a card
  number, not a code constant.
- Gas load `L = Q [sccm] × 1.27×10⁻² Torr·L/s per sccm`; chamber pressure from
  WP5 pump stack (`P = P_base + L/S_N2`). Growth pressure lands in the
  1–5×10⁻⁵ Torr range at 1–3 sccm, consistent with the current
  `plasma_pressure_torr` default.
- Ignition/response: first-order τ ≈ 6 s (existing), plus a "not ignited"
  state below `P_min` W.
- Ion-free flag: informational only (no ion-damage model in v1).

**Changes.**

- `plasma.PlasmaSource(power_W, flow_sccm, card)` with `active_flux_mls()`,
  `gas_load()`, `solve_for_flux(target_mls, flow_fixed)`.
- `process.ProcessSimulator`: `self.plasma` becomes a `PlasmaSource`; the per-
  layer V/III request from WP1 is converted to a power setpoint at the card's
  default flow; `n_flux_scale` slider maps to power. Snapshot adds
  `plasma_power_W`, `plasma_flow_sccm`, `plasma_ignited`.
- Reactor card: `plasma: {P_max_W: 600, P_ref, Q_ref, Phi_ref_mls, a, Q_half,
  tau_s, P_min_W}`.
- `data/benchmarks/plasma_rate_vs_power.json` slot (schema: power, flow,
  growth rate) + `benchmarks.py` observable `active_n_flux_mls`; empty until
  the tool produces data, but the fit path exists (Nelder-Mead + Bayes reuse).
- `live.py`: readout shows power/flow; strip chart trace for active-N flux.

**Tests.** monotone in P and Q; saturation; 600 W reaches the card's rated rate;
V/III request round-trips through `solve_for_flux`; pressure rises with flow.

**Acceptance.** Recipe V/III → plasma power on screen; rate ceiling of the tool
is a card number. ~250 LOC. Depends on WP1.

---

## WP5 — Chamber environment, diagnostics, interlocks

**Goal.** The chamber the wafer sits in matches slide 8: pump stack, LN₂ shroud,
10⁻¹¹ mbar base class, band-edge pyrometer, BFM, RGA, 30 keV RHEED, interlocks
and a run log.

**Physics / models.**

- **Pump stack** (`chamber.py`, extends `process.Chamber`): species ledger
  {N₂, H₂, H₂O, CO, Ga-vapour}; effective speed per species
  `S = S_turbo + S_cryo + S_ion` with species factors (cryo pumps H₂O/N₂ well,
  H₂ poorly; ion/TSP the reverse) [PRIOR]; outgassing load per species vs
  wall temperature and bake state; `P_base` after bake = 10⁻¹¹ mbar class;
  unbaked 10⁻⁹. Time constant `V/S` with V from the card (8-inch chamber
  ~300–500 L).
- **LN₂ shroud**: split the wafer's radiative sink into a cold fraction
  (shroud at 90–100 K, view factor `f_shroud`) and a hot fraction (cell flange,
  cells at their `T_cell`, view factor `f_cells`), giving an effective
  `T_sur,eff⁴ = f_shroud T_shroud⁴ + f_cells T_cells⁴ + (1−f)·T_wall⁴`. Replaces
  the single 350 K number; the current default is recovered when the card has
  no shroud section. Shroud state (LN₂ on/off) is a run input.
- **Pyrometer** (`diagnostics.py`): band-edge type reads the substrate
  (not the film) at `r_spot`, noise σ, τ, emissivity-independent by design;
  optional offset for viewport coating. Feeds WP2's controller.
- **BFM**: ion-gauge BEP = Σ over open cells of `flux × bep_per_mls ×
  species sensitivity` when the gauge is inserted; insertion is a live toggle
  that shadows the wafer (deposit paused).
- **RGA**: partial pressures from the species ledger; displayed as a bar
  panel; H₂O/CO relative to N₂ is the "interface cleanliness" proxy the
  regrowth process cares about (slide 5).
- **RHEED**: `energy_kv` default 30 in `rheed_pattern.pattern` and
  `physical_pattern`; live/report pass the card value.
- **Interlocks** (`control.py`): shutters forced closed when `P > 1×10⁻⁴ Torr`;
  heater clamp at `T_heater_max_K`; cell clamp at `T_cell_max`; plasma off
  when flow = 0. Each trip is logged.
- **Run log**: `ProcessSimulator.log` list of (t, event) and a CSV export of
  snapshots every N s behind `--log` (files only behind flags, per project
  rule).
- **Units**: snapshot keeps Torr internally; add `pressure_mbar` and a menu
  toggle for display.

**Changes.** `chamber.py`, `diagnostics.py`, `control.py` (new); `process.py`
wires them; `thermal.py` takes `T_sur_eff` from the chamber each step;
`live.py` adds RGA bars, BFM toggle, interlock banner; reactor card gains
`pumping`, `shroud`, `diagnostics`, `interlocks` sections.

**Tests.** base pressure after bake in the 10⁻¹¹ mbar class; growth pressure
with plasma on within 1–5×10⁻⁵ Torr; shroud-on lowers wafer T for the same
heater (edge more than centre); pyrometer noise bounded; interlock closes
shutters on a pressure spike and logs it; RHEED wavelength at 30 kV = 0.0698 Å.

**Acceptance.** Live dashboard shows pressure by species, RGA, pyrometer vs true
T, interlock state; base-pressure spec on screen. ~600 LOC. Independent of
WP1–4 except the pyrometer hook used by WP2.

---

## WP6 — Substrates and the regrowth-relevant process stages

**Goal.** The wafers the tool will actually see and the in-chamber part of the
regrowth flow (no etch, no anneal module — those are outside the growth chamber).

**Changes.**

- Substrate cards (`cards/`): `Si111_8in.json` (725 µm), `Sapphire_c_8in.json`
  (k exponent ~1.3, ε ≈ 0.45 back-coated, CTE 7.5×10⁻⁶), `SiC_4H_8in.json`
  (k 370 W/mK at 300 K, exponent 1.2, CTE 4.3×10⁻⁶), and a
  `GaN_on_Si_template.json` whose `template_lattice_a` = 3.189 (homoepitaxial
  regrowth: zero misfit, TDD inherited from the template field
  `tdd_template_cm2`). Each carries emissivity, k(T), CRSS, biaxial modulus.
- **Interrupt stage** in `process._build_stages`: `{"kind": "interrupt"}` from
  `Layer.pre_dwell_s` (closed shutters, N plasma optional, at the layer's T).
  During an interrupt `_deposit` is replaced by `_desorb`: thickness decrements
  by `R_dec(T(r)) × dt` when N is off (thermal clean), zero when N plasma is on
  (N-stabilised surface). This needs the `max(gr,0)` floor removed from the
  regime law for the closed-shutter branch only (handoff item 3 sketch).
  Guard: never below zero per node; Stoney increments are linear so negative
  increments are exact.
- **Regrowth interface bookkeeping**: the first layer after an interrupt
  records an `interface` entry {t, T, dwell, N_on, thickness_removed(r)} in the
  snapshot; the RGA H₂O/CO integral over the dwell is reported as the
  interface-exposure proxy. No Si/O interface model in v1 (needs data).
- `wafer.defect_density_profile`: wire the analytic step-density producer
  `step ~ (D/F)^(−1/6)` from `kinetics.d_over_f` (AUDIT §7 open item) so TDD
  finally has a producer on the live path, and add the template-TDD floor for
  homoepitaxial regrowth. Re-anchor `coalescence_calib` to the Mathis series
  so the 1e8–1e10 range holds.
- `EXAMPLE_STACKS["regrowth_nplus"]`: template GaN (interrupt 300 s, N on) →
  GaN:Si 100 nm at 0.3 ML/s Ga-rich.

**Tests.** interrupt with N off removes `R_dec × dwell` at the centre and less
at the cooler edge; with N on removes nothing; TDD profile is produced by the
live snapshot and stays within the literature gate; sapphire card gives a
larger ΔT than Si at the same heater (lower k).

**Acceptance.** Regrowth recipe runs on a GaN template with an interrupt, TDD and
doping on screen. ~400 LOC. Depends on WP3 (dopants) and WP5 (RGA proxy).

---

## WP7 — Calibration, validation, documentation

- `calibrate.py`: anchors per **zone** and per **setpoint** (2–3 heater
  settings) to break the emissivity/gap/heater-radius degeneracy (AUDIT §6
  open item); staged order thermal → flux → plasma → cells; blind hold-out
  stays the bow. `bayes.py` gets the plasma and cell parameters as
  `FitParam`s.
- `benchmarks.py`: new observables `active_n_flux_mls`, `cell_flux_mls`,
  `doping_cm3`; JSON slots with provenance strings ("EMPTY — fill from Phase-1
  commissioning"), so the day the tool produces data the fit is one command.
- `tests/test_literature_benchmarks.py`: gates for Mg incorporation onset,
  plasma linearity, 30 kV wavelength, 8-inch zone flattening.
- `explanation.md`: new sections (heater zones, cells, plasma, chamber,
  doping); `AUDIT.md` §8 "Phase-1 chamber build" with one entry per WP,
  numbers before/after.
- Menu==run gate test extended to zones, plasma power, cell temperatures.

~300 LOC plus docs. Last.

---

## Sequencing and dependencies

```
WP0 (envelope, card)  ──►  WP1 (V/III)  ──►  WP4 (plasma)
        │                       │
        └──►  WP2 (zones+control) ◄── pyrometer from WP5
        │
        └──►  WP3 (cells, dopants)  ──►  WP6 (substrates, interrupt, TDD)
                                              ▲
                          WP5 (chamber, diagnostics, interlocks)
                                              │
                                        WP7 (calibration, docs)
```

Order of execution: **WP0 → WP1 → WP2 → WP5 → WP3 → WP4 → WP6 → WP7.**
WP0+WP1 are two short sessions and already turn the 8-inch numbers from
"slips, 67 %" into a flux-geometry-limited few percent. WP2 is the proposal's
headline and the largest single change to `thermal.py`; do it before the
source bank so the source bank is tested against a flat wafer.

Rough size: ~3.2 kLOC new/changed, ~60 new tests; 8–10 sessions at one WP per
session (WP2, WP3, WP5 may take two).

## Risks and open decisions for the user

1. **Single pyrometer.** Slide 8 lists one band-edge pyrometer. Multi-zone
   closed-loop balancing cannot regulate what it does not sense; WP2 ships
   both modes and the plan recommends raising an edge sensor at the design
   review. The simulator will show the difference.
2. **Priors without data.** Plasma scaling, cell vapour constants, Mg
   incorporation and pump species factors are literature-typical priors. Each
   has a benchmark slot; none should be quoted as a tool number until WP7 is
   fed commissioning data.
3. **Regrowth interface chemistry** (Si/O pile-up, slide 5) is not modelled;
   only an exposure proxy is reported. A real model needs XPS/SIMS data from
   the pilot line.
4. **12-inch platens.** Everything scales with `R`; the Phase-1 card is 8-inch.
   A 12-inch card is a copy with `R 0.15` once zone radii for that platen exist.
5. **Performance.** Multi-zone Newton and ten cells multiply the per-step cost;
   the flux(r) cache (5 s) and the reduced-node optimiser already exist. Budget:
   live step ≤ 30 ms at 8-inch (currently ~10 ms).

## Explicitly out of scope

Transfer hub, load-lock, robot and platens handling, in-vacuum anneal module,
PVD module, dry etch, ex-situ cleans, dynamical RHEED, kMC decomposition
channel (AUDIT F5).
