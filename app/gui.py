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


class RPGWorldApp(tk.Tk):
    def __init__(self, state: GameState):
        super().__init__()
        self.state = state
        self.title("RPG World App — Weird Fantasy Region Generator")
        self.geometry("1100x720")
        self.minsize(800, 520)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.status_var = tk.StringVar(value="Ready. Generate a region to begin.")
        self.selection_handler = None
        self._build()
        if self.state.tables.warnings:
            self.status_var.set(f"Loaded with {len(self.state.tables.warnings)} table warning(s).")

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
        actions = [
            ("Generate New Region", self.generate),
            ("Settlement Overview", self.view_settlement),
            ("NPC List", self.view_npcs),
            ("Location List", self.view_locations),
            ("Dungeon Overview", self.view_dungeon),
            ("Dungeon Rooms", self.view_dungeon_rooms),
            ("Wilderness Overview", self.view_wilderness),
            ("Encounter List", self.view_encounters),
            ("Adventure Hook", self.view_hook),
            ("Save World", self.save_world),
            ("Load World", self.load_world),
            ("Clear Output", self.clear_output),
        ]
        for text, command in actions:
            ttk.Button(sidebar, text=text, command=command, width=24).pack(fill="x", pady=3)
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

    def generate(self) -> None:
        def action():
            world = self.state.generate_new_region()
            self.hide_index()
            self.show(self.world_overview(), f"Generated {world.name}.")

        self.guarded(action)

    def world_overview(self) -> str:
        world = self.state.require_world()
        settlement = world.settlement
        return "\n\n".join(
            [
                f"{world.name.upper()}\n{'=' * len(world.name)}",
                f"A {settlement.condition} {settlement.type} of {settlement.population} souls.",
                f"Local threat: {world.local_threat}",
                f"Nearby dungeon: {world.dungeon.name} ({world.dungeon.danger_level})",
                f"Wilderness: {world.wilderness.name} — {world.wilderness.terrain_type}",
                f"Adventure: {world.adventure_hook.major_goal}",
                "Use the buttons at left to inspect the generated region.",
            ]
        )

    def view_settlement(self) -> None:
        def action():
            self.hide_index()
            settlement = self.state.require_world().settlement
            data = asdict(settlement)
            text = block("Settlement", data, {"important_locations", "rumors"})
            text += "\n\nRUMORS\n======\n" + "\n".join(
                f"{i}. {rumor}" for i, rumor in enumerate(settlement.rumors, 1)
            )
            self.show(text, f"Viewing {settlement.name}.")

        self.guarded(action)

    def view_npcs(self) -> None:
        def action():
            npcs = self.state.require_world().npcs
            self.show_index(
                "NPCs",
                [f"{npc.name} — {npc.profession} [{npc.entity_id}]" for npc in npcs],
                self.view_npc_detail,
            )
            text = "NPC LIST\n========\n\n" + "\n".join(
                f"{index}. {npc.name} — {npc.profession} at {npc.location} [{npc.entity_id}]"
                for index, npc in enumerate(npcs, 1)
            )
            text += "\n\nSelect an NPC from the middle panel to inspect their full details."
            self.show(text, f"Viewing {len(npcs)} NPCs.")

        self.guarded(action)

    def view_npc_detail(self, index: int) -> None:
        npc = self.state.require_world().npcs[index]
        self.show(block(npc.name, asdict(npc)), f"Viewing NPC: {npc.name}.")

    def view_locations(self) -> None:
        def action():
            locations = self.state.require_world().settlement.important_locations
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
        location = world.settlement.important_locations[index]
        data = asdict(location)
        if not data["associated_npcs"]:
            data["associated_npcs"] = [
                npc.name for npc in world.npcs if npc.location == location.name
            ]
        self.show(block(location.name, data), f"Viewing location: {location.name}.")

    def view_dungeon(self) -> None:
        def action():
            self.hide_index()
            dungeon = self.state.require_world().dungeon
            text = block("Dungeon", asdict(dungeon), {"rooms"})
            self.show(text, f"Viewing {dungeon.name}.")

        self.guarded(action)

    def view_dungeon_rooms(self) -> None:
        def action():
            rooms = self.state.require_world().dungeon.rooms
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
        room = self.state.require_world().dungeon.rooms[index]
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
            encounters = self.state.require_world().wilderness.encounter_table
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
        encounter = self.state.require_world().wilderness.encounter_table[index]
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
                self.show(self.world_overview(), f"Loaded {world.name}.")

        self.guarded(action)

    def clear_output(self) -> None:
        self.hide_index()
        self.output.delete("1.0", "end")
        self.status_var.set("Output cleared.")

    def on_close(self) -> None:
        self.state.close()
        self.destroy()
