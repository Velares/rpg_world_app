from __future__ import annotations

import random
from dataclasses import dataclass

from app.table_loader import TableLoader


@dataclass(frozen=True)
class CharacterProfileDetails:
    """Rules-neutral personal details generated independently of class mechanics."""

    origin_detail: str
    formative_event: str
    personality_trait: str
    ideal: str
    bond: str
    flaw: str


class CharacterProfileGenerator:
    """Build a small character profile from editable JSON text tables."""

    TABLE_FILE = "player_background_tables"

    def __init__(self, tables: TableLoader, rng: random.Random | None = None):
        self.tables = tables
        self.rng = rng or random.Random()

    def generate(self) -> CharacterProfileDetails:
        choose = lambda category: self.tables.choose(
            self.TABLE_FILE, category, self.rng
        )
        return CharacterProfileDetails(
            origin_detail=choose("origins"),
            formative_event=choose("formative_events"),
            personality_trait=choose("personality_traits"),
            ideal=choose("ideals"),
            bond=choose("bonds"),
            flaw=choose("flaws"),
        )
