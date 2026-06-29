from __future__ import annotations

import json
import unittest
from pathlib import Path

from app.monster_classification import (
    ClassificationAffinities,
    ClassificationOptions,
    dropdown_values_for_field,
    load_classification_affinities,
    load_classification_options,
    validate_affinities_against_options,
)
from tools.importers.monster_classification_suggestions import (
    _missing_or_unknown,
    generate_suggestions,
    write_suggestions,
)
from tools.importers.monster_manual_schema import PROJECT_ROOT
from tools.report_table_inventory import (
    build_inventory,
    format_report,
    write_inventory,
)


DEFAULT_OPTIONS_JSON = PROJECT_ROOT / "data" / "tables" / "monster_classification_options.json"
DEFAULT_AFFINITIES_JSON = PROJECT_ROOT / "data" / "configs" / "monster_classification_affinities.json"
DEFAULT_MONSTER_CATALOG_JSON = PROJECT_ROOT / "data" / "catalogs" / "monsters" / "monster_catalog.json"
DEFAULT_MONSTER_APPENDIX_CATALOG_JSON = PROJECT_ROOT / "data" / "catalogs" / "monsters" / "monster_appendix_catalog.json"
MANDBMASTER_PREVIEW = PROJECT_ROOT / "data" / "import_reports" / "mandbmaster_normalized_monster_preview.json"
MEGADUNGEON_PREVIEW = PROJECT_ROOT / "data" / "import_reports" / "megadungeon_normalized_monster_preview.json"
STAGING_PREVIEW = PROJECT_ROOT / "data" / "import_reports" / "monster_corrected_staging_preview.json"


class TableInventoryTests(unittest.TestCase):
    def test_inventory_builds_without_errors(self) -> None:
        inventory = build_inventory()
        self.assertGreater(inventory["total_files"], 0)
        self.assertIn("domains", inventory)
        self.assertIn("by_domain", inventory)
        self.assertIsInstance(inventory["warnings"], list)

    def test_inventory_includes_classification_tables(self) -> None:
        inventory = build_inventory()
        files = [record["file"] for record in inventory["by_domain"].get("future classification tables", [])]
        self.assertIn("monster_classification_options.json", files)
        self.assertIn("monster_classification_affinities.json", files)

    def test_inventory_reports_required_domains(self) -> None:
        inventory = build_inventory()
        domains = inventory["domains"]
        for expected in (
            "character generation",
            "NPC generation",
            "settlement/location generation",
            "encounters/leads/adventure content",
            "inventory/equipment/resources",
            "interaction/dialogue/downtime text",
            "monster catalogs/import previews/review data",
            "source registry",
            "future classification tables",
        ):
            self.assertIn(expected, domains)

    def test_inventory_writes_outputs(self) -> None:
        report_json = PROJECT_ROOT / "data" / "import_reports" / "table_inventory_test.json"
        report_txt = PROJECT_ROOT / "data" / "import_reports" / "table_inventory_test_report.txt"
        try:
            write_inventory(json_path=report_json, txt_path=report_txt)
            self.assertTrue(report_json.exists())
            self.assertTrue(report_txt.exists())
            data = json.loads(report_json.read_text(encoding="utf-8"))
            self.assertIn("total_files", data)
            self.assertIn("by_domain", data)
            text = report_txt.read_text(encoding="utf-8")
            self.assertIn("Table Inventory Report", text)
        finally:
            report_json.unlink(missing_ok=True)
            report_txt.unlink(missing_ok=True)

    def test_inventory_format_report_is_human_readable(self) -> None:
        inventory = build_inventory()
        text = format_report(inventory)
        self.assertIn("Table Inventory Report", text)
        self.assertIn("Files scanned", text)
        self.assertIn("future classification tables", text.lower())


class ClassificationOptionsTests(unittest.TestCase):
    def test_options_load(self) -> None:
        options = load_classification_options()
        self.assertIsInstance(options, ClassificationOptions)
        self.assertGreater(len(options.keys()), 0)

    def test_required_domains_exist(self) -> None:
        options = load_classification_options()
        for field in ("monster_types", "environments", "terrains", "regions"):
            self.assertIn(field, options)
            self.assertGreater(len(options.get(field)), 0)

    def test_required_values_exist(self) -> None:
        options = load_classification_options()
        self.assertIn("undead", options.get("monster_types"))
        self.assertIn("amphibian", options.get("monster_types"))
        self.assertIn("aquatic", options.get("monster_types"))
        self.assertIn("extraplanar", options.get("monster_types"))
        self.assertIn("swamp", options.get("environments"))
        self.assertIn("underground", options.get("environments"))
        self.assertIn("graveyard", options.get("environments"))
        self.assertIn("marsh", options.get("terrains"))
        self.assertIn("aerial", options.get("terrains"))
        self.assertIn("grave-realm", options.get("regions"))

    def test_affinity_values_list(self) -> None:
        options = load_classification_options()
        values = options.get("affinity_values")
        for expected in ("always", "usually", "sometimes", "rarely", "never", "unknown"):
            self.assertIn(expected, values)

    def test_options_are_safe_for_table_loader(self) -> None:
        options = load_classification_options()
        for key, values in options._options.items():
            self.assertIsInstance(values, list)
            self.assertGreater(len(values), 0)
            for value in values:
                self.assertIsInstance(value, str)
                self.assertTrue(value.strip())


class ClassificationAffinitiesTests(unittest.TestCase):
    def test_affinities_load(self) -> None:
        affinities = load_classification_affinities()
        self.assertIsInstance(affinities, ClassificationAffinities)
        self.assertIn("undead", affinities.monster_type_affinities)

    def test_affinity_values_are_valid(self) -> None:
        warnings = validate_affinities_against_options()
        for warning in warnings:
            if "unknown affinity value" in warning:
                self.fail(f"Invalid affinity value: {warning}")

    def test_seeded_affinities_use_known_options(self) -> None:
        warnings = validate_affinities_against_options()
        bad_references = [
            w for w in warnings if "unknown" in w and "monster_type" not in w
        ]
        self.assertEqual(bad_references, [])

    def test_affinity_lookup(self) -> None:
        affinities = load_classification_affinities()
        self.assertEqual(affinities.get_affinity("undead", "environment", "graveyard"), "usually")
        self.assertEqual(affinities.get_affinity("aquatic", "environment", "aquatic"), "always")
        self.assertEqual(affinities.get_affinity("aerial", "terrain", "aerial"), "always")
        self.assertIsNone(affinities.get_affinity("undead", "environment", "forest"))

    def test_affinity_domains(self) -> None:
        affinities = load_classification_affinities()
        for monster_type, fields in affinities.monster_type_affinities.items():
            for field in fields:
                self.assertIn(field, ("environment", "terrain", "region"))


class DropdownValueTests(unittest.TestCase):
    def test_dropdown_defaults_to_unknown(self) -> None:
        values, selected = dropdown_values_for_field("environment", "")
        self.assertEqual(selected, "unknown")
        self.assertIn("unknown", values)

    def test_dropdown_selects_known_value(self) -> None:
        values, selected = dropdown_values_for_field("environment", "swamp")
        self.assertEqual(selected, "swamp")
        self.assertIn("swamp", values)

    def test_dropdown_preserves_unknown_value(self) -> None:
        values, selected = dropdown_values_for_field("environment", "cloud-top")
        self.assertEqual(selected, "cloud-top")
        self.assertIn("cloud-top", values)

    def test_dropdown_values_include_unknown(self) -> None:
        values, _ = dropdown_values_for_field("terrain", "")
        self.assertIn("unknown", values)
        self.assertTrue(all(isinstance(v, str) and v.strip() for v in values))

    def test_dropdown_for_monster_type(self) -> None:
        values, selected = dropdown_values_for_field("monster_type", "undead")
        self.assertEqual(selected, "undead")
        self.assertIn("undead", values)


class SuggestionToolTests(unittest.TestCase):
    def test_suggestions_generate_without_errors(self) -> None:
        suggestions = generate_suggestions()
        self.assertIn("record_count", suggestions)
        self.assertIn("total_suggestions", suggestions)
        self.assertIn("suggestions", suggestions)
        self.assertIsInstance(suggestions["suggestions"], list)

    def test_suggestions_do_not_overwrite_corrections(self) -> None:
        suggestions = generate_suggestions()
        for record in suggestions["suggestions"]:
            self.assertIn("record_id", record)
            self.assertIn("suggestions", record)
            for field, suggestion in record["suggestions"].items():
                self.assertIn("suggested_value", suggestion)
                self.assertIn("confidence", suggestion)
                self.assertIn("reason", suggestion)

    def test_suggestions_write_outputs(self) -> None:
        suggestions = generate_suggestions()
        json_path = PROJECT_ROOT / "data" / "import_reports" / "monster_classification_suggestions_test.json"
        report_path = PROJECT_ROOT / "data" / "import_reports" / "monster_classification_suggestions_test_report.txt"
        try:
            write_suggestions(suggestions, json_path=json_path, report_path=report_path)
            self.assertTrue(json_path.exists())
            self.assertTrue(report_path.exists())
            data = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertIn("total_suggestions", data)
            text = report_path.read_text(encoding="utf-8")
            self.assertIn("Monster Classification Suggestions Report", text)
        finally:
            json_path.unlink(missing_ok=True)
            report_path.unlink(missing_ok=True)

    def test_missing_or_unknown(self) -> None:
        self.assertTrue(_missing_or_unknown(None))
        self.assertTrue(_missing_or_unknown(""))
        self.assertTrue(_missing_or_unknown("unknown"))
        self.assertTrue(_missing_or_unknown("Unknown"))
        self.assertFalse(_missing_or_unknown("swamp"))
        self.assertFalse(_missing_or_unknown("forest"))


class SafetyTests(unittest.TestCase):
    def test_no_live_catalog_modification(self) -> None:
        before_catalog = DEFAULT_MONSTER_CATALOG_JSON.read_text(encoding="utf-8")
        before_appendix = DEFAULT_MONSTER_APPENDIX_CATALOG_JSON.read_text(encoding="utf-8")
        load_classification_options()
        load_classification_affinities()
        build_inventory()
        generate_suggestions()
        after_catalog = DEFAULT_MONSTER_CATALOG_JSON.read_text(encoding="utf-8")
        after_appendix = DEFAULT_MONSTER_APPENDIX_CATALOG_JSON.read_text(encoding="utf-8")
        self.assertEqual(before_catalog, after_catalog)
        self.assertEqual(before_appendix, after_appendix)

    def test_no_generated_preview_modification(self) -> None:
        before_staging = STAGING_PREVIEW.read_text(encoding="utf-8")
        if MANDBMASTER_PREVIEW.exists():
            before_mandbmaster = MANDBMASTER_PREVIEW.read_text(encoding="utf-8")
        else:
            before_mandbmaster = None
        if MEGADUNGEON_PREVIEW.exists():
            before_megadungeon = MEGADUNGEON_PREVIEW.read_text(encoding="utf-8")
        else:
            before_megadungeon = None
        load_classification_options()
        load_classification_affinities()
        build_inventory()
        generate_suggestions()
        after_staging = STAGING_PREVIEW.read_text(encoding="utf-8")
        self.assertEqual(before_staging, after_staging)
        if before_mandbmaster is not None:
            after_mandbmaster = MANDBMASTER_PREVIEW.read_text(encoding="utf-8")
            self.assertEqual(before_mandbmaster, after_mandbmaster)
        if before_megadungeon is not None:
            after_megadungeon = MEGADUNGEON_PREVIEW.read_text(encoding="utf-8")
            self.assertEqual(before_megadungeon, after_megadungeon)


if __name__ == "__main__":
    unittest.main()
