"""Machine-readable run manifest (PHASE1_CHAMBER_PLAN.md sections 6-7)."""

import hashlib
import json
import platform
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from . import __version__

LABELS = ("synthetic", "representative_chamber", "proposed_machine")
VALIDATION_STATUSES = ("not_validated", "verified_numerically", "validated_against_published_case")


def canonical_hash(obj):
    """SHA-256 of a JSON-serialisable object with sorted keys."""
    text = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=_jsonable)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _jsonable(x):
    if isinstance(x, np.ndarray):
        return x.tolist()
    if isinstance(x, np.generic):
        return x.item()
    raise TypeError(f"not JSON serialisable: {type(x).__name__}")


def _git_commit(root):
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True,
                             text=True, timeout=10)
        dirty = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True,
                               text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return out.stdout.strip() + ("-dirty" if dirty.stdout.strip() else "")


def build_manifest(run_id, *, label, inputs, outputs, validation_status="not_validated",
                   warnings=(), disabled_physics=()):
    """Assemble a run manifest. `label` and `validation_status` are restricted vocabularies."""
    if label not in LABELS:
        raise ValueError(f"label must be one of {LABELS}")
    if validation_status not in VALIDATION_STATUSES:
        raise ValueError(f"validation_status must be one of {VALIDATION_STATUSES}")
    root = Path(__file__).resolve().parents[2]
    return {
        "schema_version": "0.1",
        "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "label": label,
        "validation_status": validation_status,
        "package_version": __version__,
        "git_commit": _git_commit(root),
        "python": platform.python_version(),
        "numpy": np.__version__,
        "platform": platform.platform(),
        "inputs_sha256": canonical_hash(inputs),
        "inputs": inputs,
        "outputs": outputs,
        "disabled_physics": list(disabled_physics),
        "warnings": list(warnings),
    }


def write_manifest(manifest, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, default=_jsonable) + "\n", encoding="utf-8")
    return path
