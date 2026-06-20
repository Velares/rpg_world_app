import json
import random
import tempfile
import unittest
from pathlib import Path

from app.calendar import TIME_PERIODS
from app.database import Database
from app.exporters import (
    export_character_text,
    export_event_log_text,
    export_world_summary,
)
from app.game_state import GameState
from app.models import InventoryItem
from app.table_loader import TableLoader


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "data" / "tables"


class StressTests(unittest.TestCase):
    def make_state(self, folder: Path, seed: int = 1, tables: Path = TABLES) -> GameState:
        return GameState(
            TableLoader(tables),
            Database(folder / "worlds.db"),
            random.Random(seed),
        )

    def assert_valid_state(self, state: GameState) -> None:
        if state.world is None:
            return
        world = state.world
        player = world.player_state
        self.assertTrue(
            world.generation_seed is None or isinstance(world.generation_seed, str)
        )
        self.assertIsNotNone(world.settlement)
        self.assertIsNotNone(world.dungeon)
        self.assertIsNotNone(world.wilderness)
        self.assertIsNotNone(world.adventure_hook)
        self.assertIsInstance(player.day, int)
        self.assertGreaterEqual(player.day, 1)
        self.assertIn(player.time_period, TIME_PERIODS)
        self.assertIsInstance(player.age_days_accumulated, int)
        self.assertGreaterEqual(player.age_days_accumulated, 0)
        for resource_name in (
            "supplies",
            "torches",
            "light_turns_remaining",
            "food",
            "water",
            "coin",
            "wounds",
            "position",
            "attention",
            "turns_elapsed",
        ):
            value = getattr(player, resource_name)
            self.assertIsInstance(value, int, resource_name)
        if player.character is not None:
            self.assertIsInstance(player.character.age_years, int)
            self.assertGreaterEqual(player.character.age_years, 0)
            self.assertIsInstance(player.character.bonuses, dict)
        self.assertIsInstance(player.inventory, list)
        for item in player.inventory:
            self.assertIsInstance(item, InventoryItem)
            self.assertIsInstance(item.item_key, str)
            self.assertTrue(item.item_key)
            self.assertIsInstance(item.name, str)
            self.assertTrue(item.name)
            self.assertIsInstance(item.quantity, int)
            self.assertGreater(item.quantity, 0)
        self.assertTrue(all(isinstance(entry, str) for entry in player.event_log))
        self.assertTrue(all(isinstance(entry, str) for entry in player.action_log))
        self.assertIsInstance(player.timeline_entries, list)
        for entry in player.timeline_entries:
            self.assertIsInstance(entry.day, int)
            self.assertGreaterEqual(entry.day, 1)
            self.assertIn(entry.time_period, TIME_PERIODS)
            self.assertIsInstance(entry.action_type, str)
            self.assertTrue(entry.action_type)
            self.assertIsInstance(entry.result_text, str)
        self.assertIsInstance(player.quest_log, list)
        self.assertIsInstance(player.leads, list)
        self.assertTrue(all(isinstance(value, str) for value in player.known_npc_ids))
        self.assertTrue(all(isinstance(value, str) for value in player.known_location_ids))
        self.assertTrue(all(isinstance(value, int) for value in player.known_rumor_indices))
        self.assertTrue(all(isinstance(value, str) for value in player.known_threats))
        self.assertTrue(all(isinstance(value, int) for value in player.discovered_room_ids))
        valid_encounters = {enc.entity_id for enc in world.wilderness.encounter_table}
        self.assertTrue(
            player.pending_encounter_id == "" or player.pending_encounter_id in valid_encounters
        )
        for npc in world.npcs:
            self.assertIsInstance(npc.interaction_count, int)
            self.assertGreaterEqual(npc.interaction_count, 0)
            self.assertIsInstance(npc.prominence_score, int)
            self.assertGreaterEqual(npc.prominence_score, 0)
            self.assertIsInstance(npc.prominent, bool)
            self.assertIsInstance(npc.is_key_npc, bool)
            self.assertIsInstance(npc.faction_tag, str)
            self.assertIsInstance(npc.recent_interaction_notes, list)
            self.assertTrue(all(isinstance(note, str) for note in npc.recent_interaction_notes))
        self.assertIsInstance(world.npc_relationships, list)
        seen_pairs = set()
        for relationship in world.npc_relationships:
            pair = tuple(sorted((relationship.npc_a_id, relationship.npc_b_id)))
            self.assertEqual(pair, (relationship.npc_a_id, relationship.npc_b_id))
            self.assertNotIn(pair, seen_pairs)
            seen_pairs.add(pair)
            self.assertIn(relationship.relationship_state, {"ally", "at_odds", "neutral", "unknown"})
            self.assertIsInstance(relationship.recent_event_notes, list)
        self.assertIsInstance(world.faction_status_notes, dict)
        if player.current_room_id is not None:
            valid_rooms = {room.room_id for room in world.dungeon.rooms}
            self.assertIn(player.current_room_id, valid_rooms)
        if player.active_downtime_task is not None:
            active = player.active_downtime_task
            self.assertIsInstance(active.task_key, str)
            self.assertTrue(active.task_key)
            self.assertIsInstance(active.required_days, int)
            self.assertGreater(active.required_days, 0)
            self.assertIsInstance(active.progress_days, int)
            self.assertGreaterEqual(active.progress_days, 0)

    def test_no_world_and_no_character_actions_fail_cleanly(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 201)
            self.assertIn("NO ACTIVE WORLD", export_world_summary(None))
            self.assertIn("NO ACTIVE WORLD", export_character_text(None))
            self.assertIn("NO ACTIVE WORLD", export_event_log_text(None))
            guarded_calls = [
                lambda: state.save_world("Before Generate"),
                lambda: state.travel("town"),
                state.search,
                state.talk_to_npc,
                state.inspect_location,
                state.rest,
                state.retreat,
                lambda: state.start_downtime_task("train_skill"),
            ]
            for call in guarded_calls:
                with self.assertRaises(RuntimeError) as ctx:
                    call()
                self.assertTrue(str(ctx.exception))
            with self.assertRaises(RuntimeError):
                state.advance_downtime(1)
            world = state.generate_new_region()
            result = state.perform_check("search_area", "Standard", roll_override=12)
            self.assertEqual(result.outcome, "success")
            self.assertIn("NO PLAYER CHARACTER", export_character_text(world))
            with self.assertRaises(RuntimeError):
                state.start_downtime_task("train_skill")
            with self.assertRaises(RuntimeError):
                state.advance_downtime(1)
            self.assert_valid_state(state)
            state.close()

    def test_repeated_actions_and_repeated_saves_remain_stable(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 202)
            save_ids = []
            for seed_name in ("First", "Second", "Third"):
                world = state.generate_new_region()
                self.assertTrue(world.player_state.event_log)
                self.assert_valid_state(state)
                save_ids.append(state.save_world(seed_name))
            self.assertEqual(len(state.list_worlds()), 3)
            loaded = state.load_world(save_ids[0])
            self.assertIsNotNone(loaded.player_state)
            for _ in range(8):
                state.search()
                state.talk_to_npc()
            state.travel("wilderness")
            for _ in range(8):
                try:
                    state.search()
                except RuntimeError:
                    pass
            state.travel("dungeon_entrance")
            state.explore_current_area()
            for _ in range(8):
                try:
                    state.search()
                except RuntimeError:
                    pass
            for _ in range(4):
                state.retreat()
            self.assert_valid_state(state)
            state.close()

    def test_illogical_sequences_fail_gracefully_without_corruption(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 203)
            try:
                state.generate_new_region()
                self.assertIn("already within the relative safety of town", state.retreat())
                state.world.player_state.food = 0
                state.world.player_state.water = 0
                hardship = state.rest()
                self.assertIn("Rest without food or water", hardship)
                with self.assertRaises(RuntimeError):
                    state.resolve_encounter("investigate")
                with self.assertRaises(RuntimeError):
                    state.advance_downtime(1)
                with self.assertRaises(RuntimeError):
                    state.start_downtime_task("maintain_equipment")
                state.create_character("Logic Guard", "Ranger", state.character_backgrounds()[0])
                state.start_downtime_task("maintain_equipment")
                with self.assertRaises(RuntimeError):
                    state.start_downtime_task("train_skill")
                self.assertEqual(state.remove_inventory_item("missing"), 0)
                added = state.add_inventory_item("??? strange object ???", quantity=1)
                self.assertTrue(added.item_key.startswith("legacy_"))
                with self.assertRaises(ValueError):
                    state.add_inventory_item("bad quantity", quantity="two")
                with self.assertRaises(ValueError):
                    state.remove_inventory_item("missing", quantity="one")
                self.assertIn(state.world.name.upper(), export_world_summary(state.world))
                self.assert_valid_state(state)
            finally:
                state.close()

    def test_corrupt_calendar_and_time_fields_load_safely(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 204)
            world = state.generate_new_region()
            data = world.to_dict()
            data["player_state"]["day"] = "bad-day"
            data["player_state"]["time_period"] = "Twilight"
            data["player_state"]["age_days_accumulated"] = -8
            restored = type(world).from_dict(data)
            self.assertEqual(restored.player_state.day, 1)
            self.assertEqual(restored.player_state.time_period, "Morning")
            self.assertEqual(restored.player_state.age_days_accumulated, 0)
            self.assertEqual(restored.player_state.event_log[0], world.player_state.event_log[0])
            state.close()

    def test_missing_interaction_category_and_malformed_weighted_entries_fall_back(self):
        with tempfile.TemporaryDirectory() as temp:
            table_dir = Path(temp)
            for path in TABLES.glob("*.json"):
                data = json.loads(path.read_text(encoding="utf-8"))
                if path.name == "interaction_tables.json":
                    data.pop("npc_dialogue_warning", None)
                    data["check_success_additions"] = [{"value": "", "weight": 0}, {"weight": 1}]
                (table_dir / path.name).write_text(json.dumps(data), encoding="utf-8")
            state = self.make_state(table_dir, 205, tables=table_dir)
            world = state.generate_new_region()
            self.assertIsNotNone(world)
            self.assertTrue(state.tables.warnings)
            self.assertTrue(
                any("Missing required table: interaction_tables.npc_dialogue_warning" in warning
                    for warning in state.tables.warnings)
            )
            self.assert_valid_state(state)
            state.close()

    def test_repeated_exports_and_old_save_then_new_actions(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 206)
            world = state.generate_new_region()
            save_id = state.save_world("Oldish Save")
            loaded = state.load_world(save_id)
            loaded_data = loaded.to_dict()
            loaded_data["player_state"]["character"] = None
            loaded_data["player_state"].pop("active_downtime_task", None)
            loaded_data["player_state"].pop("age_days_accumulated", None)
            loaded_data["player_state"].pop("timeline_entries", None)
            loaded_data.pop("npc_relationships", None)
            loaded_data.pop("faction_status_notes", None)
            for npc in loaded_data["npcs"]:
                npc.pop("prominent", None)
                npc.pop("recent_interaction_notes", None)
                npc.pop("is_key_npc", None)
                npc.pop("faction_tag", None)
            restored = type(loaded).from_dict(loaded_data)
            state.world = restored
            self.assertIn("NO PLAYER CHARACTER", export_character_text(state.world))
            self.assertIn("EVENT LOG", export_event_log_text(state.world))
            with self.assertRaises(RuntimeError):
                state.advance_downtime(2)
            result = state.perform_check("search_area", "Standard", roll_override=12)
            self.assertEqual(result.outcome, "success")
            self.assert_valid_state(state)
            state.close()

    def test_deterministic_randomized_stress_sequence_preserves_invariants(self):
        with tempfile.TemporaryDirectory() as temp:
            rng = random.Random(207)
            state = self.make_state(Path(temp), 207)
            state.generate_new_region()
            state.create_character("Stress Tester", "Ranger", state.character_backgrounds()[0])
            saved_ids = []
            action_keys = [
                "search_area",
                "sneak_past_danger",
                "read_ancient_markings",
                "negotiate_with_npc",
                "track_creature",
                "force_dangerous_action",
            ]
            for index in range(180):
                choice = rng.choice(
                    [
                        "travel",
                        "explore",
                        "search",
                        "talk",
                        "inspect_location",
                        "inspect_room",
                        "rest",
                        "full_rest",
                        "retreat",
                        "encounter",
                        "check",
                        "downtime_start",
                        "downtime_advance",
                        "save",
                        "load",
                        "inventory",
                        "generate",
                        "character",
                    ]
                )
                try:
                    if choice == "travel":
                        state.travel(rng.choice(["town", "wilderness", "dungeon_entrance"]))
                    elif choice == "explore":
                        state.explore_current_area()
                    elif choice == "search":
                        state.search()
                    elif choice == "talk":
                        state.talk_to_npc()
                    elif choice == "inspect_location":
                        state.inspect_location()
                    elif choice == "inspect_room":
                        state.inspect_room()
                    elif choice == "rest":
                        state.rest()
                    elif choice == "full_rest":
                        state.full_rest()
                    elif choice == "retreat":
                        state.retreat()
                    elif choice == "encounter":
                        state.resolve_encounter(rng.choice(["avoid", "approach", "investigate", "retreat"]))
                    elif choice == "check":
                        state.perform_check(
                            rng.choice(action_keys),
                            rng.choice(["Easy", "Standard", "Hard", "Severe"]),
                            roll_override=((index % 20) + 1),
                        )
                    elif choice == "downtime_start":
                        tasks = state.available_downtime_tasks()
                        if tasks:
                            state.start_downtime_task(rng.choice(tasks)["task_key"])
                    elif choice == "downtime_advance":
                        state.advance_downtime(rng.randint(1, 3))
                    elif choice == "save":
                        saved_ids.append(state.save_world(f"Stress Save {index}"))
                    elif choice == "load" and saved_ids:
                        state.load_world(rng.choice(saved_ids))
                    elif choice == "inventory":
                        if rng.random() < 0.5:
                            state.add_inventory_item("stress token", quantity=1)
                        else:
                            state.remove_inventory_item("stress token", quantity=1)
                    elif choice == "generate":
                        state.generate_new_region()
                    elif choice == "character" and state.world.player_state.character is None:
                        state.create_character(
                            f"Stress {index}",
                            rng.choice([cls.class_name for cls in state.character_classes()]),
                            rng.choice(state.character_backgrounds()),
                        )
                except (RuntimeError, ValueError) as exc:
                    self.assertTrue(str(exc))
                self.assert_valid_state(state)
            state.close()


if __name__ == "__main__":
    unittest.main()
