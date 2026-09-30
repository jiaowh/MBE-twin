import json

import numpy as np
import pytest

from mbe_twin.manifest import build_manifest, canonical_hash, write_manifest
from mbe_twin.metrics import radial_ring_weights, radial_uniformity, weighted_stats


def test_ring_weights_cover_disk():
    rho = np.linspace(0.0, 0.1, 51)
    assert radial_ring_weights(rho, 0.1).sum() == pytest.approx(np.pi * 0.01, rel=1e-14)


def test_uniform_profile_has_zero_nonuniformity():
    rho = np.linspace(0.0, 0.1, 51)
    s = radial_uniformity(np.full_like(rho, 7.0), rho, 0.1)
    assert s["mean"] == pytest.approx(7.0)
    assert s["std_pct"] == pytest.approx(0.0, abs=1e-12)
    assert s["half_range_pct"] == 0.0


def test_linear_profile_area_mean():
    # Area mean of f = rho over a disk of radius R is 2R/3.
    rho = np.linspace(0.0, 0.1, 4001)
    s = radial_uniformity(rho, rho, 0.1)
    assert s["mean"] == pytest.approx(2.0 * 0.1 / 3.0, rel=1e-6)
    assert s["half_range_pct"] == pytest.approx(100.0 * 0.1 / (2.0 * s["mean"]))


def test_edge_exclusion_drops_outer_samples():
    rho = np.linspace(0.0, 0.1, 101)
    profile = np.where(rho > 0.097, 2.0, 1.0)
    assert radial_uniformity(profile, rho, 0.1, edge_exclusion=0.003)["half_range_pct"] == 0.0
    assert radial_uniformity(profile, rho, 0.1)["half_range_pct"] > 0.0


def test_weighted_stats_ignores_zero_weights():
    s = weighted_stats([1.0, 100.0, 1.0], [1.0, 0.0, 1.0])
    assert s["max"] == 1.0


def test_manifest_hash_is_order_independent_and_labels_restricted(tmp_path):
    assert canonical_hash({"a": 1, "b": [1, 2]}) == canonical_hash({"b": [1, 2], "a": 1})
    with pytest.raises(ValueError):
        build_manifest("r", label="validated_twin", inputs={}, outputs={})
    with pytest.raises(ValueError):
        build_manifest("r", label="synthetic", inputs={}, outputs={}, validation_status="validated")
    m = build_manifest("r1", label="representative_chamber", inputs={"x": np.float64(1.0)},
                       outputs={"y": np.arange(3)})
    path = write_manifest(m, tmp_path / "m.json")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["label"] == "representative_chamber"
    assert loaded["outputs"]["y"] == [0, 1, 2]
    assert loaded["inputs_sha256"] == canonical_hash({"x": 1.0})
