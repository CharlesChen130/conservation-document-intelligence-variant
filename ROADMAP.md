# Conservation Document Intelligence Variant — Release Roadmap

## Goal

Publish the independent DOC036 variant as a reproducible Streamlit Community Cloud research demonstration while preserving its separate repository boundary, evidence provenance, immutable evaluation history, and disclosed limitations.

The inherited prototype roadmap is complete historical context. This roadmap records the current variant release and the work required for strict acceptance after deployment.

## Current snapshot

| Workstream | Status | Evidence or remaining action |
|---|---|---|
| Inherited prototype baseline | Complete | Baseline commit `ac698b715c55f42779c36182b85f193f3cd7c7ed` |
| DOC036 corpus addition | Complete | `DOC036`, 566 pages, 258 chunks; provenance in `VARIANT_REQUIREMENTS.md` |
| Variant runtime corpus | Complete | 36 documents and 982 page-aware chunks |
| Semantic index | Complete | 982 vectors, 1,536 dimensions, current manifest |
| Entity and relation layer | Automated checks complete | 9,612 mentions and 1,389 relations; manual DOC036 review remains |
| Two-level Wiki | Implemented | 15 pages with 27 cited summary statements, 36 additional nonduplicated key facts, separate corpus coverage, and 83 resolving links; manual review remains |
| Chatbot presentation | Implemented | Direct answer first, key supporting findings, cited supporting-document list, all-evidence expander, and abstention |
| Automated verification | Complete | 145 tests passing |
| Variant development smoke | Complete | Three live development questions passed the recorded smoke audit |
| DOC036-centered holdout V1 | Complete, strict gate failed | 12 PASS, 5 PARTIAL, 3 FAIL; immutable first-run audit retained |
| GitHub publication | Pending owner action | Review, commit feature branch, fast-forward `main`, push variant repository |
| Streamlit deployment | Pending owner action | Create separate app, add secret, choose URL/visibility, run cloud smoke test |
| Strict variant acceptance | Blocked | Repair failure classes and pass a new untouched holdout |

## Deployment versus acceptance

The application is deployable as a transparently labeled research demonstration. Deployment is useful for PI review and user evaluation, but it does not mean the strict acceptance gate passed.

Strict acceptance remains blocked because:

- only 8 of 16 supported DOC036 holdout questions fully passed;
- one answerable question falsely abstained;
- two other supported questions failed due to incorrect facet/number selection or missed DOC036 evidence;
- the DOC036-specific relation additions and regenerated Wiki still require manual domain review; and
- the separate cloud smoke test has not yet been recorded.

## Completed PI requirements

- [x] Add the PI-supplied 2022 Missouri Comprehensive Conservation Strategy as `DOC036`.
- [x] Rebuild the variant metadata, SQLite/FTS corpus, vector index, entities, relations, and Wiki independently.
- [x] Organize Wiki navigation first by **Entity type**, then by **Entity**.
- [x] Hide generated YAML/front-matter fields from the rendered Wiki.
- [x] Retain the chatbot's supporting-document list.
- [x] Add a query-focused **Core findings** summary.
- [x] Replace count-only Wiki summaries with cited entity information and move mention/document statistics to **Corpus coverage**.
- [x] Present a model-authored direct **Answer** from the same structured call before **Key supporting findings**; validate it against the surviving claims and use a claim-derived fallback when needed.
- [x] Freeze, execute exactly once, and manually audit a 20-question DOC036-centered holdout.
- [x] Preserve document/page citations, claim validation, and explicit abstention.

## Release path

### 1. Local preflight — complete

- [x] Confirm independent working directory, branch, and remote.
- [x] Confirm `.env`, Streamlit secrets, local Codex context, and raw DOC036 are ignored.
- [x] Confirm the committed runtime artifacts are small enough for normal GitHub publication.
- [x] Run the complete suite: 145 passed.
- [x] Verify the frozen evaluation and output hashes.
- [x] Update public project, technical, user, deployment, requirements, and roadmap documentation.

### 2. Review and create the release commit — pending owner approval

Follow `DEPLOYMENT.md` to:

1. inspect all modified and new files;
2. stage only the intended variant release;
3. confirm no key, local context, raw attachment, or processed build file is staged;
4. commit `feature/variant-pi-requirements`; and
5. record the release commit hash.

### 3. Publish the independent GitHub `main` branch — pending owner action

- update local `main` from `origin/main` using fast-forward-only commands;
- fast-forward merge `feature/variant-pi-requirements` into `main`;
- rerun the full test suite; and
- push `main` only to `CharlesChen130/conservation-document-intelligence-variant`.

Do not rename the feature branch over `main`, force-push, change the remote, or push these artifacts to another CDIP repository.

### 4. Create the separate Streamlit app — pending owner action

- connect Streamlit Community Cloud to the variant GitHub repository;
- deploy branch `main` and entrypoint `app.py` with Python 3.12;
- choose a variant-specific `*.streamlit.app` URL;
- select public or private application visibility independently of repository visibility;
- configure the variant `OPENAI_API_KEY` through Streamlit Secrets; and
- configure provider-side budget and usage monitoring.

### 5. Run the cloud smoke test — pending

Verify the 36-document/982-chunk counts, DOC036 retrieval, semantic search, two-level Wiki navigation, cited entity summaries separated from corpus coverage, hidden front matter, answer-first chatbot output and citations, correct abstention, official Evaluation UI scope, reboot behavior, and isolation from the earlier CDIP app.

Record the deployed commit, app URL, visibility, smoke result, and rollback commit in the handoff record in `DEPLOYMENT.md`.

## Post-deployment quality roadmap

The existing V01–V20 set is now a known immutable regression set. It must not be presented as a fresh post-repair holdout.

### A. Build separate diagnostic cases

Create development-only cases for these failure classes:

1. exact section selection in a long, internally repetitive document;
2. competition between DOC036 and overlapping inherited sources;
3. multi-facet coverage surviving generation and claim pruning; and
4. validating that a cited number answers the requested aggregation.

### B. Implement general repairs

Potential repair directions include section-aware retrieval metadata, long-document diversification, preference rules when a question explicitly names DOC036, improved multi-facet evidence selection, and requested-number/aggregation validation. Repairs must address general failure types rather than memorizing V01–V20.

### C. Re-run known regressions

After repairs:

- run targeted diagnostic tests;
- run the full automated suite;
- replay inherited engineering regressions;
- replay V01–V20 only as known regression evidence; and
- check safety, citation, latency, and token-cost regressions.

### D. Freeze a new untouched holdout

Design a new balanced holdout that is disjoint from development, official, engineering, and V01–V20 questions. Freeze its specification and relevant input hashes before the first execution. Strict acceptance requires this fresh set to satisfy the approved threshold.

### E. Complete independent review

Before consequential use, obtain and record conservation-domain review of:

- the 402 DOC036-derived relations;
- the regenerated Wiki with 27 summary statements and 36 additional key facts;
- representative DOC036 answers and citations; and
- the language used to disclose research-prototype limitations.

## Release and acceptance gates

| Gate | Research-demo deployment | Strict acceptance |
|---|---:|---:|
| 36-document runtime corpus complete | Required; complete | Required; complete |
| Current 982-vector semantic index | Required; complete | Required; complete |
| 148 automated tests | Required; complete | Required; complete |
| Secrets excluded from Git | Required; complete locally | Required |
| Variant holdout disclosed | Required; complete | Not sufficient |
| DOC036 V1 strict holdout pass | Not required if failure is disclosed | Failed |
| New untouched post-repair holdout | Not required for demo | Pending |
| Manual DOC036 knowledge review | Recommended | Pending |
| Separate Streamlit cloud smoke | Pending | Pending |
| Domain-expert certification | Recommended | Pending |

## Repository and deployment boundary

- Work and artifacts remain in `/home/songxi/CDIP-variant`.
- The only configured GitHub destination is `CharlesChen130/conservation-document-intelligence-variant`.
- The deployment uses a separate Streamlit app, URL, visibility setting, secret, and rollback record.
- Raw DOC036 and local requirement inputs remain uncommitted; versioned derived artifacts provide the runtime corpus.
- Changes are not copied into another CDIP repository without explicit review and authorization.

## Owner decisions still required

- approve the staged release contents and commit;
- push the variant `main` branch;
- choose GitHub repository visibility;
- authorize Streamlit access to the repository;
- choose the Streamlit URL and application visibility;
- enter the variant API key and configure its budget;
- run and record the cloud smoke test; and
- decide whether to begin the post-deployment quality-repair cycle.