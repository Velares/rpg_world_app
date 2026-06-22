from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4

from app.equipment import (
    COIN_PER_POUND,
    HAND_SLOTS,
    default_equipment_slots,
    encumbrance_effects,
    encumbrance_state,
)

ABILITY_SCORE_NAMES = (
    "strength",
    "dexterity",
    "constitution",
    "intelligence",
    "wisdom",
    "charisma",
)


def default_ability_scores() -> dict[str, int]:
    return {name: 10 for name in ABILITY_SCORE_NAMES}


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
    interaction_count: int = 0
    first_interacted_date: str = ""
    last_interacted_date: str = ""
    prominence_score: int = 0
    prominent: bool = False
    deeper_backstory: str = ""
    personal_motive: str = ""
    hidden_pressure: str = ""
    relationship_to_player: str = ""
    ongoing_thread: str = ""
    prominence_notes: str = ""
    recent_interaction_notes: list[str] = field(default_factory=list)
    is_key_npc: bool = False
    key_npc_since: str = ""
    key_npc_reason: str = ""
    key_npc_notes: str = ""
    faction_tag: str = "unknown"


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
    class_role: str = "adventurer"
    class_type: str = "generalist"
    class_subtype: str = ""
    ability_scores: dict[str, int] = field(default_factory=default_ability_scores)
    fixed_scores: dict[str, int] = field(default_factory=dict)
    derived_scores: dict[str, int] = field(default_factory=dict)


@dataclass
class InventoryItem:
    """A descriptive item record without combat or economy mechanics."""

    item_key: str
    name: str
    instance_id: str = field(default_factory=lambda: f"item_{uuid4().hex[:12]}")
    category: str = "Miscellaneous"
    quantity: int = 1
    description: str = ""
    tags: list[str] = field(default_factory=list)
    equipped: bool = False
    carried: bool = True
    consumable: bool = False
    quest_related: bool = False
    tradeable: bool = True
    bulk: float = 0.0
    valid_slots: list[str] = field(default_factory=list)
    handedness: str = ""
    speed_factor: int = 0
    range_profile: str = ""
    mode: str = ""
    placeholder_damage: str = ""
    placeholder_special_rules: str = ""
    placeholder_value: str = ""
    placeholder_condition: str = ""
    container_capacity_bulk: float = 0.0

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

    @property
    def is_equippable(self) -> bool:
        return bool(self.valid_slots)

    @property
    def total_bulk(self) -> float:
        return round(float(self.bulk) * max(1, int(self.quantity)), 2)


def default_inventory() -> list[InventoryItem]:
    return [
        InventoryItem(
            item_key="bedroll",
            name="Bedroll",
            category="Supply",
            description="Basic bedding for a rough camp.",
            tags=["camp", "starter"],
            bulk=1.0,
            valid_slots=["Back"],
        ),
        InventoryItem(
            item_key="flint_steel",
            name="Flint and Steel",
            category="Tool",
            description="A basic fire-lighting kit.",
            tags=["fire", "starter"],
            bulk=0.1,
        ),
    ]


def default_item_metadata(item_key: str, category: str) -> dict[str, Any]:
    key = str(item_key).strip()
    category_name = str(category).strip()
    defaults = {
        "bulk": 0.0,
        "valid_slots": [],
        "handedness": "",
        "speed_factor": 0,
        "range_profile": "",
        "mode": "",
        "placeholder_damage": "",
        "placeholder_special_rules": "",
        "placeholder_value": "",
        "placeholder_condition": "",
        "container_capacity_bulk": 0.0,
    }
    if key == "blade" or category_name == "Weapon":
        defaults.update(
            {
                "bulk": 1.0,
                "valid_slots": ["Main Hand", "Backpack / Container"],
                "handedness": "1H",
                "speed_factor": 4,
                "range_profile": "close",
                "mode": "melee",
                "placeholder_damage": "1d6 placeholder",
            }
        )
    elif category_name == "Armor":
        defaults.update(
            {
                "bulk": 2.0 if key == "light_armor" else 0.5,
                "valid_slots": ["Chest"] if key == "light_armor" else ["Back"],
            }
        )
    elif category_name == "Container":
        defaults.update(
            {
                "bulk": 1.0,
                "valid_slots": ["Backpack / Container", "Back"],
                "container_capacity_bulk": 10.0,
            }
        )
    elif category_name in {"Tool", "Miscellaneous"}:
        defaults.update({"bulk": 0.5, "valid_slots": ["Backpack / Container", "Belt"]})
    elif category_name == "Supply":
        defaults.update({"bulk": 1.0, "valid_slots": ["Back", "Backpack / Container"]})
    return defaults


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
    progress_outcomes: list[dict[str, Any]] = field(default_factory=list)
    completion_outcomes: list[dict[str, Any]] = field(default_factory=list)
    complication_outcomes: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class LeadRecord:
    text: str
    source: str = ""
    location: str = ""
    related_npc: str = ""
    status: str = "active"
    suggested_action: str = ""
    category: str = "other"
    last_updated_day: int = 0


@dataclass
class TimelineEntry:
    day: int
    time_period: str
    action_type: str
    result_text: str
    location_context: str = ""
    npc_id: str = ""
    npc_name: str = ""
    location_id: str = ""
    location_name: str = ""
    quest_ref: str = ""
    lead_ref: str = ""
    downtime_ref: str = ""
    resource_impact: str = ""


@dataclass
class NpcRelationship:
    npc_a_id: str
    npc_b_id: str
    relationship_state: str = "neutral"
    affinity_score: int = 0
    first_established_date: str = ""
    last_checked_date: str = ""
    reason_text: str = ""
    recent_event_notes: list[str] = field(default_factory=list)


@dataclass
class DiaryEntry:
    entry_id: str
    title: str
    text: str
    created_day: int
    created_time_period: str
    player_notes: str = ""
    importance: str = "ordinary"
    source_action: str = ""
    protected: bool = False
    hidden: bool = False
    auto_generated: bool = False


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
    lead_records: list[LeadRecord] = field(default_factory=list)
    position: int = 0
    attention: int = 0
    last_consequence: str = ""
    last_check: CheckResult | None = None
    turns_elapsed: int = 0
    age_days_accumulated: int = 0
    active_downtime_task: ActiveDowntimeTask | None = None
    timeline_entries: list[TimelineEntry] = field(default_factory=list)
    diary_entries: list[DiaryEntry] = field(default_factory=list)
    equipment_slots: dict[str, str] = field(default_factory=default_equipment_slots)
    use_coin_weight: bool = False

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

    def inventory_instance(self, instance_id: str) -> InventoryItem | None:
        return next(
            (item for item in self.inventory if item.instance_id == instance_id),
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
        metadata_defaults = default_item_metadata(new_item.item_key, new_item.category)
        if new_item.bulk == 0 and metadata_defaults["bulk"] > 0:
            new_item.bulk = metadata_defaults["bulk"]
        if (
            new_item.container_capacity_bulk == 0
            and metadata_defaults["container_capacity_bulk"] > 0
        ):
            new_item.container_capacity_bulk = metadata_defaults["container_capacity_bulk"]
        amount = new_item.quantity if quantity is None else quantity
        if not isinstance(amount, int) or isinstance(amount, bool):
            raise ValueError("Inventory quantity must be a whole number.")
        if amount <= 0:
            raise ValueError("Inventory quantity must be positive.")
        if new_item.is_equippable:
            created_item: InventoryItem | None = None
            for _ in range(amount):
                clone = InventoryItem(**asdict(new_item))
                clone.instance_id = f"item_{uuid4().hex[:12]}"
                clone.quantity = 1
                self.inventory.append(clone)
                created_item = clone
            return created_item if created_item is not None else new_item
        existing = self.inventory_item(new_item.item_key)
        if existing:
            existing.quantity += amount
            return existing
        new_item.quantity = amount
        self.inventory.append(new_item)
        return new_item

    def ensure_inventory_item(self, item: InventoryItem) -> InventoryItem:
        existing = None if item.is_equippable else self.inventory_item(item.item_key)
        if existing is not None:
            existing.quantity = max(existing.quantity, item.quantity)
            return existing
        clone = InventoryItem(**asdict(item))
        if item.is_equippable:
            clone.instance_id = f"item_{uuid4().hex[:12]}"
            clone.quantity = 1
        self.inventory.append(clone)
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
            self.unequip_item(item.instance_id)
            self.inventory.remove(item)
        return removed

    def equipped_items(self) -> list[InventoryItem]:
        seen_ids = {instance_id for instance_id in self.equipment_slots.values() if instance_id}
        return [
            item for item in self.inventory
            if item.instance_id in seen_ids or item.equipped
        ]

    def carried_items(self) -> list[InventoryItem]:
        return [item for item in self.inventory if item.carried]

    def equipped_bulk(self) -> float:
        return round(sum(item.total_bulk for item in self.equipped_items()), 2)

    def total_carried_bulk(self) -> float:
        total = sum(item.total_bulk for item in self.carried_items())
        if self.use_coin_weight and self.coin > 0:
            total += self.coin / COIN_PER_POUND
        return round(total, 2)

    def strength_score(self) -> int:
        if self.character is None:
            return 10
        return max(1, int(self.character.ability_scores.get("strength", 10)))

    def encumbrance_state(self) -> str:
        return encumbrance_state(self.total_carried_bulk(), self.strength_score())

    def encumbrance_effects(self) -> dict[str, str]:
        return encumbrance_effects(self.encumbrance_state())

    def slot_item(self, slot_name: str) -> InventoryItem | None:
        instance_id = self.equipment_slots.get(slot_name, "")
        return self.inventory_instance(instance_id) if instance_id else None

    def equip_item(self, item_ref: str, slot_name: str) -> InventoryItem:
        item = self.inventory_instance(item_ref) or self.inventory_item(item_ref)
        if item is None:
            raise KeyError(f"No inventory item matches {item_ref}")
        if slot_name not in self.equipment_slots:
            raise ValueError(f"Unknown equipment slot: {slot_name}")
        if slot_name not in item.valid_slots:
            raise ValueError(f"{item.name} cannot be equipped in {slot_name}.")
        if item.handedness == "2H" and slot_name != "Main Hand":
            raise ValueError(f"{item.name} must be equipped in Main Hand.")
        if slot_name == "Off Hand":
            main_hand = self.slot_item("Main Hand")
            if main_hand and main_hand.handedness == "2H":
                raise RuntimeError("Off Hand is blocked by a two-handed weapon.")
        if item.handedness == "2H" and self.slot_item("Off Hand") is not None:
            raise RuntimeError("Unequip the current Off Hand item before using a two-handed weapon.")
        if slot_name == "Main Hand":
            current_main = self.slot_item("Main Hand")
            if current_main and current_main.handedness == "2H":
                self.unequip_item(current_main.instance_id)
        current_slot_item = self.slot_item(slot_name)
        if current_slot_item is not None and current_slot_item.instance_id != item.instance_id:
            self.unequip_item(current_slot_item.instance_id)
        self.unequip_item(item.instance_id)
        self.equipment_slots[slot_name] = item.instance_id
        item.equipped = True
        if item.handedness == "2H":
            self.equipment_slots["Off Hand"] = item.instance_id
        return item

    def unequip_slot(self, slot_name: str) -> None:
        if slot_name not in self.equipment_slots:
            raise ValueError(f"Unknown equipment slot: {slot_name}")
        instance_id = self.equipment_slots.get(slot_name, "")
        if instance_id:
            self.unequip_item(instance_id)

    def unequip_item(self, item_ref: str) -> None:
        item = self.inventory_instance(item_ref) or self.inventory_item(item_ref)
        if item is None:
            return
        for slot_name, instance_id in list(self.equipment_slots.items()):
            if instance_id == item.instance_id:
                self.equipment_slots[slot_name] = ""
        item.equipped = False

    def auto_equip_defaults(self) -> None:
        for item in self.inventory:
            if not item.equipped or not item.valid_slots:
                continue
            item.equipped = False
            preferred_slots = list(item.valid_slots)
            if item.handedness == "2H":
                preferred_slots = ["Main Hand", *preferred_slots]
            elif "Main Hand" in preferred_slots:
                preferred_slots = ["Main Hand", *[slot for slot in preferred_slots if slot != "Main Hand"]]
            for slot_name in preferred_slots:
                try:
                    self.equip_item(item.instance_id, slot_name)
                    break
                except (RuntimeError, ValueError):
                    continue


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
    npc_relationships: list[NpcRelationship] = field(default_factory=list)
    faction_status_notes: dict[str, str] = field(default_factory=dict)
    last_key_npc_phase_day: int = 0
    generation_seed: str | None = None
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
            character_data.setdefault("class_role", "adventurer")
            character_data.setdefault("class_type", "generalist")
            character_data.setdefault("class_subtype", "")
            ability_scores = character_data.get("ability_scores")
            if not isinstance(ability_scores, dict):
                ability_scores = {}
            character_data["ability_scores"] = {
                name: (
                    value
                    if isinstance(value := ability_scores.get(name), int)
                    and not isinstance(value, bool)
                    else 10
                )
                for name in ABILITY_SCORE_NAMES
            }
            for scores_key in ("fixed_scores", "derived_scores"):
                raw_scores = character_data.get(scores_key)
                if isinstance(raw_scores, dict):
                    character_data[scores_key] = {
                        str(key): value
                        for key, value in raw_scores.items()
                        if isinstance(value, int) and not isinstance(value, bool)
                    }
                else:
                    character_data[scores_key] = {}
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
            downtime_data.setdefault("progress_outcomes", [])
            downtime_data.setdefault("completion_outcomes", [])
            downtime_data.setdefault("complication_outcomes", [])
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
        player_data.setdefault("lead_records", [])
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
        timeline_data = player_data.get("timeline_entries", [])
        if isinstance(timeline_data, list):
            player_data["timeline_entries"] = [
                TimelineEntry(**item) for item in timeline_data if isinstance(item, dict)
            ]
        else:
            player_data["timeline_entries"] = []
        diary_data = player_data.get("diary_entries", [])
        if isinstance(diary_data, list):
            clean_diary_entries: list[DiaryEntry] = []
            for index, item in enumerate(diary_data):
                if not isinstance(item, dict):
                    continue
                item.setdefault("entry_id", f"legacy_diary_{index}")
                item.setdefault("title", "Diary Entry")
                item.setdefault("text", "")
                item.setdefault("created_day", player_data["day"])
                item.setdefault("created_time_period", player_data["time_period"])
                item.setdefault("player_notes", "")
                item.setdefault("importance", "ordinary")
                item.setdefault("source_action", "")
                item.setdefault("protected", False)
                item.setdefault("hidden", False)
                item.setdefault("auto_generated", False)
                if not isinstance(item["created_day"], int) or isinstance(
                    item["created_day"], bool
                ):
                    item["created_day"] = 1
                else:
                    item["created_day"] = max(1, item["created_day"])
                if item["created_time_period"] not in (
                    "Morning",
                    "Afternoon",
                    "Evening",
                    "Night",
                ):
                    item["created_time_period"] = "Morning"
                clean_diary_entries.append(DiaryEntry(**item))
            player_data["diary_entries"] = clean_diary_entries
        else:
            player_data["diary_entries"] = []
        lead_record_data = player_data.get("lead_records", [])
        lead_records: list[LeadRecord] = []
        if isinstance(lead_record_data, list):
            for item in lead_record_data:
                if isinstance(item, str):
                    lead_records.append(
                        LeadRecord(
                            text=item,
                            suggested_action=item,
                        )
                    )
                elif isinstance(item, dict):
                    item.setdefault("text", "")
                    item.setdefault("source", "")
                    item.setdefault("location", "")
                    item.setdefault("related_npc", "")
                    item.setdefault("status", "active")
                    item.setdefault("suggested_action", item.get("text", ""))
                    item.setdefault("category", "other")
                    item.setdefault("last_updated_day", 0)
                    if not isinstance(item["last_updated_day"], int) or isinstance(
                        item["last_updated_day"], bool
                    ):
                        item["last_updated_day"] = 0
                    else:
                        item["last_updated_day"] = max(0, item["last_updated_day"])
                    if item["text"]:
                        lead_records.append(LeadRecord(**item))
        legacy_leads = player_data.get("leads", [])
        if not lead_records and isinstance(legacy_leads, list):
            for lead in legacy_leads:
                if isinstance(lead, str) and lead.strip():
                    lead_records.append(
                        LeadRecord(
                            text=lead.strip(),
                            suggested_action=lead.strip(),
                        )
                    )
        player_data["lead_records"] = lead_records
        player_data["leads"] = [
            lead.text
            for lead in lead_records
            if lead.status not in {"resolved", "false"} and lead.text
        ]
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
                    metadata_defaults = default_item_metadata(
                        item["item_key"],
                        item["category"],
                    )
                    item.setdefault("quantity", 1)
                    item.setdefault("description", "")
                    item.setdefault("tags", [])
                    item.setdefault("equipped", False)
                    item.setdefault("carried", True)
                    item.setdefault("consumable", False)
                    item.setdefault("quest_related", False)
                    item.setdefault("tradeable", True)
                    item.setdefault("instance_id", f"item_{uuid4().hex[:12]}")
                    for metadata_key, metadata_value in metadata_defaults.items():
                        item.setdefault(metadata_key, metadata_value)
                    inventory.append(InventoryItem(**item))
            player_data["inventory"] = inventory
        equipment_slots = player_data.get("equipment_slots")
        if not isinstance(equipment_slots, dict):
            equipment_slots = default_equipment_slots()
        else:
            normalized_slots = default_equipment_slots()
            for slot_name in normalized_slots:
                value = equipment_slots.get(slot_name, "")
                normalized_slots[slot_name] = value if isinstance(value, str) else ""
            equipment_slots = normalized_slots
        player_data["equipment_slots"] = equipment_slots
        player_data["use_coin_weight"] = bool(player_data.get("use_coin_weight", False))
        player_data["hexes"] = [Hex(**item) for item in player_data.get("hexes", [])]
        npc_data = data.get("npcs", [])
        for item in npc_data:
            item.setdefault("entity_id", new_id("npc"))
            item.setdefault("location_id", "")
            item.setdefault("interaction_count", 0)
            item.setdefault("first_interacted_date", "")
            item.setdefault("last_interacted_date", "")
            item.setdefault("prominence_score", 0)
            item.setdefault("prominent", False)
            item.setdefault("deeper_backstory", "")
            item.setdefault("personal_motive", "")
            item.setdefault("hidden_pressure", "")
            item.setdefault("relationship_to_player", "")
            item.setdefault("ongoing_thread", "")
            item.setdefault("prominence_notes", "")
            item.setdefault("is_key_npc", False)
            item.setdefault("key_npc_since", "")
            item.setdefault("key_npc_reason", "")
            item.setdefault("key_npc_notes", "")
            item.setdefault("faction_tag", "unknown")
            notes = item.get("recent_interaction_notes", [])
            item["recent_interaction_notes"] = [
                str(note) for note in notes if isinstance(note, str) and note
            ]
        hook_data = data["adventure_hook"]
        hook_data.setdefault("entity_id", new_id("hook"))
        hook_data.setdefault("key_npc_id", "")
        relationship_data = data.get("npc_relationships", [])
        relationships: list[NpcRelationship] = []
        if isinstance(relationship_data, list):
            for item in relationship_data:
                if not isinstance(item, dict):
                    continue
                item.setdefault("npc_a_id", "")
                item.setdefault("npc_b_id", "")
                item.setdefault("relationship_state", "neutral")
                item.setdefault("affinity_score", 0)
                item.setdefault("first_established_date", "")
                item.setdefault("last_checked_date", "")
                item.setdefault("reason_text", "")
                notes = item.get("recent_event_notes", [])
                item["recent_event_notes"] = [
                    str(note) for note in notes if isinstance(note, str) and note
                ]
                relationships.append(NpcRelationship(**item))
        faction_status_notes = data.get("faction_status_notes", {})
        if not isinstance(faction_status_notes, dict):
            faction_status_notes = {}
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
            npc_relationships=relationships,
            faction_status_notes={
                str(key): str(value)
                for key, value in faction_status_notes.items()
                if key and value
            },
            last_key_npc_phase_day=(
                data.get("last_key_npc_phase_day", 0)
                if isinstance(data.get("last_key_npc_phase_day", 0), int)
                and not isinstance(data.get("last_key_npc_phase_day", 0), bool)
                else 0
            ),
            generation_seed=data.get("generation_seed"),
            world_id=data.get("world_id"),
        )
        if not any(world.player_state.equipment_slots.values()) and any(
            item.equipped and item.valid_slots for item in world.player_state.inventory
        ):
            world.player_state.auto_equip_defaults()
        world.repair_relationship_ids()
        world.normalize_relationship_records()
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

    def normalize_relationship_records(self) -> None:
        valid_states = {"ally", "at_odds", "neutral", "unknown"}
        deduped: dict[tuple[str, str], NpcRelationship] = {}
        for relationship in self.npc_relationships:
            if not relationship.npc_a_id or not relationship.npc_b_id:
                continue
            pair = tuple(sorted((relationship.npc_a_id, relationship.npc_b_id)))
            relationship.npc_a_id, relationship.npc_b_id = pair
            if relationship.relationship_state not in valid_states:
                relationship.relationship_state = "neutral"
            if not isinstance(relationship.affinity_score, int) or isinstance(
                relationship.affinity_score, bool
            ):
                relationship.affinity_score = 0
            relationship.recent_event_notes = [
                str(note)
                for note in relationship.recent_event_notes
                if isinstance(note, str) and note
            ]
            deduped[pair] = relationship
        self.npc_relationships = list(deduped.values())
