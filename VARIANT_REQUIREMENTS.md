# CDIP variant requirements and acceptance record

## Authority and boundary

This repository is the independent CDIP variant. It inherits the validated
prototype baseline at commit `ac698b715c55f42779c36182b85f193f3cd7c7ed` and
uses Streamlit Community Cloud rather than Hugging Face Spaces. The PI email
and subsequent approved meeting feedback below govern this extension; inherited
evaluation artifacts remain historical baseline evidence unless they are explicitly
rerun for this variant.

Variant data, derived artifacts, evaluation, deployment, secrets, and rollback
remain inside this repository and its separate GitHub and Streamlit resources.

## Approved requirements

1. Add the PI-supplied `2022-Missouri-CCS.pdf` document to the corpus.
2. Organize Wiki navigation in two levels: entity type, then entity.
3. Do not expose generated Markdown/YAML metadata as page content.
4. Keep the chatbot's supporting-document list and add a query-focused core
   findings summary.
5. Replace count-only Wiki summaries with cited information about the selected
   entity; display mention and document counts separately as corpus coverage.
6. In the Chatbot, present a concise direct answer before the point-by-point
   supporting findings, without weakening citations, validation, or abstention.

## Corpus addition and provenance

| Field | Value |
|---|---|
| Document ID | `DOC036` |
| Title | The Missouri Comprehensive Conservation Strategy |
| Year | 2022 |
| Agency | Missouri Department of Conservation |
| Local build input | `data/raw/2022-Missouri-CCS.pdf` |
| Public source URL | `https://mdc.mo.gov/sites/default/files/2022-04/2022-Missouri-CCS.pdf` |
| Supplied-file SHA-256 | `a36fe284e40334da177486c491eb2610e3c621bbeca7fdbcd1eb049d4cd75dec` |
| Extraction | 566 pages; 1,142,763 normalized characters |
| Runtime chunks | 258 page-aware chunks |

The supplied attachment is retained as the authoritative variant build input.
Its checksum is recorded separately because it does not byte-match the file
currently returned by the public URL. Raw inputs and extracted text remain
ignored build artifacts; metadata and the derived runtime database are
versioned.

## Acceptance process

The variant may be accepted only after all of the following are recorded:

- catalog validation confirms exactly `DOC001` through `DOC036` and all raw
  files, checksums, extraction fields, and database records are traceable;
- SQLite/FTS contains 36 documents and 982 chunks, including 258 page-aware
  chunks for `DOC036`, and distinctive DOC036 queries retrieve it;
- the independently rebuilt knowledge layer contains referentially sound
  entities and relations and all 15 generated Wiki pages validate;
- Streamlit and Wiki tests confirm entity-type/entity navigation, cited entity
  information in Summary, separately labelled Corpus coverage, optional Key facts
  containing only additional evidence, and no raw front matter in rendered content;
- chatbot tests confirm that the same structured model call returns `Answer`
  and `Key supporting findings`, that the direct answer is constrained to the
  surviving cited claims with a safe local fallback, that the supporting-document
  list is derived only from cited evidence, and that abstention is unchanged;
- inherited official/demo and engineering regressions are rerun after the
  corpus change, while their historical results remain distinguishable from
  the new variant run;
- the three `variant_acceptance_questions` in `data/evaluation_spec.yaml` are
  manually reviewed for relevance, claim support, page citations, and
  appropriate abstention;
- a newly frozen, untouched variant holdout is evaluated separately from
  official/demo and engineering questions;
- `python scripts/04_build_vector_index.py` is run with the variant's local
  `OPENAI_API_KEY`, and the manifest is verified against all 982 chunks;
- `python scripts/08_validate_project.py --report outputs/variant_status_report.md`
  and the full automated suite pass, followed by a local Streamlit smoke test
  and a post-deployment acceptance pass in the separate variant app.

## Current acceptance status

Corpus ingestion, SQLite/FTS, entity/relation extraction, Wiki regeneration,
two-level Wiki presentation, hidden front matter, cited entity summaries separated
from corpus coverage and nonduplicated additional key facts, same-call model-authored
chatbot answers with a validated claim-derived fallback, and the 982-vector FAISS
rebuild are implemented. The full suite passes 148 tests.
The project validator passes all structural gates and reports only the frozen
failed holdout gate. All three live variant development questions passed the
grounding and presentation smoke review recorded in
`outputs/variant_acceptance_smoke.md`.

The separately frozen 20-question DOC036-centered variant holdout was executed
exactly once and did not pass its strict gate: 12 PASS, 5 PARTIAL, and 3 FAIL.
All 4 required abstentions passed, while only 8 of 16 supported questions fully
passed. The immutable first-run evidence and analysis are recorded in
`outputs/variant_holdout_v1_first_run_audit.md`. Final acceptance therefore
remains blocked by the failed variant holdout and remains pending manual review
of the DOC036 entity/relation and regenerated Wiki additions and the separate
cloud smoke test. The independent GitHub coordinate is configured as
`CharlesChen130/conservation-document-intelligence-variant`; repository
visibility, the Streamlit app URL, and application visibility remain owner
decisions.

## Release posture

The current artifacts may be published as a transparently labeled research
demonstration. Publication does not convert the failed holdout into a pass and
must not be described as final variant acceptance. Record the deployed Git
commit, Streamlit URL, visibility choice, cloud smoke-test outcome, and rollback
commit after deployment. Strict acceptance requires repairing the documented
failure classes, replaying this holdout only as a known regression set, and
passing a newly frozen untouched holdout.

