from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.monster_import_review import (
    build_candidate_rows,
    format_candidate_group,
    format_decision_block,
    get_decision,
    load_canonical_group_report,
    load_decisions,
    review_summary_text,
    save_decisions,
    set_decision,
)
from tools.importers.monster_manual_schema import (
    DEFAULT_MONSTER_APPENDIX_CATALOG_JSON,
    DEFAULT_MONSTER_CATALOG_JSON,
)


class MonsterImportReviewTests(unittest.TestCase):
    def _make_group(self, **kwargs: object) -> dict[str, object]:
        return {
            "candidate_group_id": kwargs.get("candidate_group_id", "cg_test"),
            "proposed_canonical_name": kwargs.get("proposed_canonical_name", "Test Monster"),
            "confidence": kwargs.get("confidence", "high"),
            "match_score": kwargs.get("match_score", 1.0),
            "match_reasons": kwargs.get("match_reasons", ["exact_name_match"]),
            "review_status": kwargs.get("review_status", "needs_review"),
            "user_decision": kwargs.get("user_decision", None),
            "notes": kwargs.get("notes", []),
            "records": kwargs.get(
                "records",
                [
                    {
                        "id": "a",
                        "display_name": "Test Monster",
                        "canonical_name": "Test Monster",
                        "source_id": "mandbmaster",
                        "source_title": "MandBmaster",
                        "source_page_start": 1,
                        "source_page_end": 2,
                        "armor_class": "5",
                        "hit_dice": "1",
                        "movement": "120",
                        "xp": "10",
                        "review_status": "mapped",
                    },
                    {
                        "id": "b",
                        "display_name": "Test Monster",
                        "canonical_name": "Test Monster",
                        "source_id": "megadungeon",
                        "source_title": "Megadungeon",
                        "source_page_start": 3,
                        "source_page_end": 4,
                        "armor_class": "6",
                        "hit_dice": "1",
                        "movement": "90",
                        "xp": "15",
                        "review_status": "mapped",
                    },
                ],
            ),
        }

    def _make_payload(self, groups: list[dict[str, object]] | None = None) -> dict[str, object]:
        return {
            "generated_at": "2026-01-01T00:00:00+00:00",
            "mandbmaster_preview": "mandbmaster_preview.json",
            "megadungeon_preview": "megadungeon_preview.json",
            "mandbmaster_record_count": 2,
            "megadungeon_record_count": 2,
            "total_candidate_groups": len(groups or []),
            "candidate_groups": groups or [],
        }

    def test_load_canonical_group_report_reads_valid_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "candidates.json"
            path.write_text(json.dumps(self._make_payload([self._make_group()])), encoding="utf-8")
            payload = load_canonical_group_report(path)
            self.assertEqual(payload["total_candidate_groups"], 1)
            self.assertEqual(payload["mandbmaster_record_count"], 2)

    def test_load_missing_report_fails_gracefully(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "missing.json"
            with self.assertRaises(FileNotFoundError) as ctx:
                load_canonical_group_report(path)
            self.assertIn("Canonical-group candidate report not found", str(ctx.exception))

    def test_load_malformed_json_fails_gracefully(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "candidates.json"
            path.write_text("not json", encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                load_canonical_group_report(path)
            self.assertIn("not valid JSON", str(ctx.exception))

    def test_load_report_missing_required_fields_fails_gracefully(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "candidates.json"
            path.write_text(json.dumps({"candidate_groups": []}), encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                load_canonical_group_report(path)
            self.assertIn("missing fields", str(ctx.exception))

    def test_load_report_with_non_list_candidate_groups_fails_gracefully(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "candidates.json"
            payload = self._make_payload()
            payload["candidate_groups"] = "not a list"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                load_canonical_group_report(path)
            self.assertIn("must contain a 'candidate_groups' list", str(ctx.exception))

    def test_build_candidate_rows(self) -> None:
        payload = self._make_payload(
            [
                self._make_group(confidence="high", proposed_canonical_name="Medusa"),
                self._make_group(confidence="low", proposed_canonical_name="Ant"),
            ]
        )
        rows = build_candidate_rows(payload)
        self.assertEqual(len(rows), 2)
        self.assertIn("[HIGH] Medusa", rows[0][0])
        self.assertIn("[LOW] Ant", rows[1][0])
        self.assertEqual(rows[0][1]["confidence"], "high")

    def test_format_candidate_group_shows_source_variants(self) -> None:
        group = self._make_group()
        text = format_candidate_group(group)
        self.assertIn("Canonical Group Candidate", text)
        self.assertIn("Proposed Name: Test Monster", text)
        self.assertIn("Source: MandBmaster", text)
        self.assertIn("Source: Megadungeon", text)
        self.assertIn("AC: 5", text)
        self.assertIn("AC: 6", text)
        self.assertIn("read-only, not merged", text)

    def test_format_candidate_group_includes_review_status_and_user_decision(self) -> None:
        group = self._make_group()
        text = format_candidate_group(group)
        self.assertIn("Review Status: needs_review", text)
        self.assertIn("User Decision: None", text)

    def test_review_summary_text(self) -> None:
        payload = self._make_payload(
            [
                self._make_group(confidence="high"),
                self._make_group(confidence="medium"),
                self._make_group(confidence="low"),
            ]
        )
        text = review_summary_text(payload)
        self.assertIn("Monster Import Canonical-Group Review", text)
        self.assertIn("Total candidate groups: 3", text)
        self.assertIn("High confidence: 1", text)
        self.assertIn("Medium confidence: 1", text)
        self.assertIn("Low confidence: 1", text)
        self.assertIn("Decisions are stored separately and do not merge records", text)

    def test_review_does_not_modify_live_catalog_json(self) -> None:
        before_catalog = DEFAULT_MONSTER_CATALOG_JSON.read_text(encoding="utf-8")
        before_appendix = DEFAULT_MONSTER_APPENDIX_CATALOG_JSON.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "candidates.json"
            path.write_text(json.dumps(self._make_payload([self._make_group()])), encoding="utf-8")
            load_canonical_group_report(path)
            build_candidate_rows(self._make_payload([self._make_group()]))
            format_candidate_group(self._make_group())
        after_catalog = DEFAULT_MONSTER_CATALOG_JSON.read_text(encoding="utf-8")
        after_appendix = DEFAULT_MONSTER_APPENDIX_CATALOG_JSON.read_text(encoding="utf-8")
        self.assertEqual(before_catalog, after_catalog)
        self.assertEqual(before_appendix, after_appendix)

    def test_no_master_catalog_file_created(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "candidates.json"
            path.write_text(json.dumps(self._make_payload([self._make_group()])), encoding="utf-8")
            payload = load_canonical_group_report(path)
            self.assertNotIn("master_catalog", payload)
            self.assertNotIn("merged_records", payload)

    def test_read_only_review_does_not_write_decisions(self) -> None:
        group = self._make_group(user_decision=None)
        format_candidate_group(group)
        self.assertIsNone(group["user_decision"])

    def test_missing_decision_file_loads_as_empty(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "decisions.json"
            decisions = load_decisions(path)
            self.assertEqual(decisions["decisions"], {})
            self.assertEqual(decisions["schema_version"], 1)

    def test_valid_decision_file_loads_correctly(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "decisions.json"
            data = {
                "schema_version": 1,
                "source_report": "candidates.json",
                "decisions": {
                    "cg_test": {
                        "decision": "approved",
                        "notes": "Looks correct",
                        "updated_at": "2026-01-01T00:00:00+00:00",
                        "reviewer": "local_user",
                    }
                },
            }
            path.write_text(json.dumps(data), encoding="utf-8")
            decisions = load_decisions(path)
            self.assertEqual(decisions["decisions"]["cg_test"]["decision"], "approved")
            self.assertEqual(decisions["decisions"]["cg_test"]["notes"], "Looks correct")

    def test_malformed_decision_file_fails_gracefully(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "decisions.json"
            path.write_text("not json", encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                load_decisions(path)
            self.assertIn("not valid JSON", str(ctx.exception))

    def test_decision_file_missing_decisions_object_fails_gracefully(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "decisions.json"
            path.write_text(json.dumps({"schema_version": 1}), encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                load_decisions(path)
            self.assertIn("must contain a 'decisions' object", str(ctx.exception))

    def test_saving_decision_creates_decision_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "decisions.json"
            decisions = load_decisions(path)
            set_decision(decisions, "cg_test", "approved", "Confirmed match")
            save_decisions(decisions, path)
            self.assertTrue(path.exists())
            loaded = load_decisions(path)
            self.assertEqual(loaded["decisions"]["cg_test"]["decision"], "approved")
            self.assertEqual(loaded["decisions"]["cg_test"]["notes"], "Confirmed match")

    def test_saving_updates_only_selected_group(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "decisions.json"
            decisions = load_decisions(path)
            set_decision(decisions, "cg_one", "approved", "first")
            set_decision(decisions, "cg_two", "rejected", "second")
            save_decisions(decisions, path)
            loaded = load_decisions(path)
            self.assertEqual(loaded["decisions"]["cg_one"]["decision"], "approved")
            self.assertEqual(loaded["decisions"]["cg_two"]["decision"], "rejected")
            set_decision(loaded, "cg_one", "needs_review", "changed")
            save_decisions(loaded, path)
            reloaded = load_decisions(path)
            self.assertEqual(reloaded["decisions"]["cg_one"]["decision"], "needs_review")
            self.assertEqual(reloaded["decisions"]["cg_two"]["decision"], "rejected")

    def test_notes_persist(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "decisions.json"
            decisions = load_decisions(path)
            set_decision(decisions, "cg_test", "approved", "Save these notes")
            save_decisions(decisions, path)
            loaded = load_decisions(path)
            self.assertEqual(loaded["decisions"]["cg_test"]["notes"], "Save these notes")

    def test_invalid_decision_value_is_rejected(self) -> None:
        decisions = load_decisions(Path("/nonexistent/path/decisions.json"))
        with self.assertRaises(ValueError) as ctx:
            set_decision(decisions, "cg_test", "maybe")
        self.assertIn("Invalid decision value", str(ctx.exception))

    def test_candidate_report_not_modified_by_saving_decisions(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            candidates_path = Path(temp) / "candidates.json"
            decisions_path = Path(temp) / "decisions.json"
            original_payload = self._make_payload([self._make_group()])
            candidates_path.write_text(json.dumps(original_payload), encoding="utf-8")
            payload = load_canonical_group_report(candidates_path)
            decisions = load_decisions(decisions_path)
            set_decision(decisions, "cg_test", "approved", "notes")
            save_decisions(decisions, decisions_path)
            after_payload = load_canonical_group_report(candidates_path)
            self.assertEqual(original_payload, after_payload)

    def test_build_candidate_rows_include_decision_status(self) -> None:
        payload = self._make_payload(
            [
                self._make_group(candidate_group_id="cg_approved"),
                self._make_group(candidate_group_id="cg_rejected"),
            ]
        )
        decisions = {
            "schema_version": 1,
            "source_report": "candidates.json",
            "decisions": {
                "cg_approved": {"decision": "approved"},
                "cg_rejected": {"decision": "rejected"},
            },
        }
        rows = build_candidate_rows(payload, decisions)
        self.assertIn("[APPROVED]", rows[0][0])
        self.assertIn("[REJECTED]", rows[1][0])

    def test_get_decision_returns_default_for_missing_group(self) -> None:
        decisions = {"decisions": {}}
        decision = get_decision(decisions, "missing")
        self.assertEqual(decision["decision"], "needs_review")
        self.assertEqual(decision["notes"], "")

    def test_format_decision_block(self) -> None:
        text = format_decision_block(
            {"decision": "approved", "notes": "OK", "updated_at": "2026-01-01", "reviewer": "local_user"}
        )
        self.assertIn("Decision: APPROVED", text)
        self.assertIn("Notes: OK", text)


if __name__ == "__main__":
    unittest.main()
