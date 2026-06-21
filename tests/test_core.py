import json
import random
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.calendar import age_band, calendar_date
from app.database import Database
from app.characters import BONUS_NAMES, CharacterFactory
from app.character_profiles import CharacterProfileGenerator
from app.checks import DIFFICULTIES
from app.dice import morale_check, reaction_roll, roll
from app.exporters import (
    export_character_text,
    export_event_log_text,
    export_world_summary,
)
from app.game_state import GameState
from app.gui import (
    ADVENTURE_MODE,
    DEFAULT_GUI_MODE,
    TOWN_MODE,
    action_is_enabled,
    action_check_labels,
    format_world_recap,
    mode_gameplay_labels,
    mode_sidebar_labels,
    shared_action_labels,
)
from app.inventory import InventoryCatalog
from app.key_npcs import KEY_NPC_THRESHOLD, RELATIONSHIP_STATES
from app.leads import add_lead
from app.generators.npc_generator import NPCGenerator
from app.generators.settlement_generator import SettlementGenerator
from app.models import InventoryItem, PlayerState
from app.name_generator import NameDataError, NameGenerator
from app.table_loader import TableLoader
from app.timeline import (
    PROMINENT_NPC_THRESHOLD,
    format_summary_timeline,
    format_verbose_timeline,
)
from tools.clean_names import clean_name_file, find_raw_name_file
from tools.scrub_names import is_suspicious_name, scrub_name_file


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "data" / "tables"


class DiceTests(unittest.TestCase):
    def test_supported_formulas_stay_in_bounds(self):
        rng = random.Random(9)
        cases = {
            "1d4": (1, 4),
            "2d6+2": (4, 14),
            "1d8-1": (0, 7),
            "1d10": (1, 10),
            "1d12": (1, 12),
            "1d20": (1, 20),
            "1d30": (1, 30),
        }
        for formula, bounds in cases.items():
            for _ in range(20):
                self.assertTrue(bounds[0] <= roll(formula, rng) <= bounds[1])

    def test_invalid_formulas_raise(self):
        for formula in ("d6", "1d7", "0d6", "2d6++1", "sword"):
            with self.assertRaises(ValueError):
                roll(formula)

    def test_reaction_and_morale(self):
        rng = random.Random(2)
        self.assertIsInstance(reaction_roll(rng), str)
        self.assertIsInstance(morale_check(7, rng), bool)


class NameTests(unittest.TestCase):
    def test_cleanup_removes_blanks_duplicates_sorts_and_title_cases(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            raw = root / "raw_names.txt"
            cleaned = root / "nested" / "names.txt"
            raw.write_bytes(
                b"  alice  \nBOB\n\nAlice\nmary jane\ninvalid-\xff-name\n"
            )
            count = clean_name_file(raw, cleaned)
            self.assertEqual(count, 4)
            self.assertEqual(
                cleaned.read_text(encoding="utf-8").splitlines(),
                ["Alice", "Bob", "Invalid--Name", "Mary Jane"],
            )

    def test_cleanup_missing_input_reports_without_crashing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = clean_name_file(root / "missing.txt", root / "output.txt")
            self.assertIsNone(result)
            self.assertFalse((root / "output.txt").exists())

    def test_cleanup_supports_current_and_legacy_raw_filenames(self):
        with tempfile.TemporaryDirectory() as temp:
            names_dir = Path(temp)
            legacy = names_dir / "raw_first_names.txt"
            legacy.write_text("Legacy\n", encoding="utf-8")
            self.assertEqual(
                find_raw_name_file(
                    names_dir, ("firstnames.txt", "raw_first_names.txt")
                ),
                legacy,
            )
            current = names_dir / "firstnames.txt"
            current.write_text("Current\n", encoding="utf-8")
            self.assertEqual(
                find_raw_name_file(
                    names_dir, ("firstnames.txt", "raw_first_names.txt")
                ),
                current,
            )

    def test_name_generator_produces_first_last_full_and_lists(self):
        with tempfile.TemporaryDirectory() as temp:
            names_dir = Path(temp)
            (names_dir / "first_names.txt").write_text(
                "Asha\nBram\n", encoding="utf-8"
            )
            (names_dir / "last_names.txt").write_text(
                "Crow\nSalt\n", encoding="utf-8"
            )
            generator = NameGenerator(names_dir, random.Random(3))
            self.assertIn(generator.first_name(), {"Asha", "Bram"})
            self.assertIn(generator.last_name(), {"Crow", "Salt"})
            first, last = generator.full_name().split()
            self.assertIn(first, {"Asha", "Bram"})
            self.assertIn(last, {"Crow", "Salt"})
            names = generator.full_names(5)
            self.assertEqual(len(names), 5)
            self.assertTrue(all(len(name.split()) == 2 for name in names))

    def test_name_generator_caches_files_and_handles_missing_data(self):
        with tempfile.TemporaryDirectory() as temp:
            names_dir = Path(temp)
            first_path = names_dir / "first_names.txt"
            last_path = names_dir / "last_names.txt"
            first_path.write_text("Original\n", encoding="utf-8")
            last_path.write_text("Surname\n", encoding="utf-8")
            generator = NameGenerator(names_dir, random.Random(1))
            first_path.write_text("Changed\n", encoding="utf-8")
            self.assertEqual(generator.first_name(), "Original")

            fallback = NameGenerator(
                names_dir / "absent",
                random.Random(1),
                fallback_first_names=["Fallback"],
                fallback_last_names=["Name"],
            )
            self.assertEqual(fallback.full_name(), "Fallback Name")
            empty = NameGenerator(names_dir / "also_absent", random.Random(1))
            with self.assertRaises(NameDataError):
                empty.first_name()

    def test_name_generator_shares_cache_and_invalidates_changed_files(self):
        with tempfile.TemporaryDirectory() as temp:
            names_dir = Path(temp)
            first_path = names_dir / "first_names.txt"
            last_path = names_dir / "last_names.txt"
            first_path.write_text("Asha\n", encoding="utf-8")
            last_path.write_text("Crow\n", encoding="utf-8")
            first = NameGenerator(names_dir, random.Random(1))
            second = NameGenerator(names_dir, random.Random(2))
            self.assertIs(first._first_names, second._first_names)
            self.assertIs(first._last_names, second._last_names)

            first_path.write_text("Bramble\n", encoding="utf-8")
            refreshed = NameGenerator(names_dir, random.Random(3))
            self.assertEqual(refreshed.first_name(), "Bramble")
            self.assertIsNot(first._first_names, refreshed._first_names)

    def test_empty_cleaned_name_files_use_fallbacks_with_warnings(self):
        with tempfile.TemporaryDirectory() as temp:
            names_dir = Path(temp)
            (names_dir / "first_names.txt").write_text("", encoding="utf-8")
            (names_dir / "last_names.txt").write_text("\n", encoding="utf-8")
            generator = NameGenerator(
                names_dir,
                random.Random(1),
                fallback_first_names=["Fallback"],
                fallback_last_names=["Traveler"],
            )
            self.assertEqual(generator.full_name(), "Fallback Traveler")
            self.assertEqual(len(generator.warnings), 2)
            self.assertTrue(all("is empty" in item for item in generator.warnings))

    def test_npc_generator_uses_cleaned_text_names(self):
        with tempfile.TemporaryDirectory() as temp:
            names_dir = Path(temp)
            (names_dir / "first_names.txt").write_text("Textfirst\n", encoding="utf-8")
            (names_dir / "last_names.txt").write_text("Textlast\n", encoding="utf-8")
            rng = random.Random(7)
            tables = TableLoader(TABLES)
            generator = NameGenerator(names_dir, rng)
            locations = SettlementGenerator(tables, rng).generate().important_locations
            npcs = NPCGenerator(tables, rng, generator).generate(locations, 3)
            self.assertTrue(all(npc.name == "Textfirst Textlast" or " the " in npc.name for npc in npcs))
            self.assertTrue(npcs[0].name.startswith("Textfirst Textlast"))

    def test_scrubber_removes_corruption_and_preserves_valid_unicode(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "names.txt"
            path.write_text(
                "José\nÅsa\nMüller\nBroken\ufffdName\nFranÃ§ois\nM├ller\n",
                encoding="utf-8",
            )
            result = scrub_name_file(path)
            self.assertEqual(result, (3, 3))
            self.assertEqual(
                path.read_text(encoding="utf-8").splitlines(),
                ["José", "Åsa", "Müller"],
            )

    def test_scrubber_detects_controls_and_handles_missing_file(self):
        self.assertTrue(is_suspicious_name("Bad\x00Name"))
        self.assertFalse(is_suspicious_name("D'Arcy-Søren"))
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "missing.txt"
            self.assertIsNone(scrub_name_file(path))
            self.assertFalse(path.with_suffix(".txt.tmp").exists())


class InventoryTests(unittest.TestCase):
    def test_inventory_items_add_stack_and_remove_quantities(self):
        player = PlayerState(inventory=[])
        rope = InventoryItem(
            item_key="rope",
            name="Coil of Rope",
            category="Tool",
            quantity=2,
            description="Useful for climbing and retreat.",
            tags=["climbing"],
            tradeable=True,
        )
        added = player.add_inventory_item(rope)
        self.assertEqual(added.quantity, 2)
        player.add_inventory_item(rope, quantity=3)
        self.assertEqual(player.inventory_item("rope").quantity, 5)
        self.assertEqual(player.remove_inventory_item("Coil of Rope", 2), 2)
        self.assertEqual(player.inventory_item("rope").quantity, 3)
        self.assertEqual(player.remove_inventory_item("rope", 99), 3)
        self.assertIsNone(player.inventory_item("rope"))
        self.assertEqual(player.remove_inventory_item("missing"), 0)
        with self.assertRaises(ValueError):
            player.add_inventory_item(rope, quantity=0)

    def test_item_catalog_loads_class_specific_starting_inventory(self):
        loader = TableLoader(TABLES)
        catalog = InventoryCatalog(loader)
        items = catalog.starting_inventory("Ranger")
        by_key = {item.item_key: item for item in items}
        self.assertEqual(
            set(by_key),
            {"bedroll", "flint_steel", "blade", "field_kit"},
        )
        self.assertTrue(by_key["blade"].equipped)
        self.assertEqual(by_key["field_kit"].category, "Tool")
        self.assertTrue(all(item.quantity > 0 for item in items))
        for definition in CharacterFactory(loader).classes():
            class_items = catalog.starting_inventory(definition.class_name)
            self.assertGreaterEqual(len(class_items), 4, definition.class_name)

    def test_item_table_validation_filters_bad_entries_and_references(self):
        with tempfile.TemporaryDirectory() as temp:
            table_dir = Path(temp)
            (table_dir / "item_tables.json").write_text(
                json.dumps(
                    {
                        "item_definitions": [
                            {
                                "item_key": "valid",
                                "name": "Valid Item",
                                "category": "Tool",
                                "tags": ["test"],
                            },
                            {
                                "item_key": "bad",
                                "name": "Bad Item",
                                "category": "Spell",
                            },
                        ],
                        "common_loadout": [
                            {"item_key": "valid", "quantity": 2},
                            {"item_key": "missing", "quantity": 1},
                        ],
                        "class_loadouts": [
                            {
                                "class_name": "Explorer",
                                "items": [{"item_key": "valid", "quantity": 1}],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            loader = TableLoader(table_dir)
            self.assertEqual(
                [item["item_key"] for item in loader.get("item_tables", "item_definitions")],
                ["valid"],
            )
            self.assertEqual(
                loader.get("item_tables", "common_loadout"),
                [{"item_key": "valid", "quantity": 2}],
            )
            self.assertTrue(
                any(
                    "supported category" in warning
                    for warning in loader.warnings
                )
            )
            self.assertTrue(
                any("references unknown item 'missing'" in warning for warning in loader.warnings)
            )


class WorldTests(unittest.TestCase):
    def make_state(self, folder: Path, seed: int = 1) -> GameState:
        return GameState(
            TableLoader(TABLES),
            Database(folder / "worlds.db"),
            random.Random(seed),
        )

    def test_json_tables_are_valid_and_nonempty(self):
        for path in TABLES.glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            self.assertIsInstance(data, dict)
            self.assertTrue(data)
            for values in data.values():
                self.assertIsInstance(values, list)
                self.assertTrue(values)
        self.assertEqual(TableLoader(TABLES).warnings, [])

    def test_interaction_tables_load_expected_categories(self):
        loader = TableLoader(TABLES)
        self.assertTrue(loader.get("interaction_tables", "npc_dialogue_warning"))
        self.assertTrue(loader.get("interaction_tables", "encounter_approach_trade"))
        self.assertTrue(loader.get("interaction_tables", "check_success_additions"))

    def test_downtime_tables_load_expected_task_definitions(self):
        loader = TableLoader(TABLES)
        tasks = loader.get("downtime_tables", "tasks")
        self.assertTrue(any(task["task_key"] == "train_skill" for task in tasks))
        self.assertTrue(any(task["task_key"] == "recover_from_injury" for task in tasks))

    def test_generate_new_region_accepts_text_seed_and_records_it(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 1)
            world = state.generate_new_region("gloam-harbor")
            self.assertEqual(world.generation_seed, "gloam-harbor")
            self.assertEqual(state.active_seed, "gloam-harbor")
            state.close()

    def test_same_seed_generates_same_key_world_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            state_a = self.make_state(Path(temp), 2)
            state_b = self.make_state(Path(temp), 999)
            try:
                world_a = state_a.generate_new_region("shared-seed")
                world_b = state_b.generate_new_region("shared-seed")
                self.assertEqual(world_a.settlement.name, world_b.settlement.name)
                self.assertEqual(
                    [npc.name for npc in world_a.npcs[:3]],
                    [npc.name for npc in world_b.npcs[:3]],
                )
                self.assertEqual(
                    [location.name for location in world_a.settlement.important_locations[:3]],
                    [location.name for location in world_b.settlement.important_locations[:3]],
                )
                self.assertEqual(world_a.dungeon.name, world_b.dungeon.name)
                self.assertEqual(world_a.wilderness.name, world_b.wilderness.name)
                self.assertEqual(world_a.adventure_hook.major_goal, world_b.adventure_hook.major_goal)
            finally:
                state_a.close()
                state_b.close()

    def test_different_seeds_generally_change_world_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 3)
            try:
                first = state.generate_new_region("first-seed")
                second = state.generate_new_region("second-seed")
                key_fields_a = (
                    first.settlement.name,
                    first.npcs[0].name,
                    first.dungeon.name,
                    first.wilderness.name,
                    first.adventure_hook.major_goal,
                )
                key_fields_b = (
                    second.settlement.name,
                    second.npcs[0].name,
                    second.dungeon.name,
                    second.wilderness.name,
                    second.adventure_hook.major_goal,
                )
                self.assertNotEqual(key_fields_a, key_fields_b)
            finally:
                state.close()

    def test_older_save_without_seed_loads_safely(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 4)
            try:
                world = state.generate_new_region("legacy-check")
                data = world.to_dict()
                data.pop("generation_seed", None)
                restored = type(world).from_dict(data)
                self.assertIsNone(restored.generation_seed)
            finally:
                state.close()

    def test_older_save_without_lead_records_restores_open_leads(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 41)
            try:
                world = state.generate_new_region("legacy-leads")
                data = world.to_dict()
                data["player_state"].pop("lead_records", None)
                data["player_state"]["leads"] = [
                    "Speak with Eurie Prela at The Market.",
                    "Investigate the drowned knight rumor.",
                ]
                restored = type(world).from_dict(data)
                self.assertEqual(
                    restored.player_state.leads,
                    [
                        "Speak with Eurie Prela at The Market.",
                        "Investigate the drowned knight rumor.",
                    ],
                )
                self.assertEqual(len(restored.player_state.lead_records), 2)
                self.assertEqual(
                    restored.player_state.lead_records[0].suggested_action,
                    "Speak with Eurie Prela at The Market.",
                )
            finally:
                state.close()

    def test_table_loader_filters_bad_entries_and_deduplicates_warnings(self):
        with tempfile.TemporaryDirectory() as temp:
            table_dir = Path(temp)
            (table_dir / "custom.json").write_text(
                json.dumps(
                    {
                        "results": [
                            " usable ",
                            "",
                            12,
                            {"value": " weighted ", "weight": 2},
                            {"value": "bad weight", "weight": 0},
                            {"weight": 1},
                        ],
                        "empty": [],
                    }
                ),
                encoding="utf-8",
            )
            loader = TableLoader(table_dir)
            self.assertEqual(
                loader.get("custom", "results"),
                ["usable", {"value": "weighted", "weight": 2}],
            )
            before = len(loader.warnings)
            loader.get("custom", "missing")
            loader.get("custom", "missing")
            self.assertEqual(len(loader.warnings), before + 1)
            report = loader.validation_report()
            self.assertIn("custom.json:results[1]", report)
            self.assertIn("custom.json:empty must be a non-empty list", report)
            self.assertIn("Missing table: custom.missing", report)

    def test_table_loader_choose_supports_single_entry_tables(self):
        with tempfile.TemporaryDirectory() as temp:
            table_dir = Path(temp)
            (table_dir / "custom.json").write_text(
                json.dumps({"results": ["only result"]}),
                encoding="utf-8",
            )
            loader = TableLoader(table_dir)
            rng = random.Random(5)
            self.assertEqual(loader.get("custom", "results"), ["only result"])
            self.assertEqual(loader.choose("custom", "results", rng), "only result")

    def test_table_loader_choose_supports_short_tables_without_d30_assumptions(self):
        with tempfile.TemporaryDirectory() as temp:
            table_dir = Path(temp)
            values = ["one", "two", "three"]
            (table_dir / "custom.json").write_text(
                json.dumps({"results": values}),
                encoding="utf-8",
            )
            loader = TableLoader(table_dir)
            rng = random.Random(7)
            seen = {loader.choose("custom", "results", rng) for _ in range(200)}
            self.assertEqual(seen, set(values))

    def test_table_loader_choose_supports_tables_larger_than_thirty(self):
        with tempfile.TemporaryDirectory() as temp:
            table_dir = Path(temp)
            values = [f"result_{index}" for index in range(40)]
            (table_dir / "custom.json").write_text(
                json.dumps({"results": values}),
                encoding="utf-8",
            )
            loader = TableLoader(table_dir)
            rng = random.Random(9)
            seen = {loader.choose("custom", "results", rng) for _ in range(500)}
            self.assertIn("result_39", seen)
            self.assertTrue(seen.issubset(set(values)))

    def test_table_loader_choose_honors_weighted_entries_larger_than_thirty(self):
        with tempfile.TemporaryDirectory() as temp:
            table_dir = Path(temp)
            values = [{"value": f"common_{index}", "weight": 1} for index in range(35)]
            values.append({"value": "very_rare_but_weighted", "weight": 500})
            (table_dir / "custom.json").write_text(
                json.dumps({"results": values}),
                encoding="utf-8",
            )
            loader = TableLoader(table_dir)
            rng = random.Random(11)
            results = [loader.choose("custom", "results", rng) for _ in range(100)]
            self.assertGreater(results.count("very_rare_but_weighted"), 60)
            self.assertTrue(all(isinstance(item, str) for item in results))

    def test_table_loader_uses_safe_fallback_for_unusable_entries(self):
        with tempfile.TemporaryDirectory() as temp:
            table_dir = Path(temp)
            (table_dir / "settlement_tables.json").write_text(
                json.dumps({"settlement_names_prefix": [""], "settlement_names_suffix": ["Rest"]}),
                encoding="utf-8",
            )
            loader = TableLoader(table_dir)
            self.assertEqual(loader.get("settlement_tables", "settlement_names_prefix"), ["Gloam"])
            self.assertTrue(
                any(
                    "settlement_tables.json:settlement_names_prefix has no usable entries"
                    in warning
                    for warning in loader.warnings
                )
            )

    def test_malformed_downtime_tables_use_safe_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            table_dir = Path(temp)
            (table_dir / "downtime_tables.json").write_text(
                json.dumps(
                    {
                        "tasks": [
                            {
                                "task_key": "broken",
                                "name": "",
                                "category": "study",
                                "default_duration_days": 0,
                                "allowed_contexts": [],
                                "progress_text": "",
                                "completion_text": "",
                                "complication_text": "",
                                "tags": [],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            loader = TableLoader(table_dir)
            tasks = loader.get("downtime_tables", "tasks")
            self.assertEqual(tasks[0]["task_key"], "recover_from_injury")
            self.assertTrue(
                any("downtime_tables.json:tasks[0]" in warning for warning in loader.warnings)
            )

    def test_invalid_downtime_outcomes_are_filtered_without_dropping_task(self):
        with tempfile.TemporaryDirectory() as temp:
            table_dir = Path(temp)
            (table_dir / "downtime_tables.json").write_text(
                json.dumps(
                    {
                        "tasks": [
                            {
                                "task_key": "test_task",
                                "name": "Test Task",
                                "category": "study",
                                "description": "A valid task with bad optional outcomes.",
                                "default_duration_days": 2,
                                "allowed_contexts": ["town"],
                                "progress_text": "{task_name}: progress.",
                                "completion_text": "{task_name}: complete.",
                                "complication_text": "{task_name}: complication.",
                                "tags": ["test"],
                                "progress_outcomes": [{"kind": "lead"}],
                                "completion_outcomes": "bad",
                                "complication_outcomes": [
                                    {
                                        "kind": "inventory",
                                        "text": "Broken inventory reward.",
                                        "item_key": "",
                                        "item_name": "Bad",
                                        "item_category": "Quest",
                                        "quantity": 0,
                                        "tags": []
                                    }
                                ]
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            loader = TableLoader(table_dir)
            tasks = loader.get("downtime_tables", "tasks")
            self.assertEqual(tasks[0]["task_key"], "test_task")
            self.assertEqual(tasks[0]["progress_outcomes"], [])
            self.assertEqual(tasks[0]["completion_outcomes"], [])
            self.assertEqual(tasks[0]["complication_outcomes"], [])
            self.assertTrue(
                any("progress_outcomes[0]" in warning for warning in loader.warnings)
            )
            self.assertTrue(
                any(".completion_outcomes must be a list" in warning for warning in loader.warnings)
            )

    def test_invalid_class_data_uses_structural_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            table_dir = Path(temp)
            (table_dir / "class_tables.json").write_text(
                json.dumps(
                    {
                        "backgrounds": ["Wanderer"],
                        "classes": [
                            {
                                "class_name": "Broken",
                                "role_description": "Missing most required fields.",
                                "bonuses": {},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            loader = TableLoader(table_dir)
            classes = CharacterFactory(loader).classes()
            self.assertEqual(classes[0].class_name, "Explorer")
            self.assertEqual(set(classes[0].bonuses), set(BONUS_NAMES))
            self.assertTrue(
                any("class_tables.json:classes[0]" in item for item in loader.warnings)
            )

    def test_player_profile_generator_uses_json_tables(self):
        with tempfile.TemporaryDirectory() as temp:
            table_dir = Path(temp)
            expected = {
                "origins": "Origin from JSON.",
                "formative_events": "Event from JSON.",
                "personality_traits": "Trait from JSON.",
                "ideals": "Ideal from JSON.",
                "bonds": "Bond from JSON.",
                "flaws": "Flaw from JSON.",
            }
            (table_dir / "player_background_tables.json").write_text(
                json.dumps({key: [value] for key, value in expected.items()}),
                encoding="utf-8",
            )
            profile = CharacterProfileGenerator(
                TableLoader(table_dir), random.Random(1)
            ).generate()
            self.assertEqual(profile.origin_detail, expected["origins"])
            self.assertEqual(profile.formative_event, expected["formative_events"])
            self.assertEqual(profile.personality_trait, expected["personality_traits"])
            self.assertEqual(profile.ideal, expected["ideals"])
            self.assertEqual(profile.bond, expected["bonds"])
            self.assertEqual(profile.flaw, expected["flaws"])

    def test_player_profile_table_validation_and_fallbacks(self):
        with tempfile.TemporaryDirectory() as temp:
            table_dir = Path(temp)
            (table_dir / "player_background_tables.json").write_text(
                json.dumps(
                    {
                        "origins": [""],
                        "formative_events": [12],
                        "personality_traits": [],
                    }
                ),
                encoding="utf-8",
            )
            loader = TableLoader(table_dir)
            profile = CharacterProfileGenerator(loader, random.Random(1)).generate()
            self.assertTrue(profile.origin_detail)
            self.assertTrue(profile.formative_event)
            self.assertTrue(profile.personality_trait)
            self.assertTrue(profile.ideal)
            self.assertTrue(profile.bond)
            self.assertTrue(profile.flaw)
            self.assertTrue(
                any(
                    "player_background_tables.json:origins" in warning
                    for warning in loader.warnings
                )
            )
            self.assertTrue(
                any(
                    "Missing required table: player_background_tables.ideals"
                    in warning
                    for warning in loader.warnings
                )
            )

    def test_missing_table_directory_can_still_generate_and_create_character(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            state = GameState(
                TableLoader(root / "missing_tables"),
                Database(root / "worlds.db"),
                random.Random(11),
            )
            world = state.generate_new_region()
            self.assertEqual(len(world.npcs), 10)
            self.assertEqual(len(world.dungeon.rooms), 8)
            character = state.create_character("Fallback Hero", "Explorer", "Wanderer")
            self.assertEqual(character.name, "Fallback Hero")
            self.assertTrue(character.personality_trait)
            self.assertTrue(character.bond)
            self.assertIsNotNone(world.player_state.inventory_item("basic_gear"))
            state.close()

    def test_class_table_contains_rules_neutral_starter_classes(self):
        loader = TableLoader(TABLES)
        factory = CharacterFactory(loader)
        definitions = factory.classes()
        self.assertEqual(
            {item.class_name for item in definitions},
            {
                "Fighter",
                "Thief",
                "Ranger",
                "Scholar",
                "Acolyte",
                "Occultist",
                "Mercenary",
                "Explorer",
                "Bard",
                "Mystic",
            },
        )
        self.assertTrue(factory.backgrounds())
        for definition in definitions:
            self.assertEqual(set(definition.bonuses), set(BONUS_NAMES))
            self.assertTrue(definition.role_description)
            self.assertTrue(definition.special_ability_placeholder)
            self.assertGreaterEqual(definition.starting_supplies, 0)

    def test_generated_world_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 12)
            world = state.generate_new_region()
            self.assertEqual(len(world.npcs), 10)
            self.assertEqual(len(world.settlement.important_locations), 8)
            self.assertEqual(len(world.dungeon.rooms), 8)
            self.assertEqual(len(world.wilderness.encounter_table), 10)
            all_entity_ids = [
                *(npc.entity_id for npc in world.npcs),
                *(location.entity_id for location in world.settlement.important_locations),
                *(room.entity_id for room in world.dungeon.rooms),
                *(encounter.entity_id for encounter in world.wilderness.encounter_table),
                world.adventure_hook.entity_id,
            ]
            self.assertTrue(all(all_entity_ids))
            self.assertEqual(len(all_entity_ids), len(set(all_entity_ids)))
            location_names = {item.name for item in world.settlement.important_locations}
            location_ids = {item.entity_id for item in world.settlement.important_locations}
            self.assertTrue(all(npc.location in location_names for npc in world.npcs))
            self.assertTrue(all(npc.location_id in location_ids for npc in world.npcs))
            npc_names = {npc.name for npc in world.npcs}
            npc_ids = {npc.entity_id for npc in world.npcs}
            for location in world.settlement.important_locations:
                self.assertIn(location.owner_or_keeper, npc_names)
                self.assertIn(location.owner_or_keeper, location.associated_npcs)
                self.assertIn(location.owner_npc_id, npc_ids)
                self.assertTrue(set(location.associated_npc_ids) <= npc_ids)
                self.assertTrue(location.associated_npcs)
                self.assertTrue(
                    all(
                        npc.location == location.name
                        for npc in world.npcs
                        if npc.name in location.associated_npcs
                    )
                )
            self.assertEqual([room.room_id for room in world.dungeon.rooms], list(range(1, 9)))
            for index, room in enumerate(world.dungeon.rooms, 1):
                if index < 8:
                    self.assertIn(index + 1, room.exits)
                if index > 1:
                    self.assertIn(index - 1, room.exits)
            self.assertIn(world.adventure_hook.key_npc, {npc.name for npc in world.npcs})
            self.assertIn(world.adventure_hook.key_npc_id, npc_ids)
            self.assertTrue(world.settlement.problem_connection)
            valid_problem_ids = {
                *(room.entity_id for room in world.dungeon.rooms),
                *(encounter.entity_id for encounter in world.wilderness.encounter_table),
                world.adventure_hook.entity_id,
            }
            self.assertIn(world.settlement.problem_target_id, valid_problem_ids)
            self.assertIn(world.settlement.name, world.dungeon.connection_to_town)
            self.assertIn(
                world.settlement.important_locations[0].name,
                world.dungeon.connection_to_town,
            )
            for encounter in world.wilderness.encounter_table:
                self.assertTrue(encounter.foreshadows_id)
                self.assertTrue(
                    world.dungeon.name in encounter.signs_or_foreshadowing
                    or world.local_threat in encounter.signs_or_foreshadowing
                )
            generated_references = {
                world.settlement.name,
                world.dungeon.name,
                world.wilderness.name,
                world.adventure_hook.key_npc,
                world.adventure_hook.artifact_or_relic,
                *(npc.name for npc in world.npcs),
                *(location.name for location in world.settlement.important_locations),
            }
            self.assertTrue(
                all(
                    any(reference in rumor for reference in generated_references)
                    for rumor in world.settlement.rumors
                )
            )
            state.close()

    def test_character_creation_applies_class_resources_and_survives_save(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 15)
            world = state.generate_new_region()
            definition = next(
                item for item in state.character_classes() if item.class_name == "Ranger"
            )
            background = state.character_backgrounds()[0]
            character = state.create_character("Sable Vey", "Ranger", background)
            player = world.player_state
            self.assertEqual(character.name, "Sable Vey")
            self.assertEqual(character.character_class, "Ranger")
            self.assertEqual(character.background, background)
            self.assertTrue(character.origin_detail)
            self.assertTrue(character.formative_event)
            self.assertTrue(character.personality_trait)
            self.assertTrue(character.ideal)
            self.assertTrue(character.bond)
            self.assertTrue(character.flaw)
            self.assertEqual(set(character.bonuses), set(BONUS_NAMES))
            self.assertEqual(player.supplies, definition.starting_supplies)
            self.assertEqual(player.food, definition.starting_food)
            self.assertEqual(player.water, definition.starting_water)
            self.assertEqual(player.torches, definition.starting_torches)
            self.assertEqual(player.coin, definition.starting_coin)
            inventory = {item.item_key: item for item in player.inventory}
            self.assertTrue(
                {"bedroll", "flint_steel", "blade", "field_kit"}
                <= set(inventory)
            )
            self.assertTrue(inventory["blade"].equipped)
            world_id = state.save_world("Character Save")
            loaded = state.load_world(world_id)
            self.assertEqual(loaded.player_state.character, character)
            self.assertEqual(loaded.player_state.inventory, player.inventory)
            self.assertTrue(
                any("Sable Vey" in entry for entry in loaded.player_state.event_log)
            )
            state.close()

    def test_legacy_string_and_missing_inventories_load_safely(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 19)
            world = state.generate_new_region()
            data = world.to_dict()
            data["player_state"]["inventory"] = ["old bedroll", "silver clue"]
            restored = type(world).from_dict(data)
            self.assertEqual(
                [item.name for item in restored.player_state.inventory],
                ["old bedroll", "silver clue"],
            )
            self.assertTrue(
                all(
                    item.category == "Miscellaneous"
                    for item in restored.player_state.inventory
                )
            )

            data = world.to_dict()
            data["player_state"].pop("inventory")
            restored_without_inventory = type(world).from_dict(data)
            self.assertEqual(
                {item.item_key for item in restored_without_inventory.player_state.inventory},
                {"bedroll", "flint_steel"},
            )
            state.close()

    def test_pre_profile_character_save_loads_with_safe_defaults(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 17)
            world = state.generate_new_region()
            state.create_character(
                "Old Wanderer",
                state.character_classes()[0].class_name,
                state.character_backgrounds()[0],
            )
            data = world.to_dict()
            character_data = data["player_state"]["character"]
            for key in (
                "origin_detail",
                "formative_event",
                "personality_trait",
                "ideal",
                "bond",
                "flaw",
            ):
                character_data.pop(key)
            restored = type(world).from_dict(data)
            character = restored.player_state.character
            self.assertIsNotNone(character)
            self.assertEqual(character.origin_detail, "")
            self.assertEqual(character.formative_event, "")
            self.assertEqual(character.personality_trait, "")
            self.assertEqual(character.ideal, "")
            self.assertEqual(character.bond, "")
            self.assertEqual(character.flaw, "")
            state.close()

    def test_game_state_random_names_fall_back_without_cleaned_files(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 16)
            generated = state.random_full_names(4)
            self.assertEqual(len(generated), 4)
            self.assertTrue(all(len(name.split()) >= 2 for name in generated))
            state.close()

    def test_save_load_round_trip_and_normalized_rows(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 4)
            original = state.generate_new_region()
            world_id = state.save_world("Test Save")
            loaded = state.load_world(world_id)
            self.assertEqual(loaded.name, "Test Save")
            self.assertEqual(loaded.settlement, original.settlement)
            self.assertEqual(loaded.npcs, original.npcs)
            self.assertEqual(
                [npc.entity_id for npc in loaded.npcs],
                [npc.entity_id for npc in original.npcs],
            )
            self.assertEqual(
                [encounter.foreshadows_id for encounter in loaded.wilderness.encounter_table],
                [encounter.foreshadows_id for encounter in original.wilderness.encounter_table],
            )
            self.assertEqual(
                loaded.settlement.problem_target_id,
                original.settlement.problem_target_id,
            )
            self.assertEqual(loaded.player_state, original.player_state)
            counts = {}
            for table in (
                "worlds", "settlements", "npcs", "locations", "dungeons",
                "dungeon_rooms", "wilderness_areas", "encounters",
                "adventure_hooks", "player_state",
            ):
                counts[table] = state.database.connection.execute(
                    f"SELECT COUNT(*) FROM {table}"
                ).fetchone()[0]
            self.assertEqual(counts["worlds"], 1)
            self.assertEqual(counts["npcs"], 10)
            self.assertEqual(counts["locations"], 8)
            self.assertEqual(counts["dungeon_rooms"], 8)
            self.assertEqual(counts["encounters"], 10)
            state.close()

    def test_missing_tables_use_fallback(self):
        with tempfile.TemporaryDirectory() as temp:
            loader = TableLoader(Path(temp) / "absent")
            value = loader.choose("missing", "missing", random.Random(1))
            self.assertTrue(value)
            self.assertTrue(loader.warnings)

    def test_malformed_table_is_reported_without_crashing(self):
        with tempfile.TemporaryDirectory() as temp:
            table_dir = Path(temp)
            (table_dir / "broken.json").write_text("{not valid json", encoding="utf-8")
            loader = TableLoader(table_dir)
            value = loader.choose("broken", "anything", random.Random(1))
            self.assertTrue(value)
            self.assertTrue(any("Could not load broken.json" in item for item in loader.warnings))

    def test_version_01_save_shape_still_loads(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 8)
            world = state.generate_new_region()
            data = world.to_dict()
            data["settlement"].pop("problem_connection")
            data["settlement"].pop("problem_target_type")
            data["settlement"].pop("problem_target_id")
            for location in data["settlement"]["important_locations"]:
                location.pop("associated_npcs")
                location.pop("associated_npc_ids")
                location.pop("owner_npc_id")
                location.pop("entity_id")
            for npc in data["npcs"]:
                npc.pop("entity_id")
                npc.pop("location_id")
            data["dungeon"].pop("town_location_id")
            for room in data["dungeon"]["rooms"]:
                room.pop("entity_id")
            for encounter in data["wilderness"]["encounter_table"]:
                encounter.pop("entity_id")
                encounter.pop("foreshadows_type")
                encounter.pop("foreshadows_id")
            data["adventure_hook"].pop("entity_id")
            data["adventure_hook"].pop("key_npc_id")
            restored = type(world).from_dict(data)
            self.assertEqual(restored.settlement.problem_connection, restored.settlement.local_problem)
            self.assertTrue(
                all(location.associated_npcs for location in restored.settlement.important_locations)
            )
            self.assertTrue(all(npc.entity_id and npc.location_id for npc in restored.npcs))
            self.assertTrue(
                all(
                    location.entity_id
                    and location.owner_npc_id
                    and location.associated_npc_ids
                    for location in restored.settlement.important_locations
                )
            )
            self.assertTrue(all(room.entity_id for room in restored.dungeon.rooms))
            self.assertTrue(
                all(
                    encounter.entity_id and encounter.foreshadows_id
                    for encounter in restored.wilderness.encounter_table
                )
            )
            self.assertTrue(restored.adventure_hook.entity_id)
            self.assertTrue(restored.adventure_hook.key_npc_id)
            state.close()

    def test_version_02_player_state_defaults_to_playable(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 18)
            world = state.generate_new_region()
            data = world.to_dict()
            for key in (
                "current_location",
                "current_location_id",
                "current_room_id",
                "day",
                "time_period",
                "coin",
                "wounds",
                "discovered_room_ids",
                "pending_encounter_id",
                "action_log",
                "event_log",
                "known_npc_ids",
                "known_location_ids",
                "known_rumor_indices",
                "known_threats",
                "leads",
                "turns_elapsed",
            ):
                data["player_state"].pop(key)
            restored = type(world).from_dict(data)
            self.assertEqual(restored.player_state.current_location, "town")
            self.assertEqual(restored.player_state.day, 1)
            self.assertEqual(restored.player_state.time_period, "Morning")
            self.assertEqual(restored.player_state.coin, 20)
            self.assertEqual(restored.player_state.wounds, 0)
            self.assertEqual(restored.player_state.action_log, [])
            self.assertEqual(restored.player_state.event_log, [])
            self.assertIsNone(restored.player_state.character)
            state.close()

    def test_older_character_and_player_state_get_age_and_downtime_defaults(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 19)
            world = state.generate_new_region()
            state.create_character("Nera Vale", "Scholar", state.character_backgrounds()[0])
            data = world.to_dict()
            data["player_state"]["character"].pop("age_years")
            data["player_state"].pop("age_days_accumulated", None)
            data["player_state"].pop("active_downtime_task", None)
            restored = type(world).from_dict(data)
            self.assertEqual(restored.player_state.character.age_years, 26)
            self.assertEqual(restored.player_state.age_days_accumulated, 0)
            self.assertIsNone(restored.player_state.active_downtime_task)
            state.close()

    def test_older_active_downtime_task_defaults_new_outcome_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 20)
            world = state.generate_new_region()
            state.create_character("Old Task", "Ranger", state.character_backgrounds()[0])
            state.start_downtime_task("train_skill")
            data = world.to_dict()
            task = data["player_state"]["active_downtime_task"]
            task.pop("progress_outcomes", None)
            task.pop("completion_outcomes", None)
            task.pop("complication_outcomes", None)
            restored = type(world).from_dict(data)
            active = restored.player_state.active_downtime_task
            self.assertEqual(active.progress_outcomes, [])
            self.assertEqual(active.completion_outcomes, [])
            self.assertEqual(active.complication_outcomes, [])
            state.close()


class ExporterTests(unittest.TestCase):
    def make_state(self, folder: Path, seed: int = 1) -> GameState:
        return GameState(
            TableLoader(TABLES),
            Database(folder / "worlds.db"),
            random.Random(seed),
        )

    def test_world_export_contains_summary_sections(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 70)
            world = state.generate_new_region("world-export-seed")
            text = export_world_summary(world)
            self.assertIn(world.name.upper(), text)
            self.assertIn("Seed: world-export-seed", text)
            self.assertIn("Calendar:", text)
            self.assertIn("Downtime:", text)
            self.assertIn("KNOWN CONTACTS AND LEADS", text)
            self.assertIn("RUMOR LEADS", text)
            self.assertIn("OPEN LEADS", text)
            self.assertIn("SUGGESTED NEXT ACTIONS", text)
            self.assertIn(world.adventure_hook.major_goal, text)
            state.close()

    def test_character_export_handles_missing_world_and_character(self):
        self.assertIn("NO ACTIVE WORLD", export_character_text(None))
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 71)
            world = state.generate_new_region()
            self.assertIn("NO PLAYER CHARACTER", export_character_text(world))
            state.close()

    def test_character_export_separates_inventory_from_resource_counters(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 72)
            try:
                world = state.generate_new_region("character-export-seed")
                state.create_character(
                    "Tarin Vale",
                    "Ranger",
                    state.character_backgrounds()[0],
                )
                state.add_inventory_item(
                    InventoryItem(
                        item_key="trail_rations",
                        name="Trail Rations",
                        category="Supply",
                        quantity=2,
                        description="Packed food for a short journey.",
                        consumable=True,
                    ),
                    quantity=2,
                )
                text = export_character_text(world)
                self.assertIn("Seed: character-export-seed", text)
                self.assertIn("Age:", text)
                self.assertIn("Age Band:", text)
                self.assertIn("Current Calendar:", text)
                self.assertIn("Trail Rations x2 (Supply) [consumable]", text)
                self.assertIn("RESOURCES", text)
                self.assertIn("Food: 9", text)
                self.assertNotIn("Food x9", text)
                self.assertIn(
                    "Resource counters remain separate from inventory records",
                    text,
                )
            finally:
                state.close()

    def test_event_log_export_handles_empty_and_pending_states(self):
        self.assertIn("NO ACTIVE WORLD", export_event_log_text(None))
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 73)
            world = state.generate_new_region("event-export-seed")
            world.player_state.event_log = []
            text = export_event_log_text(world)
            self.assertIn("Seed: event-export-seed", text)
            self.assertIn("No events recorded yet.", text)
            self.assertIn("Calendar:", text)
            self.assertIn("Downtime:", text)
            world.player_state.pending_encounter_id = "enc_test"
            text = export_event_log_text(world)
            self.assertIn("DANGER IS PENDING", text)
            state.close()

    def test_seed_survives_save_and_load(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 74)
            try:
                state.generate_new_region("save-seed")
                world_id = state.save_world("Seed Save")
                loaded = state.load_world(world_id)
                self.assertEqual(loaded.generation_seed, "save-seed")
                self.assertEqual(state.active_seed, "save-seed")
            finally:
                state.close()


class ExplorationTests(unittest.TestCase):
    def make_state(self, folder: Path, seed: int = 1) -> GameState:
        state = GameState(
            TableLoader(TABLES),
            Database(folder / "worlds.db"),
            random.Random(seed),
        )
        state.generate_new_region()
        return state

    def test_travel_dungeon_movement_light_and_retreat(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 21)
            player = state.world.player_state
            state.travel("dungeon_entrance")
            self.assertEqual(player.current_location, "dungeon_entrance")
            state.explore_current_area()
            self.assertEqual(player.current_location, "dungeon")
            self.assertEqual(player.current_room_id, 1)
            self.assertIn(1, player.discovered_room_ids)
            self.assertEqual(player.torches, 5)
            self.assertEqual(player.light_turns_remaining, 5)
            first_exit = state.world.dungeon.rooms[0].exits[0]
            state.move_room(first_exit)
            self.assertEqual(player.current_room_id, first_exit)
            self.assertIn(first_exit, player.discovered_room_ids)
            self.assertEqual(player.light_turns_remaining, 4)
            state.retreat()
            self.assertEqual(player.current_location, "dungeon_entrance")
            self.assertIsNone(player.current_room_id)
            state.close()

    def test_talk_to_npc_varies_and_adds_leads(self):
        with tempfile.TemporaryDirectory() as temp:
            messages = set()
            for seed in (71, 72, 73, 74):
                state = self.make_state(Path(temp), seed)
                try:
                    player = state.world.player_state
                    initial_leads = len(player.leads)
                    message = state.talk_to_npc()
                    messages.add(message)
                    self.assertGreater(len(player.leads), initial_leads)
                    self.assertIn(message, player.event_log[-1])
                finally:
                    state.close()
            self.assertGreater(len(messages), 1)

    def test_encounter_resolution_varies_across_seeded_runs(self):
        with tempfile.TemporaryDirectory() as temp:
            results = set()
            for seed in (81, 82, 83, 84, 85):
                state = self.make_state(Path(temp), seed)
                try:
                    player = state.world.player_state
                    state.travel("wilderness")
                    encounter = state.world.wilderness.encounter_table[0]
                    player.pending_encounter_id = encounter.entity_id
                    result = state.resolve_encounter("approach")
                    results.add(result)
                    self.assertIn(result, player.event_log[-1])
                finally:
                    state.close()
            self.assertGreater(len(results), 1)


class ActionCheckTests(unittest.TestCase):
    def make_state(self, folder: Path, seed: int = 1) -> GameState:
        state = GameState(
            TableLoader(TABLES),
            Database(folder / "worlds.db"),
            random.Random(seed),
        )
        state.generate_new_region()
        return state

    def test_check_resolution_all_outcomes(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 60)
            cases = [
                (1, "critical failure"),
                (5, "failure"),
                (10, "partial success"),
                (12, "success"),
                (17, "critical success"),
            ]
            for roll_result, expected in cases:
                result = state.perform_check(
                    "search_area",
                    "Standard",
                    roll_override=roll_result,
                )
                self.assertEqual(result.roll_result, roll_result)
                self.assertEqual(result.difficulty_class, DIFFICULTIES["Standard"])
                self.assertEqual(result.total, roll_result)
                self.assertEqual(result.outcome, expected)
                self.assertTrue(result.narrative_result)
                self.assertTrue(result.consequence)
            state.close()

    def test_check_narration_varies_across_seeded_runs(self):
        with tempfile.TemporaryDirectory() as temp:
            narratives = set()
            for seed in (91, 92, 93, 94):
                state = self.make_state(Path(temp), seed)
                try:
                    result = state.perform_check(
                        "search_area",
                        "Standard",
                        roll_override=12,
                    )
                    narratives.add(result.narrative_result)
                finally:
                    state.close()
            self.assertGreater(len(narratives), 1)

    def test_class_bonus_changes_check_total_and_outcome(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 61)
            state.create_character(
                "Brin Salt",
                "Fighter",
                state.character_backgrounds()[0],
            )
            result = state.perform_check(
                "force_dangerous_action",
                "Easy",
                roll_override=6,
            )
            self.assertEqual(result.bonus_type, "combat")
            self.assertEqual(result.bonus_used, 2)
            self.assertEqual(result.total, 8)
            self.assertEqual(result.outcome, "success")
            self.assertIn("CHECK: Force Dangerous Action", state.world.player_state.event_log[-1])
            state.close()

    def test_all_consequences_apply_to_player_state(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 62)
            player = state.world.player_state

            turns = player.turns_elapsed
            state.perform_check(
                "search_area", roll_override=12, consequence_override="lose time"
            )
            self.assertEqual(player.turns_elapsed, turns + 2)

            supplies = player.supplies
            state.perform_check(
                "search_area", roll_override=12, consequence_override="lose supplies"
            )
            self.assertLess(player.supplies, supplies)

            wounds = player.wounds
            state.perform_check(
                "search_area", roll_override=12, consequence_override="gain wound"
            )
            self.assertEqual(player.wounds, wounds + 1)

            attention = player.attention
            state.perform_check(
                "search_area", roll_override=12, consequence_override="attract attention"
            )
            self.assertEqual(player.attention, attention + 1)

            leads = len(player.leads)
            state.perform_check(
                "search_area", roll_override=12, consequence_override="reveal clue"
            )
            self.assertGreater(len(player.leads), leads)

            position = player.position
            state.perform_check(
                "search_area", roll_override=20, consequence_override="improve position"
            )
            self.assertEqual(player.position, position + 1)
            state.perform_check(
                "search_area", roll_override=5, consequence_override="worsen position"
            )
            self.assertEqual(player.position, position)
            self.assertTrue(player.last_consequence)
            state.close()

    def test_check_state_and_character_survive_save_load(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 63)
            character = state.create_character(
                "Kest Mourn",
                "Scholar",
                state.character_backgrounds()[1],
            )
            state.travel("dungeon_entrance")
            result = state.perform_check(
                "read_ancient_markings",
                "Hard",
                roll_override=15,
                consequence_override="reveal clue",
            )
            world_id = state.save_world("Check Save")
            loaded = state.load_world(world_id)
            self.assertEqual(loaded.player_state.character, character)
            self.assertEqual(loaded.player_state.last_check, result)
            self.assertEqual(
                loaded.player_state.last_consequence,
                result.consequence,
            )
            state.close()

    def test_time_cycles_and_full_rest_reaches_next_day(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 22)
            player = state.world.player_state
            self.assertEqual((player.day, player.time_period), (1, "Morning"))
            state.search()
            self.assertEqual((player.day, player.time_period), (1, "Afternoon"))
            state.talk_to_npc()
            self.assertEqual((player.day, player.time_period), (1, "Evening"))
            coin_before = player.coin
            state.full_rest()
            self.assertEqual((player.day, player.time_period), (2, "Morning"))
            self.assertEqual(player.coin, coin_before - 2)
            self.assertTrue(all("Day " in entry for entry in player.event_log))
            state.close()

    def test_initial_discovery_is_partial_and_investigation_expands_it(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 23)
            world = state.world
            player = world.player_state
            self.assertLess(len(player.known_npc_ids), len(world.npcs))
            self.assertLess(
                len(player.known_location_ids), len(world.settlement.important_locations)
            )
            self.assertLess(
                len(player.known_rumor_indices), len(world.settlement.rumors)
            )
            initial_events = len(player.event_log)
            state.inspect_location()
            state.talk_to_npc()
            self.assertGreaterEqual(len(player.known_npc_ids), 1)
            self.assertGreaterEqual(len(player.known_rumor_indices), 2)
            self.assertTrue(player.leads)
            self.assertGreater(len(player.event_log), initial_events)
            self.assertTrue(any("Discovery:" in entry for entry in player.event_log))
            state.close()

    def test_travel_to_known_location_and_wilderness_search_discovers_threat(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 24)
            world = state.world
            player = world.player_state
            location = world.settlement.important_locations[0]
            state.travel_to_location(location.entity_id)
            self.assertEqual(player.current_location_id, location.entity_id)
            state.travel("wilderness")
            known_before = len(player.known_threats)
            state.search()
            self.assertGreaterEqual(len(player.known_threats), known_before + 1)
            self.assertTrue(player.leads)
            state.close()

    def test_wilderness_signs_and_all_resolution_choices(self):
        with tempfile.TemporaryDirectory() as temp:
            for index, choice in enumerate(("avoid", "approach", "investigate", "retreat")):
                state = self.make_state(Path(temp), 30 + index)
                player = state.world.player_state
                state.travel("wilderness")
                encounter = state.world.wilderness.encounter_table[index]
                player.pending_encounter_id = encounter.entity_id
                result = state.resolve_encounter(choice)
                self.assertTrue(result)
                self.assertEqual(player.pending_encounter_id, "")
                self.assertTrue(player.action_log)
                state.close()

    def test_search_talk_rest_consequences_and_save_load(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 44)
            player = state.world.player_state
            start_turns = player.turns_elapsed
            self.assertIn("speak with", state.talk_to_npc())
            self.assertGreater(player.turns_elapsed, start_turns)
            state.search()
            player.wounds = 2
            player.food = 7
            player.water = 7
            state.rest()
            self.assertGreaterEqual(player.wounds, 0)
            self.assertGreaterEqual(player.supplies, 0)
            self.assertGreaterEqual(player.food, 0)
            self.assertGreaterEqual(player.water, 0)
            world_id = state.save_world("Exploration Save")
            snapshot = state.world.player_state
            loaded = state.load_world(world_id)
            self.assertEqual(loaded.player_state, snapshot)
            self.assertTrue(loaded.player_state.event_log)
            self.assertEqual(loaded.player_state.day, snapshot.day)
            self.assertEqual(loaded.player_state.known_npc_ids, snapshot.known_npc_ids)
            state.close()

    def test_event_log_export_includes_new_interaction_text(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 95)
            try:
                message = state.talk_to_npc()
                exported = export_event_log_text(state.world)
                self.assertIn(message, exported)
            finally:
                state.close()


class CalendarAndDowntimeTests(unittest.TestCase):
    def make_state(self, folder: Path, seed: int = 1) -> GameState:
        state = GameState(
            TableLoader(TABLES),
            Database(folder / "worlds.db"),
            random.Random(seed),
        )
        state.generate_new_region()
        return state

    def test_calendar_initialization_uses_weird_fantasy_season_labels(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 96)
            current = calendar_date(
                state.world.player_state.day,
                state.world.player_state.time_period,
            )
            self.assertEqual(current.year, 1000)
            self.assertEqual(current.season, "Thaw")
            self.assertEqual(current.day_of_season, 1)
            self.assertEqual(current.time_period, "Morning")
            state.close()

    def test_calendar_rolls_from_one_season_to_the_next(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 97)
            player = state.world.player_state
            player.day = 30
            player.time_period = "Night"
            state.search()
            current = calendar_date(player.day, player.time_period)
            self.assertEqual((player.day, player.time_period), (31, "Morning"))
            self.assertEqual(current.season, "Emberwake")
            self.assertEqual(current.day_of_season, 1)
            state.close()

    def test_age_band_labels_cover_expected_ranges(self):
        self.assertEqual(age_band(20), "Young Adult")
        self.assertEqual(age_band(30), "Adult")
        self.assertEqual(age_band(50), "Seasoned")
        self.assertEqual(age_band(70), "Elder")
        self.assertEqual(age_band(90), "Ancient")

    def test_age_increases_after_enough_calendar_time_passes(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 98)
            state.create_character("Iven Gloam", "Ranger", state.character_backgrounds()[0])
            player = state.world.player_state
            initial_age = player.character.age_years
            state.start_downtime_task("study_target")
            state.advance_downtime(120)
            self.assertEqual(player.character.age_years, initial_age + 1)
            self.assertEqual(player.age_days_accumulated, 0)
            state.close()

    def test_starting_advancing_and_completing_downtime_updates_state(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 99)
            try:
                state.create_character("Downtime Worker", "Ranger", state.character_backgrounds()[0])
                player = state.world.player_state
                start_day = player.day
                message = state.start_downtime_task("work_for_coin")
                self.assertIn("Started downtime task", message)
                self.assertIsNotNone(player.active_downtime_task)
                coin_before = player.coin
                result = state.advance_downtime(3)
                self.assertIn("work", result.lower())
                self.assertIsNone(player.active_downtime_task)
                self.assertEqual(player.day, start_day + 3)
                self.assertGreater(player.coin, coin_before)
                self.assertTrue(any("Downtime begins:" in entry for entry in player.event_log))
                self.assertTrue(any("Work for Coin" in entry for entry in player.event_log))
            finally:
                state.close()

    def test_downtime_progress_can_add_location_aware_lead(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 102)
            try:
                state.create_character("Lead Finder", "Ranger", state.character_backgrounds()[0])
                player = state.world.player_state
                known_locations = len(player.known_location_ids)
                state.start_downtime_task("investigate_rumor")
                result = state.advance_downtime(1)
                self.assertIn("Downtime lead:", result)
                self.assertGreater(len(player.leads), 1)
                self.assertGreaterEqual(len(player.known_location_ids), known_locations + 1)
                self.assertTrue(any("Downtime lead:" in entry for entry in player.event_log))
            finally:
                state.close()

    def test_downtime_completion_can_add_npc_or_quest_followup(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 103)
            try:
                state.create_character("Social Thread", "Ranger", state.character_backgrounds()[0])
                player = state.world.player_state
                known_npcs = len(player.known_npc_ids)
                state.start_downtime_task("build_relationship")
                result = state.advance_downtime(4)
                self.assertIn("Relationship lead:", result)
                self.assertIsNone(player.active_downtime_task)
                self.assertGreaterEqual(len(player.known_npc_ids), known_npcs + 1)
                self.assertTrue(any("Relationship lead:" in lead for lead in player.leads))
            finally:
                state.close()

    def test_downtime_complication_can_apply_world_aware_resource_cost(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 104)
            try:
                state.create_character("Kit Keeper", "Ranger", state.character_backgrounds()[0])
                player = state.world.player_state
                supplies_before = player.supplies
                state.start_downtime_task("maintain_equipment")
                state.rng = random.Random(1)
                result = state.advance_downtime(1)
                self.assertIn("Complication:", result)
                self.assertEqual(player.supplies, supplies_before - 1)
                self.assertTrue(any("costs you -1 supply" in entry for entry in player.event_log))
            finally:
                state.close()

    def test_downtime_without_new_outcome_fields_uses_safe_defaults(self):
        with tempfile.TemporaryDirectory() as temp:
            table_dir = Path(temp)
            for path in TABLES.glob("*.json"):
                if path.name == "downtime_tables.json":
                    continue
                (table_dir / path.name).write_text(
                    path.read_text(encoding="utf-8"),
                    encoding="utf-8",
                )
            (table_dir / "downtime_tables.json").write_text(
                json.dumps(
                    {
                        "tasks": [
                            {
                                "task_key": "plain_task",
                                "name": "Plain Task",
                                "category": "study",
                                "description": "Old-style task without optional outcomes.",
                                "default_duration_days": 1,
                                "allowed_contexts": ["town"],
                                "progress_text": "{task_name}: progress.",
                                "completion_text": "{task_name}: complete.",
                                "complication_text": "{task_name}: complication.",
                                "tags": ["plain"]
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            state = GameState(
                TableLoader(table_dir),
                Database(table_dir / "worlds.db"),
                random.Random(1),
            )
            try:
                world = state.generate_new_region()
                state.create_character("Plain Worker", "Ranger", state.character_backgrounds()[0])
                state.start_downtime_task("plain_task")
                result = state.advance_downtime(1)
                self.assertIn("Plain Task: progress.", result)
                self.assertIn("Plain Task: complete.", result)
                self.assertTrue(world.player_state.event_log)
            finally:
                state.close()

    def test_recovery_downtime_can_reduce_wounds(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 100)
            try:
                state.create_character("Recovering Scout", "Ranger", state.character_backgrounds()[0])
                player = state.world.player_state
                player.wounds = 2
                state.start_downtime_task("recover_from_injury")
                state.advance_downtime(3)
                self.assertEqual(player.wounds, 1)
            finally:
                state.close()

    def test_active_downtime_task_survives_save_and_load(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 101)
            try:
                state.create_character("Patient Student", "Scholar", state.character_backgrounds()[0])
                state.start_downtime_task("train_skill")
                state.advance_downtime(1)
                world_id = state.save_world("Downtime Save")
                loaded = state.load_world(world_id)
                active = loaded.player_state.active_downtime_task
                self.assertIsNotNone(active)
                self.assertEqual(active.task_key, "train_skill")
                self.assertEqual(active.progress_days, 1)
            finally:
                state.close()

    def test_downtime_outcomes_appear_in_event_log_export(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 105)
            try:
                state.create_character("Export Watcher", "Ranger", state.character_backgrounds()[0])
                state.start_downtime_task("investigate_rumor")
                state.advance_downtime(1)
                exported = export_event_log_text(state.world)
                self.assertIn("Downtime lead:", exported)
                self.assertIn("Calendar:", exported)
                self.assertIn("Downtime:", exported)
            finally:
                state.close()

    def test_downtime_progress_display_caps_at_required_days(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 118)
            try:
                state.create_character("Capped Progress", "Ranger", state.character_backgrounds()[0])
                state.start_downtime_task("train_skill")
                result = state.advance_downtime(6)
                self.assertIn("5/5", result)
                self.assertNotIn("6/5", result)
            finally:
                state.close()

    def test_training_completion_records_concrete_result_and_follow_up(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 119)
            try:
                state.create_character("Ready Walker", "Ranger", state.character_backgrounds()[0])
                player = state.world.player_state
                state.start_downtime_task("train_skill")
                result = state.advance_downtime(5)
                self.assertIn("Training complete:", result)
                self.assertTrue(
                    any("Training edge:" in note for note in player.quest_log)
                )
                self.assertTrue(
                    any("practical test" in lead for lead in player.leads)
                )
            finally:
                state.close()


class LeadTrackingTests(unittest.TestCase):
    def make_state(self, folder: Path, seed: int = 1) -> GameState:
        state = GameState(
            TableLoader(TABLES),
            Database(folder / "worlds.db"),
            random.Random(seed),
        )
        state.generate_new_region("lead-seed")
        return state

    def test_duplicate_leads_are_deduped_and_corroborated(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 120)
            try:
                player = state.world.player_state
                text = "Investigate why the oath-bound dead fear salt and open flame."
                add_lead(
                    player,
                    text,
                    source="Aethelberht Seyed",
                    location="The Last Lantern",
                    related_npc="Eurie Prela",
                    status="uncorroborated",
                    suggested_action="Speak with Eurie Prela at The Market.",
                    category="talk",
                )
                add_lead(
                    player,
                    text,
                    source="Eurie Prela",
                    location="The Market",
                    related_npc="Eurie Prela",
                    status="uncorroborated",
                    suggested_action="Speak with Eurie Prela at The Market.",
                    category="talk",
                )
                matching = [lead for lead in player.lead_records if lead.text == text]
                self.assertEqual(len(matching), 1)
                self.assertEqual(matching[0].status, "corroborated")
                self.assertIn("Aethelberht Seyed", matching[0].source)
                self.assertIn("Eurie Prela", matching[0].source)
                self.assertEqual(player.leads.count(text), 1)
            finally:
                state.close()

    def test_summary_and_exports_surface_open_leads_and_next_actions(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 121)
            try:
                player = state.world.player_state
                state.create_character("Lead Watcher", "Ranger", state.character_backgrounds()[0])
                add_lead(
                    player,
                    "The drowned knight fears salt and open flame.",
                    source="Aethelberht Seyed",
                    location="The Last Lantern",
                    related_npc="Eurie Prela",
                    status="uncorroborated",
                    suggested_action="Speak with Eurie Prela at The Market.",
                    category="talk",
                )
                add_lead(
                    player,
                    "A sealed cellar is tied to a hidden key.",
                    source="Aethelberht Seyed",
                    location="The Last Lantern",
                    suggested_action="Find the sealed cellar connected to Aethelberht Seyed's key.",
                    category="explore",
                )
                summary = format_summary_timeline(state.world)
                world_text = export_world_summary(state.world)
                character_text = export_character_text(state.world)
                event_text = export_event_log_text(state.world)
                self.assertIn("Open Leads", summary)
                self.assertIn("Suggested Next Actions", summary)
                self.assertIn("Talk:", summary)
                self.assertIn("Speak with Eurie Prela at The Market.", summary)
                self.assertIn("OPEN LEADS", world_text)
                self.assertIn("SUGGESTED NEXT ACTIONS", world_text)
                self.assertIn("Find the sealed cellar connected to Aethelberht Seyed's key.", world_text)
                self.assertIn("OPEN LEADS", character_text)
                self.assertIn("OPEN LEADS", event_text)
            finally:
                state.close()


class TimelineAndNpcTests(unittest.TestCase):
    def make_state(self, folder: Path, seed: int = 1) -> GameState:
        state = GameState(
            TableLoader(TABLES),
            Database(folder / "worlds.db"),
            random.Random(seed),
        )
        state.generate_new_region("timeline-seed")
        return state

    def test_timeline_formatters_handle_empty_state(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 106)
            try:
                world = state.world
                world.player_state.timeline_entries.clear()
                summary = format_summary_timeline(world)
                verbose = format_verbose_timeline(world)
                self.assertIn("No timeline activity has been summarized yet.", summary)
                self.assertIn("No structured timeline entries recorded yet.", verbose)
            finally:
                state.close()

    def test_talking_repeatedly_promotes_npc_to_prominent(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 107)
            try:
                player = state.world.player_state
                first_known = state.world.npcs[0]
                for npc in state.world.npcs[1:]:
                    npc.location_id = "other_location"
                player.current_location = "town"
                player.current_location_id = first_known.location_id
                for _ in range(PROMINENT_NPC_THRESHOLD):
                    state.talk_to_npc()
                    player.current_location = "town"
                    player.current_location_id = first_known.location_id
                npc = next(item for item in state.world.npcs if item.entity_id == first_known.entity_id)
                self.assertTrue(npc.prominent)
                self.assertGreaterEqual(npc.interaction_count, PROMINENT_NPC_THRESHOLD)
                self.assertTrue(npc.deeper_backstory)
                self.assertTrue(npc.personal_motive)
                self.assertTrue(npc.recent_interaction_notes)
                self.assertTrue(
                    any(
                        entry.action_type == "npc_prominence" and entry.npc_id == npc.entity_id
                        for entry in player.timeline_entries
                    )
                )
            finally:
                state.close()

    def test_timeline_entries_capture_action_metadata(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 108)
            try:
                state.search()
                state.talk_to_npc()
                state.travel("wilderness")
                player = state.world.player_state
                action_types = {entry.action_type for entry in player.timeline_entries}
                self.assertIn("search", action_types)
                self.assertIn("talk", action_types)
                self.assertIn("travel", action_types)
                self.assertTrue(any(entry.location_context for entry in player.timeline_entries))
                verbose = format_verbose_timeline(state.world)
                self.assertIn("VERBOSE TIMELINE", verbose)
                self.assertIn("SEARCH", verbose)
            finally:
                state.close()

    def test_exports_include_timeline_and_prominent_npc_sections(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 109)
            try:
                state.create_character("Journal Keeper", "Ranger", state.character_backgrounds()[0])
                first_known = state.world.npcs[0]
                for npc in state.world.npcs[1:]:
                    npc.location_id = "other_location"
                state.world.player_state.current_location = "town"
                state.world.player_state.current_location_id = first_known.location_id
                for _ in range(PROMINENT_NPC_THRESHOLD):
                    state.talk_to_npc()
                    state.world.player_state.current_location = "town"
                    state.world.player_state.current_location_id = first_known.location_id
                world_text = export_world_summary(state.world)
                character_text = export_character_text(state.world)
                event_text = export_event_log_text(state.world)
                self.assertIn("JOURNAL SUMMARY", world_text)
                self.assertIn("PROMINENT NPCS", world_text)
                self.assertIn("RECENT MAJOR ACTIONS", character_text)
                self.assertIn("TIMELINE SUMMARY", event_text)
                self.assertIn("VERBOSE TIMELINE", event_text)
            finally:
                state.close()

    def test_older_save_defaults_missing_timeline_and_prominence_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 110)
            try:
                data = state.world.to_dict()
                data["player_state"].pop("timeline_entries", None)
                npc = data["npcs"][0]
                for key in (
                    "interaction_count",
                    "first_interacted_date",
                    "last_interacted_date",
                    "prominence_score",
                    "prominent",
                    "deeper_backstory",
                    "personal_motive",
                    "hidden_pressure",
                    "relationship_to_player",
                    "ongoing_thread",
                    "prominence_notes",
                    "recent_interaction_notes",
                ):
                    npc.pop(key, None)
                restored = type(state.world).from_dict(data)
                restored_npc = restored.npcs[0]
                self.assertEqual(restored.player_state.timeline_entries, [])
                self.assertFalse(restored_npc.prominent)
                self.assertEqual(restored_npc.interaction_count, 0)
                self.assertEqual(restored_npc.recent_interaction_notes, [])
            finally:
                state.close()

    def test_npc_becomes_key_at_threshold_only_once(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 111)
            try:
                player = state.world.player_state
                first_known = state.world.npcs[0]
                for npc in state.world.npcs[1:]:
                    npc.location_id = "other_location"
                player.current_location = "town"
                player.current_location_id = first_known.location_id
                for _ in range(KEY_NPC_THRESHOLD):
                    state.talk_to_npc()
                    player.current_location = "town"
                    player.current_location_id = first_known.location_id
                npc = next(item for item in state.world.npcs if item.entity_id == first_known.entity_id)
                self.assertTrue(npc.is_key_npc)
                first_since = npc.key_npc_since
                first_reason = npc.key_npc_reason
                state.talk_to_npc()
                self.assertEqual(npc.key_npc_since, first_since)
                self.assertEqual(npc.key_npc_reason, first_reason)
                self.assertEqual(
                    sum(1 for entry in player.timeline_entries if entry.action_type == "key_npc"),
                    1,
                )
            finally:
                state.close()

    def test_relationship_records_created_when_multiple_key_npcs_exist(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 112)
            try:
                from app.key_npcs import promote_key_npc_if_needed

                for npc in state.world.npcs[:2]:
                    npc.prominence_score = KEY_NPC_THRESHOLD
                    npc.prominent = True
                    promote_key_npc_if_needed(state.world, npc, state.rng, state.tables)
                self.assertEqual(len(state.world.npc_relationships), 1)
                relationship = state.world.npc_relationships[0]
                self.assertIn(relationship.relationship_state, RELATIONSHIP_STATES)
                self.assertEqual(
                    {relationship.npc_a_id, relationship.npc_b_id},
                    {state.world.npcs[0].entity_id, state.world.npcs[1].entity_id},
                )
                state.run_key_npc_interaction_phase()
                self.assertEqual(len(state.world.npc_relationships), 1)
            finally:
                state.close()

    def test_key_npc_phase_noops_with_zero_or_one_key_npc(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 113)
            try:
                self.assertEqual(state.run_key_npc_interaction_phase(), "")
                npc = state.world.npcs[0]
                npc.is_key_npc = True
                npc.faction_tag = "independent"
                self.assertEqual(state.run_key_npc_interaction_phase(), "")
            finally:
                state.close()

    def test_key_npc_phase_creates_event_and_updates_status(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 114)
            try:
                npc_a, npc_b = state.world.npcs[:2]
                for npc in (npc_a, npc_b):
                    npc.is_key_npc = True
                    npc.prominent = True
                    npc.faction_tag = "local_traders"
                state.world.normalize_relationship_records()
                state.world.npc_relationships = []
                state.world.last_key_npc_phase_day = 0
                player = state.world.player_state
                from app.key_npcs import ensure_relationship_record

                relationship = ensure_relationship_record(state.world, npc_a, npc_b, state.rng)
                relationship.relationship_state = "ally"
                state.rng = random.Random(1)
                player.day = 3
                result = state.run_key_npc_interaction_phase()
                self.assertTrue(result)
                self.assertIn("coordin", result.lower())
                self.assertTrue(any(entry.action_type == "faction_phase" for entry in player.timeline_entries))
                self.assertTrue(state.world.faction_status_notes)
            finally:
                state.close()

    def test_older_save_defaults_missing_key_npc_and_relationship_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 115)
            try:
                data = state.world.to_dict()
                data.pop("npc_relationships", None)
                data.pop("faction_status_notes", None)
                data.pop("last_key_npc_phase_day", None)
                npc = data["npcs"][0]
                for key in ("is_key_npc", "key_npc_since", "key_npc_reason", "key_npc_notes", "faction_tag"):
                    npc.pop(key, None)
                restored = type(state.world).from_dict(data)
                self.assertEqual(restored.npc_relationships, [])
                self.assertEqual(restored.faction_status_notes, {})
                self.assertEqual(restored.last_key_npc_phase_day, 0)
                self.assertFalse(restored.npcs[0].is_key_npc)
                self.assertEqual(restored.npcs[0].faction_tag, "unknown")
            finally:
                state.close()

    def test_malformed_relationship_state_recovers_safely(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 116)
            try:
                data = state.world.to_dict()
                data["npc_relationships"] = [
                    {
                        "npc_a_id": state.world.npcs[0].entity_id,
                        "npc_b_id": state.world.npcs[1].entity_id,
                        "relationship_state": "chaotic",
                        "affinity_score": "bad",
                        "recent_event_notes": [1, "usable note"],
                    },
                    {
                        "npc_a_id": state.world.npcs[1].entity_id,
                        "npc_b_id": state.world.npcs[0].entity_id,
                        "relationship_state": "ally",
                    },
                ]
                restored = type(state.world).from_dict(data)
                self.assertEqual(len(restored.npc_relationships), 1)
                relationship = restored.npc_relationships[0]
                self.assertEqual(relationship.relationship_state, "ally")
                self.assertIsInstance(relationship.affinity_score, int)
                self.assertEqual(relationship.recent_event_notes, [])
            finally:
                state.close()


class GuiHelperTests(unittest.TestCase):
    def make_state(self, folder: Path, seed: int = 1) -> GameState:
        state = GameState(
            TableLoader(TABLES),
            Database(folder / "worlds.db"),
            random.Random(seed),
        )
        state.generate_new_region("gui-mode-seed")
        return state

    def test_mode_helper_labels_match_town_and_adventure_split(self):
        self.assertEqual(DEFAULT_GUI_MODE, TOWN_MODE)
        self.assertIn("Create Character", mode_sidebar_labels(TOWN_MODE))
        self.assertIn("Settlement Overview", mode_sidebar_labels(TOWN_MODE))
        self.assertIn("Dungeon Overview", mode_sidebar_labels(ADVENTURE_MODE))
        self.assertIn("Start Downtime", mode_gameplay_labels(TOWN_MODE))
        self.assertIn("Travel to Wilderness", mode_gameplay_labels(ADVENTURE_MODE))
        self.assertEqual(shared_action_labels()[0], "Generate New Region")
        self.assertIn("Journal / World Recap", shared_action_labels())
        self.assertIn("Export Event Log", shared_action_labels())
        self.assertIn("Search Area", action_check_labels())
        with self.assertRaises(ValueError):
            mode_sidebar_labels("Campfire Mode")

    def test_action_availability_rules_cover_world_and_character_prerequisites(self):
        self.assertTrue(
            action_is_enabled(
                "Generate New Region",
                has_world=False,
                has_character=False,
            )
        )
        self.assertTrue(
            action_is_enabled(
                "Journal / World Recap",
                has_world=False,
                has_character=False,
            )
        )
        self.assertFalse(
            action_is_enabled(
                "Create Character",
                has_world=False,
                has_character=False,
            )
        )
        self.assertFalse(
            action_is_enabled(
                "Settlement Overview",
                has_world=False,
                has_character=False,
            )
        )
        self.assertFalse(
            action_is_enabled(
                "Start Downtime",
                has_world=True,
                has_character=False,
            )
        )
        self.assertFalse(
            action_is_enabled(
                "Search Area",
                has_world=True,
                has_character=False,
            )
        )
        self.assertTrue(
            action_is_enabled(
                "Settlement Overview",
                has_world=True,
                has_character=False,
            )
        )
        self.assertTrue(
            action_is_enabled(
                "Start Downtime",
                has_world=True,
                has_character=True,
            )
        )
        self.assertTrue(
            action_is_enabled(
                "Search Area",
                has_world=True,
                has_character=True,
            )
        )

    def test_world_recap_handles_missing_world(self):
        text = format_world_recap(None)
        self.assertIn("WORLD RECAP", text)
        self.assertIn("Generate or load a world first.", text)

    def test_world_recap_surfaces_current_state_summary(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 117)
            try:
                state.create_character("Recap Watcher", "Ranger", state.character_backgrounds()[0])
                world = state.world
                npc = world.npcs[0]
                npc.is_key_npc = True
                npc.faction_tag = "local_traders"
                npc.key_npc_reason = "They have become central to local intrigue."
                world.faction_status_notes["local_traders"] = "stable"
                world.player_state.event_log.append("A market whisper points back to the shrine.")
                text = format_world_recap(world)
                self.assertIn("Seed: gui-mode-seed", text)
                self.assertIn("Character: Recap Watcher, Ranger", text)
                self.assertIn("ACTIVE LEADS", text)
                self.assertIn("QUEST NOTES", text)
                self.assertIn("KEY NPCS", text)
                self.assertIn(npc.name, text)
                self.assertIn("local_traders: stable", text)
                self.assertIn("JOURNAL SUMMARY", text)
            finally:
                state.close()


if __name__ == "__main__":
    unittest.main()
