from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from app.source_registry import (
    DEFAULT_SOURCE_REGISTRY_PATH,
    build_source_validation_report,
    load_source_registry_payload,
    validate_source_registry,
)
from tools.validate_sources import main as validate_sources_main


def sample_entry(**overrides: object) -> dict[str, object]:
    entry: dict[str, object] = {
        "source_id": "advanced_labyrinth_lord",
        "title": "Advanced Labyrinth Lord",
        "domain": "rules_references",
        "role": "primary_rules_baseline",
        "status": "active",
        "expected_path": "data/import_sources/advanced_labyrinth_lord.pdf",
        "file_required": False,
        "importer_family": "rules_reference",
        "priority": 10,
        "notes": "Primary durable rules baseline.",
        "license_or_usage_note": "Local reference only.",
        "active_for_rules": True,
        "active_for_content": False,
    }
    entry.update(overrides)
    return entry


class SourceRegistryTests(unittest.TestCase):
    def write_registry(self, root: Path, payload: dict[str, object]) -> Path:
        path = root / "source_registry.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return path

    def test_default_registry_loads_and_preserves_titles_and_paths(self):
        payload = load_source_registry_payload(DEFAULT_SOURCE_REGISTRY_PATH)
        entries = payload["sources"]
        self.assertTrue(entries)
        advanced = next(
            entry for entry in entries if entry["source_id"] == "advanced_labyrinth_lord"
        )
        self.assertEqual(advanced["title"], "Advanced Labyrinth Lord")
        self.assertIn("data/import_sources/", advanced["expected_path"])

    def test_duplicate_source_id_detection(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            registry = self.write_registry(
                root,
                {"sources": [sample_entry(), sample_entry(title="Duplicate")]},
            )
            result = validate_source_registry(registry, project_root=root)
        self.assertTrue(any("duplicate source_id" in item for item in result.errors))

    def test_missing_required_field_detection(self):
        invalid = sample_entry()
        invalid.pop("domain")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            registry = self.write_registry(root, {"sources": [invalid]})
            result = validate_source_registry(registry, project_root=root)
        self.assertTrue(any("missing required fields: domain" in item for item in result.errors))

    def test_unknown_domain_detection(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            registry = self.write_registry(
                root,
                {"sources": [sample_entry(domain="unknown_domain")]},
            )
            result = validate_source_registry(registry, project_root=root)
        self.assertTrue(any("unknown domain" in item for item in result.errors))

    def test_inactive_missing_source_does_not_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            registry = self.write_registry(
                root,
                {
                    "sources": [
                        sample_entry(
                            source_id="removed_source",
                            status="inactive",
                            active_for_rules=False,
                            active_for_content=False,
                        )
                    ]
                },
            )
            result = validate_source_registry(registry, project_root=root)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])

    def test_optional_missing_source_warns_but_does_not_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            registry = self.write_registry(root, {"sources": [sample_entry()]})
            result = validate_source_registry(registry, project_root=root)
        self.assertEqual(result.errors, [])
        self.assertTrue(any("active source file not found" in item for item in result.warnings))

    def test_required_active_missing_source_is_an_error(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            registry = self.write_registry(
                root,
                {"sources": [sample_entry(file_required=True)]},
            )
            result = validate_source_registry(registry, project_root=root)
        self.assertTrue(any("required active source file missing" in item for item in result.errors))

    def test_present_file_is_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            pdf_path = root / "data" / "import_sources" / "advanced_labyrinth_lord.pdf"
            pdf_path.parent.mkdir(parents=True, exist_ok=True)
            pdf_path.write_bytes(b"%PDF-1.4")
            registry = self.write_registry(root, {"sources": [sample_entry()]})
            result = validate_source_registry(registry, project_root=root)
        self.assertEqual(result.present_files, 1)
        self.assertEqual(result.missing_expected_files, 0)

    def test_report_summary_groups_by_domain_and_status(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            registry = self.write_registry(
                root,
                {
                    "sources": [
                        sample_entry(source_id="rules_a"),
                        sample_entry(
                            source_id="monster_a",
                            domain="monsters",
                            role="stable_monster_import_source",
                            expected_path="data/import_sources/mandbmaster.pdf",
                            active_for_rules=False,
                            active_for_content=True,
                        ),
                        sample_entry(
                            source_id="placeholder_a",
                            domain="spells",
                            role="future_domain_placeholder",
                            status="placeholder",
                            active_for_rules=False,
                            active_for_content=False,
                        ),
                    ]
                },
            )
            result = validate_source_registry(registry, project_root=root)
            report = build_source_validation_report(result)
        self.assertIn("rules_references: 1", report)
        self.assertIn("monsters: 1", report)
        self.assertIn("spells: 1", report)
        self.assertIn("active: 2", report)
        self.assertIn("placeholder: 1", report)

    def test_path_validation_does_not_require_committed_pdfs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            registry = self.write_registry(
                root,
                {
                    "sources": [
                        sample_entry(
                            source_id="future_magic_items",
                            domain="magic_items",
                            role="future_domain_placeholder",
                            status="placeholder",
                            expected_path="data/import_sources/magic_items/<filename>.pdf",
                            active_for_rules=False,
                            active_for_content=False,
                        )
                    ]
                },
            )
            result = validate_source_registry(registry, project_root=root)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.warnings, [])

    def test_future_importer_domains_are_accepted_and_cli_returns_zero_without_pdfs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            registry = self.write_registry(
                root,
                {
                    "sources": [
                        sample_entry(
                            source_id="future_modules",
                            domain="modules_keyed_locations",
                            role="future_domain_placeholder",
                            status="placeholder",
                            expected_path="data/import_sources/modules_keyed_locations/<filename>.pdf",
                            active_for_rules=False,
                            active_for_content=False,
                        )
                    ]
                },
            )
            exit_code = validate_sources_main(
                ["--registry", str(registry), "--root", str(root)]
            )
        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
