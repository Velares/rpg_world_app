from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.importers.add_bestiary_importer import import_add_bestiary
from tools.importers.monster_appendix_importer import import_monster_appendices
from tools.importers.monster_json_importer import import_monsters_from_json
from tools.importers.monster_manual_importer import import_monster_manual
from tools.importers.monster_manual_schema import (
    ADD_BESTIARY_SOURCE_ID,
    MONSTER_MANUAL_SOURCE_ID,
    resolve_registered_monster_source,
)
from tools.monster_import_status import build_status_report


class MonsterImportReadinessTests(unittest.TestCase):
    def test_resolve_registered_monster_source_rejects_inactive_without_override(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            registry_path = root / "source_registry.json"
            registry_path.write_text(
                json.dumps(
                    {
                        "sources": [
                            {
                                "source_id": "old_monster_source",
                                "title": "Old Monster Source",
                                "domain": "monsters",
                                "role": "legacy_content_source",
                                "status": "inactive",
                                "expected_path": "data/import_sources/old.pdf",
                                "file_required": False,
                                "importer_family": "monster_manual_pdf",
                                "priority": 1,
                                "notes": "Retired source.",
                                "license_or_usage_note": "Local only.",
                                "active_for_rules": False,
                                "active_for_content": True,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                resolve_registered_monster_source(
                    default_source_id="old_monster_source",
                    source_id="old_monster_source",
                    registry_path=registry_path,
                    project_root=root,
                )

    def test_manual_import_direct_path_override_keeps_registered_source_metadata(self):
        sample_pages = []
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pdf_path = root / "manual.pdf"
            pdf_path.write_bytes(b"%PDF-sample")
            output_path = root / "monster_catalog.json"
            report_path = root / "monster_report.txt"
            with patch(
                "tools.importers.monster_manual_importer.extract_pdf_pages",
                return_value=sample_pages,
            ):
                result = import_monster_manual(
                    pdf_path=pdf_path,
                    output_path=output_path,
                    report_path=report_path,
                    source_id=MONSTER_MANUAL_SOURCE_ID,
                )
        self.assertEqual(result.catalog["source_id"], MONSTER_MANUAL_SOURCE_ID)
        self.assertIn("Source path mode: direct override", result.report_text)

    def test_appendix_import_direct_path_override_keeps_registered_source_metadata(self):
        sample_pages = []
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pdf_path = root / "appendix.pdf"
            pdf_path.write_bytes(b"%PDF-sample")
            catalog_path = root / "monster_catalog.json"
            catalog_path.write_text(json.dumps({"monsters": []}), encoding="utf-8")
            output_path = root / "appendix_catalog.json"
            report_path = root / "appendix_report.txt"
            unmatched_path = root / "appendix_unmatched.txt"
            with patch(
                "tools.importers.monster_appendix_importer.extract_appendix_pages",
                return_value=sample_pages,
            ):
                result = import_monster_appendices(
                    pdf_path=pdf_path,
                    monster_catalog_path=catalog_path,
                    output_path=output_path,
                    report_path=report_path,
                    unmatched_review_path=unmatched_path,
                    source_id=MONSTER_MANUAL_SOURCE_ID,
                )
        self.assertEqual(result.catalog["source_id"], MONSTER_MANUAL_SOURCE_ID)
        self.assertIn("Source ID: mandbmaster_combined_monster_manual", result.report_text)

    def test_add_bestiary_missing_registered_source_fails_cleanly(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pdf_path = root / "missing.pdf"
            with self.assertRaises(FileNotFoundError) as context:
                import_add_bestiary(pdf_path=pdf_path, source_id=ADD_BESTIARY_SOURCE_ID)
        self.assertIn("adventures_dark_and_deep_bestiary", str(context.exception))

    def test_monster_import_status_report_lists_registered_sources_and_commands(self):
        report = build_status_report(
            Path(__file__).resolve().parents[1] / "data" / "source_registry.json",
            Path(__file__).resolve().parents[1],
        )
        self.assertIn("Monster Import Readiness", report)
        self.assertIn("mandbmaster_combined_monster_manual", report)
        self.assertIn("python tools/importers/monster_manual_importer.py", report)
        self.assertIn("python tools/import_add_bestiary.py", report)
        self.assertIn("python tools/importers/megadungeon_monster_importer.py --probe", report)

    def test_json_import_unknown_registry_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            json_path = root / "sample.json"
            json_path.write_text(json.dumps([{"name": "Ash Lurker", "size": "Medium"}]), encoding="utf-8")
            catalog_path = root / "monster_catalog.json"
            catalog_path.write_text(json.dumps({"monsters": []}), encoding="utf-8")
            with self.assertRaises(ValueError):
                import_monsters_from_json(
                    json_path,
                    catalog_path=catalog_path,
                    source_id="unknown_source_id",
                )


if __name__ == "__main__":
    unittest.main()
