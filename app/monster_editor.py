from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.importers.monster_manual_schema import PROJECT_ROOT


DEFAULT_CORRECTIONS_PATH = (
    PROJECT_ROOT / "data" / "import_reviews" / "monster_normalized_field_corrections.json"
)
CORRECTION_SCHEMA_VERSION = 1
VALID_RECORD_STATUSES = {"needs_review", "corrected", "approved"}
DEFAULT_RECORD_STATUS = "needs_review"
DEFAULT_REVIEWER = "local_user"

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
DEFAULT_CORRECTABLE_FIELDS = DISPLAY_FIELDS


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


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_record_status(value: str) -> str:
    normalized = str(value).strip().lower()
    if normalized not in VALID_RECORD_STATUSES:
        raise ValueError(
            f"Invalid record_status '{value}'. Allowed values: {sorted(VALID_RECORD_STATUSES)}"
        )
    return normalized


def load_corrections(path: Path | None = None) -> dict[str, Any]:
    """Load persisted normalized monster field corrections.

    Returns an empty corrections container if the file is missing.
    Raises ValueError if the file exists but is malformed.
    """
    corrections_path = path or DEFAULT_CORRECTIONS_PATH
    if not corrections_path.exists():
        return {
            "schema_version": CORRECTION_SCHEMA_VERSION,
            "source_reports": [
                str(DEFAULT_MANDBMASTER_PREVIEW_PATH),
                str(DEFAULT_MEGADUNGEON_PREVIEW_PATH),
            ],
            "corrections": {},
        }
    try:
        data = json.loads(corrections_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Corrections file at {corrections_path} is not valid JSON: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise ValueError(f"Corrections file at {corrections_path} must be a JSON object.")
    if "corrections" not in data or not isinstance(data["corrections"], dict):
        raise ValueError(
            f"Corrections file at {corrections_path} must contain a 'corrections' object."
        )
    return data


def save_corrections(corrections: dict[str, Any], path: Path | None = None) -> None:
    """Persist normalized monster field corrections atomically.

    Generated preview files and live catalog JSON are not modified.
    """
    corrections_path = path or DEFAULT_CORRECTIONS_PATH
    corrections_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": corrections.get("schema_version", CORRECTION_SCHEMA_VERSION),
        "source_reports": corrections.get(
            "source_reports",
            [
                str(DEFAULT_MANDBMASTER_PREVIEW_PATH),
                str(DEFAULT_MEGADUNGEON_PREVIEW_PATH),
            ],
        ),
        "corrections": corrections.get("corrections", {}),
    }
    fd, temp_name = tempfile.mkstemp(
        dir=str(corrections_path.parent), suffix=".json", prefix=".tmp_"
    )
    try:
        with open(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.flush()
        temp_path = Path(temp_name)
        temp_path.replace(corrections_path)
    except Exception:
        try:
            Path(temp_name).unlink(missing_ok=True)
        except OSError:
            pass
        raise


def get_record_correction(corrections: dict[str, Any], record_id: str) -> dict[str, Any]:
    """Return the stored correction entry for a record, or a default empty entry."""
    if not isinstance(corrections, dict) or "corrections" not in corrections:
        return {
            "fields": {},
            "record_notes": "",
            "record_status": DEFAULT_RECORD_STATUS,
            "updated_at": "",
            "reviewer": DEFAULT_REVIEWER,
        }
    stored = corrections.get("corrections", {}).get(record_id, {})
    return {
        "fields": dict(stored.get("fields", {})),
        "record_notes": stored.get("record_notes", ""),
        "record_status": stored.get("record_status", DEFAULT_RECORD_STATUS),
        "updated_at": stored.get("updated_at", ""),
        "reviewer": stored.get("reviewer", DEFAULT_REVIEWER),
    }


def set_field_correction(
    corrections: dict[str, Any],
    record_id: str,
    field_name: str,
    corrected_value: str,
    previous_value: Any,
    notes: str = "",
    reviewer: str = DEFAULT_REVIEWER,
) -> dict[str, Any]:
    """Set a field correction for a normalized monster record.

    Invalid field names are rejected with ValueError.
    """
    if field_name not in DISPLAY_FIELDS:
        raise ValueError(
            f"Field '{field_name}' is not in the correctable field list."
        )
    if "corrections" not in corrections or not isinstance(corrections["corrections"], dict):
        corrections["corrections"] = {}
    if record_id not in corrections["corrections"]:
        corrections["corrections"][record_id] = {
            "fields": {},
            "record_notes": "",
            "record_status": DEFAULT_RECORD_STATUS,
            "updated_at": "",
            "reviewer": DEFAULT_REVIEWER,
        }
    corrections["corrections"][record_id]["fields"][field_name] = {
        "corrected_value": str(corrected_value).strip(),
        "previous_value": previous_value if previous_value is not None else None,
        "notes": str(notes).strip(),
        "updated_at": _now_utc_iso(),
        "reviewer": reviewer,
    }
    corrections["corrections"][record_id]["updated_at"] = _now_utc_iso()
    corrections["corrections"][record_id]["reviewer"] = reviewer
    return corrections


def set_record_status(
    corrections: dict[str, Any],
    record_id: str,
    status: str,
    record_notes: str = "",
    reviewer: str = DEFAULT_REVIEWER,
) -> dict[str, Any]:
    """Set the record-level status and notes for a normalized monster record."""
    normalized_status = _validate_record_status(status)
    if "corrections" not in corrections or not isinstance(corrections["corrections"], dict):
        corrections["corrections"] = {}
    if record_id not in corrections["corrections"]:
        corrections["corrections"][record_id] = {
            "fields": {},
            "record_notes": "",
            "record_status": DEFAULT_RECORD_STATUS,
            "updated_at": "",
            "reviewer": DEFAULT_REVIEWER,
        }
    entry = corrections["corrections"][record_id]
    entry["record_status"] = normalized_status
    entry["record_notes"] = str(record_notes).strip()
    entry["updated_at"] = _now_utc_iso()
    entry["reviewer"] = reviewer
    return corrections


def apply_corrections(record: dict[str, Any], corrections: dict[str, Any]) -> dict[str, Any]:
    """Return a shallow copy of the record with stored corrections overlaid.

    The original record is not modified. Corrected values are converted to
    strings for display purposes; missing/placeholder markers remain visible.
    """
    overlayed = dict(record)
    record_id = record.get("id", "")
    entry = get_record_correction(corrections, record_id)
    for field_name, correction in entry.get("fields", {}).items():
        if field_name in DISPLAY_FIELDS:
            overlayed[field_name] = correction["corrected_value"]
    overlayed["__correction_record_status"] = entry.get("record_status", DEFAULT_RECORD_STATUS)
    overlayed["__correction_record_notes"] = entry.get("record_notes", "")
    return overlayed


def format_corrected_field(
    field_name: str,
    original_value: Any,
    correction: dict[str, Any] | None,
    missing_fields: list[str],
    placeholder_fields: list[str],
    mapping_confidence: dict[str, str],
) -> str:
    """Return a display line for a field showing original and corrected values."""
    corrected_value = correction["corrected_value"] if correction else None
    markers: list[str] = []
    if field_name in missing_fields:
        markers.append("MISSING")
    if field_name in placeholder_fields:
        markers.append("PLACEHOLDER")
    if correction:
        markers.append("CORRECTED")
    confidence = mapping_confidence.get(field_name, "")
    if confidence and confidence not in {"high", "missing"}:
        markers.append(f"confidence:{confidence}")

    marker_text = f" [{' | '.join(markers)}]" if markers else ""
    lines = [f"{field_name}: {_present(original_value)}{marker_text}"]
    if correction:
        lines.append(f"  -> corrected: {_present(corrected_value)}")
        if correction.get("notes"):
            lines.append(f"  -> correction note: {correction['notes']}")
    return "\n".join(lines)


def format_corrected_record(
    metadata: dict[str, Any],
    record: dict[str, Any],
    corrections: dict[str, Any],
) -> str:
    """Return a readable text block showing original and corrected field values."""
    record_id = record.get("id", "")
    entry = get_record_correction(corrections, record_id)
    overlayed = apply_corrections(record, corrections)

    lines = [
        "Normalized Monster Record (with Corrections)",
        "=============================================",
        "",
        f"Source: {metadata.get('source_title', 'N/A')} ({metadata.get('source_id', 'N/A')})",
        f"Source File: {metadata.get('source_file', 'N/A')}",
        f"Record ID: {record_id}",
        f"Source Entry ID: {record.get('source_entry_id', 'N/A')}",
        f"Source Slug: {record.get('source_slug', 'N/A')}",
        f"Source Pages: {record.get('source_page_start', 'N/A')} - {record.get('source_page_end', 'N/A')}",
        f"Generated Review Status: {record.get('review_status', 'N/A')}",
        f"Correction Record Status: {entry.get('record_status', DEFAULT_RECORD_STATUS).upper()}",
    ]
    if entry.get("record_notes"):
        lines.append(f"Record Notes: {entry['record_notes']}")
    if entry.get("updated_at"):
        lines.append(f"Last Corrected: {entry['updated_at']}")

    lines.extend(["", "Common Fields", "-------------"])
    missing_fields = record.get("missing_fields", [])
    placeholder_fields = record.get("placeholder_fields", [])
    mapping_confidence = record.get("mapping_confidence", {})
    for field_name in DISPLAY_FIELDS:
        original_value = record.get(field_name)
        correction = entry.get("fields", {}).get(field_name)
        lines.append(
            format_corrected_field(
                field_name,
                original_value,
                correction,
                missing_fields,
                placeholder_fields,
                mapping_confidence,
            )
        )

    lines.extend(
        [
            "",
            "Review only. Corrections are stored separately and do not modify",
            "generated preview files, source records, or the live catalog.",
        ]
    )
    return "\n".join(lines)


def correction_summary_text(corrections: dict[str, Any]) -> str:
    """Return a summary of stored corrections for display."""
    total_records = len(corrections.get("corrections", {}))
    total_fields = sum(
        len(entry.get("fields", {}))
        for entry in corrections.get("corrections", {}).values()
    )
    status_counts: dict[str, int] = {}
    for entry in corrections.get("corrections", {}).values():
        status = entry.get("record_status", DEFAULT_RECORD_STATUS)
        status_counts[status] = status_counts.get(status, 0) + 1

    lines = [
        "Correction Store Summary",
        "========================",
        "",
        f"Records with corrections: {total_records}",
        f"Corrected fields: {total_fields}",
    ]
    if status_counts:
        lines.append("")
        for status, count in sorted(status_counts.items()):
            lines.append(f"{status}: {count}")
    return "\n".join(lines)

