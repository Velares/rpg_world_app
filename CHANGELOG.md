# Changelog

Notable project milestones are recorded here. Dates are omitted where the Git
history is the more reliable source.

## Unreleased - monster import roadmap realignment

- Documented the revised long-term monster-import direction: all approved
  monster sources should eventually feed one normalized master monster
  catalog rather than remaining only as permanent side-pack outputs.
- Clarified that current source-specific parsers, previews, and content-pack
  outputs are staging layers that preserve raw source data and provenance
  before a later normalization/merge step.
- Documented a proposed standard normalized monster field set covering core
  combat/stat data, provenance, raw source text, placeholder tracking,
  mapping confidence, review state, and future user corrections.
- Recorded placeholder and mapping policy so missing fields do not block
  imports, guessed values stay flagged, aliases can map into shared fields,
  and ambiguous source text remains reviewable.
- Recorded future review/correction and deduplication expectations: keep
  source variants distinct, support canonical grouping later, and avoid silent
  overwrite while multiple sources are still being normalized.
- Documented combat-model roadmap: a modular, rules-neutral d20 OSR-style combat
  resolution layer; inspection of earlier combat/social solo-play spreadsheets
  for reusable logic; and a future combat test/stress harness for balance
  auditing.

## v0.8.23 - Controlled Monster Classification Dropdowns and Suggestions

- Added `tools/report_table_inventory.py` to scan data/table/config files and
  produce `data/import_reports/table_inventory.json` and
  `data/import_reports/table_inventory_report.txt`.
- Inventory report groups files by domain (character generation, NPC generation,
  settlement/location generation, encounters/leads/adventure content,
  inventory/equipment/resources, interaction/dialogue/downtime text,
  monster catalogs/import previews/review data, source registry,
  future classification tables, and other/unknown).
- Added `data/tables/monster_classification_options.json` with controlled lists for
  `monster_types`, `environments`, `terrains`, `regions`, and `affinity_values`.
- Added `data/configs/monster_classification_affinities.json` with
  `schema_version`, `affinity_values`, and `monster_type_affinities` seeded for
  undead, aquatic, amphibian, aerial, construct, demon, devil, elemental, plant,
  fungus, insect, arachnid, giant, and humanoid.
- Added `app/monster_classification.py` with helpers to load and validate the
  options and affinities tables, plus `dropdown_values_for_field` for dropdown
  behavior (select known option, default to `unknown`, preserve unknown values).
- Added `tools/importers/monster_classification_suggestions.py` to generate
  conservative best-guess classification suggestions for missing `environment`,
  `terrain`, `region`, and `monster_type` fields based on affinity rules and
  keyword hints.
- Suggestion outputs:
  - `data/import_reports/monster_classification_suggestions.json`
  - `data/import_reports/monster_classification_suggestions_report.txt`
- Suggestions never overwrite existing corrections, live catalogs, or generated
  previews; they are intended for review before manual application.
- Added `Classification Suggestions` as a Monster Editor sub-category and a new
  `view_classification_suggestions` method in `app/gui.py`.
- Converted `environment`, `terrain`, `region`, and `monster_type` fields in the
  Normalized Monster Review → Correct Fields dialog to editable Comboboxes.
- Added `tests/test_table_inventory_and_classification.py` with 26 focused tests
  for inventory, options, affinities, dropdown values, and the suggestion tool.
- Updated `tests/test_editor_hub.py` for the new Classification Suggestions
  sub-category and related GUI method.
- Confirmed no live catalog JSON modification, no normalized preview file
  modification, no staging preview modification unless regenerated, no importer
  behavior changes, no record merging, and no PDFs added.
- Generated current reports: table inventory (29 files across 10 domains) and
  classification suggestions (1320 suggestions across 487 records).
- Raised the validated suite to 363 passing `unittest` tests.

## v0.8.22 - Combat-Ready Monster Projection

- Added `tools/importers/monster_combat_projection.py` to build a non-live
  combat-ready projection from the corrected staging preview.
- Output files:
  - `data/import_reports/monster_combat_projection.json`
  - `data/import_reports/monster_combat_projection_report.txt`
- Each projection record includes identity/provenance, raw combat fields, parsed
  models (AC, HD, movement, attacks, damage, morale), `hit_points_formula`,
  conservative `armor_class_type`, `combat_tags`, `tag_sources`, and a
  `projection_status` (`ready`, `missing_combat_fields`, `parse_warning`,
  `needs_review`) with `projection_warnings`.
- Parsers are conservative: damage supports `NdN`, `N-N`, and comma-separated
  multi-attack lists; hit dice supports `N`, `N+M`, `N-M`, and `NdN`; movement
  extracts numeric values; AC parses integers and infers descending only inside the
  classic 0-9 band. Unparseable values become model `null` and warnings.
- Added `Combat Projection Preview` as a Monster Editor sub-category and a new
  `view_combat_projection_preview` method in `app/gui.py`.
- Added `tests/test_monster_combat_projection.py` with 17 focused tests and
  updated `tests/test_editor_hub.py`.
- Confirmed no live catalog JSON modification, no normalized preview file
  modification, no staging preview modification unless regenerated, no importer
  changes, and no record merging.
- Generated a current combat projection with 521 records (268 MandBmaster, 253
  Megadungeon), 220 ready and 301 needing review.
- Raised the validated suite to 331 passing `unittest` tests.

## v0.8.21 - Staged Corrected Monster Dataset Preview

- Added `tools/importers/monster_corrected_staging_preview.py` to build a
  non-live corrected monster dataset from MandBmaster and Megadungeon normalized
  previews and the saved correction store.
- Output files:
  - `data/import_reports/monster_corrected_staging_preview.json`
  - `data/import_reports/monster_corrected_staging_preview_report.txt`
- Each staged record includes `original`, `corrections`, `effective`,
  `source_provenance`, and `review_metadata` sections. Corrections are applied as
  an overlay; original values are preserved.
- The tool preserves source variants, does not merge records, does not modify
  generated previews, and does not modify live catalog JSON. Canonical group
  decisions are included as metadata/context only.
- Report text includes counts, correction status, most-corrected fields, missing
  and placeholder counts, a no-master-catalog warning, and sample records.
- Added `Corrected Staging Preview` as a sub-option in the Monster Editor hub
  and a new `view_corrected_staging_preview` method in `app/gui.py` that
  regenerates the preview and displays the report.
- Added `tests/test_monster_corrected_staging_preview.py` with 17 focused tests.
- Updated `tests/test_editor_hub.py` for the new sub-category and GUI method.
- Confirmed no live catalog JSON modification, no normalized preview file
  modification, no importer changes, and no record merging.
- Generated a current staging preview with 521 records (268 MandBmaster, 253
  Megadungeon).
- Raised the validated suite to 313 passing `unittest` tests.

## v0.8.20 - Direct Monster Editor Action

- Added a direct, clearly visible **Monster Editor** shared action in
  `app/gui.py` so it appears as a first-class sidebar button.
- Mapped the new action directly to `view_monster_editor` in the sidebar command
  map.
- Kept the existing **Editors** hub intact; its Monster Editor entry still routes
  to the same Monster Editor sub-hub.
- Updated `app/editor_hub.py` summary text so the Monster Editor hub and Editors
  hub clearly list the available categories and explain:
  - Canonical Candidate Review for approve/reject decisions on same-monster matches
  - Normalized Monster Review for inspecting imported records and correcting fields
  - Corrections stored separately without modifying source imports or live catalog
- Updated `tests/test_editor_hub.py` to verify the direct Monster Editor action,
  command-map mapping, and that the Editors hub and placeholder messages remain
  intact.
- Confirmed no live catalog JSON modification, no importer changes, and no record
  merging.
- Raised the validated suite to 295 passing `unittest` tests.

## v0.8.19 - Normalized Monster Field Correction Storage

- Added correction-store helpers to `app/monster_editor.py`:
  `load_corrections`, `save_corrections`, `get_record_correction`,
  `set_field_correction`, `set_record_status`, `apply_corrections`,
  `format_corrected_field`, `format_corrected_record`, and
  `correction_summary_text`.
- Correction store path:
  `data/import_reviews/monster_normalized_field_corrections.json`.
- Correction schema version 1 with `source_reports`, `schema_version`, and a
  `corrections` object keyed by normalized monster ID.
- Per-field correction support for `corrected_value`, `previous_value`, `notes`,
  `updated_at`, and `reviewer`. Record-level support for `record_status`
  (`needs_review`, `corrected`, `approved`) and `record_notes`.
- Missing correction files load as empty corrections; malformed files raise
  `ValueError` and are never overwritten by the load path. Saves are atomic.
- Invalid correctable field names are rejected with `ValueError`.
- Corrections apply as an overlay to the displayed record; original generated
  preview records are never modified.
- Updated `app/gui.py` so Normalized Monster Review loads the correction store,
  displays a correction summary, highlights corrected fields, and adds a
  `Correct Fields` button that opens an `Edit Corrections` dialog. The dialog
  shows every correctable field with its original value, an editable value, and
  a notes entry, plus record status and record notes.
- Added a reusable `set_index_action_button` helper for view-specific index-frame
  actions.
- Added 18 focused correction tests to `tests/test_monster_editor.py` and
  updated `tests/test_editor_hub.py` for the new dialog method.
- Confirmed no generated preview JSON modification, no live catalog JSON
  modification, no importer changes, and no record merging.
- Raised the validated suite to 293 passing `unittest` tests.

## v0.8.18 - Normalized Monster Review

- Added `app/monster_editor.py` with helpers to load the MandBmaster and
  Megadungeon normalized monster preview files without merging them.
- Added `load_normalized_preview`, `load_all_normalized_previews`,
  `build_normalized_monster_rows`, `format_normalized_monster`, and
  `review_summary_text` for read-only review of normalized records.
- Extended `app/editor_hub.py` so the Monster Editor entry has two sub-options:
  Canonical Candidate Review and Normalized Monster Review.
- Updated `app/gui.py` with `view_monster_editor` and
  `view_normalized_monster_review` methods. The normalized review screen lists
  all source records and displays normalized fields, missing/placeholder markers,
  low-confidence markers, review notes, raw stat blocks, and raw text previews.
- Added clear warnings that the screen is review-only and does not modify source
  records or catalogs.
- Added graceful handling for missing or malformed normalized preview files.
- Added `tests/test_monster_editor.py` with focused coverage for loading both
  preview files, combining records, preserving source variants, building display
  rows, missing/placeholder/low-confidence highlighting, and live-catalog
  preservation.
- Updated `tests/test_editor_hub.py` for the new monster editor sub-categories.
- Confirmed no live catalog JSON modification, no importer changes, and no
  record merging.
- Raised the validated suite to 275 passing `unittest` tests.

## v0.8.17 - Editors hub

- Added `app/editor_hub.py` with the canonical editor category list and
  placeholder messages for not-yet-implemented editors.
- Added an `Editors` shared action in `app/gui.py` that opens a list/detail hub.
- Editor categories: Monster Editor / Monster Import Review, NPC Editor,
  PC Editor, Item Editor, Spell Editor.
- Wired the existing `Monster Import Review` (with persistent decisions) as the
  first live editor entry point.
- Placeholder editors display clear "Not implemented yet" messages with their
  intended future purpose instead of failing silently.
- Added `tests/test_editor_hub.py` with focused coverage for categories,
  placeholders, summary text, and live-catalog preservation.
- Confirmed no live catalog JSON modification, no importer changes, and no
  record merging.
- Raised the validated suite to 258 passing `unittest` tests.

## v0.8.16 - persistent monster canonical-group review decisions

- Added separate decision storage at
  `data/import_reviews/monster_canonical_group_decisions.json`.
- Added `load_decisions`, `save_decisions`, `get_decision`, `set_decision`, and
  `format_decision_block` helpers in `app/monster_import_review.py`.
- Decisions are written atomically via a temp file and rename; malformed files
  fail gracefully and are never overwritten by the load path.
- Updated `app/gui.py` so the `Monster Import Review` screen supports
  approve/reject/needs-review choices and free-text notes per candidate group.
- The candidate list shows saved decision status (e.g., `[APPROVED]`).
- Added focused tests in `tests/test_monster_import_review.py` for missing,
  valid, and malformed decision files; save behavior; notes persistence; and
  live-catalog preservation.
- Raised the validated suite to 249 passing `unittest` tests.

## v0.8.15 - cross-source canonical monster group candidates

- Added `tools/importers/monster_canonical_group_candidates.py` to generate a
  review-only, non-merging comparison of MandBmaster and Megadungeon
  normalized monster previews.
- Implemented deterministic, conservative matching: exact name, normalized-key
  (case/punctuation/spacing), singular/plural, parenthetical, and name
  similarity with optional `armor_class`/`hit_dice`/`movement`/`xp` field match.
- Emitted `data/import_reports/monster_canonical_group_candidates.json` and
  `data/import_reports/monster_canonical_group_candidates_report.txt` as
  review-only outputs with 8 candidate groups (1 high, 4 medium, 3 low).
- Preserved every source variant in each candidate group; set all groups to
  `review_status='needs_review'` and reserved a `user_decision` field.
- Added `tests/test_monster_canonical_group_candidates.py` with focused
  coverage for exact, case/punctuation, singular/plural, parenthetical, and
  field-similarity matches, plus live-catalog preservation and determinism.
- Confirmed `data/catalogs/monsters/*.json` is unchanged and no master monster
  catalog is created or modified by the tool.
- Raised the validated suite to 225 passing `unittest` tests.

## v0.8.14 - monster importer readiness and source-aware tooling

- Added reusable source-registry lookup helpers so importer tooling can load
  registered source metadata and resolved expected paths without duplicating
  validation logic.
- Added canonical monster source IDs plus a shared resolver in
  `tools/importers/monster_manual_schema.py` for the combined manual PDF and
  the ADD Bestiary source.
- Made `tools/importers/monster_manual_importer.py`,
  `tools/importers/monster_appendix_importer.py`,
  `tools/importers/monster_json_importer.py`, and
  `tools/importers/add_bestiary_importer.py` source-registry aware while
  preserving direct path override support.
- Standardized monster importer reports so they include importer name, source
  ID, source title, source status, source path mode, input/output paths, and
  next recommended action text.
- Added `tools/monster_import_status.py` as a practical readiness command for
  registered monster sources, present/missing local files, recommended import
  commands, and primary output paths.
- Preserved dry-run safety for JSON import preview while allowing a registered
  source ID to flow through `import_metadata.source_id`.
- Added focused readiness tests for registry lookup helpers, source-aware
  manual/appendix/JSON/ADD behavior, inactive-source blocking, and the new
  monster import status helper.
- Raised the validated suite to 172 passing `unittest` tests while
  `python -m compileall .` and `python tools/validate_sources.py` continue to
  pass.

## v0.8.13 - source registry and source-path validation

- Added an editable source registry at `data/source_registry.json` as Step 1
  of the 8-step source/import roadmap.
- Recorded the current durable source policy in machine-readable form,
  including the `Advanced Labyrinth Lord` primary baseline,
  `Labyrinth Lord Revised Edition` core/basic reference, `OSE` as
  comparison-only, inactive removed rules PDFs, the stable
  `mandbmaster.pdf` monster source, the separate ADD Bestiary source path, and
  future domain placeholders.
- Added `app/source_registry.py` for reusable registry loading, validation,
  allowed domain/status checks, duplicate `source_id` detection, and local
  expected-path presence reporting without requiring source PDFs to be
  committed.
- Added `tools/validate_sources.py` for a lightweight CLI report covering total
  sources, domain/status grouping, present files, missing expected files,
  warnings, and errors.
- Kept missing optional or inactive local PDFs from failing normal validation,
  while reserving hard failures for malformed registry data or explicitly
  required active files.
- Added focused `unittest` coverage for valid registry loading, duplicate IDs,
  missing required fields, unknown domains, inactive/optional missing-path
  handling, required active missing-path errors, summary reporting, and future
  domain placeholders.
- This milestone does not import new content and does not change existing
  monster, appendix, JSON-import, or ADD importer behavior.

## v0.8.12 - ADD Bestiary import milestone 1

- Added `tools/import_add_bestiary.py` and
  `tools/importers/add_bestiary_importer.py` for Milestone 1 support aimed at
  the user-provided *Adventures Dark and Deep Bestiary* PDF.
- Scoped the ADD importer to actual PDF pages 4 through 438 only, explicitly
  skipping front matter, appendices, and index pages by actual PDF page number
  rather than printed page numbers.
- Added raw page text extraction to
  `import_work/adventures_dark_and_deep_bestiary/raw_pages/page_###.txt`.
- Added conservative single-entry parsing that only accepts records with the
  expected ADD stat labels plus at least one prose section, while rejecting
  unsupported repeated-stat-block entries as
  `multi_variant_stat_block_not_supported_yet`.
- Added draft content-pack output targets for
  `data/content_packs/imported/adventures_dark_and_deep_bestiary/pack.json`
  and `monsters.json`.
- Added lightweight monster-catalog helpers for loading the core monster
  catalog beside imported monster packs and returning a combined alphabetical
  monster view without overwriting same-name records from different sources.
- Added validation coverage for imported ADD pack structure and tests for
  single-entry parsing, multi-variant rejection, page-range behavior, stable
  IDs, combined sorting, and same-name/different-source warnings.
- Added `.gitignore` coverage for local-only `import_work/` output and
  `data/import_sources/`.
- Raised the validated suite to 152 passing `unittest` tests.

## v0.8.11 - monster catalog multi-source import foundation

- Added a small shared monster-catalog import layer for canonical JSON
  normalization, source metadata conventions, and conservative merge-preview
  behavior without changing the stable PDF or appendix importers.
- Added `tools/importers/monster_json_importer.py` for dry-run JSON monster
  imports with a text report plus a JSON preview artifact before any catalog
  write is attempted.
- Added source metadata conventions for imported records through optional
  `import_metadata` fields such as `source_id`, `source_name`, `source_type`,
  `source_file`, `source_page`, `source_record_id`, `import_method`,
  `import_version`, `original_name`, `normalized_name`, warnings, and notes.
- Added conservative merge decisions for exact duplicates, would-add,
  would-update, would-conflict, and protected-conflict cases instead of
  silently overwriting existing catalog entries.
- Added lightweight manual/custom protection rules keyed off
  `custom_record`, `manual_override`, `protected_fields`, and manual/custom
  source types to prepare for later Bestiary editing without building the full
  GUI yet.
- Kept the default JSON import path non-destructive: explicit write mode only
  applies safe additions, while updates and conflicts remain report-only for
  later review.
- Preserved the current monster-manual catalog and appendix catalog workflows
  unchanged while extending importer tests to cover JSON happy path, malformed
  records, metadata preservation, duplicate detection, conflict reporting, and
  manual/custom protection.
- Raised the validated suite to 146 passing `unittest` tests.

## v0.8.10 - appendix unmatched review and normalization pass

- Added a conservative appendix normalization pass that keeps the standalone
  appendix importer separate from the stable monster stat-block importer.
- Added general matching improvements for appendix references through broader
  normalized lookup variants, including article stripping, simple singular
  handling, parenthetical-descriptor normalization, and tightly limited
  one-edit typo recovery when the result is unique.
- Reduced unmatched appendix references from 413 to 395 without adding
  monster-specific hard-coded mappings.
- Preserved truly unresolved appendix references as unmatched instead of
  guessing, and kept ambiguous handling available when a future normalization
  rule would hit more than one catalog target.
- Added an `Unmatched Reference Review` section to the appendix import report
  plus a separate `monster_appendix_unmatched_review.txt` audit artifact with
  grouped repeated names, category counts, pages, and example tables.
- Added focused appendix importer tests for grouped unmatched reporting,
  context preservation, and the new conservative normalization rules.
- Reran both importers successfully: the monster catalog remains at 268 real
  records with the same one unresolved `WORM, FURNACE` intelligence gap, while
  the appendix catalog remains at 2,981 rows with 2,586 matched references,
  395 unmatched references, and 0 ambiguous references.
- Raised the validated suite to 139 passing `unittest` tests.

## v0.8.9 - monster appendix parser milestone 1

- Added `tools/importers/monster_appendix_importer.py` as a separate appendix
  parsing path so terrain, rarity, and level appendix data can be extracted
  without destabilizing the stable monster stat-block importer.
- Added shared schema defaults for appendix page ranges plus appendix catalog
  and report output paths.
- Added conservative appendix parsing for `Appendix B: Monsters by Level`,
  `Appendix C: Monsters by Rarity`, and `Appendix D: Monsters by Terrain Type`
  across both books of the combined PDF.
- Preserved actual PDF page numbers, section titles, table titles, terrain /
  climate / region context, roll ranges, raw row text, and per-row match state
  in the generated appendix catalog.
- Added conservative monster-name matching against the existing
  `monster_catalog.json`, including simple punctuation/case normalization and
  safe comma-form matching such as `Wax Golem` -> `GOLEM, WAX`.
- Kept unmatched appendix rows instead of guessing, and reported unmatched and
  ambiguous rows separately in `monster_appendix_import_report.txt`.
- Added focused appendix importer tests for section detection, wrapped heading
  merging, roll ranges, context carry-forward, matching behavior, unmatched
  preservation, and output-file generation.
- Reran the stable monster stat importer and preserved the validated v0.8.8
  baseline of 268 parsed monster records, zero warnings, and one remaining
  unresolved common-field gap for `WORM, FURNACE` intelligence.
- The current local appendix rerun against `data/import_sources/mandbmaster.pdf`
  produced 2,981 appendix records with 2,568 matched references, 413
  unmatched references, and 0 ambiguous matches.
- Raised the validated suite to 137 passing `unittest` tests.

## v0.8.8 - monster importer normalization pass

- Tightened monster-manual stat parsing for real-entry spillover after the
  Milestone 1 header and page-marker cleanup settled.
- Added a small unmodeled-label guard so lines such as `CHANCE OF:`,
  `Magic Use:`, `Sleeping:`, and similar side labels no longer leak into
  structured fields like `ALIGNMENT`.
- Added targeted recovery for page-top orphaned stat lines when PDF extraction
  separates late stat fields from a monster heading but the nearby prose still
  clearly belongs to that same monster.
- Fixed `WYRM, KURGAN` so `ALIGNMENT` is no longer polluted by the following
  chance-of-use lines.
- Recovered `Dragon, Crustacean` intelligence, alignment, level/xp, and full
  treasure continuation from split page text without reintroducing false
  header records.
- Kept `Worm, Furnace` honestly reported with a missing `INTELLIGENCE` field
  because the extracted PDF text still does not provide a recoverable value.
- Added focused importer regression coverage for the wyrm spillover case, the
  orphaned crustacean-dragon stat continuation case, and the intentionally
  unresolved furnace-worm case.
- The current validated full-PDF rerun still produces 268 parsed monsters and
  111 rejected candidate headings, with no false single-letter records, no
  running-header records, no duplicate IDs, and one remaining missing common
  field in the report.
- Raised the validated suite to 130 passing `unittest` tests.

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
- Tightened heading detection and page cleanup so running headers, letter
  markers, dangling fragments, and standalone page-number lines are rejected
  before catalog generation instead of becoming false monsters.
- Updated the import report to distinguish candidate headings, rejected header
  candidates, parsed monster records, missing expected fields, and duplicate
  IDs among real records only.
- Kept the work tooling-only: no save/load schema changes, no app-facing
  encounter generation, no appendix parsing, and no hard-coded monster data in
  application logic.
- The current local full-PDF rerun now produces 268 parsed monsters with 111
  rejected candidate headings, no false single-letter or running-header
  records in the catalog, and no duplicate IDs from header noise.
- Raised the validated suite to 123 passing `unittest` tests.

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
