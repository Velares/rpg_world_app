from __future__ import annotations

from app.equipment import EQUIPMENT_SLOTS
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
            bulk=float(definition.get("bulk", 0.0)),
            valid_slots=[str(slot) for slot in definition.get("valid_slots", [])],
            handedness=str(definition.get("handedness", "")),
            speed_factor=int(definition.get("speed_factor", 0)),
            range_profile=str(definition.get("range_profile", "")),
            mode=str(definition.get("mode", "")),
            placeholder_damage=str(definition.get("placeholder_damage", "")),
            placeholder_special_rules=str(
                definition.get("placeholder_special_rules", "")
            ),
            placeholder_value=str(definition.get("placeholder_value", "")),
            placeholder_condition=str(definition.get("placeholder_condition", "")),
            container_capacity_bulk=float(definition.get("capacity_bulk", 0.0)),
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


def equipped_slot_lines(player) -> list[str]:
    lines = []
    for slot_name in EQUIPMENT_SLOTS:
        item = player.slot_item(slot_name)
        label = item.name if item is not None else "-"
        if slot_name == "Off Hand":
            main_hand = player.slot_item("Main Hand")
            if main_hand and main_hand.handedness == "2H" and label == main_hand.name:
                label = f"{label} (occupied by 2H weapon)"
        lines.append(f"{slot_name}: {label}")
    return lines


def inventory_summary_lines(player) -> list[str]:
    return [
        f"{item.name} x{item.quantity} [{item.category}] bulk {item.total_bulk:g}"
        for item in player.inventory
    ]
