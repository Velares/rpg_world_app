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
- Current branch: `main`
- Current development state: `main` includes an unreleased plain-text export
  milestone beyond `v0.7.3`
- Latest commit: `08da18b` - `Add plain-text export actions`

Recent milestone completed:

- Added plain-text export for the active world summary
- Added plain-text export for the active character sheet
- Added plain-text export for the persistent event log
- Added simple Tkinter export actions for `.txt` output
- Preserved save/load compatibility by avoiding schema changes
- Kept food, water, torches, coin, and supplies as separate counters instead
  of duplicating them as inventory quantities

## Validation Status

Verified on the current milestone:

- `python -m unittest discover -s tests -v` -> 47 tests passing
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

### Current unreleased changes on `main`

- Added `app/exporters.py` for focused plain-text export formatting
- Added `Export World`, `Export Character`, and `Export Event Log` buttons in
  the Tkinter interface
- Added exporter tests and updated project documentation

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
- Move between dungeon rooms through connected exits
- Take short rests and full rests
- Retreat from danger
- Track days and time periods:
  Morning, Afternoon, Evening, and Night
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
- Emphasize scouting, negotiation, caution, and escape over tactical combat

### Persistence, logs, and exports

- Save worlds to SQLite
- Load previous worlds from SQLite
- Preserve event logs across play and save/load
- Export the active world summary to plain text
- Export the active character sheet to plain text
- Export the active event log to plain text

### Diagnostics and editable content

- Load generation data from editable JSON files
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

1. Add more NPC dialogue leads and encounter-resolution variety.
2. Add optional seed entry for reproducible generation.
3. Add a small inventory-management dialog only when gameplay needs it.
4. Consider richer export options only after the plain-text flow settles.
