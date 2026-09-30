# GaN/AlN MBE digital twin

Last updated: 30 September 2026. This page is the plain-language overview. The technical details (code, solvers, commands, status by subsystem) are in the [developer guide](docs/DEVELOPER.md), and the command behind every quoted number is in [docs/REPRODUCE.md](docs/REPRODUCE.md).

## What the project is trying to build

**The machine.** Molecular beam epitaxy (MBE) grows extremely thin crystal layers, here gallium nitride (GaN) and aluminium nitride (AlN), the materials in LEDs and fast power transistors. Inside a vacuum chamber, small ovens called effusion cells heat liquid gallium or aluminium until it evaporates. The vapour flies across the chamber and lands on a hot, spinning 200 mm (8-inch) silicon wafer. There it combines with nitrogen from a plasma source and builds up a crystal layer, atom by atom.

**The goal.** We're building a digital twin: a computer model that predicts what the real machine will do. Examples are how evenly the layer grows across the wafer, and how hot each part of the wafer gets. With a trustworthy twin you can try source positions, heater designs and settings on a laptop instead of spending weeks and expensive wafers on the real machine.

**The catch.** The actual machine isn't built yet, and no manufacturer publishes full drawings. So we model a representative chamber, a typical 200 mm GaN machine of the RIBER / Veeco class. Each piece of physics is checked against a published experiment where someone measured the real thing. A model that reproduces those measurements can be trusted for design comparisons. Exact predictions for the real machine must wait for its own drawings and measurements.

## What has been done

**1. Planning and a reference library.** Written plans cover what the twin must do, how accurate it must be, and how it will be tested. The reference library holds about 30 papers and data sheets, each tracked and checked by an automatic audit script.

**2. The "beam" model: how evaporated metal travels to the wafer.**
- Basic version: it treats each oven as a simple spray pattern and computes how much metal lands where on a spinning wafer.
- Better version: the metal really sits at the bottom of a deep cup (the crucible), and the cup's walls shape the spray. The crucible model follows millions of virtual atoms bouncing off the walls. It was checked against an exact mathematical answer.
- Test against real measurements: a 1991 experiment (R07) measured the spray pattern from such a cup. Our model matched it well when the cup was nearly full, and captured how the pattern narrows as the metal is used up. A simple spray model can't do that.

**3. The atom-collision problem.** The model assumed atoms inside the cup never bump into each other. That's only true when the oven is cool and the metal vapour thin. At realistic GaN growth speeds, the gallium vapour is dense enough that atoms do collide, and that changes the spray. We use SPARTA, a free research program that simulates gas collisions (it runs in the Linux environment on the laptop). With collisions switched off, it reproduces our own model to 1–2 %.

**4. Two outside reviews (29 and 30 September).** A reviewer went through the code and results twice. The verdict both times: good progress, but some conclusions claimed more than the evidence showed. Every point raised was valid and has been fixed or is being fixed:
- Repeatability: every run now gets its own fresh folder and writes down its exact settings before it starts. Batch files spell out every setting, so changing a default later cannot silently change an old result. A batch that fails now says so loudly instead of looking finished.
- Physics we got wrong: in a tilted oven, liquid gallium stays level, like water in a tilted glass. With a level surface, a nearly full cup would spill at the usual 46 degree port angle. So the most optimistic case in our first study (0.5 % unevenness) cannot happen.
- A measuring-tape error: the formula we used to turn the simulated spray into an "unevenness" number could be off by more than 1 percentage point. We tested several formulas against exact answers and switched to one that is accurate to about 0.2 points. All gallium results were recalculated.
- Overclaiming: numbers that turned out weaker than they looked were corrected in the notes rather than quietly kept.

**5. How sure are we? (the uncertainty study).** A collision simulation is statistical, like an opinion poll, so each answer carries random noise. We ran the same 1991 test cases many times with different random seeds, smaller time steps and finer grids.
- At our original settings the noise was as big as the effect we were measuring, so the first "matches within 1–2 %" was partly luck.
- With 5 times more simulated atoms, the collision model matches the 1991 spray shapes within about 1–2 %, against 4–20 % for the no-collision model.
- The one tuned number, the effective size of a bismuth atom in collisions, is pinned to a range of 8–10 Å.
- Open puzzle: the model's absolute deposition rate is 7–15 % too low in every case. That's not simulation noise, and the cause is still unknown.

**6. Gallium on our 200 mm wafer, with collisions.** We simulated a gallium oven at real GaN growth conditions (1 µm/h) on the representative chamber. Numbers below use the corrected unevenness formula.
- As the cup empties, unevenness at a 46 degree port grows from about 2 % (nearly full) to about 8–10 % (nearly empty). Without collisions it would be about 10 %. Collisions only make a clear difference when the cup is nearly empty.
- The biggest remaining unknown is the "size" of a gallium atom in collisions, which no source gives. We try a range of sizes; it matters most for a nearly empty cup.
- Best port angle: steeper ports even out an emptying cup. At the best angle for each fill level, unevenness drops to about 1 % or less (we can't resolve it more finely than that). But a full cup spills above about 48 degrees, so no single fixed port angle is best over a whole campaign. That's a real design trade-off to decide.
- Keeping the growth speed constant as the cup empties needs a hotter oven. Our first estimate (about 8.5 °C) used the simpler no-collision model to set the temperature. The reviewer rightly asked for it to be checked with collisions included; those runs are in progress.
- Still being checked: whether the "about 1 %" at the best angles holds with finer grids, smaller time steps and more atoms. Those runs are in progress too.

**7. Nitrogen (planning started).** In the usual gallium-rich growth recipe, the layer's thickness follows the nitrogen supply, not the gallium supply. What matters for the gallium oven is therefore the gallium-to-nitrogen ratio across the wafer.
- The nitrogen source spreads its gas through a plate with many small holes. How the nitrogen spreads over the wafer depends mostly on the shape of those holes (how deep compared with how wide), and hardly at all on the plate's size.
- Combining the gallium and nitrogen maps changes the picture. Depending on the plate, the ratio across the wafer can be more even than the gallium alone, or the opposite. So we need a drawing of a real nitrogen plate before settling where the gallium oven goes.

**8. Heater and temperature modelling.** Elmer, the free heat-flow simulator, passes two exact tests: heat conduction, and heat radiation between two hot plates (within 0.25 °C). The published heater experiment we planned to copy (R03) turned out to be a weak test. It heats four 6-inch wafers off-centre on a large plate, its measured differences (2–6 °C) are close to its own ±2 °C measurement error, and even its authors' model misplaces the hot spots. We've saved its data but are looking for a better heater case.

**9. Keeping the laptop safe.** On 30 September four post-processing jobs each tried to load about 55 million simulated atoms at once and ran the laptop out of memory, which took VS Code down. The code now reads the data one snapshot at a time (same results, tiny memory). Batches run at most 3 jobs and only start a job when at least 3 GB of memory is free.

**10. Checks built in throughout.** There are about 120 automatic tests; when last run, all passed. Every number is traced to a source, and uncertain or unexplained results are recorded rather than hidden. Each saved result stores a fingerprint of the exact code that produced it.

## What's still missing

- **Beam model:** finish the checks at the best angles and the constant-growth-speed runs; a sourced value for the gallium atom's collision size; an explanation for the 7–15 % rate gap. After that, an oven cup shape that keeps the spray steadier as it empties.
- **Nitrogen:** a real (or representative) drawing of the nitrogen source's hole plate.
- **Heater:** a better published test case than R03, then the 200 mm heater model.
- **Growth chemistry:** how gallium, aluminium and nitrogen actually form the crystal at the surface.
- **The real machine:** its drawings and first measurements. These will eventually turn this from a representative twin into its own twin.

## In one sentence

Two outside reviews made the project more honest and repeatable. The collision model demonstrably matches the 1991 measurements with stated uncertainty, and the gallium study shows that no single fixed port angle is best over a whole campaign. The nitrogen source has turned out to be the input that most limits the next design decision.
