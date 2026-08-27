from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from src.conservation_intelligence.chatbot import answer_question
from src.conservation_intelligence.paths import DATABASE_PATH, PROJECT_ROOT, WIKI_DIR
from src.conservation_intelligence.wiki import clean_wiki_evidence, validate_wiki_page


CITATION_RE = re.compile(r"\[(DOC\d{3}), pp?\. [^\]]+\]")
FACT_CITATION_RE = re.compile(
    r"\[(DOC\d{3})(?:, pp?\. ([^\]]+))?\]\s*$"
)
WIKI_LINK_RE = re.compile(r"\]\(([^)]+\.md)\)")


@dataclass
class NeverCalledProvider:
    model: str = "never-called"
    calls: int = 0

    def answer(self, question: str, evidence: str, wiki_context: str) -> str:
        self.calls += 1
        raise AssertionError("The structured wetland summary must not call the model")


def test_precomputed_corpus_is_complete_and_referentially_sound() -> None:
    connection = sqlite3.connect(DATABASE_PATH)
    assert connection.execute("SELECT COUNT(*) FROM documents").fetchone()[0] == 36
    assert connection.execute("SELECT COUNT(*) FROM chunks").fetchone()[0] == 982
    assert connection.execute("SELECT COUNT(*) FROM entities").fetchone()[0] == 9612
    assert connection.execute("SELECT COUNT(*) FROM relations").fetchone()[0] == 1389
    assert connection.execute("SELECT COUNT(*) FROM wiki_pages").fetchone()[0] == 15

    orphan_chunks = connection.execute(
        "SELECT COUNT(*) FROM chunks c LEFT JOIN documents d ON d.doc_id = c.doc_id "
        "WHERE d.doc_id IS NULL"
    ).fetchone()[0]
    orphan_entities = connection.execute(
        "SELECT COUNT(*) FROM entities e LEFT JOIN chunks c ON c.chunk_id = e.chunk_id "
        "WHERE c.chunk_id IS NULL"
    ).fetchone()[0]
    orphan_relations = connection.execute(
        "SELECT COUNT(*) FROM relations r LEFT JOIN chunks c ON c.chunk_id = r.chunk_id "
        "WHERE c.chunk_id IS NULL"
    ).fetchone()[0]
    mismatched_relation_documents = connection.execute(
        "SELECT COUNT(*) FROM relations r JOIN chunks c ON c.chunk_id = r.chunk_id "
        "WHERE r.doc_id != c.doc_id"
    ).fetchone()[0]
    connection.close()

    assert orphan_chunks == 0
    assert orphan_entities == 0
    assert orphan_relations == 0
    assert mismatched_relation_documents == 0


def test_required_relation_types_are_present() -> None:
    required = {
        "species_uses_habitat",
        "threat_affects_species",
        "agency_manages_program",
        "document_mentions_location",
        "document_mentions_species",
    }
    connection = sqlite3.connect(DATABASE_PATH)
    actual = {
        row[0] for row in connection.execute("SELECT DISTINCT relation FROM relations")
    }
    connection.close()
    assert required <= actual


def test_required_wetland_summary_uses_canonical_evidence_without_model() -> None:
    provider = NeverCalledProvider()

    result = answer_question(
        "Generate a short cited summary of wetland conservation evidence in the corpus.",
        provider,
    )

    assert result.generation_status == "deterministic"
    assert result.retrieval_mode == "structured_wetland_summary"
    assert "Community Health Index" in result.answer
    assert "[DOC002, pp. 6-8]" in result.answer
    assert provider.calls == 0


def test_versioned_wiki_is_valid_and_cites_only_known_documents() -> None:
    connection = sqlite3.connect(DATABASE_PATH)
    known_ids = {row[0] for row in connection.execute("SELECT doc_id FROM documents")}
    connection.close()

    pages = sorted(WIKI_DIR.glob("*/*.md"))
    assert 10 <= len(pages) <= 20
    for page in pages:
        content = page.read_text(encoding="utf-8")
        assert validate_wiki_page(content) == []
        assert {match.group(1) for match in CITATION_RE.finditer(content)} <= known_ids


def test_wiki_facts_and_internal_links_are_traceable() -> None:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    for page in sorted(WIKI_DIR.glob("*/*.md")):
        content = page.read_text(encoding="utf-8")
        title_match = re.search(r"(?m)^title:\s*(.+)$", content)
        type_match = re.search(r"(?m)^entity_type:\s*(\S+)$", content)
        assert title_match and type_match
        title = json.loads(title_match.group(1))
        entity_type = type_match.group(1)

        facts_match = re.search(
            r"(?ms)^## Key facts\s*$\n(.*?)(?=^##\s)", content
        )
        assert facts_match
        facts = [
            line.removeprefix("- ").strip()
            for line in facts_match.group(1).splitlines()
            if line.startswith("- ")
        ]
        for fact in facts:
            citation_match = FACT_CITATION_RE.search(fact)
            assert citation_match
            evidence = " ".join(fact[: citation_match.start()].split())
            page_number = citation_match.group(2)
            page_clause = " AND c.page = ?" if page_number else ""
            parameters = [
                title.casefold(),
                entity_type,
                citation_match.group(1),
            ]
            if page_number:
                parameters.append(page_number)
            matching_rows = connection.execute(
                f"""
                SELECT e.evidence
                FROM entities e
                JOIN chunks c ON c.chunk_id = e.chunk_id
                WHERE e.normalized_name = ? AND e.entity_type = ?
                  AND e.doc_id = ?{page_clause}
                """,
                parameters,
            ).fetchall()
            assert evidence in {
                clean_wiki_evidence(row["evidence"], title) for row in matching_rows
            }

        for target in WIKI_LINK_RE.findall(content):
            resolved = (page.parent / target).resolve()
            assert resolved.is_relative_to(WIKI_DIR.resolve())
            assert resolved.exists()
    connection.close()


def test_streamlit_cloud_deployment_contract() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    deployment = (PROJECT_ROOT / "DEPLOYMENT.md").read_text(encoding="utf-8")
    requirements = (PROJECT_ROOT / "requirements.txt").read_text(encoding="utf-8")
    gitignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "Streamlit Community Cloud" in readme
    assert "Main file path: `app.py`" in deployment
    assert "Python version: `3.12`" in deployment
    assert "CharlesChen130/conservation-document-intelligence-variant" in deployment
    assert "streamlit==" in requirements
    assert ".env" in gitignore
    assert ".streamlit/secrets.toml" in gitignore
    assert (PROJECT_ROOT / "app.py").is_file()
    assert (PROJECT_ROOT / "TECHNICAL_IMPLEMENTATION_REPORT.md").is_file()
    assert (PROJECT_ROOT / "USER_MANUAL.md").is_file()
    assert (PROJECT_ROOT / "db" / "conservation.db").stat().st_size > 1_000_000
    assert (PROJECT_ROOT / "vector_index" / "chunks.faiss").stat().st_size > 1_000_000
    assert (PROJECT_ROOT / "vector_index" / "manifest.json").is_file()
