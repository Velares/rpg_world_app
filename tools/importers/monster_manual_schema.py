from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MONSTER_MANUAL_PDF = (
    PROJECT_ROOT / "data" / "import_sources" / "mandbmaster.pdf"
)
DEFAULT_MONSTER_CATALOG_JSON = (
    PROJECT_ROOT / "data" / "catalogs" / "monsters" / "monster_catalog.json"
)
DEFAULT_MONSTER_IMPORT_REPORT = (
    PROJECT_ROOT / "data" / "import_reports" / "monster_manual_import_report.txt"
)

BOOK_ENTRY_RANGES: tuple[tuple[int, int, int], ...] = (
    (1, 2, 115),
    (2, 124, 220),
)

EXPECTED_REQUIRED_FIELDS: tuple[str, ...] = (
    "id",
    "name",
    "source.book",
    "source.actual_page_start",
    "source.actual_page_end",
    "raw_text",
)

EXPECTED_COMMON_FIELDS: tuple[str, ...] = (
    "stat_block.size",
    "stat_block.move",
    "stat_block.armor_class",
    "stat_block.hit_dice",
    "stat_block.rarity",
    "stat_block.intelligence",
    "stat_block.alignment",
    "stat_block.level_xp.raw",
)

STAT_LABELS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("size", ("SIZE",)),
    ("move", ("MOVE",)),
    ("armor_class", ("ARMOR CLASS",)),
    ("hit_dice", ("HIT DICE",)),
    ("attacks", ("ATTACKS",)),
    ("damage", ("DAMAGE",)),
    ("special_attacks", ("SPECIAL ATTACKS",)),
    ("special_defenses", ("SPECIAL DEFENSES",)),
    ("magic_resistance", ("MAGIC RESISTANCE",)),
    ("rarity", ("RARITY",)),
    ("number_encountered", ("NO. ENCOUNTERED",)),
    ("lair_probability", ("LAIR PROBABILITY", "LAIR PROBABLITY")),
    ("treasure", ("TREASURE",)),
    ("intelligence", ("INTELLIGENCE",)),
    ("alignment", ("ALIGNMENT",)),
    ("level_xp", ("LEVEL/X.P.", "LEVEL/X.P", "LEVEL / X.P.", "LEVEL / X.P")),
)

SECTION_LABELS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("general_information", ("GENERAL INFORMATION",)),
    ("languages", ("LANGUAGES",)),
    ("physical_description", ("PHYSICAL DESCRIPTION",)),
    ("variants", ("VARIANTS",)),
)

LABEL_TO_KEY = {
    label: key
    for key, labels in (*STAT_LABELS, *SECTION_LABELS)
    for label in labels
}
