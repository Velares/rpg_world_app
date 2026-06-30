from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.models import World


class Database:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.connection = sqlite3.connect(self.path)
        except sqlite3.Error as exc:
            raise RuntimeError(
                f"Could not open database at {self.path}: {exc}"
            ) from exc
        self.connection.row_factory = sqlite3.Row
        self.initialize_schema()

    def initialize_schema(self) -> None:
        self.connection.executescript(
            """
            PRAGMA foreign_keys = ON;
            CREATE TABLE IF NOT EXISTS worlds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                data_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS settlements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                world_id INTEGER NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                data_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS npcs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                world_id INTEGER NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                location TEXT,
                data_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                world_id INTEGER NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                type TEXT,
                data_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS dungeons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                world_id INTEGER NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                data_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS dungeon_rooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                world_id INTEGER NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
                dungeon_name TEXT NOT NULL,
                room_id INTEGER NOT NULL,
                data_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS wilderness_areas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                world_id INTEGER NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                data_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS encounters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                world_id INTEGER NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
                encounter_type TEXT NOT NULL,
                data_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS adventure_hooks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                world_id INTEGER NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
                major_goal TEXT NOT NULL,
                data_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS player_state (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                world_id INTEGER NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,
                data_json TEXT NOT NULL
            );
            """
        )
        self.connection.commit()

    @staticmethod
    def _json(data) -> str:
        return json.dumps(data, ensure_ascii=False, sort_keys=True)

    def save_world(self, world: World, save_name: str) -> int:
        data = world.to_dict()
        data["name"] = save_name.strip() or world.name
        data["world_id"] = None
        with self.connection:
            cursor = self.connection.execute(
                "INSERT INTO worlds (name, created_at, data_json) VALUES (?, ?, ?)",
                (data["name"], world.created_at, self._json(data)),
            )
            world_id = int(cursor.lastrowid)
            settlement = data["settlement"]
            self.connection.execute(
                "INSERT INTO settlements (world_id, name, data_json) VALUES (?, ?, ?)",
                (world_id, settlement["name"], self._json(settlement)),
            )
            for npc in data["npcs"]:
                self.connection.execute(
                    "INSERT INTO npcs (world_id, name, location, data_json) VALUES (?, ?, ?, ?)",
                    (world_id, npc["name"], npc["location"], self._json(npc)),
                )
            for location in settlement["important_locations"]:
                self.connection.execute(
                    "INSERT INTO locations (world_id, name, type, data_json) VALUES (?, ?, ?, ?)",
                    (world_id, location["name"], location["type"], self._json(location)),
                )
            dungeon = data["dungeon"]
            self.connection.execute(
                "INSERT INTO dungeons (world_id, name, data_json) VALUES (?, ?, ?)",
                (world_id, dungeon["name"], self._json(dungeon)),
            )
            for room in dungeon["rooms"]:
                self.connection.execute(
                    "INSERT INTO dungeon_rooms (world_id, dungeon_name, room_id, data_json) VALUES (?, ?, ?, ?)",
                    (world_id, dungeon["name"], room["room_id"], self._json(room)),
                )
            wilderness = data["wilderness"]
            self.connection.execute(
                "INSERT INTO wilderness_areas (world_id, name, data_json) VALUES (?, ?, ?)",
                (world_id, wilderness["name"], self._json(wilderness)),
            )
            for encounter in wilderness["encounter_table"]:
                self.connection.execute(
                    "INSERT INTO encounters (world_id, encounter_type, data_json) VALUES (?, ?, ?)",
                    (world_id, encounter["encounter_type"], self._json(encounter)),
                )
            hook = data["adventure_hook"]
            self.connection.execute(
                "INSERT INTO adventure_hooks (world_id, major_goal, data_json) VALUES (?, ?, ?)",
                (world_id, hook["major_goal"], self._json(hook)),
            )
            self.connection.execute(
                "INSERT INTO player_state (world_id, data_json) VALUES (?, ?)",
                (world_id, self._json(data["player_state"])),
            )
        world.world_id = world_id
        world.name = data["name"]
        return world_id

    def list_worlds(self) -> list[tuple[int, str, str]]:
        rows = self.connection.execute(
            "SELECT id, name, created_at FROM worlds ORDER BY id DESC"
        ).fetchall()
        return [(row["id"], row["name"], row["created_at"]) for row in rows]

    def load_world(self, world_id: int) -> World:
        row = self.connection.execute(
            "SELECT data_json FROM worlds WHERE id = ?", (world_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"No saved world with id {world_id}")
        try:
            data = json.loads(row["data_json"])
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Save data for world {world_id} is corrupt: {exc}"
            ) from exc
        data["world_id"] = world_id
        return World.from_dict(data)

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> "Database":
        return self

    def __exit__(self, *_args) -> None:
        self.close()
