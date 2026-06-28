from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.source_registry import (
    DEFAULT_SOURCE_REGISTRY_PATH,
    PROJECT_ROOT as SOURCE_REGISTRY_PROJECT_ROOT,
    SourceRegistryEntryStatus,
    get_source_registry_entry_status,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SOURCE_REGISTRY_PATH = DEFAULT_SOURCE_REGISTRY_PATH
MONSTER_MANUAL_SOURCE_ID = "mandbmaster_combined_monster_manual"
MONSTER_APPENDIX_SOURCE_ID = MONSTER_MANUAL_SOURCE_ID
ADD_BESTIARY_SOURCE_ID = "adventures_dark_and_deep_bestiary"
MEGADUNGEON_MONSTER_SOURCE_ID = "megadungeon_monster_manual"
DEFAULT_MONSTER_MANUAL_PDF = (
    PROJECT_ROOT / "data" / "import_sources" / "mandbmaster.pdf"
)
DEFAULT_MEGADUNGEON_MONSTER_PDF = (
    PROJECT_ROOT / "data" / "import_sources" / "MegadungeonMonsterManual.pdf"
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


@dataclass
class ResolvedMonsterSource:
    source_id: str | None
    source_title: str | None
    source_status: str | None
    source_path: Path
    path_display: str
    exists: bool
    used_path_override: bool
    registry_status: SourceRegistryEntryStatus | None

    @property
    def is_registered(self) -> bool:
        return self.registry_status is not None


def resolve_registered_monster_source(
    *,
    default_source_id: str,
    override_path: Path | None = None,
    source_id: str | None = None,
    allow_inactive_source: bool = False,
    registry_path: Path = SOURCE_REGISTRY_PATH,
    project_root: Path = SOURCE_REGISTRY_PROJECT_ROOT,
) -> ResolvedMonsterSource:
    effective_source_id = source_id or default_source_id
    registry_status = get_source_registry_entry_status(
        effective_source_id,
        path=registry_path,
        project_root=project_root,
    )
    if registry_status is not None and registry_status.domain != "monsters":
        raise ValueError(
            f"Source '{effective_source_id}' is registered under domain "
            f"'{registry_status.domain}', not 'monsters'."
        )
    if (
        registry_status is not None
        and registry_status.status in {"inactive", "comparison_only", "deprecated"}
        and not allow_inactive_source
    ):
        raise ValueError(
            f"Source '{effective_source_id}' is marked {registry_status.status} in the source registry. "
            "Pass --allow-inactive-source only when you deliberately want to import from it."
        )

    source_path = override_path or (
        registry_status.resolved_path if registry_status is not None else None
    )
    if source_path is None:
        raise ValueError(
            f"No source path could be resolved for monster source '{effective_source_id}'."
        )
    exists = source_path.exists()
    if not exists:
        if registry_status is not None:
            if override_path is not None:
                raise FileNotFoundError(
                    "Registered monster source override not found: "
                    f"{source_path}\nRegistered source: {registry_status.title} "
                    f"[{registry_status.source_id}]"
                )
            raise FileNotFoundError(
                "Registered monster source not found: "
                f"{registry_status.title} [{registry_status.source_id}] at "
                f"{registry_status.expected_path}"
            )
        raise FileNotFoundError(f"Monster source file not found: {source_path}")

    return ResolvedMonsterSource(
        source_id=registry_status.source_id if registry_status is not None else effective_source_id,
        source_title=registry_status.title if registry_status is not None else source_path.stem,
        source_status=registry_status.status if registry_status is not None else "unregistered_path",
        source_path=source_path,
        path_display=(
            registry_status.expected_path if registry_status is not None and not override_path else str(source_path)
        ),
        exists=exists,
        used_path_override=override_path is not None,
        registry_status=registry_status,
    )
