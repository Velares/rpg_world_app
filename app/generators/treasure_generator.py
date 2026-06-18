from __future__ import annotations

from app.generators.common import BaseGenerator


class TreasureGenerator(BaseGenerator):
    def generate(self) -> str:
        category = self.rng.choice(
            ["coins", "mundane_treasure", "useful_items", "weird_relics", "minor_magic_items", "cursed_items"]
        )
        return self.pick("treasure_tables", category)
