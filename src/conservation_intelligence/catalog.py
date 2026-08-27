from __future__ import annotations

import csv
import os
import tempfile
from pathlib import Path
from typing import Iterable

from .paths import METADATA_PATH


REQUIRED_COLUMNS = (
    "doc_id",
    "title",
    "year",
    "agency",
    "topic",
    "url",
    "local_file",
    "file_type",
    "download_status",
    "notes",
    "original_url",
    "resolved_url",
    "retrieved_at",
    "checksum_sha256",
    "extracted_file",
    "extraction_status",
    "page_count",
    "extracted_characters",
    "extraction_notes",
)
REQUIRED_DOC_IDS = tuple(f"DOC{number:03d}" for number in range(1, 37))


class CatalogError(ValueError):
    """Raised when source catalog data violates the project contract."""


def load_catalog(path: Path | None = None) -> list[dict[str, str]]:
    catalog_path = path or METADATA_PATH
    with catalog_path.open("r", encoding="utf-8", newline="") as catalog_file:
        reader = csv.DictReader(catalog_file)
        if reader.fieldnames is None:
            raise CatalogError("Source catalog has no header")
        missing = [column for column in REQUIRED_COLUMNS if column not in reader.fieldnames]
        if missing:
            raise CatalogError(f"Source catalog is missing columns: {', '.join(missing)}")
        return [{key: value or "" for key, value in row.items()} for row in reader]


def validate_catalog(rows: Iterable[dict[str, str]]) -> list[str]:
    row_list = list(rows)
    errors: list[str] = []
    doc_ids = [row.get("doc_id", "") for row in row_list]

    if len(row_list) != len(REQUIRED_DOC_IDS):
        errors.append(
            f"expected {len(REQUIRED_DOC_IDS)} rows, found {len(row_list)}"
        )
    if len(set(doc_ids)) != len(doc_ids):
        errors.append("doc_id values must be unique")

    missing_ids = sorted(set(REQUIRED_DOC_IDS) - set(doc_ids))
    unexpected_ids = sorted(set(doc_ids) - set(REQUIRED_DOC_IDS))
    if missing_ids:
        errors.append(f"missing IDs: {', '.join(missing_ids)}")
    if unexpected_ids:
        errors.append(f"unexpected IDs: {', '.join(unexpected_ids)}")

    for row in row_list:
        doc_id = row.get("doc_id", "<missing>")
        for field in ("title", "agency", "topic", "url", "original_url"):
            if not row.get(field, "").strip():
                errors.append(f"{doc_id}: missing {field}")
        url = row.get("url", "")
        if url and not url.startswith("https://"):
            errors.append(f"{doc_id}: source URL must use HTTPS")

    return errors


def save_catalog(rows: Iterable[dict[str, str]], path: Path | None = None) -> None:
    catalog_path = path or METADATA_PATH
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    row_list = list(rows)

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{catalog_path.name}.", suffix=".tmp", dir=catalog_path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as catalog_file:
            writer = csv.DictWriter(catalog_file, fieldnames=REQUIRED_COLUMNS, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(row_list)
        temporary_path.replace(catalog_path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
