from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from tools.importers.monster_manual_schema import (
    BOOK_ENTRY_RANGES,
    DEFAULT_MONSTER_CATALOG_JSON,
    DEFAULT_MONSTER_IMPORT_REPORT,
    DEFAULT_MONSTER_MANUAL_PDF,
    EXPECTED_COMMON_FIELDS,
    EXPECTED_REQUIRED_FIELDS,
    LABEL_TO_KEY,
    MONSTER_MANUAL_SOURCE_ID,
    ResolvedMonsterSource,
    SECTION_LABELS,
    resolve_registered_monster_source,
)


HEADING_IGNORE = {
    "TABLE OF CONTENTS",
    "APPENDIX",
    "GENERAL INFORMATION",
    "LANGUAGES",
    "PHYSICAL DESCRIPTION",
    "VARIANTS",
    *LABEL_TO_KEY.keys(),
}
SECTION_KEYS = {key for key, _ in SECTION_LABELS}
LABEL_PATTERN = re.compile(
    r"^\s*(SIZE|MOVE|ARMOR CLASS|HIT DICE|ATTACKS|DAMAGE|SPECIAL ATTACKS|"
    r"SPECIAL DEFENSES|MAGIC RESISTANCE|RARITY|FREQUENCY|NO\. ENCOUNTERED|"
    r"LAIR PROBABILITY|LAIR PROBABLITY|TREASURE|INTELLIGENCE|ALIGNMENT|"
    r"LEVEL/X\.P\.|LEVEL/X\.P|LEVEL / X\.P\.|LEVEL / X\.P)\s*:\s*(.*)$",
    re.IGNORECASE,
)
SECTION_PATTERN = re.compile(
    r"^\s*(GENERAL INFORMATION|LANGUAGES|PHYSICAL DESCRIPTION|VARIANTS)\s*:?\s*(.*)$",
    re.IGNORECASE,
)
PAGE_MARKER_PATTERN = re.compile(r"^\s*\d{1,3}(?:\s+\d{1,3})?\s*$")
HEADING_CHAR_PATTERN = re.compile(r"^[A-Z0-9 '&(),./\-]+$")
LETTER_RANGE_PATTERN = re.compile(r"^[A-Z](?:\s*-\s*[A-Z])?$")
GENERIC_LABEL_PATTERN = re.compile(r"^\s*([A-Za-z][A-Za-z0-9/ .+\-()']{0,40})\s*:\s*(.*)$")


@dataclass
class ImportPage:
    actual_page: int
    book: int
    text: str


@dataclass
class ParsedEntry:
    heading: str
    book: int
    actual_page_start: int
    actual_page_end: int
    raw_text: str
    start_page_prefix: str = ""


@dataclass
class MonsterImportResult:
    catalog: dict[str, Any]
    report_text: str
    candidate_headings_detected: int
    rejected_candidate_count: int
    monsters_detected: int
    monsters_parsed: int
    warnings: list[str] = field(default_factory=list)
    missing_expected_fields: list[str] = field(default_factory=list)
    duplicate_ids: list[str] = field(default_factory=list)
    rejected_candidates: list[str] = field(default_factory=list)
    first_last_by_book: dict[int, tuple[str | None, str | None]] = field(default_factory=dict)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import monster entries from the combined monster manual PDF."
    )
    parser.add_argument(
        "pdf_path",
        nargs="?",
        default=str(DEFAULT_MONSTER_MANUAL_PDF),
        help="Path to the combined monster manual PDF.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_MONSTER_CATALOG_JSON),
        help="Path to write the editable monster catalog JSON.",
    )
    parser.add_argument(
        "--report",
        default=str(DEFAULT_MONSTER_IMPORT_REPORT),
        help="Path to write the import report text file.",
    )
    parser.add_argument(
        "--source-id",
        default=MONSTER_MANUAL_SOURCE_ID,
        help="Registered monster source ID to use for source metadata and default path resolution.",
    )
    parser.add_argument(
        "--allow-inactive-source",
        action="store_true",
        help="Allow import from a source registry entry marked inactive, comparison-only, or deprecated.",
    )
    return parser.parse_args(argv)


def canonical_label(label: str) -> str:
    normalized = " ".join(label.strip().upper().split())
    return LABEL_TO_KEY.get(normalized, normalized.lower())


def book_for_page(actual_page: int) -> int | None:
    for book, start, end in BOOK_ENTRY_RANGES:
        if start <= actual_page <= end:
            return book
    return None


def extract_pdf_pages(pdf_path: Path) -> list[ImportPage]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "The monster manual importer requires pypdf for PDF extraction. "
            "Use the bundled Codex runtime Python or install pypdf in the "
            "environment used for this tooling command."
        ) from exc

    reader = PdfReader(str(pdf_path))
    pages: list[ImportPage] = []
    for index, page in enumerate(reader.pages, start=1):
        book = book_for_page(index)
        if book is None:
            continue
        text = page.extract_text() or ""
        pages.append(ImportPage(actual_page=index, book=book, text=text))
    return pages


def normalize_line(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\x0c", " ")).strip()


def normalize_multiline_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(normalize_line(line) for line in text.splitlines() if normalize_line(line))


def is_page_marker_line(line: str) -> bool:
    stripped = normalize_line(line)
    return bool(stripped and PAGE_MARKER_PATTERN.fullmatch(stripped))


def title_case_name(name: str) -> str:
    return " ".join(name.strip().split()).title()


def slugify_name(name: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "", title_case_name(name).lower())
    return base or "unknownmonster"


def build_heading_name_variants(name: str) -> set[str]:
    normalized = title_case_name(name)
    variants = {
        normalized.lower(),
        normalized.replace(",", "").lower(),
    }
    if "," in normalized:
        left, right = [part.strip() for part in normalized.split(",", 1)]
        swapped = f"{right} {left}".strip().lower()
        variants.add(swapped)
        if not swapped.endswith("s"):
            variants.add(f"{swapped}s")
    return {variant for variant in variants if variant}


def is_running_header_candidate(line: str) -> bool:
    stripped = normalize_line(line)
    if not stripped:
        return False
    if stripped.startswith("OF "):
        return True
    if LETTER_RANGE_PATTERN.fullmatch(stripped):
        return True
    if stripped.startswith("-") or stripped.endswith("-"):
        return True
    if " - " in stripped:
        return True
    return False


def is_blocking_header_line(line: str) -> bool:
    stripped = normalize_line(line)
    if not stripped or ":" in stripped:
        return False
    if stripped in HEADING_IGNORE:
        return False
    if stripped != stripped.upper():
        return False
    if not re.search(r"[A-Z]", stripped):
        return False
    if not HEADING_CHAR_PATTERN.fullmatch(stripped):
        return False
    return True


def is_heading_candidate(line: str) -> bool:
    stripped = normalize_line(line)
    return is_blocking_header_line(stripped) and not is_running_header_candidate(stripped)


def looks_like_narrative_line(line: str) -> bool:
    stripped = normalize_line(line)
    if not stripped:
        return False
    if LABEL_PATTERN.match(stripped) or SECTION_PATTERN.match(stripped):
        return False
    return bool(re.search(r"[a-z]", stripped))


def has_size_before_next_header(
    lines: list[tuple[int, str]], start_index: int, lookahead: int = 12
) -> bool:
    seen = 0
    for _, candidate in lines[start_index + 1 :]:
        stripped = normalize_line(candidate)
        if not stripped:
            continue
        seen += 1
        if re.match(r"^SIZE\s*:", stripped, re.IGNORECASE):
            return True
        if SECTION_PATTERN.match(stripped):
            return False
        if looks_like_narrative_line(stripped):
            return False
        if is_blocking_header_line(stripped):
            return False
        if seen >= lookahead:
            break
    return False


def clean_page_lines(page: ImportPage) -> list[tuple[int, str]]:
    return [
        (page.actual_page, line)
        for line in page.text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
        if not is_page_marker_line(line)
    ]


def merge_split_label_records(line_records: list[tuple[int, str]]) -> list[tuple[int, str]]:
    merged: list[tuple[int, str]] = []
    index = 0
    while index < len(line_records):
        page_number, line = line_records[index]
        current = normalize_line(line)
        if index + 1 < len(line_records):
            _, next_line = line_records[index + 1]
            following = normalize_line(next_line)
            if (
                current
                and following
                and ":" in following
                and re.fullmatch(r"[A-Z/.\- ]{1,4}", current)
            ):
                combined = f"{current}{following}"
                combined_label = combined.split(":", 1)[0].strip().upper()
                if combined_label in LABEL_TO_KEY:
                    merged.append((page_number, combined))
                    index += 2
                    continue
        merged.append((page_number, line))
        index += 1
    return merged


def get_start_page_prefix_lines(
    line_records: list[tuple[int, str]], start_index: int
) -> list[str]:
    if not line_records or start_index <= 0:
        return []
    page_number = line_records[start_index][0]
    prefix_start = start_index
    while prefix_start > 0 and line_records[prefix_start - 1][0] == page_number:
        prefix_start -= 1
    return [line for _, line in line_records[prefix_start:start_index]]


def find_orphan_stat_lines(start_page_prefix: str, heading: str) -> list[str]:
    raw_lines = [
        line
        for line in start_page_prefix.replace("\r\n", "\n").replace("\r", "\n").splitlines()
        if normalize_line(line)
    ]
    if not raw_lines:
        return []
    section_index = next(
        (index for index, line in enumerate(raw_lines) if SECTION_PATTERN.match(normalize_line(line))),
        None,
    )
    if section_index is None:
        return []
    stat_region = raw_lines[:section_index]
    if not any(LABEL_PATTERN.match(normalize_line(line)) for line in stat_region):
        return []
    variants = build_heading_name_variants(heading)
    context_window = " ".join(
        normalize_line(line).lower() for line in raw_lines[section_index : section_index + 8]
    )
    if not any(variant in context_window for variant in variants):
        return []
    return [normalize_line(line) for line in stat_region if normalize_line(line)]


def trim_to_last_labeled_stat_line(stat_lines: list[str]) -> list[str]:
    last_label_index = None
    for index, line in enumerate(stat_lines):
        if LABEL_PATTERN.match(normalize_line(line)):
            last_label_index = index
    if last_label_index is None:
        return stat_lines
    return stat_lines[: last_label_index + 1]


def is_unmodeled_label_line(line: str) -> bool:
    stripped = normalize_line(line)
    if not stripped:
        return False
    if LABEL_PATTERN.match(stripped) or SECTION_PATTERN.match(stripped):
        return False
    return bool(GENERIC_LABEL_PATTERN.match(stripped))


def detect_entries_from_pages(pages: list[ImportPage]) -> tuple[list[ParsedEntry], list[str], int]:
    entries: list[ParsedEntry] = []
    rejected_candidates: list[str] = []
    candidate_headings_detected = 0
    for book in sorted({page.book for page in pages}):
        book_pages = [page for page in pages if page.book == book]
        line_records: list[tuple[int, str]] = []
        for page in book_pages:
            line_records.extend(clean_page_lines(page))
        line_records = merge_split_label_records(line_records)

        start_indexes: list[int] = []
        for index, (_, line) in enumerate(line_records):
            if not is_blocking_header_line(line):
                continue
            candidate_headings_detected += 1
            if is_heading_candidate(line) and has_size_before_next_header(line_records, index):
                start_indexes.append(index)
            else:
                rejected_candidates.append(normalize_line(line))

        for offset, start_index in enumerate(start_indexes):
            end_index = start_indexes[offset + 1] if offset + 1 < len(start_indexes) else len(line_records)
            chunk = line_records[start_index:end_index]
            if not chunk:
                continue
            raw_text = "\n".join(line for _, line in chunk).strip()
            if not raw_text:
                continue
            entries.append(
                ParsedEntry(
                    heading=normalize_line(chunk[0][1]),
                    book=book,
                    actual_page_start=chunk[0][0],
                    actual_page_end=chunk[-1][0],
                    raw_text=raw_text,
                    start_page_prefix="\n".join(get_start_page_prefix_lines(line_records, start_index)).strip(),
                )
            )
    return entries, rejected_candidates, candidate_headings_detected


def split_entries_from_pages(pages: list[ImportPage]) -> list[ParsedEntry]:
    entries, _, _ = detect_entries_from_pages(pages)
    return entries


def split_size_value(value: str | None) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    cleaned = " ".join(value.split())
    match = re.match(r"^([A-Za-z][A-Za-z\- ]*)(.*)$", cleaned)
    if not match:
        return cleaned, None
    size = match.group(1).strip(" ,;")
    detail = match.group(2).strip(" ,;")
    return size or None, detail or None


def split_damage_values(value: str | None) -> list[str]:
    if not value:
        return []
    cleaned = " ".join(value.split())
    if "," in cleaned:
        parts = [part.strip() for part in cleaned.split(",")]
    elif " and " in cleaned.lower():
        parts = [part.strip() for part in re.split(r"\band\b", cleaned, flags=re.IGNORECASE)]
    else:
        parts = [cleaned]
    return [part for part in parts if part]


def parse_level_xp(value: str | None) -> dict[str, Any]:
    cleaned = " ".join((value or "").split())
    parsed: dict[str, Any] = {"raw": cleaned}
    if not cleaned:
        return parsed
    match = re.match(
        r"^(?P<level>\d+)\s*/\s*(?P<xp_base>[\d,]+)(?:\s*\+\s*(?P<xp_per_hp>\d+)\s*/?\s*hp)?$",
        cleaned,
        re.IGNORECASE,
    )
    if match:
        parsed["level"] = int(match.group("level"))
        parsed["xp_base"] = int(match.group("xp_base").replace(",", ""))
        if match.group("xp_per_hp") is not None:
            parsed["xp_per_hp"] = int(match.group("xp_per_hp"))
    return parsed


def is_level_xp_continuation_line(line: str) -> bool:
    stripped = normalize_line(line)
    return bool(re.match(r"^\d+\s*HD?\b", stripped, re.IGNORECASE))


def find_stat_and_section_split(lines: list[str]) -> tuple[list[str], list[str]]:
    size_index = next(
        (index for index, line in enumerate(lines) if re.match(r"^\s*SIZE\s*:", line, re.IGNORECASE)),
        None,
    )
    if size_index is None:
        return [], lines
    level_index = next(
        (
            index
            for index in range(size_index, len(lines))
            if re.match(r"^\s*LEVEL(?: /)?/X\.P\.?\s*:", lines[index], re.IGNORECASE)
        ),
        None,
    )
    section_index = next(
        (
            index
            for index in range(size_index, len(lines))
            if SECTION_PATTERN.match(lines[index])
        ),
        None,
    )
    if section_index is not None:
        return lines[size_index:section_index], lines[section_index:]
    if level_index is None:
        return lines[size_index:], []

    blank_after_level = False
    for index in range(level_index + 1, len(lines)):
        stripped = normalize_line(lines[index])
        if not stripped:
            blank_after_level = True
            continue
        if is_level_xp_continuation_line(stripped):
            blank_after_level = False
            continue
        if blank_after_level or looks_like_narrative_line(lines[index]):
            return lines[size_index:index], lines[index:]
    return lines[size_index:], []


def parse_stat_block(stat_lines: list[str]) -> dict[str, Any]:
    values: dict[str, list[str]] = {}
    current_key: str | None = None
    for raw_line in stat_lines:
        line = normalize_line(raw_line)
        if not line:
            continue
        match = LABEL_PATTERN.match(line)
        if match:
            current_key = canonical_label(match.group(1))
            remainder = match.group(2).strip()
            values.setdefault(current_key, [])
            if remainder:
                values[current_key].append(remainder)
            continue
        if is_unmodeled_label_line(line):
            current_key = None
            continue
        if current_key is not None:
            values.setdefault(current_key, []).append(line)

    raw_values = {key: " ".join(parts).strip() for key, parts in values.items()}
    size, size_detail = split_size_value(raw_values.get("size"))
    return {
        "size": size,
        "size_detail": size_detail,
        "move": raw_values.get("move"),
        "armor_class": raw_values.get("armor_class"),
        "hit_dice": raw_values.get("hit_dice"),
        "attacks": raw_values.get("attacks"),
        "damage": split_damage_values(raw_values.get("damage")),
        "special_attacks": raw_values.get("special_attacks"),
        "special_defenses": raw_values.get("special_defenses"),
        "magic_resistance": raw_values.get("magic_resistance"),
        "rarity": raw_values.get("rarity"),
        "number_encountered": raw_values.get("number_encountered"),
        "lair_probability": raw_values.get("lair_probability"),
        "treasure": raw_values.get("treasure"),
        "intelligence": raw_values.get("intelligence"),
        "alignment": raw_values.get("alignment"),
        "level_xp": parse_level_xp(raw_values.get("level_xp")),
    }


def parse_sections(section_lines: list[str]) -> dict[str, str | None]:
    sections = {key: None for key in SECTION_KEYS}
    if not section_lines:
        return {
            "general_information": None,
            "languages": None,
            "physical_description": None,
            "variants": None,
        }

    current_key = "general_information"
    buffer: dict[str, list[str]] = {key: [] for key in SECTION_KEYS}
    for raw_line in section_lines:
        line = normalize_line(raw_line)
        if not line:
            if buffer[current_key]:
                buffer[current_key].append("")
            continue
        match = SECTION_PATTERN.match(line)
        if match:
            current_key = canonical_label(match.group(1))
            remainder = match.group(2).strip()
            if remainder:
                buffer[current_key].append(remainder)
            continue
        buffer[current_key].append(line)

    for key in SECTION_KEYS:
        text = "\n".join(buffer[key]).strip()
        sections[key] = text or None
    return {
        "general_information": sections["general_information"],
        "languages": sections["languages"],
        "physical_description": sections["physical_description"],
        "variants": sections["variants"],
    }


def build_tags(stat_block: dict[str, Any]) -> list[str]:
    tags: list[str] = []
    for key in ("size", "intelligence", "alignment", "rarity"):
        value = stat_block.get(key)
        if not value:
            continue
        normalized = re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")
        if not normalized:
            continue
        if key == "intelligence":
            normalized = f"{normalized}_intelligence"
        tags.append(normalized)
    seen: set[str] = set()
    return [tag for tag in tags if not (tag in seen or seen.add(tag))]


def parse_monster_entry(entry: ParsedEntry, source_file: str) -> tuple[dict[str, Any], list[str]]:
    warnings: list[str] = []
    raw_lines = [
        line
        for line in entry.raw_text.replace("\r\n", "\n").replace("\r", "\n").splitlines()
        if normalize_line(line) or line.strip() == ""
    ]
    stat_lines, section_lines = find_stat_and_section_split(raw_lines)
    orphan_stat_lines = find_orphan_stat_lines(entry.start_page_prefix, entry.heading)
    if orphan_stat_lines:
        stat_lines = trim_to_last_labeled_stat_line(stat_lines) + orphan_stat_lines
    if not stat_lines:
        warnings.append(f"{entry.heading}: could not locate a SIZE-based stat block.")
    stat_block = parse_stat_block(stat_lines)
    sections = parse_sections(section_lines)
    monster = {
        "id": slugify_name(entry.heading),
        "name": title_case_name(entry.heading),
        "sort_name": entry.heading,
        "source": {
            "file": source_file,
            "book": entry.book,
            "actual_page_start": entry.actual_page_start,
            "actual_page_end": entry.actual_page_end,
        },
        "stat_block": stat_block,
        "sections": sections,
        "tags": build_tags(stat_block),
        "raw_text": normalize_multiline_text(entry.raw_text),
    }
    return monster, warnings


def dotted_has_value(mapping: dict[str, Any], dotted_key: str) -> bool:
    current: Any = mapping
    for part in dotted_key.split("."):
        if not isinstance(current, dict) or part not in current:
            return False
        current = current[part]
    if isinstance(current, str):
        return bool(current.strip())
    if isinstance(current, list):
        return bool(current)
    return current is not None


def build_report_text(
    *,
    source_info: ResolvedMonsterSource,
    output_path: Path,
    report_path: Path,
    candidate_headings_detected: int,
    rejected_candidate_count: int,
    monsters_detected: int,
    monsters_parsed: int,
    warnings: list[str],
    rejected_candidates: list[str],
    missing_expected_fields: list[str],
    duplicate_ids: list[str],
    first_last_by_book: dict[int, tuple[str | None, str | None]],
) -> str:
    page_ranges = ", ".join(
        f"Book {book}: actual pages {start}-{end}" for book, start, end in BOOK_ENTRY_RANGES
    )
    lines = [
        "Monster Manual Import Report",
        "============================",
        "",
        "Importer: monster_manual_importer",
        f"Source ID: {source_info.source_id or 'None'}",
        f"Source title: {source_info.source_title or 'None'}",
        f"Source status: {source_info.source_status or 'None'}",
        f"Source path used: {source_info.source_path}",
        f"Source path mode: {'direct override' if source_info.used_path_override else 'registry/default'}",
        f"Registered expected path: {source_info.path_display}",
        f"Input file present: {'yes' if source_info.exists else 'no'}",
        f"Catalog output path: {output_path}",
        f"Report output path: {report_path}",
        "",
        f"Page ranges processed: {page_ranges}",
        f"Candidate headings detected: {candidate_headings_detected}",
        f"Candidate headings rejected as running headers or invalid entries: {rejected_candidate_count}",
        f"Monster records detected: {monsters_detected}",
        f"Monster records successfully parsed: {monsters_parsed}",
        "",
        "Warnings:",
    ]
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- None")
    lines.extend(["", "Rejected candidate headings:"])
    if rejected_candidates:
        lines.extend(f"- {item}" for item in rejected_candidates)
    else:
        lines.append("- None")
    lines.extend(["", "Entries missing expected fields:"])
    if missing_expected_fields:
        lines.extend(f"- {item}" for item in missing_expected_fields)
    else:
        lines.append("- None")
    lines.extend(["", "Duplicate IDs:"])
    if duplicate_ids:
        lines.extend(f"- {item}" for item in duplicate_ids)
    else:
        lines.append("- None")
    lines.extend(["", "First and last monster detected per book:"])
    for book, _, _ in BOOK_ENTRY_RANGES:
        first_name, last_name = first_last_by_book.get(book, (None, None))
        lines.append(
            f"- Book {book}: first={first_name or 'None'}, last={last_name or 'None'}"
        )
    lines.extend(
        [
            "",
            "Next recommended action:",
            f"- Review {report_path.name} for missing expected fields and rejected headings.",
            f"- Use {output_path.name} as the current source-preserving monster catalog artifact.",
        ]
    )
    return "\n".join(lines) + "\n"


def build_catalog_from_pages(
    pages: list[ImportPage], source_file_name: str, source_info: ResolvedMonsterSource
) -> MonsterImportResult:
    entries, rejected_candidates, candidate_headings_detected = detect_entries_from_pages(pages)
    monsters: list[dict[str, Any]] = []
    warnings: list[str] = []
    missing_expected_fields: list[str] = []
    first_last_by_book: dict[int, tuple[str | None, str | None]] = {}

    for book in sorted({page.book for page in pages}):
        book_entries = [entry for entry in entries if entry.book == book]
        first_last_by_book[book] = (
            book_entries[0].heading if book_entries else None,
            book_entries[-1].heading if book_entries else None,
        )

    for entry in entries:
        monster, entry_warnings = parse_monster_entry(entry, source_file_name)
        warnings.extend(entry_warnings)
        if monster["stat_block"].get("size") is None:
            warnings.append(
                f"{monster['name']}: rejected from catalog because no SIZE-based stat block was parsed."
            )
            rejected_candidates.append(monster["sort_name"])
            continue
        missing_required = [
            field_name
            for field_name in EXPECTED_REQUIRED_FIELDS
            if not dotted_has_value(monster, field_name)
        ]
        missing_common = [
            field_name
            for field_name in EXPECTED_COMMON_FIELDS
            if not dotted_has_value(monster, field_name)
        ]
        if missing_required:
            warnings.append(f"{monster['name']}: missing required fields {', '.join(missing_required)}")
        if missing_common:
            missing_expected_fields.append(
                f"{monster['name']}: {', '.join(missing_common)}"
            )
        monsters.append(monster)

    duplicate_ids = sorted(
        monster_id for monster_id, count in Counter(monster["id"] for monster in monsters).items() if count > 1
    )
    if duplicate_ids:
        warnings.extend(f"Duplicate monster id detected: {monster_id}" for monster_id in duplicate_ids)

    catalog = {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_id": source_info.source_id,
        "source_title": source_info.source_title,
        "source_status": source_info.source_status,
        "source_path": str(source_info.source_path),
        "source_pdf": source_file_name,
        "books_processed": [book for book, _, _ in BOOK_ENTRY_RANGES],
        "page_ranges_processed": [
            {"book": book, "actual_page_start": start, "actual_page_end": end}
            for book, start, end in BOOK_ENTRY_RANGES
        ],
        "monster_count": len(monsters),
        "monsters": monsters,
    }
    report_text = build_report_text(
        source_info=source_info,
        output_path=DEFAULT_MONSTER_CATALOG_JSON,
        report_path=DEFAULT_MONSTER_IMPORT_REPORT,
        candidate_headings_detected=candidate_headings_detected,
        rejected_candidate_count=len(rejected_candidates),
        monsters_detected=len(entries),
        monsters_parsed=len(monsters),
        warnings=warnings,
        rejected_candidates=rejected_candidates,
        missing_expected_fields=missing_expected_fields,
        duplicate_ids=duplicate_ids,
        first_last_by_book=first_last_by_book,
    )
    return MonsterImportResult(
        catalog=catalog,
        report_text=report_text,
        candidate_headings_detected=candidate_headings_detected,
        rejected_candidate_count=len(rejected_candidates),
        monsters_detected=len(entries),
        monsters_parsed=len(monsters),
        warnings=warnings,
        missing_expected_fields=missing_expected_fields,
        duplicate_ids=duplicate_ids,
        rejected_candidates=rejected_candidates,
        first_last_by_book=first_last_by_book,
    )


def import_monster_manual(
    pdf_path: Path = DEFAULT_MONSTER_MANUAL_PDF,
    output_path: Path = DEFAULT_MONSTER_CATALOG_JSON,
    report_path: Path = DEFAULT_MONSTER_IMPORT_REPORT,
    *,
    source_id: str = MONSTER_MANUAL_SOURCE_ID,
    allow_inactive_source: bool = False,
) -> MonsterImportResult:
    source_info = resolve_registered_monster_source(
        default_source_id=MONSTER_MANUAL_SOURCE_ID,
        override_path=pdf_path if pdf_path != DEFAULT_MONSTER_MANUAL_PDF else None,
        source_id=source_id,
        allow_inactive_source=allow_inactive_source,
    )

    pages = extract_pdf_pages(source_info.source_path)
    result = build_catalog_from_pages(
        pages=pages,
        source_file_name=source_info.source_path.name,
        source_info=source_info,
    )
    result.report_text = build_report_text(
        source_info=source_info,
        output_path=output_path,
        report_path=report_path,
        candidate_headings_detected=result.candidate_headings_detected,
        rejected_candidate_count=result.rejected_candidate_count,
        monsters_detected=result.monsters_detected,
        monsters_parsed=result.monsters_parsed,
        warnings=result.warnings,
        rejected_candidates=result.rejected_candidates,
        missing_expected_fields=result.missing_expected_fields,
        duplicate_ids=result.duplicate_ids,
        first_last_by_book=result.first_last_by_book,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result.catalog, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    report_path.write_text(result.report_text, encoding="utf-8")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = import_monster_manual(
            pdf_path=Path(args.pdf_path),
            output_path=Path(args.output),
            report_path=Path(args.report),
            source_id=args.source_id,
            allow_inactive_source=args.allow_inactive_source,
        )
    except FileNotFoundError as exc:
        print(exc)
        return 1
    except RuntimeError as exc:
        print(exc)
        return 1

    print(
        f"Parsed {result.monsters_parsed} monsters from {Path(args.pdf_path).name} "
        f"with {len(result.warnings)} warning(s)."
    )
    print(f"Wrote catalog: {args.output}")
    print(f"Wrote report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
