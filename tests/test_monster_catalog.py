from __future__ import annotations

import json
import tempfile
import unittest
import warnings
from pathlib import Path

from app.monster_catalog import (
    DEFAULT_IMPORTED_MONSTER_PACKS_ROOT,
    load_core_monster_records,
    load_imported_monster_records,
    load_monster_catalog,
)
from tools.importers.monster_manual_schema import DEFAULT_MONSTER_CATALOG_JSON


class MonsterCatalogLoaderTests(unittest.TestCase):
    def test_default_monster_catalog_load_remains_core_only(self):
        core_records = load_core_monster_records()
        default_records = load_monster_catalog()
        self.assertEqual(len(default_records), len(core_records))
        self.assertEqual(len(default_records), 268)
        self.assertFalse(
            any(record.get("source_id") == "megadungeon_monster_manual" for record in default_records)
        )

    def test_imported_pack_records_are_opt_in(self):
        imported_records = load_imported_monster_records()
        self.assertEqual(len(imported_records), 253)

        default_records = load_monster_catalog()
        combined_records = load_monster_catalog(include_imported=True)

        self.assertEqual(len(default_records), 268)
        self.assertEqual(len(combined_records), len(default_records) + len(imported_records))
        self.assertEqual(len(combined_records), 521)

    def test_megadungeon_pack_loads_expected_records(self):
        imported_records = load_imported_monster_records()
        by_name = {record["name"]: record for record in imported_records}

        aarakocra = by_name["Aarakocra"]
        self.assertEqual(aarakocra["id"], "megadungeon.monster.aarakocra")
        self.assertEqual(aarakocra["source_id"], "megadungeon_monster_manual")
        self.assertEqual(aarakocra["source_title"], "Megadungeon Monster Manual")
        self.assertEqual(aarakocra["actual_page_start"], 9)
        self.assertEqual(aarakocra["actual_page_end"], 9)
        self.assertEqual(aarakocra["parser_status"], "parsed")
        self.assertEqual(aarakocra["confidence"], "high")

        rock_manta = by_name["Rock Manta"]
        self.assertEqual(rock_manta["id"], "megadungeon.monster.rockmanta")
        self.assertEqual(rock_manta["source_id"], "megadungeon_monster_manual")
        self.assertEqual(rock_manta["actual_page_start"], 83)
        self.assertEqual(rock_manta["actual_page_end"], 83)
        self.assertEqual(rock_manta["xp"], "47 , 95, 220, 650")

    def test_duplicate_names_from_imported_packs_do_not_replace_core_records(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            catalog_path = root / "monster_catalog.json"
            content_packs_root = root / "content_packs" / "imported" / "sample_pack"
            content_packs_root.mkdir(parents=True, exist_ok=True)

            catalog_path.write_text(
                json.dumps(
                    {
                        "monster_count": 2,
                        "monsters": [
                            {"id": "manual.monster.skeleton", "name": "Skeleton", "sort_name": "SKELETON"},
                            {"id": "manual.monster.zombie", "name": "Zombie", "sort_name": "ZOMBIE"},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            (content_packs_root / "pack.json").write_text(
                json.dumps(
                    {
                        "id": "imported.sample_pack",
                        "name": "Sample Pack",
                        "source_id": "sample_pack",
                        "source_title": "Sample Pack",
                        "enabled": True,
                    }
                ),
                encoding="utf-8",
            )
            (content_packs_root / "monsters.json").write_text(
                json.dumps(
                    {
                        "monsters": [
                            {
                                "id": "sample.monster.skeleton",
                                "name": "Skeleton",
                                "sort_name": "SKELETON",
                                "source_id": "sample_pack",
                                "source_title": "Sample Pack",
                                "actual_page_start": 7,
                                "actual_page_end": 7,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            combined_records = load_monster_catalog(
                catalog_path=catalog_path,
                content_packs_root=root / "content_packs" / "imported",
                include_imported=True,
            )

        skeletons = [record for record in combined_records if record.get("name") == "Skeleton"]
        self.assertEqual(len(combined_records), 3)
        self.assertEqual(len(skeletons), 2)
        self.assertEqual({record["id"] for record in skeletons}, {"manual.monster.skeleton", "sample.monster.skeleton"})

    def test_malformed_imported_pack_is_skipped_with_warning(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pack_dir = root / "broken_pack"
            pack_dir.mkdir(parents=True, exist_ok=True)
            (pack_dir / "pack.json").write_text("{not valid json", encoding="utf-8")
            (pack_dir / "monsters.json").write_text(json.dumps({"monsters": []}), encoding="utf-8")

            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                imported_records = load_imported_monster_records(root)

        self.assertEqual(imported_records, [])
        self.assertTrue(any("Skipping imported monster pack" in str(item.message) for item in caught))

    def test_non_list_monsters_payload_is_skipped_with_warning(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pack_dir = root / "broken_pack"
            pack_dir.mkdir(parents=True, exist_ok=True)
            (pack_dir / "pack.json").write_text(
                json.dumps(
                    {
                        "id": "imported.broken_pack",
                        "name": "Broken Pack",
                        "source_id": "broken_pack",
                        "source_title": "Broken Pack",
                        "enabled": True,
                    }
                ),
                encoding="utf-8",
            )
            (pack_dir / "monsters.json").write_text(json.dumps({"monsters": {"name": "bad"}}), encoding="utf-8")

            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                imported_records = load_imported_monster_records(root)

        self.assertEqual(imported_records, [])
        self.assertTrue(any("must contain a list" in str(item.message) for item in caught))

    def test_default_imported_packs_root_points_at_imported_content_packs(self):
        self.assertEqual(
            DEFAULT_IMPORTED_MONSTER_PACKS_ROOT,
            DEFAULT_MONSTER_CATALOG_JSON.parents[2] / "content_packs" / "imported",
        )


if __name__ == "__main__":
    unittest.main()
