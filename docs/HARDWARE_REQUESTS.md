# Hardware information requested for the 200 mm GaN MBE design

Status: 2026-10-02. For the hardware team and for nitrogen-source, heater and chamber vendors.

We are choosing where to mount the nitrogen plasma source and the gallium cells on a 200 mm GaN-on-Si MBE chamber, which nitrogen aperture plate to specify, and which heater to use, using a computer model of the chamber. The working layout mounts the nitrogen source on the same ring as the effusion cells, aimed about 100 mm off the wafer centre. The model shows that the choice, and whether the target growth rate is reachable at all, now depend on a few hardware facts that no published source gives. Each request below says what we need, in what form, and which decision it settles. Approximate or preliminary figures are useful; please say how each figure was obtained (measured, calculated or specified).

## 1. Nitrogen plasma source: active-nitrogen output (highest priority)

**What we need.** For the source and aperture plate you would supply:
- Active nitrogen output in atoms per second leaving the plate, versus N2 flow (2, 5, 10, 20, 35 sccm if the source allows) and RF power (up to 600 W).
- If output in atoms/s is not available: the N-limited (gallium-rich) GaN growth rate at the wafer centre for those flows and powers, with the source-to-wafer distance, the source angle to the wafer normal, the wafer size and the growth temperature of that measurement.
- The flow range in which the discharge stays in its bright (inductive) mode with that plate, and the mass-flow controller's calibration gas and standard conditions.

**Why.** On a 200 mm wafer, 1 um/h of GaN needs about 4.5-7e18 active N atoms/s leaving the plate, depending on the layout. One sccm of N2 contains 9e17 N atoms/s. With a plate like the published Veeco UNI-Bulb one, 1 um/h stays within the flow range our model can vouch for only if 80-90 % of the feed's atoms leave the plate as active nitrogen. With a large high-conductance plate and strong pumping, 22 % would do. Published growth rates suggest roughly 6-57 % at 15-34 sccm, depending on chamber geometry that the papers do not state. If the real figure is near the low end, one source reaches only about 0.05-0.3 um/h on 200 mm, and the design must plan for that or for more than one source.

## 2. Aperture plate drawing

**What we need.** Hole count, hole diameter, plate thickness, hole pattern and active (perforated) radius; any hole tilt; plate material.

**Why.** The plate sets both the beam shape (how evenly the nitrogen lands) and the highest flow at which the holes still emit as the model assumes. For a plate like the published Veeco UNI-Bulb one (about 2000 holes of 0.34 mm in a 0.5 mm plate), that limit is about 6 sccm. A plate with 8000 holes of 0.5 mm in a 0.5 mm plate over a 30 mm radius stays within it up to about 40 sccm, and in the model makes 1 um/h reachable at realistic conversion.

**Please also tell us:** whether such a high-conductance plate can be supplied for your source, and the lowest flow at which it keeps the plasma lit (a published high-conductance plate needed at least 3 sccm).

## 3. Pumping

**What we need.** The effective pumping speed for N2 at the growth chamber during growth (with the cryoshroud cold), or the chamber pressure measured at two or more N2 flows; pump models and the conductance of the pumping port.

**Why.** Gas the pumps cannot remove scatters both beams. With 0.5 m^3/s effective speed, 1 um/h is unreachable for either layout at any conversion; with 2 m^3/s it needs the high conversion above; a published cryo-pumped chamber reached at least about 4 m^3/s.

## 4. Substrate heater

**What we need.** The heater element's maximum temperature and what the quoted 1200 C rating refers to (element, holder or wafer); zone layout and power per zone; expected element lifetime in an active-nitrogen atmosphere at that temperature. Also: whether a pyrometer (or other sensor) can view the wafer centre during growth, and its accuracy.

**Why.** To hold 740 C across realistic wafer and holder variations, the model needs the element up to about 1500 K, about 27 K above 1200 C. Without that headroom some wafers run up to 18 K cold and, with a fixed gallium supply, form gallium droplets. A wafer-centre temperature reading accurate to about 2 K, used to correct the gallium supply, removes most of that risk in the model.

## 5. Mounts, ports and holder

**What we need.**
- Port schedule of the chamber (angles and flange sizes), with machining tolerance of the port axes.
- Nitrogen source mount: type (fixed, tilting adapter), adjustment range, the pivot point of any adjustment, and the repeatability of the aim after remounting.
- Wafer holder drawing: lip height above the wafer face, opening radius, wafer support.
- Effusion cell, shutter and flange drawings for the Ga and Al cells.

**Why.** The working layout needs the nitrogen port machined about 15 deg off the line to the wafer centre. A pointing error of 0.8 deg moves the aim 4-16 mm depending on where the mount pivots, which roughly doubles the thickness spread. With the nitrogen source on the cell ring, the gallium and aluminium cells leave a guaranteed gap of about 6 mm (9 mm at the closest sampled points) with our assumed dimensions; the real drawings decide whether that fits.

## 6. Chamber drawing

**What we need.** A dimensioned chamber drawing or CAD model: source ports, cryoshroud, RHEED and pyrometer lines of sight, main shutter, manipulator.

**Why.** The clearance checks so far use simplified solids and do not include the cryoshroud or the diagnostic lines of sight.

## Contact and format

Any format is fine (PDF datasheets, drawings, spreadsheets, emails). Partial answers are useful: items 1-3 decide whether the target growth rate is reachable and are the most urgent.
