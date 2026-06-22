from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.importers.monster_manual_importer import (
    ImportPage,
    build_catalog_from_pages,
    import_monster_manual,
    is_heading_candidate,
    is_page_marker_line,
    parse_monster_entry,
    split_entries_from_pages,
)


class MonsterManualImporterTests(unittest.TestCase):
    def test_page_marker_lines_are_recognized(self):
        self.assertTrue(is_page_marker_line("20 21"))
        self.assertTrue(is_page_marker_line("59"))
        self.assertFalse(is_page_marker_line("LEVEL/X.P.: 2 / 65 + 2/hp"))
        self.assertFalse(is_page_marker_line("1-4"))

    def test_running_headers_and_letter_markers_are_rejected(self):
        rejected = [
            "A",
            "B",
            "I-K",
            "ACANOPYORNIS - ACULEAN - ADDLEVETCH - ARCANOPLASM",
            "BARATHELAR - BLACKWATER SLOUGH - BLESSED RING",
            "OF HEAVEN",
            "CRYSTALLINE - WYRM, ENSLAVING - WYRM, KURGAN",
        ]
        accepted = [
            "ACANOPYORNIS",
            "GOLEM, WAX",
            "MONSTER VESTIGE",
            "ZOMBIE, HOUND",
        ]
        for line in rejected:
            self.assertFalse(is_heading_candidate(line), line)
        for line in accepted:
            self.assertTrue(is_heading_candidate(line), line)

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

    def test_accepts_real_monster_names_with_commas_and_multiline_level_xp(self):
        pages = [
            ImportPage(
                actual_page=90,
                book=2,
                text="""MONSTER VESTIGE
SIZE: Variable
MOVE: 220 ft.
ARMOR CLASS: 0 / as possessed creature
HIT DICE: As possessed creature
ATTACKS: 1 / as possessed creature
DAMAGE: (n/a)
SPECIAL ATTACKS: Possession
SPECIAL DEFENSES: None
MAGIC RESISTANCE: 25%
RARITY: Very rare
NO. ENCOUNTERED: 1
LAIR PROBABILITY: 100%
TREASURE: Nil
INTELLIGENCE: Variable; usually Semi
ALIGNMENT: Neutral or any Evil
LEVEL/X.P.: 5 / 900 + X/hp

GOLEM, WAX
SIZE: Medium (7 ft. tall)
MOVE: 60 ft.
ARMOR CLASS: 5
HIT DICE: 40 hit points
ATTACKS: 2
DAMAGE: 1-10, 1-10
SPECIAL ATTACKS: See below
SPECIAL DEFENSES: See below
MAGIC RESISTANCE: See below
RARITY: Very rare
NO. ENCOUNTERED: 1-4
LAIR PROBABILITY: 100%
TREASURE: None
INTELLIGENCE: None
ALIGNMENT: Neutral
LEVEL/X.P.: 7 / 1,680

PELUDA
SIZE: Large (10 ft. long)
MOVE: 150 ft.
ARMOR CLASS: 5
HIT DICE: 9-12
ATTACKS: 1
DAMAGE: 3-18
SPECIAL ATTACKS: Breath weapon, poison, quills
SPECIAL DEFENSES: See below
MAGIC RESISTANCE: None
RARITY: Very rare
NO. ENCOUNTERED: 1
LAIR PROBABILITY: 35%
TREASURE: None
INTELLIGENCE: Low to average
ALIGNMENT: Neutral
LEVEL/X.P.:
9 HD: 7 / 3,000 + 12/hp
10 HD: 8 / 3,800 + 13/hp
11HD: 8 / 4,700 + 14/hp
12 HD: 9 / 6,550 + 16/hp

ZOMBIE, HOUND
SIZE: Small
MOVE: 90 ft.
ARMOR CLASS: 8
HIT DICE: 2
ATTACKS: 1
DAMAGE: 1-6
SPECIAL ATTACKS: None
SPECIAL DEFENSES: None
MAGIC RESISTANCE: None
RARITY: Common
NO. ENCOUNTERED: 1-8
LAIR PROBABILITY: 0%
TREASURE: None
INTELLIGENCE: Animal
ALIGNMENT: Neutral evil
LEVEL/X.P.: 2 / 40 + 1/hp
""",
            )
        ]
        entries = split_entries_from_pages(pages)
        self.assertEqual(
            [entry.heading for entry in entries],
            ["MONSTER VESTIGE", "GOLEM, WAX", "PELUDA", "ZOMBIE, HOUND"],
        )
        peluda = next(entry for entry in entries if entry.heading == "PELUDA")
        monster, _ = parse_monster_entry(peluda, "sample.pdf")
        self.assertEqual(
            monster["stat_block"]["level_xp"]["raw"],
            "9 HD: 7 / 3,000 + 12/hp 10 HD: 8 / 3,800 + 13/hp 11HD: 8 / 4,700 + 14/hp 12 HD: 9 / 6,550 + 16/hp",
        )

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

    def test_rejected_running_headers_do_not_enter_catalog_or_duplicates(self):
        pages = [
            ImportPage(
                actual_page=65,
                book=1,
                text="""66 67
L
LASSOO - LATCH FROG - LOSTLING
LASSOO
SIZE: Small (3 ft. wide)
MOVE: 40 ft.
ARMOR CLASS: 7
HIT DICE: 2
ATTACKS: 1
DAMAGE: 1-6
RARITY: Rare
INTELLIGENCE: Animal
ALIGNMENT: Neutral
LEVEL/X.P.: 2 / 35 + 1/hp
""",
            ),
            ImportPage(
                actual_page=217,
                book=2,
                text="""97
X-Z
XIAROEN - YALI - YUXA - ZIBURINIS - ZOMBIE, HOUND
ZOMBIE, HOUND
SIZE: Small
MOVE: 90 ft.
ARMOR CLASS: 8
HIT DICE: 2
ATTACKS: 1
DAMAGE: 1-6
RARITY: Common
INTELLIGENCE: Animal
ALIGNMENT: Neutral evil
LEVEL/X.P.: 2 / 40 + 1/hp
""",
            ),
        ]
        result = build_catalog_from_pages(pages, "sample.pdf", Path("sample.pdf"))
        names = [monster["sort_name"] for monster in result.catalog["monsters"]]
        self.assertEqual(names, ["LASSOO", "ZOMBIE, HOUND"])
        self.assertEqual(result.duplicate_ids, [])
        self.assertIn("L", result.rejected_candidates)
        self.assertIn("LASSOO - LATCH FROG - LOSTLING", result.rejected_candidates)
        self.assertIn("X-Z", result.rejected_candidates)
        self.assertIn("XIAROEN - YALI - YUXA - ZIBURINIS - ZOMBIE, HOUND", result.rejected_candidates)

    def test_page_markers_are_removed_from_real_fields(self):
        pages = [
            ImportPage(
                actual_page=20,
                book=1,
                text="""CEILIDH HORROR
SIZE: Large (8 ft. long)
MOVE: 120 ft.
ARMOR CLASS: 4
HIT DICE: 2
ATTACKS: 1
DAMAGE: 2-8
SPECIAL ATTACKS: Vocalize
SPECIAL DEFENSES: None
MAGIC RESISTANCE: None
RARITY: Rare
NO. ENCOUNTERED: 1 or 3-24
LAIR PROBABILITY: 50%
TREASURE: None
INTELLIGENCE: Semi
ALIGNMENT: Neutral
LEVEL/X.P.: 2 / 45 + 1/hp
20 21
General information: test
""",
            ),
            ImportPage(
                actual_page=59,
                book=1,
                text="""LESSER GOLEM, WOOD
SIZE: Large
MOVE: 60 ft.
ARMOR CLASS: 4
HIT DICE: 50 hit points
ATTACKS: 1
DAMAGE: 3-12
SPECIAL ATTACKS: Warp wood
SPECIAL DEFENSES: See below
59
MAGIC RESISTANCE: None
RARITY: Very Rare
NO. ENCOUNTERED: 1
LAIR PROBABILITY: None
TREASURE: None
INTELLIGENCE: None
ALIGNMENT: Neutral
LEVEL/X.P.: 8 / 5,150
""",
            ),
            ImportPage(
                actual_page=95,
                book=2,
                text="""WYRM, KURGAN
SIZE: Large (42 ft. long)
MOVE: 180 ft., burrowing 120 ft.
ARMOR CLASS: -1
HIT DICE: 10-13
ATTACKS: 3
DAMAGE: 1-8, 1-8, 3-30
SPECIAL ATTACKS: See below
SPECIAL DEFENSES: See below
MAGIC RESISTANCE: 20%
RARITY: Very rare
NO. ENCOUNTERED: 1
LAIR PROBABILITY: 65%
TREASURE: None
I
""",
            ),
            ImportPage(
                actual_page=96,
                book=2,
                text="""96
NTELLIGENCE: Very
ALIGNMENT: Neutral evil
LEVEL/X.P.: Varies
General information: test
""",
            ),
        ]
        result = build_catalog_from_pages(pages, "sample.pdf", Path("sample.pdf"))
        by_name = {monster["sort_name"]: monster for monster in result.catalog["monsters"]}
        self.assertEqual(
            by_name["CEILIDH HORROR"]["stat_block"]["level_xp"]["raw"],
            "2 / 45 + 1/hp",
        )
        self.assertEqual(
            by_name["LESSER GOLEM, WOOD"]["stat_block"]["special_defenses"],
            "See below",
        )
        self.assertEqual(
            by_name["LESSER GOLEM, WOOD"]["stat_block"]["magic_resistance"],
            "None",
        )
        self.assertEqual(
            by_name["WYRM, KURGAN"]["stat_block"]["intelligence"],
            "Very",
        )

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
