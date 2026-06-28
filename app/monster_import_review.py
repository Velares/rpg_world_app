from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tools.importers.monster_manual_schema import PROJECT_ROOT


DEFAULT_CANDIDATES_PATH = (
    PROJECT_ROOT / "data" / "import_reports" / "monster_canonical_group_candidates.json"
)

REQUIRED_TOP_LEVEL_FIELDS = {
    "generated_at",
    "mandbmaster_record_count",
    "megadungeon_record_count",
    "total_candidate_groups",
    "candidate_groups",
}


def load_canonical_group_report(path: Path | None = None) -> dict[str, Any]:
    """Load the canonical-group candidate report JSON.

    Raises FileNotFoundError with a helpful message if the report is missing,
    and ValueError if the JSON is malformed or missing required fields.
    """
    report_path = path or DEFAULT_CANDIDATES_PATH
    if not report_path.exists():
        raise FileNotFoundError(
            f"Canonical-group candidate report not found at {report_path}. "
            "Run 'python tools/importers/monster_canonical_group_candidates.py' first."
        )
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Canonical-group candidate report at {report_path} is not valid JSON: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise ValueError(
            f"Canonical-group candidate report at {report_path} must be a JSON object."
        )
    missing = REQUIRED_TOP_LEVEL_FIELDS - set(payload.keys())
    if missing:
        raise ValueError(
            f"Canonical-group candidate report at {report_path} is missing fields: {sorted(missing)}"
        )
    if not isinstance(payload["candidate_groups"], list):
        raise ValueError(
            f"Canonical-group candidate report at {report_path} must contain a 'candidate_groups' list."
        )
    return payload


def _format_record(record: dict[str, Any]) -> str:
    lines = [
        f"  - ID: {record.get('id', 'N/A')}",
        f"  - Display Name: {record.get('display_name', 'N/A')}",
        f"  - Canonical Name: {record.get('canonical_name', 'N/A')}",
        f"  - Source: {record.get('source_title', 'N/A')} ({record.get('source_id', 'N/A')})",
        f"  - Pages: {record.get('source_page_start', 'N/A')} - {record.get('source_page_end', 'N/A')}",
        f"  - AC: {record.get('armor_class', 'N/A')}, HD: {record.get('hit_dice', 'N/A')}, "
        f"MV: {record.get('movement', 'N/A')}, XP: {record.get('xp', 'N/A')}",
        f"  - Review Status: {record.get('review_status', 'N/A')}",
    ]
    return "\n".join(lines)


def format_candidate_group(group: dict[str, Any]) -> str:
    """Return a readable text block for a single candidate group."""
    lines = [
        "Canonical Group Candidate",
        "=========================",
        "",
        f"Group ID: {group.get('candidate_group_id', 'N/A')}",
        f"Proposed Name: {group.get('proposed_canonical_name', 'N/A')}",
        f"Confidence: {group.get('confidence', 'N/A')}",
        f"Match Score: {group.get('match_score', 'N/A')}",
        f"Match Reasons: {', '.join(group.get('match_reasons', [])) or 'N/A'}",
        f"Review Status: {group.get('review_status', 'N/A')}",
        f"User Decision: {group.get('user_decision', 'None')}",
        "",
        "Source Variants (read-only, not merged):",
        "----------------------------------------",
    ]
    for index, record in enumerate(group.get("records", []), 1):
        lines.append(f"\nVariant {index}:")
        lines.append(_format_record(record))
    notes = group.get("notes", [])
    if notes:
        lines.extend(["", "Notes:", "------"])
        lines.extend(f"- {note}" for note in notes)
    lines.extend(
        [
            "",
            "This is a review suggestion only. No records have been merged.",
        ]
    )
    return "\n".join(lines)


def build_candidate_rows(payload: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Build (label, group) tuples for a list-based UI."""
    rows: list[tuple[str, dict[str, Any]]] = []
    for group in payload.get("candidate_groups", []):
        confidence = group.get("confidence", "unknown")
        proposed = group.get("proposed_canonical_name", "Unknown")
        score = group.get("match_score", "N/A")
        label = f"[{confidence.upper()}] {proposed} (score={score})"
        rows.append((label, group))
    return rows


def review_summary_text(payload: dict[str, Any]) -> str:
    """Return a summary suitable for the main output pane."""
    confidence_counts = {"high": 0, "medium": 0, "low": 0}
    for group in payload.get("candidate_groups", []):
        confidence = group.get("confidence", "unknown")
        confidence_counts[confidence] = confidence_counts.get(confidence, 0) + 1

    lines = [
        "Monster Import Canonical-Group Review",
        "=====================================",
        "",
        f"MandBmaster records: {payload.get('mandbmaster_record_count', 'N/A')}",
        f"Megadungeon records: {payload.get('megadungeon_record_count', 'N/A')}",
        f"Total candidate groups: {payload.get('total_candidate_groups', 'N/A')}",
        f"High confidence: {confidence_counts.get('high', 0)}",
        f"Medium confidence: {confidence_counts.get('medium', 0)}",
        f"Low confidence: {confidence_counts.get('low', 0)}",
        "",
        "This is a read-only review surface. No records are merged.",
        "Select a candidate group from the list to inspect source variants.",
    ]
    return "\n".join(lines)
