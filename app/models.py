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
    supplies: int = 10
    torches: int = 6
    light_turns_remaining: int = 0
    food: int = 7
    water: int = 7
    rest_risk: str = "Unknown"
    inventory: list[str] = field(default_factory=lambda: ["bedroll", "flint and steel"])
    quest_log: list[str] = field(default_factory=list)
    hexes: list[Hex] = field(default_factory=list)


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
        settlement_data = data["settlement"]
        # Version 0.1 saves did not include explicit relationship fields.
        settlement_data.setdefault("problem_connection", settlement_data.get("local_problem", ""))
        for item in settlement_data.get("important_locations", []):
            item.setdefault("associated_npcs", [])
        settlement_data["important_locations"] = [
            Location(**item) for item in settlement_data.get("important_locations", [])
        ]
        dungeon_data = data["dungeon"]
        dungeon_data["rooms"] = [DungeonRoom(**item) for item in dungeon_data.get("rooms", [])]
        wilderness_data = data["wilderness"]
        wilderness_data["encounter_table"] = [
            Encounter(**item) for item in wilderness_data.get("encounter_table", [])
        ]
        player_data = data["player_state"]
        player_data["hexes"] = [Hex(**item) for item in player_data.get("hexes", [])]
        return cls(
            name=data["name"],
            settlement=Settlement(**settlement_data),
            npcs=[NPC(**item) for item in data.get("npcs", [])],
            dungeon=Dungeon(**dungeon_data),
            wilderness=WildernessArea(**wilderness_data),
            adventure_hook=AdventureHook(**data["adventure_hook"]),
            local_threat=data["local_threat"],
            player_state=PlayerState(**player_data),
            created_at=data["created_at"],
            world_id=data.get("world_id"),
        )
