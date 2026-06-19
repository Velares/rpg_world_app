from __future__ import annotations

from app.generators.common import BaseGenerator
from app.ids import new_id
from app.models import Location, NPC
from app.name_generator import NameGenerator


class NPCGenerator(BaseGenerator):
    def __init__(self, tables, rng, name_generator: NameGenerator | None = None):
        super().__init__(tables, rng)
        self.name_generator = name_generator

    def generate_name(self) -> str:
        if self.name_generator is not None:
            return self.name_generator.full_name()
        category = self.rng.choice(["male_names", "female_names", "neutral_names"])
        return f"{self.pick('npc_tables', category)} {self.pick('npc_tables', 'surnames')}"

    def generate(self, locations: list[Location], count: int = 10) -> list[NPC]:
        npcs = []
        used_names: dict[str, int] = {}
        for index in range(count):
            name = self.generate_name()
            used_names[name] = used_names.get(name, 0) + 1
            if used_names[name] > 1:
                name = f"{name} the {self.pick('npc_tables', 'professions').title()}"
            location = locations[index] if index < len(locations) else self.rng.choice(locations)
            npcs.append(
                NPC(
                    name=name,
                    age=self.rng.randint(16, 78),
                    ancestry=self.pick("npc_tables", "ancestries"),
                    profession=self.pick("npc_tables", "professions"),
                    # Seed one NPC into every important location before assigning
                    # additional townsfolk, guaranteeing a keeper-sized roster.
                    location=location.name,
                    appearance=self.pick("npc_tables", "appearances"),
                    personality=self.pick("npc_tables", "personalities"),
                    motivation=self.pick("npc_tables", "motivations"),
                    fear=self.pick("npc_tables", "fears"),
                    secret=self.pick("npc_tables", "secrets"),
                    relationship_to_town=self.pick("npc_tables", "relationships"),
                    attitude_toward_player=self.pick("npc_tables", "attitudes"),
                    useful_information=self.pick("npc_tables", "useful_information"),
                    possible_service=self.pick("npc_tables", "possible_services"),
                    danger_level=self.danger(),
                    entity_id=new_id("npc"),
                    location_id=location.entity_id,
                )
            )
        return npcs
