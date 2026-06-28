from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from tools.importers.monster_manual_schema import PROJECT_ROOT


DEFAULT_CANDIDATES_PATH = (
    PROJECT_ROOT / "data" / "import_reports" / "monster_canonical_group_candidates.json"
)

DECISIONS_DIR = PROJECT_ROOT / "data" / "import_reviews"
DEFAULT_DECISIONS_PATH = DECISIONS_DIR / "monster_canonical_group_decisions.json"

DECISION_SCHEMA_VERSION = 1
VALID_DECISIONS = {"approved", "rejected", "needs_review"}
DEFAULT_DECISION = "needs_review"
DEFAULT_REVIEWER = "local_user"

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
        "Decisions are stored separately and do not merge records.",
        "Select a candidate group from the list to inspect source variants and edit decisions.",
    ]
    return "\n".join(lines)


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_decision(value: str) -> str:
    normalized = str(value).strip().lower()
    if normalized not in VALID_DECISIONS:
        raise ValueError(
            f"Invalid decision value '{value}'. Allowed values: {sorted(VALID_DECISIONS)}"
        )
    return normalized


def load_decisions(path: Path | None = None) -> dict[str, Any]:
    """Load persisted review decisions.

    Returns an empty decisions container if the file is missing.
    Raises ValueError if the file exists but is malformed.
    """
    decisions_path = path or DEFAULT_DECISIONS_PATH
    if not decisions_path.exists():
        return {
            "schema_version": DECISION_SCHEMA_VERSION,
            "source_report": str(DEFAULT_CANDIDATES_PATH),
            "decisions": {},
        }
    try:
        data = json.loads(decisions_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"Decision file at {decisions_path} is not valid JSON: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise ValueError(f"Decision file at {decisions_path} must be a JSON object.")
    if "decisions" not in data or not isinstance(data["decisions"], dict):
        raise ValueError(
            f"Decision file at {decisions_path} must contain a 'decisions' object."
        )
    return data


def save_decisions(decisions: dict[str, Any], path: Path | None = None) -> None:
    """Persist review decisions atomically using a temp file and rename.

    The candidate report is not modified. Only the separate decision file is
    written.
    """
    decisions_path = path or DEFAULT_DECISIONS_PATH
    decisions_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": decisions.get("schema_version", DECISION_SCHEMA_VERSION),
        "source_report": decisions.get("source_report", str(DEFAULT_CANDIDATES_PATH)),
        "decisions": decisions.get("decisions", {}),
    }
    fd, temp_name = tempfile.mkstemp(
        dir=str(decisions_path.parent), suffix=".json", prefix=".tmp_"
    )
    try:
        with open(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.flush()
        temp_path = Path(temp_name)
        temp_path.replace(decisions_path)
    except Exception:
        try:
            Path(temp_name).unlink(missing_ok=True)
        except OSError:
            pass
        raise


def get_decision(decisions: dict[str, Any], group_id: str) -> dict[str, Any]:
    """Return the stored decision for a candidate group, or a default."""
    stored = decisions.get("decisions", {}).get(group_id, {})
    return {
        "decision": stored.get("decision", DEFAULT_DECISION),
        "notes": stored.get("notes", ""),
        "updated_at": stored.get("updated_at", ""),
        "reviewer": stored.get("reviewer", DEFAULT_REVIEWER),
    }


def set_decision(
    decisions: dict[str, Any],
    group_id: str,
    decision: str,
    notes: str = "",
    reviewer: str = DEFAULT_REVIEWER,
) -> dict[str, Any]:
    """Set a decision for a candidate group and return the updated container."""
    normalized = _validate_decision(decision)
    if "decisions" not in decisions or not isinstance(decisions["decisions"], dict):
        decisions["decisions"] = {}
    decisions["decisions"][group_id] = {
        "decision": normalized,
        "notes": str(notes).strip(),
        "updated_at": _now_utc_iso(),
        "reviewer": reviewer,
    }
    return decisions


def build_candidate_rows(
    payload: dict[str, Any], decisions: dict[str, Any] | None = None
) -> list[tuple[str, dict[str, Any]]]:
    """Build (label, group) tuples for a list-based UI."""
    rows: list[tuple[str, dict[str, Any]]] = []
    for group in payload.get("candidate_groups", []):
        confidence = group.get("confidence", "unknown")
        proposed = group.get("proposed_canonical_name", "Unknown")
        score = group.get("match_score", "N/A")
        group_id = group.get("candidate_group_id", "")
        decision = get_decision(decisions or {}, group_id) if group_id else None
        decision_tag = ""
        if decision and decision.get("decision") and decision["decision"] != DEFAULT_DECISION:
            decision_tag = f"[{decision['decision'].upper()}] "
        label = f"{decision_tag}[{confidence.upper()}] {proposed} (score={score})"
        rows.append((label, group))
    return rows


def format_decision_block(decision: dict[str, Any]) -> str:
    """Return a readable text block for a stored decision."""
    lines = [
        "Stored Decision",
        "---------------",
        f"Decision: {decision.get('decision', DEFAULT_DECISION).upper()}",
        f"Notes: {decision.get('notes', '') or 'None'}",
        f"Updated: {decision.get('updated_at', 'N/A')}",
        f"Reviewer: {decision.get('reviewer', DEFAULT_REVIEWER)}",
    ]
    return "\n".join(lines)
