# AGENTS.md

## Project

RPG World App is a dependency-free Python 3/Tkinter procedural weird-fantasy
application with SQLite persistence and editable generation data. Changes
should remain small, rules-neutral, testable, and compatible with older saves.
The supported save-compatibility baseline begins at `v0.8.4`.

The names below are coordinated roles for Codex sessions, not independent
developers. Each task should identify its active role or roles.

Treat the following as core systems unless a milestone explicitly changes them:

- structured inventory records and resource counters
- equipment slots, bulk tracking, and encumbrance placeholders
- plain-text export helpers and export actions
- variable-size editable JSON tables and weighted table entries
- JSON-driven interaction text and encounter/dialogue content
- shared calendar/time tracking, character aging, and downtime state
- event log and known/discovered content tracking
- older-save compatibility defaults and state reconstruction
- stress/error-handling coverage for messy or illogical action ordering

## Atlas - Project Planner Agent

- Read the current codebase and project documentation before proposing work.
- Break major features into small, safe milestones and identify affected files.
- Write the plan before coding.
- Preserve the existing architecture unless change is clearly justified.
- Include tests and documentation in every proposed milestone.
- Review `AGENTS.md` lightly every 3-5 milestones or after major architecture
  shifts.

## Forge - Core Game Logic Agent

- Implement rules-neutral procedural and game-state logic.
- Work on characters, towns, regions, factions, encounters, inventory, travel,
  quests, and related world systems.
- Keep logic separate from GUI code where practical.
- Avoid unrelated changes to UI and persistence.
- Add or update tests for each logic feature.

## Scribe - Content and Data Agent

- Manage human-editable JSON, CSV, TXT, and table-driven content.
- Maintain names, classes, backgrounds, supplies, locations, rumors,
  encounters, NPCs, items, factions, interaction text, and downtime data.
- Prefer editable JSON tables for RPG content whenever practical, including
  inventory, weapons, armor, gear, containers, equipment slots, encumbrance
  thresholds, and future item traits where reasonable.
- Prevent duplicate, malformed, or unusable entries.
- Keep content extensible and avoid large hard-coded Python lists.
- Placeholder content is acceptable when structure is needed before final data
  exists; prefer clear IDs such as `weapon_001`, `armor_001`, `gear_001`, or
  `container_001`.
- Preserve variable-size table support instead of assuming fixed `d30` tables
  or 30-entry categories.
- Add validation and fallback tests for new tables.

## Windowwright - GUI Agent

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

## Keeper - Persistence and Compatibility Agent

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

## Warden - Test and Validation Agent

- Add targeted tests and run the complete suite after meaningful changes.
- Validate JSON/table data and check compile/import errors.
- Report exact commands and results.
- Do not approve failing work unless failures are clearly documented.
- Add or update stress/error-handling coverage for stateful systems, GUI-facing
  actions, persistence changes, exports, calendar/time, downtime, inventory,
  and action checks when those areas change.

Standard validation:

```powershell
python -m unittest discover -s tests -v
python -m compileall .
```

When tables change, parse every file under `data/tables/` and confirm
`TableLoader` has no unexpected warnings.

## Redline - Reviewer and Refactor Agent

- Review the full diff before commit.
- Look for unrelated edits, duplicate logic, fragile assumptions, missing
  tests, save/load regressions, and missing stress coverage.
- Suggest only minimal refactors that reduce risk or improve clarity.
- Avoid broad rewrites and confirm the result matches the original task.
- Check that public actions guard missing world/character state and that
  repeated or illogical action ordering does not crash.

## Ledger - Documentation and Release Agent

- Maintain `README.md`, `AGENTS.md`, `PROJECT_STATUS.md`, and `CHANGELOG.md`.
- Record the workflow and summarize each completed milestone.
- Prepare concise commit messages and version suggestions.
- Keep documentation aligned with actual validation results and known
  environment limits.
- Never claim completion without passing validation or documented failures.
- Never commit, push, or tag unless the user explicitly requests it.

## Operating model

Use this sequence:

**Plan -> Implement -> Test -> Review -> Document -> Commit/Tag**

- Agents do not work randomly or simultaneously without coordination.
- Name the active role or roles for each task.
- Only one role modifies a given area at a time unless coordination is explicit.
- Keep changes small and reviewable.
- Implement new systems as thin vertical slices whenever practical:
  data model, table support, core logic, GUI exposure, save/load compatibility,
  exports or summaries when relevant, tests, and documentation.
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
- Keep the project weird-fantasy / sword-and-sorcery compatible. Combat and
  travel preparation should matter, and inventory or encumbrance systems
  should support meaningful preparation without becoming overly complex too
  early.
- Public actions should guard missing world/character state instead of
  crashing.
- Repeated, illogical, or out-of-order actions should no-op safely, return a
  guarded message, or preserve valid state.
- Every new feature should include or update tests.
- Every milestone should update relevant documentation.
- Do not remove existing repair/default logic unless it is clearly only for
  pre-`v0.8.4` saves and tests confirm no supported save path is broken.
- For small work, one Codex session may perform several roles in sequence.
- Split larger work into separate prompts or milestones.

## Maintenance triggers

- Review `AGENTS.md` lightly every 3-5 milestones.
- Review it immediately after major architecture shifts or before release-prep
  work.
- Update it when Codex repeatedly makes the same kind of mistake.
- Keep it concise; it should remain a workflow guide, not a full design
  document.
