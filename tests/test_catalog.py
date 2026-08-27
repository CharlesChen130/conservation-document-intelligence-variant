from __future__ import annotations

from src.conservation_intelligence.catalog import load_catalog, validate_catalog


def test_required_catalog_is_complete_and_valid():
    rows = load_catalog()

    assert len(rows) == 36
    assert validate_catalog(rows) == []

