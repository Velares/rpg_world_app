from __future__ import annotations

from app.generators.common import BaseGenerator
from app.generators.encounter_generator import EncounterGenerator
from app.models import Dungeon, Settlement, WildernessArea


class WildernessGenerator(BaseGenerator):
    def generate(
        self,
        encounter_count: int = 10,
        settlement: Settlement | None = None,
        dungeon: Dungeon | None = None,
    ) -> WildernessArea:
        encounters = EncounterGenerator(self.tables, self.rng)
        generated_encounters = []
        for index in range(encounter_count):
            base_sign = self.pick("monster_tables", "monster_signs")
            if settlement and dungeon and index % 2 == 0:
                connection = (
                    f"The sign bears the same unnatural marks described at {dungeon.name}; "
                    f"scouting it may reveal a safer approach."
                )
                target_type = "dungeon_room"
                target_id = dungeon.rooms[0].entity_id
            elif settlement:
                connection = (
                    f"Locals connect this sign to {settlement.nearby_danger}; careful travelers "
                    f"can use it as an early warning."
                )
                target_type = "local_threat"
                target_id = f"threat:{settlement.name}"
            else:
                connection = ""
                target_type = ""
                target_id = ""
            generated_encounters.append(
                encounters.generate(
                    f"{base_sign} {connection}".strip(),
                    foreshadows_type=target_type,
                    foreshadows_id=target_id,
                )
            )
        return WildernessArea(
            name=self.pick("wilderness_tables", "wilderness_names"),
            terrain_type=self.pick("wilderness_tables", "terrain_types"),
            weather=self.pick("wilderness_tables", "weather"),
            dominant_feature=self.pick("wilderness_tables", "dominant_features"),
            resources=self.pick("wilderness_tables", "resources"),
            travel_hazards=self.pick("wilderness_tables", "travel_hazards"),
            encounter_table=generated_encounters,
            weird_fantasy_detail=self.pick("weird_tables", "strange_weather"),
        )
