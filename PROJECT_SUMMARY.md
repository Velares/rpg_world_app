# RPG World App - Project Summary

## Overview

`RPG World App` is a dependency-free Python/Tkinter weird-fantasy region
generator with a lightweight playable exploration loop, SQLite persistence,
editable JSON-driven content, structured inventory, and rules-neutral
character creation.

The project is designed to stay small, local, testable, and compatible with
older save data.

## Current Status

- Tagged release: `v0.7.3`
- Current development version on `main`: `v0.7.7`
- Current branch: `main`
- Current development state: `main` includes the `v0.7.7` stress and
  error-handling milestone beyond the tagged `v0.7.3` release
- Latest completed commit before this docs/versioning pass: `61a8d6d` -
  `Prepare v0.7.6 calendar and downtime framework update`

Recent milestone completed:

- Added focused stress and illogical-action regression coverage in
  `tests/test_stress.py`
- Added invariant checks around calendar fields, resources, inventory,
  event logs, and pending encounter references after randomized action
  sequences
- Hardened invalid loaded calendar fields so bad day/time values recover
  safely instead of breaking later turns
- Tightened public inventory quantity validation and downtime precondition
  guards with minimal code changes driven by tests

Previous completed milestone:

- Added a shared weird-fantasy calendar layer with year, season, day, and
  time-period tracking built on the existing exploration loop
- Added JSON-driven downtime task definitions and a lightweight one-task
  strategic-play framework for starting, advancing, completing, and
  complicating long-term work
- Added simple character aging in years with narrative age bands and safe
  defaults for older saves
- Added minimal Tkinter downtime actions plus calendar, age, and downtime
  information in the player-state and export views
- Preserved save/load compatibility by defaulting new fields for older saves

Previous completed milestone:

- Added a dedicated JSON-driven interaction-text table for NPC dialogue leads,
  encounter outcomes, and action flavor text
- Expanded NPC conversations with more varied warnings, requests, secrets,
  trade leads, local trouble, clue, and oddity results
- Expanded encounter resolution for avoid, approach, investigate, and retreat
  so outcomes feel more varied while staying rules-neutral
- Added table-driven flavor to searching, inspecting, exploring, retreating,
  and generic d20 action-check narration
- Preserved save/load compatibility by avoiding schema changes

Previous completed milestone:

- Added plain-text export for the active world summary
- Added plain-text export for the active character sheet
- Added plain-text export for the persistent event log
- Added simple Tkinter export actions for `.txt` output
- Removed the remaining central fixed-size editable-table assumption so JSON
  generation categories may contain any practical non-empty number of entries
- Made weighted-entry selection work through the standard generator table path
- Preserved save/load compatibility by avoiding schema changes
- Kept food, water, torches, coin, and supplies as separate counters instead
  of duplicating them as inventory quantities

## Validation Status

Verified on the current milestone:

- `python -m unittest discover -s tests -v` -> 74 tests passing
- `python -m compileall .` -> passing
- All files under `data/tables/` parse with zero unexpected `TableLoader`
  warnings

Environment note:

- A Tkinter smoke test could not fully run in this environment because the
  local Python 3.11 install could not find a usable `init.tcl`

## Version History

### v0.7.3

- Added lightweight structured inventory records
- Added JSON-defined common and class starting gear
- Preserved separate gameplay counters for food, water, torches, coin, and
  supplies
- Preserved compatibility with legacy inventory saves

### v0.7.2

- Added the coordinated AI agent workflow
- Documented the development sequence:
  `Plan -> Implement -> Test -> Review -> Document -> Commit/Tag`

### v0.7.1

- Added generated character profile details:
  origin, formative event, personality trait, ideal, bond, and flaw
- Added safe defaults for older character saves

### v0.7.0

- Hardened JSON-driven content loading and validation
- Added diagnostics and fallbacks for malformed or missing generation data
- Added cached large name-file loading

### v0.7.7

- Added `tests/test_stress.py` for no-world, no-character, repeated-action,
  illogical-sequence, corrupt-data, old-save, and deterministic randomized
  stress coverage
- Added invariant checks after messy public action sequences
- Hardened loaded calendar defaults and public inventory quantity validation
- Guarded downtime start/advance behind character creation

### v0.7.6

- Added `app/calendar.py` for shared calendar, aging, and timeline helpers
- Added `app/downtime.py` plus `data/tables/downtime_tables.json` for
  strategic downtime tasks
- Centralized time advancement across exploration, checks, rests, and
  downtime
- Added age tracking, age bands, downtime summaries, and calendar output to
  exports and player-state views
- Added regression tests for calendar rollovers, downtime progress, aging,
  export visibility, and older-save defaults

### v0.7.5

- Added `app/interaction_text.py` for table-driven interaction-text formatting
- Added `data/tables/interaction_tables.json` for dialogue leads, encounter
  outcomes, and action-check flavor text
- Expanded NPC talk, searching, inspecting, exploring, retreating, and generic
  action checks with more varied event-log narration
- Expanded encounter resolution with more avoid, approach, investigate, and
  failed-forward style outcomes
- Added regression tests for interaction variety and export compatibility

### v0.7.4

- Added `app/exporters.py` for focused plain-text export formatting
- Added `Export World`, `Export Character`, and `Export Event Log` buttons in
  the Tkinter interface
- Centralized flexible table selection in `TableLoader`
- Added tests for one-entry, short, long, weighted, and malformed tables
- Updated project documentation for `v0.7.4`

## What The Game Can Currently Do

### World and region generation

- Generate a weird-fantasy starting region
- Generate a settlement with population, condition, industries, local
  problems, secrets, and nearby danger
- Generate 10 NPCs with names, professions, motivations, fears, secrets, and
  relationships
- Generate important locations with keepers and associated NPCs
- Generate a connected 8-room dungeon
- Generate a wilderness area with hazards, resources, and encounters
- Generate an adventure hook linked to the region
- Preserve stable IDs and cross-references among generated entities

### Character creation and identity

- Create a player character with name, class, and background
- Choose from 10 JSON-defined starter classes
- Generate a random full name from cleaned text datasets with safe fallbacks
- Apply class-based starting resources
- Apply six rules-neutral bonuses:
  Combat, Exploration, Social, Lore, Survival, and Stealth
- Generate descriptive profile details:
  origin, formative event, personality trait, ideal, bond, and flaw
- Track a simple character age in years with a narrative age band

### Inventory and resources

- Track structured inventory records with:
  item key, name, category, quantity, description, tags, and practical state
  flags
- Load common and class-specific starting inventory from JSON
- Display equipped, consumable, quest-related, carried/stored, and tradeable
  item states
- Preserve separate resource counters for:
  supplies, food, water, torches, coin, and wounds-related play impact
- Safely load older saves that used legacy string-based inventory entries

### Exploration loop

- Travel between town, wilderness, dungeon entrance, and dungeon rooms
- Explore the current area
- Search for clues, discoveries, threats, and leads
- Inspect town locations
- Inspect dungeon rooms
- Talk to NPCs
- Receive varied NPC dialogue leads such as rumors, warnings, requests,
  secrets, faction hints, trade leads, and personal oddities
- Move between dungeon rooms through connected exits
- Take short rests and full rests
- Retreat from danger
- Track days and time periods:
  Morning, Afternoon, Evening, and Night
- Map tactical time into an in-world calendar with year, season, day, and time
  period
- Track discovered people, locations, rumors, threats, and rooms over time

### Action checks and consequences

- Run generic `1d20 + bonus vs difficulty` action checks
- Use four difficulty levels:
  Easy, Standard, Hard, and Severe
- Produce five outcome grades:
  critical failure, failure, partial success, success, critical success
- Apply narrative/game-state consequences such as:
  losing time, losing supplies, gaining wounds, attracting attention,
  revealing clues, and changing position

### Encounters and noncombat play

- Surface wilderness warning signs before full danger
- Resolve encounter choices through:
  avoid, approach, investigate, and retreat
- See more varied narrative resolutions such as negotiated outcomes, trade,
  help, odd omens, failed-forward complications, and costly successes
- Emphasize scouting, negotiation, caution, and escape over tactical combat

### Strategic downtime

- Start one active downtime task at a time
- Advance downtime by days instead of individual tactical turns
- Use JSON-driven task definitions for training, research, recovery, study,
  labor, repair, maintenance, rumor work, and relationship-building
- Log downtime starts, progress, complications, and completion in the event log
- Apply a few light completion effects such as recovery, coin, supplies, or
  new leads without introducing a full subsystem

### Stress handling

- Safely reject actions before world generation where public API preconditions
  are missing
- Safely reject downtime actions before character creation
- Tolerate repeated searches, saves, loads, exports, rests, retreats, and
  randomized action ordering without corrupting core state
- Recover from malformed loaded calendar/time fields with compatibility defaults

### Persistence, logs, and exports

- Save worlds to SQLite
- Load previous worlds from SQLite
- Preserve event logs across play and save/load
- Export the active world summary to plain text
- Export the active character sheet to plain text
- Export the active event log to plain text

### Diagnostics and editable content

- Load generation data from editable JSON files
- Allow editable generation categories with any practical non-empty size
- Validate required table files and categories at startup
- Skip malformed entries safely
- Provide fallback generation data when local files are missing or invalid
- Show diagnostics in the GUI through the `Data Diagnostics` view

## Current Boundaries

Intentionally not implemented yet:

- Tactical combat
- Detailed equipment rules
- Leveling
- Spell systems
- Visual maps
- Deterministic seed controls in the GUI
- Multiplayer or web/server deployment
- Rich export formats such as PDF or HTML

## Next Candidate Goals

1. Add optional seed entry for reproducible generation.
2. Expand downtime consequences with more location, faction, and quest-aware
   follow-up only if the lightweight framework proves useful in play.
3. Add a small inventory-management dialog only when gameplay needs it.
4. Design later character retirement so retired protagonists can remain in the
   same world as NPCs after the calendar/downtime layer settles.
5. Add GUI-layer guard tests only if a reliable headless Tk/Tcl setup becomes
   available.
