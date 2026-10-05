# GaN/AlN MBE digital twin

This project models a 200 mm molecular beam epitaxy (MBE) growth chamber to help design a machine that grows more uniform semiconductor layers. It studies how source positions, nitrogen supply, wafer heating and operating conditions affect the thickness of GaN grown on a silicon wafer.

The long-term scope includes GaN and AlN. The working growth model currently covers **GaN only**.

**Current state:** this is a research codebase with working physics models and design studies for a representative chamber. The proposed machine has not been built, and its drawings and measurements are not yet available. Several models have passed numerical checks, and the metal-source model has been compared with a published experiment. The nitrogen, heater and growth models still need experimental validation. A complete twin calibrated to the proposed machine is not yet implemented.

This overview reflects the recorded studies through **3 October 2026**. Detailed results and their reproduction commands are linked below.

## What the project is trying to achieve

MBE grows thin crystal layers by directing beams of material onto a heated wafer in a vacuum chamber. Heated cells supply gallium and aluminium; a plasma source supplies reactive nitrogen. The wafer rotates to spread the incoming material more evenly.

On a 200 mm wafer, source geometry and temperature differences can produce uneven growth. This project asks which changes would improve thickness uniformity while maintaining a useful growth rate and acceptable material quality. The model can compare design options before hardware is built, and later help interpret measurements from the machine.

![Representative chamber with sources below a downward-facing wafer](docs/figures/chamber.png)

*Representative geometry, not a drawing of the proposed machine. The baseline gallium source is 350 mm from the wafer centre, at 46° to the wafer axis.*

Success means a measured improvement on real wafers against an agreed baseline. A numerical uniformity target and minimum acceptable growth rate have not yet been agreed. Material quality will need its own measurements; the current model does not predict it.

## How the model works

The studies connect four main calculations:

1. **Material leaving the sources.** Calculate how the metal crucible and nitrogen outlet holes shape their beams.
2. **Material reaching the wafer.** Account for source position, wafer rotation, obstructions and scattering by gas in the chamber.
3. **Wafer temperature.** Calculate heat transfer between the heater, wafer and holder.
4. **GaN growth.** Combine the gallium supply, nitrogen supply and temperature at each point to estimate growth rate, thickness and whether gallium droplets form.

Layout studies combine these calculations with pumping capacity, heater limits and mechanical clearances. They also vary uncertain inputs to see whether a design still works when conditions differ from the nominal case.

The repository uses Python models, **SPARTA** for particle simulations with gas collisions, and **Elmer** for heat-transfer verification cases. The main heater design studies use a separate, simplified Python model. The workflow is intended to run on a laptop; larger particle simulations run in batches.

## What is implemented

| Area | Available now | Main limitation |
|---|---|---|
| Metal sources | Direct-beam transport, crucible emission, gas collisions, tilted liquid surfaces, fill-level changes and source-temperature adjustment | Gallium collision properties remain uncertain; experimental comparison uses a bismuth source |
| Nitrogen source | Outlet-plate geometry, beam maps, off-centre aiming, pointing errors and a particle simulation of flow through one hole | No measured active-nitrogen map; total reactive output is an uncertain input |
| Chamber gas | Pressure from nitrogen flow and effective pumping speed; direct-beam loss and scattered atoms returning to the wafer; gas plume near the nitrogen source | Simplified chamber and fixed gas fields; wall behaviour is uncertain |
| Heater and wafer | Radial radiation and conduction, heater zones, holder contact, power limits, temperature sensing and control studies | Simplified geometry; no measured heater validation |
| GaN growth | Steady-state growth rate, decomposition and gallium balance; nitrogen-limited growth and droplet onset | No transient growth, AlN chemistry, morphology or crystal-quality prediction |
| Layout comparison | Source and shutter clearances; coupled supply, pressure, temperature and thickness calculations across many operating cases | Assumed hardware dimensions and properties; no mechanical approval for the real machine |
| Commissioning preparation | Measurement plan and rehearsals using synthetic data | No calibration or validation data from the proposed machine |

## What the studies have found

### Nitrogen and temperature determine thickness in gallium-rich growth

In the model's gallium-rich operating range, enough gallium is available everywhere and growth is mainly limited by reactive nitrogen. Thickness then follows the nitrogen map, with a temperature-dependent loss from GaN decomposition.

Gallium uniformity still matters: too little gallium leaves this operating range, while too much produces droplets. A flatter gallium beam alone therefore does not guarantee a flatter grown layer. The nitrogen, gallium and temperature maps have to be assessed together.

### The gallium beam changes as the crucible empties

The model follows evaporation from the liquid surface through the crucible and onto the rotating wafer. It includes the fact that liquid gallium stays level when its cell is tilted.

At the baseline 46° port angle, the predicted gallium supply variation grows from about **2% to 8–10% range/mean** as the liquid recedes from 40 mm to 120 mm below the crucible mouth. Steeper source angles can reduce this to roughly 1–2%, but the best angle changes with fill level. A fresh charge would spill at angles preferred by a nearly empty crucible, so one fixed angle cannot be optimal throughout a campaign.

![Gallium arrival profiles and uniformity as the crucible empties](docs/figures/ga_fill.png)

The source must also run hotter as it empties to maintain the same gallium supply. The collision simulations require about a 12–13 °C increase across the studied fill range at 46°. These are gallium-arrival results; they do not directly predict layer thickness.

The source model has been compared with the published R07 bismuth experiment. It reproduces normalized deposition profiles to roughly 1–2%. Including paired bismuth atoms brings calculated absolute rates to approximately −6.5% to +5% of the measured rates. That supports the modelling method, but does not establish the collision properties of gallium.

### Nitrogen plate geometry and aim are major design choices

Long, narrow outlet holes produce a concentrated nitrogen beam. Aiming that beam at the wafer centre can give poor uniformity. Aiming near the wafer edge lets rotation distribute it more evenly, but makes alignment important. Shallow holes are generally less sensitive to pointing errors.

![Nitrogen uniformity as the source aim changes for several hole depths](docs/figures/n_aim.png)

The plate must also pass enough gas. At high flow, collisions inside its holes can invalidate the simplest beam model. The repository includes a single-hole collision study, but it does not simulate the entire plasma source, reactive species or interactions between neighbouring holes.

The fraction of nitrogen feed that leaves the source in a reactive form is still unknown for the proposed hardware. Estimates from published growth rates depend on assumed geometry and are not supplier specifications.

### Heater design needs both an even temperature profile and enough power

The heater studies show that zone count alone is not enough. Radial power distribution, wafer contact with the holder and heat loss at the edge all matter. Measuring temperature at several radii helps control the profile; one centre reading mainly controls the overall temperature.

Heater limits also matter. A design that produces an even wafer in an unconstrained calculation may require an element temperature above its rating. The layout studies include that limit and variations in wafer heat emission and holder contact.

A cooler wafer reduces the thickness loss from decomposition, but narrows the allowable gallium supply range. The model therefore favours adjusting gallium supply using the wafer-temperature reading. The growth window must first be measured on the machine's own temperature scale.

### Scattered atoms cannot all be treated as lost

Gas in the chamber scatters atoms travelling toward the wafer. The latest studies follow those atoms after collisions, including through the denser gas near the nitrogen source. Many still reach the wafer, especially gallium atoms.

Including them changes the required nitrogen flow and the predicted thickness profile. It also makes the result depend on whether chamber walls absorb reactive nitrogen or return it to the gas. That behaviour needs measurement during commissioning.

## Current design direction

The provisional choice is **layout B-p**: the nitrogen source sits on the same port ring as the metal cells, with its beam aimed about 97.5 mm from the wafer centre toward the source side. Its aim was selected for growth pressure. **B-L** uses a larger outlet plate designed in this study and an aim offset of about 90 mm. It is a promising alternative if the supplier can build and operate that plate.

The current working operating point is **1 µm/h at about 720 °C**, with gallium supply adjusted from a wafer-centre temperature reading. This is a modelling choice, conditional on nitrogen output, pumping, heater performance and acceptable crystal quality. The temperature is based on the published growth laws' scales and must be calibrated on the real machine.

At that operating point, the studies including scattered atoms and the nitrogen plume give worst-case thickness **half-range/mean of about 1.5–1.8%** across the qualifying scenarios. Other scattering and wall assumptions extend that range to about 2.1%. These are model results over a selected set of conditions, not demonstrated wafer uniformity or a probability of production success.

The main decisions remain:

- **Nitrogen source and plate:** the larger B-L plate makes 1 µm/h achievable at more plausible reactive-nitrogen output, given strong pumping. Its manufacturability and stable plasma operating range need confirmation.
- **Pumping:** effective nitrogen pumping speed determines growth pressure. The present model does not establish whether weak pumping can support the intended rate.
- **Temperature measurement and gallium calibration:** the studies indicate a shared error allowance equivalent to roughly 3 °C for positioning gallium supply within the growth window. Sensor repeatability of about 1–2 °C is only one part of that allowance.
- **Mechanical fit:** simplified models give about 6 mm minimum guaranteed clearance for the B family over the full shutter motion. Actual source, shutter, holder and chamber drawings are needed to check the design.
- **Acceptance criteria:** uniformity, minimum growth rate and material-quality requirements must be agreed before a layout can be accepted.

The [layout comparison](docs/LAYOUT_COMPARISON.md) contains the assumptions, scenario tables and failure conditions. Its section 10 includes scattering and the nitrogen plume; earlier sections retain the older direct-beam results for comparison.

### Reading the uniformity numbers

Two metrics appear in the studies:

- **Range/mean:** `(maximum − minimum) / mean × 100%`, used in many source-beam studies.
- **Half-range/mean:** half of that value, used for the main thickness comparisons and sometimes written as “±X%”.

For example, 4% range/mean is 2% half-range/mean. The latter is not a statistical confidence interval. Comparisons must also use the same wafer area and edge exclusion; the detailed study records specify these. Percentages of tested cases are shares of a chosen grid of conditions, not manufacturing yield estimates.

## What needs to happen next

1. **Obtain the hardware information.** Priorities are reactive-nitrogen output versus flow and power, the outlet-plate drawing, effective pumping speed, heater ratings and source/mount dimensions. The [hardware request list](docs/HARDWARE_REQUESTS.md) explains what each answer resolves.
2. **Agree the performance requirements.** Set the baseline, thickness target, minimum useful growth rate and material-quality requirements. Confirm whether the proposed temperature is suitable for the intended layers.
3. **Replace assumed geometry and properties.** Recheck clearances, source maps, gas transport and heating with the actual hardware data.
4. **Calibrate during commissioning.** Measure nitrogen-limited and gallium-limited growth, temperature profiles, pressure, source alignment and droplet onset. The synthetic rehearsals suggest varying pump throttling at fixed nitrogen flow to distinguish gas scattering from changes in source output.
5. **Validate on separate runs and demonstrate improvement.** Reserve complete wafers and operating conditions that were not used for fitting. Compare a baseline and candidate design using the [measurement protocol](docs/DATA_AND_VALIDATION_PLAN.md).

The [commissioning plan](docs/COMMISSIONING_PLAN.md) includes the measurement sequence and the synthetic rehearsals already completed for nitrogen, temperature and gallium calibration. Those rehearsals test the proposed procedure; they are not experimental validation.

Further scans of steeper nitrogen ports, additional gallium collision sizes, adjustable cells and heater variants are on hold until they are likely to change a design decision.

## Running the code

Use **Python 3.11 or newer**. From the repository root, create a virtual environment and install the package with its test dependencies. For PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[test]"
.\.venv\Scripts\python.exe -m pytest -q
```

To run the introductory direct-beam geometry scan:

```powershell
.\.venv\Scripts\python.exe scripts/stage_a_beam_scan.py
```

This scan compares source geometries and writes results under `results/stage_a_beam_scan/`. It does not run the full coupled layout study.

SPARTA studies additionally require the pinned SPARTA build in WSL. Elmer verification cases require the configured Elmer installation. Tests requiring an unavailable external solver are skipped. See the [developer guide](docs/DEVELOPER.md) for solver setup, optional tools and batch resource limits, and [reproduction guide](docs/REPRODUCE.md) for the command behind each recorded study.

## Repository guide

| Location | Contents |
|---|---|
| [`src/mbe_twin/`](src/mbe_twin/) | Physics models, geometry, uniformity metrics and solver interfaces |
| [`scripts/`](scripts/) | Study runners, comparisons, plotting and provenance checks |
| [`tests/`](tests/) | Numerical checks, conservation tests, regressions and solver checks |
| [`cases/`](cases/) | Fixed batch settings and external-solver verification cases |
| [`data/`](data/) | Model parameters, benchmarks, hardware assumptions and compact recorded results |
| `results/` | Generated study output and large solver files; ignored by Git |
| [`docs/`](docs/) | Design comparisons, setup, reproduction instructions, reviews and validation plans |
| [`ref/`](ref/README.md) | Reference library, evidence notes and archived plans |

Run records retain settings, source-code hashes and solver information so results can be traced to the code that produced them. The [provenance report](data/runs/studies/PROVENANCE.md) records differences between saved studies and later code changes. Numerical tests and repeat runs check implementation and simulation error; agreement with machine measurements is a separate requirement.

For the broader scope and development plan, read the [Phase-1 plan](PHASE1_CHAMBER_PLAN.md). The [physics architecture](mbe_twin.md) describes the intended equations and model interfaces, including capabilities that are still planned. The original [project proposal](MBE_Phase1_Proposal_v1.2.pptx) is preserved; subsequent engineering reviews are in the Markdown documents.

README figures are generated by [`scripts/make_readme_figures.py`](scripts/make_readme_figures.py) from saved study records.
