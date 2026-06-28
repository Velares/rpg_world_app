from __future__ import annotations

import tkinter as tk
from dataclasses import asdict
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Callable

from app.calendar import age_band, format_calendar
from app.diary import (
    DIARY_SCOPES,
    entries_for_scope,
    format_entry,
    format_scope_text,
    recent_entries_text,
)
from app.downtime import DowntimeEngine
from app.editor_hub import (
    editors_hub_summary_text,
    get_editor_categories,
    get_editor_placeholder_text,
)
from app.equipment import EQUIPMENT_SLOTS
from app.exporters import (
    export_character_text,
    export_event_log_text,
    export_world_summary,
    inventory_item_text,
)
from app.game_state import GameState
from app.inventory import equipped_slot_lines
from app.leads import format_open_leads, format_recent_lead_changes, format_suggested_next_actions
from app.models import World
from app.monster_import_review import (
    build_candidate_rows,
    format_candidate_group,
    format_decision_block,
    get_decision,
    load_canonical_group_report,
    load_decisions,
    save_decisions,
    set_decision,
    review_summary_text,
)
from app.timeline import format_summary_timeline, format_verbose_timeline


TOWN_MODE = "Town Mode"
ADVENTURE_MODE = "Adventure Mode"
GUI_MODES = (TOWN_MODE, ADVENTURE_MODE)
DEFAULT_GUI_MODE = TOWN_MODE

MODE_SIDEBAR_ACTIONS = {
    TOWN_MODE: (
        "Create Character",
        "Settlement Overview",
        "NPC List",
        "Location List",
        "Journal Summary",
    ),
    ADVENTURE_MODE: (
        "Wilderness Overview",
        "Dungeon Overview",
        "Dungeon Rooms",
        "Encounter List",
        "Adventure Hook",
        "Verbose Timeline",
    ),
}

MODE_GAMEPLAY_ACTIONS = {
    TOWN_MODE: (
        "Talk / Socialize",
        "Inspect Town / Current Location",
        "Search Town / Look for Leads",
        "Rest / Recover",
        "Full Rest",
        "Start Downtime",
        "Advance Downtime",
    ),
    ADVENTURE_MODE: (
        "Return to Town",
        "Travel to Location",
        "Travel to Wilderness",
        "Travel to Dungeon",
        "Explore Current Area",
        "Search",
        "Inspect Location",
        "Talk to NPC",
        "Move to Room",
        "Inspect Room",
        "Short Rest",
        "Full Rest",
        "Retreat",
        "Avoid Encounter",
        "Approach Encounter",
        "Investigate Signs",
        "Retreat from Encounter",
    ),
}

SHARED_ACTIONS = (
    "Generate New Region",
    "View Character",
    "Inventory / Equipment",
    "Character Diary",
    "Journal / World Recap",
    "Follow Open Lead",
    "Event Log",
    "Export Event Log",
    "Export World",
    "Export Character",
    "Save World",
    "Load World",
    "Data Diagnostics",
    "Monster Import Review",
    "Editors",
    "Clear Output",
)

ACTION_CHECKS = (
    ("Search Area", "search_area"),
    ("Sneak Past Danger", "sneak_past_danger"),
    ("Read Markings", "read_ancient_markings"),
    ("Negotiate", "negotiate_with_npc"),
    ("Track Creature", "track_creature"),
    ("Force Action", "force_dangerous_action"),
)

WORLD_REQUIRED_ACTIONS = {
    "Create Character",
    "View Character",
    "Settlement Overview",
    "NPC List",
    "Location List",
    "Dungeon Overview",
    "Dungeon Rooms",
    "Wilderness Overview",
    "Encounter List",
    "Adventure Hook",
    "Event Log",
    "Journal Summary",
    "Verbose Timeline",
    "Inventory / Equipment",
    "Character Diary",
    "Follow Open Lead",
    "Export Event Log",
    "Export World",
    "Export Character",
    "Save World",
    "Talk / Socialize",
    "Inspect Town / Current Location",
    "Search Town / Look for Leads",
    "Rest / Recover",
    "Full Rest",
    "Start Downtime",
    "Advance Downtime",
    "Return to Town",
    "Travel to Location",
    "Travel to Wilderness",
    "Travel to Dungeon",
    "Explore Current Area",
    "Search",
    "Inspect Location",
    "Talk to NPC",
    "Move to Room",
    "Inspect Room",
    "Short Rest",
    "Retreat",
    "Avoid Encounter",
    "Approach Encounter",
    "Investigate Signs",
    "Retreat from Encounter",
}

CHARACTER_REQUIRED_ACTIONS = {
    "View Character",
    "Inventory / Equipment",
    "Character Diary",
    "Export Character",
    "Start Downtime",
    "Advance Downtime",
    "Search Area",
    "Sneak Past Danger",
    "Read Markings",
    "Negotiate",
    "Track Creature",
    "Force Action",
}


def label(text: str) -> str:
    return text.replace("_", " ").title()


def block(title: str, values: dict, skip: set[str] | None = None) -> str:
    skip = skip or set()
    lines = [title.upper(), "=" * len(title)]
    for key, value in values.items():
        if key in skip:
            continue
        lines.append(f"{label(key)}: {value}")
    return "\n".join(lines)


def shared_action_labels() -> tuple[str, ...]:
    return SHARED_ACTIONS


def mode_sidebar_labels(mode: str) -> tuple[str, ...]:
    if mode not in MODE_SIDEBAR_ACTIONS:
        raise ValueError(f"Unknown GUI mode: {mode}")
    return MODE_SIDEBAR_ACTIONS[mode]


def mode_gameplay_labels(mode: str) -> tuple[str, ...]:
    if mode not in MODE_GAMEPLAY_ACTIONS:
        raise ValueError(f"Unknown GUI mode: {mode}")
    return MODE_GAMEPLAY_ACTIONS[mode]


def action_check_labels() -> tuple[str, ...]:
    return tuple(label for label, _key in ACTION_CHECKS)


def action_is_enabled(
    action_label: str,
    *,
    has_world: bool,
    has_character: bool,
) -> bool:
    if action_label in WORLD_REQUIRED_ACTIONS and not has_world:
        return False
    if action_label in CHARACTER_REQUIRED_ACTIONS and not has_character:
        return False
    return True


def format_world_recap(world: World | None) -> str:
    if world is None:
        return (
            "WORLD RECAP\n"
            "===========\n"
            "Generate or load a world first."
        )
    player = world.player_state
    character = player.character
    character_line = (
        f"{character.name}, {character.character_class}, age {character.age_years} "
        f"({age_band(character.age_years)})"
        if character
        else "No character created yet."
    )
    location_line = player.current_location
    if player.current_room_id is not None:
        location_line += f" / room {player.current_room_id}"
    known_rumors = [
        world.settlement.rumors[index]
        for index in player.known_rumor_indices
        if index < len(world.settlement.rumors)
    ]
    key_npcs = [npc for npc in world.npcs if npc.is_key_npc][:5]
    prominent_npcs = [
        npc for npc in world.npcs if npc.prominent and not npc.is_key_npc
    ][:5]
    recent_events = player.event_log[-5:]
    faction_notes = [
        f"{tag}: {status}" for tag, status in sorted(world.faction_status_notes.items())
    ]
    summary_lines = _body_lines(format_summary_timeline(world))
    return "\n".join(
        [
            "WORLD RECAP",
            "===========",
            f"Seed: {world.generation_seed or 'Random / not recorded'}",
            f"Calendar: {format_calendar(player.day, player.time_period)}",
            f"Character: {character_line}",
            f"Current Location: {location_line}",
            f"Settlement: {world.settlement.name}",
            f"Downtime: {DowntimeEngine.summarize(player.active_downtime_task)}",
            "",
            "RESOURCES",
            "=========",
            (
                f"Supplies {player.supplies} | Food {player.food} | Water {player.water} | "
                f"Torches {player.torches} | Coin {player.coin} | Wounds {player.wounds}"
            ),
            "",
            "LOADOUT",
            "=======",
            (
                f"Total Bulk {player.total_carried_bulk():g} | Equipped Bulk {player.equipped_bulk():g} | "
                f"Encumbrance {player.encumbrance_state()}"
            ),
            _bulleted_or_fallback(
                equipped_slot_lines(player),
                "No equipment slots recorded.",
            ),
            "",
            "OPEN LEADS",
            "==========",
            format_open_leads(world),
            "",
            "RECENT LEAD CHANGES",
            "===================",
            format_recent_lead_changes(world),
            "",
            "SUGGESTED NEXT ACTIONS",
            "======================",
            format_suggested_next_actions(world),
            "",
            "QUEST NOTES",
            "===========",
            _bulleted_or_fallback(player.quest_log, "No quest notes recorded."),
            "",
            "KNOWN CLUES AND THREATS",
            "=======================",
            _bulleted_or_fallback(
                [
                    *known_rumors[:3],
                    *player.known_threats[:3],
                ],
                "No clues or threats recorded yet.",
            ),
            "",
            "KEY NPCS",
            "========",
            _bulleted_or_fallback(
                [
                    f"{npc.name} [{npc.faction_tag}] - {npc.key_npc_reason or 'Important contact.'}"
                    for npc in key_npcs
                ],
                "No key NPCs yet.",
            ),
            "",
            "OTHER PROMINENT NPCS",
            "====================",
            _bulleted_or_fallback(
                [
                    f"{npc.name} - {npc.prominence_notes or 'Recurring figure.'}"
                    for npc in prominent_npcs
                ],
                "No additional prominent NPCs yet.",
            ),
            "",
            "FACTION AND RELATIONSHIP NOTES",
            "==============================",
            _bulleted_or_fallback(
                faction_notes,
                "No faction or relationship notes recorded yet.",
            ),
            "",
            "RECENT IMPORTANT EVENTS",
            "=======================",
            _numbered_or_fallback(recent_events, "No recent events recorded yet."),
            "",
            "DIARY HIGHLIGHTS",
            "================",
            recent_entries_text(player),
            "",
            "JOURNAL SUMMARY",
            "===============",
            "\n".join(summary_lines) or "No timeline activity has been summarized yet.",
        ]
    )


def _body_lines(text: str) -> list[str]:
    lines = text.splitlines()
    if len(lines) <= 4:
        return lines
    return lines[4:] or lines


def _bulleted_or_fallback(values: list[str], fallback: str) -> str:
    return "\n".join(f"- {value}" for value in values if value) or fallback


def _numbered_or_fallback(values: list[str], fallback: str) -> str:
    return "\n".join(
        f"{index}. {value}" for index, value in enumerate((value for value in values if value), 1)
    ) or fallback


class LoadDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, worlds: list[tuple[int, str, str]]):
        super().__init__(parent)
        self.title("Load World")
        self.geometry("560x300")
        self.transient(parent)
        self.grab_set()
        self.selected_id: int | None = None
        self.tree = ttk.Treeview(self, columns=("name", "created"), show="headings")
        self.tree.heading("name", text="Save Name")
        self.tree.heading("created", text="Created")
        self.tree.column("name", width=250)
        self.tree.column("created", width=270)
        for world_id, name, created in worlds:
            self.tree.insert("", "end", iid=str(world_id), values=(name, created))
        self.tree.pack(fill="both", expand=True, padx=12, pady=12)
        ttk.Button(self, text="Load Selected", command=self.accept).pack(pady=(0, 12))
        self.tree.bind("<Double-1>", lambda _event: self.accept())

    def accept(self) -> None:
        selection = self.tree.selection()
        if selection:
            self.selected_id = int(selection[0])
            self.destroy()


class CharacterDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, classes, backgrounds: list[str], random_name):
        super().__init__(parent)
        self.title("Create Character")
        self.geometry("520x430")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.result: tuple[str, str, str] | None = None
        self.classes = {item.class_name: item for item in classes}

        form = ttk.Frame(self, padding=14)
        form.pack(fill="both", expand=True)
        ttk.Label(form, text="Name").pack(anchor="w")
        self.name_var = tk.StringVar()
        name_row = ttk.Frame(form)
        name_row.pack(fill="x", pady=(2, 10))
        ttk.Entry(name_row, textvariable=self.name_var).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(
            name_row,
            text="Random Name",
            command=lambda: self.name_var.set(random_name()),
        ).pack(side="left", padx=(8, 0))
        ttk.Label(form, text="Class").pack(anchor="w")
        self.class_var = tk.StringVar(value=classes[0].class_name)
        class_box = ttk.Combobox(
            form,
            textvariable=self.class_var,
            values=[item.class_name for item in classes],
            state="readonly",
        )
        class_box.pack(fill="x", pady=(2, 10))
        ttk.Label(form, text="Background").pack(anchor="w")
        self.background_var = tk.StringVar(value=backgrounds[0])
        ttk.Combobox(
            form,
            textvariable=self.background_var,
            values=backgrounds,
            state="readonly",
        ).pack(fill="x", pady=(2, 10))
        self.preview_var = tk.StringVar()
        ttk.Label(
            form,
            textvariable=self.preview_var,
            justify="left",
            wraplength=480,
        ).pack(fill="x", pady=10)
        buttons = ttk.Frame(form)
        buttons.pack(side="bottom", fill="x")
        ttk.Button(buttons, text="Create", command=self.accept).pack(side="right")
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="right", padx=8)
        class_box.bind("<<ComboboxSelected>>", lambda _event: self.update_preview())
        self.update_preview()

    def update_preview(self) -> None:
        definition = self.classes[self.class_var.get()]
        bonuses = ", ".join(
            f"{name.title()} {value:+d}" for name, value in definition.bonuses.items()
        )
        self.preview_var.set(
            f"{definition.role_description}\n\n"
            f"Starting resources: supplies {definition.starting_supplies}, "
            f"food {definition.starting_food}, water {definition.starting_water}, "
            f"torches {definition.starting_torches}, coin {definition.starting_coin}\n\n"
            f"Bonuses: {bonuses}\n"
            f"Ability placeholder: {definition.special_ability_placeholder}\n\n"
            "Origin, formative event, personality, ideal, bond, and flaw "
            "will be generated from the editable player background tables."
        )

    def accept(self) -> None:
        if not self.name_var.get().strip():
            messagebox.showwarning("Create Character", "Enter a character name.", parent=self)
            return
        self.result = (
            self.name_var.get().strip(),
            self.class_var.get(),
            self.background_var.get(),
        )
        self.destroy()


class DiaryEntryDialog(tk.Toplevel):
    def __init__(
        self,
        parent: tk.Misc,
        *,
        title_text: str,
        entry_title: str = "",
        entry_text: str = "",
        player_notes: str = "",
        protected: bool = False,
    ):
        super().__init__(parent)
        self.title(title_text)
        self.geometry("620x520")
        self.transient(parent)
        self.grab_set()
        self.result: dict[str, str] | None = None
        form = ttk.Frame(self, padding=12)
        form.pack(fill="both", expand=True)
        ttk.Label(form, text="Title").pack(anchor="w")
        self.title_var = tk.StringVar(value=entry_title)
        title_entry = ttk.Entry(form, textvariable=self.title_var)
        title_entry.pack(fill="x", pady=(2, 8))
        ttk.Label(form, text="Entry Text").pack(anchor="w")
        self.text_box = tk.Text(form, height=12, wrap="word")
        self.text_box.pack(fill="both", expand=True, pady=(2, 8))
        self.text_box.insert("1.0", entry_text)
        ttk.Label(form, text="Player Notes").pack(anchor="w")
        self.notes_box = tk.Text(form, height=8, wrap="word")
        self.notes_box.pack(fill="both", expand=True, pady=(2, 8))
        self.notes_box.insert("1.0", player_notes)
        if protected:
            title_entry.configure(state="disabled")
            self.text_box.configure(state="disabled")
            ttk.Label(
                form,
                text="Protected milestone: original title and text stay read-only, but player notes may be added.",
                wraplength=560,
                justify="left",
            ).pack(anchor="w", pady=(0, 8))
        buttons = ttk.Frame(form)
        buttons.pack(fill="x")
        ttk.Button(buttons, text="Save", command=self.accept).pack(side="right")
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(
            side="right", padx=(0, 8)
        )

    def accept(self) -> None:
        self.result = {
            "title": self.title_var.get().strip(),
            "text": self.text_box.get("1.0", "end").strip(),
            "player_notes": self.notes_box.get("1.0", "end").strip(),
        }
        self.destroy()


class EquipmentDialog(tk.Toplevel):
    def __init__(self, parent: tk.Misc, state: GameState):
        super().__init__(parent)
        self.state = state
        self.title("Inventory / Equipment")
        self.geometry("900x620")
        self.transient(parent)
        self.grab_set()
        self.item_options: dict[str, str] = {}
        self.item_var = tk.StringVar()
        self.slot_var = tk.StringVar(value=EQUIPMENT_SLOTS[0])

        container = ttk.Frame(self, padding=12)
        container.pack(fill="both", expand=True)
        controls = ttk.Frame(container)
        controls.pack(fill="x", pady=(0, 8))
        ttk.Label(controls, text="Item").grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.item_box = ttk.Combobox(controls, textvariable=self.item_var, state="readonly")
        self.item_box.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        ttk.Label(controls, text="Slot").grid(row=0, column=2, sticky="w", padx=(0, 6))
        self.slot_box = ttk.Combobox(
            controls,
            textvariable=self.slot_var,
            values=list(EQUIPMENT_SLOTS),
            state="readonly",
        )
        self.slot_box.grid(row=0, column=3, sticky="ew", padx=(0, 10))
        ttk.Button(controls, text="Equip", command=self.equip_selected).grid(row=0, column=4, padx=(0, 6))
        ttk.Button(controls, text="Unequip Slot", command=self.unequip_selected).grid(row=0, column=5, padx=(0, 6))
        ttk.Button(controls, text="Refresh", command=self.refresh).grid(row=0, column=6, padx=(0, 6))
        ttk.Button(controls, text="Close", command=self.destroy).grid(row=0, column=7)
        controls.columnconfigure(1, weight=2)
        controls.columnconfigure(3, weight=1)

        self.summary_var = tk.StringVar()
        ttk.Label(container, textvariable=self.summary_var, justify="left").pack(fill="x", pady=(0, 8))

        body = ttk.Frame(container)
        body.pack(fill="both", expand=True)
        self.equipment_text = tk.Text(body, wrap="word", font=("Consolas", 10), padx=10, pady=10)
        self.equipment_text.pack(side="left", fill="both", expand=True)
        self.inventory_text = tk.Text(body, wrap="word", font=("Consolas", 10), padx=10, pady=10)
        self.inventory_text.pack(side="left", fill="both", expand=True)
        self.refresh()

    def refresh(self) -> None:
        world = self.state.require_world()
        player = world.player_state
        self.item_options = {
            f"{item.name} [{item.instance_id}]": item.instance_id
            for item in player.inventory
        }
        self.item_box.configure(values=list(self.item_options))
        if self.item_options and self.item_var.get() not in self.item_options:
            self.item_var.set(next(iter(self.item_options)))
        self.summary_var.set(
            f"Total Bulk: {player.total_carried_bulk():g} | Equipped Bulk: {player.equipped_bulk():g} | "
            f"Encumbrance: {player.encumbrance_state()} | Strength Capacity Baseline: {player.strength_score()}"
        )
        self.equipment_text.delete("1.0", "end")
        self.equipment_text.insert(
            "1.0",
            "EQUIPPED SLOTS\n==============\n"
            + "\n".join(equipped_slot_lines(player))
            + "\n\nENCUMBRANCE EFFECTS\n===================\n"
            + "\n".join(
                f"{key.replace('_', ' ').title()}: {value}"
                for key, value in player.encumbrance_effects().items()
            ),
        )
        self.inventory_text.delete("1.0", "end")
        inventory_lines = [
            f"- {inventory_item_text(item, detailed=True)}"
            + (
                f"\n  Slots: {', '.join(item.valid_slots)}"
                if item.valid_slots else ""
            )
            for item in player.inventory
        ]
        self.inventory_text.insert(
            "1.0",
            "INVENTORY\n=========\n" + ("\n".join(inventory_lines) or "No items."),
        )

    def equip_selected(self) -> None:
        label = self.item_var.get()
        if not label:
            raise RuntimeError("Select an item to equip.")
        self.state.equip_item(self.item_options[label], self.slot_var.get())
        self.refresh()

    def unequip_selected(self) -> None:
        self.state.unequip_slot(self.slot_var.get())
        self.refresh()


class RPGWorldApp(tk.Tk):
    def __init__(self, state: GameState):
        super().__init__()
        self.state = state
        self.title("RPG World App — Weird Fantasy Region Generator")
        self.geometry("1100x720")
        self.minsize(800, 520)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.status_var = tk.StringVar(value="Ready. Generate a region to begin.")
        self.player_state_var = tk.StringVar(value="No active world.")
        self.check_difficulty_var = tk.StringVar(value="Standard")
        self.seed_var = tk.StringVar(value="")
        self.mode_var = tk.StringVar(value=DEFAULT_GUI_MODE)
        self.current_major_view = "play"
        self.selection_handler = None
        self.sidebar_buttons: dict[str, ttk.Button] = {}
        self.gameplay_buttons: dict[str, ttk.Button] = {}
        self.check_buttons: dict[str, ttk.Button] = {}
        self.diary_lists: dict[str, tk.Listbox] = {}
        self.diary_scope_entries: dict[str, list[str]] = {}
        self._build()
        self.update_player_state()
        warning_count = len(self.state.tables.warnings) + len(
            self.state.name_generator.warnings
        )
        if warning_count:
            self.status_var.set(
                f"Loaded with {warning_count} data warning(s); see Data Diagnostics."
            )

    def _build(self) -> None:
        container = ttk.Frame(self, padding=10)
        container.pack(fill="both", expand=True)
        sidebar = ttk.Frame(container)
        sidebar.pack(side="left", fill="y", padx=(0, 10))
        seed_box = ttk.LabelFrame(sidebar, text="Generation Seed", padding=6)
        seed_box.pack(fill="x", pady=(0, 8))
        ttk.Entry(seed_box, textvariable=self.seed_var).pack(fill="x")
        ttk.Label(
            seed_box,
            text="Leave blank for normal random generation.",
            justify="left",
            wraplength=180,
        ).pack(anchor="w", pady=(4, 0))
        mode_box = ttk.LabelFrame(sidebar, text="Play Mode", padding=6)
        mode_box.pack(fill="x", pady=(0, 8))
        ttk.Label(mode_box, textvariable=self.mode_var, anchor="center").pack(fill="x")
        toggle_row = ttk.Frame(mode_box)
        toggle_row.pack(fill="x", pady=(6, 0))
        ttk.Button(
            toggle_row,
            text=TOWN_MODE,
            command=lambda: self.set_mode(TOWN_MODE),
        ).pack(side="left", fill="x", expand=True, padx=(0, 4))
        ttk.Button(
            toggle_row,
            text=ADVENTURE_MODE,
            command=lambda: self.set_mode(ADVENTURE_MODE),
        ).pack(side="left", fill="x", expand=True)
        self.mode_sidebar_frame = ttk.LabelFrame(sidebar, text="Mode Views", padding=4)
        self.mode_sidebar_frame.pack(fill="x", pady=(0, 8))
        self.shared_sidebar_frame = ttk.LabelFrame(sidebar, text="Shared Actions", padding=4)
        self.shared_sidebar_frame.pack(fill="x", pady=(0, 8))
        # Version 0.2 adds a lightweight record browser between navigation
        # and the detail pane. It is reused for NPCs, locations, rooms, and encounters.
        self.index_frame = ttk.Frame(container)
        self.index_title = ttk.Label(self.index_frame, text="Items", font=("", 10, "bold"))
        self.index_title.pack(fill="x", pady=(0, 5))
        self.index_list = tk.Listbox(self.index_frame, width=32, exportselection=False)
        index_scroll = ttk.Scrollbar(
            self.index_frame, orient="vertical", command=self.index_list.yview
        )
        self.index_list.configure(yscrollcommand=index_scroll.set)
        self.index_list.pack(side="left", fill="both", expand=True)
        index_scroll.pack(side="right", fill="y")
        self.index_list.bind("<<ListboxSelect>>", self._on_index_selected)
        self.display_frame = ttk.Frame(container)
        self.display_frame.pack(side="left", fill="both", expand=True)
        self.sidebar_command_map = {
            "Generate New Region": self.generate,
            "Create Character": self.create_character,
            "View Character": self.view_character,
            "Inventory / Equipment": self.view_equipment,
            "Character Diary": self.view_diary,
            "Settlement Overview": self.view_settlement,
            "NPC List": self.view_npcs,
            "Location List": self.view_locations,
            "Dungeon Overview": self.view_dungeon,
            "Dungeon Rooms": self.view_dungeon_rooms,
            "Wilderness Overview": self.view_wilderness,
            "Encounter List": self.view_encounters,
            "Adventure Hook": self.view_hook,
            "Event Log": self.view_event_log,
            "Journal / World Recap": self.view_world_recap,
            "Follow Open Lead": self.follow_open_lead,
            "Journal Summary": self.view_timeline_summary,
            "Verbose Timeline": self.view_verbose_timeline,
            "Export Event Log": self.export_event_log,
            "Export World": self.export_world,
            "Export Character": self.export_character,
            "Data Diagnostics": self.view_data_diagnostics,
            "Monster Import Review": self.view_monster_import_review,
            "Editors": self.view_editors,
            "Save World": self.save_world,
            "Load World": self.load_world,
            "Clear Output": self.clear_output,
        }

        state_box = ttk.LabelFrame(self.display_frame, text="Player State", padding=7)
        state_box.pack(fill="x", pady=(0, 7))
        ttk.Label(
            state_box,
            textvariable=self.player_state_var,
            anchor="w",
            justify="left",
        ).pack(fill="x")

        # Exploration controls stay separate from the content browser so the
        # established Version 0.2 navigation remains uncluttered.
        self.gameplay_command_map = {
            "Talk / Socialize": lambda: self.perform_action(self.state.talk_to_npc),
            "Inspect Town / Current Location": lambda: self.perform_action(
                self.state.inspect_location
            ),
            "Search Town / Look for Leads": lambda: self.perform_action(self.state.search),
            "Rest / Recover": lambda: self.perform_action(self.state.rest),
            "Start Downtime": self.start_downtime,
            "Advance Downtime": self.advance_downtime,
            "Return to Town": lambda: self.perform_action(lambda: self.state.travel("town")),
            "Travel to Location": self.travel_to_location,
            "Travel to Wilderness": lambda: self.perform_action(
                lambda: self.state.travel("wilderness")
            ),
            "Travel to Dungeon": lambda: self.perform_action(
                lambda: self.state.travel("dungeon_entrance")
            ),
            "Explore Current Area": lambda: self.perform_action(self.state.explore_current_area),
            "Search": lambda: self.perform_action(self.state.search),
            "Inspect Location": lambda: self.perform_action(self.state.inspect_location),
            "Talk to NPC": lambda: self.perform_action(self.state.talk_to_npc),
            "Move to Room": self.move_room,
            "Inspect Room": lambda: self.perform_action(self.state.inspect_room),
            "Short Rest": lambda: self.perform_action(self.state.rest),
            "Full Rest": lambda: self.perform_action(self.state.full_rest),
            "Retreat": lambda: self.perform_action(self.state.retreat),
            "Avoid Encounter": lambda: self.encounter_choice("avoid"),
            "Approach Encounter": lambda: self.encounter_choice("approach"),
            "Investigate Signs": lambda: self.encounter_choice("investigate"),
            "Retreat from Encounter": lambda: self.encounter_choice("retreat"),
        }
        self.mode_action_box = ttk.LabelFrame(
            self.display_frame, text=f"{DEFAULT_GUI_MODE} Actions", padding=5
        )
        self.mode_action_box.pack(fill="x", pady=(0, 7))

        self.check_box = ttk.LabelFrame(self.display_frame, text="Action Checks", padding=5)
        ttk.Label(self.check_box, text="Difficulty").grid(row=0, column=0, padx=2, pady=2)
        ttk.Combobox(
            self.check_box,
            textvariable=self.check_difficulty_var,
            values=["Easy", "Standard", "Hard", "Severe"],
            state="readonly",
            width=10,
        ).grid(row=0, column=1, sticky="ew", padx=2, pady=2)
        for index, (text, action_key) in enumerate(ACTION_CHECKS, start=2):
            button = ttk.Button(
                self.check_box,
                text=text,
                command=lambda key=action_key: self.perform_check(key),
            )
            button.grid(row=0, column=index, sticky="ew", padx=2, pady=2)
            self.check_buttons[text] = button
        for column in range(8):
            self.check_box.columnconfigure(column, weight=1)
        self.output = tk.Text(
            self.display_frame,
            wrap="word",
            font=("Consolas", 10),
            padx=12,
            pady=12,
            undo=False,
        )
        self.output_scrollbar = ttk.Scrollbar(
            self.display_frame, orient="vertical", command=self.output.yview
        )
        self.output.configure(yscrollcommand=self.output_scrollbar.set)
        self.output.pack(side="left", fill="both", expand=True)
        self.output_scrollbar.pack(side="right", fill="y")
        self._build_diary_area()
        ttk.Label(self, textvariable=self.status_var, anchor="w", padding=(10, 5)).pack(
            fill="x", side="bottom"
        )
        self._render_sidebar_actions()
        self._render_mode_actions()

    @staticmethod
    def _clear_children(frame: ttk.Frame) -> None:
        for child in frame.winfo_children():
            child.destroy()

    def _build_diary_area(self) -> None:
        self.diary_frame = ttk.Frame(self.display_frame)
        controls = ttk.Frame(self.diary_frame)
        controls.pack(fill="x", pady=(0, 8))
        ttk.Button(controls, text="Add Entry", command=self.add_diary_entry).pack(
            side="left"
        )
        ttk.Button(controls, text="Edit / Add Note", command=self.edit_diary_entry).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(controls, text="Hide Entry", command=self.hide_diary_entry).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(controls, text="Delete Entry", command=self.delete_diary_entry).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(controls, text="Refresh", command=self.refresh_diary_view).pack(
            side="left", padx=(6, 0)
        )
        ttk.Button(controls, text="Exit Diary", command=self.exit_diary_view).pack(
            side="right"
        )
        body = ttk.Frame(self.diary_frame)
        body.pack(fill="both", expand=True)
        self.diary_notebook = ttk.Notebook(body)
        self.diary_notebook.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.diary_notebook.bind("<<NotebookTabChanged>>", lambda _event: self._sync_diary_detail())
        self.diary_detail = tk.Text(body, wrap="word", font=("Consolas", 10), padx=10, pady=10)
        self.diary_detail.pack(side="left", fill="both", expand=True)
        for scope in DIARY_SCOPES:
            frame = ttk.Frame(self.diary_notebook, padding=6)
            listbox = tk.Listbox(frame, exportselection=False)
            scrollbar = ttk.Scrollbar(frame, orient="vertical", command=listbox.yview)
            listbox.configure(yscrollcommand=scrollbar.set)
            listbox.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            listbox.bind("<<ListboxSelect>>", lambda _event, value=scope: self._show_diary_entry_detail(value))
            self.diary_notebook.add(frame, text=scope.title())
            self.diary_lists[scope] = listbox

    def _render_sidebar_actions(self) -> None:
        self._clear_children(self.mode_sidebar_frame)
        self._clear_children(self.shared_sidebar_frame)
        self.sidebar_buttons = {}
        for text in mode_sidebar_labels(self.mode_var.get()):
            button = ttk.Button(
                self.mode_sidebar_frame,
                text=text,
                command=self.sidebar_command_map[text],
                width=24,
            )
            button.pack(fill="x", pady=2)
            self.sidebar_buttons[text] = button
        for text in shared_action_labels():
            button = ttk.Button(
                self.shared_sidebar_frame,
                text=text,
                command=self.sidebar_command_map[text],
                width=24,
            )
            button.pack(fill="x", pady=2)
            self.sidebar_buttons[text] = button

    def _render_mode_actions(self) -> None:
        mode = self.mode_var.get()
        self._clear_children(self.mode_action_box)
        self.gameplay_buttons = {}
        self.mode_action_box.configure(text=f"{mode} Actions")
        for index, text in enumerate(mode_gameplay_labels(mode)):
            row, column = divmod(index, 4)
            button = ttk.Button(
                self.mode_action_box,
                text=text,
                command=self.gameplay_command_map[text],
            )
            button.grid(row=row, column=column, sticky="ew", padx=2, pady=2)
            self.gameplay_buttons[text] = button
        for column in range(4):
            self.mode_action_box.columnconfigure(column, weight=1)
        if mode == ADVENTURE_MODE:
            if not self.check_box.winfo_ismapped():
                self.check_box.pack(fill="x", pady=(0, 7), before=self.output)
        else:
            self.check_box.pack_forget()
        self.refresh_action_states()

    def refresh_action_states(self) -> None:
        world = self.state.world
        has_world = world is not None
        has_character = bool(has_world and world.player_state.character is not None)
        for label_text, button in self.sidebar_buttons.items():
            button.configure(
                state=(
                    "normal"
                    if action_is_enabled(
                        label_text,
                        has_world=has_world,
                        has_character=has_character,
                    )
                    else "disabled"
                )
            )
        for label_text, button in self.gameplay_buttons.items():
            button.configure(
                state=(
                    "normal"
                    if action_is_enabled(
                        label_text,
                        has_world=has_world,
                        has_character=has_character,
                    )
                    else "disabled"
                )
            )
        check_state = "normal" if has_world and has_character else "disabled"
        for button in self.check_buttons.values():
            button.configure(state=check_state)
        if hasattr(self, "check_box"):
            children = self.check_box.winfo_children()
            if children:
                for child in children[:2]:
                    try:
                        child.configure(state=check_state)
                    except tk.TclError:
                        pass

    def set_mode(self, mode: str) -> None:
        if mode not in GUI_MODES:
            self.status_var.set(f"Unknown mode: {mode}")
            return
        self.mode_var.set(mode)
        self._render_sidebar_actions()
        self._render_mode_actions()
        self.status_var.set(f"Switched to {mode}.")

    def show(self, text: str, status: str = "Ready.") -> None:
        if self.current_major_view == "diary":
            self.exit_diary_view()
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)
        self.output.see("1.0")
        self.status_var.set(status)

    def hide_index(self) -> None:
        self.index_frame.pack_forget()
        self.index_list.delete(0, "end")
        self.selection_handler = None

    def show_index(self, title: str, labels: list[str], handler) -> None:
        """Populate the reusable list pane and route selection to a detail renderer."""
        self.index_title.configure(text=title)
        self.index_list.delete(0, "end")
        for item in labels:
            self.index_list.insert("end", item)
        self.selection_handler = handler
        if not self.index_frame.winfo_ismapped():
            self.index_frame.pack(
                side="left", fill="y", padx=(0, 10), before=self.display_frame
            )

    def _on_index_selected(self, _event=None) -> None:
        selection = self.index_list.curselection()
        if selection and self.selection_handler:
            self.selection_handler(selection[0])

    def guarded(self, callback) -> None:
        try:
            callback()
        except Exception as exc:
            messagebox.showerror("RPG World App", str(exc), parent=self)
            self.status_var.set(str(exc))

    def _active_diary_scope(self) -> str:
        current = self.diary_notebook.index(self.diary_notebook.select())
        return DIARY_SCOPES[current]

    def _selected_diary_entry_id(self) -> str | None:
        scope = self._active_diary_scope()
        listbox = self.diary_lists[scope]
        selection = listbox.curselection()
        if not selection:
            return None
        entries = self.diary_scope_entries.get(scope, [])
        return entries[selection[0]] if selection[0] < len(entries) else None

    def _selected_diary_entry(self):
        entry_id = self._selected_diary_entry_id()
        if entry_id is None or self.state.world is None:
            return None
        player = self.state.world.player_state
        return next(
            (entry for entry in player.diary_entries if entry.entry_id == entry_id),
            None,
        )

    def _show_diary_entry_detail(self, scope: str | None = None) -> None:
        if self.state.world is None:
            self.diary_detail.delete("1.0", "end")
            self.diary_detail.insert("1.0", "Generate or load a world first.")
            return
        entry = self._selected_diary_entry()
        if entry is None:
            scope = scope or self._active_diary_scope()
            self.diary_detail.delete("1.0", "end")
            self.diary_detail.insert(
                "1.0",
                format_scope_text(self.state.world.player_state, scope),
            )
            return
        self.diary_detail.delete("1.0", "end")
        self.diary_detail.insert("1.0", format_entry(entry))

    def _sync_diary_detail(self) -> None:
        self._show_diary_entry_detail(self._active_diary_scope())

    def refresh_diary_view(self) -> None:
        if self.state.world is None:
            return
        player = self.state.world.player_state
        for scope in DIARY_SCOPES:
            listbox = self.diary_lists[scope]
            listbox.delete(0, "end")
            entries = entries_for_scope(player, scope)
            self.diary_scope_entries[scope] = [entry.entry_id for entry in entries]
            for entry in entries:
                prefix = "[Milestone] " if entry.protected else ""
                listbox.insert("end", f"{prefix}{entry.title}")
        self._sync_diary_detail()

    def view_diary(self) -> None:
        def action():
            self.state.require_world()
            self.current_major_view = "diary"
            self.hide_index()
            self.mode_action_box.pack_forget()
            self.check_box.pack_forget()
            self.output.pack_forget()
            self.output_scrollbar.pack_forget()
            self.diary_frame.pack(fill="both", expand=True)
            self.refresh_diary_view()
            self.status_var.set("Viewing character diary.")

        self.guarded(action)

    def exit_diary_view(self) -> None:
        if self.current_major_view != "diary":
            return
        self.current_major_view = "play"
        self.diary_frame.pack_forget()
        self.mode_action_box.pack(fill="x", pady=(0, 7))
        if self.mode_var.get() == ADVENTURE_MODE:
            self.check_box.pack(fill="x", pady=(0, 7), before=self.output)
        self.output.pack(side="left", fill="both", expand=True)
        self.output_scrollbar.pack(side="right", fill="y")

    def add_diary_entry(self) -> None:
        def action():
            self.state.require_world()
            dialog = DiaryEntryDialog(self, title_text="Add Diary Entry")
            self.wait_window(dialog)
            if dialog.result:
                self.state.add_diary_entry(
                    dialog.result["title"],
                    dialog.result["text"],
                )
                self.refresh_diary_view()
                self.status_var.set("Added diary entry.")

        self.guarded(action)

    def edit_diary_entry(self) -> None:
        def action():
            entry = self._selected_diary_entry()
            if entry is None:
                raise RuntimeError("Select a diary entry first.")
            dialog = DiaryEntryDialog(
                self,
                title_text="Edit Diary Entry",
                entry_title=entry.title,
                entry_text=entry.text,
                player_notes=entry.player_notes,
                protected=entry.protected,
            )
            self.wait_window(dialog)
            if dialog.result:
                self.state.update_diary_entry(
                    entry.entry_id,
                    title=dialog.result["title"],
                    text=dialog.result["text"],
                    player_notes=dialog.result["player_notes"],
                )
                self.refresh_diary_view()
                self.status_var.set("Updated diary entry.")

        self.guarded(action)

    def hide_diary_entry(self) -> None:
        def action():
            entry = self._selected_diary_entry()
            if entry is None:
                raise RuntimeError("Select a diary entry first.")
            self.state.hide_diary_entry(entry.entry_id)
            self.refresh_diary_view()
            self.status_var.set("Diary entry hidden.")

        self.guarded(action)

    def delete_diary_entry(self) -> None:
        def action():
            entry = self._selected_diary_entry()
            if entry is None:
                raise RuntimeError("Select a diary entry first.")
            self.state.delete_diary_entry(entry.entry_id)
            self.refresh_diary_view()
            self.status_var.set("Diary entry deleted.")

        self.guarded(action)

    def update_player_state(self) -> None:
        if self.state.world is None:
            self.player_state_var.set("No active world.")
            self.refresh_action_states()
            return
        player = self.state.world.player_state
        identity = (
            f"{player.character.name}, {player.character.character_class}, "
            f"age {player.character.age_years} ({age_band(player.character.age_years)})"
            if player.character
            else "No character created"
        )
        room = f" / room {player.current_room_id}" if player.current_room_id else ""
        light = (
            f"{player.light_turns_remaining} turns, {player.torches} torches"
            if player.light_turns_remaining
            else f"unlit, {player.torches} torches"
        )
        self.player_state_var.set(
            f"Character: {identity}\n"
            f"Seed: {self.state.active_seed or 'Random / not recorded'}\n"
            f"Calendar: {format_calendar(player.day, player.time_period)}    "
            f"Day {player.day}, {player.time_period}\n"
            f"Location: "
            f"{player.current_location}{room}    Wounds: {player.wounds}\n"
            f"Supplies: {player.supplies}    Food: {player.food}    Water: {player.water}    "
            f"Torches/Light: {light}    Coin: {player.coin}\n"
            f"Downtime: {DowntimeEngine.summarize(player.active_downtime_task)}\n"
            f"Bulk: {player.total_carried_bulk():g} total / {player.equipped_bulk():g} equipped    "
            f"Encumbrance: {player.encumbrance_state()}\n"
            f"Inventory: "
            f"{', '.join(inventory_item_text(item) for item in player.inventory) or 'empty'}\n"
            f"Known: {len(player.known_npc_ids)} NPCs, "
            f"{len(player.known_location_ids)} locations, "
            f"{len(player.known_rumor_indices)} rumors, "
            f"{len(player.discovered_room_ids)} rooms\n"
            f"Position: {player.position:+d}    Attention: {player.attention}    "
            f"Last consequence: {player.last_consequence or 'None'}"
        )
        self.refresh_action_states()
        if self.current_major_view == "diary":
            self.refresh_diary_view()

    def action_log_text(self) -> str:
        return export_event_log_text(self.state.require_world())

    def perform_action(self, action) -> None:
        def run():
            message = action()
            self.hide_index()
            self.update_player_state()
            self.show(self.action_log_text(), message)

        self.guarded(run)

    def encounter_choice(self, choice: str) -> None:
        self.perform_action(lambda: self.state.resolve_encounter(choice))

    def perform_check(self, action_key: str) -> None:
        def run():
            result = self.state.perform_check(
                action_key, self.check_difficulty_var.get()
            )
            self.hide_index()
            self.update_player_state()
            self.show(self.check_result_text(result), result.outcome.title())

        self.guarded(run)

    @staticmethod
    def check_result_text(result) -> str:
        return (
            f"{result.action_name.upper()}\n{'=' * len(result.action_name)}\n"
            f"Roll: {result.roll_result}\n"
            f"Bonus Used: {result.bonus_type.title()} {result.bonus_used:+d}\n"
            f"Total: {result.total}\n"
            f"Difficulty: {result.difficulty_name} (DC {result.difficulty_class})\n"
            f"Outcome: {result.outcome.title()}\n\n"
            f"NARRATIVE\n=========\n{result.narrative_result}\n\n"
            f"CONSEQUENCE\n===========\n{result.consequence}"
        )

    def move_room(self) -> None:
        def run():
            room = self.state.exploration().current_room()
            room_id = simpledialog.askinteger(
                "Move to Room",
                f"Current room: {room.room_id}\nAvailable exits: "
                f"{', '.join(map(str, room.exits))}\n\nMove to room:",
                parent=self,
                minvalue=1,
                maxvalue=len(self.state.require_world().dungeon.rooms),
            )
            if room_id is not None:
                message = self.state.move_room(room_id)
                self.hide_index()
                self.update_player_state()
                self.show(self.action_log_text(), message)

        self.guarded(run)

    def travel_to_location(self) -> None:
        def run():
            world = self.state.require_world()
            known = [
                location
                for location in world.settlement.important_locations
                if location.entity_id in world.player_state.known_location_ids
            ]
            if not known:
                raise RuntimeError("You have not discovered any town locations yet.")
            prompt = "\n".join(
                f"{index}. {location.name}" for index, location in enumerate(known, 1)
            )
            selection = simpledialog.askinteger(
                "Travel to Location",
                f"Known locations:\n{prompt}\n\nChoose a number:",
                parent=self,
                minvalue=1,
                maxvalue=len(known),
            )
            if selection is not None:
                message = self.state.travel_to_location(known[selection - 1].entity_id)
                self.hide_index()
                self.update_player_state()
                self.show(self.action_log_text(), message)

        self.guarded(run)

    def start_downtime(self) -> None:
        def run():
            tasks = self.state.available_downtime_tasks()
            if not tasks:
                raise RuntimeError("No downtime tasks are available from the current location.")
            prompt = "\n".join(
                f"{index}. {task['name']} ({task['default_duration_days']} days)"
                for index, task in enumerate(tasks, 1)
            )
            selection = simpledialog.askinteger(
                "Start Downtime",
                f"Available downtime tasks:\n{prompt}\n\nChoose a number:",
                parent=self,
                minvalue=1,
                maxvalue=len(tasks),
            )
            if selection is not None:
                message = self.state.start_downtime_task(tasks[selection - 1]["task_key"])
                self.hide_index()
                self.update_player_state()
                self.show(self.action_log_text(), message)

        self.guarded(run)

    def advance_downtime(self) -> None:
        def run():
            days = simpledialog.askinteger(
                "Advance Downtime",
                "Advance downtime by how many days?",
                parent=self,
                minvalue=1,
                maxvalue=30,
                initialvalue=1,
            )
            if days is not None:
                message = self.state.advance_downtime(days)
                self.hide_index()
                self.update_player_state()
                self.show(self.action_log_text(), message)

        self.guarded(run)

    def generate(self) -> None:
        def action():
            world = self.state.generate_new_region(self.seed_var.get())
            self.seed_var.set(world.generation_seed or "")
            self.hide_index()
            self.update_player_state()
            self.show(self.world_overview(), f"Generated {world.name}.")

        self.guarded(action)

    def create_character(self) -> None:
        def action():
            self.state.require_world()
            dialog = CharacterDialog(
                self,
                self.state.character_classes(),
                self.state.character_backgrounds(),
                self.state.random_full_name,
            )
            self.wait_window(dialog)
            if dialog.result:
                character = self.state.create_character(*dialog.result)
                self.update_player_state()
                self.show(
                    self.character_sheet_text(),
                    f"Created {character.name}, {character.character_class}.",
                )

        self.guarded(action)

    def character_sheet_text(self) -> str:
        return export_character_text(self.state.require_world())

    def view_character(self) -> None:
        self.guarded(
            lambda: self.show(self.character_sheet_text(), "Viewing character sheet.")
        )

    def view_equipment(self) -> None:
        def action():
            self.state.require_world()
            world = self.state.require_world()
            if world.player_state.character is None:
                raise RuntimeError("Create a character before managing equipment.")
            dialog = EquipmentDialog(self, self.state)
            self.wait_window(dialog)
            self.update_player_state()
            self.show(self.character_sheet_text(), "Viewed inventory and equipment.")

        self.guarded(action)

    def world_overview(self) -> str:
        world = self.state.require_world()
        settlement = world.settlement
        threats = ", ".join(world.player_state.known_threats) or "Unknown"
        return "\n\n".join(
            [
                f"{world.name.upper()}\n{'=' * len(world.name)}",
                f"Seed: {world.generation_seed or 'Random / not recorded'}",
                f"A {settlement.condition} {settlement.type} of {settlement.population} souls.",
                f"Known threats: {threats}",
                f"Lead: rumors point toward {world.dungeon.name}, but its truth is unknown.",
                f"Wilderness: {world.wilderness.name} — {world.wilderness.terrain_type}",
                f"Quest: {world.player_state.quest_log[0]}",
                "Use the buttons at left to inspect the generated region.",
            ]
        )

    def view_settlement(self) -> None:
        def action():
            self.hide_index()
            settlement = self.state.require_world().settlement
            data = asdict(settlement)
            text = block(
                "Settlement",
                data,
                {
                    "important_locations",
                    "rumors",
                    "local_secret",
                    "nearby_danger",
                    "problem_connection",
                    "problem_target_type",
                    "problem_target_id",
                },
            )
            known_rumors = [
                settlement.rumors[index]
                for index in self.state.require_world().player_state.known_rumor_indices
                if index < len(settlement.rumors)
            ]
            text += "\n\nKNOWN RUMOR LEADS\n=================\n" + (
                "\n".join(f"{i}. {rumor}" for i, rumor in enumerate(known_rumors, 1))
                or "No rumors learned yet. Talk to people and investigate."
            )
            text += "\n\nOPEN LEADS\n==========\n" + format_open_leads(
                self.state.require_world()
            )
            text += "\n\nSUGGESTED NEXT ACTIONS\n======================\n" + (
                format_suggested_next_actions(self.state.require_world())
            )
            self.show(text, f"Viewing {settlement.name}.")

        self.guarded(action)

    def view_npcs(self) -> None:
        def action():
            world = self.state.require_world()
            npcs = [
                npc for npc in world.npcs if npc.entity_id in world.player_state.known_npc_ids
            ]
            self.show_index(
                "NPCs",
                [f"{npc.name} — {npc.profession} [{npc.entity_id}]" for npc in npcs],
                self.view_npc_detail,
            )
            text = "NPC LIST\n========\n\n" + "\n".join(
                f"{index}. {npc.name} — {npc.profession} at {npc.location} [{npc.entity_id}]"
                for index, npc in enumerate(npcs, 1)
            )
            text += (
                "\n\nSelect a known NPC to inspect their details. "
                "Conversations and investigation reveal more people."
            )
            self.show(text, f"Viewing {len(npcs)} NPCs.")

        self.guarded(action)

    def view_npc_detail(self, index: int) -> None:
        world = self.state.require_world()
        known = [
            npc for npc in world.npcs if npc.entity_id in world.player_state.known_npc_ids
        ]
        npc = known[index]
        data = asdict(npc)
        data["secret"] = "Unknown — conversation and corroboration may reveal it."
        text = block(npc.name, data)
        if npc.prominent:
            text += (
                "\n\nPROMINENT NPC DETAILS\n=====================\n"
                f"Deeper Backstory: {npc.deeper_backstory or 'Not recorded'}\n"
                f"Personal Motive: {npc.personal_motive or 'Not recorded'}\n"
                f"Hidden Pressure: {npc.hidden_pressure or 'Not recorded'}\n"
                f"Relationship to Player: {npc.relationship_to_player or 'Not recorded'}\n"
                f"Ongoing Thread: {npc.ongoing_thread or 'Not recorded'}\n"
                f"Prominence Notes: {npc.prominence_notes or 'Not recorded'}\n"
                f"Recent Interaction Notes:\n"
                f"{chr(10).join(f'- {note}' for note in npc.recent_interaction_notes) or '- None'}"
            )
        if npc.is_key_npc:
            text += (
                "\n\nKEY NPC DETAILS\n===============\n"
                f"Faction Tag: {npc.faction_tag or 'unknown'}\n"
                f"Key Since: {npc.key_npc_since or 'Not recorded'}\n"
                f"Reason: {npc.key_npc_reason or 'Not recorded'}\n"
                f"Notes: {npc.key_npc_notes or 'Not recorded'}"
            )
        self.show(text, f"Viewing NPC: {npc.name}.")

    def view_locations(self) -> None:
        def action():
            world = self.state.require_world()
            locations = [
                location
                for location in world.settlement.important_locations
                if location.entity_id in world.player_state.known_location_ids
            ]
            self.show_index(
                "Locations",
                [
                    f"{location.name} — {location.type} [{location.entity_id}]"
                    for location in locations
                ],
                self.view_location_detail,
            )
            text = "LOCATION LIST\n=============\n\n" + "\n".join(
                f"{index}. {location.name} — {location.type}; "
                f"keeper: {location.owner_or_keeper} [{location.entity_id}]"
                for index, location in enumerate(locations, 1)
            )
            text += "\n\nSelect a location from the middle panel to inspect its people and secrets."
            self.show(text, f"Viewing {len(locations)} locations.")

        self.guarded(action)

    def view_location_detail(self, index: int) -> None:
        world = self.state.require_world()
        known = [
            location
            for location in world.settlement.important_locations
            if location.entity_id in world.player_state.known_location_ids
        ]
        location = known[index]
        data = asdict(location)
        data["hidden_detail"] = "Unknown — inspect this location during play."
        if not data["associated_npcs"]:
            data["associated_npcs"] = [
                npc.name for npc in world.npcs if npc.location == location.name
            ]
        self.show(block(location.name, data), f"Viewing location: {location.name}.")

    def view_dungeon(self) -> None:
        def action():
            self.hide_index()
            world = self.state.require_world()
            dungeon = world.dungeon
            if world.player_state.discovered_room_ids:
                text = block("Dungeon", asdict(dungeon), {"rooms"})
            else:
                text = (
                    f"DUNGEON LEAD\n============\nName: {dungeon.name}\n"
                    f"Entrance report: {dungeon.entrance_description}\n"
                    "Theme, threats, rooms, and treasure remain unknown."
                )
            self.show(text, f"Viewing {dungeon.name}.")

        self.guarded(action)

    def view_dungeon_rooms(self) -> None:
        def action():
            world = self.state.require_world()
            rooms = [
                room
                for room in world.dungeon.rooms
                if room.room_id in world.player_state.discovered_room_ids
            ]
            self.show_index(
                "Dungeon Rooms",
                [f"{room.room_id}. {room.name} [{room.entity_id}]" for room in rooms],
                self.view_room_detail,
            )
            text = "DUNGEON ROOMS\n=============\n\n" + "\n".join(
                f"{room.room_id}. {room.name} — exits to {', '.join(map(str, room.exits))} "
                f"[{room.entity_id}]"
                for room in rooms
            )
            text += "\n\nSelect a room to inspect dangers, clues, preparation, and retreat options."
            self.show(text, f"Viewing {len(rooms)} dungeon rooms.")

        self.guarded(action)

    def view_room_detail(self, index: int) -> None:
        world = self.state.require_world()
        rooms = [
            room
            for room in world.dungeon.rooms
            if room.room_id in world.player_state.discovered_room_ids
        ]
        room = rooms[index]
        self.show(
            block(f"Room {room.room_id}: {room.name}", asdict(room), {"room_id", "name"}),
            f"Viewing room {room.room_id}.",
        )

    def view_wilderness(self) -> None:
        def action():
            self.hide_index()
            area = self.state.require_world().wilderness
            text = block("Wilderness", asdict(area), {"encounter_table"})
            self.show(text, f"Viewing {area.name}.")

        self.guarded(action)

    def view_encounters(self) -> None:
        def action():
            world = self.state.require_world()
            encounters = [
                encounter
                for encounter in world.wilderness.encounter_table
                if encounter.creature_or_npc in world.player_state.known_threats
                or encounter.entity_id == world.player_state.pending_encounter_id
            ]
            self.show_index(
                "Encounters",
                [
                    f"{index}. {encounter.creature_or_npc} [{encounter.entity_id}]"
                    for index, encounter in enumerate(encounters, 1)
                ],
                self.view_encounter_detail,
            )
            text = "ENCOUNTER LIST\n==============\n\n" + "\n".join(
                f"{index}. {encounter.creature_or_npc} — "
                f"{encounter.encounter_type}, {encounter.danger_level}"
                for index, encounter in enumerate(encounters, 1)
            )
            text += "\n\nSelect an encounter to inspect warning signs and noncombat options."
            self.show(text, f"Viewing {len(encounters)} wilderness encounters.")

        self.guarded(action)

    def view_encounter_detail(self, index: int) -> None:
        world = self.state.require_world()
        encounters = [
            encounter
            for encounter in world.wilderness.encounter_table
            if encounter.creature_or_npc in world.player_state.known_threats
            or encounter.entity_id == world.player_state.pending_encounter_id
        ]
        encounter = encounters[index]
        self.show(
            block(f"Encounter {index + 1}", asdict(encounter)),
            f"Viewing encounter {index + 1}.",
        )

    def view_hook(self) -> None:
        def action():
            self.hide_index()
            self.show(
                block("Adventure Hook", asdict(self.state.require_world().adventure_hook)),
                "Viewing the starting adventure hook.",
            )

        self.guarded(action)

    def view_event_log(self) -> None:
        self.guarded(
            lambda: self.show(self.action_log_text(), "Viewing the persistent event log.")
        )

    def view_world_recap(self) -> None:
        self.hide_index()
        self.show(format_world_recap(self.state.world), "Viewing the journal and world recap.")

    def follow_open_lead(self) -> None:
        def action():
            leads = self.state.open_leads()
            if not leads:
                messagebox.showinfo(
                    "Follow Open Lead",
                    "There are no open leads to follow right now.",
                    parent=self,
                )
                return
            selection = 1
            if len(leads) > 1:
                prompt = "\n".join(
                    f"{index}. {lead.suggested_action or lead.text}"
                    for index, lead in enumerate(leads, 1)
                )
                chosen = simpledialog.askinteger(
                    "Follow Open Lead",
                    "Choose an open lead to follow:\n\n" + prompt,
                    parent=self,
                    minvalue=1,
                    maxvalue=len(leads),
                )
                if chosen is None:
                    return
                selection = chosen
            result = self.state.follow_open_lead(selection - 1)
            self.show(result, "Followed an open lead.")
            self.refresh()

        self.guarded(action)

    def view_timeline_summary(self) -> None:
        self.guarded(
            lambda: self.show(
                format_summary_timeline(self.state.require_world()),
                "Viewing the journal summary.",
            )
        )

    def view_verbose_timeline(self) -> None:
        self.guarded(
            lambda: self.show(
                format_verbose_timeline(self.state.require_world()),
                "Viewing the verbose timeline.",
            )
        )

    def _default_export_name(self, stem: str) -> str:
        safe = "".join(
            character if character.isalnum() or character in (" ", "-", "_") else "_"
            for character in stem.strip()
        ).strip()
        return safe or "export"

    def _write_export(self, title: str, text: str, stem: str) -> bool:
        path = filedialog.asksaveasfilename(
            parent=self,
            title=title,
            defaultextension=".txt",
            initialfile=f"{self._default_export_name(stem)}.txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
        )
        if not path:
            self.status_var.set(f"{title} cancelled.")
            return False
        Path(path).write_text(text, encoding="utf-8")
        self.status_var.set(f"Exported to {path}.")
        return True

    def export_world(self) -> None:
        if self.state.world is None:
            messagebox.showinfo(
                "Export World",
                "Generate or load a world first.",
                parent=self,
            )
            return
        world = self.state.world
        self.guarded(
            lambda: self._write_export(
                "Export World",
                export_world_summary(world),
                f"{world.name} world summary",
            )
        )

    def export_character(self) -> None:
        if self.state.world is None:
            messagebox.showinfo(
                "Export Character",
                "Generate or load a world first.",
                parent=self,
            )
            return
        player = self.state.world.player_state
        if player.character is None:
            messagebox.showinfo(
                "Export Character",
                "Create a character first.",
                parent=self,
            )
            return
        self.guarded(
            lambda: self._write_export(
                "Export Character",
                export_character_text(self.state.world),
                f"{player.character.name} character sheet",
            )
        )

    def export_event_log(self) -> None:
        if self.state.world is None:
            messagebox.showinfo(
                "Export Event Log",
                "Generate or load a world first.",
                parent=self,
            )
            return
        world = self.state.world
        self.guarded(
            lambda: self._write_export(
                "Export Event Log",
                export_event_log_text(world),
                f"{world.name} event log",
            )
        )

    def view_data_diagnostics(self) -> None:
        """Expose startup data problems without interrupting normal generation."""
        reports = [
            self.state.tables.validation_report(),
            "",
            "NAME DATA",
            "=========",
            self.state.name_generator.source_summary(),
        ]
        if self.state.name_generator.warnings:
            reports.extend(
                ["", *[f"- {warning}" for warning in self.state.name_generator.warnings]]
            )
        else:
            reports.extend(["", "No name-data warnings."])
        self.hide_index()
        self.show("\n".join(reports), "Viewing generation data diagnostics.")

    def view_monster_import_review(self) -> None:
        """Display an editable review surface for canonical-group candidates.

        Decisions are stored separately in data/import_reviews/ and do not merge
        source records or modify the live catalog.
        """
        try:
            payload = load_canonical_group_report()
        except FileNotFoundError as exc:
            self.hide_index()
            self.show(str(exc), "Canonical-group report not found.")
            return
        except ValueError as exc:
            self.hide_index()
            self.show(str(exc), "Canonical-group report is malformed.")
            return

        try:
            decisions = load_decisions()
        except ValueError as exc:
            self.hide_index()
            self.show(str(exc), "Decision file is malformed.")
            return

        rows = build_candidate_rows(payload, decisions)
        if not rows:
            self.hide_index()
            self.show(
                review_summary_text(payload) + "\n\nNo candidate groups found.",
                "No canonical-group candidates.",
            )
            return

        labels = [label for label, _group in rows]
        groups = [group for _label, group in rows]

        def refresh_labels() -> None:
            self.index_list.delete(0, "end")
            for label, _group in build_candidate_rows(payload, decisions):
                self.index_list.insert("end", label)

        def show_detail(index: int) -> None:
            group = groups[index]
            group_id = group.get("candidate_group_id", "")
            self.open_candidate_review_dialog(group, decisions, refresh_labels)

        self.show_index("Candidate Groups", labels, show_detail)
        self.show(review_summary_text(payload), "Viewing monster import canonical-group review.")

    def open_candidate_review_dialog(
        self,
        group: dict[str, Any],
        decisions: dict[str, Any],
        refresh_callback: Callable[[], None] | None = None,
    ) -> None:
        """Open a read-only detail + editable decision dialog for one candidate group."""
        dialog = tk.Toplevel(self)
        dialog.title(f"Review: {group.get('proposed_canonical_name', 'Candidate Group')}")
        dialog.geometry("640x720")
        dialog.transient(self)
        dialog.grab_set()

        group_id = group.get("candidate_group_id", "")
        current = get_decision(decisions, group_id)

        detail = tk.Text(dialog, wrap="word", font=("Consolas", 10), padx=12, pady=12)
        detail.pack(side="top", fill="both", expand=True)
        detail.insert("1.0", format_candidate_group(group))
        detail.insert("end", "\n\n" + format_decision_block(current))
        detail.configure(state="disabled")

        controls = ttk.Frame(dialog, padding=12)
        controls.pack(side="top", fill="x")

        ttk.Label(controls, text="Decision:").grid(row=0, column=0, sticky="w")
        decision_var = tk.StringVar(value=current.get("decision", "needs_review"))
        decision_box = ttk.Combobox(
            controls,
            textvariable=decision_var,
            values=["approved", "rejected", "needs_review"],
            state="readonly",
            width=18,
        )
        decision_box.grid(row=0, column=1, sticky="w", padx=(6, 0))

        ttk.Label(controls, text="Notes:").grid(row=1, column=0, sticky="nw", pady=(8, 0))
        notes_var = tk.StringVar(value=current.get("notes", ""))
        notes_entry = ttk.Entry(controls, textvariable=notes_var, width=60)
        notes_entry.grid(row=1, column=1, sticky="ew", padx=(6, 0), pady=(8, 0))
        controls.columnconfigure(1, weight=1)

        warning = ttk.Label(
            dialog,
            text="Decisions are stored separately. No records are merged yet.",
            foreground="red",
            wraplength=560,
            justify="left",
            padding=(12, 6),
        )
        warning.pack(side="top", fill="x")

        buttons = ttk.Frame(dialog, padding=(12, 0, 12, 12))
        buttons.pack(side="top", fill="x")

        def save() -> None:
            try:
                set_decision(
                    decisions,
                    group_id,
                    decision_var.get(),
                    notes_var.get(),
                )
                save_decisions(decisions)
            except ValueError as exc:
                messagebox.showerror("Invalid Decision", str(exc), parent=dialog)
                return
            if refresh_callback:
                refresh_callback()
            self.status_var.set(f"Saved decision for {group_id}.")
            dialog.destroy()

        ttk.Button(buttons, text="Save Decision", command=save).pack(side="right")
        ttk.Button(buttons, text="Close", command=dialog.destroy).pack(side="right", padx=(0, 8))

    def view_editors(self) -> None:
        """Display the Editors hub with entry points for import/review tools."""
        editor_categories = get_editor_categories()
        labels = [label for label, _key in editor_categories]
        keys = [key for _label, key in editor_categories]

        def show_editor_detail(index: int) -> None:
            key = keys[index]
            if key == "monsters":
                self.view_monster_import_review()
                return
            self.show(
                get_editor_placeholder_text(key),
                f"{labels[index]} is not implemented yet.",
            )

        self.show_index("Editors", labels, show_editor_detail)
        self.show(editors_hub_summary_text(), "Viewing Editors hub.")

    def save_world(self) -> None:
        def action():
            world = self.state.require_world()
            save_name = simpledialog.askstring(
                "Save World", "Save name:", initialvalue=world.name, parent=self
            )
            if save_name:
                world_id = self.state.save_world(save_name)
                self.status_var.set(f"Saved '{save_name}' as world #{world_id}.")

        self.guarded(action)

    def load_world(self) -> None:
        def action():
            worlds = self.state.list_worlds()
            if not worlds:
                messagebox.showinfo("Load World", "There are no saved worlds yet.", parent=self)
                return
            dialog = LoadDialog(self, worlds)
            self.wait_window(dialog)
            if dialog.selected_id is not None:
                world = self.state.load_world(dialog.selected_id)
                self.seed_var.set(world.generation_seed or "")
                self.hide_index()
                self.update_player_state()
                self.show(self.world_overview(), f"Loaded {world.name}.")

        self.guarded(action)

    def clear_output(self) -> None:
        self.hide_index()
        self.output.delete("1.0", "end")
        self.status_var.set("Output cleared.")

    def on_close(self) -> None:
        self.state.close()
        self.destroy()
