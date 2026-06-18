from __future__ import annotations

import random

from app.table_loader import TableLoader

DANGER_LEVELS = ["Low", "Guarded", "Dangerous", "Deadly"]


class BaseGenerator:
    def __init__(self, tables: TableLoader, rng: random.Random):
        self.tables = tables
        self.rng = rng

    def pick(self, file: str, category: str):
        return self.tables.choose(file, category, self.rng)

    def danger(self, minimum: int = 0) -> str:
        return self.rng.choice(DANGER_LEVELS[minimum:])

    def settlement_name(self) -> str:
        return (
            f"{self.pick('settlement_tables', 'settlement_names_prefix')}"
            f"{self.pick('settlement_tables', 'settlement_names_suffix')}"
        )
