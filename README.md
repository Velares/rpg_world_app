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

A lightweight, rules-neutral character scaffold supports name, class,
background, starting resources, and bonuses for combat, exploration, social,
lore, survival, and stealth. The ten starter classes live in the editable
`data/tables/class_tables.json` file. Special abilities remain placeholders so
the eventual rules implementation can be SRD-friendly or replaced entirely.

Version 0.5 adds a generic `1d20 + bonus vs difficulty` action resolver. Easy,
Standard, Hard, and Severe checks use the character's combat, exploration,
social, lore, survival, or stealth bonus. Outcomes range from critical failure
to critical success and can cost time or supplies, inflict wounds, attract
attention, reveal clues, or alter the character's position. This is still an
exploration framework rather than a full combat ruleset.

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
- `app/characters.py`: rules-light class loading and character creation
- `app/checks.py`: generic d20 checks, outcomes, and state consequences
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

## Large name files

Place newline-delimited raw personal names in:

```text
data/names/raw_first_names.txt
data/names/raw_last_names.txt
```

Clean them from the project directory with:

```powershell
python tools/clean_names.py
```

The tool trims blank lines and whitespace, applies title case, removes
duplicates, sorts the results, and writes:

```text
data/names/first_names.txt
data/names/last_names.txt
```

The cleaned text files are loaded once when the app starts and used for NPC
names and the **Random Name** button in character creation. If either cleaned
file is missing or empty, the smaller editable JSON name tables remain as safe
fallbacks. Name text files are ignored by Git so very large local datasets are
not accidentally committed.

If the source data contains replacement characters or obvious mojibake, scrub
the cleaned files in place with:

```powershell
python tools/scrub_names.py
```

The scrubber preserves normal accented Unicode names, removes suspicious
corrupted lines, safely replaces each cleaned file through a temporary file,
and reports how many names were kept and removed. Raw source files are not
modified.

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
