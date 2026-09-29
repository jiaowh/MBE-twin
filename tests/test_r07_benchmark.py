"""R07 (Gericke 1991) digitized data: provenance, and model regression on the fill-level series."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from mbe_twin.crucible import Crucible, next_event_flux, simulate

ROOT = Path(__file__).resolve().parents[1]
DATA = json.loads((ROOT / "data/benchmarks/r07_gericke1991.json").read_text(encoding="utf-8"))


def test_digitized_data_provenance():
    pdf = ROOT / DATA["source_pdf"]
    assert hashlib.sha256(pdf.read_bytes()).hexdigest() == DATA["source_sha256"]
    assert DATA["provenance"] == "digitized"
    for panel in DATA["panels"].values():
        assert panel["locator"] and panel["calibration"]["max_tick_residual_px"] < 4.0
        assert 0.0 < panel["estimated_error_y"] < 0.015


@pytest.mark.parametrize("ld, max_rms", [(0.5, 0.02), (1.0, 0.02)])
def test_crucible_model_reproduces_shallow_fill_profiles(ld, max_rms):
    # Conical crucible, D = 16.5 mm, 2.6 deg taper, plane at 115 mm (R07 Fig. 3, ~0.35 A/s).
    c = DATA["panels"]["fig3"]["curves"][f"L/D={ld:g}"]
    x, y = np.array(c["x_mm"]), np.array(c["y"])
    y = y / np.interp(0.0, x, y)
    keep = np.abs(x) <= 45.0
    ev = simulate(Crucible(0.00825, ld * 0.0165, taper_half_angle=np.radians(2.6)), 60_000, rng=5)
    pts = np.stack([x[keep] / 1000, np.zeros(keep.sum()), np.full(keep.sum(), 0.115)], axis=1)
    f = next_event_flux(ev, pts, (0.0, 0.0, -1.0))
    f0 = next_event_flux(ev, [[0.0, 0.0, 0.115]], (0.0, 0.0, -1.0))[0]
    rms = np.sqrt(np.mean((f / f0 - y[keep]) ** 2))
    assert rms < max_rms


def _profile(panel):
    c = next(iter(DATA["panels"][panel]["curves"].values()))
    x, y = np.array(c["x_mm"]), np.array(c["y"])
    order = np.argsort(x)
    x, y = x[order], y[order]
    return x, y / np.interp(0.0, x, y)


def test_fig7_distance_transfer_follows_taper_apex_not_orifice():
    # R07 Fig. 7: the 265 mm profile is the 115 mm profile scaled about a point near the
    # taper apex (182 mm below the orifice), not about the orifice. Guards the digitization.
    x1, y1 = _profile("fig7_115")
    x2, y2 = _profile("fig7_265")
    keep = np.abs(x2) <= 45.0

    def rms(depth):
        scaled = x2[keep] * (115.0 + depth) / (265.0 + depth)
        return np.sqrt(np.mean((np.interp(scaled, x1, y1) - y2[keep]) ** 2))

    apex = 8.25 / np.tan(np.radians(2.6))
    assert rms(apex) < 0.02 < 0.04 < rms(0.0)
