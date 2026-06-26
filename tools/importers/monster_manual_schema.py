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
DEFAULT_MONSTER_APPENDIX_CATALOG_JSON = (
    PROJECT_ROOT / "data" / "catalogs" / "monsters" / "monster_appendix_catalog.json"
)
DEFAULT_MONSTER_APPENDIX_IMPORT_REPORT = (
    PROJECT_ROOT / "data" / "import_reports" / "monster_appendix_import_report.txt"
)
DEFAULT_MONSTER_APPENDIX_UNMATCHED_REVIEW_REPORT = (
    PROJECT_ROOT / "data" / "import_reports" / "monster_appendix_unmatched_review.txt"
)
DEFAULT_MONSTER_JSON_IMPORT_REPORT = (
    PROJECT_ROOT / "data" / "import_reports" / "monster_json_import_report.txt"
)
DEFAULT_MONSTER_JSON_IMPORT_PREVIEW = (
    PROJECT_ROOT / "data" / "import_reports" / "monster_json_import_preview.json"
)
DEFAULT_ADD_BESTIARY_PDF = (
    PROJECT_ROOT
    / "data"
    / "import_sources"
    / "adventures_dark_and_deep_bestiary"
    / "Adventures Dark and Deep Bestiaryforingestion.pdf"
)
DEFAULT_ADD_BESTIARY_PACK_DIR = (
    PROJECT_ROOT
    / "data"
    / "content_packs"
    / "imported"
    / "adventures_dark_and_deep_bestiary"
)
DEFAULT_ADD_BESTIARY_PACK_JSON = DEFAULT_ADD_BESTIARY_PACK_DIR / "pack.json"
DEFAULT_ADD_BESTIARY_MONSTERS_JSON = DEFAULT_ADD_BESTIARY_PACK_DIR / "monsters.json"
DEFAULT_ADD_BESTIARY_IMPORT_WORK_DIR = (
    PROJECT_ROOT / "import_work" / "adventures_dark_and_deep_bestiary"
)
DEFAULT_ADD_BESTIARY_RAW_PAGES_DIR = DEFAULT_ADD_BESTIARY_IMPORT_WORK_DIR / "raw_pages"
DEFAULT_ADD_BESTIARY_IMPORT_REPORT = (
    DEFAULT_ADD_BESTIARY_IMPORT_WORK_DIR / "import_report.txt"
)
ADD_BESTIARY_ENTRY_PAGE_RANGE = (4, 438)

BOOK_ENTRY_RANGES: tuple[tuple[int, int, int], ...] = (
    (1, 2, 115),
    (2, 124, 220),
)

BOOK_APPENDIX_RANGES: tuple[tuple[int, int, int], ...] = (
    (1, 117, 122),
    (2, 221, 229),
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
    ("rarity", ("RARITY", "FREQUENCY")),
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
