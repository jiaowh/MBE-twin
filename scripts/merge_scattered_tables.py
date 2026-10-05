"""Merge split runs of scripts/scattered_tables.py into one factor record.

scripts/scattered_tables.py runs the N layouts and Ga one after another. To use several cores, it
is run unchanged in parts: one per N layout (--layouts <L> with a token Ga sample) and one for Ga
(--layouts B with a token N sample). This script takes each layout's N factors from its N part and
the Ga factors from the Ga part, checks that the parts share the pressure grid, radii, particle
counts and code, and writes the combined record in the format scripts/layout_comparison.py reads.
Each part's manifest summary (run id, time, commit, source hashes, inputs) is kept in the record.

The parts all use the script's fixed seed, so their random streams start alike: noise in different
layouts' factors is correlated, which does not bias any factor.

Usage: python scripts/merge_scattered_tables.py [--parts results/scattered_tables_part_N_B ... results/scattered_tables_part_Ga]
                                                [--out results/scattered_tables]
"""

import argparse
import json
from pathlib import Path

import numpy as np

from mbe_twin.manifest import build_manifest, write_manifest

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PARTS = ["results/scattered_tables_part_N_B", "results/scattered_tables_part_N_B-p",
                 "results/scattered_tables_part_N_B-L", "results/scattered_tables_part_Ga"]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--parts", nargs="+", default=DEFAULT_PARTS)
    ap.add_argument("--out", default="results/scattered_tables")
    args = ap.parse_args()
    parts = {p: json.loads((ROOT / p / "manifest.json").read_text(encoding="utf-8")) for p in args.parts}
    ga_parts = [p for p, m in parts.items() if m["inputs"]["ga_particles"] > m["inputs"]["n_particles"]]
    n_parts = [p for p in parts if p not in ga_parts]
    if len(ga_parts) != 1:
        raise SystemExit(f"merge_scattered_tables: expected one Ga part, found {ga_parts}")
    ref = parts[ga_parts[0]]
    for p, m in parts.items():
        for key in ("p_grid_Pa", "rho_m", "chamber", "species", "ga_cos_n", "variants_gamma", "ga_d", "batches", "seed"):
            if m["inputs"][key] != ref["inputs"][key]:
                raise SystemExit(f"merge_scattered_tables: {p} differs from the Ga part in {key}")
        if m["source_sha256"] != ref["source_sha256"]:
            raise SystemExit(f"merge_scattered_tables: {p} ran different code from the Ga part")
    n_particles = {parts[p]["inputs"]["n_particles"] for p in n_parts}
    if len(n_particles) != 1:
        raise SystemExit(f"merge_scattered_tables: N parts used different particle counts {n_particles}")
    factors, diag, layouts = {"N": {}, "Ga": ref["outputs"]["factors"]["Ga"]}, {"N": {}, "Ga": ref["outputs"]["diagnostics"]["Ga"]}, []
    for p in n_parts:
        for name in parts[p]["inputs"]["layouts"]:
            if name in factors["N"]:
                raise SystemExit(f"merge_scattered_tables: layout {name} in more than one N part")
            factors["N"][name] = parts[p]["outputs"]["factors"]["N"][name]
            diag["N"][name] = parts[p]["outputs"]["diagnostics"]["N"][name]
            layouts.append(name)
    summary = {p: {k: m[k] for k in ("run_id", "created_utc", "git_commit", "source_sha256", "inputs_sha256")}
               | {"layouts": m["inputs"]["layouts"], "n_particles": m["inputs"]["n_particles"],
                  "ga_particles": m["inputs"]["ga_particles"], "used_for": "Ga" if p in ga_parts else "N"}
               for p, m in parts.items()}
    manifest = build_manifest(
        "scattered_tables", label="representative_chamber", validation_status="not_validated",
        inputs={**{k: ref["inputs"][k] for k in ("batches", "chamber", "species", "ga_cos_n", "variants_gamma", "p_grid_Pa",
                                                  "rho_m", "ga_d", "collision_diameters_m", "gas_temperature_K", "seed")},
                "layouts": layouts, "n_particles": n_particles.pop(), "ga_particles": ref["inputs"]["ga_particles"],
                "parts": summary},
        outputs={"rho_m": np.asarray(ref["outputs"]["rho_m"]), "p_grid_Pa": ref["outputs"]["p_grid_Pa"], "factors": factors,
                 "diagnostics": diag},
        sources=[Path(__file__), ROOT / "scripts/scattered_tables.py", ROOT / "src/mbe_twin/scattering.py",
                 ROOT / "src/mbe_twin/crucible.py", ROOT / "src/mbe_twin/vacuum.py", ROOT / "data/design/design_envelope.json"],
        warnings=ref["warnings"] + ["Merged from split runs of scripts/scattered_tables.py (inputs.parts)"],
        disabled_physics=ref["disabled_physics"])
    print(f"Wrote {write_manifest(manifest, Path(args.out) / 'manifest.json')}")


if __name__ == "__main__":
    main()
