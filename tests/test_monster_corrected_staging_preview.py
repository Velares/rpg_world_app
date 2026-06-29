from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.importers.monster_corrected_staging_preview import (
    build_staged_record,
    build_staging_preview,
    format_report,
    write_staging_preview,
)
from tools.importers.monster_manual_schema import (
    DEFAULT_MONSTER_APPENDIX_CATALOG_JSON,
    DEFAULT_MONSTER_CATALOG_JSON,
)


class CorrectedStagingPreviewTests(unittest.TestCase):
    def _make_record(self, **kwargs: object) -> dict[str, object]:
        return {
            "id": kwargs.get("id", "normalized.test.goblin"),
            "source_entry_id": kwargs.get("source_entry_id", "goblin"),
            "source_slug": kwargs.get("source_slug", "goblin"),
            "source_page_start": kwargs.get("source_page_start", 1),
            "source_page_end": kwargs.get("source_page_end", 1),
            "display_name": kwargs.get("display_name", "Goblin"),
            "canonical_name": kwargs.get("canonical_name", "Goblin"),
            "armor_class": kwargs.get("armor_class", "6"),
            "hit_dice": kwargs.get("hit_dice", "1-1"),
            "movement": kwargs.get("movement", "60 ft."),
            "attacks": kwargs.get("attacks", "1"),
            "damage": kwargs.get("damage", "1d6"),
            "special_attacks": kwargs.get("special_attacks", None),
            "special_defenses": kwargs.get("special_defenses", None),
            "save": kwargs.get("save", "F0"),
            "morale": kwargs.get("morale", "7"),
            "xp": kwargs.get("xp", 10),
            "alignment": kwargs.get("alignment", "Chaotic"),
            "number_appearing": kwargs.get("number_appearing", "2d4"),
            "treasure": kwargs.get("treasure", "None"),
            "monster_type": kwargs.get("monster_type", "humanoid"),
            "category": kwargs.get("category", None),
            "environment": kwargs.get("environment", None),
            "terrain": kwargs.get("terrain", None),
            "region": kwargs.get("region", None),
            "size": kwargs.get("size", "Small"),
            "intelligence": kwargs.get("intelligence", "Average"),
            "level": kwargs.get("level", None),
            "challenge": kwargs.get("challenge", None),
            "description": kwargs.get("description", None),
            "missing_fields": kwargs.get("missing_fields", ["category", "environment"]),
            "placeholder_fields": kwargs.get("placeholder_fields", ["category"]),
            "mapping_confidence": kwargs.get(
                "mapping_confidence",
                {
                    "armor_class": "high",
                    "movement": "medium",
                    "category": "missing",
                },
            ),
            "review_status": kwargs.get("review_status", "mapped_with_placeholders"),
            "raw_stat_block": kwargs.get("raw_stat_block", "AC 6, HD 1-1"),
            "raw_text": kwargs.get("raw_text", "Goblin\nAC 6"),
        }

    def _make_preview(self, records: list[dict[str, object]], source_id: str = "test_source") -> dict[str, object]:
        return {
            "generated_at": "2026-01-01T00:00:00+00:00",
            "source_id": source_id,
            "source_title": "Test Source",
            "source_file": "test.pdf",
            "record_count": len(records),
            "review_status_counts": {},
            "normalized_monsters": records,
        }

    def _make_corrections(self, record_id: str, fields: dict[str, object]) -> dict[str, object]:
        return {
            "schema_version": 1,
            "source_reports": ["a.json"],
            "corrections": {
                record_id: {
                    "fields": {
                        name: {
                            "corrected_value": str(value),
                            "previous_value": None,
                            "notes": "",
                            "updated_at": "2026-01-01T00:00:00+00:00",
                            "reviewer": "local_user",
                        }
                        for name, value in fields.items()
                    },
                    "record_notes": "",
                    "record_status": "corrected",
                    "updated_at": "2026-01-01T00:00:00+00:00",
                    "reviewer": "local_user",
                }
            },
        }

    def test_loads_normalized_preview_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "preview.json"
            path.write_text(json.dumps(self._make_preview([self._make_record()])), encoding="utf-8")
            preview = build_staging_preview([path])
            self.assertEqual(preview["record_count"], 1)
            self.assertEqual(preview["staged_records"][0]["display_name"], "Goblin")

    def test_missing_correction_file_loads_as_no_corrections(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "preview.json"
            path.write_text(json.dumps(self._make_preview([self._make_record()])), encoding="utf-8")
            preview = build_staging_preview([path])
            record = preview["staged_records"][0]
            self.assertEqual(record["review_metadata"]["correction_status"], "uncorrected")
            self.assertEqual(record["corrections"]["fields"], {})

    def test_valid_correction_file_overlays_corrected_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            preview_path = Path(temp) / "preview.json"
            corrections_path = Path(temp) / "corrections.json"
            record = self._make_record()
            preview_path.write_text(json.dumps(self._make_preview([record])), encoding="utf-8")
            corrections_path.write_text(
                json.dumps(self._make_corrections(record["id"], {"armor_class": "5"})),
                encoding="utf-8",
            )
            preview = build_staging_preview([preview_path], corrections_path)
            staged = preview["staged_records"][0]
            self.assertEqual(staged["effective"]["armor_class"], "5")
            self.assertEqual(staged["original"]["armor_class"], "6")
            self.assertEqual(staged["review_metadata"]["correction_status"], "corrected")

    def test_original_field_values_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            preview_path = Path(temp) / "preview.json"
            corrections_path = Path(temp) / "corrections.json"
            record = self._make_record()
            preview_path.write_text(json.dumps(self._make_preview([record])), encoding="utf-8")
            corrections_path.write_text(
                json.dumps(self._make_corrections(record["id"], {"armor_class": "5"})),
                encoding="utf-8",
            )
            preview = build_staging_preview([preview_path], corrections_path)
            staged = preview["staged_records"][0]
            self.assertEqual(staged["original"]["armor_class"], "6")
            self.assertEqual(staged["original"]["hit_dice"], "1-1")

    def test_effective_field_values_reflect_corrections(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            preview_path = Path(temp) / "preview.json"
            corrections_path = Path(temp) / "corrections.json"
            record = self._make_record()
            preview_path.write_text(json.dumps(self._make_preview([record])), encoding="utf-8")
            corrections_path.write_text(
                json.dumps(
                    self._make_corrections(record["id"], {"armor_class": "5", "damage": "1d8"})
                ),
                encoding="utf-8",
            )
            preview = build_staging_preview([preview_path], corrections_path)
            staged = preview["staged_records"][0]
            self.assertEqual(staged["effective"]["armor_class"], "5")
            self.assertEqual(staged["effective"]["damage"], "1d8")
            self.assertEqual(staged["effective"]["hit_dice"], "1-1")

    def test_corrected_records_remain_distinct_by_source_and_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path_a = Path(temp) / "a.json"
            path_b = Path(temp) / "b.json"
            path_a.write_text(
                json.dumps(self._make_preview([self._make_record(id="a.goblin")], source_id="source_a")),
                encoding="utf-8",
            )
            path_b.write_text(
                json.dumps(self._make_preview([self._make_record(id="b.goblin")], source_id="source_b")),
                encoding="utf-8",
            )
            preview = build_staging_preview([path_a, path_b])
            ids = [r["id"] for r in preview["staged_records"]]
            self.assertEqual(len(set(ids)), 2)

    def test_no_canonical_group_merge_occurs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path_a = Path(temp) / "a.json"
            path_b = Path(temp) / "b.json"
            path_a.write_text(
                json.dumps(self._make_preview([self._make_record(id="goblin")], source_id="source_a")),
                encoding="utf-8",
            )
            path_b.write_text(
                json.dumps(self._make_preview([self._make_record(id="goblin")], source_id="source_b")),
                encoding="utf-8",
            )
            preview = build_staging_preview([path_a, path_b])
            self.assertEqual(preview["record_count"], 2)

    def test_canonical_decisions_included_as_metadata_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            preview_path = Path(temp) / "preview.json"
            decisions_path = Path(temp) / "decisions.json"
            preview_path.write_text(json.dumps(self._make_preview([self._make_record()])), encoding="utf-8")
            decisions_path.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "source_report": "candidates.json",
                        "decisions": {"group-1": {"decision": "approved"}},
                    }
                ),
                encoding="utf-8",
            )
            preview = build_staging_preview([preview_path], canonical_decisions_path=decisions_path)
            self.assertIn("canonical_decisions_context", preview)
            self.assertEqual(preview["canonical_decisions_context"]["decisions"]["group-1"]["decision"], "approved")
            self.assertEqual(preview["record_count"], 1)

    def test_no_live_catalog_modification(self) -> None:
        before_catalog = DEFAULT_MONSTER_CATALOG_JSON.read_text(encoding="utf-8")
        before_appendix = DEFAULT_MONSTER_APPENDIX_CATALOG_JSON.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "preview.json"
            path.write_text(json.dumps(self._make_preview([self._make_record()])), encoding="utf-8")
            build_staging_preview([path])
            after_catalog = DEFAULT_MONSTER_CATALOG_JSON.read_text(encoding="utf-8")
            after_appendix = DEFAULT_MONSTER_APPENDIX_CATALOG_JSON.read_text(encoding="utf-8")
            self.assertEqual(before_catalog, after_catalog)
            self.assertEqual(before_appendix, after_appendix)

    def test_no_master_catalog_created(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "preview.json"
            path.write_text(json.dumps(self._make_preview([self._make_record()])), encoding="utf-8")
            preview = build_staging_preview([path])
            self.assertNotIn("master_catalog", preview)
            self.assertNotIn("merged_records", preview)

    def test_normalized_preview_files_not_modified(self) -> None:
        from app.monster_editor import DEFAULT_MANDBMASTER_PREVIEW_PATH, DEFAULT_MEGADUNGEON_PREVIEW_PATH

        before_mandb = DEFAULT_MANDBMASTER_PREVIEW_PATH.read_text(encoding="utf-8")
        before_mega = DEFAULT_MEGADUNGEON_PREVIEW_PATH.read_text(encoding="utf-8")
        build_staging_preview()
        after_mandb = DEFAULT_MANDBMASTER_PREVIEW_PATH.read_text(encoding="utf-8")
        after_mega = DEFAULT_MEGADUNGEON_PREVIEW_PATH.read_text(encoding="utf-8")
        self.assertEqual(before_mandb, after_mandb)
        self.assertEqual(before_mega, after_mega)

    def test_output_deterministic_except_generated_at(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "preview.json"
            path.write_text(json.dumps(self._make_preview([self._make_record()])), encoding="utf-8")
            preview1 = build_staging_preview([path])
            preview2 = build_staging_preview([path])
            self.assertEqual(preview1["record_count"], preview2["record_count"])
            self.assertEqual(
                preview1["staged_records"][0]["effective"],
                preview2["staged_records"][0]["effective"],
            )
            # generated_at is a valid ISO timestamp and may differ; ignore it.
            self.assertIsInstance(preview1["generated_at"], str)
            self.assertIsInstance(preview2["generated_at"], str)
            stripped1 = {k: v for k, v in preview1.items() if k != "generated_at"}
            stripped2 = {k: v for k, v in preview2.items() if k != "generated_at"}
            self.assertEqual(stripped1, stripped2)

    def test_report_includes_counts_and_no_merge_warning(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "preview.json"
            path.write_text(json.dumps(self._make_preview([self._make_record()])), encoding="utf-8")
            preview = build_staging_preview([path])
            report = format_report(preview)
            self.assertIn("Total normalized records read: 1", report)
            self.assertIn("WARNING: This is a non-live staging preview", report)
            self.assertIn("No master catalog was created", report)
            self.assertIn("Source variants remain distinct", report)

    def test_malformed_correction_file_fails_gracefully(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "preview.json"
            corrections_path = Path(temp) / "corrections.json"
            path.write_text(json.dumps(self._make_preview([self._make_record()])), encoding="utf-8")
            corrections_path.write_text("not json", encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                build_staging_preview([path], corrections_path)
            self.assertIn("Could not load corrections", str(ctx.exception))

    def test_invalid_correction_target_id_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "preview.json"
            corrections_path = Path(temp) / "corrections.json"
            record = self._make_record()
            path.write_text(json.dumps(self._make_preview([record])), encoding="utf-8")
            corrections_path.write_text(
                json.dumps(self._make_corrections("missing-id", {"armor_class": "5"})),
                encoding="utf-8",
            )
            preview = build_staging_preview([path], corrections_path)
            staged = preview["staged_records"][0]
            self.assertEqual(staged["effective"]["armor_class"], "6")
            self.assertEqual(staged["review_metadata"]["correction_status"], "uncorrected")

    def test_invalid_correction_field_is_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "preview.json"
            corrections_path = Path(temp) / "corrections.json"
            record = self._make_record()
            path.write_text(json.dumps(self._make_preview([record])), encoding="utf-8")
            corrections = self._make_corrections(record["id"], {"armor_class": "5"})
            corrections["corrections"][record["id"]]["fields"]["not_a_field"] = {
                "corrected_value": "x",
                "previous_value": None,
                "notes": "",
                "updated_at": "2026-01-01T00:00:00+00:00",
                "reviewer": "local_user",
            }
            corrections_path.write_text(json.dumps(corrections), encoding="utf-8")
            preview = build_staging_preview([path], corrections_path)
            staged = preview["staged_records"][0]
            self.assertEqual(staged["effective"]["armor_class"], "5")
            self.assertNotIn("not_a_field", staged["effective"])

    def test_write_staging_preview_creates_json_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "preview.json"
            path.write_text(json.dumps(self._make_preview([self._make_record()])), encoding="utf-8")
            preview = build_staging_preview([path])
            json_path = Path(temp) / "out.json"
            report_path = Path(temp) / "out.txt"
            write_staging_preview(preview, json_path, report_path)
            self.assertTrue(json_path.exists())
            self.assertTrue(report_path.exists())
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["record_count"], 1)
            self.assertIn("Total normalized records read: 1", report_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
