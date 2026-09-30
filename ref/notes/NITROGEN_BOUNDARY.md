# Nitrogen boundary and measurement access (planning)

Started 2026-09-29 in response to the Stage A review (recommendation 6). Plasma chemistry is not modelled here. This note defines the nitrogen *boundary* the twin needs, and the commissioning measurements that will pin it down. Evidence already collected: [hardware evidence](HARDWARE_EVIDENCE.md) (H02 RF source sheet, P0 data request), [growth evidence](GROWTH_EVIDENCE.md) (G02, G06, nitrogen source matrix), [representative chamber](REFERENCE_CHAMBER.md) (R10-R12, gap in public 200 mm maps).

## Why it limits the source-layout decision now

The governing objective is a measured reduction in wafer nonuniformity, as defined in [the Phase-1 outcome contract](../../PHASE1_CHAMBER_PLAN.md#11-project-success-and-design-decisions). This nitrogen work supports that objective by connecting source-layout choices to the active-N map and growth regime. A better Ga/N margin is intermediate evidence; thickness improvement must be predicted with the relevant growth physics and checked on independent wafers.

Plasma-assisted GaN is normally grown slightly Ga-rich, in the intermediate regime. Local growth rate is then set by the arriving active-N flux, and excess Ga forms a surface bilayer or droplets. Consequences:

- **Thickness uniformity follows the active-N map, not the Ga map.** Ga delivery only has to keep every point of the wafer inside the Ga-rich window: above N-stoichiometry and below the droplet threshold at the growth temperature.
- **The Ga-source criterion changes.** The Ga study (`scripts/sparta_ga.py`) reports Ga range/mean and centre flux. For Ga-rich growth, the design quantity is the local Ga/N ratio across the wafer, min and max. Its range is the Ga range combined with the N range. A Ga layout with 5 % range can be acceptable under a flat N map but not under an N map that tilts the other way.
- **N-limited and metal-limited regimes decouple the two maps.** A Ga-limited (N-rich) layer maps Ga delivery; a Ga-rich, N-limited layer maps active N. That is the cleanest route to separate spatial boundaries at commissioning (below).
- AlN and AlGaN are grown near stoichiometry or Al-limited, where the Al map sets thickness. Their tolerance must be judged separately.

## Representative boundary model (Stage A/B)

- **Geometry.** A plasma cell with a PBN aperture plate: a pattern of short holes (diameter and plate thickness set the per-hole Clausing transmission), throw and port angle as design variables. H02 (SVTA RF-6.02) gives a typical 10.5-inch throw and "coverage up to 8 inches", but no hole map; the proposal's source is unspecified. Treat hole count, pattern radius and plate thickness as ranges.
- **Transport.** Active N leaving the plate is collisionless at growth pressures (to be checked with the same Knudsen estimate as the Ga cells). Each hole is a short-tube emitter. The existing `crucible.py` / `beam.CrucibleSource` machinery covers this: one tube per hole, summed on the rotating wafer.
- **Unknowns kept as parameters.** Radial output profile across the plate (discharge non-uniformity), wall recombination inside the holes (per-hole transmission of atoms versus N2), ion fraction and energy (a separate species, not in the thickness model), and total active-N output versus power and flow (R10-R12, then the commissioning source matrix).
- **Deliverable.** The wafer-plane active-N map and its sensitivity to hole pattern, plate profile, throw and angle. Combined with the Ga study, it gives the Ga/N ratio range over the wafer for candidate layouts.

## Measurement access at commissioning

Listed in order of how directly each one constrains the boundary. Plan the ports and tools before design freeze.

| Measurement | Constrains | Access needed | Notes |
|---|---|---|---|
| Ga-rich (N-limited) GaN, 200 mm, ex-situ thickness map | Active-N spatial map | Mapping reflectometry or ellipsometry after growth; growth recipe with verified Ga excess everywhere | Verify the Ga-rich condition across the wafer (surface Ga bilayer and no droplets). Otherwise the map mixes regimes |
| Ga-limited (N-rich) GaN, same geometry, ex-situ map | Ga spatial map, independent of N | Same | Held out against the Ga source model; do not reuse for the N fit ([growth evidence](GROWTH_EVIDENCE.md) rule) |
| RHEED growth-regime transitions at wafer centre | Absolute active-N flux at one point versus power and flow | RHEED port with the wafer at growth position | Gives the absolute scale for the N map |
| Optical emission spectroscopy of the plasma | Source state and drift (not absolute flux) | Viewport or fibre port on the source (confirm the selected unit has one) | Track source ageing between maps |
| In-situ laser reflectometry (one or two points) | Growth rate versus time: checks a map is steady and stays in one regime | Normal-incidence port or a pyrometer/reflectometer head | Links ex-situ maps to recipe time |
| BFM at the growth position | Ga beam at one point; checks Ga source temperature-to-flux calibration | Retractable gauge on the manipulator | Flux only; no spatial map |

Request in the P0 data list: aperture-plate drawing and hole map, source mounting angle and throw, OES viewport, and whether the manipulator carries a BFM.

## First sensitivity result (2026-09-29)

`src/mbe_twin/aperture.py` implements the plate. Each hole is a short tube sharing one random walk, weighted by a radial output profile. Tests check it against a single `CrucibleSource` (exact) and against a Lambertian disk for dense thin holes (0.2 %). `scripts/nitrogen_plate.py` scans hole aspect L/r (0, 2, 5), plate radius (10, 20 mm), output profile (uniform, centre- or edge-peaked by 50 %), throw (267, 350 mm) and port angle (0-50 deg), with the plate aimed at the wafer centre. Range/mean on the rotating 200 mm wafer:

| Throw | L/r | 0 deg | 20 deg | 40 deg | 50 deg |
|---|---|---|---|---|---|
| 350 mm | 0 | 15.6-15.7 % | 12.4-12.5 % | 3.7 % | 1.8-1.9 % |
| 350 mm | 2 | 33.8-35.4 % | 30.3-31.9 % | 20.3-21.8 % | 13.8-15.1 % |
| 350 mm | 5 | 67.3-72.6 % | 62.7-67.8 % | 49.6-54.2 % | 40.7-45.1 % |
| 267 mm | 0 | 26.0-26.3 % | 21.2-21.4 % | 7.4-7.5 % | 2.0 % |
| 267 mm | 2 | 50.9-53.6 % | 45.7-48.2 % | 30.6-32.8 % | 20.0-22.0 % |
| 267 mm | 5 | 98.1-106.8 % | 91.6-100.0 % | 72.6-80.3 % | 59.0-65.8 % |

Ranges span plate radius and output profile.

- **The hole aspect ratio dominates.** Plate radius and the output profile across the plate move range/mean by 0-2 points for thin and moderate holes and up to 9 points for the most beamed case; L/r moves it by tens of points. The hole diameter and plate thickness are therefore the most important nitrogen inputs to obtain (P0 request: aperture-plate drawing).
- A free-molecular plate of beaming holes (L/r >= 2) aimed at the wafer centre cannot give a uniform 200 mm N map at these throws. Real large-area plates presumably rely on hole angles, hole-density patterns or off-centre aim, none of which is public. The model can represent tilted holes and density patterns once a drawing exists.
- **Caveat: the holes may not be free-molecular.** RF sources run with a discharge pressure far above chamber pressure, so the gas in the holes can be transitional or viscous, which changes the angular distribution (as collisions did for the Ga cells).

**Hole Knudsen number** (`scripts/nitrogen_knudsen.py`, 2026-09-30). The pressure behind the plate follows from flow over plate conductance, p = Q / C, so it is estimated rather than assumed. Brackets: 0.5-3 sccm, 50-500 holes, hole radius 0.1-0.3 mm, L/r 2-5, gas at 300-600 K, and the N2 diameter 3.7 A x/÷ 1.3 (a textbook value, not sourced here).

- The implied source pressure is 0.1-140 Pa.
- Plates with many holes (500), or holes of 0.3 mm radius at low flow, give Kn = lambda / (2r) of 3-250. That is free-molecular, and the aperture model above is self-consistent.
- Few small holes (50 x 0.1 mm) at 3 sccm give Kn 0.2-1.4. That is transitional, and the free-molecular hole beaming above would then be wrong in the same way the free-molecular Ga cell was.
- Which regime applies depends on the plate's total open area, so the aperture drawing decides it. For a transitional plate, the DSMC route used for the Ga cells (SPARTA, one hole or a hole cluster) is available.

## Ga/N ratio across the wafer (recomputed 2026-09-30 with the corrected estimator)

`scripts/ga_n_ratio.py` divides the fitted Ga DSMC profiles (46 deg, 350 mm, level melt; [representative chamber](REFERENCE_CHAMBER.md)) by two representative N maps (plate at 40 deg, 350 mm). Both are rotation-averaged. The Ga profiles now come from the annulus-fit estimator (order 4). The first version of this table used the earlier point-quartic fit, which overstated deep-fill Ga non-uniformity by up to about 1 point; that version is superseded. Spread of the local Ga/N ratio, as range/mean over 200 mm, across the Ga diameter bracket (2.5-8 A) and the collisionless case:

| Ga fill | Ga alone | / thin-plate N (N edge/centre 0.96) | / beaming-hole N, L/r 2 (edge/centre 0.82) |
|---|---|---|---|
| 40 mm | 2.0-2.4 % | 1.8-2.2 % | 17.0-17.5 % |
| 70 mm | 5.0-6.0 % | 1.7-2.6 % | 13.1-14.1 % |
| 120 mm | 7.7-10.3 % | 4.4-6.9 % | 9.0-11.6 % |

Each Ga value carries the estimator's scatter of about 0.2-0.6 points ([representative chamber](REFERENCE_CHAMBER.md)), which propagates into the ratios.

- Ga uniformity alone is the wrong criterion. With a thin plate, the edge-low Ga and N maps partly cancel. At 70 and 120 mm the ratio is clearly more uniform than Ga alone; at 40 mm the two are about the same. With beaming holes, the ratio is most non-uniform for a fresh charge and improves as the melt recedes, the opposite of the Ga-alone trend.
- The Ga/N margin a layout must hold is therefore set jointly by the Ga fill range and the N plate. The N plate is the less constrained of the two (hole geometry unknown; regime depends on open area). The nitrogen boundary is now the limiting input for the source-layout decision, as the review anticipated.

## Published plates: flow regime and geometry (2026-09-30)

`scripts/nitrogen_plate_scenarios.py` (record `results/nitrogen_plate_scenarios/manifest.json`) takes the published hole sets and brackets what is not published. The plates are R13's original 712 and modified 4000 holes of 0.2032 mm, and R30's UNI-Bulb plate of about 2000 x 0.343 mm ([physics-data note](PHYSICS_DATA_SEARCH_2026-09-30.md), section 4). The brackets are thickness 0.5 / 1 / 2 mm, active radius 12.5 / 20 mm, 0.5 / 3 / 10 sccm N2, and 300 / 600 K gas. The first sensitivity study above stopped at L/r = 5; these plates give L/r = 2.9-19.7.

- **Flow regime** (hole Kn = lambda / 2r, with p behind the plate from the free-molecular conductance; range over the N2-diameter bracket):

  | Plate | 0.5 sccm | 3 sccm | 10 sccm |
  |---|---|---|---|
  | R13 original (712 x 0.203 mm) | 6-74 | 1.1-12 | 0.3-3.7 |
  | R13 modified (4000 x 0.203 mm) | 36-415 | 6-69 | 1.8-21 |
  | R30 (2000 x 0.343 mm) | 46-483 | 7.7-80 | 2.3-24 |

  - For the many-hole plates at the usual 0.5-3 sccm, Kn is mostly above 10, so the free-molecular hole model is roughly self-consistent (the 2 mm / 300 K / large-diameter corner reaches 6-8).
  - At 10 sccm, or with the 712-hole plate at 3 sccm and above, the holes are transitional. Free-molecular beaming is not reliable there; a hole-scale DSMC would be needed. This matches R13's stated reason for the 4000-hole redesign: lower pressure behind the plate at high flow.
- **Geometry.** On a hexagonal pattern, all six plate and radius combinations leave webs of 0.17-1.2 mm (open area 1.8-38 %), so none is excluded as impossible to machine. The hole pattern and active radius remain unknown.
- **Wafer maps** (free-molecular, valid where Kn is at least about 10). Range/mean over 200 mm at 350 mm throw, with the plate aimed at the wafer centre, uniform hole output and straight holes. The map depends on L/r and the plate extent, not on hole count or size. Ranges cover the active radii of 12.5 and 20 mm.

  | L/r (plate, thickness) | 0 deg | 30 deg | 50 deg |
  |---|---|---|---|
  | 2.9 (R30, 0.5 mm) | 43-45 % | 34-36 % | 21-22 % |
  | 4.9 (R13, 0.5 mm) | 67-70 % | 56-60 % | 40-43 % |
  | 5.8 (R30, 1 mm) | 79-83 % | 68-72 % | 50-53 % |
  | 9.8 (R13, 1 mm) | 129-139 % | 115-124 % | 91-99 % |
  | 11.7 (R30, 2 mm) | 142-154 % | 127-138 % | 101-112 % |
  | 19.7 (R13, 2 mm) | 218-251 % | 198-228 % | 163-190 % |

  - Hole sampling is converged: halving the hole pitch (61 to about 220 sampled holes) changes the deepest case by at most 0.25 points.
  - Every published hole set gives an N map far less uniform than the Ga map (1-10 %). Even the shallowest case (R30 in 0.5 mm, L/r 2.9) is 21-45 %. A thin cosine plate (L/r 0) is 16 % at 0 deg (first study).
  - Taken literally, this says a straight-hole plate aimed at the wafer centre from 350 mm cannot give a uniform N-limited thickness on 200 mm. Either production sources differ from this picture, or the layout compensates. Candidates, none yet modelled: aiming the plate off-centre (`aim_offset` exists in `aperture.py`), tilted or diverging holes, larger throw, hole-wall recombination and collisions reshaping the beam, and the source's real active radius.
  - This is the largest open question for the source layout. It raises the priority of the N map over any further Ga refinement. It also raises the value of a measured N-limited thickness map at commissioning, which is the only direct test.
- **Not addressed:** the total active-N output (R10-R12, R18, commissioning), hole-wall recombination (grows with L/r) and the ion fraction. Hole counts alone do not supply the spatial pattern or the output.

## Can the layout even out a beaming plate? (2026-10-01)

`scripts/nitrogen_aim_study.py` (records `results/nitrogen_aim_study/` and `results/nitrogen_aim_study_ext/`). Free-molecular straight holes, a 20 mm active radius, 350 mm throw and uniform hole output. The aim point is moved along the source's azimuth (positive towards the source side) and the port angle is varied. A narrow beam aimed off-centre on a rotating wafer spreads over an annulus. The first grid (offsets -80 to 80 mm, 0-45 deg) put the beaming plates' optima on its edge, so it was extended (offsets 60-150 mm, 40-65 deg).

| L/r (R30 hole in) | Aimed at centre, same angle | Best found | Where | Worst within +/-10 mm of that aim |
|---|---|---|---|---|
| 0 (thin plate) | 1.0 % (45 deg) | 0.3 % | +55 mm, 45 deg | 0.4 % |
| 2.9 (0.5 mm plate) | 9 % (65 deg) | 0.3 % | +75 mm, 65 deg | 2.1 % |
| 5.8 (1 mm) | 33 % (65 deg) | 0.9 % | +105 mm, 65 deg | 4.4 % |
| 11.7 (2 mm) | 75 % (65 deg) | 0.9 % | +100 mm, 65 deg | 10.4 % |

- **Yes, in the model.** Aiming the plate near the wafer edge brings every published hole set below 1 % range/mean. The optimum is a valley in (aim, angle): for L/r 2.9, 45 deg at +105 mm also gives 1.0 %.
- **The price is pointing tolerance.** Deeper holes give a narrower beam, and the map becomes very sensitive to the aim point. At 350 mm, 10 mm at the wafer is about 1.6 deg of pointing. For L/r 11.7 that costs up to 10 points, for L/r 5.8 up to 4, for L/r 2.9 up to 2. Source alignment (and its drift with bake-out and plate replacement) then becomes a design and commissioning requirement.
- **Longer throw does not help at the same aim.** At 450 mm with the 350 mm optimum aim, range/mean rises to 2.3-14 % for the beaming plates; the aim has to be re-optimized.
- **Limits.** Free-molecular (valid for the many-hole plates at 0.5-3 sccm), 19 sampled holes (pitch R/2; the scenario study shows sampling converged), a 15 mm grid refined in 5 mm steps, and a single uniform-output plate. Steep 60-65 deg N ports must also clear the Ga cell and shutter geometry, which is not checked. Real plates may have tilted holes or radial output profiles.

## Next steps

1. Done: aperture-plate source.
2. Done (first pass): sensitivity study above. Add tilted holes and hole-density patterns when a representative drawing is found.
3. Combine with the Ga DSMC results: Ga/N ratio range across 200 mm for candidate layouts over the admissible fill range.
4. Done (2026-09-30): Knudsen check for the published plates (above). Still open: plume collisions just outside the plate at 10 sccm, and a hole-scale DSMC for the transitional cases if they matter for the chosen operating range.
