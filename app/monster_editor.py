from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.importers.monster_manual_schema import PROJECT_ROOT


DEFAULT_MANDBMASTER_PREVIEW_PATH = (
    PROJECT_ROOT / "data" / "import_reports" / "mandbmaster_normalized_monster_preview.json"
)
DEFAULT_MEGADUNGEON_PREVIEW_PATH = (
    PROJECT_ROOT / "data" / "import_reports" / "megadungeon_normalized_monster_preview.json"
)

REQUIRED_PREVIEW_FIELDS = {
    "generated_at",
    "source_id",
    "source_title",
    "record_count",
    "normalized_monsters",
}

DISPLAY_FIELDS = [
    "display_name",
    "canonical_name",
    "armor_class",
    "hit_dice",
    "movement",
    "attacks",
    "damage",
    "special_attacks",
    "special_defenses",
    "save",
    "morale",
    "xp",
    "alignment",
    "number_appearing",
    "treasure",
    "monster_type",
    "category",
    "environment",
    "terrain",
    "region",
    "size",
    "intelligence",
    "level",
    "challenge",
    "description",
]


def _present(value: Any) -> str:
    if value is None:
        return "<missing>"
    text = str(value).strip()
    return text or "<empty>"


def load_normalized_preview(path: Path) -> dict[str, Any]:
    """Load a normalized monster preview JSON file.

    Raises FileNotFoundError with a helpful message if the report is missing,
    and ValueError if the JSON is malformed or missing required fields.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"Normalized monster preview not found at {path}. "
            "Run the appropriate importer first."
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Normalized monster preview at {path} is not valid JSON: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise ValueError(
            f"Normalized monster preview at {path} must be a JSON object."
        )
    missing = REQUIRED_PREVIEW_FIELDS - set(payload.keys())
    if missing:
        raise ValueError(
            f"Normalized monster preview at {path} is missing fields: {sorted(missing)}"
        )
    if not isinstance(payload["normalized_monsters"], list):
        raise ValueError(
            f"Normalized monster preview at {path} must contain a 'normalized_monsters' list."
        )
    return payload


def load_all_normalized_previews(
    paths: list[Path] | None = None,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Load multiple normalized preview files and return (metadata, records) pairs.

    Missing or malformed files raise immediately so the caller can report them.
    """
    preview_paths = paths or [
        DEFAULT_MANDBMASTER_PREVIEW_PATH,
        DEFAULT_MEGADUNGEON_PREVIEW_PATH,
    ]
    results: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for path in preview_paths:
        metadata = load_normalized_preview(path)
        for record in metadata.get("normalized_monsters", []):
            results.append((metadata, record))
    return results


def build_normalized_monster_rows(
    records: list[tuple[dict[str, Any], dict[str, Any]]],
) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    """Build (label, metadata, record) tuples for a list-based UI."""
    rows: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    for metadata, record in records:
        source_id = metadata.get("source_id", "unknown")
        display_name = record.get("display_name", "Unknown Monster")
        review_status = record.get("review_status", "unknown")
        missing = len(record.get("missing_fields", []))
        placeholder = len(record.get("placeholder_fields", []))
        label = (
            f"[{source_id}] {display_name} "
            f"({review_status}; {missing} missing, {placeholder} placeholders)"
        )
        rows.append((label, metadata, record))
    return rows


def format_normalized_monster(metadata: dict[str, Any], record: dict[str, Any]) -> str:
    """Return a readable text block for a single normalized monster record."""
    lines = [
        "Normalized Monster Record",
        "=========================",
        "",
        f"Source: {metadata.get('source_title', 'N/A')} ({metadata.get('source_id', 'N/A')})",
        f"Source File: {metadata.get('source_file', 'N/A')}",
        f"Record ID: {record.get('id', 'N/A')}",
        f"Source Entry ID: {record.get('source_entry_id', 'N/A')}",
        f"Source Slug: {record.get('source_slug', 'N/A')}",
        f"Source Pages: {record.get('source_page_start', 'N/A')} - {record.get('source_page_end', 'N/A')}",
        f"Review Status: {record.get('review_status', 'N/A')}",
        "",
        "Common Fields",
        "-------------",
    ]
    for field_name in DISPLAY_FIELDS:
        value = record.get(field_name)
        marker = ""
        if field_name in record.get("missing_fields", []):
            marker = " [MISSING]"
        elif field_name in record.get("placeholder_fields", []):
            marker = " [PLACEHOLDER]"
        confidence = record.get("mapping_confidence", {}).get(field_name, "")
        if confidence and confidence != "high":
            marker += f" ({confidence})"
        lines.append(f"{field_name}: {_present(value)}{marker}")

    normalized = record.get("normalized_fields", [])
    missing = record.get("missing_fields", [])
    placeholders = record.get("placeholder_fields", [])
    review_notes = record.get("review_notes", [])

    lines.extend(
        [
            "",
            "Field Summary",
            "-------------",
            f"Normalized fields: {len(normalized)}",
            f"Missing fields: {len(missing)}",
            f"Placeholder fields: {len(placeholders)}",
        ]
    )
    if review_notes:
        lines.extend(["", "Review Notes", "------------"])
        lines.extend(f"- {note}" for note in review_notes)

    raw_stat_block = record.get("raw_stat_block", "")
    if raw_stat_block:
        lines.extend(
            [
                "",
                "Raw Stat Block",
                "--------------",
                raw_stat_block,
            ]
        )

    raw_text = record.get("raw_text", "")
    if raw_text:
        preview = raw_text[:1200]
        if len(raw_text) > 1200:
            preview += "\n... [truncated]"
        lines.extend(
            [
                "",
                "Raw Text Preview",
                "----------------",
                preview,
            ]
        )

    lines.extend(
        [
            "",
            "Review only. No source records or catalogs are modified.",
        ]
    )
    return "\n".join(lines)


def review_summary_text(records: list[tuple[dict[str, Any], dict[str, Any]]]) -> str:
    """Return a summary suitable for the main output pane."""
    source_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    total_missing = 0
    total_placeholders = 0
    for metadata, record in records:
        source_id = metadata.get("source_id", "unknown")
        source_counts[source_id] = source_counts.get(source_id, 0) + 1
        status = record.get("review_status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1
        total_missing += len(record.get("missing_fields", []))
        total_placeholders += len(record.get("placeholder_fields", []))

    lines = [
        "Normalized Monster Review",
        "=========================",
        "",
        f"Total records: {len(records)}",
    ]
    for source_id, count in sorted(source_counts.items()):
        lines.append(f"- {source_id}: {count}")
    lines.append("")
    for status, count in sorted(status_counts.items()):
        lines.append(f"{status}: {count}")
    lines.extend(
        [
            "",
            f"Total missing fields: {total_missing}",
            f"Total placeholder fields: {total_placeholders}",
            "",
            "Review only. No source records or catalogs are modified.",
            "Select a record to inspect normalized fields, missing fields, and raw text.",
        ]
    )
    return "\n".join(lines)
