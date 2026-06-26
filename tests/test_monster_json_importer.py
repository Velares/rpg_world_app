from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.importers.monster_catalog_import import (
    load_json_monster_records,
    merge_monster_catalog,
    normalize_monster_record,
)
from tools.importers.monster_json_importer import import_monsters_from_json


def sample_existing_catalog() -> dict[str, object]:
    return {
        "generated_at": "2026-06-22T00:00:00+00:00",
        "monster_count": 2,
        "monsters": [
            {
                "id": "acanopyornis",
                "name": "Acanopyornis",
                "sort_name": "ACANOPYORNIS",
                "source": {
                    "file": "MandBmaster.pdf",
                    "book": 1,
                    "actual_page_start": 2,
                    "actual_page_end": 2,
                },
                "stat_block": {
                    "size": "Large",
                    "size_detail": None,
                    "move": "180 ft.",
                    "armor_class": "8",
                    "hit_dice": "3",
                    "attacks": "3",
                    "damage": ["1-4", "1-4", "1-2"],
                    "special_attacks": None,
                    "special_defenses": None,
                    "magic_resistance": None,
                    "rarity": "Uncommon",
                    "number_encountered": None,
                    "lair_probability": None,
                    "treasure": None,
                    "intelligence": "Animal",
                    "alignment": "Neutral",
                    "level_xp": {"raw": "2 / 65 + 2/hp"},
                },
                "sections": {
                    "general_information": None,
                    "languages": None,
                    "physical_description": None,
                    "variants": None,
                },
                "tags": ["animal_intelligence"],
                "raw_text": "",
            },
            {
                "id": "manualspecter",
                "name": "Manual Specter",
                "sort_name": "MANUAL SPECTER",
                "source": {"file": "bestiary_notes.json", "name": "Bestiary Notes", "type": "custom"},
                "stat_block": {
                    "size": "Medium",
                    "size_detail": None,
                    "move": None,
                    "armor_class": None,
                    "hit_dice": None,
                    "attacks": None,
                    "damage": [],
                    "special_attacks": None,
                    "special_defenses": None,
                    "magic_resistance": None,
                    "rarity": None,
                    "number_encountered": None,
                    "lair_probability": None,
                    "treasure": None,
                    "intelligence": None,
                    "alignment": None,
                    "level_xp": {"raw": ""},
                },
                "sections": {
                    "general_information": "Hand-entered note.",
                    "languages": None,
                    "physical_description": None,
                    "variants": None,
                },
                "tags": [],
                "raw_text": "",
                "custom_record": True,
                "protected_fields": ["stat_block", "sections"],
            },
        ],
    }


class MonsterJsonImporterTests(unittest.TestCase):
    def test_normalize_monster_record_maps_flat_fields_and_metadata(self):
        normalized = normalize_monster_record(
            {
                "name": "Lantern Hound",
                "size": "Medium",
                "hit_dice": "3",
                "rarity": "Rare",
                "source_record_id": "LH-01",
                "temperament": "watchful",
            },
            source_name="Sample Pack",
            source_type="json",
            source_file="sample_monsters.json",
        )
        self.assertEqual(normalized.errors, [])
        record = normalized.record
        assert record is not None
        self.assertEqual(record["id"], "lanternhound")
        self.assertEqual(record["sort_name"], "LANTERN HOUND")
        self.assertEqual(record["stat_block"]["size"], "Medium")
        self.assertEqual(record["source"]["record_id"], "LH-01")
        self.assertEqual(record["import_metadata"]["source_id"], "json:Sample Pack")
        self.assertIn("temperament", record["source_extra_fields"])

    def test_load_json_monster_records_accepts_monsters_list(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "sample.json"
            path.write_text(
                json.dumps(
                    {
                        "monsters": [
                            {"name": "Ash Lurker", "size": "Medium"},
                            {"name": "Bog Lamprey", "size": "Small"},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            records, warnings, errors = load_json_monster_records(path)
        self.assertEqual(len(records), 2)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_missing_name_is_reported_as_error(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "invalid.json"
            path.write_text(json.dumps([{"size": "Medium"}]), encoding="utf-8")
            records, warnings, errors = load_json_monster_records(path)
        self.assertEqual(records, [])
        self.assertEqual(warnings, [])
        self.assertEqual(errors, ["Record 1: Missing required field: name"])

    def test_merge_marks_exact_duplicate_and_safe_addition(self):
        normalized_records = [
            normalize_monster_record(
                {
                    "name": "Acanopyornis",
                    "sort_name": "ACANOPYORNIS",
                    "id": "acanopyornis",
                    "stat_block": sample_existing_catalog()["monsters"][0]["stat_block"],
                    "sections": sample_existing_catalog()["monsters"][0]["sections"],
                    "tags": sample_existing_catalog()["monsters"][0]["tags"],
                },
                source_name="Import Pack",
                source_type="json",
                source_file="import.json",
            ).record,
            normalize_monster_record(
                {"name": "Salt Widow", "size": "Medium", "hit_dice": "4", "rarity": "Rare"},
                source_name="Import Pack",
                source_type="json",
                source_file="import.json",
            ).record,
        ]
        result = merge_monster_catalog(
            sample_existing_catalog(),
            [record for record in normalized_records if record is not None],
            apply_safe_additions=True,
        )
        actions = [decision.action for decision in result.decisions]
        self.assertEqual(actions, ["exact_duplicate", "would_add"])
        self.assertEqual(result.merged_catalog["monster_count"], 3)

    def test_same_source_record_with_changed_data_reports_would_update(self):
        existing = sample_existing_catalog()
        existing["monsters"][0]["import_metadata"] = {
            "source_id": "json:Import Pack",
            "source_record_id": "A-01",
            "source_type": "json",
        }
        record = normalize_monster_record(
            {
                "name": "Acanopyornis",
                "id": "acanopyornis",
                "size": "Huge",
                "source_record_id": "A-01",
            },
            source_name="Import Pack",
            source_type="json",
            source_file="import.json",
        ).record
        assert record is not None
        result = merge_monster_catalog(existing, [record])
        self.assertEqual(result.decisions[0].action, "would_update")

    def test_manual_custom_record_blocks_conflicting_import(self):
        record = normalize_monster_record(
            {
                "name": "Manual Specter",
                "sort_name": "MANUAL SPECTER",
                "size": "Large",
            },
            source_name="Import Pack",
            source_type="json",
            source_file="import.json",
        ).record
        assert record is not None
        result = merge_monster_catalog(sample_existing_catalog(), [record])
        self.assertEqual(result.decisions[0].action, "protected_conflict")

    def test_import_writes_preview_and_report_in_dry_run_mode(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            json_path = root / "sample_import.json"
            json_path.write_text(
                json.dumps(
                    [
                        {"name": "Ash Lurker", "size": "Medium", "source_record_id": "ASH-1"},
                        {"size": "Small"},
                    ]
                ),
                encoding="utf-8",
            )
            catalog_path = root / "monster_catalog.json"
            catalog_path.write_text(json.dumps(sample_existing_catalog()), encoding="utf-8")
            report_path = root / "report.txt"
            preview_path = root / "preview.json"

            result = import_monsters_from_json(
                json_path,
                catalog_path=catalog_path,
                report_path=report_path,
                preview_output_path=preview_path,
                output_catalog_path=root / "merged_catalog.json",
                source_name="Sample JSON Pack",
            )

            self.assertFalse(result.wrote_catalog)
            self.assertTrue(report_path.exists())
            self.assertTrue(preview_path.exists())
            preview = json.loads(preview_path.read_text(encoding="utf-8"))
            self.assertEqual(preview["decision_counts"]["would_add"], 1)
            self.assertIn("Record 2: Missing required field: name", preview["errors"])
            self.assertIn("Dry run only: yes", report_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
