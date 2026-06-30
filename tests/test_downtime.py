"""Unit tests for app.downtime module."""

import random
import unittest
from pathlib import Path

from app.downtime import DowntimeEngine
from app.models import (
    ActiveDowntimeTask,
    AdventureHook,
    Dungeon,
    DungeonRoom,
    Encounter,
    Location,
    NPC,
    PlayerCharacter,
    PlayerState,
    Settlement,
    WildernessArea,
    World,
)
from app.table_loader import TableLoader


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "data" / "tables"


def _make_character():
    return PlayerCharacter(
        name="Tester",
        character_class="Fighter",
        background="Soldier",
        starting_supplies=10,
        bonuses={"combat": 2, "exploration": 1, "social": 0, "lore": 0, "survival": 1, "stealth": 0},
    )


def _make_world(player=None):
    if player is None:
        player = PlayerState(character=_make_character())
    return World(
        name="Test World",
        settlement=Settlement(
            name="Testville",
            type="Village",
            population=200,
            wealth_level="Modest",
            government_type="Council",
            main_industry="Farming",
            secondary_industry="Trade",
            condition="Fair",
            local_problem="Rats",
            local_secret="Hidden cave",
            nearby_danger="Goblins",
            weird_fantasy_detail="Floating stones",
            important_locations=[
                Location(
                    name="Market",
                    type="market",
                    condition="Good",
                    owner_or_keeper="Bob",
                    public_description="Busy",
                    hidden_detail="Secret",
                    rumor_connected="Odd",
                    possible_encounter="Thief",
                    useful_resource="Supplies",
                    entity_id="loc_001",
                )
            ],
            rumors=["A rumor"],
        ),
        npcs=[
            NPC(
                name="Bob",
                age=40,
                ancestry="Human",
                profession="Merchant",
                location="Market",
                appearance="Stout",
                personality="Jovial",
                motivation="Profit",
                fear="Bandits",
                secret="Smuggler",
                relationship_to_town="Resident",
                attitude_toward_player="Friendly",
                useful_information="Knows the roads",
                possible_service="Trade goods",
                danger_level="Low",
                entity_id="npc_001",
                location_id="loc_001",
            )
        ],
        dungeon=Dungeon(
            name="Dark Caves",
            entrance_description="Dark",
            theme="Horror",
            danger_level="High",
            number_of_rooms=3,
            boss_or_final_threat="Dragon",
            treasure_or_secret="Gold",
            connection_to_town="Old mine",
            rooms=[
                DungeonRoom(
                    room_id=1,
                    name="Entrance Hall",
                    description="A dark hall",
                    exits=[2],
                    what_player_notices_first="Darkness",
                    contents="Empty",
                    danger="None",
                    monster_or_npc="None",
                    trap_or_hazard="None",
                    clue="Scratches",
                    treasure="None",
                    noncombat_resolution_options="None",
                    preparation_that_helps="Torch",
                    retreat_option="Back to entrance",
                    entity_id="room_001",
                )
            ],
        ),
        wilderness=WildernessArea(
            name="Wild Forest",
            terrain_type="Forest",
            weather="Rainy",
            dominant_feature="Ancient trees",
            resources="Wood",
            travel_hazards="Mud",
            encounter_table=[
                Encounter(
                    what_player_notices_first="Rustling",
                    encounter_type="Beast",
                    creature_or_npc="Wolf",
                    intent="Hunt",
                    danger_level="Medium",
                    signs_or_foreshadowing="Tracks",
                    how_to_avoid="Stay quiet",
                    how_to_negotiate="Impossible",
                    how_to_fight_safely="Use fire",
                    preparation_that_helps="Torches",
                    reward_or_clue="Pelt",
                    morale=7,
                    reaction_roll_result="Hostile",
                    entity_id="enc_001",
                )
            ],
        ),
        adventure_hook=AdventureHook(
            trigger="Letter",
            major_goal="Find artifact",
            obstacle="Guardian",
            location="Temple",
            location_feature="Altar",
            phenomenon="Magic",
            villain_goal="Domination",
            artifact_or_relic="Orb",
            theme="Mystery",
            key_npc="Sage",
            first_clue="Map",
            time_pressure="Moon",
            failure_consequence="Doom",
            noncombat_paths="Diplomacy",
            entity_id="hook_001",
        ),
        local_threat="Goblins",
        player_state=player,
        created_at="2024-01-01",
    )


class DowntimeEngineAvailableTasksTests(unittest.TestCase):
    def setUp(self):
        self.world = _make_world()
        self.tables = TableLoader(TABLES)
        self.rng = random.Random(42)
        self.engine = DowntimeEngine(self.world, self.tables, self.rng)

    def test_returns_list(self):
        tasks = self.engine.available_tasks()
        self.assertIsInstance(tasks, list)

    def test_tasks_have_task_key(self):
        tasks = self.engine.available_tasks()
        for task in tasks:
            self.assertIn("task_key", task)
            self.assertIn("name", task)


class DowntimeEngineStartTaskTests(unittest.TestCase):
    def setUp(self):
        self.world = _make_world()
        self.tables = TableLoader(TABLES)
        self.rng = random.Random(42)
        self.engine = DowntimeEngine(self.world, self.tables, self.rng)

    def test_start_task_requires_character(self):
        self.world.player_state.character = None
        with self.assertRaises(RuntimeError):
            self.engine.start_task("rest_and_recover")

    def test_start_unknown_task_raises(self):
        with self.assertRaises(ValueError):
            self.engine.start_task("nonexistent_task_key")

    def test_start_task_creates_active_task(self):
        tasks = self.engine.available_tasks()
        if not tasks:
            self.skipTest("No downtime tasks available")
        task_key = tasks[0]["task_key"]
        result = self.engine.start_task(task_key)
        self.assertIn("Started", result)
        self.assertIsNotNone(self.world.player_state.active_downtime_task)

    def test_cannot_start_second_task(self):
        tasks = self.engine.available_tasks()
        if not tasks:
            self.skipTest("No downtime tasks available")
        task_key = tasks[0]["task_key"]
        self.engine.start_task(task_key)
        with self.assertRaises(RuntimeError):
            self.engine.start_task(task_key)


class DowntimeEngineAdvanceTaskTests(unittest.TestCase):
    def setUp(self):
        self.world = _make_world()
        self.tables = TableLoader(TABLES)
        self.rng = random.Random(42)
        self.engine = DowntimeEngine(self.world, self.tables, self.rng)

    def test_advance_requires_character(self):
        self.world.player_state.character = None
        with self.assertRaises(RuntimeError):
            self.engine.advance_task()

    def test_advance_requires_active_task(self):
        with self.assertRaises(RuntimeError):
            self.engine.advance_task()

    def test_advance_zero_days_raises(self):
        tasks = self.engine.available_tasks()
        if not tasks:
            self.skipTest("No downtime tasks available")
        self.engine.start_task(tasks[0]["task_key"])
        with self.assertRaises(ValueError):
            self.engine.advance_task(days=0)

    def test_advance_negative_days_raises(self):
        tasks = self.engine.available_tasks()
        if not tasks:
            self.skipTest("No downtime tasks available")
        self.engine.start_task(tasks[0]["task_key"])
        with self.assertRaises(ValueError):
            self.engine.advance_task(days=-1)

    def test_advance_progresses_task(self):
        tasks = self.engine.available_tasks()
        if not tasks:
            self.skipTest("No downtime tasks available")
        self.engine.start_task(tasks[0]["task_key"])
        initial_progress = self.world.player_state.active_downtime_task.progress_days
        self.engine.advance_task(days=1)
        if self.world.player_state.active_downtime_task is not None:
            self.assertGreater(
                self.world.player_state.active_downtime_task.progress_days,
                initial_progress,
            )

    def test_advance_to_completion(self):
        tasks = self.engine.available_tasks()
        if not tasks:
            self.skipTest("No downtime tasks available")
        self.engine.start_task(tasks[0]["task_key"])
        required = self.world.player_state.active_downtime_task.required_days
        self.engine.advance_task(days=required)
        self.assertIsNone(self.world.player_state.active_downtime_task)


class DowntimeEngineSummarizeTests(unittest.TestCase):
    def test_summarize_none(self):
        self.assertEqual(DowntimeEngine.summarize(None), "None")

    def test_summarize_active_task(self):
        task = ActiveDowntimeTask(
            task_key="rest",
            name="Rest",
            category="recovery",
            required_days=3,
            progress_days=1,
        )
        summary = DowntimeEngine.summarize(task)
        self.assertIn("Rest", summary)
        self.assertIn("1/3", summary)
        self.assertIn("2 remaining", summary)


class DowntimeEngineSerializeTests(unittest.TestCase):
    def test_serialize_none(self):
        self.assertIsNone(DowntimeEngine.serialize(None))

    def test_serialize_task(self):
        task = ActiveDowntimeTask(
            task_key="rest",
            name="Rest",
            category="recovery",
            required_days=3,
            progress_days=1,
        )
        data = DowntimeEngine.serialize(task)
        self.assertIsInstance(data, dict)
        self.assertEqual(data["task_key"], "rest")
        self.assertEqual(data["progress_days"], 1)


class DowntimeCompletionEffectsTests(unittest.TestCase):
    def setUp(self):
        self.world = _make_world()
        self.tables = TableLoader(TABLES)
        self.rng = random.Random(42)
        self.engine = DowntimeEngine(self.world, self.tables, self.rng)

    def test_recovery_reduces_wounds(self):
        self.world.player_state.wounds = 2
        task = ActiveDowntimeTask(
            task_key="recover",
            name="Recovery",
            category="recovery",
            required_days=1,
            progress_days=0,
            progress_text="Resting ({progress_days}/{total_days} days).",
            completion_text="Recovery done.",
            complication_text="Setback.",
        )
        self.world.player_state.active_downtime_task = task
        self.engine.advance_task(days=1)
        self.assertLessEqual(self.world.player_state.wounds, 2)

    def test_labor_earns_coin(self):
        initial_coin = self.world.player_state.coin
        task = ActiveDowntimeTask(
            task_key="labor",
            name="Labor",
            category="labor",
            required_days=1,
            progress_days=0,
            progress_text="Working ({progress_days}/{total_days} days).",
            completion_text="Job done.",
            complication_text="Trouble.",
        )
        self.world.player_state.active_downtime_task = task
        self.engine.advance_task(days=1)
        self.assertGreater(self.world.player_state.coin, initial_coin)

    def test_craft_gives_supplies(self):
        initial_supplies = self.world.player_state.supplies
        task = ActiveDowntimeTask(
            task_key="craft",
            name="Crafting",
            category="craft",
            required_days=1,
            progress_days=0,
            progress_text="Crafting ({progress_days}/{total_days} days).",
            completion_text="Item ready.",
            complication_text="Material lost.",
        )
        self.world.player_state.active_downtime_task = task
        self.engine.advance_task(days=1)
        self.assertGreater(self.world.player_state.supplies, initial_supplies)

    def test_training_adds_quest_log(self):
        task = ActiveDowntimeTask(
            task_key="train",
            name="Weapon Training",
            category="training",
            required_days=1,
            progress_days=0,
            progress_text="Training ({progress_days}/{total_days} days).",
            completion_text="Training complete.",
            complication_text="Strained.",
        )
        self.world.player_state.active_downtime_task = task
        self.engine.advance_task(days=1)
        self.assertTrue(
            any("edge" in note.lower() or "training" in note.lower()
                for note in self.world.player_state.quest_log)
        )

    def test_trade_adds_lead(self):
        task = ActiveDowntimeTask(
            task_key="trade",
            name="Trade Negotiation",
            category="trade",
            required_days=1,
            progress_days=0,
            progress_text="Negotiating ({progress_days}/{total_days} days).",
            completion_text="Deal closed.",
            complication_text="Haggling.",
        )
        self.world.player_state.active_downtime_task = task
        self.engine.advance_task(days=1)
        self.assertTrue(len(self.world.player_state.lead_records) > 0)


class DowntimeEngineLeadCategoryTests(unittest.TestCase):
    def test_lead_category_training(self):
        task = ActiveDowntimeTask(task_key="t", name="T", category="training")
        self.assertEqual(DowntimeEngine._lead_category_for_task(task), "downtime")

    def test_lead_category_social(self):
        task = ActiveDowntimeTask(task_key="t", name="T", category="social")
        self.assertEqual(DowntimeEngine._lead_category_for_task(task), "talk")

    def test_lead_category_investigation(self):
        task = ActiveDowntimeTask(task_key="t", name="T", category="investigation")
        self.assertEqual(DowntimeEngine._lead_category_for_task(task), "investigate")

    def test_lead_category_craft(self):
        task = ActiveDowntimeTask(task_key="t", name="T", category="craft")
        self.assertEqual(DowntimeEngine._lead_category_for_task(task), "explore")

    def test_lead_category_other(self):
        task = ActiveDowntimeTask(task_key="t", name="T", category="bizarre")
        self.assertEqual(DowntimeEngine._lead_category_for_task(task), "other")


if __name__ == "__main__":
    unittest.main()
