from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.importers.monster_manual_importer import slugify_name, title_case_name


JSON_IMPORT_VERSION = "v0.8.11"
TOP_LEVEL_ALLOWED_FIELDS = {
    "id",
    "name",
    "sort_name",
    "display_name",
    "source",
    "source_id",
    "source_name",
    "source_type",
    "source_file",
    "source_page",
    "source_record_id",
    "source_book",
    "source_actual_page_start",
    "source_actual_page_end",
    "import_method",
    "stat_block",
    "sections",
    "tags",
    "raw_text",
    "notes",
    "warnings",
    "custom_record",
    "manual_override",
    "protected_fields",
    "edited_fields",
    "last_updated",
    "import_metadata",
    "size",
    "move",
    "armor_class",
    "hit_dice",
    "attacks",
    "damage",
    "special_attacks",
    "special_defenses",
    "magic_resistance",
    "rarity",
    "number_encountered",
    "lair_probability",
    "treasure",
    "intelligence",
    "alignment",
    "level_xp",
    "general_information",
    "languages",
    "physical_description",
    "variants",
}
STAT_BLOCK_FIELDS = (
    "size",
    "size_detail",
    "move",
    "armor_class",
    "hit_dice",
    "attacks",
    "damage",
    "special_attacks",
    "special_defenses",
    "magic_resistance",
    "rarity",
    "number_encountered",
    "lair_probability",
    "treasure",
    "intelligence",
    "alignment",
    "level_xp",
)
SECTION_FIELDS = (
    "general_information",
    "languages",
    "physical_description",
    "variants",
)
MANUAL_SOURCE_TYPES = {"custom", "manual", "generated", "user"}


@dataclass
class NormalizedMonsterRecord:
    record: dict[str, Any] | None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class MergeDecision:
    action: str
    monster_id: str | None
    monster_name: str
    normalized_name: str
    reason: str
    warnings: list[str] = field(default_factory=list)
    existing_monster_id: str | None = None
    source_record_key: str | None = None


@dataclass
class MonsterCatalogMergeResult:
    merged_catalog: dict[str, Any]
    normalized_records: list[dict[str, Any]]
    decisions: list[MergeDecision]
    warnings: list[str] = field(default_factory=list)


def normalize_monster_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", name.casefold())


def load_json_file(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def coerce_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def coerce_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [text for item in value if (text := coerce_text(item))]
    if isinstance(value, str):
        text = coerce_text(value)
        return [text] if text else []
    return []


def coerce_level_xp(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        result = {str(key): val for key, val in value.items()}
        raw_value = coerce_text(result.get("raw"))
        if raw_value is not None:
            result["raw"] = raw_value
        return result
    raw_value = coerce_text(value)
    return {"raw": raw_value or ""}


def normalize_stat_block(raw_record: dict[str, Any]) -> dict[str, Any]:
    source = raw_record.get("stat_block")
    stat_source = source if isinstance(source, dict) else {}
    result: dict[str, Any] = {}
    for field_name in STAT_BLOCK_FIELDS:
        if field_name == "damage":
            value = stat_source.get(field_name, raw_record.get(field_name))
            result[field_name] = coerce_string_list(value)
            continue
        if field_name == "level_xp":
            value = stat_source.get(field_name, raw_record.get(field_name))
            result[field_name] = coerce_level_xp(value)
            continue
        value = stat_source.get(field_name, raw_record.get(field_name))
        result[field_name] = coerce_text(value)
    return result


def normalize_sections(raw_record: dict[str, Any]) -> dict[str, str | None]:
    source = raw_record.get("sections")
    section_source = source if isinstance(source, dict) else {}
    return {
        field_name: coerce_text(section_source.get(field_name, raw_record.get(field_name)))
        for field_name in SECTION_FIELDS
    }


def build_import_metadata(
    *,
    source_id_override: str | None,
    source_name: str,
    source_type: str,
    source_file: str,
    import_method: str,
    original_name: str,
    normalized_name: str,
    source_record_id: str | None,
    source_page: int | None,
    import_version: str,
    warnings: list[str],
    extra_fields: list[str],
    notes: list[str],
) -> dict[str, Any]:
    source_id = source_id_override or f"{source_type}:{source_name}"
    metadata: dict[str, Any] = {
        "source_id": source_id,
        "source_name": source_name,
        "source_type": source_type,
        "source_file": source_file,
        "source_page": source_page,
        "import_method": import_method,
        "import_version": import_version,
        "original_name": original_name,
        "normalized_name": normalized_name,
        "source_record_id": source_record_id,
        "warnings": warnings,
        "notes": notes,
    }
    if extra_fields:
        metadata["extra_fields"] = extra_fields
    return metadata


def normalize_monster_record(
    raw_record: Any,
    *,
    source_id_override: str | None = None,
    source_name: str,
    source_type: str,
    source_file: str,
    import_method: str = "json_import",
    import_version: str = JSON_IMPORT_VERSION,
) -> NormalizedMonsterRecord:
    if not isinstance(raw_record, dict):
        return NormalizedMonsterRecord(
            record=None,
            errors=["Record must be a JSON object."],
        )

    warnings: list[str] = []
    errors: list[str] = []
    original_name = coerce_text(
        raw_record.get("name") or raw_record.get("display_name") or raw_record.get("sort_name")
    )
    if not original_name:
        errors.append("Missing required field: name")
        return NormalizedMonsterRecord(record=None, warnings=warnings, errors=errors)

    sort_name = coerce_text(raw_record.get("sort_name")) or original_name.upper()
    display_name = coerce_text(raw_record.get("name")) or title_case_name(original_name)
    normalized_name = normalize_monster_name(sort_name)
    source_record_id = coerce_text(raw_record.get("source_record_id"))
    source_page_raw = raw_record.get("source_page")
    source_page = source_page_raw if isinstance(source_page_raw, int) else None

    stat_block = normalize_stat_block(raw_record)
    if stat_block.get("size") is None:
        warnings.append("Missing recommended field: stat_block.size")
    if not any(stat_block.get(field_name) for field_name in ("hit_dice", "level_xp", "rarity")):
        warnings.append("Missing recommended monster detail fields.")

    sections = normalize_sections(raw_record)
    tags = coerce_string_list(raw_record.get("tags"))
    raw_text = coerce_text(raw_record.get("raw_text")) or ""
    protected_fields = coerce_string_list(raw_record.get("protected_fields"))
    edited_fields = coerce_string_list(raw_record.get("edited_fields"))
    notes = coerce_string_list(raw_record.get("notes"))
    extra_fields = sorted(set(raw_record) - TOP_LEVEL_ALLOWED_FIELDS)
    if extra_fields:
        warnings.append(f"Preserving extra source fields: {', '.join(extra_fields)}")

    source: dict[str, Any] = {}
    if isinstance(raw_record.get("source"), dict):
        source.update(raw_record["source"])
    source.setdefault("file", coerce_text(raw_record.get("source_file")) or source_file)
    source.setdefault("name", coerce_text(raw_record.get("source_name")) or source_name)
    source.setdefault("type", coerce_text(raw_record.get("source_type")) or source_type)
    if source_record_id:
        source.setdefault("record_id", source_record_id)
    if source_page is not None:
        source.setdefault("actual_page_start", source_page)
        source.setdefault("actual_page_end", source_page)
    if isinstance(raw_record.get("source_book"), int):
        source.setdefault("book", raw_record["source_book"])
    if isinstance(raw_record.get("source_actual_page_start"), int):
        source["actual_page_start"] = raw_record["source_actual_page_start"]
    if isinstance(raw_record.get("source_actual_page_end"), int):
        source["actual_page_end"] = raw_record["source_actual_page_end"]

    record = {
        "id": coerce_text(raw_record.get("id")) or slugify_name(display_name),
        "name": display_name,
        "sort_name": sort_name,
        "source": source,
        "stat_block": stat_block,
        "sections": sections,
        "tags": tags,
        "raw_text": raw_text,
        "custom_record": bool(raw_record.get("custom_record", False)),
        "manual_override": bool(raw_record.get("manual_override", False)),
        "protected_fields": protected_fields,
        "edited_fields": edited_fields,
        "last_updated": coerce_text(raw_record.get("last_updated")),
        "source_conflicts": [],
        "import_metadata": build_import_metadata(
            source_id_override=source_id_override,
            source_name=source["name"],
            source_type=source["type"],
            source_file=str(source["file"]),
            import_method=coerce_text(raw_record.get("import_method")) or import_method,
            original_name=original_name,
            normalized_name=normalized_name,
            source_record_id=source_record_id or coerce_text(source.get("record_id")),
            source_page=source.get("actual_page_start") if isinstance(source.get("actual_page_start"), int) else None,
            import_version=import_version,
            warnings=warnings.copy(),
            extra_fields=extra_fields,
            notes=notes,
        ),
    }
    for field_name in extra_fields:
        record.setdefault("source_extra_fields", {})[field_name] = raw_record[field_name]
    return NormalizedMonsterRecord(record=record, warnings=warnings, errors=errors)


def iter_json_monster_records(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        monsters = payload.get("monsters")
        if isinstance(monsters, list):
            return monsters
        return [payload]
    raise ValueError("JSON source must be a record object, a list of records, or an object containing a monsters list.")


def load_json_monster_records(
    json_path: Path,
    *,
    source_id_override: str | None = None,
    source_name: str | None = None,
    source_type: str = "json",
    import_method: str = "json_import",
    import_version: str = JSON_IMPORT_VERSION,
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    payload = load_json_file(json_path)
    warnings: list[str] = []
    errors: list[str] = []
    normalized_records: list[dict[str, Any]] = []
    for index, raw_record in enumerate(iter_json_monster_records(payload), start=1):
        normalized = normalize_monster_record(
            raw_record,
            source_id_override=source_id_override,
            source_name=source_name or json_path.stem,
            source_type=source_type,
            source_file=json_path.name,
            import_method=import_method,
            import_version=import_version,
        )
        if normalized.errors:
            errors.append(f"Record {index}: {'; '.join(normalized.errors)}")
            continue
        if normalized.record is not None:
            normalized_records.append(normalized.record)
            warnings.extend(f"Record {index}: {warning}" for warning in normalized.warnings)
    return normalized_records, warnings, errors


def canonical_record_for_comparison(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": record.get("id"),
        "name": record.get("name"),
        "sort_name": record.get("sort_name"),
        "stat_block": record.get("stat_block"),
        "sections": record.get("sections"),
        "tags": record.get("tags"),
        "raw_text": record.get("raw_text"),
    }


def records_equivalent(left: dict[str, Any], right: dict[str, Any]) -> bool:
    return canonical_record_for_comparison(left) == canonical_record_for_comparison(right)


def is_manual_or_protected(record: dict[str, Any]) -> bool:
    if record.get("custom_record") or record.get("manual_override"):
        return True
    protected_fields = record.get("protected_fields")
    if isinstance(protected_fields, list) and protected_fields:
        return True
    import_metadata = record.get("import_metadata")
    if isinstance(import_metadata, dict):
        source_type = str(import_metadata.get("source_type") or "").lower()
        if source_type in MANUAL_SOURCE_TYPES:
            return True
    source = record.get("source")
    if isinstance(source, dict):
        source_type = str(source.get("type") or "").lower()
        if source_type in MANUAL_SOURCE_TYPES:
            return True
    return False


def source_record_key(record: dict[str, Any]) -> str | None:
    import_metadata = record.get("import_metadata")
    source_id = None
    record_id = None
    if isinstance(import_metadata, dict):
        source_id = coerce_text(import_metadata.get("source_id"))
        record_id = coerce_text(import_metadata.get("source_record_id"))
    if not source_id:
        source = record.get("source")
        if isinstance(source, dict):
            source_name = coerce_text(source.get("name"))
            source_type = coerce_text(source.get("type"))
            if source_name and source_type:
                source_id = f"{source_type}:{source_name}"
            record_id = record_id or coerce_text(source.get("record_id"))
    if source_id and record_id:
        return f"{source_id}::{record_id}"
    return None


def build_existing_indexes(
    catalog: dict[str, Any],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_source_record: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in catalog.get("monsters", []):
        monster_id = coerce_text(record.get("id"))
        if monster_id:
            by_id[monster_id].append(record)
        normalized_name = normalize_monster_name(str(record.get("sort_name") or record.get("name") or ""))
        if normalized_name:
            by_name[normalized_name].append(record)
        record_key = source_record_key(record)
        if record_key:
            by_source_record[record_key].append(record)
    return by_id, by_name, by_source_record


def build_catalog_sources(catalog: dict[str, Any], source_summary: dict[str, Any]) -> list[dict[str, Any]]:
    existing = catalog.get("catalog_sources")
    sources = deepcopy(existing) if isinstance(existing, list) else []
    sources.append(source_summary)
    return sources


def merge_monster_catalog(
    existing_catalog: dict[str, Any],
    imported_records: list[dict[str, Any]],
    *,
    apply_safe_additions: bool = False,
) -> MonsterCatalogMergeResult:
    merged_catalog = deepcopy(existing_catalog)
    merged_catalog.setdefault("monsters", [])
    existing_by_id, existing_by_name, existing_by_source_record = build_existing_indexes(merged_catalog)
    decisions: list[MergeDecision] = []
    warnings: list[str] = []
    seen_input_source_records: set[str] = set()

    for record in imported_records:
        monster_id = str(record.get("id") or "")
        monster_name = str(record.get("name") or record.get("sort_name") or monster_id)
        normalized_name = normalize_monster_name(str(record.get("sort_name") or monster_name))
        record_key = source_record_key(record)
        action = "would_add"
        reason = "No matching monster ID, normalized name, or source record was found."
        existing_match: dict[str, Any] | None = None

        if record_key and record_key in seen_input_source_records:
            action = "would_conflict"
            reason = "The same source record appears more than once in the JSON import input."
        elif record_key:
            seen_input_source_records.add(record_key)

        if action == "would_add" and record_key and existing_by_source_record.get(record_key):
            existing_match = existing_by_source_record[record_key][0]
            if records_equivalent(existing_match, record):
                action = "exact_duplicate"
                reason = "A matching source record with equivalent monster data already exists."
            elif is_manual_or_protected(existing_match):
                action = "protected_conflict"
                reason = "An existing manual or protected monster record blocks source-record overwrite."
            else:
                action = "would_update"
                reason = "The same source record already exists but differs from the imported data."

        if action == "would_add" and existing_by_id.get(monster_id):
            existing_match = existing_by_id[monster_id][0]
            if records_equivalent(existing_match, record):
                action = "exact_duplicate"
                reason = "A monster with the same ID and equivalent data already exists."
            elif is_manual_or_protected(existing_match):
                action = "protected_conflict"
                reason = "An existing manual or protected monster record uses the same ID."
            else:
                action = "would_conflict"
                reason = "An existing monster record uses the same ID but different data."

        if action == "would_add" and existing_by_name.get(normalized_name):
            existing_match = existing_by_name[normalized_name][0]
            if records_equivalent(existing_match, record):
                action = "exact_duplicate"
                reason = "A monster with the same normalized name and equivalent data already exists."
            elif is_manual_or_protected(existing_match):
                action = "protected_conflict"
                reason = "An existing manual or protected monster record uses the same normalized name."
            else:
                action = "would_conflict"
                reason = "An existing monster record uses the same normalized name but different data."

        decision = MergeDecision(
            action=action,
            monster_id=monster_id or None,
            monster_name=monster_name,
            normalized_name=normalized_name,
            reason=reason,
            warnings=list(record.get("import_metadata", {}).get("warnings", [])),
            existing_monster_id=existing_match.get("id") if existing_match else None,
            source_record_key=record_key,
        )
        decisions.append(decision)
        if decision.warnings:
            warnings.extend(f"{monster_name}: {warning}" for warning in decision.warnings)

        if action == "would_add" and apply_safe_additions:
            merged_catalog["monsters"].append(record)
            existing_by_id.setdefault(monster_id, []).append(record)
            existing_by_name.setdefault(normalized_name, []).append(record)
            if record_key:
                existing_by_source_record.setdefault(record_key, []).append(record)

    if apply_safe_additions:
        merged_catalog["monster_count"] = len(merged_catalog["monsters"])
        merged_catalog["generated_at"] = datetime.now(UTC).isoformat()
    return MonsterCatalogMergeResult(
        merged_catalog=merged_catalog,
        normalized_records=imported_records,
        decisions=decisions,
        warnings=warnings,
    )


def build_json_import_preview(
    *,
    source_path: Path,
    source_id: str | None,
    source_name: str,
    source_type: str,
    source_status: str | None = None,
    existing_catalog: dict[str, Any],
    merge_result: MonsterCatalogMergeResult,
    errors: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    decision_counts = Counter(decision.action for decision in merge_result.decisions)
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "import_version": JSON_IMPORT_VERSION,
        "source": {
            "id": source_id,
            "path": str(source_path),
            "name": source_name,
            "type": source_type,
            "status": source_status,
            "method": "json_import",
        },
        "base_monster_count": existing_catalog.get("monster_count", len(existing_catalog.get("monsters", []))),
        "normalized_record_count": len(merge_result.normalized_records),
        "decision_counts": dict(decision_counts),
        "errors": errors,
        "warnings": warnings + merge_result.warnings,
        "decisions": [
            {
                "action": decision.action,
                "monster_id": decision.monster_id,
                "monster_name": decision.monster_name,
                "normalized_name": decision.normalized_name,
                "reason": decision.reason,
                "warnings": decision.warnings,
                "existing_monster_id": decision.existing_monster_id,
                "source_record_key": decision.source_record_key,
            }
            for decision in merge_result.decisions
        ],
        "normalized_records": merge_result.normalized_records,
    }


def build_json_import_report_text(
    *,
    source_path: Path,
    source_id: str | None,
    source_name: str,
    source_type: str,
    source_status: str | None = None,
    existing_catalog: dict[str, Any],
    merge_result: MonsterCatalogMergeResult,
    errors: list[str],
    warnings: list[str],
    apply_safe_additions: bool,
) -> str:
    decision_counts = Counter(decision.action for decision in merge_result.decisions)
    lines = [
        "Monster JSON Import Report",
        "==========================",
        "",
        f"Source ID: {source_id or 'None'}",
        f"Source path: {source_path}",
        f"Source name: {source_name}",
        f"Source type: {source_type}",
        f"Source status: {source_status or 'unregistered_path'}",
        f"Base catalog monster count: {existing_catalog.get('monster_count', len(existing_catalog.get('monsters', [])))}",
        f"Normalized JSON records: {len(merge_result.normalized_records)}",
        f"Dry run only: {'no' if apply_safe_additions else 'yes'}",
        "",
        "Decision counts:",
    ]
    if decision_counts:
        for action, count in sorted(decision_counts.items()):
            lines.append(f"- {action}: {count}")
    else:
        lines.append("- None")

    lines.extend(["", "Errors:"])
    if errors:
        lines.extend(f"- {item}" for item in errors)
    else:
        lines.append("- None")

    lines.extend(["", "Warnings:"])
    merged_warnings = warnings + merge_result.warnings
    if merged_warnings:
        lines.extend(f"- {item}" for item in merged_warnings)
    else:
        lines.append("- None")

    lines.extend(["", "Would add:"])
    additions = [decision for decision in merge_result.decisions if decision.action == "would_add"]
    if additions:
        lines.extend(
            f"- {decision.monster_name} ({decision.monster_id})"
            for decision in additions
        )
    else:
        lines.append("- None")

    lines.extend(["", "Would update:"])
    updates = [decision for decision in merge_result.decisions if decision.action == "would_update"]
    if updates:
        lines.extend(
            f"- {decision.monster_name} ({decision.monster_id}) vs existing {decision.existing_monster_id}: {decision.reason}"
            for decision in updates
        )
    else:
        lines.append("- None")

    lines.extend(["", "Conflicts and protected records:"])
    conflicts = [
        decision
        for decision in merge_result.decisions
        if decision.action in {"would_conflict", "protected_conflict"}
    ]
    if conflicts:
        lines.extend(
            f"- {decision.monster_name} ({decision.monster_id}) [{decision.action}]: {decision.reason}"
            for decision in conflicts
        )
    else:
        lines.append("- None")

    lines.extend(["", "Exact duplicates:"])
    duplicates = [decision for decision in merge_result.decisions if decision.action == "exact_duplicate"]
    if duplicates:
        lines.extend(
            f"- {decision.monster_name} ({decision.monster_id})"
            for decision in duplicates
        )
    else:
        lines.append("- None")

    lines.extend(
        [
            "",
            "Source metadata conventions:",
            "- import_metadata.source_id preserves a registered source ID when one is supplied; otherwise it falls back to '<source_type>:<source_name>'.",
            "- import_metadata preserves source_name, source_type, source_file, source_page, source_record_id, import_method, import_version, original_name, normalized_name, warnings, notes, and any extra source fields.",
            "- manual/custom protection relies on custom_record, manual_override, protected_fields, or a manual/custom source type.",
            "",
            "Merge behavior:",
            "- Dry-run preview never silently overwrites existing catalog records.",
            "- Manual or protected records block updates and are reported as protected_conflict.",
            "- Explicit write mode only applies safe additions; conflicts and updates remain report-only for later review.",
            "",
            "Deferred follow-up:",
            "- Full Bestiary editing remains a future milestone.",
            "- Region and rarity generation remain a future milestone after the catalog and Bestiary patterns settle.",
            "- Spells, gear, arms, armor, and image support remain intentionally deferred.",
        ]
    )
    return "\n".join(lines) + "\n"
