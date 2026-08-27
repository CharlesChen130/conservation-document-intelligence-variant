# Variant acceptance chatbot smoke test

**Run date:** 2026-08-26

**Scope:** Three development questions defined under `variant_acceptance_questions`
in `data/evaluation_spec.yaml`, executed with the current semantic index and
grounded chatbot. This is not an untouched holdout or independent domain review.

## Result summary

| ID | Status | Retrieval | Evidence chunks | Engineering result |
|---|---|---|---:|---|
| VARIANT-1 | `structured_generated_pruned` | semantic | 6 | PASS |
| VARIANT-2 | `structured_generated_pruned_narrowed` | semantic | 6 | PASS |
| VARIANT-3 | `structured_generated_relabelled` | semantic | 6 | PASS |

All three answers passed the application's deterministic grounding and citation
validation. The rendered form included `Core findings` and a cited supporting-
document section. No question failed or abstained.

## VARIANT-1

**Question:** What statewide conservation approach does the Missouri
Comprehensive Conservation Strategy describe?

Core findings described a priority-focused statewide land-conservation approach
and its acquisition, easement, lease, agreement, grant, public-access, and
incentive tools. The supporting-document list cited only:

- The Missouri Comprehensive Conservation Strategy `[DOC036, pp. 64-67]`

**Review:** PASS. The response addressed the statewide approach and remained
within cited DOC036 evidence.

## VARIANT-2

**Question:** How does the strategy use Conservation Opportunity Areas or
priority geographies?

Core findings explained that multiple priority areas are combined into
Conservation Opportunity Areas and Priority Geographies that rank highly across
disciplines and conservation goals. It also described assessment and monitoring
within Priority Geographies. Supporting documents were:

- The Missouri Comprehensive Conservation Strategy `[DOC036, pp. 11-13]`
- MDC Annual Review FY2024 `[DOC016]`

**Review:** PASS. DOC036 directly answered the question; DOC016 provided a
relevant operational follow-through without replacing the strategy evidence.

## VARIANT-3

**Question:** What does the strategy report about landscape health and climate
adaptation?

Core findings described landscape-level health and resiliency, projected
climate and land-use change, wildlife-response modeling, and climate-smart
planning. Supporting documents were:

- The Missouri Comprehensive Conservation Strategy `[DOC036, pp. 131-132]`
- MDC Annual Review FY2021 `[DOC018]`

**Review:** PASS. The answer covered both landscape health and climate
adaptation with validated citations and did not claim an achieved conservation
outcome.

## Remaining acceptance boundary

This development smoke test does not satisfy the required untouched variant
holdout. Final acceptance still requires a separately frozen question set,
blind review, and the separate Streamlit Cloud post-deployment test.

