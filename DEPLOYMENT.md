# CDIP Variant Deployment Guide

This guide publishes the independent DOC036 variant to its own GitHub repository and Streamlit Community Cloud application. It must not reuse or update the earlier CDIP repository, Streamlit app, URL, or secrets.

Normal startup runs `app.py` and reads the committed SQLite database, FAISS index, wiki, and evaluation artifacts. It does not download source documents, extract text, or rebuild indexes in the cloud.

## Release identity and status

| Setting | Value |
|---|---|
| Local repository | `/home/songxi/CDIP-variant` |
| GitHub repository | `CharlesChen130/conservation-document-intelligence-variant` |
| Current development branch | `feature/variant-pi-requirements` |
| Streamlit deployment branch | `main` |
| Entrypoint | `app.py` |
| Python | 3.12 |
| Expected test result | 145 passed |

The PI-requested features are implemented and locally verified. The variant is suitable for a transparently labeled research demonstration, but it is not strictly accepted: the frozen DOC036-centered holdout scored 12 PASS, 5 PARTIAL, and 3 FAIL. Preserve that result and disclose the limitation.

The raw PI attachment under `data/raw/` is intentionally ignored and will not be uploaded. Its provenance and checksum are versioned in `data/metadata.csv` and `VARIANT_REQUIREMENTS.md`; its extracted content is already contained in the committed runtime database and vector index.

## 1. Local release preflight

Run these commands from WSL before creating the release commit:

```bash
cd /home/songxi/CDIP-variant
git remote -v
git branch --show-current
git status --short
python -m pytest -q
python scripts/08_validate_project.py --report outputs/variant_status_report.md
streamlit run app.py
```

Confirm that:

- `origin` points only to `CharlesChen130/conservation-document-intelligence-variant`;
- the tests report `145 passed`;
- the validator reports the expected `NOT READY` status because the strict frozen-holdout gate has not passed, not because a structural artifact is missing;
- the local app loads at <http://localhost:8501> and `/_stcore/health` is healthy; and
- the status report and DOC036 first-run audit remain separate artifacts.

Verify that secrets, local instructions, and rebuild-only source files are ignored:

```bash
git check-ignore -v \
  .env \
  .streamlit/secrets.toml \
  AGENTS.override.md \
  .codex-local/PROTOTYPE_V1_CONTEXT.md \
  data/raw/2022-Missouri-CCS.pdf \
  data/processed/DOC036.txt

git ls-files \
  .env \
  .streamlit/secrets.toml \
  AGENTS.override.md \
  .codex-local
```

The first command should identify an ignore rule for each path. The second command should print nothing.

Expected runtime counts are:

- 36 documents, including `DOC036`;
- 982 page-aware chunks, including 258 from `DOC036`;
- 9,612 entity mentions;
- 1,389 evidence-linked relations;
- 15 wiki pages, 48 validated facts, and 83 resolving links; and
- 982 FAISS vectors with 1,536 dimensions.

The DOC007/DOC008 byte-identity warning is expected and documented.

## 2. Commit the feature branch and publish `main`

Review the complete change set before staging:

```bash
git status --short
git diff --stat
git diff -- README.md DEPLOYMENT.md USER_MANUAL.md \
  TECHNICAL_IMPLEMENTATION_REPORT.md VARIANT_REQUIREMENTS.md ROADMAP.md
```

Stage the intended variant release and inspect the staged file list before committing:

```bash
git add -A
git diff --cached --name-only
git status --short
git commit -m "Implement DOC036 conservation intelligence variant"
```

Do not commit if the staged list contains `.env`, `.streamlit/secrets.toml`, `AGENTS.override.md`, `.codex-local/`, or a raw/processed DOC036 build file.

Publish through the existing `main` branch; do not rename the feature branch over it:

```bash
git switch main
git pull --ff-only origin main
git merge --ff-only feature/variant-pi-requirements
python -m pytest -q
git push origin main
```

If either fast-forward command fails, stop and inspect the branch history. Do not force-push or change the remote to work around a divergence.

## 3. Create the separate Streamlit Community Cloud app

Use the current [Streamlit Community Cloud deployment workflow](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy):

1. Sign in at <https://share.streamlit.io/> using the GitHub account that administers the variant repository.
2. Switch to the workspace matching the repository owner.
3. If the repository is private, grant Streamlit access to private repositories.
4. Select **Create app**, then **Yup, I have an app**.
5. Enter the deployment coordinates below.
6. Open **Advanced settings**, select Python 3.12, and configure secrets.
7. Deploy and watch the build logs.

| Streamlit setting | Value |
|---|---|
| Repository | `CharlesChen130/conservation-document-intelligence-variant` |
| Branch | `main` |
| Main file path | `app.py` |
| Python version | 3.12 |
| App URL | Choose an available variant-specific `*.streamlit.app` subdomain |

Deployment contract: Main file path: `app.py`; Python version: `3.12`.

The deploying GitHub account must have repository administrator permission. Streamlit can deploy from a public or private repository. Repository visibility and app visibility are separate owner decisions, but Community Cloud currently allows only one private app at a time. If the earlier CDIP app is private, make one app public or remove the older private app before keeping this variant private. See Streamlit's [GitHub connection](https://docs.streamlit.io/deploy/streamlit-community-cloud/get-started/connect-your-github-account) and [sharing](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app) documentation.

## 4. Configure secrets and cost controls

In **Advanced settings → Secrets**, enter root-level TOML:

```toml
OPENAI_API_KEY = "your-variant-project-api-key"
# Optional overrides:
# OPENAI_CHAT_MODEL = "gpt-4.1-mini"
# OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
# FEEDBACK_FORM_URL = "https://example.com/feedback"
```

Use a separate OpenAI project key and budget for this variant when practical. Enter the real key only in Streamlit's Secrets interface; never place it in GitHub, logs, screenshots, documentation, `.env.example`, or `.streamlit/secrets.toml`. Streamlit documents this workflow in [Secrets management](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management).

Configure provider-side usage limits and monitoring before making the app public. The application limits each browser session, but that is not a global spending limit.

## 5. Use the committed runtime artifacts

The current FAISS artifacts already match all 982 chunks. Do not rebuild the corpus or semantic index in Streamlit Cloud and do not rebuild them merely for the first upload.

If the corpus, chunks, or embedding model changes later, rebuild and validate locally before committing:

```bash
python scripts/03_build_chunks.py
python scripts/04_build_vector_index.py
python scripts/05_extract_entities.py
python scripts/06_generate_wiki.py --per-category 3
python -m pytest -q
python scripts/08_validate_project.py --report outputs/variant_status_report.md
```

Commit the resulting database, FAISS files, wiki, structured exports, and evaluation/status artifacts together so the deployed runtime stays internally consistent.

## 6. Post-deployment smoke and acceptance review

After the first deployment and every material update, confirm:

- [ ] The app loads without a Python exception and Cloud logs show no missing-file error.
- [ ] Corpus shows 36 records, including `DOC036`, with working public-source links.
- [ ] Evaluation metrics show 982 chunks, 9,612 entity mentions, 1,389 relations, and 15 wiki pages.
- [ ] Keyword search returns page-aware evidence for `wetland restoration` and `invasive carp`.
- [ ] Semantic search works with the configured key and current 982-vector index.
- [ ] All wiki pages use the two-level **Entity type** then **Entity** selectors.
- [ ] Wiki content does not expose `generated_at`, `generation_method`, or other YAML front matter.
- [ ] A DOC036 question such as “How does MDC use overlay analysis and a conservation heat map to quality-assure Conservation Opportunity Areas?” returns inspectable DOC036 evidence.
- [ ] Chatbot answers show **Core findings**, a cited supporting-document list, and matching **Retrieved evidence**.
- [ ] A clearly unsupported question, such as an exact guaranteed 2035 wolf population, produces an abstention rather than an invented value.
- [ ] The public Evaluation tab exposes only the 10 official questions, not engineering or holdout cases.
- [ ] App visibility matches the owner's intended setting and the earlier CDIP app remains unchanged.
- [ ] Rebooting the app preserves the same counts without rebuilding.
- [ ] The deployed Git commit, app URL, visibility, and smoke-test result are recorded.

A cloud smoke pass completes the deployment check but does not erase the failed strict holdout or constitute final variant acceptance.

## 7. Updates, logs, and rollback

Pushing a new commit to the configured GitHub branch triggers a Streamlit update. Dependency changes in `requirements.txt` trigger a fuller rebuild. Use **Manage app** and Cloud logs to inspect failures.

For a bad release, prefer a traceable revert:

```bash
git switch main
git revert <bad-release-commit>
git push origin main
```

Record the prior known-good commit before deployment. Do not force-push or rewrite published history for ordinary rollback.

Runtime filesystem and browser-session state are ephemeral. Store durable corpus, index, wiki, and reports in Git; keep feedback in an external service. Changing the app's Python version after deployment requires deleting and redeploying the app, so record the custom subdomain, GitHub coordinates, and secrets before doing so.

## 8. Owner handoff record

Complete this record after deployment. Do not record the API key itself.

```text
GitHub repository: CharlesChen130/conservation-document-intelligence-variant
Deployed Git commit:
Streamlit URL:
Repository visibility:
Application visibility:
OpenAI project/budget configured:
Deployment date:
Cloud smoke result:
Known-good rollback commit:
Known limitation disclosed: DOC036 holdout 12 PASS / 5 PARTIAL / 3 FAIL
```

The remaining owner actions are GitHub authentication, commit/push approval, Streamlit account authorization, the URL and visibility choices, secret entry, and the post-deployment smoke test.