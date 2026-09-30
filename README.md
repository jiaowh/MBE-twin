# GaN/AlN MBE digital twin

A laptop-scale computer model of a 200 mm molecular beam epitaxy (MBE) machine. Its purpose is to find design and operating changes that make grown layers more uniform across the wafer, before those changes are tried on the real machine.

This page explains the project in plain language. The technical details (code, solvers, commands, status by subsystem) are in the [developer guide](docs/DEVELOPER.md). The command behind every quoted number is in [docs/REPRODUCE.md](docs/REPRODUCE.md).

**Contents**
1. [The machine and the problem](#1-the-machine-and-the-problem)
2. [What the twin is](#2-what-the-twin-is)
3. [The gallium beam](#3-the-gallium-beam)
4. [Gallium on the 200 mm wafer](#4-gallium-on-the-200-mm-wafer)
5. [Nitrogen](#5-nitrogen)
6. [How the layer grows](#6-how-the-layer-grows)
7. [Wafer temperature](#7-wafer-temperature)
8. [How results are made trustworthy](#8-how-results-are-made-trustworthy)
9. [Where things stand](#9-where-things-stand)
10. [Glossary](#10-glossary)

## 1. The machine and the problem

**What MBE does.** MBE grows extremely thin crystal layers atom by atom. Here the layers are gallium nitride (GaN) and aluminium nitride (AlN), the materials in LEDs and fast power transistors.

**How it works.**
- A sealed chamber is pumped down to a near-perfect vacuum.
- Small ovens called **effusion cells** heat liquid gallium or aluminium until it evaporates.
- The vapour flies in straight lines across the chamber, like light from a lamp, and lands on a hot silicon wafer.
- There it meets nitrogen from a **plasma source** and forms the crystal.
- The wafer spins so that every point on it sees the sources from all sides.

![Side view of the chamber: the wafer at the top facing down, with the gallium cell and nitrogen source aimed at it from below](docs/figures/chamber.png)

*Schematic of the representative chamber, not to scale. The gallium cell sits 350 mm from the wafer centre, tilted 46° from the wafer's axis.*

**The problem: nonuniformity.** The sources sit off to the side, so the edge of a 200 mm wafer doesn't receive exactly the same supply as the centre, and the heater doesn't warm it perfectly evenly. The grown layer ends up slightly thicker in some places than others, and its properties vary too. We measure this with **range/mean**: the difference between the thickest and thinnest points, divided by the average. For example, 2 % means the thickest spot is 2 % thicker than the thinnest, relative to the average.

**The goal.** Reduce nonuniformity across the 200 mm wafer while keeping the required growth rate and material quality. Success will first be judged on thickness uniformity against an agreed baseline, and will count only once it is measured on the real machine. The [project outcome criteria](PHASE1_CHAMBER_PLAN.md#11-project-success-and-design-decisions) and [measurement protocol](docs/DATA_AND_VALIDATION_PLAN.md#demonstrating-wafer-uniformity-improvement) define how improvements will be assessed. The numerical targets will be set from baseline data.

## 2. What the twin is

A **digital twin** here is a set of physics simulations that together predict how evenly material arrives on, and grows on, the wafer. We can then change things on the laptop (where a source points, the heater design, oven temperatures) and see what improves the wafer. That is much cheaper than testing each change on the real machine.

```mermaid
flowchart LR
    A[Gallium & aluminium ovens<br/>how the vapour spreads] --> D[Supply map<br/>on the wafer]
    B[Nitrogen plasma source<br/>how the gas spreads] --> D
    C[Heater<br/>wafer temperature map] --> E[Growth at the surface<br/>thickness & quality map]
    D --> E
    E --> F[Compare design options<br/>port angles, crucibles, heaters]
    F --> G[Test the best one<br/>on the real machine]
```

**Why a "representative" chamber.** The real machine isn't built yet, and no manufacturer publishes full drawings. So we model a typical 200 mm GaN machine of the RIBER / Veeco class, with dimensions taken from published sources. That lets us compare design ideas now. Exact predictions for the real machine need its own drawings and measurements.

**How each part earns trust.** Every piece of physics goes through the same ladder before its results are used:

```mermaid
flowchart LR
    V1[1. Exact test<br/>matches a textbook answer] --> V2[2. Published experiment<br/>reproduces a real measurement] --> V3[3. Representative chamber<br/>design comparisons] --> V4[4. Real machine<br/>calibrated with its own data]
```

## 3. The gallium beam

**The crucible.** The oven holds liquid metal in a deep cup (the **crucible**). The vapour leaves the liquid surface, bounces off the hot cup walls, and comes out of the mouth as a spray, the **beam**. The cup walls shape that spray: a deep, nearly empty cup gives a narrower spray than a full one.

**The liquid stays level.** The cell is tilted toward the wafer, but liquid gallium stays level, like water in a tilted glass. That creates a limit. At the usual 46° tilt, a cup filled closer than about 37 mm to its mouth spills. As the charge is used up over a campaign, the level drops deeper into the cup.

![Three tilted cups: one too full and spilling, one freshly filled 40 mm below the mouth, one nearly empty at 120 mm](docs/figures/level_melt.png)

*The "recess" is how far the liquid sits below the cup's mouth, measured along the cup's axis. The twin studies 40 mm (fresh), 70 mm and 120 mm (nearly empty).*

**When atoms collide.** At low oven temperatures the vapour is so thin that atoms never meet each other; they only hit walls. The simple model (**free-molecular**) assumes exactly that, and follows millions of virtual atoms bouncing through the cup. At real GaN growth speeds, though, the gallium vapour inside the cup is dense enough that atoms do collide, and that reshapes the spray. For that we use **SPARTA**, a free research program that simulates gas collisions (method: DSMC, see the [glossary](#10-glossary)).

**Checking against a real experiment.** In 1991 Gericke and colleagues (reference R07) measured the spray from a bismuth cell at three evaporation speeds. Faster evaporation means denser vapour, more collisions and a wider spray. The collision model follows all three measured shapes within about 1–2 %. The no-collision model misses by up to 20 %.

![Measured and simulated deposit profiles at three evaporation speeds; the collision model follows the measurement while the no-collision model does not](docs/figures/r07_validation.png)

*Deposit across a flat plate in front of the cell, relative to the centre. Black: measurement. Blue: collision model with its statistical error. Orange: no-collision model.*

What this test settles and what it leaves open:
- **One tuned number.** Collisions depend on how "big" an atom is in a collision. For bismuth the test pins that size to 8–10 Å.
- **Open puzzle.** The model's absolute deposition rate is 7–15 % lower than measured in every case. This is not simulation noise. The spray *shape*, which is what uniformity depends on, is reproduced.
- **A likely explanation.** Bismuth vapour is not all single atoms. Published data put about 30 % of it as paired atoms (Bi₂). A pair carries two atoms, so at the same vapour pressure more bismuth arrives, about 12–13 % more. That is the size of the gap. It is not yet built into the model: the pressures the 1991 paper states are themselves 1.4–1.7 times the handbook values, so the check needs care.

## 4. Gallium on the 200 mm wafer

With the beam model tested, we apply it to a gallium cell in the representative chamber at a real GaN growth speed (1 µm per hour). The model follows atoms from the liquid surface, through the cup, across the chamber and onto the spinning wafer.

**Unevenness grows as the cup empties.** At the standard 46° port, unevenness grows from about 2 % with a fresh charge to 8–10 % when the cup is nearly empty. The deeper the liquid, the narrower the spray, so the wafer edge gets less.

![Left: Ga arrival across the wafer radius for three fill levels. Right: range/mean rises from about 2 % to 8–10 % as the melt recedes](docs/figures/ga_fill.png)

*Right panel: each line uses a different assumed gallium atom size. The dashed line is the no-collision model.*

**The biggest unknown: the gallium atom's size.** No published source gives the collision size of a gallium atom, so we try a range (2.5, 5.68 and 8 Å). It hardly matters for a fresh charge. For a nearly empty cup, bigger atoms mean more collisions, which widen the spray again. There the answer ranges from about 8 % to 10 %.

A new estimate narrows that range from physics rather than guesswork. Atoms attract each other at a distance with a strength that has been calculated for every element. Scaling from noble gases, whose collision sizes are well measured, gives about 4 Å for gallium if that attraction were all there is. The same method says bismuth should be about 4 Å, but the 1991 experiment needs 8–10 Å. Metal atoms bond as well as attract, which makes them "look" bigger. Carrying bismuth's extra factor over to gallium gives at most about 9.6 Å. The next runs will use 4, 6 and 9.6 Å. Gallium vapour, unlike bismuth, is almost entirely single atoms (paired atoms under 0.1 %, checked against a 1998 measurement), so the model's single-atom picture holds.

**Choosing the port angle.** Tilting the cell more steeply compensates for the narrowing spray. The best angle depends on the fill: about 48° for a fresh 40 mm charge, about 54° at 70 mm and about 58° at 120 mm. At its best angle each fill reaches roughly 1–2 %.

![Range/mean against port angle for three fill levels, with the spill limit for a fresh charge above 48.2°](docs/figures/ga_angle.png)

*Solid lines: collision model (atom size 8 Å) with statistical error. Dotted: no collisions. Red shading: angles where a fresh charge would spill. Grey bars at 54° and 58°: the spread of repeat runs with finer settings. Grey band: values not yet pinned down by those repeats.*

What the angle study means:
- **No fixed angle is best for a whole campaign.** A fresh charge would spill beyond 48.2°, while an emptying cup prefers 54–58°. Choosing a port angle is a real design trade-off.
- **The best values are only known roughly.** We repeated the two best cases with a different random seed, a halved time step, a finer grid and twice the simulated atoms. The results moved between 0.7 and 1.4 % at 70 mm, and between 0.9 and 1.9 % at 120 mm. So the best achievable is about 1 % for a half-empty cup and about 1.5–2 % for a nearly empty one. Pinning it down further would need much longer runs.

**Keeping the gallium supply constant.** As the cup empties, less vapour escapes, so the oven must run hotter to keep the same gallium supply. The no-collision model puts the increase at about 8.5 °C between 40 and 120 mm. With collisions, the supply actually delivered at those temperatures is 4 % below to 9 % above the target. So the twin now adjusts the temperature from the collision simulation itself, repeating until the supply at the wafer centre is within ±1.5 % of the target. These runs started on the night of 30 September.

What is held constant is the gallium arriving at the centre of the wafer, not the growth rate. The growth rate also depends on the nitrogen supply and on how much gallium actually sticks, which the twin does not model yet. The runs also record the average gallium supply over the whole wafer, since the edge receives less than the centre.

**What these results are, and are not.** They compare design options on a representative chamber, with a known uncertainty and one clearly bracketed unknown (the atom size). They are not a thickness prediction for a specific machine. In the usual gallium-rich GaN recipe, thickness follows the nitrogen supply (next section).

## 5. Nitrogen

In the usual gallium-rich recipe, a thin excess film of gallium sits on the surface, and the crystal grows as fast as nitrogen arrives. So the **thickness map follows the nitrogen map**. What matters for the gallium cell is the **gallium-to-nitrogen ratio** across the wafer, which must stay gallium-rich everywhere.

**The nitrogen source.** The plasma source releases its gas through a plate with many small holes. Our model of that plate shows:
- **Hole shape sets the spread.** How the nitrogen spreads over the wafer depends mostly on the holes' shape (how deep compared with how wide). The plate's overall size barely matters.
- **Real plates look much less even than the gallium beam.** Two published plates give real hole counts and sizes (about 700 to 4000 holes, 0.2–0.34 mm wide), but not the plate thickness, so we tried 0.5–2 mm. At normal gas flows the gas in the holes is thin enough for the model to apply. Straight holes that are several times longer than they are wide send the nitrogen out in a narrow jet. Aimed at the wafer centre from 350 mm, the model then gives nitrogen maps with range/mean of 20 % to over 100 %, against 1–10 % for gallium. - **Aiming off-centre evens it out, at a price.** If the source is pointed not at the wafer centre but near its edge, the spinning wafer sweeps the narrow jet over a ring. In the model this brings every published plate below 1 % range/mean. The catch is that the narrower the jet, the more precisely the source must point. For the deepest holes, a pointing error of 1.6° (10 mm at the wafer) can cost up to 10 points; for a thin plate it hardly matters. A thin plate or shallow holes are the safer choice, and the source mounting needs a way to measure and adjust its aim.
- **Still the least certain input.** None of this is tested against a measured nitrogen map, and the real plate's thickness, hole pattern and hole angles are unknown. A thickness map grown with nitrogen as the limiting supply on the real machine will be the direct test.
- **The ratio can go either way.** Combining gallium and nitrogen maps can make the ratio across the wafer more even than the gallium alone, or less even, depending on the plate. A drawing of a real (or representative) plate is needed before settling where the gallium cell goes.

## 6. How the layer grows

The first growth model combines the gallium map, the nitrogen map and the wafer temperature at each point on the wafer. It uses only constants measured in published experiments (R20, G01, G02) and keeps exact account of every gallium atom: built into the crystal, evaporated again, or left on the surface as droplets.

![Left: the usable range of gallium-to-nitrogen supply ratio between rough growth (below 1) and droplets (above each line) widens with temperature. Right: the thickness change from a 10 °C hotter wafer edge rises steeply with temperature](docs/figures/growth_window.png)

*Left: the usable window lies between rough growth (ratio below 1) and gallium droplets (above the line). The three lines are three published measurements of where droplets start. Right: how much a wafer edge 10 °C hotter than the centre changes the layer thickness there.*

What it shows:
- **Inside the window, the gallium map does not affect thickness.** The layer grows as fast as nitrogen arrives, minus a small loss from the crystal slowly evaporating at growth temperature. So thickness follows the nitrogen map and the temperature map.
- **The gallium map decides whether the whole wafer stays in the window.** At a cooler growth temperature (about 700 °C) the window is narrow. A nearly empty gallium cup at the standard 46° port can push part of the wafer out of it, while the best angles keep it in.
- **Temperature is a trade-off.** A hotter wafer widens the window, but the evaporation loss rises steeply with temperature. A 10 °C difference between wafer centre and edge then changes thickness by about 0.3 % at 700 °C, 1–1.6 % at 740 °C and 4.5–6.4 % at 780 °C (range/mean). So the chosen growth temperature sets how even the heater must be.
- **Uncertain edges of the window.** Three published measurements of where droplets start disagree by up to a factor of four, partly because each lab measures temperature differently. The real machine's own measurements will settle it.

A provisional summary of what these results suggest for the machine design, and what they cannot yet say, is in [docs/SOURCE_DESIGN_PROVISIONAL.md](docs/SOURCE_DESIGN_PROVISIONAL.md).

## 7. Wafer temperature

The wafer heater is modelled with **Elmer**, a free heat-flow simulator. It passes two exact tests: heat conduction, and heat radiation between two hot plates (within 0.25 °C).

The first published heater experiment we examined (R03) turned out to be a weak test. Its wafers sit off-centre on a large plate, and its measured temperature differences (2–6 °C) are close to its own ±2 °C measurement error. Its data are saved, and better heater experiments are still being looked for.

**A first 200 mm heater model.** A simplified model of a heater under a spinning wafer, whose rim rests on a holder ledge, is checked against an exact radiation answer (within 0.03 °C). Its dimensions are typical values, not a real machine's. It shows:
- **One heating zone is far from enough.** The wafer edge runs about 90 °C colder than the centre. Two zones bring this to about 35 °C and three to about 17 °C.
- **How the heat is spread matters more than the number of zones.** A heater whose heating density varies smoothly with radius gets to about 2–10 °C.
- **The wafer's edge support matters as much as the heater.** How far the wafer overlaps its holder, and how well they touch, changes the result several-fold.
- **Control precision matters.** A 5 % error in one zone's power adds 6–10 °C. So either the zone powers must be held very precisely, or the wafer temperature must be measured at more than one radius.

At 740 °C, every 1 °C of temperature spread adds roughly 0.1–0.16 % to the thickness spread (section 6). So these numbers feed directly into the heater and sensor choices for the real machine.

## 8. How results are made trustworthy

- **Statistical error bars.** Collision simulations are statistical, like an opinion poll, so every result carries an error estimate from splitting the run into independent pieces. Important cases are rerun with another random seed, smaller time steps and finer grids.
- **A checked unevenness formula.** Turning a noisy simulated spray into one range/mean number needs a smoothing formula. Ours was tested against exact answers: it is off by at most 0.2 points, and its random scatter is 0.3–0.5 points.
- **Every result can be rerun.** Each run gets its own folder and records its full settings before it starts. Saved results carry a fingerprint of the exact code that produced them, and batch files spell out every setting.
- **Automatic tests.** About 130 automatic tests check the code; all pass. Every number is traced to a published source, and unknown or unexplained results are labelled rather than hidden.
- **The laptop stays safe.** Simulation output is read one snapshot at a time. A new job starts only when enough memory is free, both in Windows and in the Linux environment where the collision simulator runs. When the laptop is shared with other work, jobs also wait for a free processor core, and an overnight queue stops starting new jobs at a set hour.

## 9. Where things stand

| Part | Status |
|---|---|
| Gallium beam model | Tested against a real experiment (shape within 1–2 %); absolute rate 7–15 % low, likely paired bismuth atoms (test running) |
| Gallium on the 200 mm wafer | Fill and port-angle study done, including numerical checks at the best angles; constant-gallium-supply runs running |
| Nitrogen source | Two published plates modelled: a narrow jet unless aimed off-centre, then below 1 % but sensitive to pointing; plate thickness and pattern unknown |
| Wafer heater | First 200 mm model: zone count, edge support and control precision compared; not yet checked against any measured heater |
| Surface growth chemistry | First model from published constants: growth window and thickness from the gallium, nitrogen and temperature maps; not yet tested against a wafer |
| The real machine | Needs its drawings and first measurements, which will turn the representative twin into its own twin |

**Next.**
1. Finish the constant-gallium-supply runs and the test of whether paired bismuth atoms close the 1991 rate gap (both running).
2. Decide, from that test, whether to rerun the gallium study with atom sizes of 4, 6 and 9.6 Å. These are plausible values spanning a range argued from other atoms, not proven limits.
3. Check that a steep, off-centre nitrogen port fits next to the gallium cell and shutters, and find what the real plates look like (thickness, hole pattern, hole angles).
4. Design a crucible shape that keeps the spray steadier as it empties. Two patented production designs are now on file: a cup with a narrow inner opening, whose output does not depend on the fill, and a Riber-type cell reported to give 0.4 % over 190 mm.
5. Add a platen and heat shields to the heater model, and find a stronger heater experiment. Emissivity data for the silicon wafer and the boron-nitride parts are now on file. A production-heater study (R05) measured what spoils wafer temperature (ring overlap, a shiny platen, a too-small heater gap), which the heater model must be able to show, but it lacks the dimensions needed to recreate it exactly.

The sources and calculations from the latest search are in the [physics-data note](ref/notes/PHYSICS_DATA_SEARCH_2026-09-30.md).

**Side idea (optional, not on the main path).** Could an adjustable gallium oven keep the layer even as the cup empties? The best angle steepens from about 48° to 58° as the cup empties, and a full cup only spills at steep angles, so "start shallow, tilt steeper later" never spills. When the laptop is free, we'll compare three ways to do it:
- an oven that can tilt at its mounting;
- two gallium ovens at different angles, with their output share changing over time;
- a better-shaped cup.

Tilting a hot oven of liquid gallium has real engineering risks (sealing, spitting droplets, recalibration), and the comparison will list them. Details are in the [reference-chamber note](ref/notes/REFERENCE_CHAMBER.md#exploratory-non-essential).

## 10. Glossary

| Term | Meaning |
|---|---|
| Å (ångström) | 0.1 nanometre, about the size of an atom |
| Beam | The spray of vapour leaving a source |
| Crucible | The cup inside an effusion cell that holds the liquid metal |
| DSMC | Direct Simulation Monte Carlo: simulates a gas by following many sample atoms and letting them collide at random with the right probabilities |
| Effusion cell | The oven that evaporates the metal |
| Free-molecular | Gas so thin that atoms never collide with each other, only with walls |
| Gallium-rich growth | A recipe with slightly more gallium than nitrogen, so thickness follows the nitrogen supply |
| MBE | Molecular beam epitaxy: growing crystals from beams of atoms in vacuum |
| Range/mean | (thickest − thinnest) ÷ average: our measure of unevenness |
| Recess | How far the liquid surface sits below the crucible's mouth |
| Representative chamber | A typical machine built from published dimensions, standing in until the real machine's drawings exist |
| R03, R07, … | Reference numbers of published sources in the [reference library](ref/) |

Figures are drawn by `scripts/make_readme_figures.py` from the saved run records.
