import json
import random
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app.database import Database
from app.dice import morale_check, reaction_roll, roll
from app.game_state import GameState
from app.table_loader import TableLoader


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

    def test_generated_world_contract(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 12)
            world = state.generate_new_region()
            self.assertEqual(len(world.npcs), 10)
            self.assertEqual(len(world.settlement.important_locations), 8)
            self.assertEqual(len(world.dungeon.rooms), 8)
            self.assertEqual(len(world.wilderness.encounter_table), 10)
            location_names = {item.name for item in world.settlement.important_locations}
            self.assertTrue(all(npc.location in location_names for npc in world.npcs))
            npc_names = {npc.name for npc in world.npcs}
            for location in world.settlement.important_locations:
                self.assertIn(location.owner_or_keeper, npc_names)
                self.assertIn(location.owner_or_keeper, location.associated_npcs)
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
            self.assertTrue(world.settlement.problem_connection)
            self.assertIn(world.settlement.name, world.dungeon.connection_to_town)
            self.assertIn(
                world.settlement.important_locations[0].name,
                world.dungeon.connection_to_town,
            )
            for encounter in world.wilderness.encounter_table:
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

    def test_save_load_round_trip_and_normalized_rows(self):
        with tempfile.TemporaryDirectory() as temp:
            state = self.make_state(Path(temp), 4)
            original = state.generate_new_region()
            world_id = state.save_world("Test Save")
            loaded = state.load_world(world_id)
            self.assertEqual(loaded.name, "Test Save")
            self.assertEqual(loaded.settlement, original.settlement)
            self.assertEqual(loaded.npcs, original.npcs)
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
            for location in data["settlement"]["important_locations"]:
                location.pop("associated_npcs")
            restored = type(world).from_dict(data)
            self.assertEqual(restored.settlement.problem_connection, restored.settlement.local_problem)
            self.assertTrue(
                all(not location.associated_npcs for location in restored.settlement.important_locations)
            )
            state.close()


if __name__ == "__main__":
    unittest.main()
