# Changelog

Notable project milestones are recorded here. Dates are omitted where the Git
history is the more reliable source.

## v0.7.6 - Calendar, aging, and downtime framework

- Added `app/calendar.py` to centralize campaign date formatting, time
  advancement, age-band labeling, and long-term aging updates.
- Added `data/tables/downtime_tables.json` plus schema-aware validation and
  fallbacks for JSON-driven downtime task definitions.
- Added `app/downtime.py` and one-active-task support for starting,
  progressing, completing, and occasionally complicating strategic downtime.
- Wired exploration actions, travel, rest, retreat, and generic action checks
  into the shared calendar/time helper so tactical play advances time
  consistently.
- Added simple character age tracking, age bands, downtime summaries, and
  calendar information to player-state display and plain-text exports.
- Preserved save/load compatibility with defaults for older characters and
  player-state saves that predate calendar-aging-downtime fields.
- Added regression coverage for calendar initialization, rollovers, downtime
  loading/fallbacks, task progress/completion, age advancement, exports, and
  save compatibility.

## v0.7.5 - Dialogue leads and encounter variety

- Added `data/tables/interaction_tables.json` for JSON-driven dialogue leads,
  encounter-resolution variety, action-check flavor text, and related
  interaction narration.
- Expanded NPC conversation results with more varied lead styles such as
  warnings, requests, secrets, trade leads, local trouble, and personal
  oddities.
- Expanded encounter outcomes so avoiding, approaching, investigating, and
  retreating can resolve through more varied narrative results while staying
  rules-neutral.
- Added table-driven flavor to searching, inspecting, exploring, retreating,
  and generic d20 action-check narration.
- Added regression coverage for interaction table loading, NPC talk variety,
  encounter variety, check-narration variety, and event-log export
  compatibility.

## v0.7.4 - Plain-text export and flexible table sizes

- Added `app/exporters.py` for focused plain-text world, character, and event
  log export formatting.
- Added simple Tkinter **Export World**, **Export Character**, and
  **Export Event Log** actions with `.txt` as the default save type.
- Removed any remaining fixed-size generation-table assumption from the central
  selection path so editable JSON categories may contain any non-empty
  practical number of entries.
- Made weighted-entry selection work through the standard table chooser used by
  generators.
- Kept export data rules-neutral and preserved separate food, water, torches,
  coin, and supplies counters instead of duplicating them as inventory
  quantities.
- Added regression coverage for generated worlds, empty-state handling, pending
  encounters, character/resource formatting, one-entry tables, short tables,
  tables larger than 30 entries, weighted tables, and malformed-table
  fallbacks.

## v0.7.3 - Structured inventory

- Added rules-neutral inventory records with quantities, categories,
  descriptions, tags, and practical state flags.
- Added JSON-defined common and class starting gear.
- Added minimal character-sheet and player-state inventory display.
- Migrated legacy string inventories and missing inventory fields safely.
- Kept food, water, torches, coin, and supplies as separate gameplay counters.

## v0.7.2 - AI agent workflow

- Defined eight coordinated Codex roles for planning, logic, content, GUI,
  persistence, validation, review, and release documentation.
- Added a concise Plan -> Implement -> Test -> Review -> Document ->
  Commit/Tag operating model.
- Added the workflow and a procedural-town milestone example to the README.

## v0.7.1 - Player background profiles

- Added JSON-driven origin, formative event, personality trait, ideal, bond,
  and flaw generation for new player characters.
- Added character-sheet display, table validation, safe fallbacks, and
  compatibility defaults for older character saves.

## v0.7.0 — Generation data hardening

- Added schema-aware validation and safe fallbacks for JSON generation tables.
- Added GUI data diagnostics and clearer missing/malformed-data reporting.
- Cached large cleaned name datasets across generator instances.
- Added tests for invalid, missing, and empty generation data.
- Added the raw and cleaned first-name and surname datasets plus the current
  SQLite save database to the repository.

## v0.6.0 — Name data cleanup

- Added large text-file name generation for NPCs and character creation.
- Added cleanup and corruption-scrubbing tools for imported name datasets.
- Added first-name, last-name, full-name, batch, fallback, and caching tests.

## v0.5.0 — Action checks

- Added rules-neutral d20 checks using Combat, Exploration, Social, Lore,
  Survival, and Stealth bonuses.
- Added graded outcomes, narrative consequences, and save/load support.

## v0.4.0 — Character classes

- Added player character creation with name, class, and background.
- Added 10 editable, rules-neutral classes in `data/tables/class_tables.json`.
- Added class-based starting supplies and six bonuses: Combat, Exploration,
  Social, Lore, Survival, and Stealth.
- Added placeholder special abilities, character-sheet display, and compatible
  persistence for character state.

## v0.3.0 — Exploration and discovery

- Added time periods, travel, searching, conversations, rest, retreat,
  discoveries, resource pressure, dungeon movement, and persistent event logs.
- Preserved compatibility with earlier generated worlds and saves.
