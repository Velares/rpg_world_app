from __future__ import annotations

import argparse
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
import re
from typing import Any


if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from tools.importers.monster_manual_importer import is_page_marker_line, normalize_line
from tools.importers.monster_manual_schema import (
    DEFAULT_MEGADUNGEON_MONSTER_PDF,
    MEGADUNGEON_MONSTER_SOURCE_ID,
    ResolvedMonsterSource,
    resolve_registered_monster_source,
)


LABEL_ALIASES = {
    "noenc": "number_encountered",
    "alignment": "alignment",
    "movement": "movement",
    "armorclass": "armor_class",
    "hitdice": "hit_dice",
    "attacks": "attacks",
    "damage": "damage",
    "save": "save",
    "morale": "morale",
    "treasure": "treasure",
    "xp": "xp",
}
DISPLAY_LABELS = {
    "number_encountered": "No. Enc",
    "alignment": "Alignment",
    "movement": "Movement",
    "armor_class": "Armor Class",
    "hit_dice": "Hit Dice",
    "attacks": "Attacks",
    "damage": "Damage",
    "save": "Save",
    "morale": "Morale",
    "treasure": "Treasure",
    "xp": "XP",
}
REQUIRED_STAT_KEYS = tuple(DISPLAY_LABELS.keys())
MUST_HAVE_STAT_KEYS = {
    "number_encountered",
    "alignment",
    "movement",
    "armor_class",
    "hit_dice",
    "xp",
}
HEADING_CONNECTORS = {"a", "an", "and", "for", "in", "of", "or", "the", "to"}
HEADING_IGNORE = {
    "Credits and Acknowledgements",
    "MEGADUNGEON",
    "MONSTER MANUAL",
    "Greg Gillespie",
}
GENERIC_LABEL_PATTERN = re.compile(r"^\s*([A-Za-z. ]{2,40})\s*:\s*(.*)$")
TITLE_WORD_PATTERN = re.compile(r"^[A-Z][a-z]+(?:['-][A-Z][a-z]+)*$")
UPPERCASE_WORD_PATTERN = re.compile(r"^[A-Z]{2,}$")
HEADING_TOKEN_PATTERN = re.compile(r"[A-Za-z]+(?:['-][A-Za-z]+)*|[A-Z]{2,}|&|\d+")
LABEL_TOKEN_NORMALIZER = re.compile(r"[^a-z]+")


@dataclass
class ProbePage:
    actual_page: int
    text: str


@dataclass
class MegadungeonMonsterEntry:
    name: str
    source_id: str
    actual_page_start: int
    actual_page_end: int
    raw_stat_block: str
    raw_text: str
    fields: dict[str, str]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class MegadungeonProbeResult:
    source: ResolvedMonsterSource
    pages: list[int]
    entries: list[MegadungeonMonsterEntry]
    report_text: str


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe the Megadungeon Monster Manual PDF without writing catalog output."
    )
    parser.add_argument(
        "pdf_path",
        nargs="?",
        default=None,
        help="Optional direct path override for the Megadungeon Monster Manual PDF.",
    )
    parser.add_argument(
        "--probe",
        action="store_true",
        help="Run read-only probe mode. This milestone supports probe mode only.",
    )
    parser.add_argument(
        "--pages",
        nargs="*",
        type=int,
        default=None,
        help="Actual PDF pages to probe, for example --pages 9 11 83.",
    )
    parser.add_argument(
        "--source-id",
        default=MEGADUNGEON_MONSTER_SOURCE_ID,
        help="Registered monster source ID used for source metadata and default path resolution.",
    )
    parser.add_argument(
        "--allow-inactive-source",
        action="store_true",
        help="Allow probing a source registry entry marked inactive or comparison-only.",
    )
    return parser.parse_args(argv)


def resolve_probe_source(
    pdf_path: Path | None = None,
    *,
    source_id: str = MEGADUNGEON_MONSTER_SOURCE_ID,
    allow_inactive_source: bool = False,
) -> ResolvedMonsterSource:
    return resolve_registered_monster_source(
        default_source_id=MEGADUNGEON_MONSTER_SOURCE_ID,
        override_path=pdf_path,
        source_id=source_id,
        allow_inactive_source=allow_inactive_source,
    )


def extract_probe_pages(
    pdf_path: Path,
    actual_pages: list[int] | None = None,
) -> list[ProbePage]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError(
            "The Megadungeon probe requires pypdf for PDF extraction. "
            "Use the bundled Codex runtime Python or install pypdf in the "
            "environment used for this tooling command."
        ) from exc

    reader = PdfReader(str(pdf_path))
    if actual_pages is None:
        pages_to_read = list(range(1, len(reader.pages) + 1))
    else:
        pages_to_read = actual_pages

    pages: list[ProbePage] = []
    for actual_page in pages_to_read:
        if actual_page < 1 or actual_page > len(reader.pages):
            raise ValueError(
                f"Requested page {actual_page} is outside the PDF page range 1-{len(reader.pages)}."
            )
        text = reader.pages[actual_page - 1].extract_text() or ""
        pages.append(ProbePage(actual_page=actual_page, text=text))
    return pages


def normalize_label_token(label: str) -> str:
    compact = LABEL_TOKEN_NORMALIZER.sub("", normalize_line(label).lower())
    return compact


def parse_stat_label_line(line: str) -> tuple[str, str] | None:
    match = GENERIC_LABEL_PATTERN.match(line)
    if not match:
        return None
    key = LABEL_ALIASES.get(normalize_label_token(match.group(1)))
    if key is None:
        return None
    return key, normalize_line(match.group(2))


def tokenize_heading(line: str) -> list[str]:
    return HEADING_TOKEN_PATTERN.findall(line)


def is_title_case_heading_candidate(line: str) -> bool:
    stripped = normalize_line(line)
    if not stripped or ":" in stripped or stripped in HEADING_IGNORE:
        return False
    if stripped.endswith((".", ";", ",")):
        return False
    tokens = tokenize_heading(stripped)
    if not tokens or len(tokens) > 6:
        return False

    saw_title_word = False
    for token in tokens:
        lower = token.lower()
        if lower in HEADING_CONNECTORS:
            continue
        if token == "&":
            continue
        if token.isdigit():
            return False
        if TITLE_WORD_PATTERN.fullmatch(token) or UPPERCASE_WORD_PATTERN.fullmatch(token):
            saw_title_word = True
            continue
        return False
    return saw_title_word


def has_required_stat_block_nearby(
    lines: list[tuple[int, str]],
    start_index: int,
    *,
    lookahead: int = 18,
    min_labels: int = 8,
) -> bool:
    found: set[str] = set()
    steps = 0
    for _, candidate in lines[start_index + 1 :]:
        stripped = normalize_line(candidate)
        if not stripped:
            continue
        steps += 1
        parsed = parse_stat_label_line(stripped)
        if parsed is not None:
            found.add(parsed[0])
            if len(found) >= min_labels and MUST_HAVE_STAT_KEYS.issubset(found):
                return True
            continue
        if is_title_case_heading_candidate(stripped):
            return False
        if steps >= lookahead:
            break
    return False


def build_normalized_line_index(pages: list[ProbePage]) -> list[tuple[int, str]]:
    indexed_lines: list[tuple[int, str]] = []
    for page in pages:
        for raw_line in page.text.replace("\r\n", "\n").replace("\r", "\n").splitlines():
            line = normalize_line(raw_line)
            if not line or is_page_marker_line(line):
                continue
            indexed_lines.append((page.actual_page, line))
    return indexed_lines


def split_entries_from_pages(pages: list[ProbePage]) -> list[MegadungeonMonsterEntry]:
    indexed_lines = build_normalized_line_index(pages)
    heading_indexes = [
        index
        for index, (_, line) in enumerate(indexed_lines)
        if is_title_case_heading_candidate(line)
        and has_required_stat_block_nearby(indexed_lines, index)
    ]

    entries: list[MegadungeonMonsterEntry] = []
    for position, start_index in enumerate(heading_indexes):
        end_index = (
            heading_indexes[position + 1]
            if position + 1 < len(heading_indexes)
            else len(indexed_lines)
        )
        entry_lines = indexed_lines[start_index:end_index]
        if not entry_lines:
            continue
        entries.append(parse_entry_lines(entry_lines))
    return entries


def parse_entry_lines(entry_lines: list[tuple[int, str]]) -> MegadungeonMonsterEntry:
    start_page = entry_lines[0][0]
    end_page = entry_lines[-1][0]
    name = entry_lines[0][1]
    body_lines = [line for _, line in entry_lines[1:]]
    raw_text = "\n".join(line for _, line in entry_lines)

    fields: dict[str, str] = {}
    warnings: list[str] = []
    raw_stat_lines: list[str] = []
    duplicate_keys: list[str] = []
    collecting_stat_block = True

    for line in body_lines:
        parsed = parse_stat_label_line(line)
        if parsed is not None and collecting_stat_block:
            key, value = parsed
            if key in fields:
                duplicate_keys.append(key)
            fields[key] = value
            raw_stat_lines.append(line)
            continue
        collecting_stat_block = False

    if not raw_stat_lines:
        warnings.append("no_stat_block_detected")

    missing_keys = [key for key in REQUIRED_STAT_KEYS if key not in fields]
    if missing_keys:
        warnings.append(
            "missing_stat_labels: " + ", ".join(DISPLAY_LABELS[key] for key in missing_keys)
        )
    if duplicate_keys:
        warnings.append(
            "duplicate_stat_labels: "
            + ", ".join(DISPLAY_LABELS[key] for key in sorted(set(duplicate_keys)))
        )
    if end_page > start_page:
        warnings.append("entry_spans_multiple_pages")

    return MegadungeonMonsterEntry(
        name=name,
        source_id=MEGADUNGEON_MONSTER_SOURCE_ID,
        actual_page_start=start_page,
        actual_page_end=end_page,
        raw_stat_block="\n".join(raw_stat_lines),
        raw_text=raw_text,
        fields=fields,
        warnings=warnings,
    )


def build_probe_report(
    source: ResolvedMonsterSource,
    pages: list[ProbePage],
    entries: list[MegadungeonMonsterEntry],
) -> str:
    lines = [
        "Megadungeon Monster Probe",
        "=========================",
        "",
        f"Source ID: {source.source_id}",
        f"Source title: {source.source_title}",
        f"Source status: {source.source_status}",
        f"Source path mode: {'direct override' if source.used_path_override else 'registry default'}",
        f"Source path: {source.path_display}",
        f"Pages probed: {', '.join(str(page.actual_page) for page in pages) if pages else '(none)'}",
        f"Entries detected: {len(entries)}",
    ]
    for entry in entries:
        lines.extend(
            [
                "",
                f"{entry.name} (pages {entry.actual_page_start}-{entry.actual_page_end})",
                f"Warnings: {', '.join(entry.warnings) if entry.warnings else 'None'}",
            ]
        )
        for key in REQUIRED_STAT_KEYS:
            if key in entry.fields:
                lines.append(f"- {DISPLAY_LABELS[key]}: {entry.fields[key]}")
    return "\n".join(lines) + "\n"


def probe_megadungeon(
    *,
    pdf_path: Path | None = None,
    actual_pages: list[int] | None = None,
    source_id: str = MEGADUNGEON_MONSTER_SOURCE_ID,
    allow_inactive_source: bool = False,
) -> MegadungeonProbeResult:
    source = resolve_probe_source(
        pdf_path,
        source_id=source_id,
        allow_inactive_source=allow_inactive_source,
    )
    pages = extract_probe_pages(source.source_path, actual_pages=actual_pages)
    entries = split_entries_from_pages(pages)
    report_text = build_probe_report(source, pages, entries)
    return MegadungeonProbeResult(
        source=source,
        pages=[page.actual_page for page in pages],
        entries=entries,
        report_text=report_text,
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.probe:
        print(
            "Only --probe mode is supported in this milestone. "
            "No catalog-writing import has been implemented yet.",
            file=sys.stderr,
        )
        return 2

    override_path = Path(args.pdf_path) if args.pdf_path else None
    try:
        result = probe_megadungeon(
            pdf_path=override_path,
            actual_pages=args.pages,
            source_id=args.source_id,
            allow_inactive_source=args.allow_inactive_source,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(result.report_text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
