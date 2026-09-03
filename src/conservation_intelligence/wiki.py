from __future__ import annotations

import json
import posixpath
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml

from .database import connect_database
from .paths import DATABASE_PATH, PROJECT_ROOT, WIKI_DIR
from .repository import evidence_quality_issues


CATEGORY_TYPES = {
    "species": ("species",),
    "habitats": ("habitat", "wetland"),
    "locations": ("location", "river"),
    "threats": ("threat",),
    "agencies": ("agency",),
}

WIKI_CATEGORY_LABELS = {
    "species": "Species",
    "habitats": "Habitats",
    "locations": "Locations",
    "threats": "Threats",
    "agencies": "Agencies",
}
FRONT_MATTER_PATTERN = re.compile(
    r"\A---[ \t]*\r?\n(?P<metadata>.*?)\r?\n---[ \t]*(?:\r?\n|\Z)",
    flags=re.DOTALL,
)
CITATION_PATTERN = re.compile(r"\[DOC\d{3}(?:, p{1,2}\. \d+(?:-\d+)?)?\]")
WIKI_NOISE_PATTERN = re.compile(
    r"\b(?:table of contents|literature cited|cited references|bibliography|"
    r"taxa scientific name|list of acronyms|index of tables)\b|(?:\.\s*){8,}",
    flags=re.IGNORECASE,
)
WIKI_FRAGMENT_PATTERN = re.compile(
    r"\b(?:image details|scientific name|by the numbers|in this section|"
    r"stay in touch|download issue|fiscal year comparison|budget summary|"
    r"where we have been|report and recommendations|action plan outcome|"
    r"newsroom|get the latest news|page\s+\d+|p\s*a\s*g\s*e\s*\|)\b",
    flags=re.IGNORECASE,
)
FACT_VERB_PATTERN = re.compile(
    r"\b(?:is|are|was|were|has|have|provid|support|affect|threat|manage|"
    r"monitor|protect|restore|conserv|occur|found|include|reduce|increase|"
    r"declin|improv|require|use)\w*\b",
    flags=re.IGNORECASE,
)
SEMANTIC_RELATION_TYPES = {
    "species_uses_habitat": ("species", "habitat"),
    "threat_affects_species": ("threat", "species"),
    "agency_manages_program": ("agency", "program"),
}
FINITE_VERB_PATTERN = re.compile(
    r"\b(?:is|are|was|were|has|have|had|will|would|can|could|may|might|must|"
    r"should|provides?|supports?|affects?|manages?|monitors?|protects?|"
    r"restores?|conserves?|occurs?|includes?|reduces?|increases?|declines?|"
    r"improves?|requires?|uses?|leads?|continues?|collaborated|reported|"
    r"found|estimated|undertakes?|works?|conducted|placed|gave|helps?|shows?|"
    r"indicates?|covers?|involves?|identified|listed|mentioned|agreed|signed|"
    r"tasked|focused|maintains?|develops?|coordinates?|received|performed|"
    r"strives?|hired|partnered|contributes?)\b",
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class WikiPage:
    page_id: str
    title: str
    entity_type: str
    file_path: str
    content: str


@dataclass(frozen=True)
class WikiDocument:
    path: Path
    category: str
    title: str
    entity_type: str
    body: str
    mentions: int = 0
    documents: int = 0


def _metadata_integer(metadata: dict[str, object], key: str) -> int:
    try:
        return int(metadata.get(key, 0) or 0)
    except (TypeError, ValueError):
        return 0


def parse_wiki_document(path: Path, *, wiki_dir: Path = WIKI_DIR) -> WikiDocument:
    """Load a generated Wiki page without exposing its YAML front matter."""
    content = path.read_text(encoding="utf-8")
    match = FRONT_MATTER_PATTERN.match(content)
    metadata: dict[str, object] = {}
    body = content
    if match:
        loaded = yaml.safe_load(match.group("metadata")) or {}
        if isinstance(loaded, dict):
            metadata = {str(key): value for key, value in loaded.items()}
        body = content[match.end() :].lstrip()

    relative_path = path.resolve().relative_to(wiki_dir.resolve())
    category = relative_path.parts[0] if len(relative_path.parts) > 1 else ""
    title = str(metadata.get("title") or path.stem.replace("-", " ").title())
    fallback_types = CATEGORY_TYPES.get(category, (category.rstrip("s"),))
    entity_type = str(metadata.get("entity_type") or fallback_types[0])
    return WikiDocument(
        path=path,
        category=category,
        title=title,
        entity_type=entity_type,
        body=body,
        mentions=_metadata_integer(metadata, "mentions"),
        documents=_metadata_integer(metadata, "documents"),
    )


def load_wiki_documents(*, wiki_dir: Path = WIKI_DIR) -> list[WikiDocument]:
    if not wiki_dir.exists():
        return []
    documents = [
        parse_wiki_document(path, wiki_dir=wiki_dir)
        for path in wiki_dir.glob("*/*.md")
    ]
    return sorted(
        documents,
        key=lambda item: (
            tuple(CATEGORY_TYPES).index(item.category)
            if item.category in CATEGORY_TYPES
            else len(CATEGORY_TYPES),
            item.title.casefold(),
        ),
    )


def slugify(value: str) -> str:
    value = value.casefold().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or "entity"


def citation(doc_id: str, page: str) -> str:
    if not page:
        return f"[{doc_id}]"
    prefix = "pp." if "-" in page else "p."
    return f"[{doc_id}, {prefix} {page}]"


def clean_wiki_evidence(text: str, entity_name: str = "") -> str:
    """Normalize extraction-only PDF artifacts without changing the claim."""
    normalized = re.sub(r"\s+", " ", text).strip()
    normalized = re.sub(r"[\u200b-\u200d\ufeff]", "", normalized)
    normalized = re.sub(r"^[•▪◆■✦×]+\s*", "", normalized)
    normalized = re.sub(r"^Introduction\s+", "", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"(?<=\w)\s*-\s+(?=[a-z])", "", normalized)
    normalized = re.sub(r"\b(f[fil])\s+(?=[a-z])", r"\1", normalized)
    normalized = re.sub(
        r"\b([B-HJ-Z])\s+([a-z]{3,})\b",
        lambda match: match.group(1) + match.group(2),
        normalized,
    )
    normalized = re.sub(
        r"\b(?:[A-Z]\s+){2,}[A-Z]\b",
        lambda match: re.sub(r"\s+", "", match.group(0)),
        normalized,
    )
    if entity_name:
        entity_variant = rf"{re.escape(entity_name)}s?"
        if re.match(rf"^{entity_variant}\b", normalized, flags=re.IGNORECASE):
            sentence_starter = re.search(
                r"\b(?:There|Over|During|Since|More than|About)\b",
                normalized[len(entity_name) : 100],
            )
            if sentence_starter:
                offset = len(entity_name) + sentence_starter.start()
                candidate = normalized[offset:]
                if FINITE_VERB_PATTERN.search(candidate):
                    normalized = candidate
            repeated_statement = list(
                re.finditer(
                    rf"\b{entity_variant}\s+(?:is|are|has|have|will)\b",
                    normalized[:140],
                    flags=re.IGNORECASE,
                )
            )
            if repeated_statement and repeated_statement[-1].start() > 0:
                normalized = normalized[repeated_statement[-1].start() :]
        heading = re.match(
            rf"^{re.escape(entity_name)}\s+(.+)$",
            normalized,
            flags=re.IGNORECASE,
        )
        if heading and re.search(
            rf"\b{re.escape(entity_name)}(?:'s|’s)?\b",
            heading.group(1)[:120],
            flags=re.IGNORECASE,
        ):
            normalized = heading.group(1)
    normalized = re.sub(
        r"^Why\s+[A-Z][A-Za-z-]+\s+Matter\s+",
        "",
        normalized,
    )
    normalized = re.sub(
        r"^[A-Z][^.!?]{0,60}\bAbout\s+(?=\d)",
        "About ",
        normalized,
    )
    return normalized


def wiki_evidence_quality_issues(
    text: str,
    chunk_text: str = "",
    *,
    entity_name: str = "",
    entity_type: str = "",
) -> list[str]:
    """Reject extraction fragments that are traceable but unsuitable as wiki facts."""
    normalized = clean_wiki_evidence(text, entity_name)
    words = re.findall(r"\b\w+\b", normalized)
    issues: list[str] = []
    if len(words) < 6:
        issues.append("too_short")
    if len(normalized) > 450:
        issues.append("too_long")
    if not re.search(r"[.!?]$", normalized):
        issues.append("incomplete_ending")
    if re.search(r"\b(?:Fig|St|[A-Z])\.$", normalized):
        issues.append("abbreviation_ending")
    if normalized.count("(") != normalized.count(")"):
        issues.append("unbalanced_parenthesis")
    if entity_name and re.match(
        rf"^{re.escape(entity_name)}\s*[,;:]",
        normalized,
        flags=re.IGNORECASE,
    ):
        issues.append("entity_list_fragment")
    first_word = re.search(r"[A-Za-z]", normalized)
    if (
        first_word is None
        or not normalized[first_word.start()].isupper()
        or normalized.startswith(("(", "[", "'", "“", "”", "‘", "’"))
    ):
        issues.append("incomplete_start")
    if WIKI_NOISE_PATTERN.search(normalized) or WIKI_FRAGMENT_PATTERN.search(normalized):
        issues.append("document_scaffolding")
    if "|" in normalized or re.search(
        r"\b(?:Overview|Conservation Newsroom)\b", normalized[:120]
    ):
        issues.append("document_scaffolding")
    finite_verb = FINITE_VERB_PATTERN.search(normalized)
    if not finite_verb:
        issues.append("no_finite_verb")
    elif re.search(r"\band\s+$", normalized[: finite_verb.start()]):
        issues.append("leading_conjunction_predicate")
    repeated_lead = re.match(r"^(\w+(?:\s+\w+)?)\s+\1\b", normalized, re.IGNORECASE)
    if repeated_lead:
        issues.append("repeated_heading")
    if entity_name:
        title_lead = re.match(
            rf"^{re.escape(entity_name)}\s+([A-Za-z]+)\b",
            normalized,
            flags=re.IGNORECASE,
        )
        title_lead_is_verb = bool(
            title_lead and FINITE_VERB_PATTERN.fullmatch(title_lead.group(1))
        )
        if (
            title_lead
            and title_lead.group(1).casefold() != "and"
            and not title_lead_is_verb
        ):
            issues.append("entity_heading_compound")
        if (
            title_lead
            and title_lead.group(1).casefold() == "are"
            and not entity_name.casefold().endswith("s")
        ):
            issues.append("subject_verb_mismatch")
    if entity_type == "location" and entity_name:
        title_lead = re.match(
            rf"^{re.escape(entity_name)}\s+([A-Za-z]+)\b",
            normalized,
            flags=re.IGNORECASE,
        )
        allowed_leads = {
            "and", "are", "can", "could", "has", "have", "had", "is",
            "may", "might", "must", "should", "was", "were", "will", "would",
        }
        if title_lead and title_lead.group(1).casefold() not in allowed_leads:
            issues.append("location_name_compound")
        if entity_name.casefold() == "united states":
            us_lead = re.match(r"^US\s+([A-Za-z]+)\b", normalized)
            if us_lead and not FINITE_VERB_PATTERN.fullmatch(us_lead.group(1)):
                issues.append("location_name_compound")
    if entity_type in {"species", "threat"} and entity_name:
        compound = re.match(
            rf"^{re.escape(entity_name)}\s+([A-Z][A-Za-z]+)\b",
            normalized,
            flags=re.IGNORECASE,
        )
        if compound and compound.group(1).casefold() not in {"the"}:
            issues.append("entity_heading_compound")
        if compound and compound.group(1).casefold() == "the" and not re.search(
            rf"\b{re.escape(entity_name)}\b",
            normalized[len(entity_name) + 1 :],
            flags=re.IGNORECASE,
        ):
            issues.append("entity_heading_compound")
    if any(symbol in normalized for symbol in ("✦", "", "▪", "◆", "■")):
        issues.append("embedded_bullet")
    if re.search(r"\b(?:geese|mice|people|children)\s+is\b", normalized, re.IGNORECASE):
        issues.append("subject_verb_mismatch")
    if re.match(r"^[A-Z][A-Za-z]+\s+\d+\s+(?:where|which|that)\b", normalized):
        issues.append("page_header_fragment")
    if entity_name and re.match(
        rf"^{re.escape(entity_name)}\s+and\s+[A-Z][^.!?]{{0,100}},\s+is\b",
        normalized,
        flags=re.IGNORECASE,
    ):
        issues.append("missing_compound_subject")
    if normalized.count(";") >= 3:
        issues.append("list_fragment")
    if re.search(r"\b(?:https?://|www\.)", normalized, flags=re.IGNORECASE):
        issues.append("embedded_url")
    if re.search(r"[A-Za-z)]/[A-Z]", normalized):
        issues.append("caption_fragment")
    if "\ufffd" in normalized:
        issues.append("replacement_character")
    issues.extend(evidence_quality_issues(chunk_text))
    return list(dict.fromkeys(issues))


def select_entities(
    connection: sqlite3.Connection,
    per_category: int = 3,
    minimum_facts: int = 1,
) -> list[tuple[str, str, str, int, int]]:
    selected: list[tuple[str, str, str, int, int]] = []
    for category, entity_types in CATEGORY_TYPES.items():
        placeholders = ",".join("?" for _ in entity_types)
        rows = connection.execute(
            f"""
            SELECT name, entity_type, COUNT(*) AS mentions, COUNT(DISTINCT doc_id) AS documents
            FROM entities
            WHERE entity_type IN ({placeholders})
            GROUP BY normalized_name, entity_type
            ORDER BY documents DESC, mentions DESC, name
            """,
            [*entity_types],
        ).fetchall()
        category_pages = 0
        for row in rows:
            if len(
                _entity_evidence(
                    connection,
                    row["name"],
                    row["entity_type"],
                    limit=minimum_facts,
                )
            ) < minimum_facts:
                continue
            selected.append(
                (
                    category,
                    row["name"],
                    row["entity_type"],
                    row["mentions"],
                    row["documents"],
                )
            )
            category_pages += 1
            if category_pages == per_category:
                break
    return selected


def _entity_evidence(
    connection: sqlite3.Connection, name: str, entity_type: str, limit: int = 6
) -> list[sqlite3.Row]:
    rows = connection.execute(
        """
        SELECT e.evidence, e.doc_id, e.chunk_id, c.page, d.title, d.agency, d.topic,
               COALESCE(NULLIF(d.resolved_url, ''), d.url) AS source_url,
               c.chunk_text
        FROM entities AS e
        JOIN chunks AS c ON c.chunk_id = e.chunk_id
        JOIN documents AS d ON d.doc_id = e.doc_id
        WHERE e.normalized_name = ? AND e.entity_type = ?
        ORDER BY e.doc_id, c.page, e.chunk_id
        """,
        (name.casefold(), entity_type),
    ).fetchall()

    scored: list[tuple[float, sqlite3.Row]] = []
    for row in rows:
        text = re.sub(r"\s+", " ", row["evidence"]).strip()
        if wiki_evidence_quality_issues(
            text,
            row["chunk_text"],
            entity_name=name,
            entity_type=entity_type,
        ):
            continue
        score = 6 - abs(len(text) - 180) / 90
        if 60 <= len(text) <= 300:
            score += 4
        if FACT_VERB_PATTERN.search(text):
            score += 4
        if re.match(r"^[A-Z][^.]{0,80}\b(?:is|are|will|has|have)\b", text):
            score += 2
        score -= 1.5 * text.count("•")
        score -= max(0, text.count(",") - 10) * 0.25
        if re.search(r"\bPage\s+\d+\b|[≥≤]", text, flags=re.IGNORECASE):
            score -= 3
        scored.append((score, row))

    scored.sort(
        key=lambda item: (
            -item[0],
            item[1]["doc_id"],
            item[1]["page"] or "",
            item[1]["chunk_id"],
        )
    )
    selected: list[sqlite3.Row] = []
    selected_chunks: set[str] = set()
    selected_evidence: set[str] = set()
    per_document: dict[str, int] = {}
    for max_per_document in (1, 2):
        for _, row in scored:
            cleaned_evidence = clean_wiki_evidence(row["evidence"], name)
            normalized_evidence = re.sub(
                r"\W+", " ", cleaned_evidence.casefold()
            ).strip()
            if (
                row["chunk_id"] in selected_chunks
                or normalized_evidence in selected_evidence
            ):
                continue
            if per_document.get(row["doc_id"], 0) >= max_per_document:
                continue
            selected.append(row)
            selected_chunks.add(row["chunk_id"])
            selected_evidence.add(normalized_evidence)
            per_document[row["doc_id"]] = per_document.get(row["doc_id"], 0) + 1
            if len(selected) == limit:
                return selected
    return selected


def _semantic_related_entities(
    connection: sqlite3.Connection,
    name: str,
    *,
    limit: int = 8,
) -> list[dict[str, object]]:
    rows = connection.execute(
        """
        SELECT r.subject, r.relation, r.object, r.doc_id, r.chunk_id,
               r.evidence, r.confidence, c.page
        FROM relations AS r
        JOIN chunks AS c ON c.chunk_id = r.chunk_id
        WHERE (LOWER(r.subject) = ? OR LOWER(r.object) = ?)
          AND r.relation IN (
              'species_uses_habitat',
              'threat_affects_species',
              'agency_manages_program'
          )
        ORDER BY r.confidence DESC, r.doc_id, r.chunk_id
        """,
        (name.casefold(), name.casefold()),
    ).fetchall()
    selected: dict[tuple[str, str], dict[str, object]] = {}
    for row in rows:
        subject_type, object_type = SEMANTIC_RELATION_TYPES[row["relation"]]
        page_is_subject = row["subject"].casefold() == name.casefold()
        counterpart = row["object"] if page_is_subject else row["subject"]
        counterpart_type = object_type if page_is_subject else subject_type
        key = (counterpart.casefold(), row["relation"])
        selected.setdefault(
            key,
            {
                "name": counterpart,
                "entity_type": counterpart_type,
                "relation": row["relation"],
                "page_is_subject": page_is_subject,
                "doc_id": row["doc_id"],
                "page": row["page"],
                "evidence": row["evidence"],
                "confidence": row["confidence"],
            },
        )
        if len(selected) == limit:
            break
    return list(selected.values())


def _co_mentioned_entities(
    connection: sqlite3.Connection, name: str, entity_type: str, limit: int = 16
) -> list[sqlite3.Row]:
    return connection.execute(
        """
        SELECT e2.name, e2.entity_type,
               COUNT(DISTINCT e2.doc_id) AS shared_documents,
               COUNT(DISTINCT e2.chunk_id) AS shared_chunks,
               GROUP_CONCAT(DISTINCT e2.doc_id) AS doc_ids
        FROM entities AS e1
        JOIN entities AS e2 ON e2.chunk_id = e1.chunk_id AND e2.entity_id != e1.entity_id
        WHERE e1.normalized_name = ? AND e1.entity_type = ?
          AND e2.entity_type != 'date'
          AND NOT (e2.normalized_name = e1.normalized_name AND e2.entity_type = e1.entity_type)
        GROUP BY e2.normalized_name, e2.entity_type
        HAVING COUNT(DISTINCT e2.doc_id) >= 2
        ORDER BY shared_documents DESC, shared_chunks DESC, e2.name
        LIMIT ?
        """,
        (name.casefold(), entity_type, limit),
    ).fetchall()


def _related_entity_display(
    *,
    name: str,
    entity_type: str,
    current_path: str,
    page_index: dict[tuple[str, str], str],
) -> str:
    target = page_index.get((entity_type, name.casefold()))
    if not target or target == current_path:
        return f"**{name}**"
    relative = posixpath.relpath(target, start=posixpath.dirname(current_path))
    return f"**[{name}]({relative})**"


def _relationship_description(relation: str, page_is_subject: bool) -> str:
    descriptions = {
        ("species_uses_habitat", True): "this species uses the related habitat",
        ("species_uses_habitat", False): "this habitat is used by the related species",
        ("threat_affects_species", True): "this threat affects the related species",
        ("threat_affects_species", False): "this species is affected by the related threat",
        ("agency_manages_program", True): "this agency manages the related program",
        ("agency_manages_program", False): "this program is managed by the related agency",
    }
    return descriptions[(relation, page_is_subject)]


def render_page(
    connection: sqlite3.Connection,
    *,
    category: str,
    name: str,
    entity_type: str,
    mentions: int,
    document_count: int,
    generated_at: str,
    page_index: dict[tuple[str, str], str],
) -> WikiPage:
    evidence_rows = _entity_evidence(connection, name, entity_type)
    mention_label = "mention" if mentions == 1 else "mentions"
    document_label = "document" if document_count == 1 else "documents"
    evidence_snippet_label = "snippet" if len(evidence_rows) == 1 else "snippets"
    corpus_count = connection.execute(
        "SELECT COUNT(*) FROM documents"
    ).fetchone()[0]
    semantic_related_rows = _semantic_related_entities(connection, name)
    co_mentioned_rows = _co_mentioned_entities(connection, name, entity_type)
    page_slug = slugify(name)
    relative_path = Path("wiki") / category / f"{page_slug}.md"
    page_id = f"wiki-{category}-{page_slug}"

    lines = [
        "---",
        f"title: {json.dumps(name)}",
        f"entity_type: {entity_type}",
        f"mentions: {mentions}",
        f"documents: {document_count}",
        f"generated_at: {generated_at}",
        "generated: true",
        "generation_method: evidence_ranked",
        "---",
        "",
        f"# {name}",
        "",
        "## Summary",
        "",
    ]
    for row in evidence_rows[:2]:
        lines.extend(
            [
                (
                    f"{clean_wiki_evidence(row['evidence'], name)} "
                    f"{citation(row['doc_id'], row['page'])}"
                ),
                "",
            ]
        )
    if not evidence_rows:
        lines.extend(
            [
                "No supporting evidence was retained; this page requires review.",
                "",
            ]
        )

    lines.extend(
        [
            "## Corpus coverage",
            "",
            (
                f"Corpus extraction recorded {mentions} {mention_label} of **{name}** across "
                f"{document_count} public {document_label}. This page retains "
                f"{len(evidence_rows)} ranked evidence {evidence_snippet_label}."
            ),
            "",
            "## Key facts",
            "",
        ]
    )
    for row in evidence_rows[:4]:
        lines.append(
            f"- {clean_wiki_evidence(row['evidence'], name)} "
            f"{citation(row['doc_id'], row['page'])}"
        )
    if not evidence_rows:
        lines.append("- No supporting evidence was retained; this page requires review.")

    lines.extend(["", "## Related documents", ""])
    seen_documents: set[str] = set()
    for row in evidence_rows:
        if row["doc_id"] in seen_documents:
            continue
        seen_documents.add(row["doc_id"])
        lines.append(
            f"- **{row['doc_id']} — {row['title']}** ({row['agency']}; {row['topic']}). "
            f"[Open source]({row['source_url']}) {citation(row['doc_id'], row['page'])}"
        )

    lines.extend(["", "## Related entities", ""])
    related_count = 0
    explicit_names: set[tuple[str, str]] = set()
    for row in semantic_related_rows:
        related_name = str(row["name"])
        related_type = str(row["entity_type"])
        explicit_names.add((related_type, related_name.casefold()))
        display = _related_entity_display(
            name=related_name,
            entity_type=related_type,
            current_path=relative_path.as_posix(),
            page_index=page_index,
        )
        description = _relationship_description(
            str(row["relation"]), bool(row["page_is_subject"])
        )
        lines.append(
            f"- {display} ({related_type}) — explicit `{row['relation']}` relation: "
            f"{description}. {citation(str(row['doc_id']), str(row['page'] or ''))}"
        )
        related_count += 1

    for row in co_mentioned_rows:
        key = (row["entity_type"], row["name"].casefold())
        if key in explicit_names or related_count >= 8:
            continue
        display = _related_entity_display(
            name=row["name"],
            entity_type=row["entity_type"],
            current_path=relative_path.as_posix(),
            page_index=page_index,
        )
        doc_ids = sorted((row["doc_ids"] or "").split(","))[:3]
        related_citations = " ".join(citation(doc_id, "") for doc_id in doc_ids if doc_id)
        lines.append(
            f"- {display} ({row['entity_type']}) — co-mentioned with this entity in "
            f"{row['shared_documents']} documents; this is a corpus association only, "
            f"not an inferred semantic relationship. {related_citations}"
        )
        related_count += 1

    if not related_count:
        lines.append("- No explicit or repeated corpus relationships met the evidence threshold.")

    lines.extend(["", "## Evidence snippets", ""])
    for row in evidence_rows:
        lines.append(
            f"> {clean_wiki_evidence(row['evidence'], name)}  \n> — "
            f"{citation(row['doc_id'], row['page'])}, "
            f"chunk `{row['chunk_id']}`"
        )
        lines.append("")

    lines.extend(
        [
            "## Open questions",
            "",
            f"- Which sources provide the strongest direct evidence about {name}?",
            f"- What important aspects of {name} are absent from this {corpus_count}-source corpus?",
            "- Do newer documents confirm, qualify, or contradict the extracted evidence?",
            "",
        ]
    )
    return WikiPage(
        page_id=page_id,
        title=name,
        entity_type=entity_type,
        file_path=relative_path.as_posix(),
        content="\n".join(lines),
    )


def generate_wiki(
    *,
    database_path: Path = DATABASE_PATH,
    wiki_dir: Path = WIKI_DIR,
    per_category: int = 3,
) -> list[WikiPage]:
    generated_at = datetime.now(timezone.utc).isoformat()
    with connect_database(database_path) as connection:
        selected = select_entities(connection, per_category=per_category)
        page_index = {
            (entity_type, name.casefold()): (
                Path("wiki") / category / f"{slugify(name)}.md"
            ).as_posix()
            for category, name, entity_type, _, _ in selected
        }
        pages = [
            render_page(
                connection,
                category=category,
                name=name,
                entity_type=entity_type,
                mentions=mentions,
                document_count=document_count,
                generated_at=generated_at,
                page_index=page_index,
            )
            for category, name, entity_type, mentions, document_count in selected
        ]

        connection.execute("DELETE FROM wiki_pages")
        connection.executemany(
            """
            INSERT INTO wiki_pages (page_id, title, entity_type, file_path, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                (page.page_id, page.title, page.entity_type, page.file_path, generated_at)
                for page in pages
            ),
        )

    expected_paths = {
        (
            wiki_dir / Path(page.file_path).relative_to("wiki")
            if wiki_dir != WIKI_DIR
            else PROJECT_ROOT / page.file_path
        ).resolve()
        for page in pages
    }
    for existing in wiki_dir.glob("*/*.md"):
        if existing.resolve() in expected_paths:
            continue
        existing_content = existing.read_text(encoding="utf-8")
        if re.search(r"(?m)^generated:\s*true\s*$", existing_content):
            existing.unlink()

    for page in pages:
        destination = PROJECT_ROOT / page.file_path
        if wiki_dir != WIKI_DIR:
            destination = wiki_dir / Path(page.file_path).relative_to("wiki")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".md.part")
        temporary.write_text(page.content, encoding="utf-8")
        temporary.replace(destination)

    manifest = {
        "generated_at": generated_at,
        "page_count": len(pages),
        "pages": [page.file_path for page in pages],
    }
    wiki_dir.mkdir(parents=True, exist_ok=True)
    (wiki_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return pages


def _section_body(content: str, heading: str) -> str:
    match = re.search(
        rf"(?ms)^{re.escape(heading)}\s*$\n(.*?)(?=^##\s|\Z)",
        content,
    )
    return match.group(1).strip() if match else ""


def _section_bullets(content: str, heading: str) -> list[str]:
    return [
        line.removeprefix("- ").strip()
        for line in _section_body(content, heading).splitlines()
        if line.startswith("- ")
    ]


def validate_wiki_page(content: str) -> list[str]:
    errors: list[str] = []
    sections = (
        "## Summary",
        "## Corpus coverage",
        "## Key facts",
        "## Related documents",
        "## Related entities",
        "## Evidence snippets",
        "## Open questions",
    )
    for section in sections:
        if not re.search(rf"(?m)^{re.escape(section)}\s*$", content):
            errors.append(f"missing section: {section}")
    if errors:
        return errors

    title_match = re.search(r"(?m)^title:\s*(.+)$", content)
    type_match = re.search(r"(?m)^entity_type:\s*(\S+)$", content)
    entity_name = ""
    entity_type = ""
    if not title_match or not type_match:
        errors.append("page contains no entity metadata")
    else:
        try:
            entity_name = str(json.loads(title_match.group(1)))
        except json.JSONDecodeError:
            errors.append("page title metadata is not valid JSON")
        entity_type = type_match.group(1)

    summary = _section_body(content, "## Summary")
    if not CITATION_PATTERN.search(summary):
        errors.append("summary contains no corpus citation")

    facts = _section_bullets(content, "## Key facts")
    if not facts:
        errors.append("key facts contains no bullet items")
    normalized_facts: set[str] = set()
    for fact in facts:
        if not CITATION_PATTERN.search(fact):
            errors.append(f"uncited key fact: {fact[:80]}")
        if WIKI_NOISE_PATTERN.search(fact):
            errors.append(f"noisy key fact: {fact[:80]}")
        fact_text = CITATION_PATTERN.sub("", fact).strip()
        quality_issues = wiki_evidence_quality_issues(
            fact_text,
            entity_name=entity_name,
            entity_type=entity_type,
        )
        if quality_issues:
            errors.append(
                f"low-quality key fact ({', '.join(quality_issues)}): {fact[:80]}"
            )
        if len(fact) > 700:
            errors.append(f"overlong key fact: {fact[:80]}")
        normalized = CITATION_PATTERN.sub("", fact).casefold().strip(" .")
        if normalized in normalized_facts:
            errors.append(f"duplicate key fact: {fact[:80]}")
        normalized_facts.add(normalized)

    documents = _section_bullets(content, "## Related documents")
    if not documents:
        errors.append("related documents contains no bullet items")
    for document in documents:
        if not CITATION_PATTERN.search(document):
            errors.append(f"uncited related document: {document[:80]}")
        if "[Open source](" not in document:
            errors.append(f"related document contains no source link: {document[:80]}")

    related_entities = _section_bullets(content, "## Related entities")
    for related in related_entities:
        if related.startswith("No explicit or repeated corpus relationships"):
            continue
        if not CITATION_PATTERN.search(related):
            errors.append(f"uncited related entity: {related[:80]}")
        if "co-mentioned" in related:
            if "not an inferred semantic relationship" not in related:
                errors.append(f"unqualified co-mention: {related[:80]}")
            if len(CITATION_PATTERN.findall(related)) < 2:
                errors.append(f"co-mention lacks cross-document evidence: {related[:80]}")
        elif "explicit `" not in related:
            errors.append(f"untyped entity relationship: {related[:80]}")
    if re.search(r"shares? .*evidence chunks?", content, flags=re.IGNORECASE):
        errors.append("page presents chunk co-occurrence as a relationship")

    evidence = _section_body(content, "## Evidence snippets")
    evidence_blocks = [
        block for block in re.split(r"\n\s*\n", evidence) if block.startswith(">")
    ]
    if not evidence_blocks:
        errors.append("evidence snippets contains no quoted evidence")
    for block in evidence_blocks:
        if not CITATION_PATTERN.search(block) or "chunk `" not in block:
            errors.append(f"unattributed evidence snippet: {block[:80]}")
        if WIKI_NOISE_PATTERN.search(block):
            errors.append(f"noisy evidence snippet: {block[:80]}")

    questions = _section_bullets(content, "## Open questions")
    if not questions:
        errors.append("open questions contains no bullet items")
    for question in questions:
        if not question.endswith("?"):
            errors.append(f"open question is not a question: {question[:80]}")

    if not CITATION_PATTERN.search(content):
        errors.append("page contains no corpus citation")
    return errors
