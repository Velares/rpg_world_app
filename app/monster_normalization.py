from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"
CONFIDENCE_MISSING = "missing"
PLACEHOLDER_VALUE = None
REVIEW_STATUS_MAPPED = "mapped"
REVIEW_STATUS_MAPPED_WITH_PLACEHOLDERS = "mapped_with_placeholders"
REVIEW_STATUS_NEEDS_REVIEW = "needs_review"

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
