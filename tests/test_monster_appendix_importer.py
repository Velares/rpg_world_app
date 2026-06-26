from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.importers.monster_appendix_importer import (
    ImportPage,
    build_appendix_catalog_from_pages,
    build_appendix_report_text,
    build_unmatched_review_text,
    build_monster_reference_index,
    collapse_wrapped_appendix_lines,
    import_monster_appendices,
    match_monster_reference_details,
    match_monster_reference,
    normalize_monster_reference_name,
    parse_appendix_records_from_pages,
)


def sample_monster_catalog() -> dict[str, object]:
    return {
        "monsters": [
            {"id": "acanopyornis", "name": "Acanopyornis", "sort_name": "ACANOPYORNIS"},
            {"id": "addlevetch", "name": "Addlevetch", "sort_name": "ADDLEVETCH"},
            {"id": "bloodworm", "name": "Blood Worm", "sort_name": "BLOOD WORM"},
            {"id": "golemwax", "name": "Golem, Wax", "sort_name": "GOLEM, WAX"},
            {"id": "monstervestige", "name": "Monster Vestige", "sort_name": "MONSTER VESTIGE"},
            {"id": "peluda", "name": "Peluda", "sort_name": "PELUDA"},
            {"id": "zombiehound", "name": "Zombie, Hound", "sort_name": "ZOMBIE, HOUND"},
            {"id": "crossbreedshrieker", "name": "Crossbreed, Shrieker/Shambling Mound", "sort_name": "CROSSBREED, SHRIEKER/SHAMBLING MOUND"},
            {"id": "dragonamohaji", "name": "Dragon, Amohaji", "sort_name": "DRAGON, AMOHAJI"},
            {"id": "giantsea", "name": "Giant, Sea", "sort_name": "GIANT, SEA"},
            {"id": "quickener", "name": "Quickener", "sort_name": "QUICKENER"},
            {"id": "brainlockmoldspider", "name": "Brainlock Mold (Spider)", "sort_name": "BRAINLOCK MOLD (SPIDER)"},
            {"id": "unihornjackal", "name": "Unihorn Jackal", "sort_name": "UNIHORN JACKAL"},
            {"id": "pelisit", "name": "Pelisit", "sort_name": "PELISIT"},
            {"id": "phasegriffon", "name": "Phase Griffon", "sort_name": "PHASE GRIFFON"},
            {"id": "phasegriffonalt", "name": "Phase-Griffon", "sort_name": "PHASE-GRIFFON"},
            {"id": "thehowler", "name": "The Howler", "sort_name": "THE HOWLER"},
            {"id": "shadowcats", "name": "Shadow Cat", "sort_name": "SHADOW CAT"},
        ]
    }


class MonsterAppendixImporterTests(unittest.TestCase):
    def test_comma_form_and_normalized_matching_are_supported(self):
        index, _, _ = build_monster_reference_index(sample_monster_catalog())
        monster_id, status = match_monster_reference("Wax Golem", index)
        self.assertEqual(status, "matched")
        self.assertEqual(monster_id, "golemwax")
        monster_id, status = match_monster_reference("Green Feeder", index)
        self.assertEqual(status, "unmatched")
        self.assertIsNone(monster_id)

    def test_ambiguous_normalized_match_is_reported(self):
        index, _, _ = build_monster_reference_index(sample_monster_catalog())
        monster_id, status = match_monster_reference("Phase Griffon", index)
        self.assertEqual(status, "ambiguous")
        self.assertIsNone(monster_id)

    def test_wrapped_heading_and_monster_lines_are_collapsed(self):
        known_keys = {
            normalize_monster_reference_name("Crossbreed, Shrieker/Shambling Mound"),
        }
        merged = collapse_wrapped_appendix_lines(
            [
                (221, "Tropical or Subtropical"),
                (221, "Wilderness"),
                (223, "Crossbreed, Shrieker/"),
                (223, "Shambling Mound"),
                (224, "Crossbreed, Shrieker/Sham-"),
                (224, "bling Mound"),
            ],
            known_keys,
        )
        self.assertEqual(
            merged,
            [
                (221, "Tropical or Subtropical Wilderness"),
                (223, "Crossbreed, Shrieker/Shambling Mound"),
                (224, "Crossbreed, Shrieker/Shambling Mound"),
            ],
        )

    def test_level_rarity_and_terrain_records_are_parsed_with_context(self):
        index, _, canonical_names = build_monster_reference_index(sample_monster_catalog())
        pages = [
            ImportPage(
                actual_page=117,
                book=1,
                text="""APPENDIX B: MONSTERS BY LEVEL
LEVEL I
Acanopyornis
Blood Worm (1HD to 2HD)
APPENDIX C: MONSTERS BY RARITY
Common
Zombie, Hound
APPENDIX D: MONSTERS BY TERRAIN TYPE
Temperate Wilderness
Forest
Wax Golem
Elemental Prince
Urban or Settled
Temperate
Monster Vestige
Astral
Quickener
""",
            )
        ]
        records, sections, skipped = parse_appendix_records_from_pages(pages, index, canonical_names)
        self.assertEqual(
            sections,
            [
                "Appendix B: MONSTERS BY LEVEL",
                "Appendix C: MONSTERS BY RARITY",
                "Appendix D: MONSTERS BY TERRAIN TYPE",
            ],
        )
        self.assertEqual(skipped, [])
        blood_worm = next(record for record in records if record["monster_name"] == "Blood Worm")
        self.assertEqual(blood_worm["encounter_type"], "level")
        self.assertEqual(blood_worm["table_title"], "Level I")
        self.assertEqual(blood_worm["notes"], "1HD to 2HD")
        wax_golem = next(record for record in records if record["monster_name"] == "Wax Golem")
        self.assertEqual(wax_golem["monster_id"], "golemwax")
        self.assertEqual(wax_golem["region"], "Wilderness")
        self.assertEqual(wax_golem["climate"], "Temperate")
        self.assertEqual(wax_golem["terrain"], "Forest")
        self.assertEqual(wax_golem["table_title"], "Temperate Wilderness / Forest")
        urban_vestige = next(record for record in records if record["monster_name"] == "Monster Vestige")
        self.assertEqual(urban_vestige["region"], "Urban or Settled")
        self.assertEqual(urban_vestige["climate"], "Temperate")
        self.assertIsNone(urban_vestige["terrain"])
        astral = next(record for record in records if record["monster_name"] == "Quickener")
        self.assertEqual(astral["region"], "Astral")
        self.assertIsNone(astral["terrain"])
        unmatched = next(record for record in records if record["monster_name"] == "Elemental Prince")
        self.assertEqual(unmatched["match_status"], "unmatched")

    def test_roll_ranges_and_raw_source_context_are_preserved(self):
        index, _, canonical_names = build_monster_reference_index(sample_monster_catalog())
        pages = [
            ImportPage(
                actual_page=221,
                book=2,
                text="""APPENDIX B: MONSTERS BY LEVEL
LEVEL II
01-30 Addlevetch
31-60 Blood Worm
""",
            )
        ]
        records, _, _ = parse_appendix_records_from_pages(pages, index, canonical_names)
        addlevetch = records[0]
        self.assertEqual(addlevetch["source_page"], 221)
        self.assertEqual(addlevetch["roll_range"], "01-30")
        self.assertEqual(addlevetch["raw_text"], "01-30 Addlevetch")
        self.assertEqual(addlevetch["monster_id"], "addlevetch")

    def test_parenthetical_article_plural_and_minor_typo_rules_match_only_when_safe(self):
        index, _, canonical_names = build_monster_reference_index(sample_monster_catalog())
        self.assertEqual(
            match_monster_reference_details("Brainlock Mold", index, canonical_names)[:3],
            ("brainlockmoldspider", "matched", "exact"),
        )
        self.assertEqual(
            match_monster_reference_details("Howler", index, canonical_names)[:3],
            ("thehowler", "matched", "exact"),
        )
        self.assertEqual(
            match_monster_reference_details("Shadow Cats", index, canonical_names)[:3],
            ("shadowcats", "matched", "singular"),
        )
        self.assertEqual(
            match_monster_reference_details("Unihorn Jackel", index, canonical_names)[:3],
            ("unihornjackal", "matched", "minor_typo"),
        )
        self.assertEqual(
            match_monster_reference_details("Pelesit", index, canonical_names)[:3],
            ("pelisit", "matched", "minor_typo"),
        )

    def test_unmatched_report_groups_repeated_names_and_preserves_context(self):
        records = [
            {
                "source_page": 119,
                "table_title": "Cold Wilderness / Mountains",
                "monster_name": "Elemental Prince",
                "normalized_monster_name": "elementalprince",
                "match_status": "unmatched",
                "match_rule": "unmatched",
                "candidate_names": [],
                "raw_text": "Elemental Prince",
            },
            {
                "source_page": 120,
                "table_title": "Cold Wilderness / Forest",
                "monster_name": "Elemental Prince",
                "normalized_monster_name": "elementalprince",
                "match_status": "unmatched",
                "match_rule": "unmatched",
                "candidate_names": [],
                "raw_text": "Elemental Prince",
            },
            {
                "source_page": 224,
                "table_title": "Cold Wilderness / Desert",
                "monster_name": "Unihorn Jackel",
                "normalized_monster_name": "unihornjackel",
                "match_status": "unmatched",
                "match_rule": "minor_typo",
                "candidate_names": ["UNIHORN JACKAL"],
                "raw_text": "Unihorn Jackel",
            },
        ]
        review_text = build_unmatched_review_text(records)
        self.assertIn("Unique unmatched normalized names: 2", review_text)
        self.assertIn("Elemental Prince | normalized=elementalprince | count=2", review_text)
        self.assertIn("suggestions: UNIHORN JACKAL", review_text)
        report_text = build_appendix_report_text(
            source_pdf_path=Path("sample.pdf"),
            sections_detected=["Appendix D: MONSTERS BY TERRAIN TYPE"],
            records=records,
            skipped_rows=[],
            warnings=[],
        )
        self.assertIn("Unmatched Reference Review:", report_text)
        self.assertIn("possible_minor_typo_or_ocr_variant", report_text)

    def test_build_catalog_reports_counts(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            catalog_path = root / "monster_catalog.json"
            catalog_path.write_text(
                json.dumps(sample_monster_catalog()),
                encoding="utf-8",
            )
            pages = [
                ImportPage(
                    actual_page=117,
                    book=1,
                    text="""APPENDIX B: MONSTERS BY LEVEL
LEVEL I
Acanopyornis
Unknown Beast
""",
                )
            ]
            result = build_appendix_catalog_from_pages(
                pages,
                "sample.pdf",
                Path("sample.pdf"),
                catalog_path,
            )
        self.assertEqual(result.records_parsed, 2)
        self.assertEqual(result.matched_count, 1)
        self.assertEqual(result.unmatched_count, 1)
        self.assertIn("Appendix rows parsed: 2", result.report_text)
        self.assertIn("Unmatched appendix rows:", result.report_text)
        self.assertEqual(result.catalog["appendix_record_count"], 2)

    def test_import_writes_catalog_and_report_from_stubbed_pages(self):
        sample_pages = [
            ImportPage(
                actual_page=117,
                book=1,
                text="""APPENDIX D: MONSTERS BY TERRAIN TYPE
Astral
Quickener
""",
            )
        ]
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pdf_path = root / "sample.pdf"
            pdf_path.write_bytes(b"%PDF-sample")
            monster_catalog_path = root / "monster_catalog.json"
            monster_catalog_path.write_text(
                json.dumps(sample_monster_catalog()),
                encoding="utf-8",
            )
            output_path = root / "monster_appendix_catalog.json"
            report_path = root / "monster_appendix_report.txt"

            from unittest.mock import patch

            with patch(
                "tools.importers.monster_appendix_importer.extract_appendix_pages",
                return_value=sample_pages,
            ):
                result = import_monster_appendices(
                    pdf_path,
                    monster_catalog_path,
                    output_path,
                    report_path,
                    root / "monster_appendix_unmatched_review.txt",
                )

            self.assertEqual(result.records_parsed, 1)
            self.assertTrue(output_path.exists())
            self.assertTrue(report_path.exists())
            self.assertIn("\"appendix_record_count\": 1", output_path.read_text(encoding="utf-8"))
            self.assertIn("Quickener", report_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
