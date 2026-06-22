# Changelog

Notable project milestones are recorded here. Dates are omitted where the Git
history is the more reliable source.

## v0.8.7 - monster manual importer milestone 1

- Added `tools/importers/monster_manual_importer.py` and
  `tools/importers/monster_manual_schema.py` for a repeatable monster-manual
  import pipeline that reads only the monster-entry page ranges from the
  combined PDF and ignores appendices for now.
- Added text-first parsing helpers for uppercase monster headings, multi-page
  entry assembly, standard stat-block labels, wrapped treasure and level/xp
  values, the `LAIR PROBABLITY` typo, and several irregular attack/damage/hit
  dice formats while preserving raw text for every imported record.
- Added editable monster catalog output structure with source page tracking,
  parsed stat blocks, section buckets, tags, and import-report generation for
  warnings, missing expected fields, duplicate IDs, and first/last entries per
  book.
- Added focused importer tests with inline fixture text for normal entries,
  mid-page follow-on entries, typo handling, multiline `LEVEL/X.P.`, and more
  complex attack/damage formats.
- Kept the work tooling-only: no save/load schema changes, no app-facing
  encounter generation, no appendix parsing, and no hard-coded monster data in
  application logic.
- Raised the validated suite to 123 passing `unittest` tests; the full real
  PDF import step remains pending until `data/import_sources/mandbmaster.pdf`
  is available locally.

## v0.8.6 - inventory, equipment, bulk, and encumbrance

- Added a lightweight equipment framework with named slots for worn gear,
  hands, rings, back items, and a backpack/container slot, plus simple
  handedness rules for one-handed and two-handed items.
- Expanded `InventoryItem` records and `data/tables/item_tables.json` so item
  definitions can carry bulk, valid slots, container capacity, and placeholder
  combat/economy-facing metadata without introducing a full ruleset.
- Added shared encumbrance helpers with four rules-neutral states:
  unencumbered, burdened, heavily burdened, and overloaded.
- Added a minimal Tkinter `Inventory / Equipment` dialog with dropdown-driven
  equip and unequip controls, current slot summaries, and carried-bulk /
  encumbrance feedback.
- Expanded character recap and plain-text export output to include equipped
  slots, carried inventory, bulk totals, and encumbrance state while keeping
  resource counters separate from inventory records.
- Updated compatibility guidance and repair defaults around the new inventory
  shape, with active support now centered on v0.8.4+ save data rather than
  the oldest early-project save experiments.
- Added regression and stress coverage for item-table validation, stackable
  versus equippable inventory behavior, slot rules, encumbrance state,
  export/recap visibility, and v0.8.4/v0.8.5 compatibility repair, bringing
  the validated suite to 118 passing `unittest` tests.

## v0.8.5 - character sheet and diary

- Expanded the character sheet with classic ability scores alongside the
  existing six gameplay bonuses, plus compatibility-safe class role, class
  type, class subtype, and placeholder fixed/derived score fields for future
  growth.
- Added a lightweight character diary system with protected milestone entries,
  editable ordinary entries, player notes on milestones, and grouped daily,
  weekly, monthly, and yearly views.
- Routed important structured timeline events into diary generation with
  placeholder importance levels so world starts, character creation, downtime,
  key-NPC milestones, faction shifts, and similar events leave a diary trail.
- Added a minimal Tkinter **Character Diary** area that takes over the main
  view until exited, with add, edit, hide, delete, refresh, and notes-focused
  milestone handling.
- Expanded character exports and recap text to surface diary highlights and the
  richer character-sheet structure without replacing the older event log.
- Preserved older-save compatibility by defaulting missing character-sheet and
  diary fields on load, raising the validated suite to 112 passing `unittest`
  tests.

## v0.8.4 - lead follow-up and resolution

- Added lightweight lead-status advancement helpers so lead threads can move
  among open, corroborated, resolved, failed, and stale states without adding
  a larger quest system.
- Added a shared follow-lead gameplay action that advances time and turns an
  open lead into a concrete result such as a corroborated clue, a resolved
  thread, a resource-costing exploration step, a new NPC contact, or a
  follow-up lead.
- Added recent lead-change formatting so summaries and exports can show not
  only unresolved leads but also which threads were recently corroborated,
  resolved, failed, or left stale.
- Added a minimal Tkinter **Follow Open Lead** action and updated recap/summary
  displays so open leads and suggested actions are clearer in regular play.
- Preserved older-save compatibility by defaulting new lead-update metadata and
  reconstructing legacy string leads safely.
- Added regression coverage for lead-status transitions, follow-lead behavior,
  recap/export visibility, GUI action-label routing, and updated stress
  invariants, bringing the validated suite to 108 passing `unittest` tests.

## v0.8.3 - lead tracking and next-action guidance

- Moved **Generate New Region** into the always-visible shared action area so a
  fresh launch exposes world generation without requiring a mode switch.
- Added centralized GUI action-availability rules so most world-dependent
  buttons stay disabled until a world exists, and character-dependent buttons
  remain disabled until a character exists.
- Kept the underlying public handlers guarded so disabled buttons improve
  usability without becoming the only safety layer.
- Added helper-level tests for initial action availability and
  world-versus-character prerequisites.
- Added lightweight structured lead records with source, location, related NPC,
  status, suggested action, and category while preserving older saves that only
  store legacy lead strings.
- Added **Open Leads** and grouped **Suggested Next Actions** sections to the
  journal summary and plain-text exports so recent rumors, clues, and downtime
  follow-ups become clearer player-facing choices.
- Routed talk, discovery, action-check, and downtime lead creation through the
  shared lead helper so duplicate leads are deduplicated and repeated evidence
  can corroborate an existing thread.
- Capped visible downtime progress at the task requirement and made training,
  trade, and generic completion text produce more concrete gameplay-facing
  follow-up instead of only vague benefit phrasing.
- Added regression coverage for lead restoration from older saves, lead
  deduplication and corroboration, next-action export visibility, capped
  downtime progress display, and concrete downtime completion follow-up.

## v0.8.2 - GUI mode split and journal recap

- Split the Tkinter action layout into two primary modes: `Town Mode` for
  social, recovery, downtime, and management play, plus `Adventure Mode` for
  travel, exploration, encounter-facing actions, and field checks.
- Added shared cross-mode actions for viewing the character, opening the new
  journal/world recap, saving, loading, exporting logs/worlds/characters, and
  viewing diagnostics without duplicating gameplay logic.
- Added a plain-text `Journal / World Recap` view that highlights the current
  calendar, character, location, downtime, resources, leads, quest notes,
  clues, key NPCs, faction notes, recent events, and journal summary in one
  place.
- Kept public action handlers guarded so hidden or mode-specific buttons are
  not the only protection against missing world, missing character, or other
  invalid state.
- Deferred larger simulated-time controls for a future milestone to keep the
  GUI split small and reviewable.
- Added non-Tk helper coverage for GUI mode routing and recap formatting,
  bringing the validated suite to 100 passing `unittest` tests.

## v0.8.1 - Key NPC and faction-interaction phase framework

- Added lightweight key-NPC promotion after highly prominent recurring NPCs
  reach a higher threshold, with key-NPC dates, reasons, notes, and placeholder
  faction tags.
- Added compatibility-safe key-NPC relationship records between promoted NPCs,
  including deduplicated pair storage, relationship state, affinity score,
  timestamps, reason text, and recent event notes.
- Added a small faction/NPC interaction phase that can run after downtime
  completion and day-boundary travel or rest, producing concise event-log and
  structured-timeline entries without introducing a full faction simulator.
- Added editable `data/tables/key_npc_tables.json` for key-NPC promotion text
  and lightweight ally/at-odds/neutral phase-event phrasing.
- Expanded plain-text exports and NPC detail views to surface key NPCs,
  relationship records, and lightweight faction-status notes where available.
- Preserved older-save compatibility by defaulting missing key-NPC fields,
  relationship records, faction-status notes, and phase metadata on load.
- Added regression and stress coverage for key-NPC thresholds, relationship
  creation and deduplication, malformed relationship recovery, phase no-op and
  event behavior, export visibility, and older-save compatibility.

## v0.8.0 - Timeline logging and prominent NPC framework

- Added `app/timeline.py` plus compatibility-safe `TimelineEntry` and NPC
  interaction fields so play can be recorded in both action-by-action and
  summary-friendly form without removing the existing event log.
- Wired exploration actions, downtime progress, checks, character creation,
  and world start-up into the structured timeline layer with calendar, action,
  location, and lightweight reference metadata.
- Added recurring-NPC promotion after repeated meaningful interactions,
  including placeholder deeper backstory, motive, pressure, relationship,
  ongoing-thread, and recent-note fields.
- Added `data/tables/npc_depth_tables.json` so recurring-NPC placeholder depth
  text remains JSON-driven and editable rather than hard-coded as large prose
  lists.
- Expanded plain-text exports and the Tkinter text UI with journal summary,
  verbose timeline, and prominent-NPC detail views while keeping GUI changes
  minimal.
- Preserved older-save compatibility by defaulting missing timeline entries,
  NPC prominence fields, and recurring-note lists on load.
- Added regression and stress coverage for timeline formatting, repeated NPC
  conversations, recurring-NPC promotion, export visibility, and malformed or
  missing timeline/NPC save data.

## v0.7.9 - World-aware downtime consequences

- Expanded `data/tables/downtime_tables.json` with optional
  `progress_outcomes`, `completion_outcomes`, and `complication_outcomes`
  entries for lightweight world-aware downtime follow-up.
- Added downtime consequence handling that can create leads, add quest notes,
  spend or recover small resources, and add quest-flavored clue items while
  routing text through the existing event log.
- Added world-aware template context for downtime text so outcomes can mention
  the current settlement, season, known NPCs, locations, rumors, threats,
  dungeon clues, wilderness clues, and character details without adding new
  heavy subsystems.
- Preserved older-save compatibility by defaulting new downtime outcome fields
  on loaded active tasks.
- Added regression coverage for downtime consequence progress, completion,
  complication handling, malformed outcome validation, old-save downtime task
  defaults, fallback behavior, and export visibility.

## v0.7.8 - Optional seed control for reproducible generation

- Added optional text-seed support to `app/game_state.py` so the same seed can
  recreate the same generated starting world when the code and local data are
  unchanged.
- Added a small Tkinter generation-seed entry field and surfaced the active
  seed in the player-state display and world overview.
- Stored the seed on generated world data without changing the SQLite schema,
  so saves without a seed still load safely and newer saves can report it.
- Added seed lines to plain-text world, character, and event-log exports when
  a generated world records one.
- Added regression coverage for text seeds, same-seed reproducibility,
  different-seed divergence, save/load seed persistence, export seed output,
  and missing-seed older-save compatibility.

## v0.7.7 - Stress and error-handling coverage

- Added `tests/test_stress.py` for no-world, no-character, repeated-action,
  illogical-sequence, old-save, corrupt-data, and deterministic randomized
  stress coverage.
- Added invariant checks around player state, calendar fields, resources,
  inventory, event logs, and pending encounter references after messy action
  sequences.
- Hardened calendar compatibility so invalid loaded `day`, `time_period`, and
  `age_days_accumulated` values fall back safely instead of breaking later time
  advancement.
- Tightened public inventory helpers so non-integer add/remove quantities fail
  with clear `ValueError` messages.
- Guarded downtime start/advance behind player-character creation to prevent
  illogical strategic actions before identity setup exists.

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
