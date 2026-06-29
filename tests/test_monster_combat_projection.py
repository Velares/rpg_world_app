from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.importers.monster_combat_projection import (
    build_combat_projection,
    format_report,
    write_combat_projection,
)
from tools.importers.monster_manual_schema import (
    DEFAULT_MONSTER_APPENDIX_CATALOG_JSON,
    DEFAULT_MONSTER_CATALOG_JSON,
)


class CombatProjectionTests(unittest.TestCase):
    def _make_staged_record(self, **kwargs: object) -> dict[str, object]:
        record_id = kwargs.get("id", "normalized.test_source.goblin")
        return {
            "id": record_id,
            "display_name": kwargs.get("display_name", "Goblin"),
            "source_id": kwargs.get("source_id", "test_source"),
            "source_title": kwargs.get("source_title", "Test Source"),
            "effective": {
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
                "size": kwargs.get("size", "Small"),
                "intelligence": kwargs.get("intelligence", "Average"),
                "level": kwargs.get("level", None),
                "challenge": kwargs.get("challenge", None),
            },
            "original": {
                "display_name": kwargs.get("display_name", "Goblin"),
                "armor_class": kwargs.get("armor_class", "6"),
            },
            "source_provenance": {
                "source_id": kwargs.get("source_id", "test_source"),
                "source_title": kwargs.get("source_title", "Test Source"),
            },
            "review_metadata": {
                "missing_fields": [],
                "placeholder_fields": [],
                "mapping_confidence": {},
                "review_status": "mapped",
                "correction_status": "uncorrected",
            },
        }

    def _make_staging_preview(self, records: list[dict[str, object]]) -> dict[str, object]:
        return {
            "schema_version": 1,
            "generated_at": "2026-01-01T00:00:00+00:00",
            "source_reports": ["preview.json"],
            "correction_store": "corrections.json",
            "canonical_decisions_store": "decisions.json",
            "canonical_decisions_context": {},
            "record_count": len(records),
            "source_counts": {},
            "staged_records": records,
        }

    def test_loads_corrected_staging_preview(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "staging.json"
            path.write_text(
                json.dumps(self._make_staging_preview([self._make_staged_record()])),
                encoding="utf-8",
            )
            projection = build_combat_projection(path)
            self.assertEqual(projection["record_count"], 1)

    def test_creates_one_projection_per_staged_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "staging.json"
            records = [self._make_staged_record(id=f"r{i}") for i in range(3)]
            path.write_text(json.dumps(self._make_staging_preview(records)), encoding="utf-8")
            projection = build_combat_projection(path)
            self.assertEqual(len(projection["projections"]), 3)

    def test_preserves_source_variants_separately(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "staging.json"
            records = [
                self._make_staged_record(id="goblin", source_id="source_a"),
                self._make_staged_record(id="goblin", source_id="source_b"),
            ]
            path.write_text(json.dumps(self._make_staging_preview(records)), encoding="utf-8")
            projection = build_combat_projection(path)
            self.assertEqual(projection["record_count"], 2)
            sources = {p["source_id"] for p in projection["projections"]}
            self.assertEqual(sources, {"source_a", "source_b"})

    def test_uses_effective_corrected_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "staging.json"
            record = self._make_staged_record()
            record["effective"]["armor_class"] = "5"  # corrected value
            path.write_text(json.dumps(self._make_staging_preview([record])), encoding="utf-8")
            projection = build_combat_projection(path)
            p = projection["projections"][0]
            self.assertEqual(p["armor_class_raw"], "5")
            self.assertEqual(p["armor_class_model"]["value"], 5)

    def test_preserves_raw_combat_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "staging.json"
            path.write_text(
                json.dumps(self._make_staging_preview([self._make_staged_record()])),
                encoding="utf-8",
            )
            projection = build_combat_projection(path)
            p = projection["projections"][0]
            self.assertEqual(p["armor_class_raw"], "6")
            self.assertEqual(p["hit_dice_raw"], "1-1")
            self.assertEqual(p["attacks_raw"], "1")
            self.assertEqual(p["damage_raw"], "1d6")

    def test_creates_model_fields_without_overwriting_raw(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "staging.json"
            path.write_text(
                json.dumps(self._make_staging_preview([self._make_staged_record()])),
                encoding="utf-8",
            )
            projection = build_combat_projection(path)
            p = projection["projections"][0]
            self.assertIsNotNone(p["armor_class_model"])
            self.assertIsNotNone(p["hit_dice_model"])
            self.assertIsNotNone(p["damage_model"])
            self.assertEqual(p["armor_class_raw"], "6")

    def test_missing_ac_hd_attacks_damage_creates_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "staging.json"
            record = self._make_staged_record()
            record["effective"]["armor_class"] = None
            record["effective"]["hit_dice"] = None
            record["effective"]["attacks"] = None
            record["effective"]["damage"] = None
            path.write_text(json.dumps(self._make_staging_preview([record])), encoding="utf-8")
            projection = build_combat_projection(path)
            p = projection["projections"][0]
            self.assertEqual(p["projection_status"], "missing_combat_fields")
            warnings = " ".join(p["projection_warnings"])
            self.assertIn("armor_class", warnings)
            self.assertIn("hit_dice", warnings)
            self.assertIn("attacks", warnings)
            self.assertIn("damage", warnings)

    def test_unparseable_damage_creates_parse_warning(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "staging.json"
            record = self._make_staged_record(damage="By weapon")
            path.write_text(json.dumps(self._make_staging_preview([record])), encoding="utf-8")
            projection = build_combat_projection(path)
            p = projection["projections"][0]
            self.assertEqual(p["projection_status"], "parse_warning")
            self.assertTrue(any("damage could not be parsed" in w for w in p["projection_warnings"]))

    def test_no_master_catalog_created(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "staging.json"
            path.write_text(
                json.dumps(self._make_staging_preview([self._make_staged_record()])),
                encoding="utf-8",
            )
            projection = build_combat_projection(path)
            self.assertNotIn("master_catalog", projection)
            self.assertNotIn("merged_records", projection)

    def test_no_live_catalog_modification(self) -> None:
        before_catalog = DEFAULT_MONSTER_CATALOG_JSON.read_text(encoding="utf-8")
        before_appendix = DEFAULT_MONSTER_APPENDIX_CATALOG_JSON.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "staging.json"
            path.write_text(
                json.dumps(self._make_staging_preview([self._make_staged_record()])),
                encoding="utf-8",
            )
            build_combat_projection(path)
            after_catalog = DEFAULT_MONSTER_CATALOG_JSON.read_text(encoding="utf-8")
            after_appendix = DEFAULT_MONSTER_APPENDIX_CATALOG_JSON.read_text(encoding="utf-8")
            self.assertEqual(before_catalog, after_catalog)
            self.assertEqual(before_appendix, after_appendix)

    def test_normalized_preview_files_not_modified(self) -> None:
        from app.monster_editor import DEFAULT_MANDBMASTER_PREVIEW_PATH, DEFAULT_MEGADUNGEON_PREVIEW_PATH

        before_mandb = DEFAULT_MANDBMASTER_PREVIEW_PATH.read_text(encoding="utf-8")
        before_mega = DEFAULT_MEGADUNGEON_PREVIEW_PATH.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "staging.json"
            path.write_text(
                json.dumps(self._make_staging_preview([self._make_staged_record()])),
                encoding="utf-8",
            )
            build_combat_projection(path)
            after_mandb = DEFAULT_MANDBMASTER_PREVIEW_PATH.read_text(encoding="utf-8")
            after_mega = DEFAULT_MEGADUNGEON_PREVIEW_PATH.read_text(encoding="utf-8")
            self.assertEqual(before_mandb, after_mandb)
            self.assertEqual(before_mega, after_mega)

    def test_staging_preview_not_modified(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "staging.json"
            content = json.dumps(self._make_staging_preview([self._make_staged_record()]))
            path.write_text(content, encoding="utf-8")
            build_combat_projection(path)
            after = path.read_text(encoding="utf-8")
            self.assertEqual(content, after)

    def test_report_includes_readiness_counts_and_no_live_catalog_warning(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "staging.json"
            path.write_text(
                json.dumps(self._make_staging_preview([self._make_staged_record()])),
                encoding="utf-8",
            )
            projection = build_combat_projection(path)
            report = format_report(projection)
            self.assertIn("Total staged records read: 1", report)
            self.assertIn("ready: 1", report)
            self.assertIn("WARNING: This is a non-live combat projection", report)
            self.assertIn("No master catalog was created", report)
            self.assertIn("Live catalog JSON was not modified", report)

    def test_write_combat_projection_creates_json_and_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "staging.json"
            path.write_text(
                json.dumps(self._make_staging_preview([self._make_staged_record()])),
                encoding="utf-8",
            )
            projection = build_combat_projection(path)
            json_path = Path(temp) / "out.json"
            report_path = Path(temp) / "out.txt"
            write_combat_projection(projection, json_path, report_path)
            self.assertTrue(json_path.exists())
            self.assertTrue(report_path.exists())
            loaded = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(loaded["record_count"], 1)
            self.assertIn("Total staged records read: 1", report_path.read_text(encoding="utf-8"))

    def test_malformed_staging_preview_fails_gracefully(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "staging.json"
            path.write_text("not json", encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                build_combat_projection(path)
            self.assertIn("not valid JSON", str(ctx.exception))

    def test_combat_tags_infer_conservatively(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "staging.json"
            record = self._make_staged_record(
                monster_type="undead",
                movement="Flying 120 ft.",
                special_attacks="Poison bite",
            )
            path.write_text(json.dumps(self._make_staging_preview([record])), encoding="utf-8")
            projection = build_combat_projection(path)
            p = projection["projections"][0]
            self.assertIn("undead", p["combat_tags"])
            self.assertIn("flying", p["combat_tags"])
            self.assertIn("poison", p["combat_tags"])

    def test_ac_type_unknown_for_unsafe_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "staging.json"
            record = self._make_staged_record(armor_class="-10")
            path.write_text(json.dumps(self._make_staging_preview([record])), encoding="utf-8")
            projection = build_combat_projection(path)
            p = projection["projections"][0]
            self.assertEqual(p["armor_class_type"], "unknown")
            self.assertEqual(p["armor_class_model"]["value"], -10)


if __name__ == "__main__":
    unittest.main()
