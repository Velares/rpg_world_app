from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.importers.monster_canonical_group_candidates import (
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    REVIEW_STATUS_NEEDS_REVIEW,
    _build_candidate_groups,
    generate_canonical_group_candidates,
)
from tools.importers.monster_manual_schema import (
    DEFAULT_MONSTER_APPENDIX_CATALOG_JSON,
    DEFAULT_MONSTER_CATALOG_JSON,
)


def _make_record(
    *,
    record_id: str,
    display_name: str,
    source_id: str,
    source_title: str,
    **kwargs: object,
) -> dict[str, object]:
    return {
        "id": record_id,
        "canonical_name": display_name,
        "display_name": display_name,
        "source_id": source_id,
        "source_title": source_title,
        "source_page_start": kwargs.get("source_page_start", 1),
        "source_page_end": kwargs.get("source_page_end", 1),
        "armor_class": kwargs.get("armor_class", "5"),
        "hit_dice": kwargs.get("hit_dice", "1"),
        "movement": kwargs.get("movement", "120"),
        "xp": kwargs.get("xp", "10"),
        "review_status": kwargs.get("review_status", "mapped"),
    }


def _write_preview(path: Path, records: list[dict[str, object]]) -> None:
    payload = {
        "generated_at": "2026-01-01T00:00:00+00:00",
        "source_id": "test_source",
        "source_title": "Test Source",
        "record_count": len(records),
        "normalized_monsters": records,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


class MonsterCanonicalGroupCandidateTests(unittest.TestCase):
    def test_exact_name_match_is_high_confidence(self) -> None:
        left = _make_record(
            record_id="normalized.mandbmaster.skeleton",
            display_name="Skeleton",
            source_id="mandbmaster_combined_monster_manual",
            source_title="MandBmaster Combined Monster Manual",
        )
        right = _make_record(
            record_id="normalized.megadungeon.skeleton",
            display_name="Skeleton",
            source_id="megadungeon_monster_manual",
            source_title="Megadungeon Monster Manual",
        )
        groups = _build_candidate_groups([left], [right])
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["confidence"], CONFIDENCE_HIGH)
        self.assertIn("exact_name_match", groups[0]["match_reasons"])
        self.assertEqual(groups[0]["review_status"], REVIEW_STATUS_NEEDS_REVIEW)

    def test_case_punctuation_insensitive_match_is_high_confidence(self) -> None:
        left = _make_record(
            record_id="normalized.mandbmaster.skeleton",
            display_name="Skeleton",
            source_id="mandbmaster_combined_monster_manual",
            source_title="MandBmaster Combined Monster Manual",
        )
        right = _make_record(
            record_id="normalized.megadungeon.skeleton",
            display_name="SKELETON!",
            source_id="megadungeon_monster_manual",
            source_title="Megadungeon Monster Manual",
        )
        groups = _build_candidate_groups([left], [right])
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["confidence"], CONFIDENCE_HIGH)
        self.assertIn(
            "case_punctuation_spacing_insensitive_name_match",
            groups[0]["match_reasons"],
        )

    def test_singular_plural_variant_is_medium_confidence(self) -> None:
        left = _make_record(
            record_id="normalized.mandbmaster.goblin",
            display_name="Goblin",
            source_id="mandbmaster_combined_monster_manual",
            source_title="MandBmaster Combined Monster Manual",
        )
        right = _make_record(
            record_id="normalized.megadungeon.goblins",
            display_name="Goblins",
            source_id="megadungeon_monster_manual",
            source_title="Megadungeon Monster Manual",
        )
        groups = _build_candidate_groups([left], [right])
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["confidence"], CONFIDENCE_MEDIUM)
        self.assertIn("singular_plural_variant", groups[0]["match_reasons"])

    def test_parenthetical_variant_is_medium_confidence(self) -> None:
        left = _make_record(
            record_id="normalized.mandbmaster.medusa",
            display_name="Medusa",
            source_id="mandbmaster_combined_monster_manual",
            source_title="MandBmaster Combined Monster Manual",
        )
        right = _make_record(
            record_id="normalized.megadungeon.medusa_greater",
            display_name="Medusa (Greater)",
            source_id="megadungeon_monster_manual",
            source_title="Megadungeon Monster Manual",
        )
        groups = _build_candidate_groups([left], [right])
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["confidence"], CONFIDENCE_MEDIUM)
        self.assertIn("parenthetical_variant", groups[0]["match_reasons"])

    def test_field_similarity_can_improve_score_without_merge(self) -> None:
        left = _make_record(
            record_id="normalized.mandbmaster.fire_beetle",
            display_name="Fire Beetle",
            source_id="mandbmaster_combined_monster_manual",
            source_title="MandBmaster Combined Monster Manual",
            hit_dice="1",
        )
        right = _make_record(
            record_id="normalized.megadungeon.giant_fire_beetle",
            display_name="Giant Fire Beetle",
            source_id="megadungeon_monster_manual",
            source_title="Megadungeon Monster Manual",
            hit_dice="1",
        )
        groups = _build_candidate_groups([left], [right])
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["confidence"], CONFIDENCE_MEDIUM)
        self.assertIn("name_similarity_with_field_match", groups[0]["match_reasons"])
        self.assertIn("hit_dice", groups[0]["match_reasons"][1])
        self.assertEqual(len(groups[0]["records"]), 2)

    def test_records_from_different_sources_remain_distinct(self) -> None:
        left = _make_record(
            record_id="normalized.mandbmaster.skeleton",
            display_name="Skeleton",
            source_id="mandbmaster_combined_monster_manual",
            source_title="MandBmaster Combined Monster Manual",
            armor_class="7",
        )
        right = _make_record(
            record_id="normalized.megadungeon.skeleton",
            display_name="Skeleton",
            source_id="megadungeon_monster_manual",
            source_title="Megadungeon Monster Manual",
            armor_class="6",
        )
        groups = _build_candidate_groups([left], [right])
        self.assertEqual(len(groups[0]["records"]), 2)
        source_ids = {r["source_id"] for r in groups[0]["records"]}
        self.assertEqual(
            source_ids,
            {"mandbmaster_combined_monster_manual", "megadungeon_monster_manual"},
        )
        # Both original armor class values are preserved.
        acs = sorted(str(r["armor_class"]) for r in groups[0]["records"])
        self.assertEqual(acs, ["6", "7"])

    def test_candidate_group_has_review_status_and_user_decision(self) -> None:
        left = _make_record(
            record_id="normalized.mandbmaster.skeleton",
            display_name="Skeleton",
            source_id="mandbmaster_combined_monster_manual",
            source_title="MandBmaster Combined Monster Manual",
        )
        right = _make_record(
            record_id="normalized.megadungeon.skeleton",
            display_name="Skeleton",
            source_id="megadungeon_monster_manual",
            source_title="Megadungeon Monster Manual",
        )
        groups = _build_candidate_groups([left], [right])
        self.assertEqual(groups[0]["review_status"], REVIEW_STATUS_NEEDS_REVIEW)
        self.assertIsNone(groups[0]["user_decision"])
        self.assertIn("candidate_group_id", groups[0])
        self.assertIn("proposed_canonical_name", groups[0])

    def test_output_does_not_modify_live_catalog_json(self) -> None:
        before_catalog = DEFAULT_MONSTER_CATALOG_JSON.read_text(encoding="utf-8")
        before_appendix = DEFAULT_MONSTER_APPENDIX_CATALOG_JSON.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            left_preview = temp_root / "mandbmaster_preview.json"
            right_preview = temp_root / "megadungeon_preview.json"
            _write_preview(
                left_preview,
                [
                    _make_record(
                        record_id="normalized.mandbmaster.skeleton",
                        display_name="Skeleton",
                        source_id="mandbmaster_combined_monster_manual",
                        source_title="MandBmaster Combined Monster Manual",
                    )
                ],
            )
            _write_preview(
                right_preview,
                [
                    _make_record(
                        record_id="normalized.megadungeon.skeleton",
                        display_name="Skeleton",
                        source_id="megadungeon_monster_manual",
                        source_title="Megadungeon Monster Manual",
                    )
                ],
            )
            generate_canonical_group_candidates(
                mandbmaster_preview_path=left_preview,
                megadungeon_preview_path=right_preview,
                output_json_path=temp_root / "candidates.json",
                output_report_path=temp_root / "candidates_report.txt",
            )
        after_catalog = DEFAULT_MONSTER_CATALOG_JSON.read_text(encoding="utf-8")
        after_appendix = DEFAULT_MONSTER_APPENDIX_CATALOG_JSON.read_text(encoding="utf-8")
        self.assertEqual(before_catalog, after_catalog)
        self.assertEqual(before_appendix, after_appendix)

    def test_output_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            left_preview = temp_root / "mandbmaster_preview.json"
            right_preview = temp_root / "megadungeon_preview.json"
            _write_preview(
                left_preview,
                [
                    _make_record(
                        record_id="normalized.mandbmaster.skeleton",
                        display_name="Skeleton",
                        source_id="mandbmaster_combined_monster_manual",
                        source_title="MandBmaster Combined Monster Manual",
                    ),
                    _make_record(
                        record_id="normalized.mandbmaster.zombie",
                        display_name="Zombie",
                        source_id="mandbmaster_combined_monster_manual",
                        source_title="MandBmaster Combined Monster Manual",
                    ),
                ],
            )
            _write_preview(
                right_preview,
                [
                    _make_record(
                        record_id="normalized.megadungeon.skeleton",
                        display_name="Skeleton",
                        source_id="megadungeon_monster_manual",
                        source_title="Megadungeon Monster Manual",
                    ),
                    _make_record(
                        record_id="normalized.megadungeon.zombie",
                        display_name="Zombie",
                        source_id="megadungeon_monster_manual",
                        source_title="Megadungeon Monster Manual",
                    ),
                ],
            )
            out1 = temp_root / "candidates1.json"
            out2 = temp_root / "candidates2.json"
            generate_canonical_group_candidates(
                mandbmaster_preview_path=left_preview,
                megadungeon_preview_path=right_preview,
                output_json_path=out1,
                output_report_path=temp_root / "candidates1_report.txt",
            )
            generate_canonical_group_candidates(
                mandbmaster_preview_path=left_preview,
                megadungeon_preview_path=right_preview,
                output_json_path=out2,
                output_report_path=temp_root / "candidates2_report.txt",
            )
            payload1 = json.loads(out1.read_text(encoding="utf-8"))
            payload2 = json.loads(out2.read_text(encoding="utf-8"))
            self.assertEqual(payload1["candidate_groups"], payload2["candidate_groups"])
            group_ids1 = [g["candidate_group_id"] for g in payload1["candidate_groups"]]
            self.assertEqual(group_ids1, ["cg_skeleton", "cg_zombie"])

    def test_no_master_catalog_created(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            left_preview = temp_root / "mandbmaster_preview.json"
            right_preview = temp_root / "megadungeon_preview.json"
            _write_preview(
                left_preview,
                [
                    _make_record(
                        record_id="normalized.mandbmaster.skeleton",
                        display_name="Skeleton",
                        source_id="mandbmaster_combined_monster_manual",
                        source_title="MandBmaster Combined Monster Manual",
                    )
                ],
            )
            _write_preview(
                right_preview,
                [
                    _make_record(
                        record_id="normalized.megadungeon.skeleton",
                        display_name="Skeleton",
                        source_id="megadungeon_monster_manual",
                        source_title="Megadungeon Monster Manual",
                    )
                ],
            )
            output_json = temp_root / "candidates.json"
            generate_canonical_group_candidates(
                mandbmaster_preview_path=left_preview,
                megadungeon_preview_path=right_preview,
                output_json_path=output_json,
                output_report_path=temp_root / "candidates_report.txt",
            )
            payload = json.loads(output_json.read_text(encoding="utf-8"))
            self.assertNotIn("master_catalog", payload)
            self.assertNotIn("merged_records", payload)
            for group in payload["candidate_groups"]:
                self.assertEqual(len(group["records"]), 2)

    def test_reads_both_normalized_preview_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            left_preview = temp_root / "mandbmaster_preview.json"
            right_preview = temp_root / "megadungeon_preview.json"
            _write_preview(
                left_preview,
                [
                    _make_record(
                        record_id="normalized.mandbmaster.skeleton",
                        display_name="Skeleton",
                        source_id="mandbmaster_combined_monster_manual",
                        source_title="MandBmaster Combined Monster Manual",
                    )
                ],
            )
            _write_preview(
                right_preview,
                [
                    _make_record(
                        record_id="normalized.megadungeon.skeleton",
                        display_name="Skeleton",
                        source_id="megadungeon_monster_manual",
                        source_title="Megadungeon Monster Manual",
                    )
                ],
            )
            output_json = temp_root / "candidates.json"
            payload, _ = generate_canonical_group_candidates(
                mandbmaster_preview_path=left_preview,
                megadungeon_preview_path=right_preview,
                output_json_path=output_json,
                output_report_path=temp_root / "candidates_report.txt",
            )
            self.assertEqual(payload["mandbmaster_record_count"], 1)
            self.assertEqual(payload["megadungeon_record_count"], 1)


if __name__ == "__main__":
    unittest.main()
