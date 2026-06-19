from __future__ import annotations

from dataclasses import dataclass

from app.models import PlayerCharacter, World
from app.table_loader import TableLoader
from app.table_schemas import BONUS_NAMES


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


class CharacterFactory:
    """Loads replaceable class data and applies it to the existing player state."""

    def __init__(self, tables: TableLoader):
        self.tables = tables

    def classes(self) -> list[CharacterClassDefinition]:
        definitions = []
        for item in self.tables.get("class_tables", "classes"):
            if not isinstance(item, dict):
                continue
            bonuses = {
                name: int(item.get("bonuses", {}).get(name, 0)) for name in BONUS_NAMES
            }
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

        character = PlayerCharacter(
            name=clean_name,
            character_class=definition.class_name,
            background=background,
            starting_supplies=definition.starting_supplies,
            bonuses=dict(definition.bonuses),
            role_description=definition.role_description,
            special_ability_placeholder=definition.special_ability_placeholder,
        )
        player = world.player_state
        player.character = character
        player.supplies = definition.starting_supplies
        player.food = definition.starting_food
        player.water = definition.starting_water
        player.torches = definition.starting_torches
        player.coin = definition.starting_coin
        entry = (
            f"Day {player.day}, {player.time_period} — {character.name}, a "
            f"{character.character_class} with the {character.background} background, "
            "takes up the region's unfinished business."
        )
        player.action_log.append(entry)
        player.event_log.append(entry)
        return character
