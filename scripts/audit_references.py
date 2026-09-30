"""Index and audit the acquired reference library; never runs a physics solver."""
from pathlib import Path
import hashlib
import json
import logging
import re
from datetime import date
from urllib.parse import unquote

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]


class PdfWarnings(logging.Handler):
    def __init__(self):
        super().__init__()
        self.messages = []

    def emit(self, record):
        self.messages.append(record.getMessage())


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def as_list(obj):
    return obj if isinstance(obj, list) else obj["sources"]


def collect():
    records = []
    growth_checks = {x["file"]: x for x in read_json(ROOT / "ref/growth/file_verification.json")["files"]}
    for group in ("growth", "hardware", "methods", "reference"):
        manifest = f"ref/{group}/sources.json"
        for original in as_list(read_json(ROOT / manifest)):
            s = dict(original)
            if group == "growth" and s.get("local_path") in growth_checks:
                baseline = growth_checks[s["local_path"]]
                s["sha256"] = baseline["sha256"]
                s["bytes"] = baseline["bytes"]
            s["collection"] = group
            s["detail_manifest"] = manifest
            artifacts = s.get("artifacts", [])
            if s.get("local_path"):
                artifacts = [{"path": s["local_path"], "status": "downloaded",
                              "sha256": s.get("sha256"), "bytes": s.get("bytes")}]
            s["indexed_artifacts"] = artifacts
            records.append(s)
    return records


def audit(records):
    issues, artifacts, seen = [], [], set()
    for s in records:
        if s["id"] in seen:
            issues.append(f"Duplicate source ID {s['id']}")
        seen.add(s["id"])
        for a in s["indexed_artifacts"]:
            relative = a.get("path")
            if not relative:
                continue
            path = (ROOT / relative).resolve()
            if not path.is_relative_to(ROOT):
                issues.append(f"Outside repository: {relative}")
                continue
            if not path.is_file():
                issues.append(f"Missing artifact: {relative}")
                continue
            raw = path.read_bytes()
            digest = hashlib.sha256(raw).hexdigest()
            item = {"id": s["id"], "path": relative, "bytes": len(raw),
                    "sha256": digest, "source_status": a.get("status"),
                    "usable_source": a.get("status") == "downloaded"}
            if a.get("sha256") and a["sha256"].lower() != digest:
                issues.append(f"Hash mismatch: {relative}")
            if a.get("bytes") is not None and a["bytes"] != len(raw):
                issues.append(f"Byte count mismatch: {relative}")
            if item["usable_source"] and path.suffix.lower() == ".pdf":
                if not raw.startswith(b"%PDF-"):
                    issues.append(f"Not a PDF: {relative}")
                else:
                    try:
                        warnings = PdfWarnings()
                        logger = logging.getLogger("pypdf")
                        logger.addHandler(warnings)
                        previous_propagate = logger.propagate
                        logger.propagate = False
                        reader = PdfReader(path)
                        item["pdf_pages"] = len(reader.pages)
                        item["first_page_text_characters"] = len(reader.pages[0].extract_text() or "")
                        item["parser_warning_count"] = len(warnings.messages)
                        item["parser_warning_examples"] = warnings.messages[:3]
                    except Exception as exc:
                        issues.append(f"PDF parse failed: {relative}: {exc}")
                    finally:
                        logger.removeHandler(warnings)
                        logger.propagate = previous_propagate
            elif item["usable_source"] and path.suffix.lower() == ".html":
                txt = raw.decode("utf-8", errors="replace").lower()
                if "<html" not in txt and "<!doctype" not in txt:
                    issues.append(f"Not recognizable HTML: {relative}")
            artifacts.append(item)
    # Check active authored Markdown; historical documents deliberately retain old paths.
    docs = [ROOT / "README.md", ROOT / "mbe_twin.md", ROOT / "PHASE1_CHAMBER_PLAN.md",
            ROOT / "ref/README.md"]
    docs += list((ROOT / "docs").glob("*.md")) + list((ROOT / "ref/notes").glob("*.md"))
    for path in docs:
        if not path.exists():
            issues.append(f"Missing active document: {path.relative_to(ROOT)}")
            continue
        txt = path.read_text(encoding="utf-8-sig")
        if len(re.findall(r"^```", txt, re.M)) % 2:
            issues.append(f"Unbalanced code fences: {path.relative_to(ROOT)}")
        for target in re.findall(r"\[[^\]]*\]\(([^\n)]+)\)", txt):
            target = target.strip().strip("<>")
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target) or target.startswith("#"):
                continue
            target = unquote(target.split("#")[0])
            if target and not (path.parent / target).exists():
                issues.append(f"Broken link in {path.relative_to(ROOT)}: {target}")
        for block in re.findall(r"```json\s*\n(.*?)\n```", txt, re.S):
            try:
                json.loads(block)
            except ValueError as exc:
                issues.append(f"Invalid embedded JSON in {path.name}: {exc}")
    read_json(ROOT / "data/intake/machine_requirements.json")
    return artifacts, issues


def make_index(records):
    lines = ["# Reference library", "", "New search, 2026-09-30: [references for predictive validation](notes/VALIDATION_REFERENCE_SEARCH_2026-09-30.md), including sources R16-R20, access limits and follow-ups. These are reference acquisitions, not completed validation cases.", "",
             "Second search, 2026-09-30: [physics data for the open Stage A questions](notes/PHYSICS_DATA_SEARCH_2026-09-30.md), sources R21-R31 and the R05 full text: Bi2 and the R07 rate deficit, a Ga collision-diameter bracket, Ga2, nitrogen plate holes, depletion-resistant crucibles, emissivities and heater-uniformity mechanisms.", "", "Compiled 2026-09-13. This is an acquired evidence collection for the GaN/AlN chamber plan. Literature and comparator specifications do not validate this custom chamber.", "",
             "Read the annotated reviews: [growth/materials](notes/GROWTH_EVIDENCE.md), [hardware](notes/HARDWARE_EVIDENCE.md), and [solver/fidelity](notes/SOLVER_AND_FIDELITY.md) and [representative chamber](notes/REFERENCE_CHAMBER.md). The [combined manifest](sources.json) preserves the detailed source records; [integrity report](integrity_report.json) records file checks. Original-source copyright and license terms remain applicable.", "",
             "The [proposal text](proposal/SLIDE_TEXT.md) comes from all 19 supplied slides. [Archived plans](archive/) preserve the pre-review drafts. These are project inputs, separate from externally acquired evidence.", ""]
    for group, label in (("growth", "Papers and material properties"), ("hardware", "Chamber and component specifications"), ("methods", "Solvers and numerical methods"), ("reference", "Representative chamber and published test cases")):
        lines += [f"## {label}", "", "| ID | Source | Local copy or access status |", "|---|---|---|"]
        for s in records:
            if s["collection"] != group:
                continue
            links = []
            for a in s["indexed_artifacts"]:
                if a.get("status") == "downloaded" and a.get("path"):
                    p = Path(a["path"])
                    links.append(f"[{p.suffix.lstrip('.').upper()}]({p.relative_to('ref').as_posix()})")
            title = s["title"].replace("|", "/")
            stamp = str(s.get("year", s.get("publisher", s.get("vendor", ""))))
            local = ", ".join(links) if links else "URL only / local source unavailable; see detailed manifest"
            lines.append(f"| {s['id']} | [{title}]({s['url']}) ({stamp}) | {local} |")
        lines += ["", f"Details: [{group}/sources.json]({group}/sources.json).", ""]
    lines += ["## Remaining evidence gaps", "", "G03 is a bibliographic lead without reviewed original full text. G05/G06 have reviewed online content but no local paper. H02/H04/H10/H11 have incomplete local source access. Most R-series records were reviewed from abstracts or index entries only; check their numbers against full texts before use. HTML challenge responses are retained only as failed-download diagnostics and excluded from usable-source counts. Consult source-level status before extracting data.", "",
              "The library includes no actual machine CAD or calibration dataset. Obtain wafer/template specifications, optical/contact properties, source output maps, selected pump/diagnostic data and independent GaN/AlN wafers through the [data plan](../docs/DATA_AND_VALIDATION_PLAN.md). No digitized dataset or fitted parameter has been fabricated from these papers.", "",
              "Rerun `python scripts/audit_references.py` from the repository with pypdf installed to check the collection. This checks file integrity and document structure, not physical correctness, browser availability of every external URL, or simulation accuracy.", ""]
    (ROOT / "ref/README.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    records = collect()
    make_index(records)
    (ROOT / "ref/sources.json").write_text(json.dumps({"schema_version": 1,
        "compiled_date": str(date.today()), "sources": records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # This generated report is a valid link target even on the first audit run.
    report_path = ROOT / "ref/integrity_report.json"
    if not report_path.exists():
        report_path.write_text('{"status":"audit_in_progress"}\n', encoding="utf-8")
    artifacts, issues = audit(records)
    report = {"checked_date": str(date.today()), "source_count": len(records),
              "usable_pdf_count": sum(x["usable_source"] and "pdf_pages" in x for x in artifacts),
              "usable_html_count": sum(x["usable_source"] and x["path"].endswith(".html") for x in artifacts),
              "artifacts": artifacts, "issues": issues, "physics_validation": "not_performed"}
    (ROOT / "ref/integrity_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "artifacts"}, ensure_ascii=True, indent=2))
    raise SystemExit(bool(issues))
