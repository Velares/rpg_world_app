# AGENTS.md

RPG World App is a dependency-free Python 3/Tkinter procedural weird-fantasy
application with SQLite persistence and editable generation data. Changes
should remain small, rules-neutral, testable, and compatible with older saves.
The supported save-compatibility baseline begins at `v0.8.4`.

## Authority boundary

- ChatGPT/project owner controls process design, gameplay design, rules design,
  source priority, and product direction.
- Devin handles implementation and may suggest improvements for security,
  stability, efficiency, maintainability, test coverage, and code organization.
- Do not describe Devin as the source of product/gameplay design decisions.

## Project roles (workflow lenses)

The names below are coordinated workflow lenses for implementation sessions,
not independent developers. Each task may identify one or more active lenses.

### Atlas - Project Planner

- Read the current codebase and project documentation before proposing work.
- Break major features into small, safe milestones and identify affected files.
- Write the plan before coding.
- Preserve the existing architecture unless change is clearly justified.
- Include tests and documentation in every proposed milestone.
- Review `AGENTS.md` lightly every 3-5 milestones or after major architecture
  shifts.

### Forge - Core Game Logic

- Implement rules-neutral procedural and game-state logic.
- Work on characters, towns, regions, factions, encounters, inventory, travel,
  quests, and related world systems.
- Keep logic separate from GUI code where practical.
- Avoid unrelated changes to UI and persistence.
- Add or update tests for each logic feature.

### Scribe - Content and Data

- Manage human-editable JSON, CSV, TXT, and table-driven content.
- Maintain names, classes, backgrounds, supplies, locations, rumors,
  encounters, NPCs, items, factions, interaction text, and downtime data.
- Prefer editable JSON tables for RPG content whenever practical.
- Prevent duplicate, malformed, or unusable entries.
- Keep content extensible and avoid large hard-coded Python lists.
- Placeholder content is acceptable when structure is needed before final data
  exists; prefer clear IDs such as `weapon_001`, `armor_001`, `gear_001`, or
  `container_001`.
- Preserve variable-size table support instead of assuming fixed `d30` tables.
- Add validation and fallback tests for new tables.

### Windowwright - GUI

- Work on Tkinter/interface code unless coordination requires otherwise.
- Add dialogs, panels, buttons, labels, menus, and display updates.
- Connect UI to existing game state instead of duplicating logic.
- Maintain simple, readable layouts and guarded GUI behavior.
- Prefer testing GUI-facing behavior through public state/helper methods when a
  real Tk root cannot be created.
- Keep the main event/action log system-controlled. Editable player text should
  live in dedicated notes, diary, or other player-facing systems instead.
- Do not claim a Tkinter smoke test passed if the environment cannot find a
  usable `init.tcl`; report the limitation clearly instead.
- Do not alter procedural logic unless specifically requested.

### Keeper - Persistence and Compatibility

- Own save/load behavior and backward compatibility.
- Add migration defaults when persistent models gain fields.
- Ensure new data does not break supported older saves.
- Protect compatibility for calendar fields, age fields, downtime task state,
  inventory records, equipment slots, encumbrance-related state, event logs,
  and known/discovered content.
- Treat missing newer fields in supported older saves as a normal supported
  path.
- Preserve compatibility with `v0.8.4+` saves.
- Do not spend time preserving pre-`v0.8.4` saves unless a later milestone
  explicitly restores that requirement.
- Add tests for loading older save structures.
- Review every feature that changes persistent state.

### Warden - Test and Validation

- Add targeted tests and run the complete suite after meaningful changes.
- Validate JSON/table data and check compile/import errors.
- Report exact commands and results.
- Do not approve failing work unless failures are clearly documented.
- Add or update stress/error-handling coverage for stateful systems, GUI-facing
  actions, persistence changes, exports, calendar/time, downtime, inventory,
  and action checks when those areas change.

### Redline - Reviewer and Refactor

- Review the full diff before commit.
- Look for unrelated edits, duplicate logic, fragile assumptions, missing
  tests, save/load regressions, and missing stress coverage.
- Suggest only minimal refactors that reduce risk or improve clarity.
- Avoid broad rewrites and confirm the result matches the original task.
- Check that public actions guard missing world/character state and that
  repeated or illogical action ordering does not crash.

### Ledger - Documentation and Release

- Maintain `README.md`, `AGENTS.md`, `PROJECT_STATUS.md`, and `CHANGELOG.md`.
- Record the workflow and summarize each completed milestone.
- Prepare concise commit messages and version suggestions.
- Keep documentation aligned with actual validation results and known
  environment limits.
- Never claim completion without passing validation or documented failures.
- Never commit, push, or tag unless the user explicitly requests it.

## Core durable rules

- Work in small, safe milestones.
- Preserve `v0.8.4+` save compatibility.
- Keep data table-driven where practical.
- Keep GUI logic separated from core logic where practical.
- Include or update tests for every feature.
- Run validation and report exact results.
- Do not commit PDFs.
- Do not commit `data/saves/worlds.db` unless explicitly requested.
- Do not commit generated timestamp churn from unrelated reports.
- Do not modify live catalog JSON unless explicitly requested.
- Do not modify importer behavior except when the task is specifically importer work.
- Do not redirect toward mobile, Windows porting, web/browser work, packaging,
  or combat implementation unless explicitly requested.

## Current import pipeline guardrails

- Continue the import/review/editor pipeline before combat.
- Monsters are the current import focus.
- Active pipeline stages: source registry and path validation, source-specific
  parsers, normalized monster previews, canonical-group candidate report,
  Monster Import Review, persistent canonical-group decisions, Normalized
  Monster Review, persistent field corrections, corrected staging preview,
  combat-ready monster projection.
- Do not merge records into a master catalog until explicitly requested.
- Keep source variants distinct.
- Store corrections and decisions separately from generated import data.
- Keep generated previews, staging outputs, and combat projections separate from
  live catalog JSON.

## Rules and source guidance

- Primary rules baseline: `Advanced Labyrinth Lord`.
- Core/basic reference: `Labyrinth Lord Revised Edition`.
- Comparison/reference only: `OSE`; do not treat it as the main baseline for
  new work.
- `Swords & Wizardry` monster books may be used as monster/content sources
  when present, but the Swords & Wizardry rules PDFs should not be treated as
  active rules references.
- Preserve source records first; do not blindly merge duplicates before source
  variants are preserved.
- Preserve original source title, source page, and raw text when practical.
- Missing fields should not block import. Preserve null/unknown or explicit
  placeholders, record mapping confidence, and flag uncertain fields for review.
- Normalize imported material toward LL terminology later, while keeping
  original source variants instead of overwriting them.
- Keep future importer work separated by content domain (monsters, spells, magic
  items, mundane equipment, treasure tables, modules/keyed locations, generator
  tables, factions/religions/cults).
- Do not build one giant generic PDF importer.
- Detailed source priority and status belong in `PROJECT_STATUS.md` or
  `data/source_registry.json`, not here.

## Do not commit

- PDFs.
- `data/saves/worlds.db` unless explicitly requested.
- Generated timestamp churn from unrelated reports.
- Live catalog JSON unless explicitly requested.

## Validation

Run after meaningful changes:

```powershell
python -m unittest discover -s tests -v
python -m compileall .
python tools/validate_sources.py
python tools/monster_import_status.py
```

Also run any touched importer or report-generation tool when importer/report
outputs change.

When tables change, parse every file under `data/tables/` and confirm
`TableLoader` has no unexpected warnings.

## Operating model

Plan → Implement → Test → Review → Document → Commit/Tag

- Keep changes small and reviewable.
- Implement new systems as thin vertical slices: data model, table support, core
  logic, GUI exposure, save/load compatibility, exports or summaries when
  relevant, tests, and documentation.
- Do not rewrite working systems unless the task asks for a refactor.
- Do not break supported older saves or silently remove existing features.
- Do not add dependencies without explaining why they are necessary.
- Prefer table-driven content where practical.
- Do not hard-code large editable data lists in Python when JSON tables are the
  established project pattern.
- Editable JSON generation tables are not fixed `d30` tables; categories may
  contain any practical non-empty number of entries, and weighted entries must
  keep working.
- Preserve `TableLoader` diagnostics and safe fallbacks when content is
  malformed, missing, or empty.
- Raw local PDF source files belong under `data/import_sources/` and are
  local-only inputs; they should not be committed.
- Keep the project weird-fantasy / sword-and-sorcery compatible.
- Public actions should guard missing world/character state instead of crashing.
- Repeated, illogical, or out-of-order actions should no-op safely, return a
  guarded message, or preserve valid state.
- Every new feature should include or update tests.
- Every milestone should update relevant documentation.
- Do not remove existing repair/default logic unless it is clearly only for
  pre-`v0.8.4` saves and tests confirm no supported save path is broken.
- For small work, one implementation session may perform several roles in
  sequence.
- Split larger work into separate prompts or milestones.

## Maintenance triggers

- Review `AGENTS.md` lightly every 3-5 milestones.
- Review it immediately after major architecture shifts or before release-prep
  work.
- Update it when the same kind of implementation mistake repeats.
- Keep it concise; it should remain a workflow guide, not a full design
  document.
