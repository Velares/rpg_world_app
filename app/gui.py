from __future__ import annotations

import tkinter as tk
from dataclasses import asdict
from tkinter import messagebox, simpledialog, ttk

from app.game_state import GameState


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


def inventory_item_text(item, detailed: bool = False) -> str:
    flags = []
    if item.equipped:
        flags.append("equipped")
    if item.consumable:
        flags.append("consumable")
    if item.quest_related:
        flags.append("quest")
    if not item.carried:
        flags.append("stored")
    suffix = f" [{', '.join(flags)}]" if flags else ""
    base = f"{item.name} x{item.quantity} ({item.category}){suffix}"
    if detailed and item.description:
        return f"{base} - {item.description}"
    return base


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
        self.selection_handler = None
        self._build()
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
        navigation_actions = [
            ("Generate New Region", self.generate),
            ("Create Character", self.create_character),
            ("Character Sheet", self.view_character),
            ("Settlement Overview", self.view_settlement),
            ("NPC List", self.view_npcs),
            ("Location List", self.view_locations),
            ("Dungeon Overview", self.view_dungeon),
            ("Dungeon Rooms", self.view_dungeon_rooms),
            ("Wilderness Overview", self.view_wilderness),
            ("Encounter List", self.view_encounters),
            ("Adventure Hook", self.view_hook),
            ("Event Log", self.view_event_log),
            ("Data Diagnostics", self.view_data_diagnostics),
            ("Save World", self.save_world),
            ("Load World", self.load_world),
            ("Clear Output", self.clear_output),
        ]
        for text, command in navigation_actions:
            ttk.Button(sidebar, text=text, command=command, width=24).pack(fill="x", pady=2)

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
        action_box = ttk.LabelFrame(self.display_frame, text="Exploration Actions", padding=5)
        action_box.pack(fill="x", pady=(0, 7))
        gameplay_actions = [
            ("Return to Town", lambda: self.perform_action(lambda: self.state.travel("town"))),
            ("Travel to Location", self.travel_to_location),
            (
                "Travel to Wilderness",
                lambda: self.perform_action(lambda: self.state.travel("wilderness")),
            ),
            (
                "Travel to Dungeon",
                lambda: self.perform_action(lambda: self.state.travel("dungeon_entrance")),
            ),
            ("Explore Current Area", lambda: self.perform_action(self.state.explore_current_area)),
            ("Search", lambda: self.perform_action(self.state.search)),
            ("Inspect Location", lambda: self.perform_action(self.state.inspect_location)),
            ("Talk to NPC", lambda: self.perform_action(self.state.talk_to_npc)),
            ("Move to Room", self.move_room),
            ("Inspect Room", lambda: self.perform_action(self.state.inspect_room)),
            ("Short Rest", lambda: self.perform_action(self.state.rest)),
            ("Full Rest", lambda: self.perform_action(self.state.full_rest)),
            ("Retreat", lambda: self.perform_action(self.state.retreat)),
            ("Avoid Encounter", lambda: self.encounter_choice("avoid")),
            ("Approach Encounter", lambda: self.encounter_choice("approach")),
            ("Investigate Signs", lambda: self.encounter_choice("investigate")),
            ("Retreat from Encounter", lambda: self.encounter_choice("retreat")),
        ]
        for index, (text, command) in enumerate(gameplay_actions):
            row, column = divmod(index, 4)
            ttk.Button(action_box, text=text, command=command).grid(
                row=row, column=column, sticky="ew", padx=2, pady=2
            )
        for column in range(4):
            action_box.columnconfigure(column, weight=1)

        check_box = ttk.LabelFrame(self.display_frame, text="Action Checks", padding=5)
        check_box.pack(fill="x", pady=(0, 7))
        ttk.Label(check_box, text="Difficulty").grid(row=0, column=0, padx=2, pady=2)
        ttk.Combobox(
            check_box,
            textvariable=self.check_difficulty_var,
            values=["Easy", "Standard", "Hard", "Severe"],
            state="readonly",
            width=10,
        ).grid(row=0, column=1, sticky="ew", padx=2, pady=2)
        check_actions = [
            ("Search Area", "search_area"),
            ("Sneak Past Danger", "sneak_past_danger"),
            ("Read Markings", "read_ancient_markings"),
            ("Negotiate", "negotiate_with_npc"),
            ("Track Creature", "track_creature"),
            ("Force Action", "force_dangerous_action"),
        ]
        for index, (text, action_key) in enumerate(check_actions, start=2):
            ttk.Button(
                check_box,
                text=text,
                command=lambda key=action_key: self.perform_check(key),
            ).grid(row=0, column=index, sticky="ew", padx=2, pady=2)
        for column in range(8):
            check_box.columnconfigure(column, weight=1)
        self.output = tk.Text(
            self.display_frame,
            wrap="word",
            font=("Consolas", 10),
            padx=12,
            pady=12,
            undo=False,
        )
        scrollbar = ttk.Scrollbar(self.display_frame, orient="vertical", command=self.output.yview)
        self.output.configure(yscrollcommand=scrollbar.set)
        self.output.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        ttk.Label(self, textvariable=self.status_var, anchor="w", padding=(10, 5)).pack(
            fill="x", side="bottom"
        )

    def show(self, text: str, status: str = "Ready.") -> None:
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

    def update_player_state(self) -> None:
        if self.state.world is None:
            self.player_state_var.set("No active world.")
            return
        player = self.state.world.player_state
        identity = (
            f"{player.character.name}, {player.character.character_class}"
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
            f"Character: {identity}    Day {player.day}, {player.time_period}\n"
            f"Location: "
            f"{player.current_location}{room}    Wounds: {player.wounds}\n"
            f"Supplies: {player.supplies}    Food: {player.food}    Water: {player.water}    "
            f"Torches/Light: {light}    Coin: {player.coin}\n"
            f"Inventory: "
            f"{', '.join(inventory_item_text(item) for item in player.inventory) or 'empty'}\n"
            f"Known: {len(player.known_npc_ids)} NPCs, "
            f"{len(player.known_location_ids)} locations, "
            f"{len(player.known_rumor_indices)} rumors, "
            f"{len(player.discovered_room_ids)} rooms\n"
            f"Position: {player.position:+d}    Attention: {player.attention}    "
            f"Last consequence: {player.last_consequence or 'None'}"
        )

    def action_log_text(self) -> str:
        world = self.state.require_world()
        lines = ["EVENT LOG", "=========", ""]
        lines.extend(
            f"{index}. {entry}" for index, entry in enumerate(world.player_state.event_log, 1)
        )
        if world.player_state.pending_encounter_id:
            lines.extend(
                [
                    "",
                    "DANGER IS PENDING",
                    "Use Avoid, Approach, Investigate, or Retreat from Encounter.",
                ]
            )
        return "\n".join(lines)

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

    def generate(self) -> None:
        def action():
            world = self.state.generate_new_region()
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
        player = self.state.require_world().player_state
        character = player.character
        if character is None:
            return (
                "NO PLAYER CHARACTER\n"
                "===================\n"
                "Use Create Character to choose a name, class, and background."
            )
        bonuses = "\n".join(
            f"{name.title()}: {value:+d}" for name, value in character.bonuses.items()
        )
        inventory = "\n".join(
            f"- {inventory_item_text(item, detailed=True)}"
            for item in player.inventory
        ) or "- Empty"
        return (
            f"{character.name.upper()}\n{'=' * len(character.name)}\n"
            f"Class: {character.character_class}\n"
            f"Background: {character.background}\n"
            f"Role: {character.role_description}\n"
            f"Starting Supplies: {character.starting_supplies}\n\n"
            f"BACKGROUND DETAILS\n==================\n"
            f"Origin: {character.origin_detail or 'Not recorded'}\n"
            f"Formative Event: {character.formative_event or 'Not recorded'}\n"
            f"Personality: {character.personality_trait or 'Not recorded'}\n"
            f"Ideal: {character.ideal or 'Not recorded'}\n"
            f"Bond: {character.bond or 'Not recorded'}\n"
            f"Flaw: {character.flaw or 'Not recorded'}\n\n"
            f"EQUIPMENT AND INVENTORY\n=======================\n{inventory}\n\n"
            f"Resource counters remain separate: supplies {player.supplies}, "
            f"food {player.food}, water {player.water}, torches {player.torches}, "
            f"coin {player.coin}.\n\n"
            f"BONUSES\n=======\n{bonuses}\n\n"
            f"SPECIAL ABILITY PLACEHOLDER\n===========================\n"
            f"{character.special_ability_placeholder}"
        )

    def view_character(self) -> None:
        self.guarded(
            lambda: self.show(self.character_sheet_text(), "Viewing character sheet.")
        )

    def world_overview(self) -> str:
        world = self.state.require_world()
        settlement = world.settlement
        threats = ", ".join(world.player_state.known_threats) or "Unknown"
        return "\n\n".join(
            [
                f"{world.name.upper()}\n{'=' * len(world.name)}",
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
            text += "\n\nACTIVE LEADS\n============\n" + (
                "\n".join(f"- {lead}" for lead in self.state.require_world().player_state.leads)
                or "No active leads."
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
        self.show(block(npc.name, data), f"Viewing NPC: {npc.name}.")

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
