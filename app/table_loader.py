from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

from app.equipment import EQUIPMENT_SLOTS
from app.table_schemas import (
    BONUS_NAMES,
    FALLBACKS,
    ITEM_CATEGORIES,
    REQUIRED_CATEGORIES,
)


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
        self._validate_item_references()

    def _validate_entries(
        self, file_name: str, category: str, values: list[Any]
    ) -> list[Any]:
        if file_name == "class_tables.json" and category == "classes":
            return self._validate_classes(file_name, category, values)
        if file_name == "item_tables.json":
            if category == "item_definitions":
                return self._validate_item_definitions(file_name, category, values)
            if category == "common_loadout":
                return self._validate_loadout_entries(file_name, category, values)
            if category == "class_loadouts":
                return self._validate_class_loadouts(file_name, category, values)
        if file_name == "downtime_tables.json" and category == "tasks":
            return self._validate_downtime_tasks(file_name, category, values)

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

    def _validate_item_definitions(
        self, file_name: str, category: str, values: list[Any]
    ) -> list[dict[str, Any]]:
        clean: list[dict[str, Any]] = []
        seen: set[str] = set()
        for index, item in enumerate(values):
            location = f"{file_name}:{category}[{index}]"
            if not isinstance(item, dict):
                self._warn(f"{location} must be an object")
                continue
            item_key = item.get("item_key")
            name = item.get("name")
            item_category = item.get("category")
            tags = item.get("tags", [])
            if (
                not isinstance(item_key, str)
                or not item_key.strip()
                or not isinstance(name, str)
                or not name.strip()
                or item_category not in ITEM_CATEGORIES
                or not isinstance(tags, list)
                or any(not isinstance(tag, str) or not tag.strip() for tag in tags)
            ):
                self._warn(
                    f"{location} requires item_key, name, a supported category, "
                    "and text tags"
                )
                continue
            normalized_key = item_key.strip()
            if normalized_key.casefold() in seen:
                self._warn(f"{location} duplicates item key {normalized_key!r}")
                continue
            seen.add(normalized_key.casefold())
            normalized = {
                "item_key": normalized_key,
                "name": name.strip(),
                "category": item_category,
                "description": str(item.get("description", "")).strip(),
                "tags": [tag.strip() for tag in tags],
            }
            bulk = item.get("bulk", 0.0)
            if not isinstance(bulk, (int, float)) or isinstance(bulk, bool) or bulk < 0:
                self._warn(f"{location}.bulk must be a non-negative number")
                continue
            valid_slots = item.get("valid_slots", [])
            if not isinstance(valid_slots, list) or any(
                not isinstance(slot, str) or slot not in EQUIPMENT_SLOTS
                for slot in valid_slots
            ):
                self._warn(f"{location}.valid_slots must be a list of supported slot names")
                continue
            handedness = str(item.get("handedness", "")).strip()
            if handedness not in {"", "1H", "2H"}:
                self._warn(f"{location}.handedness must be '', '1H', or '2H'")
                continue
            speed_factor = item.get("speed_factor", 0)
            if not isinstance(speed_factor, int) or isinstance(speed_factor, bool):
                self._warn(f"{location}.speed_factor must be an integer")
                continue
            capacity_bulk = item.get("capacity_bulk", 0.0)
            if not isinstance(capacity_bulk, (int, float)) or isinstance(
                capacity_bulk, bool
            ) or capacity_bulk < 0:
                self._warn(f"{location}.capacity_bulk must be a non-negative number")
                continue
            normalized.update(
                {
                    "bulk": round(float(bulk), 2),
                    "valid_slots": valid_slots,
                    "handedness": handedness,
                    "speed_factor": speed_factor,
                    "range_profile": str(item.get("range_profile", "")).strip(),
                    "mode": str(item.get("mode", "")).strip(),
                    "placeholder_damage": str(item.get("placeholder_damage", "")).strip(),
                    "placeholder_special_rules": str(
                        item.get("placeholder_special_rules", "")
                    ).strip(),
                    "placeholder_value": str(item.get("placeholder_value", "")).strip(),
                    "placeholder_condition": str(
                        item.get("placeholder_condition", "")
                    ).strip(),
                    "capacity_bulk": round(float(capacity_bulk), 2),
                }
            )
            for flag, default in (
                ("equipped", False),
                ("carried", True),
                ("consumable", False),
                ("quest_related", False),
                ("tradeable", True),
            ):
                value = item.get(flag, default)
                if not isinstance(value, bool):
                    self._warn(f"{location}.{flag} must be true or false")
                    break
                normalized[flag] = value
            else:
                clean.append(normalized)
        return clean

    def _validate_loadout_entries(
        self, file_name: str, category: str, values: list[Any]
    ) -> list[dict[str, Any]]:
        clean: list[dict[str, Any]] = []
        seen: set[str] = set()
        for index, item in enumerate(values):
            location = f"{file_name}:{category}[{index}]"
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("item_key"), str)
                or not item["item_key"].strip()
                or not isinstance(item.get("quantity", 1), int)
                or isinstance(item.get("quantity", 1), bool)
                or item.get("quantity", 1) <= 0
            ):
                self._warn(f"{location} requires item_key and positive quantity")
                continue
            item_key = item["item_key"].strip()
            if item_key.casefold() in seen:
                self._warn(f"{location} duplicates item reference {item_key!r}")
                continue
            seen.add(item_key.casefold())
            clean.append(
                {
                    "item_key": item_key,
                    "quantity": item.get("quantity", 1),
                }
            )
        return clean

    def _validate_class_loadouts(
        self, file_name: str, category: str, values: list[Any]
    ) -> list[dict[str, Any]]:
        clean: list[dict[str, Any]] = []
        seen: set[str] = set()
        for index, item in enumerate(values):
            location = f"{file_name}:{category}[{index}]"
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("class_name"), str)
                or not item["class_name"].strip()
                or not isinstance(item.get("items"), list)
            ):
                self._warn(f"{location} requires class_name and an items list")
                continue
            class_name = item["class_name"].strip()
            if class_name.casefold() in seen:
                self._warn(f"{location} duplicates class name {class_name!r}")
                continue
            seen.add(class_name.casefold())
            entries = self._validate_loadout_entries(
                file_name,
                f"{category}[{index}].items",
                item["items"],
            )
            clean.append({"class_name": class_name, "items": entries})
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

    def _validate_downtime_tasks(
        self, file_name: str, category: str, values: list[Any]
    ) -> list[dict[str, Any]]:
        clean: list[dict[str, Any]] = []
        seen_keys: set[str] = set()
        for index, item in enumerate(values):
            location = f"{file_name}:{category}[{index}]"
            if not isinstance(item, dict):
                self._warn(f"{location} must be an object")
                continue
            required_text = (
                "task_key",
                "name",
                "category",
                "description",
                "progress_text",
                "completion_text",
                "complication_text",
            )
            if any(
                not isinstance(item.get(field), str) or not item[field].strip()
                for field in required_text
            ):
                self._warn(f"{location} is missing a required non-empty text field")
                continue
            duration = item.get("default_duration_days")
            contexts = item.get("allowed_contexts", [])
            tags = item.get("tags", [])
            if (
                not isinstance(duration, int)
                or isinstance(duration, bool)
                or duration <= 0
                or not isinstance(contexts, list)
                or not contexts
                or any(not isinstance(value, str) or not value.strip() for value in contexts)
                or not isinstance(tags, list)
                or any(not isinstance(value, str) or not value.strip() for value in tags)
            ):
                self._warn(
                    f"{location} requires a positive duration plus text "
                    "allowed_contexts and tags lists"
                )
                continue
            task_key = item["task_key"].strip()
            if task_key.casefold() in seen_keys:
                self._warn(f"{location} duplicates task key {task_key!r}")
                continue
            seen_keys.add(task_key.casefold())
            progress_outcomes = self._validate_downtime_outcomes(
                file_name,
                category,
                index,
                "progress_outcomes",
                item.get("progress_outcomes", []),
            )
            completion_outcomes = self._validate_downtime_outcomes(
                file_name,
                category,
                index,
                "completion_outcomes",
                item.get("completion_outcomes", []),
            )
            complication_outcomes = self._validate_downtime_outcomes(
                file_name,
                category,
                index,
                "complication_outcomes",
                item.get("complication_outcomes", []),
            )
            clean.append(
                {
                    "task_key": task_key,
                    "name": item["name"].strip(),
                    "category": item["category"].strip(),
                    "description": item["description"].strip(),
                    "default_duration_days": duration,
                    "allowed_contexts": [value.strip() for value in contexts],
                    "progress_text": item["progress_text"].strip(),
                    "completion_text": item["completion_text"].strip(),
                    "complication_text": item["complication_text"].strip(),
                    "tags": [value.strip() for value in tags],
                    "progress_outcomes": progress_outcomes,
                    "completion_outcomes": completion_outcomes,
                    "complication_outcomes": complication_outcomes,
                }
            )
        return clean

    def _validate_downtime_outcomes(
        self,
        file_name: str,
        category: str,
        task_index: int,
        field_name: str,
        values: Any,
    ) -> list[dict[str, Any]]:
        if values is None:
            return []
        location = f"{file_name}:{category}[{task_index}].{field_name}"
        if not isinstance(values, list):
            self._warn(f"{location} must be a list")
            return []
        clean: list[dict[str, Any]] = []
        valid_kinds = {"event", "lead", "quest_note", "coin", "supplies", "inventory"}
        valid_discovers = {"npc", "location", "rumor", "threat"}
        for index, item in enumerate(values):
            entry_location = f"{location}[{index}]"
            if not isinstance(item, dict):
                self._warn(f"{entry_location} must be an object")
                continue
            kind = item.get("kind")
            text = item.get("text")
            if (
                not isinstance(kind, str)
                or kind not in valid_kinds
                or not isinstance(text, str)
                or not text.strip()
            ):
                self._warn(
                    f"{entry_location} requires a supported kind and non-empty text"
                )
                continue
            discover = item.get("discover")
            if discover is not None and discover not in valid_discovers:
                self._warn(f"{entry_location}.discover is not supported")
                continue
            normalized: dict[str, Any] = {
                "kind": kind,
                "text": text.strip(),
            }
            if discover is not None:
                normalized["discover"] = discover
            if kind in {"coin", "supplies"}:
                amount = item.get("amount")
                if (
                    not isinstance(amount, int)
                    or isinstance(amount, bool)
                    or amount == 0
                ):
                    self._warn(f"{entry_location}.amount must be a non-zero integer")
                    continue
                normalized["amount"] = amount
            if kind == "inventory":
                item_key = item.get("item_key")
                item_name = item.get("item_name")
                item_category = item.get("item_category")
                quantity = item.get("quantity", 1)
                tags = item.get("tags", [])
                if (
                    not isinstance(item_key, str)
                    or not item_key.strip()
                    or not isinstance(item_name, str)
                    or not item_name.strip()
                    or item_category not in ITEM_CATEGORIES
                    or not isinstance(quantity, int)
                    or isinstance(quantity, bool)
                    or quantity <= 0
                    or not isinstance(tags, list)
                    or any(not isinstance(tag, str) or not tag.strip() for tag in tags)
                ):
                    self._warn(
                        f"{entry_location} requires item_key, item_name, item_category, "
                        "positive quantity, and text tags"
                    )
                    continue
                normalized.update(
                    {
                        "item_key": item_key.strip(),
                        "item_name": item_name.strip(),
                        "item_category": item_category,
                        "quantity": quantity,
                        "description": str(item.get("description", "")).strip(),
                        "tags": [tag.strip() for tag in tags],
                    }
                )
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

    def _validate_item_references(self) -> None:
        item_tables = self.tables.get("item_tables")
        if not item_tables:
            return
        known_items = {
            item["item_key"]
            for item in item_tables.get("item_definitions", [])
            if isinstance(item, dict) and item.get("item_key")
        }
        known_classes = {
            item["class_name"]
            for item in self.tables.get("class_tables", {}).get("classes", [])
            if isinstance(item, dict) and item.get("class_name")
        }
        for category in ("common_loadout",):
            item_tables[category] = self._filter_loadout_references(
                category, item_tables.get(category, []), known_items
            )
        valid_loadouts = []
        for index, loadout in enumerate(item_tables.get("class_loadouts", [])):
            if known_classes and loadout["class_name"] not in known_classes:
                self._warn(
                    f"item_tables.json:class_loadouts[{index}] references unknown "
                    f"class {loadout['class_name']!r}"
                )
                continue
            loadout["items"] = self._filter_loadout_references(
                f"class_loadouts[{index}].items",
                loadout.get("items", []),
                known_items,
            )
            valid_loadouts.append(loadout)
        item_tables["class_loadouts"] = valid_loadouts
        if known_classes:
            loadout_classes = {item["class_name"] for item in valid_loadouts}
            for class_name in sorted(known_classes - loadout_classes):
                self._warn(
                    f"Missing class loadout: item_tables.class_loadouts.{class_name}"
                )

    def _filter_loadout_references(
        self,
        category: str,
        entries: list[dict[str, Any]],
        known_items: set[str],
    ) -> list[dict[str, Any]]:
        clean = []
        for index, entry in enumerate(entries):
            if entry["item_key"] not in known_items:
                self._warn(
                    f"item_tables.json:{category}[{index}] references unknown "
                    f"item {entry['item_key']!r}"
                )
                continue
            clean.append(entry)
        return clean

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
        if values and all(isinstance(item, dict) and "value" in item for item in values):
            return rng.choices(
                [item["value"] for item in values],
                weights=[item.get("weight", 1) for item in values],
                k=1,
            )[0]
        return rng.choice(values)

    def weighted_choice(self, table_file: str, category: str, rng: random.Random) -> Any:
        return self.choose(table_file, category, rng)
