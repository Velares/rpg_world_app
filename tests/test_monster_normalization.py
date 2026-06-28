from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.monster_catalog import load_monster_catalog
from app.monster_normalization import (
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_MISSING,
    MANDMASTER_SOURCE_ID,
    MANDMASTER_SOURCE_TITLE,
    map_mandbmaster_core_record_to_normalized,
)
from tools.importers.megadungeon_monster_importer import (
    DEFAULT_CONTENT_MONSTERS_JSON,
    DEFAULT_NORMALIZED_PREVIEW_OUTPUT_PATH,
    DEFAULT_NORMALIZED_PREVIEW_REPORT_PATH,
    generate_normalized_preview,
    load_content_pack_records,
    map_megadungeon_content_record_to_normalized,
)
from tools.importers.mandbmaster_normalized_preview import (
    DEFAULT_OUTPUT_PATH as DEFAULT_MANDBMASTER_NORMALIZED_PREVIEW_OUTPUT_PATH,
    DEFAULT_REPORT_PATH as DEFAULT_MANDBMASTER_NORMALIZED_PREVIEW_REPORT_PATH,
    generate_mandbmaster_normalized_preview,
)
from tools.importers.monster_manual_schema import (
    DEFAULT_MONSTER_APPENDIX_CATALOG_JSON,
    DEFAULT_MONSTER_CATALOG_JSON,
)


@unittest.skipUnless(DEFAULT_CONTENT_MONSTERS_JSON.exists(), "Megadungeon content pack is required for normalization tests.")
class MonsterNormalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        payload, records = load_content_pack_records(DEFAULT_CONTENT_MONSTERS_JSON)
        cls.payload = payload
        cls.records = records
        cls.by_name = {record["name"]: record for record in records}
        core_payload = json.loads(DEFAULT_MONSTER_CATALOG_JSON.read_text(encoding="utf-8"))
        cls.core_payload = core_payload
        cls.core_records = core_payload["monsters"]
        cls.core_by_name = {record["name"]: record for record in cls.core_records}

    def test_megadungeon_aarakocra_maps_to_normalized_schema(self):
        normalized = map_megadungeon_content_record_to_normalized(self.by_name["Aarakocra"])
        self.assertEqual(normalized["id"], "normalized.megadungeon_monster_manual.aarakocra")
        self.assertEqual(normalized["canonical_name"], "Aarakocra")
        self.assertEqual(normalized["display_name"], "Aarakocra")
        self.assertEqual(normalized["source_id"], "megadungeon_monster_manual")
        self.assertEqual(normalized["source_title"], "Megadungeon Monster Manual")
        self.assertEqual(normalized["source_file"], "MegadungeonMonsterManual.pdf")
        self.assertEqual(normalized["source_page_start"], 9)
        self.assertEqual(normalized["source_page_end"], 9)
        self.assertEqual(normalized["source_entry_id"], "megadungeon.monster.aarakocra")
        self.assertEqual(normalized["source_slug"], "aarakocra")
        self.assertEqual(normalized["number_appearing"], "2d4")
        self.assertEqual(normalized["movement"], "30 (Fly 120)")
        self.assertEqual(normalized["armor_class"], "6")
        self.assertEqual(normalized["hit_dice"], "1+1")
        self.assertEqual(normalized["xp"], "33")
        self.assertEqual(normalized["mapping_confidence"]["number_appearing"], CONFIDENCE_MEDIUM)
        self.assertEqual(normalized["mapping_confidence"]["movement"], CONFIDENCE_HIGH)
        self.assertEqual(normalized["mapping_confidence"]["monster_type"], CONFIDENCE_LOW)
        self.assertEqual(normalized["monster_type"], "humanoid")
        self.assertTrue(any("Inferred monster_type" in note for note in normalized["review_notes"]))
        self.assertEqual(normalized["user_corrections"], {})

    def test_megadungeon_rock_manta_preserves_raw_multi_xp_string(self):
        normalized = map_megadungeon_content_record_to_normalized(self.by_name["Rock Manta"])
        self.assertEqual(normalized["display_name"], "Rock Manta")
        self.assertEqual(normalized["source_page_start"], 83)
        self.assertEqual(normalized["source_page_end"], 83)
        self.assertEqual(normalized["movement"], "See Below")
        self.assertEqual(normalized["attacks"], "See below")
        self.assertEqual(normalized["damage"], "See below")
        self.assertEqual(normalized["xp"], "47 , 95, 220, 650")
        self.assertEqual(normalized["mapping_confidence"]["xp"], CONFIDENCE_HIGH)
        self.assertEqual(normalized["raw_stat_block"], self.by_name["Rock Manta"]["raw_stat_block"])
        self.assertIn("Rock mantas are flying creatures", normalized["raw_text"])

    def test_missing_fields_become_placeholders_and_are_tracked(self):
        normalized = map_megadungeon_content_record_to_normalized(self.by_name["Rock Manta"])
        for field_name in ("hit_points", "special_attacks", "special_defenses", "size", "environment", "challenge", "level"):
            self.assertIsNone(normalized[field_name])
            self.assertIn(field_name, normalized["missing_fields"])
            self.assertIn(field_name, normalized["placeholder_fields"])
            self.assertEqual(normalized["mapping_confidence"][field_name], CONFIDENCE_MISSING)

    def test_inferred_values_are_review_flagged(self):
        normalized = map_megadungeon_content_record_to_normalized(self.by_name["Aarakocra"])
        self.assertEqual(normalized["review_status"], "needs_review")
        self.assertTrue(normalized["review_notes"])

    def test_normalized_preview_writes_separate_outputs_and_keeps_live_catalogs_unchanged(self):
        before_catalog = DEFAULT_MONSTER_CATALOG_JSON.read_text(encoding="utf-8")
        before_appendix = DEFAULT_MONSTER_APPENDIX_CATALOG_JSON.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            result = generate_normalized_preview(
                monsters_json_path=DEFAULT_CONTENT_MONSTERS_JSON,
                preview_output_path=temp_root / "normalized_preview.json",
                report_path=temp_root / "normalized_preview_report.txt",
            )
            self.assertEqual(result.record_count, 253)
            self.assertTrue(result.preview_path.exists())
            self.assertTrue(result.report_path.exists())
            self.assertNotEqual(result.preview_path.resolve(), DEFAULT_MONSTER_CATALOG_JSON.resolve())
            self.assertNotEqual(result.report_path.resolve(), DEFAULT_MONSTER_APPENDIX_CATALOG_JSON.resolve())
            payload = json.loads(result.preview_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["record_count"], 253)
            self.assertEqual(len(payload["normalized_monsters"]), 253)
            names = {record["display_name"] for record in payload["normalized_monsters"]}
            self.assertIn("Aarakocra", names)
            self.assertIn("Rock Manta", names)
        after_catalog = DEFAULT_MONSTER_CATALOG_JSON.read_text(encoding="utf-8")
        after_appendix = DEFAULT_MONSTER_APPENDIX_CATALOG_JSON.read_text(encoding="utf-8")
        self.assertEqual(before_catalog, after_catalog)
        self.assertEqual(before_appendix, after_appendix)

    def test_normalized_preview_output_defaults_are_separate_from_live_catalog_paths(self):
        self.assertNotEqual(DEFAULT_NORMALIZED_PREVIEW_OUTPUT_PATH.resolve(), DEFAULT_MONSTER_CATALOG_JSON.resolve())
        self.assertNotEqual(DEFAULT_NORMALIZED_PREVIEW_REPORT_PATH.resolve(), DEFAULT_MONSTER_APPENDIX_CATALOG_JSON.resolve())

    def test_default_and_imported_catalog_counts_remain_stable(self):
        default_records = load_monster_catalog()
        imported_records = load_monster_catalog(include_imported=True)
        self.assertEqual(len(default_records), 268)
        self.assertEqual(len(imported_records), 521)

    def test_mandbmaster_record_maps_to_normalized_schema(self):
        normalized = map_mandbmaster_core_record_to_normalized(self.core_by_name["Acanopyornis"])
        self.assertEqual(normalized["id"], "normalized.mandbmaster_combined_monster_manual.acanopyornis")
        self.assertEqual(normalized["canonical_name"], "Acanopyornis")
        self.assertEqual(normalized["display_name"], "Acanopyornis")
        self.assertEqual(normalized["source_id"], MANDMASTER_SOURCE_ID)
        self.assertEqual(normalized["source_title"], MANDMASTER_SOURCE_TITLE)
        self.assertEqual(normalized["source_file"], "mandbmaster.pdf")
        self.assertEqual(normalized["source_page_start"], 2)
        self.assertEqual(normalized["source_page_end"], 2)
        self.assertEqual(normalized["source_entry_id"], "acanopyornis")
        self.assertEqual(normalized["source_slug"], "acanopyornis")
        self.assertEqual(normalized["armor_class"], "8")
        self.assertEqual(normalized["hit_dice"], "3")
        self.assertEqual(normalized["movement"], "180 ft.")
        self.assertEqual(normalized["number_appearing"], "9-16")
        self.assertEqual(normalized["xp"], "2 / 65 + 2/hp")
        self.assertEqual(normalized["level"], "2")
        self.assertEqual(normalized["size"], "Large")
        self.assertEqual(normalized["mapping_confidence"]["armor_class"], CONFIDENCE_HIGH)
        self.assertEqual(normalized["mapping_confidence"]["movement"], CONFIDENCE_MEDIUM)
        self.assertEqual(normalized["mapping_confidence"]["number_appearing"], CONFIDENCE_MEDIUM)
        self.assertEqual(normalized["mapping_confidence"]["xp"], CONFIDENCE_MEDIUM)
        self.assertEqual(normalized["mapping_confidence"]["level"], CONFIDENCE_MEDIUM)
        self.assertTrue(normalized["raw_stat_block"].startswith("SIZE: Large"))
        self.assertIn("The acanopyornis is a large", normalized["raw_text"])
        self.assertEqual(normalized["user_corrections"], {})

    def test_second_mandbmaster_record_preserves_page_and_raw_fields(self):
        normalized = map_mandbmaster_core_record_to_normalized(self.core_by_name["Book Guardian"])
        self.assertEqual(normalized["display_name"], "Book Guardian")
        self.assertEqual(normalized["source_page_start"], 131)
        self.assertEqual(normalized["source_page_end"], 132)
        self.assertEqual(normalized["special_attacks"], "Surprise on 1-5")
        self.assertEqual(normalized["special_defenses"], "See below")
        self.assertEqual(normalized["treasure"], "None")
        self.assertTrue(normalized["raw_stat_block"].startswith("SIZE: Medium"))
        self.assertIn("A book guardian is a", normalized["description"])

    def test_mandbmaster_missing_fields_become_placeholders(self):
        normalized = map_mandbmaster_core_record_to_normalized(self.core_by_name["Acanopyornis"])
        for field_name in ("hit_points", "monster_type", "category", "environment", "terrain", "region", "challenge"):
            self.assertIsNone(normalized[field_name])
            self.assertIn(field_name, normalized["missing_fields"])
            self.assertIn(field_name, normalized["placeholder_fields"])
            self.assertEqual(normalized["mapping_confidence"][field_name], CONFIDENCE_MISSING)

    def test_mandbmaster_normalized_preview_writes_separate_outputs_and_keeps_live_catalogs_unchanged(self):
        before_catalog = DEFAULT_MONSTER_CATALOG_JSON.read_text(encoding="utf-8")
        before_appendix = DEFAULT_MONSTER_APPENDIX_CATALOG_JSON.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            payload, _ = generate_mandbmaster_normalized_preview(
                preview_output_path=temp_root / "mandb_preview.json",
                report_path=temp_root / "mandb_preview_report.txt",
            )
            self.assertEqual(payload["record_count"], 268)
            names = {record["display_name"] for record in payload["normalized_monsters"]}
            self.assertIn("Acanopyornis", names)
            self.assertIn("Book Guardian", names)
            self.assertEqual(
                payload["normalized_monsters"][0]["source_id"],
                MANDMASTER_SOURCE_ID,
            )
        after_catalog = DEFAULT_MONSTER_CATALOG_JSON.read_text(encoding="utf-8")
        after_appendix = DEFAULT_MONSTER_APPENDIX_CATALOG_JSON.read_text(encoding="utf-8")
        self.assertEqual(before_catalog, after_catalog)
        self.assertEqual(before_appendix, after_appendix)

    def test_mandbmaster_normalized_preview_defaults_are_separate_from_live_catalog_paths(self):
        self.assertNotEqual(
            DEFAULT_MANDBMASTER_NORMALIZED_PREVIEW_OUTPUT_PATH.resolve(),
            DEFAULT_MONSTER_CATALOG_JSON.resolve(),
        )
        self.assertNotEqual(
            DEFAULT_MANDBMASTER_NORMALIZED_PREVIEW_REPORT_PATH.resolve(),
            DEFAULT_MONSTER_APPENDIX_CATALOG_JSON.resolve(),
        )


if __name__ == "__main__":
    unittest.main()
