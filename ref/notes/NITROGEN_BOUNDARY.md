# Nitrogen boundary and measurement access (planning)

Started 2026-09-29 in response to the Stage A review (recommendation 6). Plasma chemistry is not modelled here. This note defines the nitrogen *boundary* the twin needs, and the commissioning measurements that will pin it down. Evidence already collected: [hardware evidence](HARDWARE_EVIDENCE.md) (H02 RF source sheet, P0 data request), [growth evidence](GROWTH_EVIDENCE.md) (G02, G06, nitrogen source matrix), [representative chamber](REFERENCE_CHAMBER.md) (R10-R12, gap in public 200 mm maps).

## Why it limits the source-layout decision now

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

## Next steps

1. Done: aperture-plate source.
2. Done (first pass): sensitivity study above. Add tilted holes and hole-density patterns when a representative drawing is found.
3. Combine with the Ga DSMC results: Ga/N ratio range across 200 mm for candidate layouts over the admissible fill range.
4. Knudsen check for the plate holes and the plume at typical flows (1-3 sccm).
