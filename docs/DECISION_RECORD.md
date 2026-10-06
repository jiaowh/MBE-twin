# Current design decision record

Status: 2026-10-06, after the [follow-up audit](PROJECT_AUDIT_FOLLOWUP_2026-10-06.md). This page is the one place that states what is currently chosen, on what evidence, under which assumptions, and what would reopen it. It is a provisional design-study baseline for the representative chamber, not a hardware acceptance. Details are in the [layout comparison](LAYOUT_COMPARISON.md) (sections 10-14) and the [research-gap note](../ref/notes/RESEARCH_GAP_SEARCH_2026-10-06.md).

## Provisional choice

| Item | Choice | Main evidence |
|---|---|---|
| Layout | **B-L**: nitrogen source on the 46 deg cell ring, aimed +95 mm past the wafer centre, with the large plate (about 8000 holes of 0.5 mm over a 30 mm radius) | It reaches 1 um/h inside the model's validity at a source conversion of about 0.22 or more (4 m^3/s, 35 sccm). B-p (published plate) needs 0.8-0.9. The one direct measurement of a source found at most 0.4, falling as bulb pressure rises (R41). |
| Aim | +95 mm, a nominal modelling choice | Aim scan with the 95 mm scattered-atom tables transferred to the other aims (section 14); to be trimmed at commissioning. |
| Rate | 1 um/h | Section 8; faster costs temperature, slower is less uniform. |
| Temperature | **720 C nominal** (confirmed by the project owner 2026-10-06); 710 C only with Ga fill tracking and an accepted failure tail (table below) | See below. |
| Required instruments | Ga beam-flux monitor (about 2 %), in-situ growth-rate monitor (about 1 %), emissivity-corrected pyrometry at three radii with three heater zone groups, commissioning re-aim to 0.2 deg (mount repeatable to about 0.05 deg), N-limited thickness maps to 0.1-0.3 % | Sections 11-13; [hardware requests](HARDWARE_REQUESTS.md). |

## Uniformity, admission and failure tail

The worst case quoted in earlier summaries is taken only over the grid states that pass the growth-window gate. The states that fail it (Ga droplets or N-rich growth somewhere on the wafer) have their own, larger thickness spread. All three numbers belong together. Values are half-range/mean over the 200 mm wafer for the realizable controller (rate monitor + BFM, multi-spot heater, 0.2 deg re-aim). They are shares of a chosen grid of conditions, not yields.

| | Worst case, passing states | States passing | Worst case, all valid states | With Ga fill tracking: passing / all valid |
|---|---|---|---|---|
| **B-L, 720 C** | 0.58 % | 99.99 % | 0.64 % | 100 %, 0.58 % |
| B-L, 710 C | 0.53 % | 96.7 % | 2.30 % | 98.1 %, 1.64 % |
| B-p, 720 C (assumes eta = 1) | 0.62 % | 99.96 % | 1.19 % | 100 %, 0.62 % |
| B-p, 710 C (assumes eta = 1) | 0.57 % | 95.0 % | 2.81 % | 96.8 %, 2.19 % |

- At 710 C the passing states are 0.05 point more uniform. But about 3 % of B-L's states (5 % of B-p's) leave the growth window, and their spread reaches 2.3 % (2.8 %). For B-L the failures concentrate at the deepest Ga melt level (120 mm below the crucible lip, a nearly empty charge), where 91-93 % pass (98-100 % at the other levels). Most are N-rich somewhere on the wafer (2.6 % of states) rather than droplets (0.8 %). Fill tracking recovers part of this, and campaign recalibration of the Ga flux is the lever to study next.
- At 720 C nearly every state passes, and the worst valid state is within 0.06 point of the passing-state figure.
- Given that the project ranks uniformity first, 720 C is the robust choice: its worst case over all states is about 3.6x better. 710 C buys 0.05 point on the passing states only, at the price of that tail.
- Table noise on these figures: about +/-0.04 point for B-L and +/-0.09 for B-p (bootstrap of the averaged scattered-atom tables, section 14). Between layouts the passing-state difference, +0.04 +/- 0.10 point, is not resolved. Model and hardware uncertainty are not included.

## Assumptions the choice rests on

- Source conversion (eta) about 0.3 at 4 m^3/s effective pumping. Neither is known for the proposed hardware (hardware requests 1, 3).
- The large plate can be made, fits the source body and keeps the plasma lit down to the needed low flows (request 2).
- Chamber walls absorb nitrogen atoms (gamma = 1). The literature suggests walls without plasma exposure may return most of them. In the one case tested (B-L, two seeds, one shared scattering factor across pointing states), strongly returning walls left the passing-state worst case unchanged but cut the nitrogen needed for 1 um/h from about 19 to 5.6 sccm (section 10).
- Ga calibrated at growth conditions, with the temperature reading that drives the Ga supply reproducible to about 1-2 K.
- Crystal quality at 720 C is acceptable for the intended layers. It is not modelled; plasma GaN near 710 C grows smoothly but filtered dislocations poorly with one published buffer (R39).

## What would reopen the choice

- A supplier demonstrates conversion of 0.8 or more at 10 sccm or less with the published plate: B-p becomes viable without a custom plate.
- Commissioning shows strongly returning walls: a nearly flat N-limited thickness map, or a throttle series that fits a low wall loss. The nitrogen needed then falls about 3x, which can also make B-p viable.
- The large plate cannot be supplied, or does not keep the plasma lit at the needed flows.
- Effective pumping well below 4 m^3/s.
- Material-quality requirements that rule out 710-720 C, or acceptance criteria (uniformity target, minimum rate) that differ from the goals used here.

## Not yet established

Real machine geometry and drawings, calibration data, validation on separate wafers, agreed acceptance criteria, AlN growth kinetics, and wall-return behaviour across pointing states and for B-p. The next modelling work is the campaign simulation: Ga depletion and how often the beam flux must be re-measured.
