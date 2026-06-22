from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.importers.monster_manual_importer import (
    ImportPage,
    build_catalog_from_pages,
    import_monster_manual,
    parse_monster_entry,
    split_entries_from_pages,
)


class MonsterManualImporterTests(unittest.TestCase):
    def test_normal_stat_block_parses_expected_fields(self):
        entry = split_entries_from_pages(
            [
                ImportPage(
                    actual_page=2,
                    book=1,
                    text="""ACANOPYORNIS
SIZE: Large 9 ft. tall
MOVE: 180 ft.
ARMOR CLASS: 8
HIT DICE: 3
ATTACKS: 3
DAMAGE: 1-4, 1-4, 1-2
SPECIAL ATTACKS: None
SPECIAL DEFENSES: None
MAGIC RESISTANCE: None
RARITY: Uncommon
NO. ENCOUNTERED: 9-16
LAIR PROBABILITY: 10%
TREASURE: None
INTELLIGENCE: Animal
ALIGNMENT: Neutral
LEVEL/X.P.: 2 / 65 + 2/hp

GENERAL INFORMATION:
A giant forest bird that lashes out with claws and beak.
PHYSICAL DESCRIPTION:
Long-necked and thick-feathered, with a bony crest.
""",
                )
            ]
        )[0]
        monster, warnings = parse_monster_entry(entry, "sample.pdf")
        self.assertEqual(warnings, [])
        self.assertEqual(monster["id"], "acanopyornis")
        self.assertEqual(monster["stat_block"]["size"], "Large")
        self.assertEqual(monster["stat_block"]["size_detail"], "9 ft. tall")
        self.assertEqual(monster["stat_block"]["damage"], ["1-4", "1-4", "1-2"])
        self.assertEqual(monster["stat_block"]["level_xp"]["level"], 2)
        self.assertEqual(monster["sections"]["general_information"], "A giant forest bird that lashes out with claws and beak.")
        self.assertIn("animal_intelligence", monster["tags"])

    def test_entry_detection_handles_prior_monster_text_and_multi_page_continuation(self):
        pages = [
            ImportPage(
                actual_page=15,
                book=1,
                text="""ABOLETH
SIZE: Huge
MOVE: 90 ft.
ARMOR CLASS: 4
HIT DICE: 8
ATTACKS: 4
DAMAGE: 1-6, 1-6, 1-6, 1-6
SPECIAL ATTACKS: Slime
SPECIAL DEFENSES: None
MAGIC RESISTANCE: 15%
RARITY: Rare
NO. ENCOUNTERED: 1-2
LAIR PROBABILITY: 20%
TREASURE: F
INTELLIGENCE: Very
ALIGNMENT: Lawful evil
LEVEL/X.P.: 5 / 425 + 8/hp

The creature lurks in deep water.
ADDLEVETCH
SIZE: Medium
MOVE: 120 ft.
ARMOR CLASS: 6
HIT DICE: 4+1
ATTACKS: Special
DAMAGE: Special
SPECIAL ATTACKS: Hallucinatory spores
SPECIAL DEFENSES: None
MAGIC RESISTANCE: None
RARITY: Rare
NO. ENCOUNTERED: 1-4
LAIR PROBABILITY: 15%
TREASURE: D
INTELLIGENCE: Low
ALIGNMENT: Chaotic neutral
LEVEL/X.P.: 3 / 140 +""",
            ),
            ImportPage(
                actual_page=16,
                book=1,
                text="""4/hp

GENERAL INFORMATION:
Its spoor twists the senses of nearby travelers.
VARIANTS:
Some infest ruined orchards instead of caves.
""",
            ),
        ]
        entries = split_entries_from_pages(pages)
        self.assertEqual([entry.heading for entry in entries], ["ABOLETH", "ADDLEVETCH"])
        addlevetch = entries[1]
        monster, _ = parse_monster_entry(addlevetch, "sample.pdf")
        self.assertEqual(monster["source"]["actual_page_start"], 15)
        self.assertEqual(monster["source"]["actual_page_end"], 16)
        self.assertEqual(monster["stat_block"]["level_xp"]["raw"], "3 / 140 + 4/hp")
        self.assertIn("hallucinatory spores", monster["raw_text"].lower())
        self.assertEqual(monster["sections"]["variants"], "Some infest ruined orchards instead of caves.")

    def test_typo_multiline_level_and_complex_attack_damage_are_tolerated(self):
        entry = split_entries_from_pages(
            [
                ImportPage(
                    actual_page=40,
                    book=1,
                    text="""BLOOD WORM
SIZE: Large
MOVE: 60 ft., burrow 30 ft.
ARMOR CLASS: 2 (6)
HIT DICE: 12 + 2-7
ATTACKS: 12-14 + bite
DAMAGE: 1-4 (x8), bite 2-8, Special
SPECIAL ATTACKS: Drain blood
SPECIAL DEFENSES: None
MAGIC RESISTANCE: None
RARITY: Rare
NO. ENCOUNTERED: 1-3
LAIR PROBABLITY: 25%
TREASURE: Incidental coins clinging to old nests
 and shards of armor from prior victims
INTELLIGENCE: Non-
ALIGNMENT: Neutral
LEVEL/X.P.: 6 /
650 + 10/hp

GENERAL INFORMATION:
An immense parasitic worm that erupts from soaked earth.
LANGUAGES:
None
""",
                )
            ]
        )[0]
        monster, warnings = parse_monster_entry(entry, "sample.pdf")
        self.assertEqual(warnings, [])
        self.assertEqual(monster["stat_block"]["armor_class"], "2 (6)")
        self.assertEqual(monster["stat_block"]["hit_dice"], "12 + 2-7")
        self.assertEqual(monster["stat_block"]["attacks"], "12-14 + bite")
        self.assertEqual(
            monster["stat_block"]["damage"],
            ["1-4 (x8)", "bite 2-8", "Special"],
        )
        self.assertEqual(monster["stat_block"]["lair_probability"], "25%")
        self.assertEqual(
            monster["stat_block"]["treasure"],
            "Incidental coins clinging to old nests and shards of armor from prior victims",
        )
        self.assertEqual(monster["stat_block"]["level_xp"]["xp_base"], 650)
        self.assertEqual(monster["sections"]["languages"], "None")

    def test_catalog_builder_reports_missing_fields_and_first_last_by_book(self):
        pages = [
            ImportPage(
                actual_page=2,
                book=1,
                text="""ACANOPYORNIS
SIZE: Large
MOVE: 180 ft.
ARMOR CLASS: 8
HIT DICE: 3
ATTACKS: 3
DAMAGE: 1-4, 1-4, 1-2
RARITY: Uncommon
INTELLIGENCE: Animal
ALIGNMENT: Neutral
LEVEL/X.P.: 2 / 65 + 2/hp
""",
            ),
            ImportPage(
                actual_page=124,
                book=2,
                text="""ZYGOHOUND
SIZE: Medium
MOVE: 120 ft.
ARMOR CLASS: 5
HIT DICE: 4
ATTACKS: 3/2
DAMAGE: By weapon
RARITY: Common
INTELLIGENCE: Low
ALIGNMENT: Chaotic evil
LEVEL/X.P.: 3 / 120 + 3/hp
""",
            ),
        ]
        result = build_catalog_from_pages(pages, "sample.pdf", Path("sample.pdf"))
        self.assertEqual(result.monsters_detected, 2)
        self.assertEqual(result.monsters_parsed, 2)
        self.assertEqual(result.first_last_by_book[1], ("ACANOPYORNIS", "ACANOPYORNIS"))
        self.assertEqual(result.first_last_by_book[2], ("ZYGOHOUND", "ZYGOHOUND"))
        self.assertIn("Entries missing expected fields", result.report_text)
        self.assertEqual(result.catalog["monster_count"], 2)

    def test_import_writes_catalog_and_report_from_stubbed_pages(self):
        sample_pages = [
            ImportPage(
                actual_page=2,
                book=1,
                text="""ACANOPYORNIS
SIZE: Large
MOVE: 180 ft.
ARMOR CLASS: 8
HIT DICE: 3
ATTACKS: 3
DAMAGE: 1-4, 1-4, 1-2
SPECIAL ATTACKS: None
SPECIAL DEFENSES: None
MAGIC RESISTANCE: None
RARITY: Uncommon
NO. ENCOUNTERED: 9-16
LAIR PROBABILITY: 10%
TREASURE: None
INTELLIGENCE: Animal
ALIGNMENT: Neutral
LEVEL/X.P.: 2 / 65 + 2/hp
""",
            )
        ]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pdf_path = root / "sample.pdf"
            pdf_path.write_bytes(b"%PDF-sample")
            output_path = root / "monster_catalog.json"
            report_path = root / "monster_report.txt"

            from unittest.mock import patch

            with patch(
                "tools.importers.monster_manual_importer.extract_pdf_pages",
                return_value=sample_pages,
            ):
                result = import_monster_manual(pdf_path, output_path, report_path)

            self.assertEqual(result.monsters_parsed, 1)
            self.assertTrue(output_path.exists())
            self.assertTrue(report_path.exists())
            self.assertIn("ACANOPYORNIS", report_path.read_text(encoding="utf-8"))
            self.assertIn("\"monster_count\": 1", output_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
