"""Checks on the sourced vapour-species and collision-size estimates (scripts/vapour_species.py)."""

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("vapour_species", ROOT / "scripts" / "vapour_species.py")
vs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(vs)


def test_kubaschewski_bi2_fraction_at_r07_states():
    rows = {r["state"]: r for r in vs.bismuth()}
    # Dimer fraction falls slowly with temperature over R07's range.
    assert [round(rows[s]["x_Bi2"], 3) for s in ("0.35 A/s", "3.5 A/s", "11 A/s")] == [0.324, 0.300, 0.286]
    for r in rows.values():
        x = r["x_Bi2"]
        assert r["atom_flux_gain_at_fixed_p"] == pytest.approx(1 + (2 ** 0.5 - 1) * x)


def test_noble_gas_hard_sphere_diameters_and_c6_scaling():
    d = vs.dispersion()
    hs = {e: v * 1e10 for e, v in d["noble_hs_d_273K_m"].items()}
    assert hs == pytest.approx({"Ne": 2.575, "Ar": 3.644, "Kr": 4.157, "Xe": 4.898}, abs=2e-3)
    # The scaling reproduces every noble gas within 5 % from any anchor.
    for row in d["scaling_test_m"].values():
        for e, v in row.items():
            assert v * 1e10 == pytest.approx(hs[e], rel=0.05)


def test_ga_diameter_bounds_and_dimer_fraction():
    d = vs.dispersion()
    ga = d["metals"]["Ga"]
    assert 3.8e-10 < ga["d_dispersion_min_m"] < ga["d_dispersion_max_m"] < 4.2e-10
    lo, hi = d["ga_d_from_bi_transfer_m"]
    assert 7.4e-10 < lo < hi < 9.7e-10
    ga2 = vs.gallium_dimer()
    # A 3Pi_u ground state (degeneracy 6) plus low-lying states: the measured factor exceeds 6.
    assert 6 < ga2["g_eff"]["min"] < ga2["g_eff"]["median"] < 10
    assert max(r["x_Ga2"] for r in ga2["cell"]) < 1e-3
