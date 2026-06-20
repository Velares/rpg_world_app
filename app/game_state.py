from __future__ import annotations

import hashlib
import random
from datetime import datetime

from app.calendar import append_timeline_entry
from app.database import Database
from app.characters import CharacterFactory
from app.checks import ActionResolver
from app.downtime import DowntimeEngine
from app.exploration import ExplorationEngine
from app.generators.adventure_generator import AdventureGenerator
from app.generators.dungeon_generator import DungeonGenerator
from app.generators.hex_generator import HexGenerator
from app.generators.npc_generator import NPCGenerator
from app.generators.settlement_generator import SettlementGenerator
from app.generators.wilderness_generator import WildernessGenerator
from app.models import InventoryItem, PlayerState, World
from app.name_generator import NameGenerator
from app.table_loader import TableLoader


class GameState:
    def __init__(
        self,
        tables: TableLoader,
        database: Database,
        rng: random.Random | None = None,
    ):
        self.tables = tables
        self.database = database
        self._default_rng = rng or random.Random()
        self.rng = self._default_rng
        self.world: World | None = None
        self.active_seed: str | None = None
        self._refresh_name_generator()

    @staticmethod
    def normalize_seed(seed: str | None) -> str | None:
        if seed is None:
            return None
        text = str(seed).strip()
        return text or None

    @classmethod
    def seed_value(cls, seed: str) -> int:
        normalized = cls.normalize_seed(seed)
        if normalized is None:
            raise ValueError("Seed text is required.")
        digest = hashlib.sha256(normalized.encode("utf-8")).digest()
        return int.from_bytes(digest[:8], "big", signed=False)

    def _refresh_name_generator(self) -> None:
        first_name_fallbacks = [
            *self.tables.get("npc_tables", "male_names"),
            *self.tables.get("npc_tables", "female_names"),
            *self.tables.get("npc_tables", "neutral_names"),
        ]
        self.name_generator = NameGenerator(
            self.tables.tables_dir.parent / "names",
            self.rng,
            fallback_first_names=first_name_fallbacks,
            fallback_last_names=self.tables.get("npc_tables", "surnames"),
        )

    def set_seed(self, seed: str | None) -> str | None:
        normalized = self.normalize_seed(seed)
        self.active_seed = normalized
        self.rng = (
            random.Random(self.seed_value(normalized))
            if normalized is not None
            else self._default_rng
        )
        self._refresh_name_generator()
        return self.active_seed

    def generate_new_region(self, seed: str | None = None) -> World:
        self.set_seed(seed)
        settlement = SettlementGenerator(self.tables, self.rng).generate()
        npcs = NPCGenerator(
            self.tables, self.rng, self.name_generator
        ).generate(settlement.important_locations, 10)
        # Build both sides of the NPC/location relationship for reliable inspection.
        npcs_by_location = {
            location.name: [npc for npc in npcs if npc.location == location.name]
            for location in settlement.important_locations
        }
        for index, location in enumerate(settlement.important_locations):
            residents = npcs_by_location[location.name]
            if residents:
                location.owner_or_keeper = residents[0].name
                location.associated_npcs = [npc.name for npc in residents]
                location.owner_npc_id = residents[0].entity_id
                location.associated_npc_ids = [npc.entity_id for npc in residents]
            else:
                # Every important location receives a keeper, and that NPC is reassigned
                # consistently so no building becomes an orphaned generated detail.
                keeper = npcs[index % len(npcs)]
                old_location = keeper.location
                keeper.location = location.name
                keeper.location_id = location.entity_id
                location.owner_or_keeper = keeper.name
                location.associated_npcs = [keeper.name]
                location.owner_npc_id = keeper.entity_id
                location.associated_npc_ids = [keeper.entity_id]
                npcs_by_location[old_location] = [
                    npc for npc in npcs_by_location[old_location] if npc is not keeper
                ]
                npcs_by_location[location.name] = [keeper]
        dungeon = DungeonGenerator(self.tables, self.rng).generate(settlement, 8)
        wilderness = WildernessGenerator(self.tables, self.rng).generate(
            10, settlement=settlement, dungeon=dungeon
        )
        hook = AdventureGenerator(self.tables, self.rng).generate(settlement, npcs, dungeon)
        self._connect_region(settlement, npcs, dungeon, wilderness, hook)
        hex_generator = HexGenerator(self.tables, self.rng)
        hexes = [
            hex_generator.generate(0, 0, True),
            hex_generator.generate(1, 0),
            hex_generator.generate(0, 1),
            hex_generator.generate(-1, 1),
        ]
        player_state = PlayerState(
            current_location="town",
            current_location_id=settlement.important_locations[0].entity_id,
            quest_log=[f"Investigate {hook.major_goal}"],
            hexes=hexes,
            known_npc_ids=[npcs[0].entity_id],
            known_location_ids=[settlement.important_locations[0].entity_id],
            known_rumor_indices=[0],
            leads=[
                f"Ask {npcs[0].name} why travelers avoid the road toward {dungeon.name}."
            ],
        )
        self.world = World(
            name=f"The {settlement.name} Region",
            settlement=settlement,
            npcs=npcs,
            dungeon=dungeon,
            wilderness=wilderness,
            adventure_hook=hook,
            local_threat=settlement.nearby_danger,
            player_state=player_state,
            created_at=datetime.now().astimezone().isoformat(timespec="seconds"),
            generation_seed=self.active_seed,
        )
        append_timeline_entry(
            self.world.player_state,
            f"You begin in {settlement.name}. A frightened rumor offers a lead, not an answer.",
            action_type="world_start",
            location_context="town",
            location_id=settlement.important_locations[0].entity_id,
            location_name=settlement.name,
        )
        return self.world

    def _connect_region(self, settlement, npcs, dungeon, wilderness, hook) -> None:
        """Turn isolated table results into one inspectable local situation."""
        problem_target = self.rng.choice(["dungeon", "encounter", "hook"])
        if problem_target == "dungeon":
            settlement.problem_connection = (
                f"The problem originates in {dungeon.name}: {dungeon.connection_to_town}"
            )
            settlement.problem_target_type = "dungeon_room"
            settlement.problem_target_id = dungeon.rooms[0].entity_id
        elif problem_target == "encounter":
            encounter = self.rng.choice(wilderness.encounter_table)
            settlement.problem_connection = (
                f"The problem is worsened by {encounter.creature_or_npc} in "
                f"{wilderness.name}, which seeks to {encounter.intent}."
            )
            settlement.problem_target_type = "wilderness_encounter"
            settlement.problem_target_id = encounter.entity_id
        else:
            settlement.problem_connection = (
                f"The problem is the opening movement of the adventure hook: "
                f"{hook.major_goal}, before {hook.time_pressure.lower()}."
            )
            settlement.problem_target_type = "adventure_hook"
            settlement.problem_target_id = hook.entity_id

        # Every rumor names real generated content and doubles as a navigation clue.
        featured_encounter = wilderness.encounter_table[0]
        featured_location = settlement.important_locations[0]
        keeper = featured_location.owner_or_keeper
        settlement.rumors = [
            f"{hook.key_npc} claims the road to {dungeon.name} changes beneath a moonless sky.",
            f"{keeper} of {featured_location.name} has seen signs of "
            f"{settlement.nearby_danger.lower()} beneath the floorboards.",
            f"Travelers in {wilderness.name} encountered {featured_encounter.creature_or_npc}; "
            f"its trail points toward {dungeon.name}.",
            f"{npcs[1].name} at {npcs[1].location} knows why {dungeon.boss_or_final_threat} "
            f"fears {dungeon.rooms[-1].preparation_that_helps}.",
            f"A clue to {hook.artifact_or_relic} is hidden in {dungeon.rooms[0].name}.",
            f"If {hook.major_goal} fails, {hook.failure_consequence.lower()}, and "
            f"{settlement.name} will bear the cost.",
        ]
        featured_location.rumor_connected = settlement.rumors[1]

    def require_world(self) -> World:
        if self.world is None:
            raise RuntimeError("Generate or load a world first.")
        return self.world

    def save_world(self, save_name: str) -> int:
        return self.database.save_world(self.require_world(), save_name)

    def list_worlds(self) -> list[tuple[int, str, str]]:
        return self.database.list_worlds()

    def load_world(self, world_id: int) -> World:
        self.world = self.database.load_world(world_id)
        self.active_seed = self.world.generation_seed
        return self.world

    def exploration(self) -> ExplorationEngine:
        return ExplorationEngine(self.require_world(), self.rng, self.tables)

    def downtime(self) -> DowntimeEngine:
        return DowntimeEngine(self.require_world(), self.tables, self.rng)

    def travel(self, destination: str) -> str:
        return self.exploration().travel(destination)

    def explore_current_area(self) -> str:
        return self.exploration().explore()

    def resolve_encounter(self, choice: str) -> str:
        return self.exploration().resolve_encounter(choice)

    def inspect_room(self) -> str:
        return self.exploration().inspect_room()

    def move_room(self, room_id: int) -> str:
        return self.exploration().move_room(room_id)

    def search(self) -> str:
        return self.exploration().search()

    def talk_to_npc(self) -> str:
        return self.exploration().talk_to_npc()

    def rest(self) -> str:
        return self.exploration().rest("short")

    def full_rest(self) -> str:
        return self.exploration().rest("full")

    def travel_to_location(self, location_id: str) -> str:
        return self.exploration().travel_to_location(location_id)

    def inspect_location(self) -> str:
        return self.exploration().inspect_location()

    def character_classes(self):
        return CharacterFactory(self.tables).classes()

    def character_backgrounds(self) -> list[str]:
        return CharacterFactory(self.tables).backgrounds()

    def create_character(self, name: str, class_name: str, background: str):
        return CharacterFactory(self.tables, self.rng).create(
            self.require_world(), name, class_name, background
        )

    def add_inventory_item(
        self,
        item: InventoryItem | str,
        quantity: int = 1,
        **metadata,
    ):
        return self.require_world().player_state.add_inventory_item(
            item, quantity=quantity, **metadata
        )

    def remove_inventory_item(self, item_key_or_name: str, quantity: int = 1) -> int:
        return self.require_world().player_state.remove_inventory_item(
            item_key_or_name, quantity
        )

    def random_first_name(self) -> str:
        return self.name_generator.first_name()

    def random_last_name(self) -> str:
        return self.name_generator.last_name()

    def random_full_name(self) -> str:
        return self.name_generator.full_name()

    def random_full_names(self, count: int) -> list[str]:
        return self.name_generator.full_names(count)

    def perform_check(
        self,
        action_key: str,
        difficulty_name: str = "Standard",
        roll_override: int | None = None,
        consequence_override: str | None = None,
    ):
        return ActionResolver(self.require_world(), self.rng, self.tables).resolve(
            action_key,
            difficulty_name,
            roll_override=roll_override,
            consequence_override=consequence_override,
        )

    def retreat(self) -> str:
        return self.exploration().retreat()

    def available_downtime_tasks(self) -> list[dict]:
        return self.downtime().available_tasks()

    def start_downtime_task(self, task_key: str) -> str:
        return self.downtime().start_task(task_key)

    def advance_downtime(self, days: int = 1) -> str:
        return self.downtime().advance_task(days)

    def close(self) -> None:
        self.database.close()
