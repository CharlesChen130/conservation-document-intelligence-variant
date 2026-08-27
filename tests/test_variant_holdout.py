from __future__ import annotations

from src.conservation_intelligence.evaluation import (
    load_evaluation_spec,
    load_holdout_spec,
)
from src.conservation_intelligence.paths import PROJECT_ROOT


VARIANT_HOLDOUT_PATH = PROJECT_ROOT / "data" / "variant_holdout_v1_spec.yaml"


def test_variant_holdout_is_frozen_doc036_focused_and_disjoint() -> None:
    variant = load_holdout_spec(VARIANT_HOLDOUT_PATH)
    development = load_evaluation_spec()
    questions = variant["questions"]

    development_prompts = {
        question.casefold().strip()
        for key in (
            "official_questions",
            "additional_engineering_questions",
            "variant_acceptance_questions",
        )
        for question in development[key]
    }
    prior_prompts: set[str] = set()
    for path in sorted((PROJECT_ROOT / "data").glob("holdout*_spec.yaml")):
        prior = load_holdout_spec(path)
        prior_prompts.update(
            item["question"].casefold().strip() for item in prior["questions"]
        )

    prompts = [item["question"].casefold().strip() for item in questions]
    assert [item["id"] for item in questions] == [
        f"V{number:02d}" for number in range(1, 21)
    ]
    assert len(set(prompts)) == 20
    assert set(prompts).isdisjoint(development_prompts)
    assert set(prompts).isdisjoint(prior_prompts)
    assert sum(item["expected_behavior"] == "supported_answer" for item in questions) == 16
    assert sum(item["expected_behavior"] == "abstain" for item in questions) == 4
    assert all(
        "DOC036" in item["evaluation_focus"]
        for item in questions
        if item["expected_behavior"] == "supported_answer"
    )
    assert "without tuning" in variant["policy"]

