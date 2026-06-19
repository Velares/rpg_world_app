# AGENTS.md

## Project

RPG World App is a dependency-free Python 3/Tkinter procedural weird-fantasy
application. It generates a connected settlement, NPC roster, locations,
dungeon, wilderness encounters, and adventure hook, then supports a lightweight
exploration loop with SQLite save/load.

## Working principles

- Prefer small, stable, testable changes over broad rewrites.
- Preserve save/load compatibility, including older saves. Add defaults or
  migration logic when model fields change.
- Keep setting and generator content in editable JSON under `data/tables/`
  where practical.
- Do not hard-code large content lists in Python. Large personal-name datasets
  belong in newline-delimited files under `data/names/`.
- Keep generators rules-neutral and focused. Avoid committing the project to a
  full combat, magic, leveling, or economy ruleset without explicit direction.
- Keep Tkinter changes simple, readable, and consistent with the existing
  sidebar, index list, text display, status area, and guarded error handling.
- Reuse the existing dataclasses, `GameState`, `TableLoader`, `NameGenerator`,
  and focused modules under `app/generators/`.
- Never commit, push, or create a version tag unless the user explicitly asks.

## Validation

Before considering work complete, run:

```powershell
python -m unittest discover -s tests -v
python -m compileall .
```

If JSON tables change, parse every file in `data/tables/` and confirm
`TableLoader` reports no unexpected warnings. For GUI changes, perform a brief
Tkinter smoke test when the environment allows it.

## Useful future goals

- Expand NPC backgrounds, personalities, relationships, and conversation leads.
- Deepen town/location generation and ownership without breaking references.
- Add more varied encounter tables and noncombat resolutions.
- Improve inventory and equipment handling.
- Deepen player background/personality tables without attaching new mechanics.
- Add world, character, and event-log export features.

Do not assume these are approved tasks; they are candidate directions only.
