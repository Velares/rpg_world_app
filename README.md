# RPG World App

Version 0.7.4 is a local, single-player weird-fantasy starting-region generator
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
list of prior saves. **Export World**, **Export Character**, and
**Export Event Log** write plain-text `.txt` files for the current active data.

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
New characters also receive a generated origin, formative event, personality
trait, ideal, bond, and flaw from `data/tables/player_background_tables.json`.
These details are descriptive only and do not impose additional rules.

Characters have lightweight structured inventory records with a name, category,
quantity, description, tags, and practical status flags such as equipped,
consumable, quest-related, carried, and tradeable. Common and class-flavored
starting gear is defined in `data/tables/item_tables.json`. Food, water,
torches, coin, and abstract supplies remain separate resource counters because
the exploration loop already consumes those values directly.

The app also supports plain-text export for the active world summary, the
active character sheet, and the persistent event log. Exported character text
keeps inventory records and resource counters separate so food, water, torches,
coin, and supplies are not duplicated as consumable inventory quantities.

Editable JSON generation tables are also not fixed `d30` tables. Any practical
non-empty category size works, including one-entry tables, categories shorter
than 30 entries, categories longer than 30 entries, and weighted categories.

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
- `app/character_profiles.py`: JSON-driven personal background details
- `app/inventory.py`: item catalog and class starting-loadout construction
- `app/exporters.py`: plain-text export formatting helpers
- `app/checks.py`: generic d20 checks, outcomes, and state consequences
- `app/generators/`: focused procedural generators
- `data/tables/`: editable generation content
- `data/saves/`: local SQLite saves
- `tests/`: standard-library unit tests

## Editing generation tables

Each file in `data/tables` is a JSON object whose category values are non-empty
lists. Add, remove, or rewrite list entries to change generated content without
changing Python code. Files are loaded when the app starts.

These editable JSON generation tables are not fixed `d30` tables. A category
may contain any practical non-empty number of entries:

- 1 entry works
- fewer than 30 entries work
- more than 30 entries work
- weighted entries still work

Generation code selects from the actual list length provided by the JSON data
rather than assuming 30 rows or a fixed dice index.

Simple lists choose entries uniformly. The loader also accepts weighted entries:

```json
[
  {"value": "common result", "weight": 4},
  {"value": "rare result", "weight": 1}
]
```

The loader validates required files and categories when the app starts. Entries
must be non-empty text, valid weighted text objects, or (for character classes)
objects containing all required resource and bonus fields. Missing files,
malformed JSON, invalid entries, empty categories, and missing category names
are reported as warnings. Invalid entries are skipped, and small type-safe
fallbacks prevent bad local data from crashing generation or character
creation. Use **Data Diagnostics** in the GUI to inspect the complete report.

When adding table data safely:

1. Keep the JSON root as an object and every category as a non-empty list.
2. Use non-blank strings or `{"value": "...", "weight": 1}` entries.
3. Keep weights numeric and greater than zero.
4. Preserve all six class bonus keys and use integer resource values.
5. Run the full test command below before relying on the edited tables.

Generator modules in `app/generators/` share `TableLoader` through the small
`BaseGenerator` helper. Table content remains in JSON; Python modules coordinate
selection and relationships without embedding normal setting content.

## Large name files

Place newline-delimited raw personal names in the current preferred filenames:

```text
data/names/firstnames.txt
data/names/surnames.txt
```

The older filenames `raw_first_names.txt` and `raw_last_names.txt` are also
accepted for compatibility. If both forms exist, the preferred filename above
is used.

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

The cleaned text files are read once and cached by `app/name_generator.py`.
That module provides random first names, last names, full names, and batches of
full names. NPC generation and the **Random Name** button in character creation
use the same cached generator. If either cleaned file is missing, empty, or
unreadable, the smaller editable JSON name tables remain as safe fallbacks.
The current repository tracks both raw and cleaned name datasets. Avoid
duplicating these large lists in Python or JSON.

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

Tests cover dice formulas, name cleanup and generation, character background
profiles, structured inventory, schema-aware table validation, generation with
missing data, generated counts and references, dungeon connectivity, SQLite
child records, save/load reconstruction, and older-save compatibility.

## Current boundaries

The app has a lightweight exploration game loop and character scaffold, but not
tactical combat. Visual maps, detailed combat resolution, deterministic seed
controls, multiplayer, and web/server features are intentionally deferred.

The domain and persistence layers do not depend on Tkinter, which keeps later
migration to a web or server interface practical.

## AI Agent Workflow

This is a solo-developed project supported by AI coding agents. Atlas, Forge,
Scribe, Windowwright, Keeper, Warden, Redline, and Ledger are named roles used
to organize Codex work; they are not separate uncontrolled developers.

The standard workflow is:

1. **Atlas** plans the milestone.
2. **Forge**, **Scribe**, **Windowwright**, or **Keeper** implements the
   requested logic, data, interface, or persistence work.
3. **Warden** runs tests, compilation, and data validation.
4. **Redline** reviews the full diff for scope, quality, and compatibility.
5. **Ledger** updates documentation and release notes.

One Codex session may play several roles in sequence for a small change. Larger
features should be split into separate prompts or milestones. This structure
prevents chaotic edits, protects older saves, and keeps features testable.

Example milestone: **"Add procedural towns."**

- Atlas proposes the town system structure.
- Forge implements the town generator and game-state model.
- Scribe adds town name, shop, rumor, and government tables.
- Keeper ensures towns save/load correctly and older saves still load.
- Windowwright adds GUI display for towns.
- Warden adds and runs tests.
- Redline reviews the full diff.
- Ledger updates README/changelog and prepares the release notes.
