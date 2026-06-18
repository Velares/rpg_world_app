from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any


class TableError(RuntimeError):
    pass


class TableLoader:
    FALLBACK = ["an unsettling, half-remembered omen"]

    def __init__(self, tables_dir: Path):
        self.tables_dir = Path(tables_dir)
        self.tables: dict[str, dict[str, list[Any]]] = {}
        self.warnings: list[str] = []
        self.load_all()

    def load_all(self) -> None:
        self.tables.clear()
        self.warnings.clear()
        if not self.tables_dir.exists():
            self.warnings.append(f"Tables directory is missing: {self.tables_dir}")
            return
        for path in sorted(self.tables_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("root must be a JSON object")
                clean: dict[str, list[Any]] = {}
                for key, value in data.items():
                    if not isinstance(value, list) or not value:
                        self.warnings.append(f"{path.name}:{key} is empty or is not a list")
                        continue
                    clean[key] = value
                self.tables[path.stem] = clean
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                self.warnings.append(f"Could not load {path.name}: {exc}")

    def get(self, table_file: str, category: str) -> list[Any]:
        values = self.tables.get(table_file, {}).get(category)
        if not values:
            self.warnings.append(f"Missing table: {table_file}.{category}")
            return self.FALLBACK
        return values

    def choose(self, table_file: str, category: str, rng: random.Random) -> Any:
        values = self.get(table_file, category)
        choice = rng.choice(values)
        if isinstance(choice, dict) and "value" in choice:
            return choice["value"]
        return choice

    def weighted_choice(self, table_file: str, category: str, rng: random.Random) -> Any:
        values = self.get(table_file, category)
        if values and all(isinstance(item, dict) and "value" in item for item in values):
            return rng.choices(
                [item["value"] for item in values],
                weights=[item.get("weight", 1) for item in values],
                k=1,
            )[0]
        return rng.choice(values)
