# User Manual

## Conservation Document Intelligence

Version 1.1 variant — August 26, 2026

This manual covers the independent DOC036 variant.

## 1. Purpose

Conservation Document Intelligence is a research application for searching and exploring 36 public conservation sources. It provides:

- a filterable source catalog;
- keyword and semantic search;
- an evidence-backed conservation wiki;
- a citation-based chatbot; and
- saved evaluation reports.

The system is a research prototype. Generated answers can be incomplete or incorrect. Always verify important claims using the cited source and page.

## 2. Who should use this manual

This manual is for:

- researchers and students exploring the conservation corpus;
- reviewers checking chatbot answers and citations;
- demonstration participants;
- developers running the application locally; and
- administrators deploying or updating the Streamlit application.

Sections 3–10 cover ordinary use. Sections 11–16 cover local installation and administration.

## 3. Accessing the application

### Hosted application

After deployment, open the assigned `https://...streamlit.app` address in a modern browser. No local installation is needed.

A private GitHub repository and the Streamlit application's viewer access are separate settings. The repository can remain private while the administrator makes the application public. If the application itself is private, sign in using an account authorized by the administrator.

Streamlit Community Cloud may put the application to sleep after inactivity. If a sleep page appears, select **Yes, get this app back up!** and wait for it to start.

### Local application

Developers can run the same interface at <http://localhost:8501>. See Section 11.

## 4. Interface overview

The application contains five tabs:

| Tab | Use |
|---|---|
| Corpus | Browse the 36 sources, filter metadata, and open original documents |
| Search | Retrieve page-aware evidence using keyword or semantic search |
| Wiki | Choose an entity type, then an entity, and read its cited page |
| Chatbot | Read core findings, supporting documents, and detailed retrieved evidence |
| Evaluation | Review system counts and the 10 official requirement questions and saved answers |

A research-prototype warning remains visible at the top of the application.

### Evaluation tab

The public Evaluation tab is intentionally limited to the 10 demonstration questions specified in the project requirements. Select a question to review its saved answer and citations. **View official evaluation report** opens a read-only snapshot of those 10 cases, and **Download official evaluation report** downloads the same public 10-question report.

Five additional engineering questions and the holdout and regression suites are retained as internal development artifacts. They are not selectable, displayed, or included in the public report download.

## 5. Using the Corpus tab

The Corpus tab is the best place to understand what information the system can answer.

It displays:

- document ID;
- title;
- publication year;
- agency;
- topic;
- acquisition status;
- extraction status;
- page count; and
- original public-source link.

### Filter the catalog

1. Open **Corpus**.
2. Select one or more agencies in the **Agency** filter.
3. Select one or more topics in the **Topic** filter.
4. Review the filtered table.
5. Select a link in the **Source** column to open the original public source.

Clear the selected filters to restore all 36 records.

### Document IDs

Every catalog item has an ID such as `DOC001` or `DOC012`. Search results, wiki facts, chatbot answers, and evaluation reports use the same IDs.

## 6. Using the Search tab

The Search tab returns stored source passages. It does not generate an answer.

### Keyword search

Keyword search uses the local SQLite full-text index and does not require an OpenAI API key.

1. Select **Keyword**.
2. Enter a phrase or several important terms.
3. Choose the number of results.
4. Select **Search**.
5. Review the title, document ID, page, relevance score, source link, and passage.

Good keyword searches include:

- `wetland restoration`
- `invasive carp prevention`
- `waterfowl habitat`
- `Missouri wildlife planning`
- `climate change wetlands`

Use specific nouns and actions. If a long natural-language question returns weak keyword results, shorten it to the central concepts.

### Semantic search

Semantic search uses an OpenAI query embedding and the persisted FAISS index. It requires the administrator to configure `OPENAI_API_KEY`.

1. Select **Semantic**.
2. Enter a phrase or question.
3. Choose the number of results.
4. Select **Search**.
5. Review the returned evidence exactly as you would for keyword search.

Semantic search is useful for paraphrases where the source uses different wording. If the app reports that the semantic index is unavailable, use keyword search or contact the administrator.

### Understanding a search result

A typical label resembles:

`[DOC012, p. 5] Source title · Open source · score 0.742`

- `DOC012` identifies the catalog record.
- `p. 5` is the stored source page.
- **Open source** links to the public document.
- The score ranks results for this query; it is not a confidence percentage.
- The displayed passage is source evidence, not a generated summary.

## 7. Using the Wiki tab

The Wiki tab contains 15 generated pages across species, habitats, locations, threats, and agencies.

1. Open **Wiki**.
2. Choose an **Entity type** such as Species, Habitats, Locations, Threats, or Agencies.
3. Choose an **Entity** within that type.
4. Read the summary and cited facts.
5. Follow related-page links when available.
6. Use the citations to verify the supporting source evidence.

Wiki pages are generated from stored corpus evidence. Their build metadata is used for navigation and is intentionally hidden from page content. They are not general encyclopedia articles and should not be assumed to cover information outside the 36-source corpus.

Some pages contain only one high-quality fact. This is intentional; the generator does not add weaker text merely to make every page longer.

## 8. Using the Chatbot tab

### Requirements

The chatbot is enabled only when the administrator has configured `OPENAI_API_KEY`. Hosted users do not need to provide their own key.

### Ask a question

1. Open **Chatbot**.
2. Enter one conservation question in the message field.
3. Wait while the system retrieves and checks evidence.
4. Read the query-focused **Core findings** and its cited supporting-document list.
5. Expand **Retrieved evidence** to inspect the full passages used.
6. Verify each material claim against the cited source passage.
7. Open the source link when the answer will be used in research or decision-making.

Questions are limited to 1,000 characters. Each browser session is limited to 20 chatbot questions.

### Recommended question style

Ask one focused question with a clear subject and requested action.

Good examples:

- `What conservation actions are described for invasive carp?`
- `How do the documents describe the role of wetlands in waterfowl conservation?`
- `Which agencies report invasive-species management programs?`
- `Compare the wetland priorities described by these two agencies.`
- `What evidence links climate change to wetland threats in this corpus?`

For a comparison, name both sides. For a list, state exactly what should be listed. For an exact value or date, ask the chatbot to report only values explicitly present in the corpus.

Avoid:

- combining many unrelated questions in one message;
- asking for information outside conservation or outside the corpus;
- asking the model to ignore its evidence restrictions;
- treating a missing answer as proof that no outside evidence exists; or
- entering confidential, personal, or unpublished information.

### What is sent to OpenAI

For live chatbot use, the question and selected public-corpus evidence are sent to OpenAI for answer generation. The question is also sent for semantic embedding when semantic retrieval is enabled. Do not enter sensitive information.

### Session behavior

Conversation messages are stored only in the active Streamlit browser session. They can disappear when:

- the page is refreshed;
- the browser session expires;
- the app is restarted;
- the app wakes from hibernation; or
- the user opens the app in another browser or device.

Copy important answers and citations into your own research notes.

## 9. Reading citations and evidence

The chatbot uses citations such as:

- `[DOC012, p. 5]` for one page; or
- `[DOC012, pp. 5-6]` for a page range.

A citation means that the application associated the claim with a retrieved passage from that document and page. It does not mean an independent expert approved the claim.

### Citation review checklist

For each material statement, check:

1. **Document:** Does the cited document match the subject?
2. **Page:** Does the cited page contain the relevant statement?
3. **Meaning:** Does the source support the answer's meaning, not merely similar words?
4. **Scope:** Is the answer narrower than or equal to what the source establishes?
5. **Numbers:** Are values, dates, percentages, and ranges copied exactly?
6. **Completeness:** Does the answer omit an important condition or comparison side?

If any check fails, do not rely on that statement. Record the problem for evaluation feedback.

## 10. Abstentions, partial answers, and errors

### Insufficient-evidence response

The chatbot may respond that it does not have enough retrieved evidence. This can mean:

- the corpus does not contain the information;
- retrieval did not find the relevant passage;
- the evidence covered only part of the question;
- a generated claim failed citation validation; or
- the safety validator could not establish that the answer stayed within scope.

An abstention is not proof that the requested fact is false.

### Partial-looking answers

The system can remove unsupported claims and retain supported ones. If an answer appears incomplete:

1. inspect **Retrieved evidence**;
2. split the question into smaller parts;
3. run a keyword search for the missing concept; and
4. report the case during evaluation.

### Provider error

A message such as **The grounded answer could not be produced** can indicate a missing key, expired credit, rate limit, timeout, unavailable model, or temporary provider failure. Keyword search and the wiki should remain usable.

### Known evaluation limitation

The frozen DOC036-centered variant holdout scored 12 PASS, 5 PARTIAL, and 3 FAIL. All four required abstentions passed, but only 8 of 16 supported questions fully passed. The main weaknesses were selecting the exact section of the 566-page DOC036, competition from overlapping inherited documents, and losing requested facets during answer validation. Treat the application as a transparent research demonstration and verify material claims against the cited pages.

## 11. Running locally

### Prerequisites

- Ubuntu, WSL, macOS, or another environment capable of running Python;
- Python 3.12;
- internet access for installing dependencies; and
- an OpenAI API key only if live semantic search and chatbot answers are required.

### Create the environment

From WSL or a Linux terminal:

```bash
cd /home/songxi/CDIP-variant
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

For development and tests, install:

```bash
python -m pip install -r requirements-dev.txt
```

### If virtual-environment creation fails

On Ubuntu or WSL, an `ensurepip` error normally means the venv operating-system package is missing:

```bash
sudo apt update
sudo apt install python3-venv
python3 -m venv --clear .venv
source .venv/bin/activate
```

### Configure the local API key

Copy the example:

```bash
cp .env.example .env
```

Open `.env` in a text editor and set:

```dotenv
OPENAI_API_KEY=your-real-api-key
```

Optional settings are:

```dotenv
OPENAI_CHAT_MODEL=gpt-4.1-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
FEEDBACK_FORM_URL=
```

Never commit or share `.env`.

### Start the application

```bash
streamlit run app.py
```

Open <http://localhost:8501>. Stop the server with **Ctrl+C**.

### Run tests

```bash
python -m pytest -q
```

The current variant workspace passes 145 automated tests. Run the complete suite after every corpus or behavior change.

## 12. Streamlit Community Cloud administration

### Deployment settings

Connect Streamlit Community Cloud to the independent variant GitHub repository and create an app with:

| Setting | Value |
|---|---|
| Repository | `CharlesChen130/conservation-document-intelligence-variant` |
| Branch | `main` |
| Main file path | `app.py` |
| Python version | 3.12 |
| App URL | Administrator-selected available subdomain |

The deploying GitHub account must have repository administrator permission. If the repository is private, grant Streamlit access to private repositories.

### Cloud secret

In **Advanced settings → Secrets**, enter:

```toml
OPENAI_API_KEY = "your-real-api-key"
```

Optional overrides can be added at the same root level:

```toml
OPENAI_CHAT_MODEL = "gpt-4.1-mini"
OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
FEEDBACK_FORM_URL = "https://example.com/feedback"
```

Do not upload `.env` or commit `.streamlit/secrets.toml`.

### App visibility

After deployment, review the app's sharing settings:

- choose public access for an open demonstration; or
- choose private access and add permitted viewers.

A private repository does not automatically require the application to remain private. Community Cloud currently allows only one private app at a time; if the earlier CDIP deployment is private, make one app public or remove the older private app before keeping this variant private.

### Updating the application

1. Make and test changes locally.
2. Run `python -m pytest -q`.
3. Re-run the relevant evaluation or artifact audit if data or chatbot logic changed.
4. Commit and push to `main`.
5. Watch the Streamlit Cloud logs during redeployment.
6. Repeat the post-deployment checklist in Section 13.

### Rollback

If a release fails, run `git revert <bad-release-commit>` on `main` and push the new revert commit. This preserves a traceable history, and the versioned database and index make restarts deterministic.

## 13. Post-deployment acceptance checklist

Confirm the following after first deployment and after material updates:

- [ ] The application loads without a Python exception.
- [ ] Corpus shows 36 source records, including `DOC036`.
- [ ] Agency and topic filters work.
- [ ] Source links open the intended public documents.
- [ ] Keyword search returns page-aware evidence for `wetland restoration`.
- [ ] Keyword search returns page-aware evidence for `invasive carp`.
- [ ] Semantic search works when the API secret is configured.
- [ ] All 15 wiki pages render through **Entity type** then **Entity** navigation.
- [ ] Wiki pages do not display YAML fields such as `generated_at` or `generation_method`.
- [ ] The chatbot answers a supported question with document/page citations.
- [ ] **Core findings**, the cited supporting-document list, and **Retrieved evidence** agree.
- [ ] An out-of-corpus question produces an insufficient-evidence response.
- [ ] Evaluation metrics show 982 chunks, 9,612 entity mentions, 1,389 relations, and 15 wiki pages.
- [ ] The official 10-question evaluation report displays and downloads without internal engineering or holdout questions.
- [ ] A reboot retains the same corpus and index without rebuilding.
- [ ] App visibility matches the owner's intended public or private setting and does not alter the earlier CDIP app.
- [ ] The deployed Git commit and final `*.streamlit.app` URL are recorded for rollback and handoff.
- [ ] The OpenAI project usage dashboard shows expected, bounded activity.

## 14. Troubleshooting

| Symptom | Likely cause | Action |
|---|---|---|
| `.venv/bin/activate` is missing | Virtual environment was not created | Install `python3-venv` and recreate the environment |
| `ensurepip` failed | Ubuntu venv package is missing | Follow Section 11's venv repair commands |
| Chat input is disabled | `OPENAI_API_KEY` is missing | Add the local or Streamlit secret and restart |
| Semantic search reports unavailable | Key missing, index missing/stale, or model mismatch | Confirm secret, index files, manifest, and embedding model |
| Keyword search returns nothing | Terms are absent or too restrictive | Use fewer, more specific corpus terms |
| Chatbot abstains despite promising evidence | Scope or coverage validation rejected the answer | Split the question and record the case for review |
| App shows a sleep page | Community Cloud hibernated after inactivity | Wake the app from the displayed page |
| Chat history disappeared | Session reset or app restart | Save important answers outside the app |
| Provider timeout or rate-limit error | OpenAI service, quota, or project limit | Wait, inspect provider usage, and retry once |
| App fails during cloud build | Dependency or Python mismatch | Confirm `requirements.txt` and Python 3.12 |
| App exceeds resource limits | Memory or CPU pressure | Reboot, inspect logs, and avoid runtime rebuilding |

## 15. Responsible use

This application organizes public documents and generates AI-assisted answers. It is not an authoritative conservation decision system.

Users must:

- verify consequential claims against original cited sources;
- disclose that chatbot text is AI-assisted where appropriate;
- avoid submitting confidential or personal data;
- preserve citations when copying answers;
- distinguish corpus absence from real-world absence; and
- seek qualified domain review before using results for policy, legal, funding, or management decisions.

## 16. Related documentation

- [README](README.md)
- [Deployment guide](DEPLOYMENT.md)
- [Technical implementation report](TECHNICAL_IMPLEMENTATION_REPORT.md)
- [Project roadmap](ROADMAP.md)
- [Variant requirements and acceptance record](VARIANT_REQUIREMENTS.md)
- [Variant validator report](outputs/variant_status_report.md)
- [Variant chatbot smoke audit](outputs/variant_acceptance_smoke.md)
- [DOC036-centered holdout first-run audit](outputs/variant_holdout_v1_first_run_audit.md)
- [Inherited official answer audit](outputs/full_demo_correctness_audit.md)
