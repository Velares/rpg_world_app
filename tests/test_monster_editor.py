from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.monster_editor import (
    build_normalized_monster_rows,
    format_normalized_monster,
    load_all_normalized_previews,
    load_normalized_preview,
    review_summary_text,
)
from tools.importers.monster_manual_schema import (
    DEFAULT_MONSTER_APPENDIX_CATALOG_JSON,
    DEFAULT_MONSTER_CATALOG_JSON,
)


class MonsterEditorTests(unittest.TestCase):
    def _make_record(self, **kwargs: object) -> dict[str, object]:
        return {
            "id": kwargs.get("id", "normalized.test.goblin"),
            "canonical_name": kwargs.get("canonical_name", "Goblin"),
            "display_name": kwargs.get("display_name", "Goblin"),
            "source_id": kwargs.get("source_id", "test_source"),
            "source_title": kwargs.get("source_title", "Test Source"),
            "source_file": kwargs.get("source_file", "test.pdf"),
            "source_page_start": kwargs.get("source_page_start", 1),
            "source_page_end": kwargs.get("source_page_end", 1),
            "source_entry_id": kwargs.get("source_entry_id", "goblin"),
            "source_slug": kwargs.get("source_slug", "goblin"),
            "armor_class": kwargs.get("armor_class", "6"),
            "hit_dice": kwargs.get("hit_dice", "1-1"),
            "movement": kwargs.get("movement", "60 ft."),
            "attacks": kwargs.get("attacks", "1"),
            "damage": kwargs.get("damage", "1d6"),
            "special_attacks": kwargs.get("special_attacks", None),
            "special_defenses": kwargs.get("special_defenses", None),
            "save": kwargs.get("save", "F0"),
            "morale": kwargs.get("morale", "7"),
            "alignment": kwargs.get("alignment", "Chaotic"),
            "intelligence": kwargs.get("intelligence", "Average"),
            "size": kwargs.get("size", "Small"),
            "monster_type": kwargs.get("monster_type", "humanoid"),
            "category": kwargs.get("category", None),
            "environment": kwargs.get("environment", None),
            "terrain": kwargs.get("terrain", None),
            "region": kwargs.get("region", None),
            "number_appearing": kwargs.get("number_appearing", "2d4"),
            "treasure": kwargs.get("treasure", "None"),
            "xp": kwargs.get("xp", "10"),
            "challenge": kwargs.get("challenge", None),
            "level": kwargs.get("level", None),
            "description": kwargs.get("description", None),
            "raw_stat_block": kwargs.get("raw_stat_block", "AC 6, HD 1-1"),
            "raw_text": kwargs.get("raw_text", "Goblin\nAC 6"),
            "normalized_fields": kwargs.get(
                "normalized_fields",
                [
                    "id",
                    "canonical_name",
                    "display_name",
                    "source_id",
                    "source_title",
                    "armor_class",
                    "hit_dice",
                    "movement",
                    "attacks",
                    "damage",
                    "save",
                    "morale",
                    "alignment",
                    "number_appearing",
                    "treasure",
                    "xp",
                    "raw_stat_block",
                    "raw_text",
                ],
            ),
            "missing_fields": kwargs.get("missing_fields", ["category", "environment"]),
            "placeholder_fields": kwargs.get(
                "placeholder_fields", ["category", "environment"]
            ),
            "mapping_confidence": kwargs.get(
                "mapping_confidence",
                {
                    "armor_class": "high",
                    "hit_dice": "high",
                    "movement": "medium",
                    "category": "missing",
                },
            ),
            "review_status": kwargs.get("review_status", "mapped_with_placeholders"),
            "review_notes": kwargs.get("review_notes", []),
            "user_corrections": kwargs.get("user_corrections", {}),
        }

    def _make_preview(
        self, records: list[dict[str, object]], source_id: str = "test_source"
    ) -> dict[str, object]:
        return {
            "generated_at": "2026-01-01T00:00:00+00:00",
            "source_id": source_id,
            "source_title": "Test Source",
            "source_file": "test.pdf",
            "record_count": len(records),
            "review_status_counts": {},
            "normalized_monsters": records,
        }

    def test_loads_mandbmaster_normalized_preview(self) -> None:
        from app.monster_editor import DEFAULT_MANDBMASTER_PREVIEW_PATH

        self.assertTrue(DEFAULT_MANDBMASTER_PREVIEW_PATH.exists())
        payload = load_normalized_preview(DEFAULT_MANDBMASTER_PREVIEW_PATH)
        self.assertIn("normalized_monsters", payload)
        self.assertGreater(payload["record_count"], 0)
        self.assertEqual(payload["source_id"], "mandbmaster_combined_monster_manual")

    def test_loads_megadungeon_normalized_preview(self) -> None:
        from app.monster_editor import DEFAULT_MEGADUNGEON_PREVIEW_PATH

        self.assertTrue(DEFAULT_MEGADUNGEON_PREVIEW_PATH.exists())
        payload = load_normalized_preview(DEFAULT_MEGADUNGEON_PREVIEW_PATH)
        self.assertIn("normalized_monsters", payload)
        self.assertGreater(payload["record_count"], 0)
        self.assertEqual(payload["source_id"], "megadungeon_monster_manual")

    def test_combines_records_without_overwriting_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path_a = Path(temp) / "a.json"
            path_b = Path(temp) / "b.json"
            path_a.write_text(
                json.dumps(self._make_preview([self._make_record(id="a.1")])),
                encoding="utf-8",
            )
            path_b.write_text(
                json.dumps(
                    self._make_preview(
                        [
                            self._make_record(id="a.1"),
                            self._make_record(id="b.1"),
                        ]
                    )
                ),
                encoding="utf-8",
            )
            records = load_all_normalized_previews([path_a, path_b])
            ids = [record["id"] for _metadata, record in records]
            self.assertEqual(ids.count("a.1"), 2)
            self.assertEqual(ids.count("b.1"), 1)

    def test_preserves_source_variants_separately(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path_a = Path(temp) / "a.json"
            path_b = Path(temp) / "b.json"
            path_a.write_text(
                json.dumps(
                    self._make_preview(
                        [self._make_record(id="goblin", source_id="source_a")],
                        source_id="source_a",
                    )
                ),
                encoding="utf-8",
            )
            path_b.write_text(
                json.dumps(
                    self._make_preview(
                        [self._make_record(id="goblin", source_id="source_b")],
                        source_id="source_b",
                    )
                ),
                encoding="utf-8",
            )
            records = load_all_normalized_previews([path_a, path_b])
            source_ids = [metadata["source_id"] for metadata, _record in records]
            self.assertIn("source_a", source_ids)
            self.assertIn("source_b", source_ids)

    def test_builds_display_rows_with_source_name_review_status_and_stats(self) -> None:
        records = [
            ({"source_id": "source_a", "source_title": "A"}, self._make_record()),
        ]
        rows = build_normalized_monster_rows(records)
        self.assertEqual(len(rows), 1)
        label = rows[0][0]
        self.assertIn("source_a", label)
        self.assertIn("Goblin", label)
        self.assertIn("mapped_with_placeholders", label)
        self.assertIn("2 missing", label)
        self.assertIn("2 placeholders", label)

    def test_extracts_missing_and_placeholder_fields(self) -> None:
        text = format_normalized_monster(
            {"source_id": "test", "source_title": "Test"}, self._make_record()
        )
        self.assertIn("category: <missing> [MISSING]", text)
        self.assertIn("environment: <missing> [MISSING]", text)
        self.assertIn("Missing fields: 2", text)
        self.assertIn("Placeholder fields: 2", text)

    def test_highlights_low_confidence_fields(self) -> None:
        text = format_normalized_monster(
            {"source_id": "test", "source_title": "Test"}, self._make_record()
        )
        self.assertIn("movement: 60 ft. (medium)", text)

    def test_handles_missing_report_file_gracefully(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "missing.json"
            with self.assertRaises(FileNotFoundError) as ctx:
                load_normalized_preview(path)
            self.assertIn("Normalized monster preview not found", str(ctx.exception))

    def test_handles_malformed_report_file_gracefully(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "bad.json"
            path.write_text("not json", encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                load_normalized_preview(path)
            self.assertIn("not valid JSON", str(ctx.exception))

    def test_handles_missing_required_fields_gracefully(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "incomplete.json"
            path.write_text(json.dumps({"generated_at": "now"}), encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                load_normalized_preview(path)
            self.assertIn("missing fields", str(ctx.exception))

    def test_no_live_catalog_modification(self) -> None:
        before_catalog = DEFAULT_MONSTER_CATALOG_JSON.read_text(encoding="utf-8")
        before_appendix = DEFAULT_MONSTER_APPENDIX_CATALOG_JSON.read_text(encoding="utf-8")
        load_all_normalized_previews()
        build_normalized_monster_rows([])
        review_summary_text([])
        after_catalog = DEFAULT_MONSTER_CATALOG_JSON.read_text(encoding="utf-8")
        after_appendix = DEFAULT_MONSTER_APPENDIX_CATALOG_JSON.read_text(encoding="utf-8")
        self.assertEqual(before_catalog, after_catalog)
        self.assertEqual(before_appendix, after_appendix)

    def test_no_master_catalog_created(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "preview.json"
            path.write_text(json.dumps(self._make_preview([self._make_record()])), encoding="utf-8")
            payload = load_normalized_preview(path)
            self.assertNotIn("master_catalog", payload)
            self.assertNotIn("merged_records", payload)

    def test_review_summary_text(self) -> None:
        records = [
            ({"source_id": "source_a"}, self._make_record(review_status="mapped")),
            ({"source_id": "source_b"}, self._make_record(review_status="needs_review")),
        ]
        text = review_summary_text(records)
        self.assertIn("Total records: 2", text)
        self.assertIn("source_a: 1", text)
        self.assertIn("source_b: 1", text)
        self.assertIn("mapped: 1", text)
        self.assertIn("needs_review: 1", text)


if __name__ == "__main__":
    unittest.main()
