import json
import random
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.database import Database
from app.characters import BONUS_NAMES, CharacterFactory
from app.checks import DIFFICULTIES
from app.dice import morale_check, reaction_roll, roll
from app.game_state import GameState
from app.generators.npc_generator import NPCGenerator
from app.generators.settlement_generator import SettlementGenerator
from app.name_generator import NameDataError, NameGenerator
from app.table_loader import TableLoader
from tools.clean_names import clean_name_file


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
            self.assertEqual(set(character.bonuses), set(BONUS_NAMES))
            self.assertEqual(player.supplies, definition.starting_supplies)
            self.assertEqual(player.food, definition.starting_food)
            self.assertEqual(player.water, definition.starting_water)
            self.assertEqual(player.torches, definition.starting_torches)
            self.assertEqual(player.coin, definition.starting_coin)
            world_id = state.save_world("Character Save")
            loaded = state.load_world(world_id)
            self.assertEqual(loaded.player_state.character, character)
            self.assertTrue(
                any("Sable Vey" in entry for entry in loaded.player_state.event_log)
            )
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


if __name__ == "__main__":
    unittest.main()
