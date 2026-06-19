from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from app.table_schemas import BONUS_NAMES, FALLBACKS, REQUIRED_CATEGORIES


class TableError(RuntimeError):
    pass


class TableLoader:
    FALLBACK = ("an unsettling, half-remembered omen",)

    def __init__(self, tables_dir: Path):
        self.tables_dir = Path(tables_dir)
        self.tables: dict[str, dict[str, list[Any]]] = {}
        self.warnings: list[str] = []
        self._warning_set: set[str] = set()
        self.load_all()

    def _warn(self, message: str) -> None:
        """Keep diagnostics readable when a missing table is requested often."""
        if message not in self._warning_set:
            self._warning_set.add(message)
            self.warnings.append(message)

    def load_all(self) -> None:
        self.tables.clear()
        self.warnings.clear()
        self._warning_set.clear()
        if not self.tables_dir.exists():
            self._warn(f"Tables directory is missing: {self.tables_dir}")
            return
        for path in sorted(self.tables_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("root must be a JSON object")
                clean: dict[str, list[Any]] = {}
                for key, value in data.items():
                    if not isinstance(value, list) or not value:
                        self._warn(f"{path.name}:{key} must be a non-empty list")
                        continue
                    entries = self._validate_entries(path.name, key, value)
                    if entries:
                        clean[key] = entries
                    else:
                        self._warn(f"{path.name}:{key} has no usable entries")
                self.tables[path.stem] = clean
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                self._warn(f"Could not load {path.name}: {exc}")
        self._validate_required_categories()

    def _validate_entries(
        self, file_name: str, category: str, values: list[Any]
    ) -> list[Any]:
        if file_name == "class_tables.json" and category == "classes":
            return self._validate_classes(file_name, category, values)

        clean: list[Any] = []
        for index, item in enumerate(values):
            if isinstance(item, str) and item.strip():
                clean.append(item.strip())
                continue
            if isinstance(item, dict):
                value = item.get("value")
                weight = item.get("weight", 1)
                if (
                    isinstance(value, str)
                    and value.strip()
                    and isinstance(weight, (int, float))
                    and not isinstance(weight, bool)
                    and weight > 0
                ):
                    clean.append({"value": value.strip(), "weight": weight})
                    continue
            self._warn(
                f"{file_name}:{category}[{index}] is not a usable text or "
                "weighted-text entry"
            )
        return clean

    def _validate_classes(
        self, file_name: str, category: str, values: list[Any]
    ) -> list[dict[str, Any]]:
        clean: list[dict[str, Any]] = []
        required_text = (
            "class_name",
            "role_description",
            "special_ability_placeholder",
        )
        required_numbers = (
            "starting_supplies",
            "starting_food",
            "starting_water",
            "starting_torches",
            "starting_coin",
        )
        seen_names: set[str] = set()
        for index, item in enumerate(values):
            location = f"{file_name}:{category}[{index}]"
            if not isinstance(item, dict):
                self._warn(f"{location} must be an object")
                continue
            if any(
                not isinstance(item.get(field), str) or not item[field].strip()
                for field in required_text
            ):
                self._warn(f"{location} is missing a required non-empty text field")
                continue
            if any(
                not isinstance(item.get(field), int)
                or isinstance(item[field], bool)
                or item[field] < 0
                for field in required_numbers
            ):
                self._warn(f"{location} has an invalid starting resource value")
                continue
            bonuses = item.get("bonuses")
            if not isinstance(bonuses, dict) or any(
                not isinstance(bonuses.get(name), int)
                or isinstance(bonuses[name], bool)
                for name in BONUS_NAMES
            ):
                self._warn(
                    f"{location}.bonuses must contain integer values for "
                    f"{', '.join(BONUS_NAMES)}"
                )
                continue
            class_name = item["class_name"].strip()
            if class_name.casefold() in seen_names:
                self._warn(f"{location} duplicates class name {class_name!r}")
                continue
            seen_names.add(class_name.casefold())
            normalized = dict(item)
            for field in required_text:
                normalized[field] = item[field].strip()
            normalized["bonuses"] = {
                name: bonuses[name] for name in BONUS_NAMES
            }
            clean.append(normalized)
        return clean

    def _validate_required_categories(self) -> None:
        for table_file, categories in REQUIRED_CATEGORIES.items():
            if table_file not in self.tables:
                self._warn(f"Required table file is missing: {table_file}.json")
                continue
            for category in categories:
                if category not in self.tables[table_file]:
                    self._warn(f"Missing required table: {table_file}.{category}")

    def get(self, table_file: str, category: str) -> list[Any]:
        values = self.tables.get(table_file, {}).get(category)
        if not values:
            self._warn(f"Missing table: {table_file}.{category}")
            return list(FALLBACKS.get((table_file, category), self.FALLBACK))
        return values

    def validation_report(self) -> str:
        if not self.warnings:
            return "All generation table files passed validation."
        return "Generation table warnings:\n\n" + "\n".join(
            f"- {warning}" for warning in self.warnings
        )

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
