"""Provenance of the versioned study records: which committed code each one ran, and what changed since.

For every manifest in data/runs/studies/*.json, each recorded source hash (manifest
source_sha256, LF-normalized as manifest.py hashes) is compared with the current file. Where
they differ, the file's git history is searched for the commit whose version has the recorded
hash, and the commits that changed the file after it are listed. Hand-written impact notes
(IMPACT below) say whether a later change can alter the record's numbers. Each note is a review
of one file version: it applies only while the file is at the version it was written against
(`current`, the first 12 hex digits of its LF-normalized SHA-256) and, where it says so, only to
the named records and recorded versions. A later edit of the file is therefore "not reviewed"
again until the note is re-read and re-pinned; a mismatch without an applicable note is reported
as "not reviewed". `--hashes` prints the current pins to paste after a review. The result is written next to the records as
data/runs/studies/PROVENANCE.md, so that it is found with them rather than in commit messages.

Besides source_sha256, a record can depend on data tables it names only under inputs (the scattered-arrival
factor tables: inputs.scattered_tables_sha256 and inputs.scattered_plume_tables_sha256; the Ga DSMC summaries:
inputs.ga_records_sha256, also under inputs.chamber_provenance for twin runs), and records run
with --scattered gas+plume before 2026-10-03 loaded the plume tables without recording them. Both are checked
like sources (see recorded_hashes): an input hash against the current file, and an unrecorded plume dependency
against the hashes stored by the comparison record the study read, which used the same files at the time. A
plume dependency that cannot be traced either way is reported as not reviewed.

The records themselves are never modified.

Usage: python scripts/record_provenance.py [--check]   (--check: exit 1 if a mismatch has no note)
"""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STUDIES = ROOT / "data/runs/studies"

# file -> reviews: {"current": 12-hex version of the file the note was written against, "note": why the changes up
# to that version do or do not alter older records, optional "records": [record names] and "recorded": [12-hex
# recorded versions] the note is limited to}. Values given as plain strings are written as {"note": ...} reviews
# and pinned in PINS below.
SRC_ONLY = (" Later change (2026-10-03 audit) only lists the scattered-arrival tables it reads (layout_comparison.scatter_sources) "
            "among the manifest sources; the computation is unchanged.")
IMPACT = {
    "src/mbe_twin/aperture.py": "Later changes only add optional arguments (`axis`, then `centre`) whose defaults reproduce the "
                                "earlier sources exactly (tests/test_aperture.py).",
    "scripts/nitrogen_aim_tolerance.py": "Input validation only: the script now reads the versioned scans and stops when a requested "
                                         "plate's record is missing; the tilt calculation is unchanged (commit 092d201).",
    "src/mbe_twin/heater.py": "Later change adds the optional platen; without it the model is the earlier one exactly "
                              "(regression test in tests/test_heater.py).",
    "scripts/heater_zones.py": "Later changes add the platen variations and optional heater limits to optimize(); without "
                               "limits the iteration is the earlier one (recorded heater_zones ranges reproduce bit for bit). The later "
                               "at_limit(), at_reading() and centre_reading() are new functions; at_mean() now calls at_reading() with "
                               "the wafer mean as the reading, the same secant iteration on the same quantity; optimize() is unchanged.",
    "scripts/growth_window.py": "Later change adds the --held option (centre-flux-held Ga maps); the default path is unchanged.",
    "src/mbe_twin/beam.py": "Later change adds the cylinder and holder-lip occluders and an optional background-gas mean free "
                            "path; without one the flux is exactly the earlier one (tests/test_beam.py, zero-pressure regression).",
    "scripts/layout_comparison.py": [
        {"records": ["layout_comparison.json"],
         "note": "CHANGES RESULTS. After the 2026-10-01 project audit the Ga centre flux is held absolute (it followed each "
                 "state's N before), every heater state is held to the element limit, and the N output is bounded by a coupled "
                 "feed/pressure balance; after the 2026-10-02 audit a state is valid only if the rate actually grown reaches the "
                 "target. The six-layout record layout_comparison.json (6aca3b3) is superseded for B and C by "
                 "layout_comparison_bc.json; its A, C-Ga54, R0 and D window margins were computed with the old Ga protocol."},
        {"records": ["nitrogen_aim_pressure.json", "nitrogen_aim_bigplate.json", "layout_resolution_check.json",
                     "nitrogen_rate_limits.json"],
         "note": "These records use operating_point, heater_states, att_at, area_mean, plate_knudsen, the Ga map helpers and "
                 "LIMITS['1473 K element'] (layout_resolution_check also evaluate's thickness; nitrogen_rate_limits also "
                 "P_GRID), all unchanged since their runs (function-level comparison with 353cf47 and d0f136d). The later "
                 "changes are the per-state balance in evaluate/solve_states (d0f136d), and the on-target validity label, "
                 "RATE_TOL and --kn-valid (2026-10-02), which do not change thickness, operating points or maps."},
        {"note": "Later change (2026-10-03) adds the --scattered option (scatter_factors, with_scattered, comparison_record; "
                 "per-speed attenuation tables inside the scenario loop). With the default --scattered none the tables "
                 "are the earlier ones: layout_comparison_bc.json, heater_robustness.json, operating_optimum.json and "
                 "operating_cold_limit.json reproduce bit for bit (checked 2026-10-03). Records that only import "
                 "constants or helpers (P_GRID, att_at, operating_point, ...) are unaffected. The 2026-10-03 audit changes "
                 "add scatter_sources (manifest sources only) and a check that stops a gas+plume run whose plume tables do "
                 "not bracket the feed limit; neither changes a number of a run that completes."}],
    "scripts/layout_feasibility.py": "CHANGES RESULTS. Clearances became certified lower bounds (disk samples less their covering "
                                     "radius, refined where the bound is near the margin), then bounds over the continuous "
                                     "shutter motion (2026-10-02), and now include flange/body, flange/blade and simultaneous "
                                     "blade/blade pairs. The six-layout record layout_feasibility.json is superseded for B, C, "
                                     "B-p and C-p by layout_feasibility_bc.json.",
    "src/mbe_twin/layout.py": "Later changes add disk_cover_radius, the disk distance bounds and the swept-motion bound "
                              "(shutter_reach, sweep_step_bound, swept_lower_bound); disk_to_disk now finds the nearest sample "
                              "with a k-d tree (the same minimum distance). SourcePort and the other functions are unchanged "
                              "(tests/test_layout.py); the clearance results this changes are in layout_feasibility.json's own note.",
    "data/design/design_envelope.json": "Later changes add the nitrogen_source and acceptance blocks, a note on the output "
                                        "bound, the B-p and C-p layouts and wider pumping, feed and conversion scenarios; every "
                                        "input the earlier records read is unchanged.",
    "scripts/nitrogen_aim_study.py":"Later changes add command-line options (--aspects/--offsets/--angles) and record fields; "
                                     "the grid evaluation and seeds of the default run are unchanged.",
    "scripts/heater_robustness.py": "Later change (2026-10-03) adds --scattered (scattered-arrival factors, per pumping speed) and --out; with the default --scattered none the record reproduces bit for bit (checked 2026-10-03)." + SRC_ONLY,
    "scripts/operating_optimum.py": "Later change (2026-10-03) adds --scattered; load_inputs takes the factors and the pumping speed, and inputs are keyed by layout and speed. With the default --scattered none operating_optimum.json reproduces bit for bit (checked 2026-10-03)." + SRC_ONLY,
    "scripts/operating_cold_limit.py": "Later change (2026-10-03) adds --scattered, --pyrometer-bias (default 2 K, the earlier controllers) and --t-max (default 760 C, the earlier range); with the defaults operating_cold_limit.json reproduces bit for bit (checked 2026-10-03)." + SRC_ONLY,
    "scripts/nitrogen_aim_pressure.py": "Later change (2026-10-03) adds --scattered and --factor-layout to the --combine evaluation (evaluate takes an optional factor); without them nitrogen_aim_pressure.json and nitrogen_aim_bigplate.json reproduce bit for bit (checked 2026-10-03)." + SRC_ONLY,
    "scripts/nitrogen_rate_limits.py": "Later change (2026-10-03) applies the scattered-arrival factors when the comparison record was run with --scattered; for the default record (scattered none) the attenuation is the earlier one and nitrogen_rate_limits.json reproduces bit for bit (checked 2026-10-03)." + SRC_ONLY,
    "scripts/realizable_controller.py": "Later changes (2026-10-05) add options whose defaults reproduce the recorded "
                                        "runs: --rate-um-h (default 1 um/h), --pointing-residual, --aim-maps/--aim-mm, "
                                        "--heater-control (default single), --dump-t, plus per-state factor bookkeeping; "
                                        "--pointing-residual 0.8 reproduced the 1460 K record (95.2 %, 1.53 %). The follow-up audit "
                                        "change (2026-10-05) only adds aim-map and optional-module hashes to the "
                                        "manifest. A later option, --n-tables (default off), substitutes an aim's own pointing and attenuation tables.",
    "scripts/scattered_plume_tables.py": "Later change (2026-10-03 audit) covers the grid pressures through the first one whose "
                                         "feed reaches the 35 sccm limit and adds --extend (reuses a record's covered entries); "
                                         "the covered entries of the earlier records are computed exactly as before.",
    "src/mbe_twin/sparta.py": "Later change (2026-10-03) lets wsl_path return a POSIX path unchanged when run inside WSL; on "
                              "Windows (where every record ran) the path is the earlier one.",
    "data/runs/studies/layout_comparison_bc.json": [
        {"records": ["nitrogen_rate_limits.json"],
         "note": "Regenerated after the 2026-10-02 audit (on-target validity label). The operating points and nominal values "
                 "this record reads are unchanged, and the keyed map caches it loads were rebuilt under new keys with identical "
                 "contents (checked array by array)."}],
}
PINS = {   # reviewed 2026-10-02
    "scripts/realizable_controller.py": "76eca57f2871",  # reviewed 2026-10-05
    "scripts/nitrogen_aim_pressure.py": "3ed2958db5f2",  # reviewed 2026-10-03
    "scripts/nitrogen_rate_limits.py": "29392adf050d",  # reviewed 2026-10-03
    "scripts/heater_robustness.py": "7f545f5d98da",  # reviewed 2026-10-03
    "scripts/operating_optimum.py": "4d5b02c42380",  # reviewed 2026-10-03
    "scripts/operating_cold_limit.py": "07b9707d9806",  # reviewed 2026-10-03
    "src/mbe_twin/sparta.py": "a293265e2ca3", "scripts/scattered_plume_tables.py": "e6e482fe953c",  # reviewed 2026-10-03
    "src/mbe_twin/aperture.py": "08ff8b237847", "scripts/nitrogen_aim_tolerance.py": "30922a1a37e6",
    "src/mbe_twin/heater.py": "b24c80baae47", "scripts/heater_zones.py": "2cf7e07a02dc",
    "scripts/growth_window.py": "e43c637528a9", "src/mbe_twin/beam.py": "90a90503e0a5",
    "scripts/layout_feasibility.py": "51c27c9311c3", "src/mbe_twin/layout.py": "489e036db487",
    "data/design/design_envelope.json": "e1d2e14d6e22", "scripts/nitrogen_aim_study.py": "16c682df1ad2",
}
for _r in IMPACT["scripts/layout_comparison.py"]:
    _r["current"] = "43ae5196080f"   # re-reviewed 2026-10-03 (audit changes)
for _r in IMPACT["data/runs/studies/layout_comparison_bc.json"]:
    _r["current"] = "e57fc0415cd3"


def reviews(path):
    v = IMPACT.get(path, [])
    if isinstance(v, str):
        return [{"note": v, "current": PINS.get(path)}]
    return v if isinstance(v, list) else [v]


def applicable_note(path, current, record, recorded):
    """The note of the first review that covers this record's mismatch at the file's current version, else None."""
    for r in reviews(path):
        if r.get("current") != current[:12]:
            continue
        if "records" in r and record not in r["records"]:
            continue
        if "recorded" in r and recorded[:12] not in r["recorded"]:
            continue
        return r["note"]
    return None


# input-hash fields -> {file: recorded hash}
INPUT_HASHES = {
    "scattered_tables_sha256": lambda v: {"data/runs/studies/scattered_tables.json": v},
    "scattered_plume_tables_sha256": lambda v: {f"data/runs/studies/scattered_plume_tables_{k}.json": h for k, h in v.items()},
    # Ga DSMC summaries a study reloads (paths relative to data/runs/sparta_ga; audit 2026-10-05, finding 3)
    "ga_records_sha256": lambda v: {f"data/runs/sparta_ga/{k}": h for k, h in v.items()},
    # aim maps a realizable-controller run read (paths relative to the repository root; audit follow-up 2026-10-05)
    "aim_maps_sha256": lambda v: dict(v),
}
PLUME_PREFIX = "data/runs/studies/scattered_plume_tables_"
UNTRACED = "untraced"


def recorded_hashes(m):
    """{file: recorded hash} a record depends on: its sources, input-hash fields, and (for gas+plume records that
    did not record them) the plume tables, traced through the comparison record it read; UNTRACED if none."""
    out = dict(m.get("source_sha256", {}))
    inputs = m.get("inputs", {})
    # twin runs carry their chamber definition's provenance one level down
    for scope in (inputs, inputs.get("chamber_provenance") or {}):
        for key, expand in INPUT_HASHES.items():
            if isinstance(scope.get(key), (str, dict)) and scope[key]:
                for path, h in expand(scope[key]).items():
                    out.setdefault(path, h)
    if inputs.get("scattered") == "gas+plume" and not any(p.startswith(PLUME_PREFIX) for p in out):
        traced = False
        for path in list(out):
            if path.startswith("data/runs/studies/layout_comparison") and (ROOT / path).exists():
                hashes = json.loads((ROOT / path).read_text(encoding="utf-8"))["inputs"].get("scattered_plume_tables_sha256")
                if hashes:
                    traced = True
                    for k, h in hashes.items():
                        out.setdefault(f"{PLUME_PREFIX}{k}.json", h)
        if not traced:
            for f in sorted((ROOT / "data/runs/studies").glob("scattered_plume_tables_*.json")):
                out.setdefault(f.relative_to(ROOT).as_posix(), UNTRACED)
    return out


def sha_lf(data):
    return hashlib.sha256(data.replace(b"\r\n", b"\n")).hexdigest()


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True).stdout


def history(path):
    """(commit, subject, sha256 of the file at that commit), newest first."""
    out = []
    for line in git("log", "--format=%H%x09%s", "--", path).decode("utf-8", "replace").splitlines():
        h, subject = line.split("\t", 1)
        try:
            blob = git("show", f"{h}:{path}")
        except subprocess.CalledProcessError:
            continue
        out.append((h, subject, sha_lf(blob)))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--hashes", action="store_true", help="print each reviewed file's current 12-hex version and stop")
    args = ap.parse_args()
    if args.hashes:
        for path in sorted(IMPACT):
            f = ROOT / path
            print(f"{path}: {sha_lf(f.read_bytes())[:12] if f.exists() else 'missing'}")
        return
    lines = ["# Provenance of the study records",
             "",
             "Generated by `scripts/record_provenance.py`; do not edit by hand. Each record in this directory stores the "
             "SHA-256 of the source files that produced it. Where a file has changed since, the table names the commit "
             "whose version matches the recorded hash and the later commits that touched the file, with a note on whether "
             "the change can alter the record's numbers. The records are kept unchanged.",
             "",
             "| Record | File | Recorded version | Changed since by | Effect on the record |",
             "|---|---|---|---|---|"]
    unreviewed = []
    clean = []
    for rec in sorted(STUDIES.glob("*.json")):
        m = json.loads(rec.read_text(encoding="utf-8"))
        mismatches = []
        # a summary record keeps each constituent run's dependencies separately (inputs.constituents); each is checked
        # as its own set, labelled record [run], so differing versions across runs are not merged
        sets = [(rec.name, recorded_hashes(m))]
        for run, deps in (m.get("inputs", {}).get("constituents") or {}).items():
            sets.append((f"{rec.name} [{run}]", recorded_hashes({"source_sha256": deps.get("source_sha256", {}),
                                                                 "inputs": deps})))
        for label, path, recorded in ((lb, p_, h) for lb, hs in sets for p_, h in hs.items()):
            f = ROOT / path
            current = sha_lf(f.read_bytes()) if f.exists() else "missing"
            if current == recorded:
                continue
            hist = history(path)
            match = next((i for i, (_, _, s) in enumerate(hist) if s == recorded), None)
            if recorded == UNTRACED:
                version, later = "not recorded (loaded without a hash)", []
            elif match is None:
                version, later = "no committed version (uncommitted working copy at run time)", hist[:1]
            else:
                version, later = f"`{hist[match][0][:7]}`", hist[:match]
            changed = "; ".join(f"`{h[:7]}` {s}" for h, s, _ in reversed(later)) or "-"
            note = applicable_note(path, current, rec.name, recorded)
            if note is None:
                unreviewed.append(f"{label}: {path}")
                note = "**not reviewed**"
            mismatches.append(f"| {label} | `{path}` | {version} | {changed} | {note} |")
        if mismatches:
            lines.extend(mismatches)
        else:
            clean.append(rec.name)
    lines += ["", "Records whose every source file is unchanged since the run: " + (", ".join(clean) or "none") + "."]
    (STUDIES / "PROVENANCE.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))
    if unreviewed:
        print("\nNot reviewed: " + ", ".join(unreviewed), file=sys.stderr)
        if args.check:
            sys.exit(1)


if __name__ == "__main__":
    main()
