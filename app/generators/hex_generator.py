from __future__ import annotations

from app.generators.common import BaseGenerator
from app.models import Hex


class HexGenerator(BaseGenerator):
    def generate(self, q: int, r: int, discovered: bool = False) -> Hex:
        return Hex(
            q=q,
            r=r,
            terrain=self.pick("wilderness_tables", "terrain_types"),
            feature=self.pick("wilderness_tables", "dominant_features"),
            encounter_table="local wilderness encounters",
            danger_level=self.danger(),
            discovered=discovered,
        )
