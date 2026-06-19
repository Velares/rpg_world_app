# RPG World App

Version 0.3 is a local, single-player weird-fantasy starting-region generator
with a basic playable exploration loop.
It creates a settlement, its people and locations, a connected cave dungeon,
a wilderness encounter table, and a linked adventure hook. Combat information
emphasizes warning signs, avoidance, negotiation, preparation, morale, and
retreat.

## Requirements

- Python 3.11 or a compatible Python 3 release
- Tkinter (included with standard Windows Python installations)
- No third-party packages and no network connection

## Run

From the `rpg_world_app` directory:

```powershell
python main.py
```

Click **Generate New Region**, then use the viewing buttons to inspect the
region. **Save World** writes the active world to SQLite. **Load World** opens a
list of prior saves.

Version 0.2 adds explicit links among town problems, NPCs, locations, rumors,
the dungeon, wilderness signs, and the adventure hook. NPCs, locations, dungeon
rooms, and encounters have selectable list-and-detail views in the GUI.
Generated NPCs, locations, rooms, encounters, and adventure hooks also receive
stable prefixed IDs. These ID-backed relationships survive save/load, while
older saves are upgraded in memory when opened.

Version 0.3 adds travel among town, wilderness, and dungeon; room movement;
searching, conversation, rest, and retreat; wilderness warning signs with
avoid/approach/investigate choices; dungeon light consumption; wounds and
resource pressure; and a persistent action log. Combat remains abstract and
danger can usually be scouted, negotiated with, avoided, or escaped.

The expanded Version 0.3 loop tracks days across Morning, Afternoon, Evening,
and Night. Generated people, locations, rumors, threats, and dungeon rooms begin
partially hidden and enter the journal through conversations, inspection,
searching, and exploration. Rumors create leads rather than revealing complete
answers. The persistent event log records travel, discoveries, conversations,
encounters, and rests. Food, water, torches, supplies, wounds, and coin are
saved with the world.

The database is created automatically at:

```text
data/saves/worlds.db
```

Deleting that file removes all saves. The application will create a fresh
database on its next launch.

## Project layout

- `main.py`: application entry point
- `app/gui.py`: Tkinter interface and text rendering
- `app/game_state.py`: active-world coordination
- `app/models.py`: dataclass domain models
- `app/database.py`: SQLite schema and persistence
- `app/table_loader.py`: JSON loading, validation, and fallbacks
- `app/dice.py`: dice formulas, reaction rolls, and morale checks
- `app/generators/`: focused procedural generators
- `data/tables/`: editable generation content
- `data/saves/`: local SQLite saves
- `tests/`: standard-library unit tests

## Editing generation tables

Each file in `data/tables` is a JSON object whose category values are non-empty
lists. Add, remove, or rewrite list entries to change generated content without
changing Python code. Files are loaded when the app starts.

Simple lists choose entries uniformly. The loader also accepts weighted entries:

```json
[
  {"value": "common result", "weight": 4},
  {"value": "rare result", "weight": 1}
]
```

Missing files, malformed JSON, empty categories, and missing category names are
reported as warnings. A minimal fallback result prevents a missing optional
table from crashing generation.

## Tests

From the project directory:

```powershell
python -m unittest discover -s tests -v
```

Tests cover dice formulas, JSON validity, generated counts and references,
dungeon connectivity, SQLite child records, save/load reconstruction, and
missing-table fallback behavior.

## Version 0.3 boundaries

This release has a lightweight exploration game loop, but not tactical combat.
Visual maps, character creation, detailed combat resolution, deterministic seed
controls, multiplayer, and web/server features are intentionally deferred.

The domain and persistence layers do not depend on Tkinter, which keeps later
migration to a web or server interface practical.
