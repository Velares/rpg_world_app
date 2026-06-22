from __future__ import annotations

import random
from dataclasses import dataclass

from app.calendar import append_timeline_entry
from app.character_profiles import CharacterProfileGenerator
from app.inventory import InventoryCatalog
from app.models import (
    ABILITY_SCORE_NAMES,
    PlayerCharacter,
    World,
)
from app.table_loader import TableLoader
from app.table_schemas import BONUS_NAMES

DEFAULT_CLASS_METADATA = {
    "fighter": ("melee", "fighter", ""),
    "thief": ("specialist", "thief", ""),
    "ranger": ("hybrid", "ranger", "warden"),
    "scholar": ("specialist", "scholar", "loremaster"),
    "acolyte": ("hybrid", "cleric", "ritualist"),
    "occultist": ("spellcaster", "magic_user", "occult"),
    "mercenary": ("melee", "fighter", "sellsword"),
    "explorer": ("specialist", "scout", "delver"),
    "bard": ("hybrid", "specialist", "performer"),
    "mystic": ("spellcaster", "healer", "visionary"),
}


@dataclass(frozen=True)
class CharacterClassDefinition:
    class_name: str
    role_description: str
    starting_supplies: int
    starting_food: int
    starting_water: int
    starting_torches: int
    starting_coin: int
    bonuses: dict[str, int]
    special_ability_placeholder: str
    class_role: str
    class_type: str
    class_subtype: str


class CharacterFactory:
    """Loads replaceable class data and applies it to the existing player state."""

    def __init__(self, tables: TableLoader, rng: random.Random | None = None):
        self.tables = tables
        self.rng = rng or random.Random()

    def classes(self) -> list[CharacterClassDefinition]:
        definitions = []
        for item in self.tables.get("class_tables", "classes"):
            if not isinstance(item, dict):
                continue
            bonuses = {
                name: int(item.get("bonuses", {}).get(name, 0)) for name in BONUS_NAMES
            }
            default_role, default_type, default_subtype = DEFAULT_CLASS_METADATA.get(
                str(item.get("class_name", "Adventurer")).strip().casefold(),
                ("adventurer", "generalist", ""),
            )
            definitions.append(
                CharacterClassDefinition(
                    class_name=str(item.get("class_name", "Adventurer")),
                    role_description=str(item.get("role_description", "")),
                    starting_supplies=int(item.get("starting_supplies", 10)),
                    starting_food=int(item.get("starting_food", 7)),
                    starting_water=int(item.get("starting_water", 7)),
                    starting_torches=int(item.get("starting_torches", 6)),
                    starting_coin=int(item.get("starting_coin", 20)),
                    bonuses=bonuses,
                    special_ability_placeholder=str(
                        item.get("special_ability_placeholder", "Reserved for future rules.")
                    ),
                    class_role=str(item.get("class_role", default_role)).strip()
                    or default_role,
                    class_type=str(item.get("class_type", default_type)).strip()
                    or default_type,
                    class_subtype=str(item.get("class_subtype", default_subtype)).strip(),
                )
            )
        if not definitions:
            raise RuntimeError("No valid character classes are available.")
        return definitions

    def backgrounds(self) -> list[str]:
        return [str(value) for value in self.tables.get("class_tables", "backgrounds")]

    def create(
        self,
        world: World,
        name: str,
        class_name: str,
        background: str,
    ) -> PlayerCharacter:
        definition = next(
            (item for item in self.classes() if item.class_name == class_name),
            None,
        )
        if definition is None:
            raise ValueError(f"Unknown character class: {class_name}")
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Character name is required.")
        if background not in self.backgrounds():
            raise ValueError(f"Unknown background: {background}")

        profile = CharacterProfileGenerator(self.tables, self.rng).generate()
        ability_scores = self._generate_ability_scores()
        character = PlayerCharacter(
            name=clean_name,
            character_class=definition.class_name,
            background=background,
            starting_supplies=definition.starting_supplies,
            bonuses=dict(definition.bonuses),
            role_description=definition.role_description,
            special_ability_placeholder=definition.special_ability_placeholder,
            origin_detail=profile.origin_detail,
            formative_event=profile.formative_event,
            personality_trait=profile.personality_trait,
            ideal=profile.ideal,
            bond=profile.bond,
            flaw=profile.flaw,
            age_years=self.rng.randint(18, 60),
            class_role=definition.class_role,
            class_type=definition.class_type,
            class_subtype=definition.class_subtype,
            ability_scores=ability_scores,
        )
        player = world.player_state
        player.character = character
        player.supplies = definition.starting_supplies
        player.food = definition.starting_food
        player.water = definition.starting_water
        player.torches = definition.starting_torches
        player.coin = definition.starting_coin
        for item in InventoryCatalog(self.tables).starting_inventory(
            definition.class_name
        ):
            player.ensure_inventory_item(item)
        append_timeline_entry(
            player,
            f"{character.name}, a {character.character_class} with the "
            f"{character.background} background, takes up the region's unfinished business.",
            action_type="character",
            npc_name=character.name,
        )
        return character

    def _generate_ability_scores(self) -> dict[str, int]:
        return {
            ability_name: sum(self.rng.randint(1, 6) for _ in range(3))
            for ability_name in ABILITY_SCORE_NAMES
        }
