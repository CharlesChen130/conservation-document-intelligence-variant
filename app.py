from __future__ import annotations

import os

import pandas as pd
import streamlit as st

from src.conservation_intelligence.chatbot import (
    OpenAIAnswerProvider,
    answer_question,
    format_chatbot_response,
)
from src.conservation_intelligence.database import connect_database, initialize_database
from src.conservation_intelligence.paths import METADATA_PATH, OUTPUTS_DIR, ensure_directories
from src.conservation_intelligence.evaluation import load_evaluation_spec
from src.conservation_intelligence.repository import keyword_search
from src.conservation_intelligence.semantic import (
    OpenAIEmbeddingProvider,
    semantic_index_is_current,
    semantic_search,
)
from src.conservation_intelligence.settings import load_environment, load_settings
from src.conservation_intelligence.wiki import (
    WIKI_CATEGORY_LABELS,
    load_wiki_documents,
)


load_environment()
st.set_page_config(
    page_title="Conservation Document Intelligence",
    page_icon="🌿",
    layout="wide",
)
ensure_directories()
initialize_database()
settings = load_settings()

st.title("Conservation Document Intelligence")
st.warning(
    "Research prototype: AI-generated answers may contain errors. "
    "Verify important conclusions using the cited public source documents."
)

corpus_tab, search_tab, wiki_tab, chatbot_tab, evaluation_tab = st.tabs(
    ["Corpus", "Search", "Wiki", "Chatbot", "Evaluation"]
)

with corpus_tab:
    st.header("Corpus")
    if METADATA_PATH.exists() and METADATA_PATH.stat().st_size > 0:
        metadata = pd.read_csv(METADATA_PATH, dtype=str).fillna("")
        if metadata.empty:
            st.info("The source catalog has been initialized and will be populated in Phase 1.")
        else:
            metric_columns = st.columns(3)
            metric_columns[0].metric("Source records", len(metadata))
            metric_columns[1].metric(
                "Acquired",
                int(metadata["download_status"].isin(["downloaded", "unchanged"]).sum()),
            )
            metric_columns[2].metric(
                "Text extracted",
                int(metadata["extraction_status"].isin(["extracted", "low_text"]).sum()),
            )
            filter_columns = st.columns(2)
            agencies = filter_columns[0].multiselect(
                "Agency",
                sorted(value for value in metadata["agency"].unique() if value),
            )
            topics = filter_columns[1].multiselect(
                "Topic",
                sorted(value for value in metadata["topic"].unique() if value),
            )
            visible = metadata
            if agencies:
                visible = visible[visible["agency"].isin(agencies)]
            if topics:
                visible = visible[visible["topic"].isin(topics)]
            st.dataframe(
                visible[
                    [
                        "doc_id",
                        "title",
                        "year",
                        "agency",
                        "topic",
                        "download_status",
                        "extraction_status",
                        "page_count",
                        "url",
                    ]
                ],
                use_container_width=True,
                hide_index=True,
                column_config={"url": st.column_config.LinkColumn("Source")},
            )
    else:
        st.info("The source catalog has not been generated yet.")

with search_tab:
    st.header("Search")
    semantic_ready = semantic_index_is_current()
    search_mode = st.radio(
        "Retrieval mode",
        ["Keyword", "Semantic"],
        horizontal=True,
        help="Semantic search requires a current FAISS index and an embedding API key.",
    )
    with st.form("corpus_search"):
        query = st.text_input(
            "Search the conservation corpus",
            placeholder="e.g. wetland restoration or invasive carp",
        )
        top_k = st.slider("Number of results", min_value=3, max_value=15, value=6)
        submitted = st.form_submit_button("Search", type="primary")

    if search_mode == "Semantic" and not semantic_ready:
        st.info("The semantic adapter is ready, but the corpus FAISS index has not been built yet.")

    if submitted:
        if not query.strip():
            st.warning("Enter a search query.")
        else:
            try:
                if search_mode == "Keyword":
                    with connect_database() as connection:
                        results = keyword_search(connection, query, limit=top_k)
                else:
                    if not semantic_ready:
                        raise ValueError("Build the semantic index before using semantic search.")
                    provider = OpenAIEmbeddingProvider(model=settings.models.embedding)
                    results = semantic_search(provider, query, limit=top_k)

                if not results:
                    st.info("No matching evidence was found.")
                for result in results:
                    page = f", pp. {result.page}" if "-" in result.page else (
                        f", p. {result.page}" if result.page else ""
                    )
                    st.markdown(
                        f"**[{result.doc_id}{page}] {result.title}** · "
                        f"[Open source]({result.source_url}) · score {result.score:.3f}"
                    )
                    snippet = result.text[:700] + ("…" if len(result.text) > 700 else "")
                    st.write(snippet)
            except Exception as error:
                st.error(str(error))

with wiki_tab:
    st.header("LLM Wiki")
    wiki_documents = load_wiki_documents()
    if not wiki_documents:
        st.info("Evidence-backed wiki pages will appear here after extraction.")
    else:
        available_categories = [
            category
            for category in WIKI_CATEGORY_LABELS
            if any(page.category == category for page in wiki_documents)
        ]
        selector_columns = st.columns([1, 2])
        selected_category = selector_columns[0].selectbox(
            "Entity type",
            available_categories,
            format_func=lambda category: WIKI_CATEGORY_LABELS.get(
                category, category.replace("-", " ").title()
            ),
        )
        category_documents = [
            page for page in wiki_documents if page.category == selected_category
        ]
        selected_title = selector_columns[1].selectbox(
            "Entity",
            [page.title for page in category_documents],
        )
        selected_document = next(
            page for page in category_documents if page.title == selected_title
        )
        if selected_document.mentions or selected_document.documents:
            st.caption(
                f"{selected_document.entity_type.replace('_', ' ').title()} | "
                f"{selected_document.mentions:,} mentions across "
                f"{selected_document.documents:,} public documents"
            )
        st.markdown(selected_document.body)

with chatbot_tab:
    st.header("Citation-based chatbot")
    api_configured = bool(os.getenv("OPENAI_API_KEY"))
    if not api_configured:
        st.warning("OPENAI_API_KEY is not configured; provider-based answering is disabled.")
    st.caption(
        "The Answer directly summarizes the validated claims. Key supporting findings show "
        "those claims point by point; the Supporting documents section lists only their cited sources. "
        "All retrieved evidence includes every passage considered."
    )
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    for message in st.session_state.chat_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("sources"):
                with st.expander("All retrieved evidence"):
                    st.caption(
                        "Passages considered during answer generation; not every passage "
                        "is cited in the Answer or key supporting findings."
                    )
                    for source in message["sources"]:
                        st.markdown(
                            f"**{source['citation']} — {source['title']}** · "
                            f"[Open source]({source['url']})"
                        )
                        st.write(source["snippet"])

    prompt = st.chat_input(
        "Ask a conservation question",
        disabled=not api_configured,
        max_chars=settings.chatbot.max_question_characters,
    )
    if prompt:
        user_message_count = sum(
            message["role"] == "user" for message in st.session_state.chat_messages
        )
        if user_message_count >= 20:
            st.error("This session has reached its 20-question research-demo limit.")
        else:
            st.session_state.chat_messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            with st.chat_message("assistant"):
                with st.spinner("Retrieving and checking evidence..."):
                    try:
                        chat_model = os.getenv("OPENAI_CHAT_MODEL") or settings.models.chat
                        provider = OpenAIAnswerProvider(
                            model=chat_model,
                            max_output_tokens=settings.chatbot.max_output_tokens,
                        )
                        embedding_provider = OpenAIEmbeddingProvider(
                            model=(
                                os.getenv("OPENAI_EMBEDDING_MODEL")
                                or settings.models.embedding
                            )
                        )
                        result = answer_question(
                            prompt,
                            provider,
                            embedding_provider=embedding_provider,
                            top_k=settings.chatbot.top_k,
                            candidate_k=settings.retrieval.candidate_k,
                            max_question_characters=settings.chatbot.max_question_characters,
                        )
                        display_answer = format_chatbot_response(result.answer, result.evidence)
                        st.markdown(display_answer)
                        sources = []
                        if result.evidence:
                            with st.expander("All retrieved evidence"):
                                st.caption(
                                    "Passages considered during answer generation; not every "
                                    "passage is cited in the Answer or key supporting findings."
                                )
                                for item in result.evidence:
                                    page = (
                                        f"pp. {item.page}"
                                        if "-" in item.page
                                        else (f"p. {item.page}" if item.page else "")
                                    )
                                    source_citation = (
                                        f"[{item.doc_id}, {page}]"
                                        if page
                                        else f"[{item.doc_id}]"
                                    )
                                    snippet = item.text[:700] + (
                                        "…" if len(item.text) > 700 else ""
                                    )
                                    st.markdown(
                                        f"**{source_citation} — {item.title}** · "
                                        f"[Open source]({item.source_url})"
                                    )
                                    st.write(snippet)
                                    sources.append(
                                        {
                                            "citation": source_citation,
                                            "title": item.title,
                                            "url": item.source_url,
                                            "snippet": snippet,
                                        }
                                    )
                        st.session_state.chat_messages.append(
                            {"role": "assistant", "content": display_answer, "sources": sources}
                        )
                    except Exception as error:
                        st.error(f"The grounded answer could not be produced: {error}")

with evaluation_tab:
    st.header("Evaluation")
    with connect_database() as connection:
        counts = {
            "Chunks": connection.execute("SELECT COUNT(*) FROM chunks").fetchone()[0],
            "Entity mentions": connection.execute("SELECT COUNT(*) FROM entities").fetchone()[0],
            "Relations": connection.execute("SELECT COUNT(*) FROM relations").fetchone()[0],
            "Wiki pages": connection.execute("SELECT COUNT(*) FROM wiki_pages").fetchone()[0],
        }
    metric_columns = st.columns(len(counts))
    for metric_column, (label, value) in zip(metric_columns, counts.items()):
        metric_column.metric(label, value)

    evaluation_spec = load_evaluation_spec()
    official_questions = evaluation_spec["official_questions"]
    st.selectbox("Official demo question", official_questions)
    st.caption("These are the 10 document-defined evaluation questions.")

    st.markdown(
        """
        Review each answer using the full evidence chain:

        - **Relevance:** Does it address the question?
        - **Grounding:** Does each factual paragraph have a citation?
        - **Citation quality:** Does the cited page actually support the claim?
        - **Completeness:** Is important retrieved evidence omitted?
        - **Abstention:** Does the system decline when evidence is insufficient?
        """
    )

    report_path = OUTPUTS_DIR / "demo_answers.md"
    if report_path.exists():
        report = report_path.read_text(encoding="utf-8")
        official_count = len(official_questions)
        first_internal_heading = f"\n## {official_count + 1}."
        report = report.split(first_internal_heading, maxsplit=1)[0].rstrip() + "\n"
        report = "\n".join(
            (
                f"Public report scope: {official_count} official requirement questions."
                if line.startswith("Retrieval coverage:")
                else line
            )
            for line in report.splitlines()
        )
        full_contract = (
            f"Questions 1-{official_count} reproduce the required demo questions from the project "
            "description. Later questions are additional engineering checks and do not replace the "
            "official set."
        )
        public_contract = (
            f"Questions 1-{official_count} reproduce the required demo questions from the project "
            "description. This public report contains only the official set."
        )
        report = report.replace(full_contract, public_contract).rstrip() + "\n"
        st.download_button(
            "Download official evaluation report",
            report,
            file_name="official_demo_answers.md",
            mime="text/markdown",
        )
        with st.expander("View official evaluation report"):
            st.markdown(report)

    feedback_url = os.getenv("FEEDBACK_FORM_URL")
    if feedback_url:
        st.link_button("Open feedback form", feedback_url)
    else:
        st.info(
            "External feedback is not configured. Set FEEDBACK_FORM_URL to a Google Forms, "
            "Qualtrics, or Microsoft Forms survey; cloud instance storage is not durable."
        )
