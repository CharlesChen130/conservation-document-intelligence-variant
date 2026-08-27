from __future__ import annotations

from src.conservation_intelligence.evaluation import (
    EvaluationRecord,
    load_demo_questions,
    load_evaluation_spec,
    render_report,
)
from src.conservation_intelligence.repository import SearchResult


def test_demo_question_set_has_required_and_edge_questions():
    questions = load_demo_questions()
    spec = load_evaluation_spec()

    assert len(spec["official_questions"]) == 10
    assert len(questions) == 15
    assert len(spec["variant_acceptance_questions"]) == 3
    assert set(spec["variant_acceptance_questions"]).isdisjoint(
        spec["official_questions"] + spec["additional_engineering_questions"]
    )

    assert questions[0] == "What documents discuss aquatic invasive species?"
    assert sum(item["weight_percent"] for item in spec["official_rubric"]) == 100


def test_render_report_contains_evidence_and_review_checklist():
    evidence = SearchResult(
        chunk_id="DOC001-C0001",
        doc_id="DOC001",
        title="Test Plan",
        page="3",
        text="Wetland evidence.",
        source_url="https://example.org/source",
        score=1.0,
    )
    record = EvaluationRecord(
        number=1,
        question="What discusses wetlands?",
        evidence=[evidence],
        answer="Not generated in retrieval-only mode.",
        status="retrieval_candidates",
    )

    report = render_report([record])

    assert "[DOC001, p. 3]" in report
    assert "claim-to-citation-to-source" in report
    assert "Retrieved chunks are relevant" in report
    assert "Official weighted rubric" in report
    assert "Official document question" in report
    assert "Retrieval mode: `keyword`" in report
