from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import yaml

from .chatbot import AnswerProvider, answer_question
from .database import connect_database
from .paths import DATABASE_PATH, OUTPUTS_DIR, PROJECT_ROOT
from .repository import SearchResult, keyword_search
from .semantic import EmbeddingProvider
from .wiki import citation


EVALUATION_SPEC_PATH = PROJECT_ROOT / "data" / "evaluation_spec.yaml"
HOLDOUT_SPEC_PATH = PROJECT_ROOT / "data" / "holdout_spec.yaml"


@dataclass(frozen=True)
class EvaluationRecord:
    number: int
    question: str
    evidence: Sequence[SearchResult]
    answer: str
    status: str
    retrieval_mode: str = "keyword"
    error: str = ""


def load_evaluation_spec(path: Path = EVALUATION_SPEC_PATH) -> dict[str, Any]:
    spec = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    required = (
        "official_questions",
        "additional_engineering_questions",
        "variant_acceptance_questions",
        "official_rubric",
    )
    missing = [field for field in required if not isinstance(spec.get(field), list)]
    if missing:
        raise ValueError(f"Evaluation specification is missing lists: {', '.join(missing)}")
    if len(spec["variant_acceptance_questions"]) != 3:
        raise ValueError("The variant acceptance set must contain exactly 3 questions")
    if len(spec["official_questions"]) != 10:
        raise ValueError("The document-defined evaluation must contain exactly 10 questions")
    if sum(int(item["weight_percent"]) for item in spec["official_rubric"]) != 100:
        raise ValueError("Official rubric weights must total 100 percent")
    return spec


def load_demo_questions(path: Path = EVALUATION_SPEC_PATH) -> list[str]:
    spec = load_evaluation_spec(path)
    return [*spec["official_questions"], *spec["additional_engineering_questions"]]


def load_holdout_spec(path: Path = HOLDOUT_SPEC_PATH) -> dict[str, Any]:
    spec = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    questions = spec.get("questions")
    if spec.get("version") != 1 or not isinstance(questions, list):
        raise ValueError("Holdout specification must have version 1 and a question list")
    if len(questions) != 20:
        raise ValueError("The frozen holdout evaluation must contain exactly 20 questions")
    required = {"id", "category", "expected_behavior", "question", "evaluation_focus"}
    for index, item in enumerate(questions, start=1):
        missing = required - set(item) if isinstance(item, dict) else required
        if missing:
            raise ValueError(
                f"Holdout question {index} is missing: {', '.join(sorted(missing))}"
            )
        if item["expected_behavior"] not in {"supported_answer", "abstain"}:
            raise ValueError(
                f"Holdout question {item['id']} has an invalid expected behavior"
            )
    ids = [item["id"] for item in questions]
    prompts = [item["question"].casefold().strip() for item in questions]
    if len(set(ids)) != len(ids) or len(set(prompts)) != len(prompts):
        raise ValueError("Holdout question IDs and prompts must be unique")
    if not spec.get("frozen_at") or "without tuning" not in str(spec.get("policy", "")):
        raise ValueError("Holdout specification must declare its freeze and no-tuning policy")
    return spec


def evaluate_questions(
    questions: Sequence[str],
    *,
    database_path: Path = DATABASE_PATH,
    provider: AnswerProvider | None = None,
    embedding_provider: EmbeddingProvider | None = None,
    top_k: int = 6,
    candidate_k: int | None = None,
) -> list[EvaluationRecord]:
    records: list[EvaluationRecord] = []
    for number, question in enumerate(questions, start=1):
        with connect_database(database_path) as connection:
            evidence = keyword_search(connection, question, limit=top_k)

        answer = "Not generated in retrieval-only mode."
        status = "retrieval_candidates" if evidence else "expected_or_possible_abstention"
        error = ""
        if provider is not None:
            try:
                grounded = answer_question(
                    question,
                    provider,
                    embedding_provider=embedding_provider,
                    database_path=database_path,
                    top_k=top_k,
                    candidate_k=candidate_k,
                )
                evidence = list(grounded.evidence)
                answer = grounded.answer
                status = grounded.generation_status
                retrieval_mode = grounded.retrieval_mode
            except Exception as exception:
                status = "failed"
                error = str(exception)
                retrieval_mode = "failed"
        else:
            retrieval_mode = "keyword"

        records.append(
            EvaluationRecord(
                number=number,
                question=question,
                evidence=evidence,
                answer=answer,
                status=status,
                retrieval_mode=retrieval_mode,
                error=error,
            )
        )
    return records


def render_report(records: Sequence[EvaluationRecord], provider_model: str | None = None) -> str:
    spec = load_evaluation_spec()
    official_count = len(spec["official_questions"])
    generated_at = datetime.now(timezone.utc).isoformat()
    mode = f"grounded answers with {provider_model}" if provider_model else "retrieval only"
    found = sum(bool(record.evidence) for record in records)
    lines = [
        "# Demo Question Evaluation",
        "",
        f"Generated: {generated_at}",
        "",
        f"Mode: {mode}",
        "",
        f"Retrieval coverage: {found}/{len(records)} questions returned at least one evidence chunk.",
        "",
        (
            "Automated retrieval coverage is not a correctness judgment. A reviewer must verify "
            "relevance and the claim-to-citation-to-source chain."
        ),
        "",
        "## Document-defined evaluation contract",
        "",
        (
            f"Questions 1-{official_count} reproduce the required demo questions from the project "
            "description. Later questions are additional engineering checks and do not replace the "
            "official set."
        ),
        "",
        "### Official weighted rubric",
        "",
        "| Category | Weight | Requirement | Reviewer score |",
        "|---|---:|---|---:|",
    ]
    for item in spec["official_rubric"]:
        lines.append(
            f"| {item['category']} | {item['weight_percent']}% | {item['expectation']} | /{item['weight_percent']} |"
        )
    lines.extend(
        [
            "",
            "Automated checks provide evidence for the rubric, but the final score remains a manual review.",
            "",
        ]
    )
    for record in records:
        question_type = (
            "Official document question" if record.number <= official_count else "Additional engineering question"
        )
        lines.extend(
            [
                f"## {record.number}. {record.question}",
                "",
                f"Evaluation set: **{question_type}**",
                "",
                f"Status: `{record.status}`",
                "",
                f"Retrieval mode: `{record.retrieval_mode}`",
                "",
                "### Retrieved evidence",
                "",
            ]
        )
        if record.evidence:
            for result in record.evidence:
                source_citation = citation(result.doc_id, result.page)
                snippet = result.text[:300].replace("\n", " ")
                if len(result.text) > 300:
                    snippet += "…"
                lines.append(
                    f"- {source_citation} **{result.title}** — {snippet} "
                    f"[Source]({result.source_url})"
                )
        else:
            lines.append("- No evidence retrieved; chatbot should abstain.")
        lines.extend(["", "### Answer", "", record.answer, ""])
        if record.error:
            lines.extend([f"Error: `{record.error}`", ""])
        lines.extend(
            [
                "### Manual review",
                "",
                "- [ ] Retrieved chunks are relevant.",
                "- [ ] Claims are supported by cited evidence.",
                "- [ ] Document IDs and page numbers are correct.",
                "- [ ] Unsupported claims are absent or the system abstained.",
                "- Notes:",
                "",
            ]
        )
    return "\n".join(lines)


def write_report(
    records: Sequence[EvaluationRecord],
    *,
    output_path: Path = OUTPUTS_DIR / "demo_answers.md",
    provider_model: str | None = None,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(".md.part")
    temporary.write_text(render_report(records, provider_model), encoding="utf-8")
    temporary.replace(output_path)
    return output_path


def render_holdout_report(
    records: Sequence[EvaluationRecord],
    *,
    spec_path: Path = HOLDOUT_SPEC_PATH,
    provider_model: str | None = None,
) -> str:
    spec = load_holdout_spec(spec_path)
    questions = spec["questions"]
    if len(records) != len(questions):
        raise ValueError("Holdout records do not match the frozen question count")
    generated_at = datetime.now(timezone.utc).isoformat()
    mode = f"grounded answers with {provider_model}" if provider_model else "retrieval only"
    spec_hash = hashlib.sha256(spec_path.read_bytes()).hexdigest()
    found = sum(bool(record.evidence) for record in records)
    lines = [
        "# Frozen Holdout Evaluation",
        "",
        f"Generated: {generated_at}",
        "",
        f"Mode: {mode}",
        "",
        f"Frozen specification SHA-256: `{spec_hash}`",
        "",
        f"Freeze policy: {spec['policy']}",
        "",
        f"Retrieval coverage: {found}/{len(records)} questions returned at least one evidence chunk.",
        "",
        "This report records the first run. Retrieval coverage and mechanical answer status are not semantic correctness judgments.",
        "",
        "## Frozen test inventory",
        "",
        "| ID | Category | Expected behavior | Question |",
        "|---|---|---|---|",
    ]
    for item in questions:
        lines.append(
            f"| {item['id']} | {item['category']} | {item['expected_behavior']} | {item['question']} |"
        )
    lines.append("")

    for record, item in zip(records, questions, strict=True):
        lines.extend(
            [
                f"## {item['id']}. {record.question}",
                "",
                f"Category: `{item['category']}`",
                "",
                f"Expected behavior: `{item['expected_behavior']}`",
                "",
                f"Evaluation focus: {item['evaluation_focus']}",
                "",
                f"Status: `{record.status}`",
                "",
                f"Retrieval mode: `{record.retrieval_mode}`",
                "",
                "### Retrieved evidence",
                "",
            ]
        )
        if record.evidence:
            for result in record.evidence:
                source_citation = citation(result.doc_id, result.page)
                snippet = result.text[:300].replace("\n", " ")
                if len(result.text) > 300:
                    snippet += "…"
                lines.append(
                    f"- {source_citation} **{result.title}** — {snippet} "
                    f"[Source]({result.source_url})"
                )
        else:
            lines.append("- No evidence retrieved.")
        lines.extend(["", "### Answer", "", record.answer, ""])
        if record.error:
            lines.extend([f"Error: `{record.error}`", ""])
        lines.extend(
            [
                "### Blind review",
                "",
                "- [ ] Expected answer/abstention behavior is correct.",
                "- [ ] Retrieved chunks are relevant to the complete question scope.",
                "- [ ] Every material claim is supported by its cited evidence.",
                "- [ ] Citation document IDs and pages belong to the supporting evidence.",
                "- [ ] No unsupported claim, private-data disclosure, or instruction override appears.",
                "- Result: UNREVIEWED",
                "- Notes:",
                "",
            ]
        )
    return "\n".join(lines)


def write_holdout_report(
    records: Sequence[EvaluationRecord],
    *,
    output_path: Path = OUTPUTS_DIR / "holdout_answers.md",
    spec_path: Path = HOLDOUT_SPEC_PATH,
    provider_model: str | None = None,
) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_suffix(".md.part")
    temporary.write_text(
        render_holdout_report(
            records,
            spec_path=spec_path,
            provider_model=provider_model,
        ),
        encoding="utf-8",
    )
    temporary.replace(output_path)
    return output_path
