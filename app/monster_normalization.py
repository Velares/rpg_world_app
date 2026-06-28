from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re
from typing import Any


CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"
CONFIDENCE_MISSING = "missing"
PLACEHOLDER_VALUE = None
REVIEW_STATUS_MAPPED = "mapped"
REVIEW_STATUS_MAPPED_WITH_PLACEHOLDERS = "mapped_with_placeholders"
REVIEW_STATUS_NEEDS_REVIEW = "needs_review"
MANDMASTER_SOURCE_ID = "mandbmaster_combined_monster_manual"
MANDMASTER_SOURCE_TITLE = "MandBmaster Combined Monster Manual"

SECTION_HEADINGS = (
    "General information",
    "Languages",
    "Physical description",
    "Variants",
)
STAT_LABEL_LINE_PATTERN = re.compile(r"^[A-Z][A-Z /.'()-]+:\s*", re.MULTILINE)

NORMALIZED_MONSTER_OPTIONAL_FIELDS: tuple[str, ...] = (
    "armor_class",
    "hit_dice",
    "hit_points",
    "movement",
    "attacks",
    "damage",
    "special_attacks",
    "special_defenses",
    "save",
    "morale",
    "alignment",
    "intelligence",
    "size",
    "monster_type",
    "category",
    "environment",
    "terrain",
    "region",
    "number_appearing",
    "treasure",
    "xp",
    "challenge",
    "level",
    "description",
)


@dataclass
class NormalizedMonster:
    id: str
    canonical_name: str
    display_name: str
    aliases: list[str] = field(default_factory=list)
    source_id: str = ""
    source_title: str = ""
    source_file: str = ""
    source_page_start: int | None = None
    source_page_end: int | None = None
    source_entry_id: str | None = None
    source_slug: str | None = None
    armor_class: str | None = PLACEHOLDER_VALUE
    hit_dice: str | None = PLACEHOLDER_VALUE
    hit_points: str | None = PLACEHOLDER_VALUE
    movement: str | None = PLACEHOLDER_VALUE
    attacks: str | None = PLACEHOLDER_VALUE
    damage: str | None = PLACEHOLDER_VALUE
    special_attacks: str | None = PLACEHOLDER_VALUE
    special_defenses: str | None = PLACEHOLDER_VALUE
    save: str | None = PLACEHOLDER_VALUE
    morale: str | None = PLACEHOLDER_VALUE
    alignment: str | None = PLACEHOLDER_VALUE
    intelligence: str | None = PLACEHOLDER_VALUE
    size: str | None = PLACEHOLDER_VALUE
    monster_type: str | None = PLACEHOLDER_VALUE
    category: str | None = PLACEHOLDER_VALUE
    environment: str | None = PLACEHOLDER_VALUE
    terrain: str | None = PLACEHOLDER_VALUE
    region: str | None = PLACEHOLDER_VALUE
    number_appearing: str | None = PLACEHOLDER_VALUE
    treasure: str | None = PLACEHOLDER_VALUE
    xp: str | None = PLACEHOLDER_VALUE
    challenge: str | None = PLACEHOLDER_VALUE
    level: str | None = PLACEHOLDER_VALUE
    description: str | None = PLACEHOLDER_VALUE
    raw_stat_block: str = ""
    raw_text: str = ""
    normalized_fields: list[str] = field(default_factory=list)
    missing_fields: list[str] = field(default_factory=list)
    placeholder_fields: list[str] = field(default_factory=list)
    mapping_confidence: dict[str, str] = field(default_factory=dict)
    review_status: str = REVIEW_STATUS_MAPPED
    review_notes: list[str] = field(default_factory=list)
    user_corrections: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def map_normalized_field(
    monster: NormalizedMonster,
    field_name: str,
    value: Any,
    confidence: str,
    *,
    review_note: str | None = None,
) -> None:
    clean_value = _clean_text(value)
    if clean_value is None:
        setattr(monster, field_name, PLACEHOLDER_VALUE)
        if field_name not in monster.missing_fields:
            monster.missing_fields.append(field_name)
        if field_name not in monster.placeholder_fields:
            monster.placeholder_fields.append(field_name)
        monster.mapping_confidence[field_name] = CONFIDENCE_MISSING
    else:
        setattr(monster, field_name, clean_value)
        if field_name not in monster.normalized_fields:
            monster.normalized_fields.append(field_name)
        monster.mapping_confidence[field_name] = confidence
    if review_note and review_note not in monster.review_notes:
        monster.review_notes.append(review_note)


def map_inferred_field(
    monster: NormalizedMonster,
    field_name: str,
    value: Any,
    *,
    review_note: str,
) -> None:
    map_normalized_field(
        monster,
        field_name,
        value,
        CONFIDENCE_LOW,
        review_note=review_note,
    )


def finalize_normalized_monster(monster: NormalizedMonster) -> NormalizedMonster:
    for field_name in NORMALIZED_MONSTER_OPTIONAL_FIELDS:
        if getattr(monster, field_name) in (None, ""):
            setattr(monster, field_name, PLACEHOLDER_VALUE)
            if field_name not in monster.missing_fields:
                monster.missing_fields.append(field_name)
            if field_name not in monster.placeholder_fields:
                monster.placeholder_fields.append(field_name)
            monster.mapping_confidence.setdefault(field_name, CONFIDENCE_MISSING)

    monster.normalized_fields = sorted(set(monster.normalized_fields))
    monster.missing_fields = sorted(set(monster.missing_fields))
    monster.placeholder_fields = sorted(set(monster.placeholder_fields))
    monster.review_notes = list(dict.fromkeys(monster.review_notes))

    if any(value == CONFIDENCE_LOW for value in monster.mapping_confidence.values()) or monster.review_notes:
        monster.review_status = REVIEW_STATUS_NEEDS_REVIEW
    elif monster.placeholder_fields:
        monster.review_status = REVIEW_STATUS_MAPPED_WITH_PLACEHOLDERS
    else:
        monster.review_status = REVIEW_STATUS_MAPPED
    return monster


def _clean_damage_field(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        parts = [_clean_text(item) for item in value]
        clean_parts = [part for part in parts if part]
        return ", ".join(clean_parts) or None
    return _clean_text(value)


def _clean_level_field(level_xp: Any, field_name: str) -> str | None:
    if not isinstance(level_xp, dict):
        return None
    value = level_xp.get(field_name)
    if value is None:
        return None
    return _clean_text(value)


def _build_mandbmaster_raw_stat_block(raw_text: str) -> str:
    clean_text = _clean_text(raw_text) or ""
    if not clean_text:
        return ""
    lines = clean_text.splitlines()
    collected: list[str] = []
    for line in lines[1:]:
        stripped = line.strip()
        if not stripped:
            continue
        normalized = stripped.casefold().replace(" :", ":")
        if any(normalized.startswith(f"{heading.casefold()}:") for heading in SECTION_HEADINGS):
            break
        collected.append(stripped)
    return "\n".join(collected)


def map_mandbmaster_core_record_to_normalized(record: dict[str, Any]) -> dict[str, Any]:
    display_name = _clean_text(record.get("name")) or _clean_text(record.get("sort_name")) or "Unknown Monster"
    sort_name = _clean_text(record.get("sort_name")) or display_name.upper()
    source = record.get("source") if isinstance(record.get("source"), dict) else {}
    stat_block = record.get("stat_block") if isinstance(record.get("stat_block"), dict) else {}
    sections = record.get("sections") if isinstance(record.get("sections"), dict) else {}
    level_xp = stat_block.get("level_xp") if isinstance(stat_block.get("level_xp"), dict) else {}
    raw_text = _clean_text(record.get("raw_text")) or ""

    normalized = NormalizedMonster(
        id=f"normalized.{MANDMASTER_SOURCE_ID}.{_clean_text(record.get('id')) or ''}".rstrip("."),
        canonical_name=display_name,
        display_name=display_name,
        aliases=[],
        source_id=MANDMASTER_SOURCE_ID,
        source_title=MANDMASTER_SOURCE_TITLE,
        source_file=_clean_text(source.get("file")) or "mandbmaster.pdf",
        source_page_start=source.get("actual_page_start") if isinstance(source.get("actual_page_start"), int) else None,
        source_page_end=source.get("actual_page_end") if isinstance(source.get("actual_page_end"), int) else None,
        source_entry_id=_clean_text(record.get("id")),
        source_slug=_clean_text(record.get("id")),
        raw_stat_block=_build_mandbmaster_raw_stat_block(raw_text),
        raw_text=raw_text,
    )
    normalized.normalized_fields.extend(
        [
            "id",
            "canonical_name",
            "display_name",
            "source_id",
            "source_title",
            "source_file",
            "source_page_start",
            "source_page_end",
            "source_entry_id",
            "source_slug",
            "raw_stat_block",
            "raw_text",
        ]
    )
    normalized.mapping_confidence.update(
        {
            "id": CONFIDENCE_MEDIUM,
            "canonical_name": CONFIDENCE_HIGH,
            "display_name": CONFIDENCE_HIGH,
            "source_id": CONFIDENCE_HIGH,
            "source_title": CONFIDENCE_HIGH,
            "source_file": CONFIDENCE_HIGH,
            "source_page_start": CONFIDENCE_HIGH,
            "source_page_end": CONFIDENCE_HIGH,
            "source_entry_id": CONFIDENCE_HIGH,
            "source_slug": CONFIDENCE_HIGH,
            "raw_stat_block": CONFIDENCE_HIGH,
            "raw_text": CONFIDENCE_HIGH,
        }
    )

    map_normalized_field(normalized, "armor_class", stat_block.get("armor_class"), CONFIDENCE_HIGH)
    map_normalized_field(normalized, "hit_dice", stat_block.get("hit_dice"), CONFIDENCE_HIGH)
    map_normalized_field(normalized, "movement", stat_block.get("move"), CONFIDENCE_MEDIUM)
    map_normalized_field(normalized, "attacks", stat_block.get("attacks"), CONFIDENCE_HIGH)
    map_normalized_field(normalized, "damage", _clean_damage_field(stat_block.get("damage")), CONFIDENCE_MEDIUM)
    map_normalized_field(normalized, "special_attacks", stat_block.get("special_attacks"), CONFIDENCE_HIGH)
    map_normalized_field(normalized, "special_defenses", stat_block.get("special_defenses"), CONFIDENCE_HIGH)
    map_normalized_field(normalized, "treasure", stat_block.get("treasure"), CONFIDENCE_HIGH)
    map_normalized_field(normalized, "intelligence", stat_block.get("intelligence"), CONFIDENCE_HIGH)
    map_normalized_field(normalized, "alignment", stat_block.get("alignment"), CONFIDENCE_HIGH)
    map_normalized_field(normalized, "size", stat_block.get("size"), CONFIDENCE_HIGH)
    map_normalized_field(normalized, "number_appearing", stat_block.get("number_encountered"), CONFIDENCE_MEDIUM)
    map_normalized_field(normalized, "xp", _clean_level_field(level_xp, "raw"), CONFIDENCE_MEDIUM)
    map_normalized_field(normalized, "level", _clean_level_field(level_xp, "level"), CONFIDENCE_MEDIUM)
    map_normalized_field(normalized, "description", sections.get("general_information"), CONFIDENCE_MEDIUM)

    return finalize_normalized_monster(normalized).to_dict()
