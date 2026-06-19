from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Location:
    name: str
    type: str
    condition: str
    owner_or_keeper: str
    public_description: str
    hidden_detail: str
    rumor_connected: str
    possible_encounter: str
    useful_resource: str
    # Version 0.2 keeps the full location roster instead of only its primary keeper.
    associated_npcs: list[str] = field(default_factory=list)
    entity_id: str = ""
    owner_npc_id: str = ""
    associated_npc_ids: list[str] = field(default_factory=list)


@dataclass
class NPC:
    name: str
    age: int
    ancestry: str
    profession: str
    location: str
    appearance: str
    personality: str
    motivation: str
    fear: str
    secret: str
    relationship_to_town: str
    attitude_toward_player: str
    useful_information: str
    possible_service: str
    danger_level: str
    entity_id: str = ""
    location_id: str = ""


@dataclass
class Settlement:
    name: str
    type: str
    population: int
    wealth_level: str
    government_type: str
    main_industry: str
    secondary_industry: str
    condition: str
    local_problem: str
    local_secret: str
    nearby_danger: str
    weird_fantasy_detail: str
    important_locations: list[Location] = field(default_factory=list)
    rumors: list[str] = field(default_factory=list)
    # Human-readable link to another generated entity driving the local trouble.
    problem_connection: str = ""
    problem_target_type: str = ""
    problem_target_id: str = ""


@dataclass
class DungeonRoom:
    room_id: int
    name: str
    description: str
    exits: list[int]
    what_player_notices_first: str
    contents: str
    danger: str
    monster_or_npc: str
    trap_or_hazard: str
    clue: str
    treasure: str
    noncombat_resolution_options: str
    preparation_that_helps: str
    retreat_option: str
    entity_id: str = ""


@dataclass
class Dungeon:
    name: str
    entrance_description: str
    theme: str
    danger_level: str
    number_of_rooms: int
    boss_or_final_threat: str
    treasure_or_secret: str
    connection_to_town: str
    rooms: list[DungeonRoom] = field(default_factory=list)
    town_location_id: str = ""


@dataclass
class Encounter:
    what_player_notices_first: str
    encounter_type: str
    creature_or_npc: str
    intent: str
    danger_level: str
    signs_or_foreshadowing: str
    how_to_avoid: str
    how_to_negotiate: str
    how_to_fight_safely: str
    preparation_that_helps: str
    reward_or_clue: str
    morale: int
    reaction_roll_result: str
    entity_id: str = ""
    foreshadows_type: str = ""
    foreshadows_id: str = ""


@dataclass
class WildernessArea:
    name: str
    terrain_type: str
    weather: str
    dominant_feature: str
    resources: str
    travel_hazards: str
    encounter_table: list[Encounter] = field(default_factory=list)
    weird_fantasy_detail: str = ""


@dataclass
class AdventureHook:
    trigger: str
    major_goal: str
    obstacle: str
    location: str
    location_feature: str
    phenomenon: str
    villain_goal: str
    artifact_or_relic: str
    theme: str
    key_npc: str
    first_clue: str
    time_pressure: str
    failure_consequence: str
    noncombat_paths: str
    entity_id: str = ""
    key_npc_id: str = ""


@dataclass
class Hex:
    q: int
    r: int
    terrain: str
    feature: str
    encounter_table: str
    danger_level: str
    discovered: bool = False
    notes: str = ""


@dataclass
class PlayerState:
    current_location: str = "town"
    current_room_id: int | None = None
    supplies: int = 10
    torches: int = 6
    light_turns_remaining: int = 0
    food: int = 7
    water: int = 7
    wounds: int = 0
    rest_risk: str = "Unknown"
    inventory: list[str] = field(default_factory=lambda: ["bedroll", "flint and steel"])
    quest_log: list[str] = field(default_factory=list)
    hexes: list[Hex] = field(default_factory=list)
    discovered_room_ids: list[int] = field(default_factory=list)
    pending_encounter_id: str = ""
    action_log: list[str] = field(default_factory=list)
    turns_elapsed: int = 0


@dataclass
class World:
    name: str
    settlement: Settlement
    npcs: list[NPC]
    dungeon: Dungeon
    wilderness: WildernessArea
    adventure_hook: AdventureHook
    local_threat: str
    player_state: PlayerState
    created_at: str
    world_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "World":
        from app.ids import new_id

        settlement_data = data["settlement"]
        # Version 0.1 saves did not include explicit relationship fields.
        settlement_data.setdefault("problem_connection", settlement_data.get("local_problem", ""))
        settlement_data.setdefault("problem_target_type", "")
        settlement_data.setdefault("problem_target_id", "")
        for item in settlement_data.get("important_locations", []):
            item.setdefault("associated_npcs", [])
            item.setdefault("entity_id", new_id("loc"))
            item.setdefault("owner_npc_id", "")
            item.setdefault("associated_npc_ids", [])
        settlement_data["important_locations"] = [
            Location(**item) for item in settlement_data.get("important_locations", [])
        ]
        dungeon_data = data["dungeon"]
        dungeon_data.setdefault("town_location_id", "")
        for item in dungeon_data.get("rooms", []):
            item.setdefault("entity_id", new_id("room"))
        dungeon_data["rooms"] = [DungeonRoom(**item) for item in dungeon_data.get("rooms", [])]
        wilderness_data = data["wilderness"]
        for item in wilderness_data.get("encounter_table", []):
            item.setdefault("entity_id", new_id("enc"))
            item.setdefault("foreshadows_type", "")
            item.setdefault("foreshadows_id", "")
        wilderness_data["encounter_table"] = [
            Encounter(**item) for item in wilderness_data.get("encounter_table", [])
        ]
        player_data = data["player_state"]
        # Version 0.3 exploration fields are defaulted so older saves remain playable.
        player_data.setdefault("current_location", "town")
        player_data.setdefault("current_room_id", None)
        player_data.setdefault("wounds", 0)
        player_data.setdefault("discovered_room_ids", [])
        player_data.setdefault("pending_encounter_id", "")
        player_data.setdefault("action_log", [])
        player_data.setdefault("turns_elapsed", 0)
        player_data["hexes"] = [Hex(**item) for item in player_data.get("hexes", [])]
        npc_data = data.get("npcs", [])
        for item in npc_data:
            item.setdefault("entity_id", new_id("npc"))
            item.setdefault("location_id", "")
        hook_data = data["adventure_hook"]
        hook_data.setdefault("entity_id", new_id("hook"))
        hook_data.setdefault("key_npc_id", "")
        world = cls(
            name=data["name"],
            settlement=Settlement(**settlement_data),
            npcs=[NPC(**item) for item in npc_data],
            dungeon=Dungeon(**dungeon_data),
            wilderness=WildernessArea(**wilderness_data),
            adventure_hook=AdventureHook(**hook_data),
            local_threat=data["local_threat"],
            player_state=PlayerState(**player_data),
            created_at=data["created_at"],
            world_id=data.get("world_id"),
        )
        world.repair_relationship_ids()
        return world

    def repair_relationship_ids(self) -> None:
        """Backfill ID references for Version 0.1/early 0.2 saves that used names only."""
        from app.ids import new_id

        for location in self.settlement.important_locations:
            if not location.entity_id:
                location.entity_id = new_id("loc")
        for npc in self.npcs:
            if not npc.entity_id:
                npc.entity_id = new_id("npc")
        for room in self.dungeon.rooms:
            if not room.entity_id:
                room.entity_id = new_id("room")
        for encounter in self.wilderness.encounter_table:
            if not encounter.entity_id:
                encounter.entity_id = new_id("enc")
        if not self.adventure_hook.entity_id:
            self.adventure_hook.entity_id = new_id("hook")

        locations_by_name = {
            location.name: location for location in self.settlement.important_locations
        }
        npcs_by_name = {npc.name: npc for npc in self.npcs}
        for npc in self.npcs:
            location = locations_by_name.get(npc.location)
            if location and not npc.location_id:
                npc.location_id = location.entity_id
        for location in self.settlement.important_locations:
            residents = [npc for npc in self.npcs if npc.location == location.name]
            if not location.associated_npcs:
                location.associated_npcs = [npc.name for npc in residents]
            owner = npcs_by_name.get(location.owner_or_keeper)
            if owner and not location.owner_npc_id:
                location.owner_npc_id = owner.entity_id
            if not location.associated_npc_ids:
                location.associated_npc_ids = [
                    npcs_by_name[name].entity_id
                    for name in location.associated_npcs
                    if name in npcs_by_name
                ]
        if not self.dungeon.town_location_id and self.settlement.important_locations:
            self.dungeon.town_location_id = self.settlement.important_locations[0].entity_id
        key_npc = npcs_by_name.get(self.adventure_hook.key_npc)
        if key_npc and not self.adventure_hook.key_npc_id:
            self.adventure_hook.key_npc_id = key_npc.entity_id
        if not self.settlement.problem_target_id:
            self.settlement.problem_target_type = "adventure_hook"
            self.settlement.problem_target_id = self.adventure_hook.entity_id
        first_room_id = self.dungeon.rooms[0].entity_id if self.dungeon.rooms else ""
        for encounter in self.wilderness.encounter_table:
            if encounter.foreshadows_id:
                continue
            if self.dungeon.name in encounter.signs_or_foreshadowing and first_room_id:
                encounter.foreshadows_type = "dungeon_room"
                encounter.foreshadows_id = first_room_id
            else:
                encounter.foreshadows_type = "local_threat"
                encounter.foreshadows_id = f"threat:{self.settlement.name}"
