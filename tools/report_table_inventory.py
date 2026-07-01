from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

if __name__ == "__main__":
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from tools.importers.monster_manual_schema import PROJECT_ROOT


DEFAULT_REPORT_JSON = (
    PROJECT_ROOT / "data" / "import_reports" / "table_inventory.json"
)
DEFAULT_REPORT_TXT = (
    PROJECT_ROOT / "data" / "import_reports" / "table_inventory_report.txt"
)


# Map a file stem to a domain/category.  Unknown files fall through to inference.
DOMAIN_BY_FILE: dict[str, str] = {
    "class_tables": "character generation",
    "player_background_tables": "character generation",
    "npc_tables": "NPC generation",
    "key_npc_tables": "NPC generation",
    "npc_depth_tables": "NPC generation",
    "settlement_tables": "settlement/location generation",
    "dungeon_tables": "settlement/location generation",
    "wilderness_tables": "settlement/location generation",
    "adventure_tables": "encounters/leads/adventure content",
    "weird_tables": "encounters/leads/adventure content",
    "interaction_tables": "interaction/dialogue/downtime text",
    "downtime_tables": "interaction/dialogue/downtime text",
    "item_tables": "inventory/equipment/resources",
    "treasure_tables": "inventory/equipment/resources",
    "monster_tables": "monster catalogs/import previews/review data",
    "monster_classification_options": "future classification tables",
    "monster_classification_affinities": "future classification tables",
    "source_registry": "source registry",
}

# Map a category name inside a table file to a domain, when the file itself is not enough.
DOMAIN_BY_CATEGORY: dict[str, str] = {
    "monster_names": "monster catalogs/import previews/review data",
    "monster_types": "monster catalogs/import previews/review data",
    "monster_intents": "monster catalogs/import previews/review data",
    "monster_signs": "monster catalogs/import previews/review data",
    "monster_weaknesses": "monster catalogs/import previews/review data",
    "monster_morale": "monster catalogs/import previews/review data",
    "monster_reactions": "monster catalogs/import previews/review data",
    "noncombat_options": "interaction/dialogue/downtime text",
    "avoidance_options": "interaction/dialogue/downtime text",
    "safe_combat_options": "interaction/dialogue/downtime text",
    "classes": "character generation",
    "backgrounds": "character generation",
    "origins": "character generation",
    "formative_events": "character generation",
    "personality_traits": "character generation",
    "ideals": "character generation",
    "bonds": "character generation",
    "flaws": "character generation",
    "tasks": "interaction/dialogue/downtime text",
    "item_definitions": "inventory/equipment/resources",
    "common_loadout": "inventory/equipment/resources",
    "class_loadouts": "inventory/equipment/resources",
    "male_names": "NPC generation",
    "female_names": "NPC generation",
    "neutral_names": "NPC generation",
    "surnames": "NPC generation",
    "ancestries": "NPC generation",
    "key_npc_reasons": "NPC generation",
    "key_npc_notes": "NPC generation",
    "ally_phase_events": "NPC generation",
    "at_odds_phase_events": "NPC generation",
    "neutral_phase_events": "NPC generation",
}

# Directories to scan and their default role labels.
SCAN_DIRS: list[tuple[Path, str]] = [
    (PROJECT_ROOT / "data" / "tables", "generation content"),
    (PROJECT_ROOT / "data" / "configs", "config data"),
    (PROJECT_ROOT / "data" / "catalogs", "rules data"),
    (PROJECT_ROOT / "data" / "names", "generation content"),
    (PROJECT_ROOT / "data" / "import_reports", "import data"),
    (PROJECT_ROOT / "data" / "import_reviews", "review data"),
]

# Single files to scan.
SCAN_FILES: list[tuple[Path, str]] = [
    (PROJECT_ROOT / "data" / "source_registry.json", "source registry"),
]


# Generated report filenames that should not be manually edited.
GENERATED_REPORT_FILES: set[str] = {
    "table_inventory.json",
    "table_inventory_report.txt",
    "monster_canonical_group_candidates.json",
    "monster_canonical_group_candidates_report.txt",
    "mandbmaster_normalized_monster_preview.json",
    "mandbmaster_normalized_monster_preview_report.txt",
    "megadungeon_normalized_monster_preview.json",
    "megadungeon_normalized_monster_preview_report.txt",
    "monster_corrected_staging_preview.json",
    "monster_corrected_staging_preview_report.txt",
    "monster_combat_projection.json",
    "monster_combat_projection_report.txt",
    "monster_classification_suggestions.json",
    "monster_classification_suggestions_report.txt",
}


def _category_for_path(path: Path, role: str) -> str:
    """Infer a broad domain for a table/config file."""
    stem = path.stem
    if stem in DOMAIN_BY_FILE:
        return DOMAIN_BY_FILE[stem]
    if role == "source registry":
        return "source registry"
    if role == "import data":
        return "monster catalogs/import previews/review data"
    if role == "review data":
        return "monster catalogs/import previews/review data"
    if role == "rules data":
        return "monster catalogs/import previews/review data"
    if "monster" in stem:
        return "monster catalogs/import previews/review data"
    if "name" in stem:
        return "NPC generation"
    return "other/unknown"


def _detect_fields(data: dict[str, Any] | list[Any]) -> dict[str, Any]:
    """Inspect a table category's data and return key-field summary."""
    if isinstance(data, list):
        entries = data
        first = entries[0] if entries else None
    else:
        return {}
    if not entries:
        return {"entry_count": 0, "is_empty": True}
    summary: dict[str, Any] = {
        "entry_count": len(entries),
        "sample_type": type(first).__name__,
    }
    if isinstance(first, dict):
        all_fields = set()
        for entry in entries:
            if isinstance(entry, dict):
                all_fields.update(entry.keys())
        summary["fields"] = sorted(all_fields)
        summary["id_present"] = any(
            key in ("id", "key", "item_key", "class_name", "task_key")
            for key in all_fields
        )
        summary["weighted"] = any(
            isinstance(entry, dict) and "weight" in entry for entry in entries
        )
    else:
        summary["is_text_list"] = True
    return summary


def _detect_duplicate_ids(entries: list[Any], id_field: str = "id") -> list[str]:
    """Report duplicate IDs if the entries are dicts with an id-like field."""
    if not entries or not isinstance(entries[0], dict):
        return []
    seen: dict[str, int] = {}
    duplicates: set[str] = set()
    candidates = ("id", "key", "item_key", "class_name", "task_key", "record_id")
    for field in candidates:
        if field in entries[0]:
            id_field = field
            break
    else:
        return []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        value = entry.get(id_field)
        if not isinstance(value, str) or not value.strip():
            continue
        if value in seen:
            duplicates.add(value)
        seen[value] = index
    return sorted(duplicates)


def _inspect_json(path: Path, role: str) -> dict[str, Any]:
    """Build an inventory record for a single JSON file."""
    record: dict[str, Any] = {
        "path": str(path.relative_to(PROJECT_ROOT)),
        "file": path.name,
        "table_name": path.stem,
        "domain": _category_for_path(path, role),
        "role": role,
        "generated_report": path.name in GENERATED_REPORT_FILES,
        "user_editable": path.parent.name in ("tables", "configs") and path.name not in GENERATED_REPORT_FILES,
        "categories": [],
        "warnings": [],
    }
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        record["warnings"].append(f"malformed JSON: {exc}")
        return record
    except OSError as exc:
        record["warnings"].append(f"could not read: {exc}")
        return record

    if isinstance(data, list):
        fields = _detect_fields(data)
        record["categories"].append(
            {
                "name": path.stem,
                "entry_count": fields.get("entry_count", 0),
                "is_empty": fields.get("is_empty", False),
                "fields": fields.get("fields", []),
                "id_present": fields.get("id_present", False),
                "weighted": fields.get("weighted", False),
                "is_text_list": fields.get("is_text_list", False),
                "duplicate_ids": _detect_duplicate_ids(data),
            }
        )
        if record["categories"][0]["is_empty"]:
            record["warnings"].append("table is empty")
        if record["categories"][0]["duplicate_ids"]:
            record["warnings"].append(
                f"duplicate ids: {', '.join(record['categories'][0]['duplicate_ids'][:5])}"
            )
    elif isinstance(data, dict):
        for key, value in data.items():
            if isinstance(value, list):
                fields = _detect_fields(value)
                category_record = {
                    "name": key,
                    "entry_count": fields.get("entry_count", 0),
                    "is_empty": fields.get("is_empty", False),
                    "fields": fields.get("fields", []),
                    "id_present": fields.get("id_present", False),
                    "weighted": fields.get("weighted", False),
                    "is_text_list": fields.get("is_text_list", False),
                    "domain": DOMAIN_BY_CATEGORY.get(
                        key, _category_for_path(path, role)
                    ),
                    "duplicate_ids": _detect_duplicate_ids(value),
                }
                record["categories"].append(category_record)
                if category_record["is_empty"]:
                    record["warnings"].append(f"{key}: empty table")
                if category_record["duplicate_ids"]:
                    record["warnings"].append(
                        f"{key}: duplicate ids: {', '.join(category_record['duplicate_ids'][:5])}"
                    )
    else:
        record["warnings"].append("root is neither a list nor an object")
    return record


def _find_references(path: Path, project_root: Path) -> list[str]:
    """Find which Python files appear to reference this table by name or category."""
    stem = path.stem
    references: list[str] = []
    # Simple substring search across app and tests.
    for py_path in sorted(project_root.rglob("*.py")):
        if py_path.is_dir():
            continue
        rel = str(py_path.relative_to(project_root))
        try:
            text = py_path.read_text(encoding="utf-8")
        except Exception:
            continue
        if stem in text or path.name in text:
            references.append(rel)
    return references


def build_inventory(project_root: Path | None = None) -> dict[str, Any]:
    """Scan project data files and build a structured inventory."""
    project_root = project_root or PROJECT_ROOT
    records: list[dict[str, Any]] = []
    warnings: list[str] = []

    for directory, role in SCAN_DIRS:
        if not directory.exists():
            warnings.append(f"directory missing: {directory}")
            continue
        for path in sorted(directory.glob("*.json")):
            record = _inspect_json(path, role)
            record["references"] = _find_references(path, project_root)
            records.append(record)

    for path, role in SCAN_FILES:
        if not path.exists():
            warnings.append(f"file missing: {path}")
            continue
        record = _inspect_json(path, role)
        record["references"] = _find_references(path, project_root)
        records.append(record)

    # Group by domain.
    by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        domain = record.get("domain", "other/unknown")
        by_domain[domain].append(record)

    return {
        "project_root": str(project_root),
        "total_files": len(records),
        "domains": sorted(by_domain.keys()),
        "by_domain": dict(by_domain),
        "warnings": warnings,
    }


def _format_category(category: dict[str, Any]) -> str:
    """Format a single category record for the text report."""
    fields = category.get("fields", [])
    parts = [
        f"  - {category['name']}",
        f"    entries: {category['entry_count']}",
    ]
    if category.get("is_text_list"):
        parts.append("    type: text list")
    if fields:
        parts.append(f"    fields: {', '.join(fields[:8])}{'...' if len(fields) > 8 else ''}")
    if category.get("id_present"):
        parts.append("    ids: present")
    if category.get("weighted"):
        parts.append("    weights: present")
    if category.get("duplicate_ids"):
        parts.append(f"    duplicate ids: {', '.join(category['duplicate_ids'][:5])}")
    return "\n".join(parts)


def format_report(inventory: dict[str, Any]) -> str:
    """Render a human-readable report from an inventory dict."""
    lines = [
        "Table Inventory Report",
        "======================",
        "",
        f"Project root: {inventory['project_root']}",
        f"Files scanned: {inventory['total_files']}",
        "",
        "Generated report files are NOT intended for manual editing.",
        "User-editable tables live under data/tables/.",
        "",
    ]
    for domain in inventory["domains"]:
        records = inventory["by_domain"].get(domain, [])
        lines.append(domain.upper().replace("/", " / "))
        lines.append("-" * len(domain))
        for record in records:
            lines.append(f"{record['file']}  [{record['role']}]")
            if record.get("generated_report"):
                lines.append("  NOTE: generated report; do not edit manually")
            if record.get("user_editable"):
                lines.append("  NOTE: user-editable")
            for category in record.get("categories", []):
                lines.append(_format_category(category))
            if record.get("warnings"):
                for warning in record["warnings"]:
                    lines.append(f"  WARNING: {warning}")
            if record.get("references"):
                lines.append(
                    f"  referenced by: {', '.join(record['references'][:3])}"
                )
            lines.append("")
        lines.append("")
    if inventory["warnings"]:
        lines.append("GLOBAL WARNINGS")
        lines.append("---------------")
        for warning in inventory["warnings"]:
            lines.append(f"- {warning}")
    return "\n".join(lines)


def write_inventory(
    project_root: Path | None = None,
    json_path: Path | None = None,
    txt_path: Path | None = None,
) -> dict[str, Any]:
    """Build the inventory and write both JSON and text reports."""
    inventory = build_inventory(project_root)
    json_path = json_path or DEFAULT_REPORT_JSON
    txt_path = txt_path or DEFAULT_REPORT_TXT
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(inventory, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    txt_path.parent.mkdir(parents=True, exist_ok=True)
    txt_path.write_text(format_report(inventory), encoding="utf-8")
    return inventory


def main() -> int:
    inventory = write_inventory()
    print(f"Wrote table inventory to {DEFAULT_REPORT_JSON}")
    print(f"Wrote table inventory report to {DEFAULT_REPORT_TXT}")
    print(f"Scanned {inventory['total_files']} files across {len(inventory['domains'])} domains")
    if inventory["warnings"]:
        print(f"Global warnings: {len(inventory['warnings'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
