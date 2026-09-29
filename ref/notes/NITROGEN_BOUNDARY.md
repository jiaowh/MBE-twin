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

## Next steps

1. Implement an aperture-plate source (hole pattern of short-tube emitters) using the existing beam code; verify against a single-tube `crucible.py` result and a flat-disk limit.
2. Sensitivity study of the wafer N map over hole-pattern radius, plate profile (flat versus centre-peaked output), throw and angle, labelled `representative_chamber`.
3. Combine with the Ga DSMC results: Ga/N ratio range across 200 mm for candidate layouts over the admissible fill range.
4. Knudsen check for the plate holes and the plume at typical flows (1-3 sccm).
