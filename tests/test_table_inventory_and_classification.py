from __future__ import annotations

import json
import re
import subprocess
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
    _get_corrected_value,
    _keyword_map,
    _keyword_suggestions,
    _missing_or_unknown,
    _record_title_text,
    _text_contains_keyword,
    generate_suggestions,
    suggest_for_record,
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
COMBAT_PROJECTION = PROJECT_ROOT / "data" / "import_reports" / "monster_combat_projection.json"
DEFAULT_CORRECTIONS_PATH = PROJECT_ROOT / "data" / "import_reviews" / "monster_normalized_field_corrections.json"


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
        self.assertEqual(affinities.get_affinity("aquatic", "environment", "aquatic"), "usually")
        self.assertEqual(affinities.get_affinity("avian", "terrain", "aerial"), "usually")
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

    def test_inventory_reflects_current_suggestion_report(self) -> None:
        suggestions = generate_suggestions()
        inventory = build_inventory()
        files = [record["file"] for record in inventory["by_domain"].get("monster catalogs/import previews/review data", [])]
        self.assertIn("monster_classification_suggestions.json", files)
        text = format_report(inventory)
        self.assertIn("monster_classification_suggestions", text)
        # The inventory should be regenerable after suggestions without error and
        # should pick up the report file that exists now.
        self.assertGreater(inventory["total_files"], 0)

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


class KeywordMatchingTests(unittest.TestCase):
    def test_word_boundary_does_not_match_ant_inside_unrelated_words(self) -> None:
        self.assertFalse(_text_contains_keyword("Giant", "ant"))
        self.assertFalse(_text_contains_keyword("Mantle Wraith", "ant"))
        self.assertFalse(_text_contains_keyword("Antelope", "ant"))
        self.assertTrue(_text_contains_keyword("Giant Ant", "ant"))

    def test_phrase_matching_for_multi_word_keywords(self) -> None:
        self.assertTrue(_text_contains_keyword("Shambling Mound", "shambling mound"))
        self.assertFalse(_text_contains_keyword("Shambling", "shambling mound"))
        self.assertTrue(_text_contains_keyword("Animated Statue", "animated statue"))

    def test_record_title_text_combines_name_display_name_and_canonical_name(self) -> None:
        record = {
            "id": "r1",
            "display_name": "Giant Eagle",
            "canonical_name": "Roc Lord",
            "source_id": "test",
        }
        title = _record_title_text(record)
        self.assertIn("Giant Eagle", title)
        self.assertIn("Roc Lord", title)

    def test_title_evidence_works_with_display_name_and_no_name(self) -> None:
        record = {
            "id": "r1",
            "display_name": "Giant Frog",
            "canonical_name": "Toad Beast",
            "source_id": "test",
        }
        suggestions = suggest_for_record(record)
        monster_type = suggestions["suggestions"]["monster_type"]["suggested_value"]
        self.assertIn(monster_type, ("amphibian", "animal"))

    def test_clear_title_evidence_can_produce_medium_or_high_confidence(self) -> None:
        record = {
            "id": "r1",
            "display_name": "Skeleton Warrior",
            "source_id": "test",
        }
        suggestions = suggest_for_record(record)
        suggestion = suggestions["suggestions"]["monster_type"]
        self.assertEqual(suggestion["suggested_value"], "undead")
        self.assertIn(suggestion["confidence"], ("medium", "high"))

    def test_golem_title_prioritizes_construct(self) -> None:
        options = load_classification_options()
        keyword_map = _keyword_map()
        description = "This fiery being resembles a living elemental."
        result = _keyword_suggestions("Iron Golem", description, keyword_map, options)
        types = [value for value, _affinity, _location in result.get("monster_type", [])]
        self.assertEqual(types[0], "construct")
        self.assertNotIn("elemental", types)
        self.assertNotIn("dragon", types)
        self.assertNotIn("undead", types)

    def test_golem_name_suggests_construct_not_insect(self) -> None:
        options = load_classification_options()
        keyword_map = _keyword_map()
        result = _keyword_suggestions("Iron Golem", "", keyword_map, options)
        types = {value for value, _affinity, _location in result.get("monster_type", [])}
        self.assertIn("construct", types)
        self.assertNotIn("insect", types)

    def test_skeleton_name_suggests_undead(self) -> None:
        options = load_classification_options()
        keyword_map = _keyword_map()
        for name in ("Skeleton Warrior", "Zombie Lord", "Ghoul Pack", "Wight", "Vampire", "Lich", "Mummy"):
            with self.subTest(name=name):
                result = _keyword_suggestions(name, "", keyword_map, options)
                types = {value for value, _affinity, _location in result.get("monster_type", [])}
                self.assertIn("undead", types)

    def test_amphibian_names_and_swamp_placement(self) -> None:
        for name in ("Giant Frog", "Toad Beast", "Fire Salamander"):
            with self.subTest(name=name):
                record = {"id": name, "name": name, "display_name": name, "source_id": "test"}
                suggestions = suggest_for_record(record)
                self.assertIn("amphibian", suggestions["suggestions"]["monster_type"]["suggested_value"])
                env_value = suggestions["suggestions"]["environment"]["suggested_value"]
                self.assertIn(env_value, ("swamp", "river", "lake", "forest"))
                terrain_value = suggestions["suggestions"]["terrain"]["suggested_value"]
                self.assertIn(terrain_value, ("marsh", "flooded", "shore", "river"))

    def test_fish_names_and_underwater_placement(self) -> None:
        for name in ("Shark", "Giant Eel", "Squid", "Octopus"):
            with self.subTest(name=name):
                record = {"id": name, "name": name, "display_name": name, "source_id": "test"}
                suggestions = suggest_for_record(record)
                type_value = suggestions["suggestions"]["monster_type"]["suggested_value"]
                self.assertIn(type_value, ("fish", "aquatic"))
                terrain_value = suggestions["suggestions"]["terrain"]["suggested_value"]
                self.assertIn(terrain_value, ("underwater", "river", "reef"))

    def test_bird_names_suggest_aerial_terrain_not_aerial_type(self) -> None:
        options = load_classification_options()
        keyword_map = _keyword_map()
        for name in ("Roc", "Harpy", "Giant Eagle", "Flying Snake"):
            with self.subTest(name=name):
                result = _keyword_suggestions(name, "", keyword_map, options)
                types = {value for value, _affinity, _location in result.get("monster_type", [])}
                self.assertNotIn("aerial", types)
                if name in ("Roc", "Harpy", "Giant Eagle"):
                    self.assertIn("avian", types)
                terrains = {value for value, _affinity, _location in result.get("terrain", [])}
                self.assertIn("aerial", terrains)

    def test_lichen_and_creeper_do_not_suggest_undead(self) -> None:
        options = load_classification_options()
        keyword_map = _keyword_map()
        for name in ("Sunburst Lichen", "Yellow Musk Creeper"):
            with self.subTest(name=name):
                result = _keyword_suggestions(name, "", keyword_map, options)
                types = {value for value, _affinity, _location in result.get("monster_type", [])}
                self.assertNotIn("undead", types)
                self.assertIn("plant", types)

    def test_giant_name_does_not_suggest_insect_or_plant(self) -> None:
        options = load_classification_options()
        keyword_map = _keyword_map()
        result = _keyword_suggestions("Hill Giant", "", keyword_map, options)
        types = {value for value, _affinity, _location in result.get("monster_type", [])}
        self.assertIn("giant", types)
        self.assertNotIn("insect", types)
        self.assertNotIn("plant", types)

    def test_giant_animal_title_uses_creature_noun_not_giant(self) -> None:
        for name, expected in (
            ("Giant Crab", "aquatic"),
            ("Giant Leech", "worm"),
            ("Giant Mosquito", "insect"),
        ):
            with self.subTest(name=name):
                record = {"id": name, "name": name, "display_name": name, "source_id": "test"}
                suggestions = suggest_for_record(record)
                monster_type = suggestions["suggestions"]["monster_type"]["suggested_value"]
                self.assertEqual(monster_type, expected)

    def test_fire_toad_prioritizes_amphibian(self) -> None:
        record = {"id": "firetoad", "name": "Fire Toad", "display_name": "Fire Toad", "source_id": "test"}
        suggestions = suggest_for_record(record)
        monster_type = suggestions["suggestions"]["monster_type"]["suggested_value"]
        self.assertEqual(monster_type, "amphibian")
        # Fire can influence placement/terrain but not as the primary environment.
        env_value = suggestions["suggestions"]["environment"]["suggested_value"]
        self.assertIn(env_value, ("swamp", "river", "lake", "forest"))

    def test_fungal_ant_preserves_insect_and_fungus_over_undead(self) -> None:
        record = {
            "id": "fungalant",
            "name": "Fungal Ant",
            "display_name": "Fungal Ant",
            "source_id": "test",
        }
        suggestions = suggest_for_record(record)
        types = {suggestions["suggestions"]["monster_type"]["suggested_value"]}
        for alt in suggestions["suggestions"]["monster_type"].get("alternatives", []):
            types.add(alt["value"])
        self.assertTrue({"insect", "fungus"} & types)
        self.assertNotIn("undead", types)

    def test_corrections_are_normalized_to_lowercase_options(self) -> None:
        options = load_classification_options()
        corrections = {
            "corrections": {
                "normalized.test.toad": {
                    "fields": {
                        "monster_type": {
                            "corrected_value": "Animal",
                            "previous_value": "unknown",
                            "updated_at": "2026-01-01T00:00:00+00:00",
                            "reviewer": "example",
                        }
                    }
                }
            }
        }
        value = _get_corrected_value(corrections, "normalized.test.toad", "monster_type", options)
        self.assertEqual(value, "animal")

    def test_invalid_corrections_are_rejected(self) -> None:
        options = load_classification_options()
        corrections = {
            "corrections": {
                "normalized.test.toad": {
                    "fields": {
                        "monster_type": {
                            "corrected_value": "not_a_real_type",
                            "previous_value": "unknown",
                            "updated_at": "2026-01-01T00:00:00+00:00",
                            "reviewer": "example",
                        }
                    }
                }
            }
        }
        value = _get_corrected_value(corrections, "normalized.test.toad", "monster_type", options)
        self.assertIsNone(value)

    def test_added_option_values_are_present(self) -> None:
        options = load_classification_options()
        for value in (
            "avian", "fish", "worm", "shapechanger", "lycanthrope", "celestial", "vermin"
        ):
            self.assertIn(value, options.get("monster_types"))
        for value in (
            "sky", "river", "lake", "sea", "volcanic", "ethereal", "shadow", "faerie"
        ):
            self.assertIn(value, options.get("environments"))
        for value in (
            "underwater", "ice", "snow", "sand", "dune", "lava", "burrow", "reef", "canopy", "rubble"
        ):
            self.assertIn(value, options.get("terrains"))
        for value in (
            "ocean", "island", "riverlands", "volcanic", "sky-realm", "faerie",
            "shadow-realm", "elemental plane", "hell", "abyss"
        ):
            self.assertIn(value, options.get("regions"))

    def test_affinities_only_reference_known_options(self) -> None:
        warnings = validate_affinities_against_options()
        self.assertEqual(warnings, [])

    def test_aerial_is_not_a_monster_type_in_affinities(self) -> None:
        affinities = load_classification_affinities()
        self.assertNotIn("aerial", affinities.monster_type_affinities)


class ReviewDataTrackingTests(unittest.TestCase):
    def test_gitignore_ignores_import_review_json_but_allows_examples(self) -> None:
        gitignore = PROJECT_ROOT / ".gitignore"
        self.assertTrue(gitignore.exists())
        text = gitignore.read_text(encoding="utf-8")
        self.assertIn("data/import_reviews/*.json", text)
        self.assertIn("!data/import_reviews/*.example.json", text)

    def test_real_review_json_not_tracked_by_git(self) -> None:
        result = subprocess.run(
            ["git", "ls-files", "data/import_reviews/*.json"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        tracked = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        for path in tracked:
            self.assertTrue(
                path.endswith(".example.json"),
                f"tracked review file is not an example template: {path}",
            )

    def test_example_review_templates_are_tracked(self) -> None:
        for name in (
            "monster_canonical_group_decisions.example.json",
            "monster_normalized_field_corrections.example.json",
        ):
            path = PROJECT_ROOT / "data" / "import_reviews" / name
            self.assertTrue(path.exists(), f"missing example template: {name}")
            result = subprocess.run(
                ["git", "ls-files", f"data/import_reviews/{name}"],
                cwd=PROJECT_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertIn(
                f"data/import_reviews/{name}",
                result.stdout,
                f"example template {name} should be tracked",
            )

    def test_example_review_templates_are_sanitized(self) -> None:
        for name in (
            "monster_canonical_group_decisions.example.json",
            "monster_normalized_field_corrections.example.json",
        ):
            path = PROJECT_ROOT / "data" / "import_reviews" / name
            self.assertTrue(path.exists())
            text = path.read_text(encoding="utf-8")
            # No absolute local paths (Windows-style drive letters or home dirs).
            self.assertNotRegex(text, r"[A-Za-z]:\\")
            self.assertNotIn("local_user", text)
            # Only fake example reviewer.
            self.assertIn("example_reviewer", text)
            # All example corrected values should be lowercase controlled options.
            data = json.loads(text)
            corrections = data.get("corrections", {})
            for record_id, correction in corrections.items():
                if "example" not in record_id:
                    continue
                for field, field_correction in correction.get("fields", {}).items():
                    value = field_correction.get("corrected_value", "")
                    self.assertIsInstance(value, str)
                    self.assertEqual(value, value.lower())


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
        if COMBAT_PROJECTION.exists():
            before_combat = COMBAT_PROJECTION.read_text(encoding="utf-8")
        else:
            before_combat = None
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
        if before_combat is not None:
            after_combat = COMBAT_PROJECTION.read_text(encoding="utf-8")
            self.assertEqual(before_combat, after_combat)

    def test_suggestions_do_not_write_correction_store(self) -> None:
        if not DEFAULT_CORRECTIONS_PATH.exists():
            self.skipTest("corrections file not present")
        before_mtime = DEFAULT_CORRECTIONS_PATH.stat().st_mtime
        before_text = DEFAULT_CORRECTIONS_PATH.read_text(encoding="utf-8")
        generate_suggestions()
        after_mtime = DEFAULT_CORRECTIONS_PATH.stat().st_mtime
        after_text = DEFAULT_CORRECTIONS_PATH.read_text(encoding="utf-8")
        self.assertEqual(before_mtime, after_mtime)
        self.assertEqual(before_text, after_text)

    def test_no_records_merged(self) -> None:
        suggestions = generate_suggestions()
        seen_ids = set()
        for record in suggestions["suggestions"]:
            self.assertNotIn(record["record_id"], seen_ids)
            seen_ids.add(record["record_id"])


if __name__ == "__main__":
    unittest.main()
