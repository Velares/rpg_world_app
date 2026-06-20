from __future__ import annotations

import random

from app.table_loader import TableLoader


class _SafeFormatDict(dict):
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def choose_interaction_text(
    tables: TableLoader,
    rng: random.Random,
    category: str,
    **context,
) -> str:
    template = tables.choose("interaction_tables", category, rng)
    return str(template).format_map(_SafeFormatDict(context))
