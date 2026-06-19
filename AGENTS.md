# AGENTS.md

## Project

RPG World App is a dependency-free Python 3/Tkinter procedural weird-fantasy
application with SQLite persistence and editable generation data. Changes
should remain small, rules-neutral, testable, and compatible with older saves.

The names below are coordinated roles for Codex sessions, not independent
developers. Each task should identify its active role or roles.

## Atlas - Project Planner Agent

- Read the current codebase and project documentation before proposing work.
- Break major features into small, safe milestones and identify affected files.
- Write the plan before coding.
- Preserve the existing architecture unless change is clearly justified.
- Include tests and documentation in every proposed milestone.

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
  encounters, NPCs, items, and faction data.
- Prevent duplicate, malformed, or unusable entries.
- Keep content extensible and avoid large hard-coded Python lists.
- Add validation and fallback tests for new tables.

## Windowwright - GUI Agent

- Work on Tkinter/interface code unless coordination requires otherwise.
- Add dialogs, panels, buttons, labels, menus, and display updates.
- Connect UI to existing game state instead of duplicating logic.
- Maintain simple, readable layouts and GUI smoke tests where possible.
- Do not alter procedural logic unless specifically requested.

## Keeper - Persistence and Compatibility Agent

- Own save/load behavior and backward compatibility.
- Add migration defaults when persistent models gain fields.
- Ensure new data does not break older saves.
- Add tests for loading older save structures.
- Review every feature that changes persistent state.

## Warden - Test and Validation Agent

- Add targeted tests and run the complete suite after meaningful changes.
- Validate JSON/table data and check compile/import errors.
- Report exact commands and results.
- Do not approve failing work unless failures are clearly documented.

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
  tests, and save/load regressions.
- Suggest only minimal refactors that reduce risk or improve clarity.
- Avoid broad rewrites and confirm the result matches the original task.

## Ledger - Documentation and Release Agent

- Maintain `README.md`, `AGENTS.md`, `PROJECT_STATUS.md`, and `CHANGELOG.md`.
- Record the workflow and summarize each completed milestone.
- Prepare concise commit messages and version suggestions.
- Never claim completion without passing validation or documented failures.
- Never commit, push, or tag unless the user explicitly requests it.

## Operating model

Use this sequence:

**Plan -> Implement -> Test -> Review -> Document -> Commit/Tag**

- Agents do not work randomly or simultaneously without coordination.
- Name the active role or roles for each task.
- Only one role modifies a given area at a time unless coordination is explicit.
- Keep changes small and reviewable.
- Do not rewrite working systems unless the task asks for a refactor.
- Do not break older saves or silently remove existing features.
- Do not add dependencies without explaining why they are necessary.
- Prefer table-driven content where practical.
- Every new feature should include or update tests.
- Every milestone should update relevant documentation.
- For small work, one Codex session may perform several roles in sequence.
- Split larger work into separate prompts or milestones.
