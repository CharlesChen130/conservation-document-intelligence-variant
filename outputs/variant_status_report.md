# Project status report

**Status:** NOT READY

## Artifact counts

- Catalog sources: 36
- Raw source artifacts: 36
- Database documents: 36
- Search chunks: 982
- Entity mentions: 9612
- Relations: 1389
- Wiki pages in database: 15
- Wiki Markdown files: 15

## Required validation

- Catalog contains exactly 36 sources: PASS
- Every catalog source has one raw artifact: PASS
- Every source is present and chunked in SQLite: PASS
- Wiki has at least 10 structurally valid pages: PASS
- Wiki citations reference catalog documents: PASS
- FAISS semantic index matches current corpus: PASS
- Evaluation report exists: PASS
- All 10 official questions have substantive answers: PASS
- Evaluation contains no failed/safety output: PASS
- Manual five-answer citation audit exists: PASS
- Full official correctness audit has no FAIL result: PASS
- Document-rubric evaluation exists: PASS
- Internal rubric score meets 90/100 threshold: PASS
- Relation quality gate: PASS
- Wiki quality gate: PASS
- Frozen holdout quality gate: FAIL

## Warnings

- Byte-identical source artifacts: DOC007, DOC008

## Failures

- Frozen holdout quality gate has not passed

## Optional deployment-time capabilities

- The persisted semantic index is current; query embeddings and live grounded answers require `OPENAI_API_KEY`.
- External feedback collection requires `FEEDBACK_FORM_URL`.
- Streamlit Community Cloud publication requires owner access to the configured private GitHub repository.
- A Streamlit Community Cloud startup and browser smoke test remains required after deployment.
