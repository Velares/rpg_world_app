# RPG World App — Project Status

## Current version

- Current tag: `v0.7.3`
- Current development version on `main`: `v0.7.4`
- Current branch at this update: `main`
- Runtime: Python 3.11-compatible standard library, Tkinter, and SQLite

## Latest completed work

Version 0.7.4 adds plain-text export and table-flexibility improvements:

- Added focused plain-text export formatting for active world summaries,
  character sheets, and event logs.
- Added simple Tkinter export actions for world, character, and event-log
  `.txt` output.
- Confirmed editable JSON generation tables are not fixed `d30` tables and may
  contain any practical non-empty number of entries.
- Centralized weighted-entry handling through the standard table chooser used
  by generators.
- Kept inventory exports descriptive while preserving food, water, torches,
  coin, and supplies as separate counters.
- Preserved save/load compatibility by avoiding schema changes.

Version 0.7.3 adds a lightweight structured inventory:

- Item records track category, quantity, description, tags, and rules-neutral
  equipped/carried/consumable/quest/tradeable flags.
- Common and class-flavored starting gear comes from
  `data/tables/item_tables.json`.
- Legacy string inventories and saves without inventory data migrate safely.
- Food, water, torches, coin, and supplies remain authoritative counters rather
  than duplicated inventory quantities.

Version 0.7.2 adds the coordinated AI agent workflow documented in `AGENTS.md`
and `README.md`. Named roles cover planning, logic, content, GUI, persistence,
validation, review, and release documentation.

Version 0.7.1 added JSON-driven player background and personality details:

- New characters receive a generated origin, formative event, personality
  trait, ideal, bond, and flaw.
- Profile content is editable in `data/tables/player_background_tables.json`.
- Older character saves default missing profile fields safely.

Version 0.7 hardened the data-driven generation foundation:

- Added schema-aware validation for required JSON files, categories, weighted
  entries, class resources, and all six class bonuses.
- Added safe fallbacks and deduplicated diagnostics so malformed data does not
  crash normal generation or character creation.
- Added the GUI **Data Diagnostics** view.
- Added process-wide caching for the large cleaned name files.
- Imported the raw and cleaned first-name and surname datasets into the repo.
- Preserved exact world and player-state save/load round trips.

## Current features

- Connected generation for one settlement, 10 NPCs, eight important locations,
  an eight-room cave dungeon, wilderness, 10 encounters, and an adventure hook.
- Stable IDs and cross-references among NPCs, locations, rumors, threats,
  encounters, dungeon rooms, and hooks.
- Character creation with name, background, and 10 JSON-defined classes.
- JSON-driven origin, formative event, personality trait, ideal, bond, and flaw.
- Six rules-neutral bonuses: Combat, Exploration, Social, Lore, Survival, and
  Stealth.
- Class-based resources and placeholder special abilities.
- Structured inventory records and JSON-driven class starting gear.
- Plain-text export for active world summaries, character sheets, and event logs.
- Variable-size editable JSON generation tables, including categories larger
  than 30 entries.
- Generic d20 checks with five outcome grades and exploration consequences.
- Travel, searching, conversations, rest, retreat, dungeon room movement,
  resource use, time periods, discoveries, quest log, and persistent event log.
- Tkinter list/detail views, character sheet, player-state display, simple
  export actions, save/load, and data diagnostics.
- SQLite persistence with compatibility defaults for older save shapes.

## Name generation status

- Raw datasets: `data/names/FirstNames.txt` and `data/names/Surnames.txt`.
- Cleaned datasets: `data/names/first_names.txt` and
  `data/names/last_names.txt`.
- `tools/clean_names.py` normalizes, deduplicates, and sorts raw names.
- `tools/scrub_names.py` removes suspicious corrupted entries.
- `app/name_generator.py` provides cached first, last, full, and batch names.
- NPC generation and the character-creation **Random Name** button use it.
- JSON NPC names remain safe fallbacks for missing or empty cleaned files.

## Testing status

- Test suite: `tests/test_core.py`
- Current verification: 52 tests passing with
  `python -m unittest discover -s tests -v`.
- `python -m compileall .` passes, and all 12 JSON table files parse with zero
  `TableLoader` warnings.
- A Tkinter smoke test could not complete in this environment because the local
  Python 3.11 install could not find a usable `init.tcl`.
- `pytest` is not installed and is not required by the project.
- Coverage includes dice, checks, names, cleanup/scrubbing, JSON validation,
  connected world generation, missing-data fallbacks, exploration, character
  creation, exporter output, variable-size table selection, normalized
  database rows, and older-save compatibility.

## Known issues and boundaries

- Tactical combat, visual maps, full equipment rules, leveling, and spell
  systems are intentionally not implemented.
- The app has no deterministic seed control in the GUI.
- The large name datasets and mutable `data/saves/worlds.db` are tracked, making
  the repository larger and causing save activity to modify a versioned file.
- Tests use `unittest`; `pytest` is optional and not a project dependency.
- The interface is functional but remains a text-oriented Tkinter prototype.

## Next candidate goals

1. Add more NPC dialogue leads and encounter-resolution variety.
2. Add optional seed entry for reproducible generation.
3. Add a small inventory-management dialog only when gameplay needs it.
4. Consider richer export options only after the plain-text flow settles.

## Important files and directories

- `main.py` — application entry point
- `app/game_state.py` — generation coordination and active world
- `app/models.py` — dataclasses and older-save compatibility
- `app/gui.py` — Tkinter interface
- `app/database.py` — SQLite persistence
- `app/table_loader.py`, `app/table_schemas.py` — data validation and fallbacks
- `app/name_generator.py` — cached large-file name generation
- `app/inventory.py` — item catalog and class starting loadouts
- `app/generators/` — focused procedural generators
- `data/tables/` — editable JSON content
- `data/names/` — raw and cleaned name datasets
- `data/tables/item_tables.json` — item definitions and starting gear
- `data/saves/worlds.db` — current SQLite save database
- `tools/` — name cleanup and corruption-scrubbing utilities
- `tests/test_core.py` — automated test suite
- `AGENTS.md` — named AI roles and coordinated operating model

## How to update this file

After a successful milestone, inspect the actual repository state, update the
current tag and latest-work summary, adjust features/issues/next goals, and
record the latest verified test count. Do not claim a feature or passing check
without confirming it from current code or command output.
