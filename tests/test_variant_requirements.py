from __future__ import annotations


from src.conservation_intelligence.catalog import load_catalog
from src.conservation_intelligence.database import connect_database
from src.conservation_intelligence.repository import keyword_search


DOC036_CHECKSUM = (
    "a36fe284e40334da177486c491eb2610e3c621bbeca7fdbcd1eb049d4cd75dec"
)


def test_pi_supplied_strategy_is_traceable_and_fully_chunked() -> None:
    row = next(item for item in load_catalog() if item["doc_id"] == "DOC036")

    assert row["title"] == "The Missouri Comprehensive Conservation Strategy"
    assert row["year"] == "2022"
    assert row["agency"] == "Missouri Department of Conservation"
    assert row["page_count"] == "566"
    assert row["checksum_sha256"] == DOC036_CHECKSUM
    assert row["local_file"] == "data/raw/2022-Missouri-CCS.pdf"

    with connect_database() as connection:
        document = connection.execute(
            "SELECT title, checksum_sha256 FROM documents WHERE doc_id = ?",
            ("DOC036",),
        ).fetchone()
        chunk_count = connection.execute(
            "SELECT COUNT(*) FROM chunks WHERE doc_id = ?", ("DOC036",)
        ).fetchone()[0]

    assert document is not None
    assert document["title"] == row["title"]
    assert document["checksum_sha256"] == DOC036_CHECKSUM
    assert chunk_count == 258


def test_pi_supplied_strategy_is_retrievable_by_distinctive_title() -> None:
    with connect_database() as connection:
        results = keyword_search(
            connection,
            "Missouri Comprehensive Conservation Strategy",
            limit=5,
        )

    assert results
    assert all(result.doc_id == "DOC036" for result in results)
    assert all(result.page for result in results)

