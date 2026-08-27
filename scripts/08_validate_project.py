"""Validate the precomputed corpus and write a deployment-readiness report."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.conservation_intelligence.catalog import (
    REQUIRED_DOC_IDS,
    load_catalog,
    validate_catalog,
)
from src.conservation_intelligence.evaluation import load_evaluation_spec
from src.conservation_intelligence.paths import PROJECT_ROOT as APP_PROJECT_ROOT
from src.conservation_intelligence.semantic import semantic_index_is_current
from src.conservation_intelligence.wiki import validate_wiki_page


CITATION_RE = re.compile(r"\[(DOC\d{3}), pp?\. [^\]]+\]")
MIN_INTERNAL_RUBRIC_SCORE = 90


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--report",
        default="outputs/status_report.md",
        help="Markdown report path relative to the project root.",
    )
    args = parser.parse_args()

    catalog = load_catalog()
    expected_ids = {row["doc_id"] for row in catalog}
    raw_dir = APP_PROJECT_ROOT / "data" / "raw"
    wiki_dir = APP_PROJECT_ROOT / "wiki"
    database_path = APP_PROJECT_ROOT / "db" / "conservation.db"

    failures: list[str] = []
    warnings: list[str] = []
    failures.extend(f"Catalog: {error}" for error in validate_catalog(catalog))
    raw_files: dict[str, Path] = {}
    checksums: dict[str, list[str]] = defaultdict(list)

    resolved_raw_dir = raw_dir.resolve()
    for row in sorted(catalog, key=lambda item: item["doc_id"]):
        doc_id = row["doc_id"]
        local_file = row.get("local_file", "").strip()
        source_path = (APP_PROJECT_ROOT / local_file).resolve()
        if not local_file or not source_path.is_relative_to(resolved_raw_dir):
            failures.append(
                f"{doc_id}: raw artifact path is missing or outside data/raw"
            )
            continue
        if not source_path.is_file():
            failures.append(f"{doc_id}: raw artifact is missing: {local_file}")
            continue
        raw_files[doc_id] = source_path
        checksums[sha256(source_path)].append(doc_id)

    duplicate_groups = [ids for ids in checksums.values() if len(ids) > 1]
    for group in duplicate_groups:
        warnings.append(f"Byte-identical source artifacts: {', '.join(group)}")

    if not database_path.exists():
        failures.append("db/conservation.db is missing")
        counts = {}
        database_ids: set[str] = set()
    else:
        connection = sqlite3.connect(database_path)
        counts = {
            table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("documents", "chunks", "entities", "relations", "wiki_pages")
        }
        database_ids = {
            row[0] for row in connection.execute("SELECT doc_id FROM documents").fetchall()
        }
        zero_chunk_ids = {
            row[0]
            for row in connection.execute(
                """
                SELECT d.doc_id
                FROM documents d
                LEFT JOIN chunks c ON c.doc_id = d.doc_id
                GROUP BY d.doc_id
                HAVING COUNT(c.chunk_id) = 0
                """
            ).fetchall()
        }
        connection.close()
        if zero_chunk_ids:
            failures.append(f"Documents without chunks: {', '.join(sorted(zero_chunk_ids))}")

    missing_database_ids = expected_ids - database_ids
    extra_database_ids = database_ids - expected_ids
    if missing_database_ids:
        failures.append(f"Catalog documents missing from database: {', '.join(sorted(missing_database_ids))}")
    if extra_database_ids:
        failures.append(f"Unexpected database documents: {', '.join(sorted(extra_database_ids))}")

    wiki_files = sorted(wiki_dir.glob("*/*.md"))
    cited_ids: set[str] = set()
    for page in wiki_files:
        content = page.read_text(encoding="utf-8")
        page_errors = validate_wiki_page(content)
        failures.extend(f"{page.relative_to(APP_PROJECT_ROOT)}: {error}" for error in page_errors)
        cited_ids.update(match.group(1) for match in CITATION_RE.finditer(content))

    unknown_citations = cited_ids - expected_ids
    if unknown_citations:
        failures.append(f"Wiki cites unknown documents: {', '.join(sorted(unknown_citations))}")
    if len(wiki_files) < 10:
        failures.append(f"Only {len(wiki_files)} wiki pages exist; at least 10 are required")

    evaluation_path = APP_PROJECT_ROOT / "outputs" / "demo_answers.md"
    manual_audit_path = APP_PROJECT_ROOT / "outputs" / "manual_citation_audit.md"
    full_audit_path = APP_PROJECT_ROOT / "outputs" / "full_demo_correctness_audit.md"
    rubric_path = APP_PROJECT_ROOT / "outputs" / "requirements_evaluation.md"
    relation_audit_path = APP_PROJECT_ROOT / "outputs" / "relation_quality_audit.md"
    wiki_audit_path = APP_PROJECT_ROOT / "outputs" / "wiki_quality_audit.md"
    holdout_audit_path = (
        APP_PROJECT_ROOT / "outputs" / "holdout_v4_first_run_audit.md"
    )
    official_count = len(load_evaluation_spec()["official_questions"])
    evaluation_content = ""
    evaluation_statuses: dict[int, str] = {}
    if not evaluation_path.exists():
        failures.append("outputs/demo_answers.md is missing")
    else:
        evaluation_content = evaluation_path.read_text(encoding="utf-8")
        sections = list(
            re.finditer(
                r"^## (\d+)\. .*?^Status: `([^`]+)`",
                evaluation_content,
                flags=re.MULTILINE | re.DOTALL,
            )
        )
        evaluation_statuses = {
            int(match.group(1)): match.group(2) for match in sections
        }
        missing_official = set(range(1, official_count + 1)) - set(evaluation_statuses)
        if missing_official:
            failures.append(
                "Official evaluation questions missing: "
                + ", ".join(str(item) for item in sorted(missing_official))
            )
        bad_statuses = {
            number: status
            for number, status in evaluation_statuses.items()
            if status in {"failed", "safety_abstention"}
        }
        if bad_statuses:
            failures.append(f"Evaluation contains failed safety states: {bad_statuses}")
        if re.search(r"\[S\d[^\]]*\]", evaluation_content):
            failures.append("Evaluation exposes unresolved model-facing source labels")
        for number in range(1, official_count + 1):
            section_match = re.search(
                rf"^## {number}\. .*?(?=^## \d+\.|\Z)",
                evaluation_content,
                flags=re.MULTILINE | re.DOTALL,
            )
            if section_match and "I do not have enough retrieved evidence" in section_match.group(0):
                failures.append(f"Official evaluation question {number} abstained")

    if not manual_audit_path.exists():
        failures.append("outputs/manual_citation_audit.md is missing")
    if not full_audit_path.exists():
        failures.append("outputs/full_demo_correctness_audit.md is missing")
    else:
        full_audit_content = full_audit_path.read_text(encoding="utf-8")
        if "| **FAIL** |" in full_audit_content:
            failures.append("Full official correctness audit contains a FAIL result")
        if "| **PARTIAL** |" in full_audit_content:
            warnings.append("Full official correctness audit contains PARTIAL results")
    rubric_score: int | None = None
    if not rubric_path.exists():
        failures.append("outputs/requirements_evaluation.md is missing")
    else:
        rubric_content = rubric_path.read_text(encoding="utf-8")
        rubric_match = re.search(
            r"self-score:\s*\*\*(\d+)/100\*\*",
            rubric_content,
            flags=re.IGNORECASE,
        )
        if rubric_match is None:
            failures.append("Document-rubric self-score could not be parsed")
        else:
            rubric_score = int(rubric_match.group(1))
            if rubric_score < MIN_INTERNAL_RUBRIC_SCORE:
                failures.append(
                    f"Internal rubric score {rubric_score}/100 is below the "
                    f"{MIN_INTERNAL_RUBRIC_SCORE}/100 deployment threshold"
                )
    relation_gate_passed = False
    if not relation_audit_path.exists():
        failures.append("outputs/relation_quality_audit.md is missing")
    else:
        relation_gate_passed = "**Gate result:** PASS" in relation_audit_path.read_text(
            encoding="utf-8"
        )
        if not relation_gate_passed:
            failures.append("Relation quality gate has not passed")
    wiki_gate_passed = False
    if not wiki_audit_path.exists():
        failures.append("outputs/wiki_quality_audit.md is missing")
    else:
        wiki_gate_passed = "**Gate result:** PASS" in wiki_audit_path.read_text(
            encoding="utf-8"
        )
        if not wiki_gate_passed:
            failures.append("Wiki quality gate has not passed")
    holdout_gate_passed = False
    if not holdout_audit_path.exists():
        failures.append("outputs/holdout_first_run_audit.md is missing")
    else:
        holdout_gate_passed = "**Holdout result:** PASS" in holdout_audit_path.read_text(
            encoding="utf-8"
        )
        if not holdout_gate_passed:
            failures.append("Frozen holdout quality gate has not passed")

    semantic_current = semantic_index_is_current(database_path=database_path)
    if not semantic_current:
        failures.append("FAISS semantic index is missing or stale for the current corpus")

    status = (
        "APPLICATION VALIDATION PASSED — CLOUD SMOKE TEST PENDING"
        if not failures
        else "NOT READY"
    )
    report_lines = [
        "# Project status report",
        "",
        f"**Status:** {status}",
        "",
        "## Artifact counts",
        "",
        f"- Catalog sources: {len(expected_ids)}",
        f"- Raw source artifacts: {len(raw_files)}",
        f"- Database documents: {counts.get('documents', 0)}",
        f"- Search chunks: {counts.get('chunks', 0)}",
        f"- Entity mentions: {counts.get('entities', 0)}",
        f"- Relations: {counts.get('relations', 0)}",
        f"- Wiki pages in database: {counts.get('wiki_pages', 0)}",
        f"- Wiki Markdown files: {len(wiki_files)}",
        "",
        "## Required validation",
        "",
        f"- Catalog contains exactly {len(REQUIRED_DOC_IDS)} sources: "
        f"{'PASS' if len(expected_ids) == len(REQUIRED_DOC_IDS) else 'FAIL'}",
        f"- Every catalog source has one raw artifact: {'PASS' if len(raw_files) == len(expected_ids) else 'FAIL'}",
        f"- Every source is present and chunked in SQLite: {'PASS' if not missing_database_ids and not extra_database_ids and not locals().get('zero_chunk_ids', set()) else 'FAIL'}",
        f"- Wiki has at least 10 structurally valid pages: {'PASS' if len(wiki_files) >= 10 and not any('wiki/' in item for item in failures) else 'FAIL'}",
        f"- Wiki citations reference catalog documents: {'PASS' if not unknown_citations else 'FAIL'}",
        f"- FAISS semantic index matches current corpus: {'PASS' if semantic_current else 'FAIL'}",
        f"- Evaluation report exists: {'PASS' if evaluation_path.exists() else 'FAIL'}",
        f"- All {official_count} official questions have substantive answers: {'PASS' if all(number in evaluation_statuses for number in range(1, official_count + 1)) and not any(f'Official evaluation question {number} abstained' in failures for number in range(1, official_count + 1)) else 'FAIL'}",
        f"- Evaluation contains no failed/safety output: {'PASS' if evaluation_content and not any(status in {'failed', 'safety_abstention'} for status in evaluation_statuses.values()) else 'FAIL'}",
        f"- Manual five-answer citation audit exists: {'PASS' if manual_audit_path.exists() else 'FAIL'}",
        f"- Full official correctness audit has no FAIL result: {'PASS' if full_audit_path.exists() and '| **FAIL** |' not in full_audit_content else 'FAIL'}",
        f"- Document-rubric evaluation exists: {'PASS' if rubric_path.exists() else 'FAIL'}",
        f"- Internal rubric score meets {MIN_INTERNAL_RUBRIC_SCORE}/100 threshold: {'PASS' if rubric_score is not None and rubric_score >= MIN_INTERNAL_RUBRIC_SCORE else 'FAIL'}",
        f"- Relation quality gate: {'PASS' if relation_gate_passed else 'FAIL'}",
        f"- Wiki quality gate: {'PASS' if wiki_gate_passed else 'FAIL'}",
        f"- Frozen holdout quality gate: {'PASS' if holdout_gate_passed else 'FAIL'}",
        "",
        "## Warnings",
        "",
    ]
    report_lines.extend(f"- {warning}" for warning in warnings)
    if not warnings:
        report_lines.append("- None")
    report_lines.extend(["", "## Failures", ""])
    report_lines.extend(f"- {failure}" for failure in failures)
    if not failures:
        report_lines.append("- None")
    report_lines.extend(
        [
            "",
            "## Optional deployment-time capabilities",
            "",
            "- The persisted semantic index is current; query embeddings and live grounded answers require `OPENAI_API_KEY`.",
            "- External feedback collection requires `FEEDBACK_FORM_URL`.",
            "- Streamlit Community Cloud publication requires owner access to the configured private GitHub repository.",
            "- A Streamlit Community Cloud startup and browser smoke test remains required after deployment.",
            "",
        ]
    )

    report_path = APP_PROJECT_ROOT.joinpath(*Path(args.report).parts)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report_lines), encoding="utf-8")
    print(json.dumps({"status": status, "counts": counts, "warnings": warnings, "failures": failures}, indent=2))
    print(f"Report: {report_path}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
