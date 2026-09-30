"""Elmer installation and V02 conduction benchmark (skipped when Elmer is not installed)."""

import shutil
from pathlib import Path

import numpy as np
import pytest

from mbe_twin.elmer import elmer_home, read_saveline, run_case

CASES = Path(__file__).resolve().parents[1] / "cases" / "verification"
pytestmark = pytest.mark.skipif(elmer_home() is None, reason="Elmer not installed (set ELMER_HOME)")


def test_v02_slab_with_heat_source_matches_exact_solution(tmp_path):
    work = run_case(CASES / "elmer_v02_slab", tmp_path / "run")
    line = read_saveline(work)
    x, t = line["coordinate 1"], line["temperature"]
    exact = 300.0 + 100.0 * x + 1000.0 / (2.0 * 10.0) * x * (1.0 - x)
    assert len(x) >= 21
    assert np.max(np.abs(t - exact)) < 1e-6


@pytest.mark.parametrize("eps_hot, eps_float", [(1.0, 1.0), (0.8, 0.3)])
def test_v03_diffuse_gray_radiation_between_coaxial_disks(tmp_path, eps_hot, eps_float):
    # Floating disk (insulated back and rim) facing a 1200 K disk, open to 300 K. Black
    # surfaces have the exact isothermal answer F12 T1^4 + (1 - F12) Text^4; gray surfaces
    # use the independent ring radiosity solution. The Elmer disk is not exactly isothermal
    # (spread about 0.4 K), so its area-weighted T^4 mean is compared, within 0.5 K.
    from mbe_twin.radiation import disk_view_factor, floating_disk_temperature

    case = tmp_path / "case"
    shutil.copytree(CASES / "elmer_v03_disks", case)
    sif = case / "case.sif"
    text = sif.read_text().replace("$eps1 = 1.0", f"$eps1 = {eps_hot}").replace(
        "$eps2 = 1.0", f"$eps2 = {eps_float}")
    sif.write_text(text)
    line = read_saveline(run_case(case, tmp_path / "run"))
    r, t = line["coordinate 1"], line["temperature"]
    o = np.argsort(r)
    r, t = r[o], t[o]
    w = np.diff(np.concatenate(([0.0], 0.5 * (r[1:] + r[:-1]), [r[-1]])) ** 2)
    t_mean = (np.sum(w * t ** 4) / np.sum(w)) ** 0.25
    ref = floating_disk_temperature(0.05, 0.02, 1200.0, 300.0, eps_hot, eps_float, n_rings=400)
    if eps_hot == eps_float == 1.0:
        f = float(disk_view_factor(0.05, 0.05, 0.02))
        assert ref == pytest.approx((f * 1200.0 ** 4 + (1 - f) * 300.0 ** 4) ** 0.25, abs=1e-6)
    assert t_mean == pytest.approx(ref, abs=0.5)
