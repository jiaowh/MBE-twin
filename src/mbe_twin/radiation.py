"""Reference radiative exchange for coaxial parallel disks (verification of Elmer's
diffuse-gray radiation, cases/verification/elmer_v03_disks).

View factor between coaxial parallel disks of radii r_i (emitter) and r_j at gap L
(Siegel and Howell, Thermal Radiation Heat Transfer, configuration C-41; also derivable from
the Nusselt unit-sphere method):
    F_ij = (X - sqrt(X^2 - 4 (R_j/R_i)^2)) / 2,  X = 1 + (1 + R_j^2) / R_i^2,  R = r / L.
Annulus-to-annulus factors follow by inclusion-exclusion on A F. The ring radiosity system
resolves the non-uniform radiosity over gray disks; surroundings are black at T_ext.
"""

import numpy as np

SIGMA = 5.670374419e-8  # W m^-2 K^-4 (CODATA 2018, exact)


def disk_view_factor(r_i, r_j, gap):
    """F from a disk of radius r_i > 0 to a coaxial parallel disk of radius r_j."""
    ri, rj = np.asarray(r_i, float) / gap, np.asarray(r_j, float) / gap
    x = 1.0 + (1.0 + rj * rj) / (ri * ri)
    return 0.5 * (x - np.sqrt(x * x - 4.0 * (rj / ri) ** 2))


def _af(r_i, r_j, gap):
    """Area times view factor, pi r_i^2 F_ij (zero when either radius is zero)."""
    r_i, r_j = np.broadcast_arrays(np.asarray(r_i, float), np.asarray(r_j, float))
    out = np.zeros(r_i.shape)
    ok = (r_i > 0.0) & (r_j > 0.0)
    out[ok] = np.pi * r_i[ok] ** 2 * disk_view_factor(r_i[ok], r_j[ok], gap)
    return out


def ring_exchange(edges_1, edges_2, gap):
    """Areas and view factors between annuli on two coaxial parallel disks.

    Returns (A1, A2, F12, F21) with F12[i, j] from ring i of disk 1 to ring j of disk 2.
    """
    e1, e2 = np.asarray(edges_1, float), np.asarray(edges_2, float)
    a1 = np.pi * np.diff(e1 ** 2)
    a2 = np.pi * np.diff(e2 ** 2)
    g = _af(e1[:, None], e2[None, :], gap)
    af = g[1:, 1:] - g[1:, :-1] - g[:-1, 1:] + g[:-1, :-1]
    return a1, a2, af / a1[:, None], af.T / a2[:, None]


def floating_disk_temperature(radius, gap, t_hot, t_ext, eps_hot, eps_float, n_rings=200):
    """Temperature of an isothermal disk that exchanges radiation, through one face only,
    with an isothermal coaxial disk at t_hot and black surroundings at t_ext (net zero)."""
    edges = radius * np.sqrt(np.linspace(0.0, 1.0, n_rings + 1))  # equal-area rings
    a1, a2, f12, f21 = ring_exchange(edges, edges, gap)
    n = len(a1)
    f = np.block([[np.zeros((n, n)), f12], [f21, np.zeros((n, n))]])
    eps = np.concatenate([np.full(n, eps_hot), np.full(n, eps_float)])
    area = np.concatenate([a1, a2])
    ext = SIGMA * t_ext ** 4 * (1.0 - f.sum(axis=1))

    # J = eps sigma T^4 + (1 - eps) H,  H = F J + ext. The system is linear in the emissive
    # powers, so the floating disk's net absorption is linear in its sigma T^4: solve twice.
    a = np.eye(2 * n) - (1.0 - eps)[:, None] * f

    def net_absorbed(eb_float):
        eb = np.concatenate([np.full(n, SIGMA * t_hot ** 4), np.full(n, eb_float)])
        j = np.linalg.solve(a, eps * eb + (1.0 - eps) * ext)
        h = f @ j + ext
        return float(np.sum((area * eps * (h - eb))[n:]))

    q0, q1 = net_absorbed(0.0), net_absorbed(1.0)
    return (-q0 / (q1 - q0) / SIGMA) ** 0.25
