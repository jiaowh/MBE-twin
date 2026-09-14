## ppt/slides/slide1.xml

ITF PROJECT PROPOSAL · FOR REVIEW COMMITTEE
GaN Molecular Beam Epitaxy regrowth Platform
Phase 1 of the 8-12 inch domestic MBE cluster:
the MBE growth module and in-vacuum anneal module, built first.
HK$49.0M · 24 months   within the HK$50M ITF platform-project envelope

August 2026 · Hong Kong SAR
Self-built MBE system class — in-house design, globally sourced components

## ppt/slides/slide2.xml
02
MBE PLATFORM PROPOSAL · TARGET PROCESS
The target process: selective-area regrowth (SAG)
GaN regrowth has been extensively studied in academia. Industry is going to follow. 
Source/Drain regrowth
Ultra-low contact resistance
Son. First demonstration of fmax > 700 GHz in Lg = 45 nm In0.13Al0.83Ga0.04N/GaN HEMTs 
for future 6G applications. 2026

## ppt/slides/slide3.xml
03
MBE PLATFORM PROPOSAL · TARGET PROCESS
The target process: selective-area regrowth (SAG)
GaN regrowth has been extensively studied in academia. Industry is going to follow. 
Gate regrowth
Decouple VT and Rext
SINANO. Normally-off HEMTs With Regrown p-GaN Gate and Low-Pressure Chemical Vapor Deposition SiNx Passivation by Using an AlN Pre-Layer.2019

## ppt/slides/slide4.xml
04
MBE PLATFORM PROPOSAL · TARGET PROCESS
The target process: selective-area regrowth (SAG)
GaN regrowth has been extensively studied in academia. Industry is going to follow. 
Barrier regrowth
Etch-damage free
 Jiang. Enhancement-Mode GaN MOS-HEMTs With Recess-Free Barrier Engineering and High-k ZrO2 Gate Dielectric. EDL.2018

## ppt/slides/slide5.xml
MBE PLATFORM PROPOSAL · WHY MBE
Why regrowth is hard — and advantages of MBE
05
WHY FEW LABS MASTER IT
01  Interface contamination
Si and O pile up at the etched-then-regrown interface and form a parallel leakage channel — the documented bottleneck for regrown junctions (ASU 2019; Sandia 2021).
02  Etch damage
Dry etch leaves lattice damage and roughness on the exposed surface; the regrown crystal inherits every defect — degrading breakdown and reverse leakage.
03  Thermal budget on patterned wafers
Regrowth happens on a half-processed device: MOCVD's ~1,000 °C in NH₃/H₂ attacks masks and surfaces, and hydrogen passivates the p-GaN it touches.
Etch-then-regrow in practice: the dry-etched surface (damage) and the regrowth interface (contamination) are where devices are won or lost. Even record processes need UV-ozone + chemical + in-situ cleans to recover low leakage.

WHY MBE ANSWERS ALL THREE
As low as 700°C
growth window, 200–300 °C below MOCVD — patterned surfaces, masks and existing junctions stay intact
H-free UHV
no NH₃/H₂: p-GaN is active as grown, and the regrowth interface stays clean at 10⁻¹¹ mbar
In-vacuo clean
pre-regrowth anneal + interface preparation without air break — directly attacks the Si/O problem
RHEED control
monolayer-abrupt n⁺ regions, monitored live on patterned wafers
Sources: ASU 2019 (etch-then-regrow p-n) · Sandia 2021 (interfacial Si) · NIST 2024 (regrowth-interface contaminants)

## ppt/slides/slide6.xml
06
MBE PLATFORM PROPOSAL · STRATEGIC CONTEXT
Export control has turned MBE from a purchase into a capability gap


1979
CoCom embargo — CAS institutes answer with the first domestic MBE; National S&T Progress Award, 1985.

1990s
Ban lifted — the market is ceded to imports and the domestic UHV component chain stagnates.

2019
Wassenaar re-ban — solid- and gas-source MBE systems and key components controlled for China.

2025
Control reaches orders — RIBER discloses two licence rejections, ~€4M of orders lost.

THE GAP THIS PLATFORM CLOSES
~90%
of the global MBE market held by VEECO + RIBER — both licence-gated
0
domestic production-validated MBE tools above 4 inches
8″+
wafer sizes where AI optics, GaN RF/power and MicroLED demand sits
Every embargo in history has opened a substitution window — this one is open now.
Multi-wafer nitride MBE processing (Mota reference line)
Sources: Mota feasibility report (2022 vendor shares); RIBER 2025 interim disclosures; Wassenaar Arrangement 2019 listing.

## ppt/slides/slide7.xml
07
MBE PLATFORM PROPOSAL · EXECUTIVE SUMMARY
What to build — the growth engine first
01  Strategic necessity
MBE has sat under Wassenaar export control since 2019; licence denials are now commercial reality. An 8-inch production tool can no longer simply be bought.
02  Phase 1 scope
Build the two chambers that create epitaxial quality — the 8″ MBE growth module (HK$19M) and the in-vacuum anneal module (HK$3.5M) — cluster-ready by design.

8″ MBE + High-temp anneal in 24 months
wafer size — beyond any domestic MBE in operation
Radial cluster architecture: growth, anneal and analysis modules attach to one UHV distribution hub — wafers move at 5×10⁻¹⁰ mbar, never seeing air.
PVD module 
(potential expansion)
High temperature 
anneal module

## ppt/slides/slide8.xml
08
MBE PLATFORM PROPOSAL · EXECUTIVE SUMMARY
How can we build
03  Proven blueprint, complementary partners
system design based on their 4’’ self-built system 
supply chain 
nitride process heritage
Mota, Inc. (Jiangsu)
MRDI
8’’ System Integration 
Pilot line process validation
nitride process heritage
Chamber set
Growth + buffer + load-lock · LN₂ shrouds · cluster frame
Nitrogen source
RF plasma, 600 W @ 13.56 MHz · all-ceramic discharge · ion-free flux
Substrate heater
Solid SiC, 1,200 °C in reactive gas — regrowth-grade
Effusion cells
10 sources: 3×Ga, 3×Al, Si, Mg + spares · PBN crucibles · PID loops
Pumping
Maglev turbo ≥2,000 L/s · cryopumps · ion pump + Ti sublimation
In-situ diagnostics
30 keV RHEED · band-edge pyrometer · beam-flux monitor · RGA
Wafer handling
UHV robot + platens to 12″ · heated viewports · cassette load-lock
Control
Open software stack · interlocks + logging · AI-ready (Level-5 roadmap)
UHV growth chamber
RF plasma source
30 keV RHEED gun
Wafer transfer robot

## ppt/slides/slide9.xml


09
MBE PLATFORM PROPOSAL · SUPPLY CHAIN
Key supply chain considerations
Low risk of export restriction on buying parts vs buying a full MBE system
Almost all components can find domestic replacement. (key gap is reliability)
The project team can do parts customization, if needed.
THE TEAM BEHIND PARTS CUSTOMIZATION AND VALIDATION
Zhigang Wang
Head of Etch, Thin Film & Equipment Empowerment (EET), MRDI
20 years in semiconductor equipment — 18 at Applied Materials, from 300 mm silicon process R&D (Santa Clara) to directing the Xi'an Demo Lab and leading the 200/300 mm etch engineering teams; Etch BD Lead at NAURA (2024–25).
Dr. Zhuofei Gan
R&D Lead Engineer, Equipment-Enabling Projects, MRDI
Ph.D. (HKU); co-founder of InterLitho Technology; ~20 high-impact publications. Hands-on expertise in advanced lithography, precision bonding and 2.5D/3D packaging equipment — now leading co-development of next-generation equipment at MRDI.

## ppt/slides/slide10.xml
10
MBE PLATFORM PROPOSAL · SUPPLY CHAIN
Import the best today — qualify domestic parts on the same tool

COMPONENT CATEGORY
PRIMARY SOURCE (GLOBAL)
DOMESTIC CANDIDATE

RF plasma / RF power
VEECO · OAR · AE / COMET
Hengyunchang 恒运昌
Turbomolecular pumps
Edwards · Leybold · ULVAC
SKY 中科科仪

Mass flow controllers
MKS · Bronkhorst
Sevenstar 七星华创
UHV valves
VAT · HVA · VACGEN
Kinglai / Jingsheng / Jiutian

Gauges & RGA
INFICON · MKS · Hiden
Hexin 禾信仪器
High-purity materials
UMC · DOWA · Plansee
Vital / GRINM 先导 / 有研
12
UHV component categories tracked in Mota's supplier programme
≥6
categories benchmarked on-tool during Phase 1
Imported baselines guarantee schedule; domestic parts are validated in parallel — never on the critical path. The tool itself becomes the qualification vehicle for the domestic UHV supply chain.

## ppt/slides/slide11.xml
11
MBE PLATFORM PROPOSAL · EXECUTIVE SUMMARY
The innovations that make the system succeed
Multi-zone heat balancing with real-time closed-loop control during growth – enabler for 8″ production tool vs small diameter tools
PVD + MBE cluster tool integration — low cost, high throughput
Enhanced plasma source for high-throughput Ga(Al)N growth

## ppt/slides/slide12.xml
12
MBE PLATFORM PROPOSAL · WORK PLAN
24 months, four phases, stage-gated

P1 · Design & procure   M0–M6
Design freeze · long-lead orders (chamber, pumps, sources, robotics) · MRDI site prep

G1  Design review passed; 100% long-lead on order

P2 · Assemble & test   M6–M12
Module assembly in Mota's Jiangsu class-10k cleanroom · leak-check, bake-out, pump-down · domestic bench tests

G2  Factory acceptance; ship to Hong Kong

P3 · Install & first epi   M12–M18
Installation and UHV integration at MRDI · commissioning + interlocks · first plasma → first GaN epitaxy on 8″

G3  Site acceptance; first epitaxy reviewed

P4 · Process & regrowth   M18–M24
Device-grade MQW (M22) · selective-area regrowth flow · anneal-module DOE · user demos

G4  Final review; platform enters shared service
M18
first GaN regrowth epitaxy on 8″ wafers
M22
device-grade MQW, XRD / PL verified
Quarterly steering-committee gates · budget released per phase (40 / 25 / 20 / 15%) contingent on gate approval · monthly Jiangsu–Hong Kong technical sync.

## ppt/slides/slide13.xml
Relation to the GaN technology roadmap
MBE PLATFORM PROPOSAL · ROADMAP ALIGNMENT
MRDI planar power GaN roadmap

WHAT THE ROADMAP NEEDS   Low-defectivity processes and scalable cost. Gen2 (2028) already schedules regrown S/D and scaled ohmic/gate
16

## ppt/slides/slide14.xml
13
MBE PLATFORM PROPOSAL · APPLICATIONS
A standing user base before a single external sale

Selective-area regrowth process module as standard services
Regrown ohmics and gates, buried heterostructures, PIC integration — turns a multi-week outsourced cycle into an in-house, days-long loop for MRDI users.

Nitride power & RF
GaN HEMT stacks with MBE's abrupt interfaces and hydrogen-free p-doping — feeding MRDI's GaN pilot line and the GBA device chain directly.

MicroLED & future materials
High-indium InGaN and tunnel junctions where MBE beats MOCVD; 12″ BTO / oxide epitaxy as the platform's next programme.

DAY-ONE DEMAND   MRDI's ~50 pilot runs per year · the GBA's merchant epi and device players — the platform qualifies into a market that already exists.

## ppt/slides/slide15.xml
14
MBE PLATFORM PROPOSAL · RISKS
Named risks, engineered mitigations

RISK
LEVEL
MITIGATION

8″ scale-up of self-built design
Medium
Architecture follows proven production-MBE precedents; factory acceptance per module before shipment; G2/G3 hold points
Anneal-module crystal quality
Medium
Route anchored in published high-T anneal literature; dedicated DOE with XRD/TEM verification before device commitment

Long-lead component slip
Low–Med
All procurement in Phase 1; 10% hardware contingency inside module budgets; gate reviews can re-sequence without moving first-epi milestone
Talent recruitment in Hong Kong
Medium
Joint team from day one; Mota engineers seconded for build and training; MRDI hiring programme + GBA talent schemes

Domestic component shortfall
Low
Imported baseline guarantees performance — domestic parts validated in parallel, never on the critical path
Risk ownership: technical — joint chief engineer · procurement & licensing — MRDI with Mota support · site & operations — MRDI. Reviewed at every gate.

## ppt/slides/slide16.xml
15

HK$49.0M and 24 months —
and the region's first 8″ MBE platform is built, not bought.
The MBE growth module and anneal module first — the quality core of the patented PVD + anneal + MBE cluster — designed jointly by MRDI and Mota, built from the best components the world still sells, and ready for Phase 2 to complete the 8–12″ cluster on the same interfaces.

HK$49.0M
27.5 equipment · 10.0 manpower · 5.1 ODC · 6.4 overheads

M18
first GaN epitaxy on 8″; device-grade MQW by M22

8″ → 8–12″
cluster-ready today; PVD + hub complete it in Phase 2

≥6
domestic component categories benchmarked on-tool
MRDI × JIANGSU MOTA — AUGUST 2026 · FOR REVIEW COMMITTEE EVALUATION

## ppt/slides/slide17.xml

17
MBE PLATFORM PROPOSAL · BUDGET
HK$49.0M over 24 months — inside the HK$50M envelope
EQUIPMENT & INSTALLATION — HK$27.5M
01
8″ MBE growth module (including load lock)
chamber set · 10 sources · pumping · RHEED + diagnostics · handling
19.0
02
Anneal module
in-vacuo high-T recrystallisation chamber (nudged up from 2.5 for 8″ hot zone)
3.5
03
Facility & installation
LN₂ distribution · 3-phase + UPS · chiller · bake-out · O₂ alarm
2.0
04
Freight, insurance & licences
EU→HK sea freight · rigging · customs · HK 3B001 import licence
2.0
05
Controls & software
control PCs · DAQ · frame grabber · interlocks · open stack
1.0
Deferred to Phase 2: PVD module, 12″ hub & robotics, domestic validation sets (~HK$3.5M)
ITF BUDGET STRUCTURE (HK$M)
Equipment & installation

27.5
Manpower (6.2 FTE, 24 mo)

10.0
Other direct costs

5.09
Administrative overheads (15%)

6.39

TOTAL   HK$49.0M
Industry contribution: Mota in-kind design IP + seconded engineers, ≥10% per ITF platform-project precedent.

MARKET BENCHMARK   One RIBER MBE 49 production tool was quoted at €3.54M ≈ HK$30M — more than this entire Phase-1 hardware budget, with no IP, no process database, and licence risk.

## ppt/slides/slide18.xml
18
MBE PLATFORM PROPOSAL · BUDGET DETAIL
Manpower and direct costs follow MRDI project precedents
MANPOWER — HK$10.03M (structure of prior MRDI ITF budgets)

Position / rank
FTE
Months
Rate (k)
Subtotal (k)

Division Leader (PC)
0.2
24
150
720
Senior Manager / Principal Engineer
1.5
24
100
3,600

Assoc. Principal / Lead Engineer
1.0
24
70
1,680
Senior Engineer / Engineer
3.5
24
48
4,032

Total



10,032
Vacuum/mechanical · MBE process · controls software · electrical — one tightly integrated build team, trained on-tool for MRDI operations.
OTHER DIRECT COSTS — HK$5.09M

CAN IT BE DONE INSIDE HK$50M?  Yes — with HK$1.0M headroom. The collaborator plan's HK$30M hardware is trimmed to HK$27.5M by deferring the PVD module and hub to Phase 2; HK$2.0M of added ODC funds short-loop wafer processing to validate regrowth results; manpower and ODC follow the audited MRDI budget precedents.

Source materials & first fill (7N Ga, Al, Si, Mg · PBN · gaskets)
1,000
Commissioning wafers & substrates
800

LN₂, gases & utilities (commissioning)
600
Wafer processing — regrowth validation short-loops (~60 wafers)
1,500

Material & device characterisation (AFM · XRD · mapping)
500
Domestic-component validation consumables
300

Travel & collaboration
200
Publications & patent filings
150

Audit fee
40

Subtotal (HK$k)
5,090

## ppt/slides/slide19.xml
19
MBE PLATFORM PROPOSAL · DELIVERABLES
Deliverables

D1

8″ MBE growth module + anneal module installed and commissioned at MRDI, cluster-ready

D2

Open, jointly owned control software — Level-3+ automation

D3

Demo process flows: GaN epitaxy, MQW structures and selective-area regrowth on 8″

D4

Domestic component validation data — ≥6 categories benchmarked on-tool

D5

Application demos with MRDI pilot-line users + trained local engineering team
SUCCESS METRICS (TARGETS)
10⁻¹¹ mbar
growth-module base pressure class after bake-out
M18 / M22
first GaN epitaxy on 8″ / device-grade MQW (XRD, PL)
≥5 patents
invention filings; jointly owned design + process IP
≥12 FTE
local engineers trained across vacuum, process, software

