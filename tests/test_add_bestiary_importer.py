from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.monster_catalog import (
    find_same_name_different_source_records,
    get_monsters_sorted_by_name,
)
from tools.importers.add_bestiary_importer import (
    AddBestiaryEntry,
    ImportPage,
    build_import_from_pages,
    classify_entry,
    is_add_bestiary_entry_page,
    validate_imported_monster_pack,
)
from tools.importers.monster_manual_schema import ResolvedMonsterSource


def simple_entry_text(name: str = "Aerian") -> str:
    return f"""{name}
Number: 1-4
Morale: 7
Hit Dice: 4
Armor Class: 5
Move: 60'/min., 360'/min. (flying - average)
Magic Resistance: +1
No. of Attacks: 2
Damage: 1d6/1d6
Defenses: None
Attacks: Talons
Weaknesses: None
Size: Medium
Intelligence: Average
Alignment: Neutral
Treasure Type: C
Treasure Value: 100 gp
Magical Treasure: None
X.P. Value: 175
General: A winged hunter of the high ruins.
Combat: It dives quickly and retreats if bloodied.
Appearance: Feathered scales and glassy eyes.
"""


def sample_source_info(path: str = "sample_add.pdf") -> ResolvedMonsterSource:
    return ResolvedMonsterSource(
        source_id="test.monsters.add",
        source_title="Sample ADD Source",
        source_status="active",
        source_path=Path(path),
        path_display=path,
        exists=True,
        used_path_override=True,
        registry_status=None,
    )


class AddBestiaryImporterTests(unittest.TestCase):
    def test_simple_single_entry_parses_and_preserves_required_fields(self):
        entry = AddBestiaryEntry(
            heading="Aerian",
            actual_page_start=4,
            actual_page_end=4,
            printed_page=12,
            raw_text=simple_entry_text(),
        )
        monster, rejected, _ = classify_entry(entry)
        self.assertIsNone(rejected)
        assert monster is not None
        self.assertEqual(monster["id"], "add_bestiary.monster.aerian")
        self.assertEqual(monster["source_page_actual"], 4)
        self.assertEqual(monster["source_page_printed"], 12)
        self.assertEqual(monster["stat_block"]["Move"], "60'/min., 360'/min. (flying - average)")
        self.assertEqual(monster["stat_block"]["X.P. Value"], "175")
        self.assertIn("General", monster["sections"])

    def test_multi_variant_block_is_rejected_for_milestone_one(self):
        entry = AddBestiaryEntry(
            heading="Animated Furniture",
            actual_page_start=10,
            actual_page_end=10,
            printed_page=None,
            raw_text="""Animated Furniture
Number: 1
Morale: 10
Hit Dice: 2
Armor Class: 8
Move: 30'
Magic Resistance: None
No. of Attacks: 1
Damage: 1d4
Size: Small
Intelligence: Non-
Alignment: Neutral
X.P. Value: 35
General: Animated chairs and stools attack intruders.
Number: 1
Morale: 11
Hit Dice: 5
Armor Class: 4
Move: 20'
Magic Resistance: None
No. of Attacks: 2
Damage: 1d8/1d8
Size: Large
Intelligence: Non-
Alignment: Neutral
X.P. Value: 175
Appearance: Tables and wardrobes lurch under bad enchantments.
""",
        )
        monster, rejected, _ = classify_entry(entry)
        self.assertIsNone(monster)
        self.assertIsNotNone(rejected)
        self.assertEqual(rejected.reason, "multi_variant_stat_block_not_supported_yet")

    def test_entry_page_range_skips_frontmatter_and_appendices(self):
        self.assertFalse(is_add_bestiary_entry_page(1))
        self.assertFalse(is_add_bestiary_entry_page(3))
        self.assertTrue(is_add_bestiary_entry_page(4))
        self.assertTrue(is_add_bestiary_entry_page(438))
        self.assertFalse(is_add_bestiary_entry_page(439))
        self.assertFalse(is_add_bestiary_entry_page(448))

    def test_build_import_from_pages_records_rejections_and_missing_pages(self):
        pages = [
            ImportPage(actual_page=4, book=1, text=simple_entry_text("Aerian")),
            ImportPage(actual_page=5, book=1, text="Appendix heading only"),
            ImportPage(
                actual_page=6,
                book=1,
                text="""Ant, Giant
Number: 2-12
Morale: 8
Hit Dice: 2
Armor Class: 7
Move: 90'
Magic Resistance: None
No. of Attacks: 1
Damage: 1d6
Size: Small
Intelligence: Animal
Alignment: Neutral
X.P. Value: 45
General: Worker ants defend the colony.
Number: 1-4
Morale: 9
Hit Dice: 4
Armor Class: 4
Move: 120'
Magic Resistance: None
No. of Attacks: 1
Damage: 2d4
Size: Medium
Intelligence: Animal
Alignment: Neutral
X.P. Value: 125
Appearance: Soldiers carry oversized mandibles.
""",
            ),
        ]
        result = build_import_from_pages(
            pages,
            source_info=sample_source_info(),
            existing_catalog_path=Path(__file__).resolve().parents[1] / "data" / "catalogs" / "monsters" / "monster_catalog.json",
        )
        self.assertEqual(result.accepted_count, 1)
        self.assertEqual(result.partial_count, 1)
        self.assertTrue(any(entry.heading == "Ant, Giant" for entry in result.rejected_entries))
        self.assertIn(5, result.pages_without_records)

    def test_validation_allows_distinct_same_name_different_source_records(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pack_json = root / "pack.json"
            monsters_json = root / "monsters.json"
            pack_json.write_text(
                json.dumps(
                    {
                        "id": "imported.adventures_dark_and_deep_bestiary",
                        "name": "Adventures Dark and Deep Bestiary Import",
                        "enabled": True,
                    }
                ),
                encoding="utf-8",
            )
            monsters_json.write_text(
                json.dumps(
                    {
                        "monsters": [
                            {
                                "id": "add_bestiary.monster.skeleton",
                                "name": "Skeleton",
                                "source": {"name": "ADD Bestiary"},
                                "source_page_actual": 77,
                                "stat_block": {field: "x" for field in (
                                    "Number",
                                    "Morale",
                                    "Hit Dice",
                                    "Armor Class",
                                    "Move",
                                    "Magic Resistance",
                                    "No. of Attacks",
                                    "Damage",
                                    "Size",
                                    "Intelligence",
                                    "Alignment",
                                    "X.P. Value",
                                )},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            errors = validate_imported_monster_pack(pack_json, monsters_json)
        self.assertEqual(errors, [])

    def test_combined_monster_sorting_is_alphabetical_and_keeps_sources_distinct(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            core_catalog = root / "monster_catalog.json"
            content_packs_root = root / "content_packs" / "imported" / "adventures_dark_and_deep_bestiary"
            content_packs_root.mkdir(parents=True, exist_ok=True)
            core_catalog.write_text(
                json.dumps(
                    {
                        "monster_count": 2,
                        "monsters": [
                            {"id": "manual.monster.skeleton", "name": "Skeleton", "sort_name": "SKELETON", "source": {"file": "manual.pdf"}},
                            {"id": "manual.monster.zombie", "name": "Zombie", "sort_name": "ZOMBIE", "source": {"file": "manual.pdf"}},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (content_packs_root / "pack.json").write_text(
                json.dumps(
                    {
                        "id": "imported.adventures_dark_and_deep_bestiary",
                        "name": "Adventures Dark and Deep Bestiary Import",
                        "enabled": True,
                    }
                ),
                encoding="utf-8",
            )
            (content_packs_root / "monsters.json").write_text(
                json.dumps(
                    {
                        "monsters": [
                            {"id": "add_bestiary.monster.aerian", "name": "Aerian", "sort_name": "AERIAN", "source_pack": "imported.adventures_dark_and_deep_bestiary"},
                            {"id": "add_bestiary.monster.skeleton", "name": "Skeleton", "sort_name": "SKELETON", "source_pack": "imported.adventures_dark_and_deep_bestiary"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            monsters = get_monsters_sorted_by_name(
                catalog_path=core_catalog,
                content_packs_root=root / "content_packs" / "imported",
                include_imported=True,
            )
            warnings = find_same_name_different_source_records(monsters)
        self.assertEqual(
            [monster["name"] for monster in monsters],
            ["Aerian", "Skeleton", "Skeleton", "Zombie"],
        )
        self.assertEqual(
            {monster["id"] for monster in monsters if monster["name"] == "Skeleton"},
            {"manual.monster.skeleton", "add_bestiary.monster.skeleton"},
        )
        self.assertTrue(any("Skeleton" in warning for warning in warnings))


if __name__ == "__main__":
    unittest.main()
