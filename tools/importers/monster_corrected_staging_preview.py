from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __name__ == "__main__":
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from tools.importers.monster_manual_schema import PROJECT_ROOT
from app.monster_editor import (
    DEFAULT_CORRECTIONS_PATH,
    DEFAULT_MANDBMASTER_PREVIEW_PATH,
    DEFAULT_MEGADUNGEON_PREVIEW_PATH,
    DISPLAY_FIELDS,
    apply_corrections,
    get_record_correction,
    load_all_normalized_previews,
    load_corrections,
)
from app.monster_import_review import (
    DEFAULT_DECISIONS_PATH as DEFAULT_CANONICAL_DECISIONS_PATH,
    load_decisions as load_canonical_decisions,
)


DEFAULT_STAGING_PREVIEW_JSON = (
    PROJECT_ROOT / "data" / "import_reports" / "monster_corrected_staging_preview.json"
)
DEFAULT_STAGING_PREVIEW_REPORT = (
    PROJECT_ROOT / "data" / "import_reports" / "monster_corrected_staging_preview_report.txt"
)


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_source_provenance(metadata: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_id": metadata.get("source_id", "unknown"),
        "source_title": metadata.get("source_title", "unknown"),
        "source_file": metadata.get("source_file"),
        "source_entry_id": record.get("source_entry_id"),
        "source_slug": record.get("source_slug"),
        "source_page_start": record.get("source_page_start"),
        "source_page_end": record.get("source_page_end"),
        "generated_at": metadata.get("generated_at"),
    }


def _build_review_metadata(record: dict[str, Any], corrections: dict[str, Any]) -> dict[str, Any]:
    record_id = record.get("id", "")
    entry = get_record_correction(corrections, record_id)
    correction_status = entry.get("record_status", "needs_review")
    if not entry.get("fields") and correction_status == "needs_review":
        correction_status = "uncorrected"
    return {
        "missing_fields": list(record.get("missing_fields", [])),
        "placeholder_fields": list(record.get("placeholder_fields", [])),
        "mapping_confidence": dict(record.get("mapping_confidence", {})),
        "review_status": record.get("review_status", "unknown"),
        "correction_status": correction_status,
    }


def _build_correction_block(corrections: dict[str, Any], record_id: str) -> dict[str, Any]:
    entry = get_record_correction(corrections, record_id)
    return {
        "record_status": entry.get("record_status", "needs_review"),
        "record_notes": entry.get("record_notes", ""),
        "updated_at": entry.get("updated_at", ""),
        "reviewer": entry.get("reviewer", "local_user"),
        "fields": dict(entry.get("fields", {})),
    }


def _build_original_fields(record: dict[str, Any]) -> dict[str, Any]:
    return {
        field: record.get(field)
        for field in DISPLAY_FIELDS
    }


def _build_effective_fields(record: dict[str, Any], corrections: dict[str, Any]) -> dict[str, Any]:
    overlayed = apply_corrections(record, corrections)
    return {
        field: overlayed.get(field)
        for field in DISPLAY_FIELDS
    }


def build_staged_record(
    metadata: dict[str, Any],
    record: dict[str, Any],
    corrections: dict[str, Any],
) -> dict[str, Any]:
    """Return a single staged record with original, correction, and effective sections."""
    record_id = record.get("id", "")
    return {
        "id": record_id,
        "display_name": record.get("display_name"),
        "source_id": metadata.get("source_id", "unknown"),
        "source_title": metadata.get("source_title", "unknown"),
        "original": _build_original_fields(record),
        "corrections": _build_correction_block(corrections, record_id),
        "effective": _build_effective_fields(record, corrections),
        "source_provenance": _build_source_provenance(metadata, record),
        "review_metadata": _build_review_metadata(record, corrections),
        "raw_stat_block": record.get("raw_stat_block", ""),
        "raw_text": record.get("raw_text", ""),
    }


def build_staging_preview(
    preview_paths: list[Path] | None = None,
    corrections_path: Path | None = None,
    canonical_decisions_path: Path | None = None,
) -> dict[str, Any]:
    """Load normalized records and corrections, returning a staged preview container."""
    records = load_all_normalized_previews(preview_paths)
    try:
        corrections = load_corrections(corrections_path)
    except ValueError as exc:
        raise ValueError(f"Could not load corrections: {exc}") from exc

    try:
        canonical_decisions = load_canonical_decisions(canonical_decisions_path)
    except (FileNotFoundError, ValueError):
        canonical_decisions = {}

    staged_records = [
        build_staged_record(metadata, record, corrections)
        for metadata, record in records
    ]

    source_counts: dict[str, int] = Counter()
    for metadata, _record in records:
        source_counts[metadata.get("source_id", "unknown")] += 1

    return {
        "schema_version": 1,
        "generated_at": _now_utc_iso(),
        "source_reports": [str(p) for p in (preview_paths or [
            DEFAULT_MANDBMASTER_PREVIEW_PATH,
            DEFAULT_MEGADUNGEON_PREVIEW_PATH,
        ])],
        "correction_store": str(corrections_path or DEFAULT_CORRECTIONS_PATH),
        "canonical_decisions_store": str(canonical_decisions_path or DEFAULT_CANONICAL_DECISIONS_PATH),
        "canonical_decisions_context": canonical_decisions,
        "record_count": len(staged_records),
        "source_counts": dict(source_counts),
        "staged_records": staged_records,
    }


def format_report(preview: dict[str, Any]) -> str:
    """Return a plain-text summary of the staged preview."""
    lines = [
        "Corrected Monster Staging Preview",
        "=================================",
        "",
        f"Generated at: {preview.get('generated_at', 'N/A')}",
        f"Total normalized records read: {preview.get('record_count', 0)}",
    ]

    source_counts = preview.get("source_counts", {})
    for source_id, count in sorted(source_counts.items()):
        lines.append(f"- {source_id}: {count}")

    records = preview.get("staged_records", [])
    correction_records = [r for r in records if r["corrections"].get("fields")]
    correction_records_loaded = len(correction_records)
    lines.extend([
        "",
        f"Correction records loaded: {correction_records_loaded}",
    ])

    status_counts: Counter[str] = Counter()
    field_counts: Counter[str] = Counter()
    records_with_missing = 0
    records_with_placeholders = 0
    for record in records:
        status = record["review_metadata"]["correction_status"]
        status_counts[status] += 1
        for field_name in record["corrections"].get("fields", {}):
            field_counts[field_name] += 1
        if record["review_metadata"]["missing_fields"]:
            records_with_missing += 1
        if record["review_metadata"]["placeholder_fields"]:
            records_with_placeholders += 1

    lines.extend([
        "",
        "Correction status counts:",
    ])
    for status, count in sorted(status_counts.items()):
        lines.append(f"- {status}: {count}")

    if field_counts:
        lines.extend([
            "",
            "Most often corrected fields:",
        ])
        for field_name, count in field_counts.most_common():
            lines.append(f"- {field_name}: {count}")

    lines.extend([
        "",
        f"Records still having missing fields: {records_with_missing}",
        f"Records still having placeholder fields: {records_with_placeholders}",
        "",
        "WARNING: This is a non-live staging preview. No master catalog was created.",
        "Source variants remain distinct. No records were merged.",
        "",
    ])

    corrected_sample = [r for r in records if r["corrections"].get("fields")]
    if corrected_sample:
        lines.append("Sample corrected records:")
        for record in corrected_sample[:5]:
            lines.append(f"- {record['id']}: {record['display_name']} [{record['source_id']}]")
    else:
        lines.append("No corrected records found.")

    lines.append("")
    uncorrected_sample = [r for r in records if not r["corrections"].get("fields")]
    if uncorrected_sample:
        lines.append("Sample uncorrected records:")
        for record in uncorrected_sample[:5]:
            lines.append(f"- {record['id']}: {record['display_name']} [{record['source_id']}]")
    else:
        lines.append("All records have corrections.")

    return "\n".join(lines)


def write_staging_preview(
    preview: dict[str, Any],
    json_path: Path | None = None,
    report_path: Path | None = None,
) -> tuple[Path, Path]:
    """Write the JSON staging preview and its report."""
    json_path = json_path or DEFAULT_STAGING_PREVIEW_JSON
    report_path = report_path or DEFAULT_STAGING_PREVIEW_REPORT
    json_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    json_path.write_text(
        json.dumps(preview, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    report_path.write_text(format_report(preview), encoding="utf-8")
    return json_path, report_path


def main() -> None:
    preview = build_staging_preview()
    json_path, report_path = write_staging_preview(preview)
    print(f"Wrote corrected staging preview to {json_path}")
    print(f"Wrote corrected staging report to {report_path}")


if __name__ == "__main__":
    main()
