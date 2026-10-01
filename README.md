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
8. [Choosing a layout](#8-choosing-a-layout)
9. [How results are made trustworthy](#9-how-results-are-made-trustworthy)
10. [Where things stand](#10-where-things-stand)
11. [Glossary](#11-glossary)

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

**When atoms collide.** At low oven temperatures the vapour is so thin that atoms never meet each other; they only hit walls. The simple model (**free-molecular**) assumes exactly that, and follows millions of virtual atoms bouncing through the cup. At real GaN growth speeds, though, the gallium vapour inside the cup is dense enough that atoms do collide, and that reshapes the spray. For that we use **SPARTA**, a free research program that simulates gas collisions (method: DSMC, see the [glossary](#11-glossary)).

**Checking against a real experiment.** In 1991 Gericke and colleagues (reference R07) measured the spray from a bismuth cell at three evaporation speeds. Faster evaporation means denser vapour, more collisions and a wider spray. The collision model follows all three measured shapes within about 1–2 %. The no-collision model misses by up to 20 %.

![Measured and simulated deposit profiles at three evaporation speeds; the collision model follows the measurement while the no-collision model does not](docs/figures/r07_validation.png)

*Deposit across a flat plate in front of the cell, relative to the centre. Black: measurement. Blue: collision model with its statistical error. Orange: no-collision model.*

What this test settles and what it leaves open:
- **One tuned number.** Collisions depend on how "big" an atom is in a collision. For bismuth the test pins that size to about 7–9 Å once paired atoms are included (8–10 Å without them).
- **A puzzle, now mostly solved.** With single atoms only, the model's absolute deposition rate was 7–15 % lower than measured in every case. This was not simulation noise. The spray *shape*, which is what uniformity depends on, was reproduced either way.
- **A likely explanation.** Bismuth vapour is not all single atoms. Published data put about 30 % of it as paired atoms (Bi₂). A pair carries two atoms, so at the same vapour pressure more bismuth arrives, about 12–13 % more. That is the size of the gap. The pressures the 1991 paper states are themselves 1.4–1.7 times the handbook values, so the check needs care. Paired atoms have now been added to the collision model. With the published share of pairs, the gap closes: the model reads between 6.5 % low and 5 % high at the three speeds, instead of 7–15 % low, and the spray shapes still match. The fitted atom size moves from about 9 Å to about 8 Å. How many atoms are paired and how big an atom is trade off against each other, and the 1991 data cannot separate the two.

## 4. Gallium on the 200 mm wafer

With the beam model tested, we apply it to a gallium cell in the representative chamber at a real GaN growth speed (1 µm per hour). The model follows atoms from the liquid surface, through the cup, across the chamber and onto the spinning wafer.

**Unevenness grows as the cup empties.** At the standard 46° port, unevenness grows from about 2 % with a fresh charge to 8–10 % when the cup is nearly empty. The deeper the liquid, the narrower the spray, so the wafer edge gets less.

![Left: Ga arrival across the wafer radius for three fill levels. Right: range/mean rises from about 2 % to 8–10 % as the melt recedes](docs/figures/ga_fill.png)

*Right panel: each line uses a different assumed gallium atom size. The dashed line is the no-collision model.*

**The biggest unknown: the gallium atom's size.** No published source gives the collision size of a gallium atom, so we try a range (2.5, 5.68 and 8 Å). It hardly matters for a fresh charge. For a nearly empty cup, bigger atoms mean more collisions, which widen the spray again. There the answer ranges from about 8 % to 10 %, or about 7.7–8.6 % within the now-plausible sizes of about 6–8 Å (see below).

A new estimate narrows that range from physics rather than guesswork. Atoms attract each other at a distance with a strength that has been calculated for every element. Scaling from noble gases, whose collision sizes are well measured, gives about 4 Å for gallium if that attraction were all there is. The same method says bismuth should be about 4 Å, but the 1991 experiment needs 8–10 Å. Metal atoms bond as well as attract, which makes them "look" bigger. Carrying bismuth's extra factor over to gallium gives about 9.6 Å. These are reasoned estimates, not measured limits: 4, 6 and 9.6 Å are plausible values to try, and 2.5 Å is not ruled out. The paired-atom test showed that part of bismuth's extra size came from its pairs. With that removed, the same reasoning gives about 6–8 Å for gallium, which the existing runs at 5.68 and 8 Å already cover, so they do not need to be redone. Gallium vapour, unlike bismuth, is almost entirely single atoms (paired atoms under 0.1 %, checked against a 1998 measurement), so the model's single-atom picture holds.

**Choosing the port angle.** Tilting the cell more steeply compensates for the narrowing spray. The best angle depends on the fill: about 48° for a fresh 40 mm charge, about 54° at 70 mm and about 58° at 120 mm. At its best angle each fill reaches roughly 1–2 %.

![Range/mean against port angle for three fill levels, with the spill limit for a fresh charge above 48.2°](docs/figures/ga_angle.png)

*Solid lines: collision model (atom size 8 Å) with statistical error. Dotted: no collisions. Red shading: angles where a fresh charge would spill. Grey bars at 54° and 58°: the spread of repeat runs with finer settings. Grey band: values not yet pinned down by those repeats.*

What the angle study means:
- **No fixed angle is best for a whole campaign.** A fresh charge would spill beyond 48.2°, while an emptying cup prefers 54–58°. Choosing a port angle is a real design trade-off.
- **The best values are only known roughly.** We repeated the two best cases with a different random seed, a halved time step, a finer grid and twice the simulated atoms. The results moved between 0.7 and 1.4 % at 70 mm, and between 0.9 and 1.9 % at 120 mm. So the best achievable is about 1 % for a half-empty cup and about 1.5–2 % for a nearly empty one. Pinning it down further would need much longer runs.

**Keeping the gallium supply constant.** As the cup empties, less vapour escapes, so the oven must run hotter to keep the same gallium supply. The no-collision model puts the increase at about 8.5 °C between 40 and 120 mm. With collisions, the supply actually delivered at those temperatures is 4 % below to 9 % above the target. So the twin now adjusts the temperature from the collision simulation itself, repeating until the supply at the wafer centre is within ±1.5 % of the target. All twelve cases reached that, most after a single adjustment. Keeping the supply constant from a fresh to a nearly empty cup needs about 12–13 °C more at the 46° port, more than the 8.5 °C the simple model suggests, and about 21 °C if the port angle follows the best angle. The unevenness results above hold at constant supply: about 2 % fresh to 8.3 % nearly empty at 46°, and about 1 % to 2 % at the best angles.

What is held constant is the gallium arriving at the centre of the wafer, not the growth rate. The growth rate also depends on the nitrogen supply and on how much gallium actually sticks, which the twin does not model yet. The runs also record the average gallium supply over the whole wafer, since the edge receives less than the centre.

**The chamber is not empty during growth.** The nitrogen source lets gas into the chamber, and at typical growth pressures 10–20 % of the gallium beam hits a gas molecule on its way to the wafer. Atoms that collide leave the beam, and because the paths to the near and far side of the wafer differ in length, the loss is not even. The beam model now includes this loss (with no gas it gives exactly the old answer). Where the knocked-off atoms end up is not modelled. Section 8 shows how much it matters for whole layouts: little up to about 2 × 10⁻³ Pa, a lot at ten times that.

**What these results are, and are not.** They compare design options on a representative chamber, with a known uncertainty and one clearly bracketed unknown (the atom size). They are not a thickness prediction for a specific machine. In the usual gallium-rich GaN recipe, thickness follows the nitrogen supply (next section).

## 5. Nitrogen

In the usual gallium-rich recipe, a thin excess film of gallium sits on the surface, and the crystal grows as fast as nitrogen arrives. So the **thickness map follows the nitrogen map**. What matters for the gallium cell is the **gallium-to-nitrogen ratio** across the wafer, which must stay gallium-rich everywhere.

**The nitrogen source.** The plasma source releases its gas through a plate with many small holes. Our model of that plate shows:
- **Hole shape sets the spread.** How the nitrogen spreads over the wafer depends mostly on the holes' shape (how deep compared with how wide). The plate's overall size barely matters.
- **Real plates look much less even than the gallium beam.** Two published plates give real hole counts and sizes (about 700 to 4000 holes, 0.2–0.34 mm wide), but not the plate thickness, so we tried 0.5–2 mm. The model assumes the gas in the holes is thin enough that molecules hit only the walls, not each other. At low gas flow (0.5 sccm) that holds for every plate except the 700-hole plate at 2 mm thick, which is borderline. At a typical 3 sccm it holds only for the thinner many-hole plates: the gas is too dense in the 700-hole plate, and partly too dense in 2 mm plates, so the model is less reliable for those. Straight holes that are several times longer than they are wide send the nitrogen out in a narrow jet. Aimed at the wafer centre from 350 mm, the model then gives nitrogen maps with range/mean of 20 % to over 100 %, against 1–10 % for gallium.
- **Aiming off-centre evens it out, at a price.** If the source is pointed not at the wafer centre but near its edge, the spinning wafer sweeps the narrow jet over a ring. In the model, with port angles up to 65°, this brings a thin plate and holes up to about 12 times longer than their radius (the 0.34 mm holes in plates up to 2 mm thick) to about 1 % range/mean or below, even if the plate emits unevenly across its face. The deepest published case, the 0.2 mm holes in a 2 mm plate (about 20 times longer than their radius), only reaches 3.5 %. It improves as the port gets steeper, but steeper ports have not been simulated. The catch is that the narrower the jet, the more precisely the source must point. Because the source looks at the wafer at a slant, a pointing error of 0.8° moves the aim point 5–8 mm, not the 5 mm a head-on view would suggest. Within ±0.8° the worst case is about 0.3 % for a thin plate, 1.6–1.8 % for the shallowest holes, 3–3.7 % for medium holes and 7.5–9 % for 2 mm plates (8 % for the deepest R13 case at its best angle). Within ±1.6°, it is up to 3 % for the shallowest holes and 12–17 % for the 2 mm plates. Shallow holes are the practical choice: a perfectly thin plate is the ideal, but no real plate is infinitely thin, and it also sends more of its nitrogen past the wafer. The source mounting needs a way to measure and adjust its aim.

![Nitrogen unevenness against where the source is aimed, for a thin plate and three hole depths: very uneven when aimed at the wafer centre, a narrow best region near the wafer edge](docs/figures/n_aim.png)

*Model results for four plates. The points are 15 mm apart, so the best spots lie between them; finer steps reach about 1 % or below for these four plates (not for the deeper R13 2 mm plate, see text). The deeper the holes, the narrower the dip, and the more precisely the source has to point.*

- **Still the least certain input.** None of this is tested against a measured nitrogen map, and the real plate's thickness, hole pattern and hole angles are unknown. A thickness map grown with nitrogen as the limiting supply on the real machine will be the direct test.

## 6. How the layer grows

The first growth model combines the gallium map, the nitrogen map and the wafer temperature at each point on the wafer. It uses only constants measured in published experiments (R20, G01, G02) and keeps exact account of every gallium atom: built into the crystal, evaporated again, or left on the surface as droplets.

![Left: the usable range of gallium-to-nitrogen supply ratio between rough growth (below 1) and droplets (above each line) widens with temperature. Right: the thickness change from a 10 °C hotter wafer edge rises steeply with temperature](docs/figures/growth_window.png)

*Left: the usable window lies between rough growth (ratio below 1) and gallium droplets (above the line). The three lines are three published measurements of where droplets start. Right: how much a wafer edge 10 °C hotter than the centre changes the layer thickness there.*

What it shows:
- **Inside the window, the gallium map does not affect thickness.** The layer grows as fast as nitrogen arrives, minus a small loss from the crystal slowly evaporating at growth temperature. So thickness follows the nitrogen map and the temperature map.
- **The gallium map decides whether the whole wafer stays in the window.** At a cooler growth temperature (about 700 °C) the window is narrow. A nearly empty gallium cup at the standard 46° port can push part of the wafer out of it, while the best angles keep it in.
- **Temperature is a trade-off.** A hotter wafer widens the window, but the evaporation loss rises steeply with temperature. A 10 °C difference between wafer centre and edge then changes thickness by about 0.3 % at 700 °C, 1–1.6 % at 740 °C and 4.5–6.4 % at 780 °C (range/mean). So the chosen growth temperature sets how even the heater must be.
- **Uncertain edges of the window.** Three published measurements of where droplets start disagree by up to a factor of four, partly because each lab measures temperature differently. The real machine's own measurements will settle it.

**Putting the pieces together.** Chaining the gallium, nitrogen, heater and growth models gives a predicted thickness map for a whole machine layout. Changing one part at a time shows which change does the work:
- With a deep-holed nitrogen plate aimed at the wafer centre, the layer varies by about ±27 %. Aiming it off-centre brings this to about ±0.5–1.5 %; nothing else helps until that is fixed.
- With a thin nitrogen plate, a simple layout already gives about ±0.5 % at 700 °C and ±1.4 % at 740 °C. A better heater brings 740 °C down to about ±0.5 %, and all improvements together to about ±0.2 %.
- Improvements can interact. With the centre-aimed deep-holed plate, a more even heater made the layer slightly *less* even, because the cooler edge had been partly making up for the nitrogen shortfall there.

These are predictions for a representative chamber, not measurements. Section 8 adds pointing errors, heater imperfections and the other uncertainties all at once. A provisional summary of what the results suggest for the machine design, and what they cannot yet say, is in [docs/SOURCE_DESIGN_PROVISIONAL.md](docs/SOURCE_DESIGN_PROVISIONAL.md).

## 7. Wafer temperature

The wafer heater is modelled with **Elmer**, a free heat-flow simulator. It passes two exact tests: heat conduction, and heat radiation between two hot plates (within 0.25 °C).

The first published heater experiment we examined (R03) turned out to be a weak test. Its wafers sit off-centre on a large plate, and its measured temperature differences (2–6 °C) are close to its own ±2 °C measurement error. Its data are saved, and better heater experiments are still being looked for.

**A first 200 mm heater model.** A simplified model of a heater under a spinning wafer, whose rim rests on a holder ledge, is checked against an exact radiation answer (within 0.03 °C). Its dimensions are typical values, not a real machine's. It shows:
- **One heating zone is far from enough.** The wafer edge runs about 90 °C colder than the centre. Two zones bring this to about 35 °C and three to about 17 °C.
- **How the heat is spread matters more than the number of zones.** A heater whose heating density varies smoothly with radius gets to about 2–10 °C.
- **The wafer's edge support matters as much as the heater.** How far the wafer overlaps its holder, and how well they touch, changes the result several-fold.
- **A plate that spreads the heat does not help.** Putting a heat-spreading plate between heater and wafer made the wafer less even in the model, because the wafer edge needs extra heat to make up for what it loses, and the plate smooths that away.
- **Control precision matters.** A 5 % error in one zone's power adds 6–10 °C. So either the zone powers must be held very precisely, or the wafer temperature must be measured at more than one radius.
- **The wafer has to be measured.** The silicon wafer's own heat emission is only known to ±10 %, and that alone shifts an unmeasured wafer by about 18 °C. In the model, one temperature sensor fixes the average but not the centre-to-edge shape; one sensor per heater zone gets close to the best shape the zones allow.

- **The heater element has a temperature limit.** The best smooth-density design pushes the outer heating ring to about 1380 °C to keep the wafer edge warm. The proposal's heater is rated 1200 °C, though it does not say whether that applies to the element or the wafer. Held to 1200 °C at the element, the best design's spread grows from about 2 °C to 3 °C, and it needs some spare temperature: a wafer that emits 10 % more heat than expected loses more from its growing face, and would need the element about 22 °C above the limit (section 8).

At 740 °C, every 1 °C of temperature spread adds roughly 0.1–0.16 % to the thickness spread (section 6). So these numbers feed directly into the heater and sensor choices for the real machine.

## 8. Choosing a layout

The studies above each looked at one part. To choose a machine layout, the twin now compares **complete layouts**: where every source sits, how the nitrogen source is aimed, and which heater. It checks first that the parts fit. Then it works out what the nitrogen supply, the pumps and the heater can actually deliver, and how each layout performs there when many things are slightly off at once.

**Do the parts fit?** Each source is modelled as a solid body with its mounting flange, plus a shutter blade that swings aside. The model checks the main collisions as the shutters open, and that no part blocks another source's beam. With typical dimensions (the real drawings don't exist yet), it found no clash. This is a screening, not a sign-off: eleven sources on one ring leave only about 9 mm between neighbours, and some combinations of parts and shutter movements are not checked yet. Two practical points came out of this:
- To aim the nitrogen source off-centre, its port has to be built pointing at the aim point. An adjustable mount can only trim the aim by a degree or two.
- How the source tilts matters. If it pivots at its mounting flange, about 30 cm behind the plate, a small tilt also shifts the plate sideways. That doubles how far the aim point moves: 8–16 mm per 0.8°, rather than 4–8 mm.

**How fast can a 200 mm wafer grow?** The growth rate is set by the active nitrogen reaching the wafer, and three things limit it:
- **The gas itself.** One standard cubic centimetre per minute (sccm) of nitrogen gas contains about 9 × 10¹⁷ nitrogen atoms per second. Only some fraction of them leaves the source as active atoms. Nobody has published that fraction for this kind of source, so the twin treats it as an unknown and asks how large it must be.
- **The pumps.** More gas means a higher chamber pressure, and the leftover gas knocks atoms out of both beams on their way to the wafer. Past a certain flow, adding gas lowers the growth rate.
- **The source's holes.** At high flow, the gas behind the source plate becomes dense enough that the holes no longer spray atoms in the simple way the model assumes. For the plate assumed here, that happens above about 6 sccm.

![Growth rate the nitrogen supply can reach, and thickness spread at each rate, for layouts B and C](docs/figures/layouts.png)

*Left: growth rate reached within a 10 sccm gas limit, against the fraction of the gas's atoms that leave the source active, for good (2 m³/s, solid) and poor (0.5 m³/s, dashed) pumping. Right: thickness spread at three growth rates. Dot = everything as designed; bar top = worst combination with the source aimed within 0.8°. Representative chamber, 740 °C.*

What this shows:
- **1 µm/h is only just possible.** With good pumping, layout B needs at least 60 % of the gas's atoms to leave the source active, and layout C needs 82 %. With poor pumping, neither layout reaches 1 µm/h at all. If only about a third of the atoms leave active, the ceiling is about 0.5 µm/h (B) and 0.35 µm/h (C).
- **Layout C needs about 50 % more nitrogen than B.** At 1 µm/h its gas flow is already above the point where the source's holes stop behaving simply, so its results there are outside what the model can vouch for.

**Many things off at once.** At each reachable growth rate the twin evaluates about 18,000 combinations of:
- the nitrogen source tilted up to 0.8° (or 1.6°) in any direction, about either pivot point;
- the gallium cup fresh to nearly empty, with both plausible atom sizes;
- heater imperfections (wafer emission ±10 %, poor or good edge contact, one zone 2 % off), one at a time;
- the holder's rim height (1–3 mm);
- the three published droplet limits.

As on a real machine, the gallium oven is set once and then held at a fixed output, and the heater is never allowed above its temperature limit.

What the comparison shows (layouts are defined in [docs/LAYOUT_COMPARISON.md](docs/LAYOUT_COMPARISON.md)):
- **Aiming nitrogen at the wafer centre fails**: about ±11 % thickness, whatever else is done.
- **At 1 µm/h, layout B is ahead.** B gives about ±1.1 % as designed and ±2.4 % in the worst combination; C gives ±0.9 % and ±2.8 %. B is the better of the two in 70 % of the combinations.
- **At slower growth the two are level.** C is better as designed, and their worst cases are about the same. At 740 °C, slower growth does not make the wafer more even. A fixed amount of material evaporates from the surface whatever the growth rate, so a slower layer is more affected by the temperature pattern.
- **The heater needs spare temperature.** A wafer that emits 10 % more heat than expected loses more from its growing face. To stay at temperature it would need the heater element about 22 °C above its limit; held at the limit, the wafer runs about 15 °C cold. With the gallium supply fixed, gallium then piles up into droplets in most of those cases. That takes about a tenth of all combinations out of the smooth-growth window.
- **Whether either layout "passes" is not yet decided.** The project has not agreed a uniformity target or a minimum growth rate. At 1 µm/h, a ±2 % target would be met in about 89 % (B) and 80 % (C) of the combinations, and a ±1 % target in about a third.

[docs/LAYOUT_COMPARISON.md](docs/LAYOUT_COMPARISON.md) lists, for each layout, the conditions under which it fails, the hardware information that would settle each one, and the decisions the project still has to make.

## 9. How results are made trustworthy

- **Statistical error bars.** Collision simulations are statistical, like an opinion poll, so every result carries an error estimate from splitting the run into independent pieces. Important cases are rerun with another random seed, smaller time steps and finer grids.
- **A checked unevenness formula.** Turning a noisy simulated spray into one range/mean number needs a smoothing formula. Ours was tested against exact answers: it is off by at most 0.2 points, and its random scatter is 0.3–0.5 points.
- **Every result can be rerun.** Each run gets its own folder and records its full settings before it starts. Saved results carry a fingerprint of the exact code that produced them, and batch files spell out every setting. A generated table next to the saved results shows which version of the code made each one, what has changed since, and whether that change could alter its numbers.
- **Automatic tests.** About 190 automatic tests check the code; all pass. Every number is traced to a published source, and unknown or unexplained results are labelled rather than hidden.
- **The laptop stays safe.** Simulation output is read one snapshot at a time. A new job starts only when enough memory is free, both in Windows and in the Linux environment where the collision simulator runs. When the laptop is shared with other work, jobs also wait for a free processor core, and an overnight queue stops starting new jobs at a set hour.

## 10. Where things stand

| Part | Status |
|---|---|
| Gallium beam model | Tested against a real experiment: shape within 1–2 %; with paired bismuth atoms included, rate within −6.5 to +5 % |
| Gallium on the 200 mm wafer | Fill and port-angle study done at constant gallium supply, with numerical checks at the best angles |
| Nitrogen source | Two published plates modelled: a narrow jet unless aimed off-centre, then about 1 % or below for plates up to 2 mm with 0.34 mm holes (3.5 % for the deepest R13 case) but sensitive to pointing; plate thickness and pattern unknown |
| Wafer heater | First 200 mm model: zone count, edge support, control precision and the element temperature limit compared; not yet checked against any measured heater |
| Surface growth chemistry | First model from published constants: growth window and thickness from the gallium, nitrogen and temperature maps; not yet tested against a wafer |
| Complete layouts | No clash found with typical part sizes (screening only). Layouts B and C compared at growth rates the nitrogen supply, pumps and heater can deliver, under combined uncertainty. B is the working candidate and C the alternative; 1 µm/h needs most of the source's gas to leave as active nitrogen (section 8) |
| The real machine | Needs its drawings and first measurements, which will turn the representative twin into its own twin |

**Next.**
1. With the hardware team: the nitrogen source's active output versus gas flow and power, the source plate drawing, the effective pumping speed for nitrogen, the heater element's real temperature rating, and the mount, holder and chamber drawings. The first three decide whether 1 µm/h is reachable at all; section 7 of [docs/LAYOUT_COMPARISON.md](docs/LAYOUT_COMPARISON.md) says what each one settles.
2. With the project: agree the uniformity target, the minimum growth rate and the growth temperature. Until then the comparison reports trade-offs, not a pass or fail.
3. Agree the commissioning measurements, keeping the ones used to tune the model separate from the ones used to test it: growth rate versus source flow and power, growth pressures, temperature maps, thickness maps grown with nitrogen or gallium as the limiting supply, and repeated reference runs.
4. Then re-optimize the nitrogen aim at the pressure the real flow gives, and include where the gas-scattered atoms land.

Searches for steeper nitrogen ports, more gallium atom sizes, adjustable gallium ovens and further heater variants are on hold until the comparison shows that they could change a decision.

The sources and calculations from the latest search are in the [physics-data note](ref/notes/PHYSICS_DATA_SEARCH_2026-09-30.md).

**Side idea (optional, not on the main path).** Could an adjustable gallium oven keep the layer even as the cup empties? The best angle steepens from about 48° to 58° as the cup empties, and a full cup only spills at steep angles, so "start shallow, tilt steeper later" never spills. On hold until the layout comparison (section 8) shows it could change a decision; the options would be:
- an oven that can tilt at its mounting;
- two gallium ovens at different angles, with their output share changing over time;
- a better-shaped cup.

Tilting a hot oven of liquid gallium has real engineering risks (sealing, spitting droplets, recalibration), and the comparison will list them. Details are in the [reference-chamber note](ref/notes/REFERENCE_CHAMBER.md#exploratory-non-essential).

## 11. Glossary

| Term | Meaning |
|---|---|
| Å (ångström) | 0.1 nanometre, about the size of an atom |
| Beam | The spray of vapour leaving a source |
| Crucible | The cup inside an effusion cell that holds the liquid metal |
| DSMC | Direct Simulation Monte Carlo: simulates a gas by following many sample atoms and letting them collide at random with the right probabilities |
| Effusion cell | The oven that evaporates the metal |
| Free-molecular | Gas so thin that atoms never collide with each other, only with walls |
| Growth window | The range of gallium-to-nitrogen supply in which the layer grows smoothly: below it growth is rough, above it gallium droplets form |
| Gallium-rich growth | A recipe with slightly more gallium than nitrogen, so thickness follows the nitrogen supply |
| MBE | Molecular beam epitaxy: growing crystals from beams of atoms in vacuum |
| Range/mean | (thickest − thinnest) ÷ average: our measure of unevenness |
| Recess | How far the liquid surface sits below the crucible's mouth |
| Representative chamber | A typical machine built from published dimensions, standing in until the real machine's drawings exist |
| R03, R07, … | Reference numbers of published sources in the [reference library](ref/) |

Figures are drawn by `scripts/make_readme_figures.py` from the saved run records.
