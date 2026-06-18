from __future__ import annotations

from app.generators.common import BaseGenerator
from app.models import Dungeon, DungeonRoom, Settlement


class DungeonGenerator(BaseGenerator):
    def generate(self, settlement: Settlement, room_count: int = 8) -> Dungeon:
        rooms = []
        for index in range(1, room_count + 1):
            exits = []
            if index > 1:
                exits.append(index - 1)
            if index < room_count:
                exits.append(index + 1)
            if index > 2 and self.rng.random() < 0.35:
                candidate = self.rng.randint(1, index - 2)
                if candidate not in exits:
                    exits.append(candidate)
            rooms.append(
                DungeonRoom(
                    room_id=index,
                    name=self.pick("dungeon_tables", "room_names"),
                    description=self.pick("dungeon_tables", "room_descriptions"),
                    exits=sorted(exits),
                    what_player_notices_first=self.pick("weird_tables", "eerie_sounds"),
                    contents=self.pick("dungeon_tables", "weird_room_details"),
                    danger=self.danger(1 if index == room_count else 0),
                    monster_or_npc=self.pick("dungeon_tables", "dungeon_monsters"),
                    trap_or_hazard=self.pick("dungeon_tables", self.rng.choice(["traps", "hazards"])),
                    clue=self.pick("dungeon_tables", "clues"),
                    treasure=self.pick("dungeon_tables", "treasures"),
                    noncombat_resolution_options=self.pick("monster_tables", "noncombat_options"),
                    preparation_that_helps=self.pick("monster_tables", "monster_weaknesses"),
                    retreat_option=self.pick("dungeon_tables", "retreat_options"),
                )
            )
        return Dungeon(
            name=self.pick("dungeon_tables", "dungeon_names"),
            entrance_description=self.pick("dungeon_tables", "cave_descriptions"),
            theme=self.pick("dungeon_tables", "dungeon_themes"),
            danger_level=self.danger(1),
            number_of_rooms=room_count,
            boss_or_final_threat=self.pick("dungeon_tables", "dungeon_monsters"),
            treasure_or_secret=self.pick("treasure_tables", "weird_relics"),
            connection_to_town=(
                f"A concealed passage below {settlement.important_locations[0].name} once served "
                f"{settlement.name}. The dungeon now feeds the town's problem—"
                f"{settlement.local_problem.lower()}—and preserves evidence of its secret: "
                f"{settlement.local_secret}"
            ),
            rooms=rooms,
        )
