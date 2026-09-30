"""SPARTA (DSMC) runs of a production effusion source: any frustum crucible, any melt plane,
and transport of the sampled beam onto an inclined, rotating wafer.

Generalizes the R07 benchmark set-up (scripts/sparta_r07.py, `sparta.crucible_surface`):
- `crucible_surface`: the melt section of a `crucible.Crucible`, including a level melt in a
  tilted crucible (`beam.level_melt_normal`), with the bore wall between the melt boundary
  and the lip and the absorbing orifice plane out to the box faces. Local frame as in
  `crucible` and `beam.CrucibleSource`: orifice plane z = 0, axis +z.
- `SourceRun`: writes the SPARTA input for one state (species, temperature, saturation
  pressure, collision diameter) on a two-level grid scaled by the bore diameter.
- `wafer_profile`: ballistic transport of slab samples to the wafer plane of a
  `beam.CrucibleSource` placement, histogrammed in wafer radius. Uniform rotation averages
  the flux over azimuth, so the annulus histogram is the rotation-averaged profile.
"""

from dataclasses import dataclass

import numpy as np

from .sparta import LIP, MELT, WALL, SurfaceMesh, write_surf
from .units import K_B


def crucible_surface(crucible, half_width, n_segments=64):
    """Triangulated crucible for SPARTA (types MELT, WALL, LIP; normals into the flow).

    Melt boundary and lip vertices share azimuths, so each wall quad spans one generator of
    the frustum. n_segments must be a multiple of 8 (square corners are vertices).
    """
    if n_segments % 8:
        raise ValueError("n_segments must be a multiple of 8")
    a = crucible.lip_radius
    if not a < half_width:
        raise ValueError("box half-width must exceed the lip radius")
    k = n_segments
    th = 2.0 * np.pi * np.arange(k) / k
    c, s = np.cos(th), np.sin(th)
    square = half_width / np.maximum(np.abs(c), np.abs(s))
    sq = np.stack([square * c, square * s], 1)
    on_face = np.isclose(np.abs(sq), half_width, rtol=0.0, atol=1e-12 * half_width)
    sq[on_face] = np.sign(sq[on_face]) * half_width
    melt = crucible.melt_boundary(k)  # same azimuths th
    points = np.concatenate([
        crucible.melt_origin[None, :],                          # 0: axis point on the melt
        melt,                                                   # 1..k
        np.stack([a * c, a * s, np.zeros(k)], 1),               # k+1..2k lip
        np.stack([sq[:, 0], sq[:, 1], np.zeros(k)], 1),         # 2k+1..3k box square
    ])

    def m(i):
        return 1 + i % k

    def lip(i):
        return 1 + k + i % k

    def box(i):
        return 1 + 2 * k + i % k

    tris, types = [], []
    for i in range(k):
        tris.append((0, m(i), m(i + 1)))
        types.append(MELT)
        tris += [(m(i), lip(i + 1), m(i + 1)), (m(i), lip(i), lip(i + 1))]
        types += [WALL, WALL]
        tris += [(lip(i), box(i), box(i + 1)), (lip(i), box(i + 1), lip(i + 1))]
        types += [LIP, LIP]
    return SurfaceMesh(points, np.array(tris), np.array(types))


@dataclass(frozen=True)
class SourceRun:
    """One steady DSMC state of a crucible source, lengths in metres.

    The fine grid (cell) covers the bore and one bore diameter above the orifice; coarse
    cells (coarse * cell) fill the rest. `slab_D` is the sampling slab in bore diameters
    above the orifice. `half_angle_deg` is the largest ray angle from the axis that must stay
    inside the box up to the slab top.
    """

    crucible: object  # crucible.Crucible
    species: str
    mass_kg: float
    temperature_k: float
    pressure_pa: float
    diameter_m: float | None  # None: collisionless
    cell_m: float
    coarse: int = 3
    particles: float = 2e5
    dt_factor: float = 0.3
    steps_eq: int = 8000
    steps_sample: int = 16000
    dump_every: int = 20
    slab_D: tuple = (5.0, 5.5)
    half_angle_deg: float = 25.0
    seed: int = 12345

    @property
    def bore(self):
        return 2.0 * self.crucible.lip_radius

    @property
    def n_sat(self):
        return self.pressure_pa / (K_B * self.temperature_k)

    @property
    def mean_speed(self):
        return np.sqrt(8.0 * K_B * self.temperature_k / (np.pi * self.mass_kg))

    @property
    def lowest_melt_z(self):
        return float(self.crucible.melt_boundary(720)[:, 2].min())

    @property
    def gas_volume(self):
        """Volume between melt and orifice (numerically, for fnum)."""
        c = self.crucible
        z = np.linspace(self.lowest_melt_z, 0.0, 401)
        zc = 0.5 * (z[1:] + z[:-1])
        r = c.lip_radius + c.slope * zc
        # fraction of each disk above the melt plane, from the melt height at each azimuth
        phi = np.linspace(0.0, 2.0 * np.pi, 361)[:-1]
        nrm = c.unit_melt_normal
        rr = np.sqrt((np.arange(20) + 0.5) / 20)  # equal-area radii
        area_frac = np.empty(len(zc))
        for i, (zz, rad) in enumerate(zip(zc, r)):
            x = rad * rr[:, None] * np.cos(phi)
            y = rad * rr[:, None] * np.sin(phi)
            above = (x * nrm[0] + y * nrm[1] + (zz - c.melt_origin[2]) * nrm[2]) >= 0.0
            area_frac[i] = above.mean()
        return float(np.sum(np.pi * r ** 2 * area_frac * np.diff(z)))

    @property
    def fnum(self):
        return self.n_sat * self.gas_volume / self.particles

    @property
    def dt(self):
        return self.dt_factor * self.cell_m / self.mean_speed

    @property
    def slab(self):
        return (self.slab_D[0] * self.bore, self.slab_D[1] * self.bore)

    @property
    def lambda_sat(self):
        if self.diameter_m is None:
            return np.inf
        return K_B * self.temperature_k / (np.sqrt(2.0) * np.pi * self.diameter_m ** 2 * self.pressure_pa)

    def box(self):
        h = self.coarse * self.cell_m
        a = self.crucible.lip_radius
        need = max(1.25 * self.bore, self.slab[1] * np.tan(np.radians(self.half_angle_deg)) + a)
        half_width = h * np.ceil(need / h)
        zlo = self.lowest_melt_z - 0.5 * h
        nz = int(np.ceil((self.slab[1] + 0.5 * self.bore - zlo) / h))
        return half_width, zlo, zlo + nz * h, int(round(2 * half_width / h)), nz

    def config(self):
        c = self.crucible
        return {
            "crucible": {"lip_radius_m": c.lip_radius, "melt_depth_m": c.melt_depth,
                         "slope": c.slope, "melt_normal": list(map(float, c.unit_melt_normal))},
            "species": self.species, "mass_kg": self.mass_kg, "T_K": self.temperature_k,
            "p_Pa": self.pressure_pa, "diameter_m": self.diameter_m, "cell_m": self.cell_m,
            "coarse": self.coarse, "particles": self.particles, "dt_factor": self.dt_factor,
            "steps_eq": self.steps_eq, "steps_sample": self.steps_sample,
            "dump_every": self.dump_every, "slab_D": list(self.slab_D),
            "half_angle_deg": self.half_angle_deg, "seed": self.seed,
            "fnum": self.fnum, "dt_s": self.dt, "slab_m": list(self.slab),
            "lambda_sat_m": None if self.diameter_m is None else self.lambda_sat,
            "gas_volume_m3": self.gas_volume,
        }

    def write_inputs(self, work):
        half_width, zlo, top, nx, nz = self.box()
        write_surf(crucible_surface(self.crucible, half_width), work / "surf.crucible",
                   comment=f"{self.species} crucible (SI units)")
        sp = self.species
        amu = self.mass_kg / 1.66053906660e-27
        (work / "gas.species").write_text(f"{sp} {amu:.6f} {self.mass_kg:.6e} 0 0 0 0 0 1.0 0.0\n",
                                          encoding="ascii", newline="\n")
        d = self.diameter_m if self.diameter_m is not None else 1e-10
        (work / "gas.vss").write_text(f"{sp} {d:.6e} 0.5 {self.temperature_k:.2f} 1.0\n",
                                      encoding="ascii", newline="\n")
        grid = f"create_grid {nx} {nx} {nz}"
        if self.coarse > 1:
            grid += f" levels 2 region 2 fine {self.coarse} {self.coarse} {self.coarse} inside any"
        t, slab = self.temperature_k, self.slab
        lines = [
            f"seed {self.seed}", "dimension 3", "units si", "global gridcut 0.0",
            "boundary o o o",
            f"create_box {-half_width} {half_width} {-half_width} {half_width} {zlo} {top}",
            f"region fine cylinder z 0 0 {self.crucible.lip_radius + 0.5 * self.bore} {zlo} {self.bore}",
            grid,
            f"global fnum {self.fnum:.6e}",
            f"species gas.species {sp}",
            f"mixture melt {sp} nrho {self.n_sat:.6e} temp {t} vstream 0 0 0",
            "read_surf surf.crucible type",
            "group melt surf type 1", "group wall surf type 2", "group lip surf type 3",
            "surf_collide absorb vanish",
            f"surf_collide hot diffuse {t} 1.0",
            "surf_modify melt collide absorb", "surf_modify lip collide absorb",
            "surf_modify wall collide hot",
            "collide vss melt gas.vss" if self.diameter_m is not None else "collide none",
            "fix evap emit/surf melt melt",
            f"timestep {self.dt:.6e}",
            "stats 1000", "stats_style step cpu np nattempt ncoll nscoll",
            f"run {self.steps_eq}",
            f"region slab block INF INF INF INF {slab[0]} {slab[1]}",
            f"dump slab particle melt {self.dump_every} dump.slab.* id x y z vx vy vz",
            "dump_modify slab region slab",
            f"run {self.steps_sample}",
        ]
        (work / "in.case").write_text("\n".join(lines) + "\n", encoding="ascii", newline="\n")


def wafer_profile(positions, velocities, slab, source, wafer, radii_edges):
    """Rotation-averaged arrival flux on the wafer from slab samples in the source frame.

    positions, velocities: (N, 3) snapshots in the crucible frame (z along the axis); each
    sample stands for the same number of real particles. `source` is a
    `beam.CrucibleSource` (its lip centre and axis place the crucible frame in the chamber),
    `wafer` a `beam.Wafer`. Returns the weighted count per unit wafer area in annuli between
    radii_edges (scale by fnum / snapshots) and the weight sum of particles that reach the
    wafer plane.
    """
    p, v = np.asarray(positions, float), np.asarray(velocities, float)
    z0, z1 = slab
    keep = (p[:, 2] >= z0) & (p[:, 2] < z1) & (v[:, 2] > 0.0)
    p, v = p[keep], v[keep]
    w = v[:, 2] / (z1 - z0)
    frame = source._frame  # rows: local axes in chamber coordinates
    pc = source.to_chamber(p)
    vc = v @ frame
    c = np.asarray(wafer.center, float)
    n = np.asarray(wafer.normal, float) / np.linalg.norm(wafer.normal)
    vn = vc @ n
    with np.errstate(divide="ignore", invalid="ignore"):
        t = ((c - pc) @ n) / vn
    hit = (vn < 0.0) & (t > 0.0)
    h = pc[hit] + t[hit, None] * vc[hit]
    rho = np.linalg.norm(h - c, axis=1)
    edges = np.asarray(radii_edges, float)
    flux = np.histogram(rho, bins=edges, weights=w[hit])[0] / (np.pi * np.diff(edges ** 2))
    return flux, float(w[hit].sum())
