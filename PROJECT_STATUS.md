# RPG World App - Project Status

## Current version

- Current tag: `v0.7.3`
- Current development version on `main`: `v0.8.13`
- Current branch at this update: `main`
- Runtime: Python 3.11-compatible standard library, Tkinter, and SQLite

## Latest completed work

Version 0.8.13 adds the Step 1 source-registry and source-path validation
foundation on `main`:

- Added an editable source registry at `data/source_registry.json`.
- Recorded current durable source policy in structured form, including active
  rules references, comparison-only references, inactive removed rules PDFs,
  the stable monster-manual PDF path, the separate ADD Bestiary source path,
  and future domain placeholders.
- Added `app/source_registry.py` for reusable registry loading, validation,
  duplicate `source_id` checks, allowed domain/status checks, and local
  expected-path presence reporting.
- Added `python tools/validate_sources.py` for local source validation without
  requiring importer dependencies or committed PDFs.
- Kept missing optional/inactive local PDFs from breaking normal validation,
  while still allowing explicitly required active sources to fail validation in
  the future if needed.
- Added focused source-registry tests and raised the validated `unittest`
  count to 163 while `python -m compileall .` still passes.
- This milestone is Step 1 of the 8-step source/import roadmap and does not
  import new content or change existing importer behavior.

Version 0.8.12 adds ADD Bestiary import milestone 1 support on `main`:

- Added a dedicated ADD Bestiary importer command at
  `python tools/import_add_bestiary.py`.
- Scoped the importer to actual PDF pages 4 through 438 and documented that
  printed page numbers in the PDF are not authoritative.
- Added raw page extraction to
  `import_work/adventures_dark_and_deep_bestiary/raw_pages/` using actual PDF
  page numbers in filenames.
- Added conservative Milestone 1 parsing that accepts likely single-entry
  monsters only when the expected ADD stat block is present together with at
  least one prose section such as `General`, `Combat`, or `Appearance`.
- Deferred multi-column and repeated-stat-block variant monsters by rejecting
  them with the explicit reason
  `multi_variant_stat_block_not_supported_yet` rather than inventing bad child
  records.
- Added draft output support for
  `data/content_packs/imported/adventures_dark_and_deep_bestiary/pack.json`
  and `monsters.json`, plus a focused validator for the imported pack shape.
- Added lightweight combined monster-catalog helpers so the core manual-import
  catalog and imported content-pack monsters can be loaded together and sorted
  alphabetically by display name without overwriting same-name records from
  different sources.
- Added focused ADD importer tests and raised the validated `unittest` count
  to 152 while `python -m compileall .` still passes.
- The user-provided ADD Bestiary PDF is not present in this workspace yet, so
  the real importer command currently exits with a clear file-not-found message
  after ensuring the documented input folder exists.

Version 0.8.11 adds the monster catalog multi-source import foundation on
`main`:

- Added a shared monster-catalog import helper layer so future monster sources
  can normalize into the existing canonical monster-record shape without
  rewriting the stable PDF or appendix importers.
- Added `tools/importers/monster_json_importer.py` for JSON-based monster
  import preview, report generation, and optional safe-addition catalog writes.
- Added source metadata conventions for imported records through optional
  `import_metadata` fields such as `source_id`, `source_name`, `source_type`,
  `source_file`, `source_page`, `source_record_id`, `import_method`,
  `import_version`, `original_name`, `normalized_name`, warnings, notes, and
  preserved extra source fields.
- Added conservative merge classification for `would_add`, `exact_duplicate`,
  `would_update`, `would_conflict`, and `protected_conflict` cases so later
  multi-source catalog work stays auditable instead of silently overwriting
  records.
- Added lightweight manual/custom protection hooks keyed off
  `custom_record`, `manual_override`, `protected_fields`, and manual/custom
  source types to prepare for a later editable Bestiary flow.
- Kept the default JSON import path non-destructive: dry-run preview stays the
  default, while explicit write mode only applies safe additions and leaves
  updates/conflicts report-only for later review.
- Preserved the stable monster stat importer and appendix importer regression
  suites, and raised the validated `unittest` count to 146 while
  `python -m compileall .` still passes.

Version 0.8.10 adds the appendix unmatched-review and normalization pass on
`main`:

- Kept appendix parsing separate from the stable monster stat importer and
  focused only on appendix data quality.
- Added broader but still conservative appendix-name normalization through
  shared normalized variants, including article stripping, simple singular
  handling, parenthetical-descriptor removal, and tightly limited one-edit
  typo recovery when the result is unique.
- Reduced unmatched appendix references from 413 to 395 without adding a
  manual monster-mapping table or broad fuzzy guessing.
- Added a clearer `Unmatched Reference Review` section inside
  `data/import_reports/monster_appendix_import_report.txt`.
- Added a separate audit artifact at
  `data/import_reports/monster_appendix_unmatched_review.txt` with grouped
  repeated unresolved names, category counts, pages, and example tables.
- The current rerun still preserves 2,981 appendix records total, now with
  2,586 matched references, 395 unmatched references, and 0 ambiguous
  references.
- Reran the stable monster stat importer without regression: 268 parsed
  monsters, 0 warnings, 111 rejected candidate headings, no duplicate IDs, no
  null `SIZE` records, and the same one remaining missing expected field for
  `WORM, FURNACE` intelligence.
- Added focused appendix importer regression coverage and raised the validated
  `unittest` count to 139 while `python -m compileall .` still passes.

Version 0.8.9 adds the first appendix parsing milestone for monster-manual
tooling on `main`:

- Added `tools/importers/monster_appendix_importer.py` as a separate appendix
  parser so terrain, rarity, and level appendix data can be cataloged without
  changing the stable monster stat importer.
- Added appendix page-range and output-path constants in the shared importer
  schema helper.
- Parsed both books' `Appendix B`, `Appendix C`, and `Appendix D` pages into a
  new editable appendix catalog with actual PDF page references, section
  titles, table titles, region/terrain/climate context, optional roll ranges,
  raw row text, and conservative match status.
- Added conservative name matching against
  `data/catalogs/monsters/monster_catalog.json`, including punctuation/case
  normalization and safe comma-form handling such as `Wax Golem` matching
  `GOLEM, WAX`.
- Kept unmatched appendix references instead of guessing and wrote them to a
  separate appendix import report for later follow-up.
- A local rerun against `data/import_sources/MandBmaster.pdf` now produces
  2,981 appendix records with 2,568 matched references, 413 unmatched
  references, 0 ambiguous matches, and 0 skipped rows in the current parser
  pass.
- Reran the stable monster stat importer without regression: 268 parsed
  monsters, 0 warnings, 111 rejected candidate headings, no duplicate IDs, no
  null `SIZE` catalog records, and the same one remaining missing expected
  field for `WORM, FURNACE` intelligence.
- Added focused appendix importer tests and raised the validated `unittest`
  count to 137 while `python -m compileall .` still passes.

Version 0.8.8 tightens real-monster field normalization after the importer
cleanup pass on `main`:

- Added a narrow parser guard for unmodeled stat-adjacent labels so side
  fields such as `CHANCE OF`, `Magic Use`, `Sleeping`, and similar spillover
  lines no longer pollute structured values like `ALIGNMENT`.
- Added targeted recovery for page-top orphaned stat lines when PDF extraction
  separates late stat fields from a monster heading but nearby prose still
  clearly belongs to that same monster.
- Fixed `WYRM, KURGAN` so its alignment stays clean instead of absorbing the
  following chance-of-use text.
- Recovered `Dragon, Crustacean` intelligence, alignment, level/xp, and full
  treasure continuation from split page text.
- Kept `Worm, Furnace` honestly flagged for a missing `INTELLIGENCE` field
  because the extracted PDF text still does not expose a reliable value to
  recover.
- Preserved the existing header/page-marker cleanup behavior, with the local
  rerun still producing 268 parsed monsters, 111 rejected candidate headings,
  no false single-letter or running-header catalog entries, no duplicate IDs,
  and one remaining missing expected common field.
- Added focused importer regression coverage and raised the validated
  `unittest` count to 130 while `python -m compileall .` still passes.

Version 0.8.7 adds the first monster-manual importer milestone on `main`:

- Added `tools/importers/monster_manual_importer.py` plus a small schema
  helper for a repeatable PDF-to-JSON monster catalog pipeline.
- Scoped Milestone 1 to the actual monster-entry pages only:
  Book 1 actual pages 2-115 and Book 2 actual pages 124-220, leaving
  appendices for later work.
- Added entry detection for uppercase monster headings followed by `SIZE:`,
  including multi-page entries and entries that begin partway down a page
  after a prior monster's prose.
- Added tolerant stat-block parsing for wrapped `TREASURE` and `LEVEL/X.P.`
  values, the `LAIR PROBABLITY` typo, AC values with parentheses, irregular
  hit-dice formats, and mixed attack/damage fields while preserving raw text.
- Added editable catalog/report output structure with source page tracking,
  section buckets, lightweight tags, duplicate-ID reporting, and missing-field
  reporting.
- Tightened heading detection and page cleanup so running headers, letter
  markers, dangling fragments, and standalone page-number lines are rejected
  before catalog generation rather than turning into false monster records.
- Kept the work tooling-only with no save/load schema changes, no app-facing
  encounter generation, and no appendix parsing yet.
- Added focused importer tests and raised the validated `unittest` count to
  123 while `python -m compileall .` still passes.
- A local rerun against `data/import_sources/MandBmaster.pdf` now produces 268
  parsed monsters with 111 rejected candidate headings, no false single-letter
  or running-header catalog entries, no duplicate IDs from header noise, and
  only two currently reported missing-expected-field cases in the real output.

Version 0.8.6 expands structured inventory into lightweight equipment, bulk,
and encumbrance support on `main`:

- Added named equipment slots for worn gear, hand items, rings, back items,
  and a backpack/container slot without introducing a heavier combat or vendor
  subsystem.
- Expanded item-table definitions and `InventoryItem` records with bulk, valid
  slots, handedness, container capacity, and placeholder combat/economy-facing
  metadata for future use.
- Added simple encumbrance helpers and rules-neutral states:
  unencumbered, burdened, heavily burdened, and overloaded.
- Added a minimal Tkinter `Inventory / Equipment` dialog with dropdown equip /
  unequip controls, slot summaries, and current bulk feedback.
- Expanded character recap and plain-text export output to show equipped
  slots, carried inventory, bulk totals, and encumbrance state while keeping
  food, water, torches, coin, and supplies as separate authoritative counters.
- Tightened compatibility repair around the newer inventory shape and
  equipment defaults, with active save compatibility now centered on the
  v0.8.4+ baseline rather than the oldest early-project save experiments.
- Added regression and stress coverage for item validation, stackable versus
  equippable behavior, slot rules, bulk/encumbrance state, export visibility,
  and compatibility repair, bringing the validated `unittest` count to 118
  while the local `init.tcl` limitation still blocks a true Tk root smoke
  test.

Version 0.8.5 expands the character sheet and adds a diary system on `main`:

- Added classic ability scores alongside the existing six gameplay bonuses so
  the character sheet now carries both immediate exploration bonuses and a more
  traditional six-score scaffold for later mechanics.
- Added compatibility-safe class role, class type, class subtype, and
  placeholder fixed/derived score fields so future rules layers have somewhere
  to grow without rewriting the current character record.
- Added a lightweight diary model with editable ordinary entries, protected
  milestone entries, player notes on milestones, and grouped daily, weekly,
  monthly, and yearly views.
- Routed important structured timeline events into diary generation with
  placeholder importance levels so major world and character developments
  create a persistent character-facing record.
- Added a minimal Tkinter `Character Diary` area that temporarily takes over
  the main display until exited, keeping Town Mode and Adventure Mode intact
  while adding a third focused place for reflection and notes.
- Expanded character exports and recap output with diary highlights and the
  richer character-sheet structure.
- Preserved older-save compatibility by defaulting missing character-sheet and
  diary fields on load, bringing the validated `unittest` count to 112 while
  the local `init.tcl` limitation still blocks a true Tk root smoke test.

Version 0.8.4 adds lightweight lead follow-up and resolution on `main`:

- Added small status helpers so lead threads can advance among open,
  corroborated, resolved, failed, and stale states without becoming a full
  quest system.
- Added a shared follow-lead gameplay action that advances time and turns an
  open lead into a concrete result such as a corroborated clue, a resolved
  thread, a resource-costing exploration step, a new contact, or a fresh
  follow-up lead.
- Added recent lead-change formatting so summaries and exports can show both
  unresolved leads and recently advanced threads.
- Added a minimal Tkinter `Follow Open Lead` action and recap/output updates so
  the player can act on current leads without a large GUI rewrite.
- Preserved older-save compatibility by defaulting new lead-update metadata
  and safely reconstructing legacy string leads.
- Added regression coverage for lead-status transitions, follow-lead behavior,
  recap/export visibility, GUI action labels, and updated stress invariants,
  bringing the validated `unittest` count to 108 while the local `init.tcl`
  limitation still blocks a true Tk root smoke test.

Version 0.8.3 improves immediate usability and next-step guidance on `main`:

- Kept `Generate New Region` in the always-visible shared action area so a
  fresh launch exposes world generation without requiring a mode switch.
- Centralized action-availability rules so most world-dependent buttons remain
  disabled until a world exists, and character-dependent buttons remain
  disabled until a character exists, while the same guarded public handlers
  stay in place underneath.
- Added lightweight structured lead records with source, location, related
  NPC, status, suggested action, and category while preserving older saves
  that only stored legacy lead strings.
- Added `Open Leads` and grouped `Suggested Next Actions` sections to the
  journal summary and plain-text exports so recent clues, rumors, and downtime
  follow-up become clearer player-facing choices.
- Routed talk, discovery, action-check, and downtime leads through a shared
  helper so duplicate leads are deduplicated and repeated evidence can
  corroborate an existing thread.
- Capped visible downtime progress at the task requirement and made training
  and other completion text produce more concrete gameplay-facing results.
- Added regression coverage for lead restoration, deduplication, export and
  summary visibility, capped downtime progress display, and concrete downtime
  follow-up, bringing the validated `unittest` count to 106 while the local
  `init.tcl` limitation still blocks a true Tk root smoke test.

Version 0.8.2 reorganizes the GUI into clearer play modes on `main`:

- Split the Tkinter action layout into `Town Mode` and `Adventure Mode` so
  settlement-management actions no longer compete with travel/exploration
  controls in one crowded button stack.
- Added shared actions across both modes for character viewing, journal recap,
  save/load, export, and diagnostics while preserving the older event-log,
  timeline, downtime, key-NPC, and export systems behind the same guarded game
  state handlers.
- Added a `Journal / World Recap` text view that summarizes the current
  calendar, character, location, downtime, resources, leads, quest notes,
  clues, key NPCs, faction notes, recent events, and journal summary in one
  place.
- Kept the change GUI-focused and deferred any broader simulated-time controls
  so the milestone stayed small and reviewable.
- Added non-Tk helper coverage for mode action lists and recap formatting,
  raising the validated `unittest` count to 100 while the local `init.tcl`
  limitation still blocks a true Tk root smoke test.

Version 0.8.1 adds key NPC and faction-interaction framework support on
`main`:

- Promoted highly prominent recurring NPCs into key NPCs with key dates,
  reasons, notes, and lightweight placeholder faction tags.
- Added deduplicated relationship records between key NPC pairs with ally,
  at-odds, neutral, or unknown states plus lightweight affinity and event-note
  tracking.
- Added a small faction/NPC interaction phase that can trigger after downtime
  completion and day-boundary travel or rest, feeding concise results into the
  event log and structured timeline.
- Added editable key-NPC text tables for promotion reasons, notes, and
  relationship-phase event phrasing.
- Extended exports and NPC detail views to surface key NPCs, relationship
  records, and lightweight faction-status notes.
- Preserved older-save compatibility by defaulting missing key-NPC,
  relationship, faction-status, and phase-metadata fields on load.

Version 0.8.0 adds timeline logging and prominent recurring NPC support on
`main`:

- Added structured timeline entries alongside the older immediate event log so
  actions can be reviewed in both verbose and summary form.
- Logged travel, exploration, searching, inspection, conversation, encounters,
  downtime, checks, and world-start activity with calendar/time and lightweight
  NPC/location/lead references.
- Added recurring-NPC tracking with interaction counts, recent interaction
  notes, and a simple prominence trigger after repeated meaningful contact.
- Added placeholder deeper recurring-NPC fields backed by editable JSON text
  tables so richer personal notes can grow without hard-coding content in
  Python.
- Extended plain-text exports and the GUI text views with journal summary,
  verbose timeline, and prominent-NPC details.
- Preserved older-save compatibility by defaulting missing timeline and
  recurring-NPC fields on load.

Version 0.7.9 expands world-aware downtime consequences on `main`:

- Added optional JSON-driven downtime outcome lists for progress, completion,
  and complication follow-up.
- Made downtime outcomes capable of referencing current settlement, season,
  known NPCs, locations, rumors, threats, dungeon clues, wilderness clues,
  leads, and simple inventory context.
- Kept the system rules-neutral by routing effects through existing leads,
  quest notes, event logs, supplies/coin counters, and lightweight clue items
  instead of adding full faction, economy, crafting, or relationship systems.
- Preserved older-save compatibility by defaulting missing outcome fields on
  loaded active downtime tasks.

Version 0.7.8 adds optional seed control for reproducible generation on `main`:

- Added optional text seed entry to the GUI and matching `GameState`
  generation support for reproducible starting-world creation.
- Scoped deterministic generation to the initial world-building flow while
  leaving blank-seed play in normal random mode.
- Stored the generation seed in world data so saved worlds and plain-text
  exports can report it when known.
- Added regression coverage for same-seed matching, different-seed divergence,
  text seed handling, save/load compatibility, and export seed lines.

Version 0.7.7 adds stress/error-handling test coverage on `main`:

- Added focused stress coverage for messy button ordering, repeated actions,
  illogical gameplay sequences, old-save action paths, and corrupt local data.
- Added deterministic randomized action-sequence testing with invariant checks
  after every step.
- Hardened loaded calendar defaults so invalid day/time values recover safely.
- Tightened inventory quantity validation and downtime precondition guards with
  minimal code changes driven by tests.

Version 0.7.6 adds a calendar, aging, and strategic-downtime framework on
`main`:

- Added a shared weird-fantasy calendar layer with year, season, day, and time
  period derived from the existing playable turn structure.
- Centralized tactical time advancement so exploration, travel, checks, rests,
  retreat, and downtime all move through the same calendar logic.
- Added JSON-driven downtime task definitions plus a lightweight one-task
  strategic-play loop for starting, advancing, completing, and complicating
  long-term work.
- Added simple character aging in years with narrative age bands and safe
  defaults for older saves.
- Kept the framework rules-neutral and avoided full skill, spell, crafting,
  economy, or relationship subsystems.

Version 0.7.5 expands dialogue and encounter variety on `main`:

- Added a dedicated `interaction_tables.json` file for JSON-driven dialogue
  leads, encounter outcomes, and interaction flavor text.
- Expanded NPC conversation leads with more varied warning, request, secret,
  trade, clue, and oddity results.
- Expanded encounter-resolution variety for avoid, approach, investigate, and
  retreat without introducing tactical combat or a heavier ruleset.
- Added table-driven flavor to searching, inspecting, exploring, retreating,
  and generic d20 action-check narration.
- Preserved save/load compatibility by avoiding schema changes.

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
- Tooling-only monster manual import pipeline for PDF-to-JSON catalog creation.
- Tooling-only monster-manual appendix import pipeline for PDF-to-JSON appendix
  catalog creation with conservative monster matching.
- Appendix unmatched-reference review output with grouped repeated unresolved
  names and conservative normalization auditing.
- Dry-run JSON monster import preview tooling with source metadata, duplicate
  detection, conflict reporting, and manual/custom protection planning for
  later multi-source Bestiary work.
- ADD Bestiary Milestone 1 importer scaffolding for actual-page parsing, raw
  page extraction, content-pack draft output, and combined alphabetical monster
  views across sources.
- Editable source registry plus local source-path validation tooling.
- Lightweight equipment slots, carried bulk, and encumbrance states.
- Optional text-seed control for reproducible world generation.
- Plain-text export for active world summaries, character sheets, and event logs.
- Lightweight structured lead tracking with grouped suggested next actions.
- Lightweight lead follow-up and status resolution without a full quest system.
- Variable-size editable JSON generation tables, including categories larger
  than 30 entries.
- Richer NPC dialogue leads and encounter-resolution variety driven by JSON
  interaction tables.
- Generic d20 checks with five outcome grades and exploration consequences.
- Travel, searching, conversations, rest, retreat, dungeon room movement,
  resource use, a shared calendar/time model, discoveries, quest log, and
  persistent event log.
- Strategic downtime tasks for training, research, recovery, study, labor,
  relationship-building, repair, and maintenance.
- World-aware downtime consequence hooks for leads, quest notes, resource
  nudges, and clue-style inventory follow-up.
- Structured timeline logging with verbose and summary views.
- Recurring-NPC tracking with prominence after repeated meaningful
  interactions.
- Placeholder recurring-NPC depth notes driven by editable JSON tables.
- Key-NPC promotion and lightweight inter-NPC relationship tracking.
- Coarse-grained faction/NPC interaction phase with lightweight status notes.
- Simple character age tracking with narrative age bands.
- Tkinter list/detail views, character sheet, player-state display, simple
  export actions, seed entry, `Town Mode` / `Adventure Mode` action groups,
  downtime controls, journal/timeline views, recap view, save/load, and data
  diagnostics.
- SQLite persistence with compatibility defaults for the supported v0.8.4+
  save baseline.

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
- Additional stress suite: `tests/test_stress.py`
- Current verification: 163 tests passing with
  `python -m unittest discover -s tests -v`.
- `python -m compileall .` passes, and all 16 JSON table files parse with zero
  `TableLoader` warnings.
- `python tools/validate_sources.py` now reports the local source-registry
  summary separately from importer runs. In the current workspace it reports
  19 total sources, 1 present file, 18 missing expected files, 3 warnings, and
  0 errors because the missing files are optional active or inactive
  references rather than required active sources.
- The monster-manual importer tests pass, but the expected default source PDF
  may differ by local filename casing. The current workspace rerun used
  `data/import_sources/MandBmaster.pdf` successfully.
- The new appendix importer also reran successfully against
  `data/import_sources/MandBmaster.pdf`, producing 2,981 appendix records with
  2,586 matched references, 395 unmatched references, 0 ambiguous matches,
  and 0 skipped rows.
- The ADD Bestiary importer command now exists and prepares the documented
  source folder automatically, but the actual source PDF is not present in this
  workspace yet, so a full import rerun remains pending the user-supplied file
  at `data/import_sources/adventures_dark_and_deep_bestiary/Adventures Dark and Deep Bestiaryforingestion.pdf`.
- No Tkinter smoke test was completed for this milestone because the local
  Python 3.11 install still lacks a usable `init.tcl`; an attempted Tk root
  creation still fails for that reason, so GUI-facing behavior was validated
  indirectly through public state and helper tests instead.
- `pytest` is not installed and is not required by the project.
- Coverage includes dice, checks, names, cleanup/scrubbing, JSON validation,
  connected world generation, missing-data fallbacks, exploration, calendar
  rollovers, downtime flow, character creation, exporter output, variable-size
  table selection, interaction variety, normalized database rows, older-save
  compatibility, reproducible seed behavior, world-aware downtime outcomes,
  timeline logging, recurring-NPC promotion, key-NPC promotion, relationship
  records, faction-phase behavior, equipment slot rules, bulk and encumbrance
  state, monster-manual stat-block parsing, and randomized/error-handling
  stress scenarios.

## Known issues and boundaries

- Tactical combat, visual maps, full equipment rules, leveling, and spell
  systems are intentionally not implemented.
- The monster importer currently depends on an external PDF reader being
  available in the runtime used for the import command. The core app runtime
  remains standard-library based.
- Monster-manual appendix parsing is now available as separate tooling output,
  but it still does not drive encounter generation inside the app or build
  higher-level encounter indexes yet.
- ADD Bestiary import Milestone 1 intentionally does not solve multi-column or
  repeated-stat-block variant monsters yet. Those entries are deferred and
  should be handled in a later milestone after more parser review.
- A few real imported monsters may still need follow-up normalization where
  the PDF formatting interrupts fields in unusual ways. The current validated
  report is down to one remaining common-field gap: `Worm, Furnace` missing a
  recoverable `INTELLIGENCE` value in the extracted text.
- The appendix catalog intentionally keeps unresolved rows for later review
  rather than guessing IDs. After the v0.8.10 cleanup pass, 395 unresolved
  rows remain. The new unmatched-review report currently splits them between
  likely encoding/OCR variants and appendix-only-or-missing-catalog names.
- The source registry intentionally describes local source expectations without
  committing the actual PDFs. Missing optional active files should be treated
  as setup notes, not importer regressions, unless a later milestone marks a
  source as required.
- `data/import_sources/` remains intentionally untracked and should continue to
  hold local-only source PDFs rather than versioned import assets.
- Save compatibility is actively maintained for v0.8.4+ data. Much older
  pre-v0.8.4 save experiments are no longer treated as a guaranteed migration
  target for new milestones.
- The large name datasets and mutable `data/saves/worlds.db` are tracked, making
  the repository larger and causing save activity to modify a versioned file.
- Tests use `unittest`; `pytest` is optional and not a project dependency.
- The interface is functional but remains a text-oriented Tkinter prototype.

## Next candidate goals

1. Use the new source registry and validation layer as the gate for Step 2:
   continue the monster importer baseline without changing the broader domain
   roadmap yet.
2. Place the user-provided ADD Bestiary PDF at the documented import_sources
   path and run the new importer to measure real accepted versus deferred
   monsters before tackling multi-variant parsing.
3. Use the new JSON import preview path to test a second monster source with a
   small common-monster sample before attempting a broader merged catalog.
4. Review the remaining 395 unmatched appendix references and decide whether
   the next follow-up should widen the monster catalog, improve the core
   stat-block importer, or add a carefully reviewed manual alias layer for
   appendix-only names before any app-facing use.
5. Optionally revisit the one remaining `Worm, Furnace` intelligence gap only
   if another extraction path reveals the missing line without special-casing
   the record.
6. Build the future Bestiary around the new import metadata and protection
   hooks: list/search/filter, source/audit visibility, manual edits, and
   preserved custom overrides.
7. Add app-facing region/rarity-based monster selection only after Bestiary
   patterns and multi-source catalog merge rules are proven stable.
8. Add lightweight inventory actions beyond equipping, such as container-aware
   stash moves, simple drop/store behavior, or clearer repair/condition hooks,
   only if they stay compatible with the current rules-neutral model.
9. Add a small simulated-time helper or preset-driven town-side fast-forward
   flow only if it can reuse the current calendar/downtime framework without
   bloating the GUI.
10. Design later character retirement so retired protagonists can remain in the
   same world as NPCs after the calendar/downtime layer settles.
11. Add GUI-layer guard tests only if a reliable headless Tk/Tcl setup becomes
   available in the local environment.
12. Consider a small seed-copy or seed-regenerate affordance only if players
   actually need more than the current single text entry.
13. Deepen key NPCs with optional world-aware quest hooks before considering
   any broader relationship or faction system.

## Important files and directories

- `main.py` - application entry point
- `app/game_state.py` - generation coordination and active world
- `app/models.py` - dataclasses and older-save compatibility
- `app/calendar.py` - shared date, time, and aging helpers
- `app/downtime.py` - strategic downtime task engine
- `app/key_npcs.py` - key-NPC promotion and faction-phase helpers
- `app/timeline.py` - structured timeline logging and recurring-NPC helpers
- `app/gui.py` - Tkinter interface
- `app/database.py` - SQLite persistence
- `app/table_loader.py`, `app/table_schemas.py` - data validation and fallbacks
- `app/interaction_text.py` - interaction template formatting helpers
- `app/name_generator.py` - cached large-file name generation
- `app/inventory.py` - item catalog and class starting loadouts
- `app/equipment.py` - slot definitions and encumbrance helpers
- `app/generators/` - focused procedural generators
- `data/tables/` - editable JSON content
- `data/tables/interaction_tables.json` - dialogue, encounter, and action text
- `data/tables/downtime_tables.json` - editable downtime task definitions
- `data/tables/key_npc_tables.json` - key-NPC and relationship-phase text
- `data/tables/npc_depth_tables.json` - recurring-NPC placeholder depth text
- `data/names/` - raw and cleaned name datasets
- `data/tables/item_tables.json` - item definitions and starting gear
- `data/saves/worlds.db` - current SQLite save database
- `tools/` - name cleanup and corruption-scrubbing utilities
- `tools/importers/` - monster manual import tooling
- `tools/importers/monster_catalog_import.py` - shared normalization and
  merge-preview helpers for future multi-source monster imports
- `tools/importers/monster_json_importer.py` - dry-run JSON monster import path
- `tools/importers/add_bestiary_importer.py` - ADD Bestiary milestone 1 import
  tooling
- `tools/import_add_bestiary.py` - simple command entry point for the ADD
  Bestiary importer
- `app/monster_catalog.py` - lightweight combined monster loading and
  alphabetical sorting helpers across sources
- `app/source_registry.py` - source registry loading and validation helpers
- `data/catalogs/monsters/monster_appendix_catalog.json` - parsed appendix
  encounter/location rows
- `data/source_registry.json` - editable source registry and expected local
  source paths
- `data/import_reports/monster_appendix_import_report.txt` - appendix importer
  audit report
- `data/import_reports/monster_appendix_unmatched_review.txt` - grouped
  unmatched appendix review artifact
- `tools/validate_sources.py` - source-registry and local path validation
  command
- `tests/test_core.py` - automated test suite
- `tests/test_source_registry.py` - source-registry validation coverage
- `tests/test_stress.py` - stress and illogical-action regression coverage
- `AGENTS.md` - named AI roles and coordinated operating model

## How to update this file

After a successful milestone, inspect the actual repository state, update the
current tag and latest-work summary, adjust features/issues/next goals, and
record the latest verified test count. Do not claim a feature or passing check
without confirming it from current code or command output.
