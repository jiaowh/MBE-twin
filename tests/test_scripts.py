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
                           "--results", str(tmp_path / "res"), "--workers", "2", *extra],
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
