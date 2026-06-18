from __future__ import annotations

from app.generators.common import BaseGenerator
from app.ids import new_id
from app.models import AdventureHook, Dungeon, NPC, Settlement


class AdventureGenerator(BaseGenerator):
    def generate(self, settlement: Settlement, npcs: list[NPC], dungeon: Dungeon) -> AdventureHook:
        key_npc = self.rng.choice(npcs)
        return AdventureHook(
            trigger=self.pick("adventure_tables", "triggers"),
            major_goal=self.pick("adventure_tables", "major_goals"),
            obstacle=self.pick("adventure_tables", "obstacles"),
            location=dungeon.name,
            location_feature=self.pick("adventure_tables", "locale_features"),
            phenomenon=self.pick("adventure_tables", "phenomena"),
            villain_goal=self.pick("adventure_tables", "villain_goals"),
            artifact_or_relic=dungeon.treasure_or_secret,
            theme=self.pick("adventure_tables", "themes"),
            key_npc=key_npc.name,
            first_clue=(
                f"{key_npc.name} in {key_npc.location} knows that "
                f"{self.pick('adventure_tables', 'first_clues')}"
            ),
            time_pressure=self.pick("adventure_tables", "time_pressures"),
            failure_consequence=self.pick("adventure_tables", "failure_consequences"),
            noncombat_paths=self.pick("adventure_tables", "noncombat_paths"),
            entity_id=new_id("hook"),
            key_npc_id=key_npc.entity_id,
        )
