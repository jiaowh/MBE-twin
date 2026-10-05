"""Script-level checks: Python 3.11 compatibility and command-line defaults."""

import importlib.util
import io
import sys
import tokenize
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCES = sorted((ROOT / "scripts").glob("*.py")) + sorted((ROOT / "src").rglob("*.py"))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.skipif(sys.version_info < (3, 12), reason="needs the PEP 701 tokenizer to see nested f-string tokens")
@pytest.mark.parametrize("path", SOURCES, ids=lambda p: p.name)
def test_no_fstring_reuses_its_own_quote(path):
    # Python 3.11 (the stated minimum) rejects f"{d["k"]}"; 3.12 accepts it, so it slips through
    # when tests run on 3.12. Nested string tokens must not start with the enclosing quote.
    open_quotes = []
    for tok in tokenize.generate_tokens(io.StringIO(path.read_text(encoding="utf-8")).readline):
        if tok.type == tokenize.FSTRING_START:
            q = tok.string.lstrip("fFrRbB")
            if open_quotes:
                assert not q.startswith(open_quotes[-1][0]), f"{path.name}:{tok.start[0]} nested f-string reuses quote"
            open_quotes.append(q)
        elif tok.type == tokenize.FSTRING_END:
            open_quotes.pop()
        elif tok.type == tokenize.STRING and open_quotes:
            body = tok.string.lstrip("rRbBuU")
            assert not body.startswith(open_quotes[-1][0]), f"{path.name}:{tok.start[0]} string reuses f-string quote"


def test_sparta_ga_default_run_name():
    ga = _load("sparta_ga")
    cfg = {"fill_m": 0.12, "diameter_m": 8e-10, "rate_um_h": 1.0, "mode": "hold", "polar_deg": 58.0}
    assert ga.default_run_name(cfg) == "fill120_d8.00_1umh_hold_58deg"
    assert ga.default_run_name({**cfg, "diameter_m": None, "polar_deg": 46.0}) == "fill120_fm_1umh_hold"


FAKE_JOB = """
import sys
from pathlib import Path
args = sys.argv[1:]
out = Path(args[args.index("--out") + 1])
out.mkdir(parents=True, exist_ok=True)
if args[0] == "fail":
    sys.exit(3)
(out / "summary.json").write_text("{}")
"""


def _batch(tmp_path, jobs, *extra):
    import json
    import subprocess

    (tmp_path / "fake.py").write_text(FAKE_JOB)
    spec = tmp_path / "b.json"
    spec.write_text(json.dumps({"script": str(tmp_path / "fake.py"), "jobs": jobs}))
    return subprocess.run([sys.executable, str(ROOT / "scripts/sparta_batch.py"), str(spec),
                           "--results", str(tmp_path / "res"), "--workers", "2", "--min-free-gb", "0", "--settle", "0", *extra],
                          capture_output=True, text=True)


def test_batch_reports_failures_and_incomplete_runs(tmp_path):
    jobs = [{"name": "good", "args": ["ok"]}, {"name": "bad", "args": ["fail"]}]
    r = _batch(tmp_path, jobs)
    assert r.returncode == 1 and "bad: FAILED" in r.stdout and "good: ok" in r.stdout
    # the failed run left a directory without summary.json: reported, not skipped as done
    r = _batch(tmp_path, jobs)
    assert r.returncode == 1 and "good: skipped (complete)" in r.stdout and "bad: INCOMPLETE" in r.stdout
    # explicit recovery: the incomplete directory is moved aside and the job reruns
    r = _batch(tmp_path, [{"name": "good", "args": ["ok"]}, {"name": "bad", "args": ["ok"]}], "--retry-incomplete")
    assert r.returncode == 0 and "bad: ok" in r.stdout
    assert list((tmp_path / "res" / "b").glob("bad.failed-*"))


def test_batch_admission_waits_for_settle(tmp_path):
    import json
    import subprocess

    job = """
import sys, time
from pathlib import Path
args = sys.argv[1:]
out = Path(args[args.index("--out") + 1]); out.mkdir(parents=True, exist_ok=True)
(out / "start").write_text(repr(time.time())); time.sleep(3); (out / "summary.json").write_text("{}")
"""
    (tmp_path / "slow.py").write_text(job)
    spec = tmp_path / "b.json"
    spec.write_text(json.dumps({"script": str(tmp_path / "slow.py"),
                                "jobs": [{"name": "a", "args": []}, {"name": "b", "args": []}]}))
    r = subprocess.run([sys.executable, str(ROOT / "scripts/sparta_batch.py"), str(spec), "--results",
                        str(tmp_path / "res"), "--workers", "2", "--min-free-gb", "0", "--settle", "2"],
                       capture_output=True, text=True)
    assert r.returncode == 0
    starts = sorted(float((tmp_path / "res" / "b" / n / "start").read_text()) for n in ("a", "b"))
    assert starts[1] - starts[0] >= 1.9  # second job admitted only after the first settled


def _flux_hold(tmp_path, monkeypatch, ratios):
    """ga_flux_hold with a two-state job file and fake run records (ratio None: no run)."""
    import json

    fh = _load("ga_flux_hold")
    tmp_path.mkdir(parents=True, exist_ok=True)
    first = tmp_path / "hold.json"
    jobs = [{"name": n, "args": ["--correct-from", "x"]} for n in ratios]
    first.write_text(json.dumps({"jobs": jobs}))
    results = tmp_path / "res"
    for name, r in ratios.items():
        if r is not None:
            (results / name).mkdir(parents=True)
            (results / name / "summary.json").write_text(
                json.dumps({"outputs": {"centre_flux_over_target": {"dsmc": r}}}))
    monkeypatch.setattr(fh, "FIRST", first)
    monkeypatch.setattr(fh, "RESULTS", results)
    monkeypatch.setattr(sys, "argv", ["ga_flux_hold.py"])
    return fh


def test_flux_hold_fails_unless_every_state_is_held(tmp_path, monkeypatch):
    # review 3: a missing or unconverged state must give a non-zero exit, not only a message
    fh = _flux_hold(tmp_path / "a", monkeypatch, {"s1": 1.005, "s2": None})
    with pytest.raises(SystemExit) as e:
        fh.main()
    assert e.value.code == 1
    fh = _flux_hold(tmp_path / "b", monkeypatch, {"s1": 1.005, "s2": 1.04})
    with pytest.raises(SystemExit) as e:
        fh.main()
    assert e.value.code == 1
    fh = _flux_hold(tmp_path / "c", monkeypatch, {"s1": 1.005, "s2": 0.99})
    fh.main()  # all within 1.5 %: returns normally (exit 0)


def test_batch_admission_checks_wsl(monkeypatch):
    b = _load("sparta_batch")
    monkeypatch.setattr(b, "available_gb", lambda: 10.0)
    monkeypatch.setattr(b, "wsl_state", lambda: (1.0, 1.5))
    assert "WSL 1.0 GB" in b.admission_blocker(3.0, 2.5, None)
    monkeypatch.setattr(b, "wsl_state", lambda: (4.0, 3.5))
    assert "load" in b.admission_blocker(3.0, 2.5, 3.2)
    assert b.admission_blocker(3.0, 2.5, 4.0) is None
    monkeypatch.setattr(b, "wsl_state", lambda: None)
    assert b.admission_blocker(3.0, 2.5, None) == "WSL state unavailable"
    assert b.admission_blocker(3.0) is None  # no WSL check requested


def test_r07_dimer_inputs(tmp_path):
    r07 = _load("sparta_r07")
    cfg = r07.resolve_config("r07_3.5", ["x_dimer=0.3"])
    r07.write_inputs(tmp_path, cfg)
    case = (tmp_path / "in.case").read_text()
    assert "mixture melt Bi2 frac 0.300000" in case and "dump.dimer.*" in case
    species = (tmp_path / "bi.species").read_text().splitlines()
    assert species[1].split()[0] == "Bi2" and float(species[1].split()[2]) == pytest.approx(2 * r07.BI_MASS, rel=1e-6)
    d2 = float((tmp_path / "bi.vss").read_text().splitlines()[1].split()[1])
    assert d2 == pytest.approx(2 ** (1 / 3) * 8e-10, rel=1e-6)
    # monatomic default: no second species, one dump series
    r07.write_inputs(tmp_path, r07.resolve_config("r07_3.5", []))
    assert "Bi2" not in (tmp_path / "in.case").read_text() + (tmp_path / "bi.species").read_text()


def test_batch_no_start_after(tmp_path):
    r = _batch(tmp_path, [{"name": "late", "args": ["ok"]}], "--no-start-after", "2000-01-01T00:00")
    assert r.returncode == 1 and "late: NOT STARTED" in r.stdout
    assert not (tmp_path / "res" / "b" / "late").exists()


def test_nitrogen_aim_tolerance_fails_without_scans(tmp_path, monkeypatch):
    mod = _load("nitrogen_aim_tolerance")
    monkeypatch.setattr(sys, "argv", ["nitrogen_aim_tolerance.py", "--studies", str(tmp_path),
                                      "--out", str(tmp_path / "out")])
    with pytest.raises(SystemExit, match="required aim scans not found"):
        mod.main()
    assert not (tmp_path / "out").exists()


def test_nitrogen_aim_tolerance_reads_versioned_scans_by_default():
    mod = _load("nitrogen_aim_tolerance")
    scans = mod.load_scans(ROOT / "data/runs/studies")
    assert [s["L_over_r"] for s in scans] == list(mod.PLATES)


def test_nitrogen_aim_tolerance_fails_on_partial_scans(tmp_path):
    # Only the thin-plate and L/r 2.92 records: the other required plates must not vanish silently.
    import shutil
    mod = _load("nitrogen_aim_tolerance")
    for name in ("nitrogen_aim_study.json", "nitrogen_aim_fine_2.92.json"):
        shutil.copy(ROOT / "data/runs/studies" / name, tmp_path / name)
    with pytest.raises(SystemExit, match="nitrogen_aim_fine_5.83.json") as err:
        mod.load_scans(tmp_path)
    assert "nitrogen_aim_fine_19.69.json" in str(err.value)
    assert [s["L_over_r"] for s in mod.load_scans(tmp_path, [0.0, 2.92])] == [0.0, 2.92]
    with pytest.raises(SystemExit, match="nitrogen_aim_fine_11.66.json"):
        mod.load_scans(tmp_path, [2.92, 11.66])
    with pytest.raises(SystemExit, match="no aim scan defined"):
        mod.load_scans(tmp_path, [2.92, 7.0])


def test_provenance_covers_ga_record_dependencies(tmp_path):
    # audit 2026-10-05 finding 3: the Ga DSMC summaries a study reloads are checked like sources, also for twin runs
    import importlib.util
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("record_provenance", root / "scripts/record_provenance.py")
    rp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rp)
    rec = "ga_dsmchold/fill070_d8_dsmchold.json"
    path = f"data/runs/sparta_ga/{rec}"
    actual = rp.sha_lf((root / path).read_bytes())
    for m in ({"inputs": {"ga_records_sha256": {rec: "0" * 64}}},
              {"inputs": {"chamber_provenance": {"ga_records_sha256": {rec: "0" * 64}}}}):
        hashes = rp.recorded_hashes(m)
        assert hashes[path] == "0" * 64 != actual          # a changed summary is a mismatch the checker reports
    assert rp.recorded_hashes({"inputs": {"ga_records_sha256": {"missing.json": "x"}}})["data/runs/sparta_ga/missing.json"] == "x"


def test_provenance_checks_summary_constituents_and_aim_maps():
    # audit follow-up 2026-10-05, finding 2: aim-map hashes are dependencies, and a summary's constituent runs are
    # expanded with their own hashes
    import importlib.util
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("record_provenance", root / "scripts/record_provenance.py")
    rp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(rp)
    deps = {"source_sha256": {"scripts/realizable_controller.py": "a" * 64},
            "aim_maps_sha256": {"results/aim_operating/aim_maps_B-L.npz": "b" * 64}}
    hashes = rp.recorded_hashes({"source_sha256": deps["source_sha256"], "inputs": deps})
    assert hashes == {"scripts/realizable_controller.py": "a" * 64, "results/aim_operating/aim_maps_B-L.npz": "b" * 64}
