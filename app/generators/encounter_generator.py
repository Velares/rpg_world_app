from __future__ import annotations

from app.dice import reaction_roll
from app.generators.common import BaseGenerator
from app.ids import new_id
from app.models import Encounter


class EncounterGenerator(BaseGenerator):
    def generate(
        self,
        foreshadowing: str | None = None,
        foreshadows_type: str = "",
        foreshadows_id: str = "",
    ) -> Encounter:
        encounter_type = self.rng.choice(["animal", "monster", "traveler", "landmark"])
        if encounter_type == "monster":
            subject = self.pick("monster_tables", "monster_names")
        elif encounter_type == "traveler":
            subject = self.pick("wilderness_tables", "npc_encounters")
        elif encounter_type == "animal":
            subject = self.pick("wilderness_tables", "animal_encounters")
        else:
            subject = self.pick("wilderness_tables", "landmarks")
        return Encounter(
            what_player_notices_first=self.pick("wilderness_tables", "tracks_and_signs"),
            encounter_type=encounter_type,
            creature_or_npc=subject,
            intent=self.pick("monster_tables", "monster_intents"),
            danger_level=self.danger(),
            signs_or_foreshadowing=foreshadowing or self.pick("monster_tables", "monster_signs"),
            how_to_avoid=self.pick("monster_tables", "avoidance_options"),
            how_to_negotiate=self.pick("monster_tables", "noncombat_options"),
            how_to_fight_safely=self.pick("monster_tables", "safe_combat_options"),
            preparation_that_helps=self.pick("monster_tables", "monster_weaknesses"),
            reward_or_clue=self.pick("treasure_tables", "clue_items"),
            morale=self.rng.randint(4, 11),
            reaction_roll_result=reaction_roll(self.rng),
            entity_id=new_id("enc"),
            foreshadows_type=foreshadows_type,
            foreshadows_id=foreshadows_id,
        )
