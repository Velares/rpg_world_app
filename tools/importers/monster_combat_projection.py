from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __name__ == "__main__":
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from tools.importers.monster_manual_schema import PROJECT_ROOT


DEFAULT_STAGING_PREVIEW_PATH = (
    PROJECT_ROOT / "data" / "import_reports" / "monster_corrected_staging_preview.json"
)
DEFAULT_COMBAT_PROJECTION_JSON = (
    PROJECT_ROOT / "data" / "import_reports" / "monster_combat_projection.json"
)
DEFAULT_COMBAT_PROJECTION_REPORT = (
    PROJECT_ROOT / "data" / "import_reports" / "monster_combat_projection_report.txt"
)


RE_DICE = re.compile(r"^(\d+)d(\d+)(?:([+-])(\d+))?$")
RE_HD = re.compile(r"^(\d+)(?:-1|\+1)?(?:d\d+)?$")
RE_NUMBER = re.compile(r"^(\d+)$")
RE_MOVEMENT = re.compile(r"(\d+)(?:\s*ft\.?|\s*')")
RE_RANGE = re.compile(r"^(\d+)-(\d+)$")


def _now_utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_dice(value: str | None) -> dict[str, Any] | None:
    """Parse a single NdN or N-N damage expression."""
    if value is None:
        return None
    text = str(value).strip().lower().rstrip(".").lstrip("(")
    if text.endswith(")"):
        text = text[:-1]

    match = RE_DICE.match(text)
    if match:
        count = int(match.group(1))
        sides = int(match.group(2))
        modifier = 0
        if match.group(3):
            sign = 1 if match.group(3) == "+" else -1
            modifier = sign * int(match.group(4))
        return {
            "count": count,
            "sides": sides,
            "modifier": modifier,
            "average": count * (sides / 2) + modifier,
            "formula": text,
        }

    range_match = RE_RANGE.match(text)
    if range_match:
        low = int(range_match.group(1))
        high = int(range_match.group(2))
        # Common OSR mapping: 1-N maps to 1dN.
        if low == 1 and high >= 2:
            sides = high
            return {
                "count": 1,
                "sides": sides,
                "modifier": 0,
                "average": (1 + sides) / 2,
                "formula": text,
            }
        return {
            "count": 1,
            "sides": high - low + 1,
            "modifier": low - 1,
            "average": (low + high) / 2,
            "formula": text,
        }

    return None


def _parse_damage(value: str | None) -> dict[str, Any] | None:
    """Parse a damage expression, including multi-attack comma-separated lists."""
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"special", "by weapon", "none", "see below"}:
        return None

    parts = [part.strip() for part in text.split(",")]
    parsed_parts = []
    for part in parts:
        parsed = _parse_dice(part)
        if parsed:
            parsed_parts.append(parsed)

    if not parsed_parts:
        return None
    if len(parsed_parts) == 1:
        return parsed_parts[0]
    return {
        "multi_attack": True,
        "parts": parsed_parts,
        "average": sum(p["average"] for p in parsed_parts),
        "formula": text,
    }


def _parse_hd(value: str | None) -> dict[str, Any] | None:
    if value is None:
        return None
    text = str(value).strip().lower()

    # General "N+M" or "N-M" format.
    modifier_match = re.match(r"^(\d+)([+-])(\d+)$", text)
    if modifier_match:
        count = int(modifier_match.group(1))
        sign = 1 if modifier_match.group(2) == "+" else -1
        modifier = sign * int(modifier_match.group(3))
        return {
            "count": count,
            "modifier": modifier,
            "sides": 8,
            "average": count * 4.5 + modifier,
            "formula": text,
        }

    # Literal dice expression like "3d8".
    dice = _parse_dice(text)
    if dice:
        return {**dice, "formula": text}

    try:
        count = int(text)
    except ValueError:
        return None
    return {
        "count": count,
        "modifier": 0,
        "sides": 8,
        "average": count * 4.5,
        "formula": text,
    }


def _parse_attacks(value: str | None) -> dict[str, Any] | None:
    if value is None:
        return None
    text = str(value).strip()
    match = RE_NUMBER.match(text)
    if match:
        return {"count": int(match.group(1)), "formula": text}
    dice = _parse_dice(text)
    if dice:
        return {"count": dice["count"], "formula": text}
    return None


def _parse_movement(value: str | None) -> dict[str, Any] | None:
    if value is None:
        return None
    text = str(value).strip()
    matches = RE_MOVEMENT.findall(text)
    if matches:
        return {"primary": int(matches[0]), "all": [int(m) for m in matches], "formula": text}
    return None


def _parse_morale(value: str | None) -> dict[str, Any] | None:
    if value is None:
        return None
    text = str(value).strip()
    match = RE_NUMBER.match(text)
    if match:
        return {"value": int(match.group(1)), "formula": text}
    return None


def _parse_ac(value: str | None) -> dict[str, Any] | None:
    if value is None:
        return None
    text = str(value).strip()
    try:
        numeric = int(text)
    except ValueError:
        return None
    # Conservative inference: classic descending AC is common in LL/OSE;
    # mark unknown unless value clearly fits the 0-9 descending band.
    ac_type = "unknown"
    if -9 <= numeric <= 9:
        ac_type = "descending"
    return {"value": numeric, "type": ac_type, "formula": text}


def _derive_combat_tags(record: dict[str, Any]) -> tuple[list[str], list[str]]:
    tags: list[str] = []
    reasons: list[str] = []
    effective = record.get("effective", {})
    monster_type = effective.get("monster_type") or ""
    movement = effective.get("movement") or ""
    special_attacks = (effective.get("special_attacks") or "").lower()
    special_defenses = (effective.get("special_defenses") or "").lower()
    size = (effective.get("size") or "").lower()

    if "undead" in monster_type.lower():
        tags.append("undead")
        reasons.append("monster_type contains undead")
    if "construct" in monster_type.lower():
        tags.append("construct")
        reasons.append("monster_type contains construct")
    if "humanoid" in monster_type.lower():
        tags.append("humanoid")
        reasons.append("monster_type contains humanoid")
    if "animal" in monster_type.lower():
        tags.append("animal")
        reasons.append("monster_type contains animal")
    if "fly" in movement.lower() or "fly" in special_attacks or "fly" in special_defenses:
        tags.append("flying")
        reasons.append("movement or special abilities mention fly")
    if "poison" in special_attacks or "poison" in special_defenses:
        tags.append("poison")
        reasons.append("special abilities mention poison")
    if "paralysis" in special_attacks or "paralysis" in special_defenses:
        tags.append("paralysis")
        reasons.append("special abilities mention paralysis")
    if "spell" in special_attacks or "spell" in special_defenses:
        tags.append("spellcaster")
        reasons.append("special abilities mention spell")
    if "swim" in movement.lower() or "water" in special_attacks or "water" in special_defenses:
        tags.append("aquatic")
        reasons.append("movement or special abilities mention water/swim")
    if "giant" in monster_type.lower() or "giant" in size:
        tags.append("giant")
        reasons.append("monster_type or size contains giant")
    if "swarm" in monster_type.lower():
        tags.append("swarm")
        reasons.append("monster_type contains swarm")
    if "ranged" in special_attacks or "ranged" in special_defenses or "missile" in special_attacks:
        tags.append("ranged")
        reasons.append("special abilities mention ranged/missile")
    if "aerial" in monster_type.lower():
        tags.append("aerial")
        reasons.append("monster_type contains aerial")

    return tags, reasons


def _project_record(record: dict[str, Any]) -> dict[str, Any]:
    effective = record.get("effective", {})
    original = record.get("original", {})
    provenance = record.get("source_provenance", {})
    review = record.get("review_metadata", {})
    warnings: list[str] = []

    ac_model = _parse_ac(effective.get("armor_class"))
    hd_model = _parse_hd(effective.get("hit_dice"))
    attacks_model = _parse_attacks(effective.get("attacks"))
    damage_model = _parse_damage(effective.get("damage"))
    movement_model = _parse_movement(effective.get("movement"))
    morale_model = _parse_morale(effective.get("morale"))

    if ac_model is None and effective.get("armor_class") is not None:
        warnings.append("armor_class could not be parsed")
    if hd_model is None and effective.get("hit_dice") is not None:
        warnings.append("hit_dice could not be parsed")
    if attacks_model is None and effective.get("attacks") is not None:
        warnings.append("attacks could not be parsed")
    if damage_model is None and effective.get("damage") is not None:
        warnings.append("damage could not be parsed")

    combat_tags, tag_sources = _derive_combat_tags(record)

    required_fields = ["armor_class", "hit_dice", "attacks", "damage"]
    missing_combat_fields = [
        field for field in required_fields if effective.get(field) is None
    ]
    if missing_combat_fields:
        warnings.append(f"missing combat fields: {', '.join(missing_combat_fields)}")

    if missing_combat_fields:
        projection_status = "missing_combat_fields"
    elif ac_model is None or hd_model is None or attacks_model is None or damage_model is None:
        projection_status = "parse_warning"
    elif warnings:
        projection_status = "needs_review"
    else:
        projection_status = "ready"

    hit_points_formula = None
    if hd_model is not None:
        hit_points_formula = f"{hd_model['count']}d{hd_model['sides']}"
        if hd_model["modifier"] != 0:
            sign = "+" if hd_model["modifier"] > 0 else ""
            hit_points_formula = f"{hit_points_formula}{sign}{hd_model['modifier']}"

    return {
        "id": record.get("id", ""),
        "original_record_id": record.get("id", ""),
        "source_id": record.get("source_id", "unknown"),
        "source_title": record.get("source_title", "unknown"),
        "display_name": effective.get("display_name") or record.get("display_name"),
        "canonical_name": effective.get("canonical_name"),
        "armor_class_raw": effective.get("armor_class"),
        "armor_class_model": ac_model,
        "armor_class_type": ac_model.get("type") if ac_model else "unknown",
        "hit_dice_raw": effective.get("hit_dice"),
        "hit_dice_model": hd_model,
        "hit_points_formula": hit_points_formula,
        "movement_raw": effective.get("movement"),
        "movement_model": movement_model,
        "attacks_raw": effective.get("attacks"),
        "attacks_model": attacks_model,
        "damage_raw": effective.get("damage"),
        "damage_model": damage_model,
        "special_attacks": effective.get("special_attacks"),
        "special_defenses": effective.get("special_defenses"),
        "save_raw": effective.get("save"),
        "morale_raw": effective.get("morale"),
        "morale_model": morale_model,
        "xp_raw": effective.get("xp"),
        "alignment": effective.get("alignment"),
        "number_appearing": effective.get("number_appearing"),
        "treasure": effective.get("treasure"),
        "monster_type": effective.get("monster_type"),
        "size": effective.get("size"),
        "intelligence": effective.get("intelligence"),
        "level": effective.get("level"),
        "challenge": effective.get("challenge"),
        "combat_tags": combat_tags,
        "tag_sources": tag_sources,
        "projection_status": projection_status,
        "projection_warnings": warnings,
        "source_provenance": provenance,
        "review_metadata": review,
    }


def build_combat_projection(
    staging_path: Path | None = None,
) -> dict[str, Any]:
    """Load a staged corrected preview and produce a combat-ready projection."""
    staging_path = staging_path or DEFAULT_STAGING_PREVIEW_PATH
    if not staging_path.exists():
        raise FileNotFoundError(f"Staging preview not found at {staging_path}")
    try:
        data = json.loads(staging_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Staging preview at {staging_path} is not valid JSON: {exc}") from exc

    staged_records = data.get("staged_records", [])
    projections = [_project_record(record) for record in staged_records]

    status_counts: Counter[str] = Counter(p["projection_status"] for p in projections)
    source_counts: Counter[str] = Counter(p["source_id"] for p in projections)
    warnings_counts: Counter[str] = Counter()
    for projection in projections:
        for warning in projection["projection_warnings"]:
            warnings_counts[warning] += 1

    missing_field_counts: Counter[str] = Counter()
    for projection in projections:
        if projection["projection_status"] == "missing_combat_fields":
            for field in ["armor_class", "hit_dice", "attacks", "damage"]:
                if projection[f"{field}_raw"] is None:
                    missing_field_counts[field] += 1

    return {
        "schema_version": 1,
        "generated_at": _now_utc_iso(),
        "source_staging_preview": str(staging_path),
        "record_count": len(projections),
        "source_counts": dict(source_counts),
        "status_counts": dict(status_counts),
        "warning_counts": dict(warnings_counts),
        "missing_field_counts": dict(missing_field_counts),
        "projections": projections,
    }


def format_report(projection: dict[str, Any]) -> str:
    """Return a plain-text summary of the combat projection."""
    lines = [
        "Combat-Ready Monster Projection",
        "==============================",
        "",
        f"Generated at: {projection.get('generated_at', 'N/A')}",
        f"Source staging preview: {projection.get('source_staging_preview', 'N/A')}",
        f"Total staged records read: {projection.get('record_count', 0)}",
        "",
        "Source counts:",
    ]
    for source_id, count in sorted(projection.get("source_counts", {}).items()):
        lines.append(f"- {source_id}: {count}")

    status_counts = projection.get("status_counts", {})
    lines.extend([
        "",
        "Projection readiness counts:",
        f"- ready: {status_counts.get('ready', 0)}",
        f"- needs_review: {status_counts.get('needs_review', 0)}",
        f"- missing_combat_fields: {status_counts.get('missing_combat_fields', 0)}",
        f"- parse_warning: {status_counts.get('parse_warning', 0)}",
    ])

    warning_counts = projection.get("warning_counts", {})
    if warning_counts:
        lines.extend([
            "",
            "Top projection warnings:",
        ])
        for warning, count in Counter(warning_counts).most_common(10):
            lines.append(f"- {warning}: {count}")

    missing_field_counts = projection.get("missing_field_counts", {})
    if missing_field_counts:
        lines.extend([
            "",
            "Top missing combat fields:",
        ])
        for field, count in Counter(missing_field_counts).most_common():
            lines.append(f"- {field}: {count}")

    lines.extend([
        "",
        "WARNING: This is a non-live combat projection. No master catalog was created.",
        "Live catalog JSON was not modified. Source variants remain distinct. No records were merged.",
        "",
    ])

    ready_sample = [p for p in projection.get("projections", []) if p["projection_status"] == "ready"]
    if ready_sample:
        lines.append("Sample ready records:")
        for p in ready_sample[:5]:
            lines.append(
                f"- {p['id']}: {p['display_name']} [AC {p['armor_class_raw']}, HD {p['hit_dice_raw']}, "
                f"Atk {p['attacks_raw']}, Dmg {p['damage_raw']}]"
            )
    else:
        lines.append("No ready records found.")

    lines.append("")
    review_sample = [p for p in projection.get("projections", []) if p["projection_status"] != "ready"]
    if review_sample:
        lines.append("Sample records needing review:")
        for p in review_sample[:5]:
            warnings = "; ".join(p["projection_warnings"]) or "no warnings"
            lines.append(f"- {p['id']}: {p['display_name']} ({warnings})")
    else:
        lines.append("All records are ready.")

    return "\n".join(lines)


def write_combat_projection(
    projection: dict[str, Any],
    json_path: Path | None = None,
    report_path: Path | None = None,
) -> tuple[Path, Path]:
    """Write the JSON combat projection and its report."""
    json_path = json_path or DEFAULT_COMBAT_PROJECTION_JSON
    report_path = report_path or DEFAULT_COMBAT_PROJECTION_REPORT
    json_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    json_path.write_text(
        json.dumps(projection, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    report_path.write_text(format_report(projection), encoding="utf-8")
    return json_path, report_path


def main() -> None:
    projection = build_combat_projection()
    json_path, report_path = write_combat_projection(projection)
    print(f"Wrote combat projection to {json_path}")
    print(f"Wrote combat projection report to {report_path}")


if __name__ == "__main__":
    main()
