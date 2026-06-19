from __future__ import annotations

from app.models import InventoryItem
from app.table_loader import TableLoader


class InventoryCatalog:
    """Build rules-neutral inventory records from editable JSON definitions."""

    TABLE_FILE = "item_tables"

    def __init__(self, tables: TableLoader):
        self.tables = tables

    def definitions(self) -> dict[str, dict]:
        return {
            str(item["item_key"]): item
            for item in self.tables.get(self.TABLE_FILE, "item_definitions")
            if isinstance(item, dict) and item.get("item_key")
        }

    def item(self, item_key: str, quantity: int = 1) -> InventoryItem:
        definition = self.definitions().get(item_key)
        if definition is None:
            raise KeyError(f"Unknown inventory item: {item_key}")
        return InventoryItem(
            item_key=item_key,
            name=str(definition["name"]),
            category=str(definition["category"]),
            quantity=quantity,
            description=str(definition.get("description", "")),
            tags=[str(tag) for tag in definition.get("tags", [])],
            equipped=bool(definition.get("equipped", False)),
            carried=bool(definition.get("carried", True)),
            consumable=bool(definition.get("consumable", False)),
            quest_related=bool(definition.get("quest_related", False)),
            tradeable=bool(definition.get("tradeable", True)),
        )

    def starting_inventory(self, class_name: str) -> list[InventoryItem]:
        entries = list(self.tables.get(self.TABLE_FILE, "common_loadout"))
        class_loadout = next(
            (
                item
                for item in self.tables.get(self.TABLE_FILE, "class_loadouts")
                if isinstance(item, dict) and item.get("class_name") == class_name
            ),
            None,
        )
        if class_loadout:
            entries.extend(class_loadout.get("items", []))

        items: list[InventoryItem] = []
        for entry in entries:
            try:
                items.append(
                    self.item(
                        str(entry["item_key"]),
                        max(1, int(entry.get("quantity", 1))),
                    )
                )
            except (KeyError, TypeError, ValueError):
                # TableLoader reports malformed definitions. Ignore an unusable
                # reference here so character creation remains recoverable.
                continue
        return items
