from __future__ import annotations

from src.conservation_intelligence.evaluation import (
    load_evaluation_spec,
    load_holdout_spec,
)


def test_holdout_set_is_frozen_unique_and_disjoint_from_development_questions():
    holdout = load_holdout_spec()
    development = load_evaluation_spec()
    questions = holdout["questions"]
    development_prompts = {
        question.casefold()
        for question in [
            *development["official_questions"],
            *development["variant_acceptance_questions"],
            *development["additional_engineering_questions"],
        ]
    }

    assert len(questions) == 20
    assert len({item["id"] for item in questions}) == 20
    assert all(item["question"].casefold() not in development_prompts for item in questions)
    assert sum(item["expected_behavior"] == "supported_answer" for item in questions) == 16
    assert sum(item["expected_behavior"] == "abstain" for item in questions) == 4
    assert "without tuning" in holdout["policy"]
