# Conservation Document Intelligence

A deployable research prototype that organizes 36 public conservation sources, searches page-aware evidence, extracts conservation entities and relations, presents an evidence-backed two-level wiki, and produces citation-checked chatbot responses with a direct answer, key supporting findings, and supporting documents.

The supplied project description and deployment guide define the inherited prototype. [VARIANT_REQUIREMENTS.md](VARIANT_REQUIREMENTS.md) records the approved PI extension, corpus provenance, independent repository boundary, and variant acceptance gates.

## Documentation

- [Technical implementation report](TECHNICAL_IMPLEMENTATION_REPORT.md)
- [Variant requirements and acceptance](VARIANT_REQUIREMENTS.md)
- [User manual](USER_MANUAL.md)
- [Deployment guide](DEPLOYMENT.md)
- [Implementation roadmap](ROADMAP.md)
- [Variant validator report](outputs/variant_status_report.md)
- [Variant chatbot smoke audit](outputs/variant_acceptance_smoke.md)
- [DOC036-centered holdout first-run audit](outputs/variant_holdout_v1_first_run_audit.md)

## Status

The PI-requested corpus, Wiki, and chatbot changes are implemented. The separately frozen DOC036-centered holdout has also been run exactly once and failed its strict gate, so the variant is not yet accepted. Independent review of the new structured artifacts and the cloud deployment check also remain outstanding:

- 36/36 catalog sources acquired and extracted, including the PI-supplied `DOC036`
- 982 deterministic, page-aware chunks in SQLite/FTS5
- 9,612 entity mentions and 1,389 evidence-linked relations
- 15 validated wiki pages across species, habitats, locations, threats, and agencies; 27/27 cited summary statements and 36/36 additional, nonduplicated key facts trace to stored evidence, and 83/83 internal links resolve
- five working Streamlit tabs: Corpus, Search, Wiki, Chatbot, and Evaluation
- a current 982-vector, 1,536-dimensional FAISS semantic index
- 148 automated tests passing
- three live variant development questions passed grounding, citation, core-findings, and supporting-document smoke checks
- DOC036-centered frozen holdout: 12 PASS, 5 PARTIAL, 3 FAIL; all 4 required abstentions passed, but only 8/16 supported questions fully passed
- the public Evaluation UI exposes only the 10 document-defined questions; 5 additional engineering checks remain in the internal saved evaluation artifact
- a completed five-answer manual citation audit and document-rubric report
- full official-answer audit: 10 PASS, 0 PARTIAL, 0 FAIL
- inherited relation-quality audit: 987/987 baseline integrity checks and 37/37 manually reviewed baseline rows passing; the 402 DOC036 relations still require variant review
- inherited wiki-quality audit: 15/15 baseline pages and 44/44 baseline facts passing; the regenerated variant Wiki has 63 nonduplicated cited statements and passes automated traceability checks but still requires variant manual review
- post-repair H, F, and G 20-question regression sets: 16/16 supported answers and 4/4 intended abstentions on each set
- provisional document-rubric self-score: 95/100 (internal deployment threshold: 90/100)

`OPENAI_API_KEY` is optional for corpus, keyword-search, wiki, and saved-evaluation browsing. It is required for live query embeddings, chatbot answers, and rebuilding the FAISS index. Publication to Streamlit Community Cloud requires the owner's GitHub and Streamlit accounts.

[VARIANT_REQUIREMENTS.md](VARIANT_REQUIREMENTS.md) is the current acceptance record. The validator result is in [outputs/variant_status_report.md](outputs/variant_status_report.md), the three-question development review is in [outputs/variant_acceptance_smoke.md](outputs/variant_acceptance_smoke.md), and the immutable first-run variant holdout analysis is in [outputs/variant_holdout_v1_first_run_audit.md](outputs/variant_holdout_v1_first_run_audit.md). Other files under `outputs/` that predate this extension document inherited prototype performance and must not be presented as completed variant evaluation.

## Quick start

Python 3.12 is the tested Streamlit Community Cloud deployment target.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
cp .env.example .env
python scripts/00_initialize.py
python -m pytest -q
streamlit run app.py
```

The versioned `db/conservation.db` is the complete runtime corpus, so the app does not download or process documents at startup. Open <http://localhost:8501> for local Streamlit or use Docker port 7860.

## Capabilities

| Area | Implementation | Credential-free |
|---|---|---|
| Corpus | searchable/filterable 36-source catalog with public links and provenance | Yes |
| Keyword retrieval | SQLite FTS5 with page-aware evidence snippets | Yes |
| Semantic retrieval | current persisted FAISS index using OpenAI embeddings | Live query/rebuild requires API key |
| Structured knowledge | rule-based typed entities and five required relation types, each tied to evidence | Yes |
| Wiki | two-level entity-type/entity navigation over 15 evidence-ranked pages; cited entity summaries are separated from corpus-coverage metadata and generated front matter is hidden | Yes |
| Chatbot | validated model-authored answer from the same structured call, safe claim-derived fallback, key supporting findings, cited supporting-document list, all-evidence expander, and abstention | Requires API key |
| Evaluation | 10 official questions in the public UI; 5 engineering checks, known regression sets, and holdouts retained as internal evaluation artifacts | Yes |

## Rebuild pipeline

Normal app startup reads precomputed artifacts. To rebuild from the public sources:

```bash
python scripts/00_initialize.py
python scripts/00_apply_source_replacements.py
python scripts/01_download_sources.py
python scripts/02_extract_text.py
python scripts/03_build_chunks.py
python scripts/05_extract_entities.py
python scripts/06_generate_wiki.py --per-category 3
python scripts/07_evaluate.py
python scripts/08_validate_project.py
```

Rebuild the semantic index after setting `OPENAI_API_KEY`:

```bash
python scripts/04_build_vector_index.py
```

Regenerate the complete internal 15-case evaluation artifact with live model answers using:

```bash
python scripts/07_evaluate.py --with-openai
```

The public Evaluation UI continues to expose only the 10 official requirement questions from that artifact.

Acquisition and processing steps are resumable. Use each command's `--help` option for document-specific or forced rebuild options.

## Configuration and secrets

Copy `.env.example` for local development. On Streamlit Community Cloud, add root-level TOML values in the app's **Secrets** settings. Root-level secrets are exposed to the application as environment variables.

- `OPENAI_API_KEY`: enables chatbot answers and index construction
- `OPENAI_CHAT_MODEL`: optional override; default is `gpt-4.1-mini`
- `OPENAI_EMBEDDING_MODEL`: optional override; default is `text-embedding-3-small`
- `VECTOR_STORE_ID`: reserved for the optional hosted retrieval adapter
- `FEEDBACK_FORM_URL`: public external survey URL shown in the Evaluation tab

Never commit `.env` or `.streamlit/secrets.toml`.

## Source provenance

The canonical record is [data/metadata.csv](data/metadata.csv). Original URLs are retained even when a broken source required an official replacement, archived official copy, or representative public DocumentCloud record. All substitutions and verification links are explicit in [data/source_replacements.csv](data/source_replacements.csv).

DOC007 and DOC008 intentionally resolve to byte-identical copies of the same DOI report because the required source list includes both its landing-page and direct-PDF entries. The audit surfaces this instead of silently removing a required ID.
DOC036 is the PI-supplied 2022 Missouri Comprehensive Conservation Strategy. Its supplied-file checksum and official public URL are recorded independently because the attachment does not byte-match the file currently served at that URL.


Raw downloads and extracted page files are rebuildable and excluded from the deployment image. Their checksums, resolved URLs, extraction counts, and status remain in the catalog; the compact derived SQLite corpus is versioned for deterministic startup.

## Project layout

```text
app.py                         Streamlit entry point
config.yaml                    Pipeline and runtime defaults
data/metadata.csv              36-source catalog and processing provenance
db/conservation.db             Precomputed runtime corpus and FTS index
scripts/                       Reproducible pipeline and audit commands
src/conservation_intelligence/ Testable application and pipeline modules
vector_index/                  Persisted FAISS index and current-corpus manifest
wiki/                          Generated, reviewable Markdown knowledge pages
outputs/                       Structured exports, evaluation, and status report
tests/                         Unit/integration/app smoke tests and questions
```

## Deployment

The primary deployment target is Streamlit Community Cloud. Use `app.py` as the entrypoint and Python 3.12; dependencies, the SQLite corpus, FAISS index, and wiki are versioned in the repository so startup performs no downloads or indexing. Detailed GitHub, secrets, deployment, smoke-test, and rollback instructions are in [DEPLOYMENT.md](DEPLOYMENT.md). The Dockerfile remains available for optional container hosting.

The official-answer, relation-quality, wiki-quality, and known-set chatbot regression gates are complete, and the provisional document-rubric score exceeds the internal threshold. Neither untouched holdout evidence base passes its strict gate: the inherited J holdout had five false abstentions, and the DOC036-centered variant holdout scored 12 PASS, 5 PARTIAL, and 3 FAIL. The app may be published for transparent research demonstration with these limitations disclosed. Independent conservation-domain review remains recommended before any consequential or production use.

## Limitations

- The rule-based entity layer favors auditability over exhaustive recall and has not received domain-expert validation.
- Wiki summaries are extractive: they show the strongest one or two cited retained evidence statements rather than uncited general encyclopedia text. Four pages omit **Key facts** because no additional retained statements remain after the Summary; repeated co-mentions are explicitly labelled as non-semantic corpus associations.
- The saved live evaluation is a self-evaluation, not an independent domain-expert assessment; the five-answer citation audit is recorded in `outputs/manual_citation_audit.md`.
- The inherited J holdout failed because unseen answerable paraphrases could trigger false abstentions or semantically adjacent answers; its immutable audit remains historical baseline evidence.
- The DOC036-centered variant holdout also failed its strict gate at 12 PASS, 5 PARTIAL, and 3 FAIL. Its immutable first-run record is in `outputs/variant_holdout_v1_first_run_audit.md`.
- Live semantic queries and answers depend on the configured OpenAI API and can be affected by model/service changes; citation and abstention checks remain deterministic.
- The prototype is not an authoritative conservation decision system. Verify consequential claims against the linked source and cited pages.

## Research prototype notice

This system uses public documents and AI-assisted answering. Generated content can contain errors. Verify important conclusions against the linked source documents and inspect the cited evidence.
