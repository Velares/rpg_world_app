# Changelog

Notable project milestones are recorded here. Dates are omitted where the Git
history is the more reliable source.

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
