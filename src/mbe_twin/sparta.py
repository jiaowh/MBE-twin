"""Geometry and post-processing for collisional crucible runs with SPARTA (DSMC).

The free-molecular model (crucible.py) cannot represent intermolecular collisions, which R07
shows reshape the beam at practical rates (scripts/crucible_knudsen.py). SPARTA runs inside
WSL (serial build, see `run_case`); this module holds the parts that do not depend on it:

- `crucible_surface`: a triangulated conical crucible in SPARTA's 3d surface-file layout.
  Flow occupies the bore and the half-space above the orifice plane z = 0. The surface is
  the melt disk (type 1) at z = -melt_depth, the bore wall (type 2), and the orifice plane
  outside the lip (type 3), a square reaching the side walls of the simulation box, which
  must be clipped there. Triangle normals, (p2 - p1) x (p3 - p1), point into the flow.
- `propagate_slab`: turns particles sampled in a thin slab above the orifice into the
  arrival flux on a distant plane normal to the axis, by straight-line flight. Far enough
  above the orifice the gas is collisionless, since its density falls as 1/r^2.

SPARTA's fix emit/surf with zero stream velocity emits Bird's (1994) eq. 4.22 flux n <v>/4
with flux-weighted normal velocities (checked in fix_emit_surf.cpp), i.e. a cosine-law
evaporating melt at saturation density n.
"""

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

import numpy as np

MELT, WALL, LIP = 1, 2, 3
# Pinned build: github.com/sparta/sparta commit e071055 (banner "SPARTA (27 Aug 2026)"),
# `make serial` in the WSL Ubuntu 24.04 home directory.
SPARTA_WSL_EXE = "~/sparta/src/spa_serial"


@dataclass(frozen=True)
class SurfaceMesh:
    points: np.ndarray  # (N, 3)
    triangles: np.ndarray  # (M, 3) zero-based point indices
    types: np.ndarray  # (M,)

    def normals(self):
        p = self.points[self.triangles]
        n = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
        return n / np.linalg.norm(n, axis=1, keepdims=True)

    def areas(self):
        p = self.points[self.triangles]
        return 0.5 * np.linalg.norm(np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]), axis=1)


def crucible_surface(lip_radius, melt_depth, half_width, *, taper_half_angle=0.0, n_segments=64):
    """Conical crucible opening toward z = 0 (as crucible.Crucible with an untilted melt).

    half_width is the box half-width in x and y; the lip plane is triangulated out to it.
    n_segments must be a multiple of 8 so that the square's corners are vertices.
    """
    if n_segments % 8:
        raise ValueError("n_segments must be a multiple of 8")
    melt_radius = lip_radius - melt_depth * np.tan(taper_half_angle)
    if not 0.0 < melt_radius <= lip_radius < half_width:
        raise ValueError("need 0 < melt radius <= lip radius < box half-width")
    th = 2.0 * np.pi * np.arange(n_segments) / n_segments
    c, s = np.cos(th), np.sin(th)
    square = half_width / np.maximum(np.abs(c), np.abs(s))  # ray from the axis to the square
    sq = np.stack([square * c, square * s], 1)
    # Points must lie exactly in a box face for SPARTA to accept the open edges there.
    sq[np.isclose(np.abs(sq), half_width, rtol=0.0, atol=1e-12 * half_width)] = \
        np.sign(sq[np.isclose(np.abs(sq), half_width, rtol=0.0, atol=1e-12 * half_width)]) * half_width
    k = n_segments
    points = np.concatenate([
        [[0.0, 0.0, -melt_depth]],                                                 # melt centre
        np.stack([melt_radius * c, melt_radius * s, np.full(k, -melt_depth)], 1),  # 1..k
        np.stack([lip_radius * c, lip_radius * s, np.zeros(k)], 1),                # k+1..2k
        np.stack([sq[:, 0], sq[:, 1], np.zeros(k)], 1),                            # 2k+1..3k
    ])

    def melt(i):
        return 1 + i % k

    def lip(i):
        return 1 + k + i % k

    def box(i):
        return 1 + 2 * k + i % k

    tris, types = [], []
    for i in range(k):
        tris.append((0, melt(i), melt(i + 1)))  # normal +z
        types.append(MELT)
        tris += [(melt(i), lip(i + 1), melt(i + 1)), (melt(i), lip(i), lip(i + 1))]  # toward axis
        types += [WALL, WALL]
        tris += [(lip(i), box(i), box(i + 1)), (lip(i), box(i + 1), lip(i + 1))]  # normal +z
        types += [LIP, LIP]
    return SurfaceMesh(points, np.array(tris), np.array(types))


def edge_use(mesh):
    """Map from undirected edge to the number of triangles using it."""
    count = {}
    for tri in mesh.triangles:
        for a, b in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
            key = (min(a, b), max(a, b))
            count[key] = count.get(key, 0) + 1
    return count


def write_surf(mesh, path, scale=1.0, comment="crucible"):
    """Write a SPARTA 3d surface file (1-based ids; one type per triangle)."""
    lines = [f"# {comment}", "", f"{len(mesh.points)} points", f"{len(mesh.triangles)} triangles",
             "", "Points", ""]
    lines += [f"{i + 1} {x * scale:.10g} {y * scale:.10g} {z * scale:.10g}"
              for i, (x, y, z) in enumerate(mesh.points)]
    lines += ["", "Triangles", ""]
    lines += [f"{i + 1} {t} {a + 1} {b + 1} {c + 1}"
              for i, ((a, b, c), t) in enumerate(zip(mesh.triangles, mesh.types))]
    Path(path).write_text("\n".join(lines) + "\n", encoding="ascii", newline="\n")


def propagate_slab(positions, velocities, slab, plane_z, radii_edges):
    """Arrival flux on the plane z = plane_z from particles sampled in a slab.

    positions, velocities: (N, 3) snapshots of particles in z in [slab[0], slab[1]); each
    sample stands for the same number of real particles. In steady state a particle with
    upward velocity v_z crosses a plane inside the slab at the rate v_z / thickness, which is
    its flux weight. Returns the weighted count per unit area in annuli between radii_edges
    (scale by fnum / snapshots for an absolute flux) and the weight sum.
    """
    p, v = np.asarray(positions, float), np.asarray(velocities, float)
    z0, z1 = slab
    keep = (p[:, 2] >= z0) & (p[:, 2] < z1) & (v[:, 2] > 0.0)
    p, v = p[keep], v[keep]
    w = v[:, 2] / (z1 - z0)
    t = (plane_z - p[:, 2]) / v[:, 2]
    rho = np.hypot(p[:, 0] + v[:, 0] * t, p[:, 1] + v[:, 1] * t)
    edges = np.asarray(radii_edges, float)
    flux = np.histogram(rho, bins=edges, weights=w)[0] / (np.pi * np.diff(edges ** 2))
    return flux, float(w.sum())


def wsl_path(path):
    """/mnt/<drive>/... path for a Windows path, for use inside WSL."""
    p = PureWindowsPath(Path(path).resolve())
    return "/mnt/" + p.drive[0].lower() + "/" + "/".join(p.parts[1:])


def sparta_available():
    if shutil.which("wsl.exe") is None:
        return False
    r = subprocess.run(["wsl.exe", "-e", "bash", "-lc", f"test -x {SPARTA_WSL_EXE}"],
                       capture_output=True, timeout=120)
    return r.returncode == 0


def run_case(work_dir, script="in.case", log="log.sparta", timeout=36000):
    """Run SPARTA (serial, in WSL) on `script` inside work_dir; returns the log text."""
    work = Path(work_dir)
    cmd = f"cd '{wsl_path(work)}' && {SPARTA_WSL_EXE} -in {script} -log {log} -screen none"
    r = subprocess.run(["wsl.exe", "-e", "bash", "-lc", cmd], capture_output=True, timeout=timeout)
    text = (work / log).read_text(encoding="utf-8", errors="replace") if (work / log).exists() else ""
    if r.returncode != 0 or "Loop time" not in text:
        raise RuntimeError(f"SPARTA failed (exit {r.returncode}):\n{text[-3000:]}"
                           f"{r.stderr.decode(errors='replace')[-2000:]}")
    return text
