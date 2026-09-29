"""Elmer installation and V02 conduction benchmark (skipped when Elmer is not installed)."""

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
