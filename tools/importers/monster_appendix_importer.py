from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from tools.importers.monster_manual_importer import (
    ImportPage,
    is_page_marker_line,
    normalize_line,
    title_case_name,
)
from tools.importers.monster_manual_schema import (
    BOOK_APPENDIX_RANGES,
    DEFAULT_MONSTER_APPENDIX_CATALOG_JSON,
    DEFAULT_MONSTER_APPENDIX_IMPORT_REPORT,
    DEFAULT_MONSTER_APPENDIX_UNMATCHED_REVIEW_REPORT,
    DEFAULT_MONSTER_CATALOG_JSON,
    DEFAULT_MONSTER_MANUAL_PDF,
)


APPENDIX_HEADING_PATTERN = re.compile(
    r"^APPENDIX\s+([BCD])\s*:\s*(.+)$",
    re.IGNORECASE,
)
LEVEL_HEADING_PATTERN = re.compile(r"^LEVEL\s+[IVXLC]+$", re.IGNORECASE)
ROLL_RANGE_PATTERN = re.compile(
    r"^(?P<roll>\d{1,3}(?:\s*-\s*\d{1,3})?)\s+(?P<rest>.+)$"
)
NOTE_PATTERN = re.compile(r"^(?P<name>.+?)\s*\((?P<note>[^()]+)\)\s*$")
CONTEXT_CLIMATE_PATTERN = re.compile(
    r"^(Cold|Temperate|Tropical or Subtropical)\s+"
    r"(Wilderness|Civilized|Freshwater|Saltwater)$",
    re.IGNORECASE,
)

RARITY_HEADINGS = {
    "Common",
    "Uncommon",
    "Rare",
    "Very Rare",
    "Unique",
}
TERRAIN_SUBHEADINGS = {
    "Mountains",
    "Hill and Rough",
    "Forest",
    "Swamp and Marsh",
    "Plain and Scrub",
    "Desert",
    "Underground",
    "Surface",
    "Depths",
}
URBAN_CLIMATE_HEADINGS = {
    "Cold",
    "Temperate",
    "Tropical or Subtropical",
}
TERRAIN_CONTEXT_HEADINGS = {
    "Underground or Ruin",
    "Cold Wilderness",
    "Temperate Wilderness",
    "Tropical or Subtropical Wilderness",
    "Cold Civilized",
    "Temperate Civilized",
    "Tropical or Subtropical Civilized",
    "Urban or Settled",
    "Cold Freshwater",
    "Temperate Freshwater",
    "Tropical or Subtropical Freshwater",
    "Cold Saltwater",
    "Temperate Saltwater",
    "Tropical or Subtropical Saltwater",
    "Astral",
    "Ethereal",
    "Extraplaner",
}
KNOWN_APPENDIX_HEADINGS = TERRAIN_CONTEXT_HEADINGS | TERRAIN_SUBHEADINGS | URBAN_CLIMATE_HEADINGS
APPENDIX_ORDER = ("B", "C", "D")
MOJIBAKE_REPLACEMENTS = {
    "â€™": "'",
    "â€˜": "'",
    "’": "'",
    "‘": "'",
    "â€œ": '"',
    "â€\x9d": '"',
    "“": '"',
    "”": '"',
    "â€“": "-",
    "â€”": "-",
    "–": "-",
    "—": "-",
}


@dataclass
class AppendixParseContext:
    appendix_key: str | None = None
    section_title: str | None = None
    level_bucket: str | None = None
    rarity_bucket: str | None = None
    region: str | None = None
    terrain: str | None = None
    climate: str | None = None
    context_title: str | None = None


@dataclass
class AppendixImportResult:
    catalog: dict[str, Any]
    report_text: str
    unmatched_review_text: str = ""
    sections_detected: list[str] = field(default_factory=list)
    records_parsed: int = 0
    matched_count: int = 0
    unmatched_count: int = 0
    ambiguous_count: int = 0
    skipped_rows: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import appendix encounter/location data from the combined monster manual PDF."
    )
    parser.add_argument(
        "pdf_path",
        nargs="?",
        default=str(DEFAULT_MONSTER_MANUAL_PDF),
        help="Path to the combined monster manual PDF.",
    )
    parser.add_argument(
        "--monster-catalog",
        default=str(DEFAULT_MONSTER_CATALOG_JSON),
        help="Path to the existing monster catalog JSON used for name matching.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_MONSTER_APPENDIX_CATALOG_JSON),
        help="Path to write the appendix catalog JSON.",
    )
    parser.add_argument(
        "--report",
        default=str(DEFAULT_MONSTER_APPENDIX_IMPORT_REPORT),
        help="Path to write the appendix import report text file.",
    )
    parser.add_argument(
        "--unmatched-review",
        default=str(DEFAULT_MONSTER_APPENDIX_UNMATCHED_REVIEW_REPORT),
        help="Path to write the appendix unmatched-reference review text file.",
    )
    return parser.parse_args(argv)


def book_for_appendix_page(actual_page: int) -> int | None:
    for book, start, end in BOOK_APPENDIX_RANGES:
        if start <= actual_page <= end:
            return book
    return None


def extract_appendix_pages(pdf_path: Path) -> list[ImportPage]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "The monster appendix importer requires pypdf for PDF extraction. "
            "Use the bundled Codex runtime Python or install pypdf in the "
            "environment used for this tooling command."
        ) from exc

    reader = PdfReader(str(pdf_path))
    pages: list[ImportPage] = []
    for index, page in enumerate(reader.pages, start=1):
        book = book_for_appendix_page(index)
        if book is None:
            continue
        text = page.extract_text() or ""
        pages.append(ImportPage(actual_page=index, book=book, text=text))
    return pages


def ascii_fold_text(text: str) -> str:
    folded = text
    for source, replacement in MOJIBAKE_REPLACEMENTS.items():
        folded = folded.replace(source, replacement)
    folded = unicodedata.normalize("NFKD", folded)
    return "".join(
        character
        for character in folded
        if unicodedata.category(character) != "Mn"
    )


def normalize_monster_reference_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", ascii_fold_text(name).casefold())


def strip_parenthetical_descriptors(name: str) -> str:
    return re.sub(r"\s*\([^)]*\)", "", name).strip()


def strip_leading_articles(name: str) -> str:
    return re.sub(r"^(?:the|a|an)\s+", "", name.strip(), flags=re.IGNORECASE)


def singularize_simple_name(name: str) -> str:
    lowered = name.casefold()
    if lowered.endswith("ies") and len(name) > 3:
        return name[:-3] + "y"
    if lowered.endswith("s") and not lowered.endswith("ss") and len(name) > 1:
        return name[:-1]
    return name


def damerau_levenshtein_distance(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    distances: dict[tuple[int, int], int] = {}
    max_distance = len(left) + len(right)
    distances[(-1, -1)] = max_distance
    for index in range(len(left) + 1):
        distances[(index, -1)] = max_distance
        distances[(index, 0)] = index
    for index in range(len(right) + 1):
        distances[(-1, index)] = max_distance
        distances[(0, index)] = index
    last_seen: dict[str, int] = {}
    for i, left_char in enumerate(left, start=1):
        db = 0
        for j, right_char in enumerate(right, start=1):
            i1 = last_seen.get(right_char, 0)
            j1 = db
            cost = 0 if left_char == right_char else 1
            if cost == 0:
                db = j
            distances[(i, j)] = min(
                distances[(i - 1, j - 1)] + cost,
                distances[(i, j - 1)] + 1,
                distances[(i - 1, j)] + 1,
                distances[(i1 - 1, j1 - 1)]
                + (i - i1 - 1)
                + 1
                + (j - j1 - 1),
            )
        last_seen[left_char] = i
    return distances[(len(left), len(right))]


def generate_match_variants(name: str) -> list[tuple[str, str]]:
    variants: list[tuple[str, str]] = [("exact", name)]
    stripped_parenthetical = strip_parenthetical_descriptors(name)
    if stripped_parenthetical and stripped_parenthetical != name:
        variants.append(("strip_parenthetical", stripped_parenthetical))
    stripped_article = strip_leading_articles(name)
    if stripped_article and stripped_article != name:
        variants.append(("strip_article", stripped_article))
    singular = singularize_simple_name(name)
    if singular and singular != name:
        variants.append(("singular", singular))
    if "," in name:
        left, right = [part.strip() for part in name.split(",", 1)]
        swapped = f"{right} {left}".strip()
        if swapped and swapped != name:
            variants.append(("comma_swap", swapped))
    else:
        parts = name.split()
        if len(parts) >= 2:
            swapped = f"{parts[-1]}, {' '.join(parts[:-1])}"
            variants.append(("comma_swap", swapped))
    seen: set[str] = set()
    return [
        (rule, variant)
        for rule, variant in variants
        if variant and not (variant in seen or seen.add(variant))
    ]


def build_monster_reference_index(
    monster_catalog: dict[str, Any],
) -> tuple[dict[str, set[str]], dict[str, dict[str, str]], dict[str, list[str]]]:
    index: dict[str, set[str]] = defaultdict(set)
    metadata: dict[str, dict[str, str]] = {}
    canonical_names: dict[str, list[str]] = defaultdict(list)
    for monster in monster_catalog.get("monsters", []):
        monster_id = str(monster.get("id") or "")
        if not monster_id:
            continue
        sort_name = str(monster.get("sort_name") or monster.get("name") or monster_id)
        display_name = str(monster.get("name") or title_case_name(sort_name))
        variants = {sort_name, display_name, sort_name.replace(",", ""), display_name.replace(",", "")}
        for _, variant in generate_match_variants(sort_name):
            variants.add(variant)
        for _, variant in generate_match_variants(display_name):
            variants.add(variant)
        for variant in variants:
            key = normalize_monster_reference_name(variant)
            if not key:
                continue
            index[key].add(monster_id)
            canonical_names[key].append(sort_name)
        metadata[monster_id] = {
            "id": monster_id,
            "name": display_name,
            "sort_name": sort_name,
        }
    return index, metadata, canonical_names


def load_monster_catalog(monster_catalog_path: Path) -> dict[str, Any]:
    if not monster_catalog_path.exists():
        raise FileNotFoundError(
            f"Monster catalog JSON not found: {monster_catalog_path}"
        )
    return json.loads(monster_catalog_path.read_text(encoding="utf-8"))


def clean_appendix_page_lines(page: ImportPage) -> list[tuple[int, str]]:
    records: list[tuple[int, str]] = []
    for raw_line in page.text.replace("\r\n", "\n").replace("\r", "\n").splitlines():
        cleaned = normalize_line(raw_line)
        if not cleaned or is_page_marker_line(cleaned):
            continue
        records.append((page.actual_page, cleaned))
    return records


def collapse_wrapped_appendix_lines(
    line_records: list[tuple[int, str]],
    known_monster_keys: set[str],
) -> list[tuple[int, str]]:
    merged: list[tuple[int, str]] = []
    index = 0
    while index < len(line_records):
        page_number, line = line_records[index]
        current = normalize_line(line)
        if index + 1 < len(line_records):
            _, next_line = line_records[index + 1]
            following = normalize_line(next_line)
            combined_without_hyphen = None
            combined_with_space = None
            if current.endswith("-") and following:
                combined_without_hyphen = f"{current[:-1]}{following}"
            elif current.endswith("/") and following:
                combined_without_hyphen = f"{current}{following}"
            elif following:
                combined_with_space = f"{current} {following}"

            if combined_without_hyphen:
                normalized = normalize_monster_reference_name(combined_without_hyphen)
                if normalized in known_monster_keys:
                    merged.append((page_number, combined_without_hyphen))
                    index += 2
                    continue
            if combined_with_space and (
                combined_with_space in KNOWN_APPENDIX_HEADINGS
                or normalize_monster_reference_name(combined_with_space) in known_monster_keys
            ):
                merged.append((page_number, combined_with_space))
                index += 2
                continue
        merged.append((page_number, current))
        index += 1
    return merged


def split_monster_line_note(line: str) -> tuple[str, str | None]:
    match = NOTE_PATTERN.match(line)
    if not match:
        return line, None
    return match.group("name").strip(), match.group("note").strip()


def parse_roll_range_prefix(line: str) -> tuple[str | None, str]:
    match = ROLL_RANGE_PATTERN.match(line)
    if not match:
        return None, line
    return match.group("roll").replace(" ", ""), match.group("rest").strip()


def find_minor_typo_candidates(
    normalized_name: str,
    canonical_names: dict[str, list[str]],
) -> list[str]:
    if len(normalized_name) < 6:
        return []
    candidates: list[str] = []
    for canonical_key, names in canonical_names.items():
        if abs(len(canonical_key) - len(normalized_name)) > 1:
            continue
        if canonical_key[:1] != normalized_name[:1]:
            continue
        if canonical_key[-1:] != normalized_name[-1:]:
            continue
        if damerau_levenshtein_distance(normalized_name, canonical_key) == 1:
            candidates.extend(names)
    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if candidate not in seen:
            deduped.append(candidate)
            seen.add(candidate)
    return deduped


def match_monster_reference_details(
    monster_name: str,
    monster_index: dict[str, set[str]],
    canonical_names: dict[str, list[str]] | None = None,
) -> tuple[str | None, str, str, list[str]]:
    for match_rule, variant in generate_match_variants(monster_name):
        key = normalize_monster_reference_name(variant)
        if not key:
            continue
        matches = sorted(monster_index.get(key, set()))
        if not matches:
            continue
        if len(matches) > 1:
            return None, "ambiguous", match_rule, matches
        return matches[0], "matched", match_rule, matches

    if canonical_names is not None:
        typo_candidates = find_minor_typo_candidates(
            normalize_monster_reference_name(monster_name),
            canonical_names,
        )
        unique_candidates = sorted(set(typo_candidates))
        if len(unique_candidates) == 1:
            candidate_names = unique_candidates
            key = normalize_monster_reference_name(candidate_names[0])
            matches = sorted(monster_index.get(key, set()))
            if len(matches) == 1:
                return matches[0], "matched", "minor_typo", matches
        if len(unique_candidates) > 1:
            return None, "ambiguous", "minor_typo", unique_candidates

    return None, "unmatched", "unmatched", []


def match_monster_reference(
    monster_name: str,
    monster_index: dict[str, set[str]],
) -> tuple[str | None, str]:
    monster_id, status, _, _ = match_monster_reference_details(monster_name, monster_index)
    return monster_id, status


def parse_appendix_heading(line: str) -> tuple[str, str] | None:
    match = APPENDIX_HEADING_PATTERN.match(line)
    if not match:
        return None
    appendix_letter = match.group(1).upper()
    return appendix_letter, f"Appendix {appendix_letter}: {match.group(2).strip()}"


def classify_terrain_context(line: str) -> tuple[str | None, str | None]:
    match = CONTEXT_CLIMATE_PATTERN.match(line)
    if match:
        climate = match.group(1)
        region = match.group(2)
        return region, climate
    return line, None


def current_table_title(context: AppendixParseContext) -> str:
    if context.appendix_key == "B":
        return context.level_bucket or "Monsters by Level"
    if context.appendix_key == "C":
        return context.rarity_bucket or "Monsters by Rarity"
    pieces = [piece for piece in (context.context_title, context.terrain) if piece]
    return " / ".join(pieces) or "Monsters by Terrain Type"


def build_appendix_record(
    *,
    context: AppendixParseContext,
    page_number: int,
    line: str,
    monster_index: dict[str, set[str]],
    canonical_names: dict[str, list[str]],
) -> dict[str, Any]:
    roll_range, remainder = parse_roll_range_prefix(line)
    monster_name, notes = split_monster_line_note(remainder)
    monster_id, match_status, match_rule, candidate_names = match_monster_reference_details(
        monster_name,
        monster_index,
        canonical_names,
    )
    return {
        "source": "monster_manual_appendix",
        "source_page": page_number,
        "source_book": book_for_appendix_page(page_number),
        "section_title": context.section_title,
        "table_title": current_table_title(context),
        "region": context.region,
        "terrain": context.terrain,
        "climate": context.climate,
        "encounter_type": {
            "B": "level",
            "C": "rarity",
            "D": "terrain",
        }.get(context.appendix_key),
        "roll_range": roll_range,
        "monster_name": monster_name,
        "normalized_monster_name": normalize_monster_reference_name(monster_name),
        "monster_id": monster_id,
        "match_status": match_status,
        "match_rule": match_rule,
        "candidate_names": candidate_names,
        "notes": notes,
        "raw_text": line,
    }


def is_appendix_row_candidate(line: str, context: AppendixParseContext) -> bool:
    if not line:
        return False
    if parse_appendix_heading(line):
        return False
    if context.appendix_key == "B":
        return not LEVEL_HEADING_PATTERN.match(line) and line.upper() != "VARIES"
    if context.appendix_key == "C":
        return line not in RARITY_HEADINGS
    if context.appendix_key == "D":
        if line in TERRAIN_CONTEXT_HEADINGS:
            return False
        if line in TERRAIN_SUBHEADINGS:
            return False
        if context.context_title == "Urban or Settled" and line in URBAN_CLIMATE_HEADINGS:
            return False
        return True
    return False


def parse_appendix_records_from_pages(
    pages: list[ImportPage],
    monster_index: dict[str, set[str]],
    canonical_names: dict[str, list[str]] | None = None,
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    known_monster_keys = set(monster_index.keys())
    line_records: list[tuple[int, str]] = []
    for page in pages:
        line_records.extend(clean_appendix_page_lines(page))
    line_records = collapse_wrapped_appendix_lines(line_records, known_monster_keys)

    context = AppendixParseContext()
    sections_detected: list[str] = []
    skipped_rows: list[str] = []
    records: list[dict[str, Any]] = []

    for page_number, line in line_records:
        appendix_heading = parse_appendix_heading(line)
        if appendix_heading:
            context = AppendixParseContext(
                appendix_key=appendix_heading[0],
                section_title=appendix_heading[1],
            )
            sections_detected.append(appendix_heading[1])
            continue

        if context.appendix_key is None:
            skipped_rows.append(f"Page {page_number}: {line}")
            continue

        if context.appendix_key == "B":
            if LEVEL_HEADING_PATTERN.match(line) or line.upper() == "VARIES":
                context.level_bucket = line.upper() if line.upper() == "VARIES" else line.title()
                continue
        elif context.appendix_key == "C":
            if line in RARITY_HEADINGS:
                context.rarity_bucket = line
                continue
        elif context.appendix_key == "D":
            if line in TERRAIN_CONTEXT_HEADINGS:
                region, climate = classify_terrain_context(line)
                context.region = region
                context.climate = climate
                context.terrain = None
                context.context_title = line
                continue
            if context.context_title == "Urban or Settled" and line in URBAN_CLIMATE_HEADINGS:
                context.climate = line
                context.region = "Urban or Settled"
                context.terrain = None
                continue
            if line in TERRAIN_SUBHEADINGS:
                context.terrain = line
                continue

        if not is_appendix_row_candidate(line, context):
            skipped_rows.append(f"Page {page_number}: {line}")
            continue
        records.append(
            build_appendix_record(
                context=context,
                page_number=page_number,
                line=line,
                monster_index=monster_index,
                canonical_names=canonical_names or {},
            )
        )
    return records, sections_detected, skipped_rows


def categorize_unmatched_record(record: dict[str, Any]) -> tuple[str, list[str]]:
    suggestions = [candidate for candidate in record.get("candidate_names", []) if candidate]
    name = str(record.get("monster_name") or "")
    if ascii_fold_text(name) != name or "�" in name:
        return "encoding_or_ocr_variant", suggestions
    if suggestions:
        if "minor_typo" in str(record.get("match_rule") or ""):
            return "possible_minor_typo_or_ocr_variant", suggestions
        return "general_candidate_review", suggestions
    return "appendix_only_or_missing_catalog_entry", []


def build_unmatched_review_text(records: list[dict[str, Any]]) -> str:
    unmatched_rows = [record for record in records if record["match_status"] == "unmatched"]
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in unmatched_rows:
        grouped[record["normalized_monster_name"]].append(record)

    category_counts = Counter()
    category_examples: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for normalized_name, entries in grouped.items():
        category, _ = categorize_unmatched_record(entries[0])
        category_counts[category] += len(entries)
        category_examples[category].append((entries[0]["monster_name"], len(entries)))

    lines = [
        "Monster Appendix Unmatched Review",
        "================================",
        "",
        f"Unmatched rows reviewed: {len(unmatched_rows)}",
        f"Unique unmatched normalized names: {len(grouped)}",
        "",
        "Category counts:",
    ]
    if category_counts:
        for category, count in category_counts.most_common():
            lines.append(f"- {category}: {count}")
    else:
        lines.append("- None")

    lines.extend(["", "Top repeated unmatched normalized names:"])
    for normalized_name, entries in sorted(
        ((name, len(rows)) for name, rows in grouped.items()),
        key=lambda item: (-item[1], item[0]),
    )[:25]:
        first = grouped[normalized_name][0]
        category, suggestions = categorize_unmatched_record(first)
        pages = sorted({record["source_page"] for record in grouped[normalized_name]})
        tables = sorted({record["table_title"] for record in grouped[normalized_name]})[:3]
        lines.append(
            f"- {first['monster_name']} | normalized={normalized_name} | count={entries} | "
            f"category={category} | pages={', '.join(str(page) for page in pages)} | "
            f"tables={'; '.join(tables)}"
        )
        if suggestions:
            lines.append(f"  suggestions: {', '.join(suggestions)}")
    return "\n".join(lines) + "\n"


def build_appendix_report_text(
    *,
    source_pdf_path: Path,
    sections_detected: list[str],
    records: list[dict[str, Any]],
    skipped_rows: list[str],
    warnings: list[str],
) -> str:
    counts = Counter(record["match_status"] for record in records)
    lines = [
        "Monster Appendix Import Report",
        "==============================",
        "",
        f"Source PDF path: {source_pdf_path}",
        "Page ranges processed: "
        + ", ".join(
            f"Book {book}: actual pages {start}-{end}"
            for book, start, end in BOOK_APPENDIX_RANGES
        ),
        f"Appendix sections detected: {len(sections_detected)}",
        f"Appendix rows parsed: {len(records)}",
        f"Matched monster references: {counts.get('matched', 0)}",
        f"Unmatched monster references: {counts.get('unmatched', 0)}",
        f"Ambiguous monster references: {counts.get('ambiguous', 0)}",
        f"Skipped/rejected rows: {len(skipped_rows)}",
        "",
        "Sections detected:",
    ]
    if sections_detected:
        lines.extend(f"- {section}" for section in sections_detected)
    else:
        lines.append("- None")
    lines.extend(["", "Warnings:"])
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- None")
    lines.extend(["", "Sample matched appendix rows:"])
    matched_rows = [record for record in records if record["match_status"] == "matched"][:10]
    if matched_rows:
        lines.extend(
            f"- Page {record['source_page']} [{record['table_title']}]: {record['monster_name']} -> {record['monster_id']}"
            for record in matched_rows
        )
    else:
        lines.append("- None")
    lines.extend(["", "Unmatched appendix rows:"])
    unmatched_rows = [record for record in records if record["match_status"] == "unmatched"]
    if unmatched_rows:
        lines.extend(
            f"- Page {record['source_page']} [{record['table_title']}]: {record['monster_name']}"
            for record in unmatched_rows
        )
    else:
        lines.append("- None")
    lines.extend(["", "Ambiguous appendix rows:"])
    ambiguous_rows = [record for record in records if record["match_status"] == "ambiguous"]
    if ambiguous_rows:
        lines.extend(
            f"- Page {record['source_page']} [{record['table_title']}]: {record['monster_name']}"
            for record in ambiguous_rows
        )
    else:
        lines.append("- None")
    lines.extend(["", "Unmatched Reference Review:"])
    unmatched_rows = [record for record in records if record["match_status"] == "unmatched"]
    unique_unmatched = defaultdict(list)
    for record in unmatched_rows:
        unique_unmatched[record["normalized_monster_name"]].append(record)
    lines.append(f"- Unique unmatched normalized names: {len(unique_unmatched)}")
    category_counts = Counter(
        categorize_unmatched_record(entries[0])[0]
        for entries in unique_unmatched.values()
    )
    if category_counts:
        lines.extend(
            f"- {category}: {count} unique names"
            for category, count in category_counts.most_common()
        )
    else:
        lines.append("- None")
    lines.extend(["", "Top repeated unmatched normalized names:"])
    for normalized_name, count in sorted(
        ((name, len(entries)) for name, entries in unique_unmatched.items()),
        key=lambda item: (-item[1], item[0]),
    )[:20]:
        first = unique_unmatched[normalized_name][0]
        category, suggestions = categorize_unmatched_record(first)
        lines.append(
            f"- {first['monster_name']} | normalized={normalized_name} | count={count} | category={category}"
        )
        if suggestions:
            lines.append(f"  suggested catalog names: {', '.join(suggestions)}")
    lines.extend(["", "Skipped/rejected rows:"])
    if skipped_rows:
        lines.extend(f"- {row}" for row in skipped_rows)
    else:
        lines.append("- None")
    return "\n".join(lines) + "\n"


def build_appendix_catalog_from_pages(
    pages: list[ImportPage],
    source_file_name: str,
    source_pdf_path: Path,
    monster_catalog_path: Path = DEFAULT_MONSTER_CATALOG_JSON,
) -> AppendixImportResult:
    monster_catalog = load_monster_catalog(monster_catalog_path)
    monster_index, _, canonical_names = build_monster_reference_index(monster_catalog)
    records, sections_detected, skipped_rows = parse_appendix_records_from_pages(
        pages, monster_index, canonical_names
    )
    warnings: list[str] = []
    counts = Counter(record["match_status"] for record in records)
    catalog = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_pdf": source_file_name,
        "page_ranges_processed": [
            {"book": book, "actual_page_start": start, "actual_page_end": end}
            for book, start, end in BOOK_APPENDIX_RANGES
        ],
        "sections_detected": sections_detected,
        "appendix_record_count": len(records),
        "matched_count": counts.get("matched", 0),
        "unmatched_count": counts.get("unmatched", 0),
        "ambiguous_count": counts.get("ambiguous", 0),
        "records": records,
    }
    report_text = build_appendix_report_text(
        source_pdf_path=source_pdf_path,
        sections_detected=sections_detected,
        records=records,
        skipped_rows=skipped_rows,
        warnings=warnings,
    )
    unmatched_review_text = build_unmatched_review_text(records)
    return AppendixImportResult(
        catalog=catalog,
        report_text=report_text,
        unmatched_review_text=unmatched_review_text,
        sections_detected=sections_detected,
        records_parsed=len(records),
        matched_count=counts.get("matched", 0),
        unmatched_count=counts.get("unmatched", 0),
        ambiguous_count=counts.get("ambiguous", 0),
        skipped_rows=skipped_rows,
        warnings=warnings,
    )


def import_monster_appendices(
    pdf_path: Path = DEFAULT_MONSTER_MANUAL_PDF,
    monster_catalog_path: Path = DEFAULT_MONSTER_CATALOG_JSON,
    output_path: Path = DEFAULT_MONSTER_APPENDIX_CATALOG_JSON,
    report_path: Path = DEFAULT_MONSTER_APPENDIX_IMPORT_REPORT,
    unmatched_review_path: Path = DEFAULT_MONSTER_APPENDIX_UNMATCHED_REVIEW_REPORT,
) -> AppendixImportResult:
    if not pdf_path.exists():
        raise FileNotFoundError(f"Monster manual PDF not found: {pdf_path}")
    pages = extract_appendix_pages(pdf_path)
    result = build_appendix_catalog_from_pages(
        pages=pages,
        source_file_name=pdf_path.name,
        source_pdf_path=pdf_path,
        monster_catalog_path=monster_catalog_path,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    unmatched_review_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result.catalog, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    report_path.write_text(result.report_text, encoding="utf-8")
    unmatched_review_path.write_text(result.unmatched_review_text, encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = import_monster_appendices(
            pdf_path=Path(args.pdf_path),
            monster_catalog_path=Path(args.monster_catalog),
            output_path=Path(args.output),
            report_path=Path(args.report),
            unmatched_review_path=Path(args.unmatched_review),
        )
    except (FileNotFoundError, RuntimeError) as exc:
        print(exc)
        return 1

    print(
        f"Parsed {result.records_parsed} appendix records from {Path(args.pdf_path).name}. "
        f"Matched={result.matched_count}, unmatched={result.unmatched_count}, "
        f"ambiguous={result.ambiguous_count}."
    )
    print(f"Wrote catalog: {args.output}")
    print(f"Wrote report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
