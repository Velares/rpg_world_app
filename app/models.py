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
class PlayerCharacter:
    """Rules-light identity layer; bonuses are intentionally system-neutral."""

    name: str
    character_class: str
    background: str
    starting_supplies: int
    bonuses: dict[str, int] = field(default_factory=dict)
    role_description: str = ""
    special_ability_placeholder: str = ""
    origin_detail: str = ""
    formative_event: str = ""
    personality_trait: str = ""
    ideal: str = ""
    bond: str = ""
    flaw: str = ""
    age_years: int = 26


@dataclass
class InventoryItem:
    """A descriptive item record without combat or economy mechanics."""

    item_key: str
    name: str
    category: str = "Miscellaneous"
    quantity: int = 1
    description: str = ""
    tags: list[str] = field(default_factory=list)
    equipped: bool = False
    carried: bool = True
    consumable: bool = False
    quest_related: bool = False
    tradeable: bool = True

    @classmethod
    def from_legacy(cls, name: str) -> "InventoryItem":
        clean_name = str(name).strip() or "Unnamed item"
        key = "".join(
            character.lower() if character.isalnum() else "_"
            for character in clean_name
        ).strip("_")
        return cls(
            item_key=f"legacy_{key or 'item'}",
            name=clean_name,
            category="Miscellaneous",
            tags=["legacy"],
        )


def default_inventory() -> list[InventoryItem]:
    return [
        InventoryItem(
            item_key="bedroll",
            name="Bedroll",
            category="Supply",
            description="Basic bedding for a rough camp.",
            tags=["camp", "starter"],
        ),
        InventoryItem(
            item_key="flint_steel",
            name="Flint and Steel",
            category="Tool",
            description="A basic fire-lighting kit.",
            tags=["fire", "starter"],
        ),
    ]


@dataclass
class CheckResult:
    action_name: str
    bonus_type: str
    roll_result: int
    bonus_used: int
    total: int
    difficulty_name: str
    difficulty_class: int
    outcome: str
    narrative_result: str
    consequence: str = ""


@dataclass
class ActiveDowntimeTask:
    task_key: str
    name: str
    category: str
    description: str = ""
    required_days: int = 1
    progress_days: int = 0
    allowed_contexts: list[str] = field(default_factory=list)
    progress_text: str = ""
    completion_text: str = ""
    complication_text: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class PlayerState:
    character: PlayerCharacter | None = None
    current_location: str = "town"
    current_location_id: str = ""
    current_room_id: int | None = None
    day: int = 1
    time_period: str = "Morning"
    supplies: int = 10
    torches: int = 6
    light_turns_remaining: int = 0
    food: int = 7
    water: int = 7
    coin: int = 20
    wounds: int = 0
    rest_risk: str = "Unknown"
    inventory: list[InventoryItem] = field(default_factory=default_inventory)
    quest_log: list[str] = field(default_factory=list)
    hexes: list[Hex] = field(default_factory=list)
    discovered_room_ids: list[int] = field(default_factory=list)
    pending_encounter_id: str = ""
    action_log: list[str] = field(default_factory=list)
    event_log: list[str] = field(default_factory=list)
    known_npc_ids: list[str] = field(default_factory=list)
    known_location_ids: list[str] = field(default_factory=list)
    known_rumor_indices: list[int] = field(default_factory=list)
    known_threats: list[str] = field(default_factory=list)
    leads: list[str] = field(default_factory=list)
    position: int = 0
    attention: int = 0
    last_consequence: str = ""
    last_check: CheckResult | None = None
    turns_elapsed: int = 0
    age_days_accumulated: int = 0
    active_downtime_task: ActiveDowntimeTask | None = None

    def inventory_item(self, item_key_or_name: str) -> InventoryItem | None:
        needle = item_key_or_name.casefold()
        return next(
            (
                item
                for item in self.inventory
                if item.item_key.casefold() == needle or item.name.casefold() == needle
            ),
            None,
        )

    def add_inventory_item(
        self,
        item: InventoryItem | str,
        quantity: int | None = None,
        **metadata,
    ) -> InventoryItem:
        if isinstance(item, str):
            new_item = InventoryItem.from_legacy(item)
            for key, value in metadata.items():
                if hasattr(new_item, key):
                    setattr(new_item, key, value)
        else:
            new_item = InventoryItem(**asdict(item))
        amount = new_item.quantity if quantity is None else quantity
        if not isinstance(amount, int) or isinstance(amount, bool):
            raise ValueError("Inventory quantity must be a whole number.")
        if amount <= 0:
            raise ValueError("Inventory quantity must be positive.")
        existing = self.inventory_item(new_item.item_key)
        if existing:
            existing.quantity += amount
            return existing
        new_item.quantity = amount
        self.inventory.append(new_item)
        return new_item

    def ensure_inventory_item(self, item: InventoryItem) -> InventoryItem:
        existing = self.inventory_item(item.item_key)
        if existing:
            existing.quantity = max(existing.quantity, item.quantity)
            return existing
        self.inventory.append(InventoryItem(**asdict(item)))
        return self.inventory[-1]

    def remove_inventory_item(self, item_key_or_name: str, quantity: int = 1) -> int:
        if not isinstance(quantity, int) or isinstance(quantity, bool):
            raise ValueError("Removal quantity must be a whole number.")
        if quantity <= 0:
            raise ValueError("Removal quantity must be positive.")
        item = self.inventory_item(item_key_or_name)
        if item is None:
            return 0
        removed = min(quantity, item.quantity)
        item.quantity -= removed
        if item.quantity == 0:
            self.inventory.remove(item)
        return removed


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
        character_data = player_data.get("character")
        if isinstance(character_data, dict):
            # Character profiles were added after the original class scaffold.
            for field_name in (
                "origin_detail",
                "formative_event",
                "personality_trait",
                "ideal",
                "bond",
                "flaw",
            ):
                character_data.setdefault(field_name, "")
            character_data.setdefault("age_years", 26)
            player_data["character"] = PlayerCharacter(**character_data)
        else:
            player_data["character"] = None
        check_data = player_data.get("last_check")
        if isinstance(check_data, dict):
            player_data["last_check"] = CheckResult(**check_data)
        else:
            player_data["last_check"] = None
        downtime_data = player_data.get("active_downtime_task")
        if isinstance(downtime_data, dict):
            downtime_data.setdefault("description", "")
            downtime_data.setdefault("required_days", 1)
            downtime_data.setdefault("progress_days", 0)
            downtime_data.setdefault("allowed_contexts", [])
            downtime_data.setdefault("progress_text", "")
            downtime_data.setdefault("completion_text", "")
            downtime_data.setdefault("complication_text", "")
            downtime_data.setdefault("tags", [])
            player_data["active_downtime_task"] = ActiveDowntimeTask(**downtime_data)
        else:
            player_data["active_downtime_task"] = None
        # Version 0.3 exploration fields are defaulted so older saves remain playable.
        player_data.setdefault("current_location", "town")
        player_data.setdefault("current_location_id", "")
        player_data.setdefault("current_room_id", None)
        player_data.setdefault("day", 1)
        player_data.setdefault("time_period", "Morning")
        player_data.setdefault("coin", 20)
        player_data.setdefault("wounds", 0)
        player_data.setdefault("discovered_room_ids", [])
        player_data.setdefault("pending_encounter_id", "")
        player_data.setdefault("action_log", [])
        player_data.setdefault("event_log", list(player_data.get("action_log", [])))
        player_data.setdefault("known_npc_ids", [])
        player_data.setdefault("known_location_ids", [])
        player_data.setdefault("known_rumor_indices", [])
        player_data.setdefault("known_threats", [])
        player_data.setdefault("leads", [])
        player_data.setdefault("position", 0)
        player_data.setdefault("attention", 0)
        player_data.setdefault("last_consequence", "")
        player_data.setdefault("turns_elapsed", 0)
        player_data.setdefault("age_days_accumulated", 0)
        if not isinstance(player_data["day"], int) or isinstance(player_data["day"], bool):
            player_data["day"] = 1
        else:
            player_data["day"] = max(1, player_data["day"])
        if player_data["time_period"] not in ("Morning", "Afternoon", "Evening", "Night"):
            player_data["time_period"] = "Morning"
        if not isinstance(player_data["age_days_accumulated"], int) or isinstance(
            player_data["age_days_accumulated"], bool
        ):
            player_data["age_days_accumulated"] = 0
        else:
            player_data["age_days_accumulated"] = max(0, player_data["age_days_accumulated"])
        inventory_data = player_data.get("inventory")
        if inventory_data is None:
            player_data["inventory"] = default_inventory()
        else:
            inventory: list[InventoryItem] = []
            for item in inventory_data:
                if isinstance(item, str):
                    inventory.append(InventoryItem.from_legacy(item))
                elif isinstance(item, dict):
                    legacy_key = InventoryItem.from_legacy(
                        item.get("name", "")
                    ).item_key
                    item.setdefault("item_key", legacy_key)
                    item.setdefault("name", "Unnamed item")
                    item.setdefault("category", "Miscellaneous")
                    item.setdefault("quantity", 1)
                    item.setdefault("description", "")
                    item.setdefault("tags", [])
                    item.setdefault("equipped", False)
                    item.setdefault("carried", True)
                    item.setdefault("consumable", False)
                    item.setdefault("quest_related", False)
                    item.setdefault("tradeable", True)
                    inventory.append(InventoryItem(**item))
            player_data["inventory"] = inventory
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
