# RPG World App

Version 0.8.14 is a local, single-player weird-fantasy starting-region generator
with a basic playable exploration loop.
It creates a settlement, its people and locations, a connected cave dungeon,
a wilderness encounter table, and a linked adventure hook. Combat information
emphasizes warning signs, avoidance, negotiation, preparation, morale, and
retreat.

## Requirements

- Python 3.11 or a compatible Python 3 release
- Tkinter (included with standard Windows Python installations)
- No third-party packages and no network connection

## Run

From the `rpg_world_app` directory:

```powershell
python main.py
```

Click **Generate New Region**, then use the viewing buttons to inspect the
region. The optional **Generation Seed** field accepts any text string; leave
it blank to keep normal random generation. **Save World** writes the active
world to SQLite. **Load World** opens a list of prior saves. **Export World**,
**Export Character**, and **Export Event Log** write plain-text `.txt` files
for the current active data. When a world is active, **Start Downtime** and
**Advance Downtime** provide a minimal strategic-play entry point for long-term
tasks. The GUI now splits actions into **Town Mode** and **Adventure Mode** so
recovery, social, downtime, and management play stay separate from travel,
exploration, encounter-facing actions, and field checks. **Journal / World
Recap** gathers the current calendar, character, location, downtime,
resources, leads, quest notes, key NPC notes, faction notes, recent events,
and journal summary into one text view. **Journal Summary** and
**Verbose Timeline** still show condensed and action-by-action campaign
logging without replacing the older event log.
**Character Diary** now opens a third major view with daily, weekly, monthly,
and yearly tabs, allowing ordinary entries to be edited or hidden while major
auto-generated milestones remain protected and accept player notes only.

On first launch, **Generate New Region** is available immediately from the
shared action area, so world generation does not require a mode switch.
Buttons that rely on world or character state are also disabled until their
prerequisites exist, while the underlying handlers remain guarded for safety.

Version 0.2 adds explicit links among town problems, NPCs, locations, rumors,
the dungeon, wilderness signs, and the adventure hook. NPCs, locations, dungeon
rooms, and encounters have selectable list-and-detail views in the GUI.
Generated NPCs, locations, rooms, encounters, and adventure hooks also receive
stable prefixed IDs. These ID-backed relationships survive save/load, while
older saves are upgraded in memory when opened.

Version 0.3 adds travel among town, wilderness, and dungeon; room movement;
searching, conversation, rest, and retreat; wilderness warning signs with
avoid/approach/investigate choices; dungeon light consumption; wounds and
resource pressure; and a persistent action log. Combat remains abstract and
danger can usually be scouted, negotiated with, avoided, or escaped.

The expanded Version 0.3 loop tracks days across Morning, Afternoon, Evening,
and Night. Generated people, locations, rumors, threats, and dungeon rooms begin
partially hidden and enter the journal through conversations, inspection,
searching, and exploration. Rumors create leads rather than revealing complete
answers. The persistent event log records travel, discoveries, conversations,
encounters, and rests. Food, water, torches, supplies, wounds, and coin are
saved with the world.

A lightweight, rules-neutral character scaffold supports name, class,
background, starting resources, and bonuses for combat, exploration, social,
lore, survival, and stealth. The ten starter classes live in the editable
`data/tables/class_tables.json` file. Special abilities remain placeholders so
the eventual rules implementation can be SRD-friendly or replaced entirely.
New characters also receive a generated origin, formative event, personality
trait, ideal, bond, and flaw from `data/tables/player_background_tables.json`.
These details are descriptive only and do not impose additional rules.
The character sheet now also carries classic Strength, Dexterity,
Constitution, Intelligence, Wisdom, and Charisma scores beside the existing
six gameplay bonuses, plus lightweight class role/type/subtype and placeholder
fixed/derived score fields for future expansion.

Characters have lightweight structured inventory records with a name, category,
quantity, description, tags, and practical status flags such as equipped,
consumable, quest-related, carried, and tradeable. Common and class-flavored
starting gear is defined in `data/tables/item_tables.json`. Food, water,
torches, coin, and abstract supplies remain separate resource counters because
the exploration loop already consumes those values directly.

Version 0.8.6 expands that inventory layer into a lightweight equipment and
encumbrance framework. Item definitions can now include bulk, valid equipment
slots, handedness, simple placeholder combat-facing notes, and optional
container capacity. Characters track named slots such as Head, Chest, Belt,
Back, Main Hand, Off Hand, rings, and Backpack / Container, while a new
**Inventory / Equipment** dialog provides simple dropdown-driven equip and
unequip controls. Encumbrance remains rules-neutral with four states:
unencumbered, burdened, heavily burdened, and overloaded.

This is still not a full tactical equipment simulator. The current system is
meant to answer practical questions like what the character is wearing or
carrying, whether a two-handed item blocks the off hand, roughly how much
bulk is being carried, and whether the current loadout should affect travel or
field readiness. Placeholder damage, range, speed, and value fields are stored
for future use without introducing a full combat or economy ruleset yet.

The app also supports plain-text export for the active world summary, the
active character sheet, and the persistent event log. Exported character text
keeps inventory records and resource counters separate so food, water, torches,
coin, and supplies are not duplicated as consumable inventory quantities. When
the current world was generated from a seed, exports also include that seed for
support reports and reproducible sharing.

Open leads are now tracked as lightweight records instead of only loose text.
Conversation, discovery, checks, and downtime can add or corroborate leads
with a source, location, related NPC, status, suggested action, and category.
The world summary, journal summary, and plain-text exports now surface both
**Open Leads** and grouped **Suggested Next Actions** so the player has clearer
short-term choices to follow.

Lead follow-up remains intentionally lightweight. The player can now follow an
open lead directly instead of only reading it in summaries. A followed lead can
be corroborated, resolved, marked stale, or marked failed, and may produce a
connected clue, contact, warning, resource cost, or new follow-up lead. This
still is not a full quest system; it is a small gameplay-facing extension of
the lead loop.

The diary system is similarly lightweight. Important world and character events
from the structured timeline can create protected milestone entries with
placeholder importance levels, while the player can still add ordinary diary
entries for planning or reflection. Protected milestones keep their original
text but allow appended player notes.

World generation now supports optional reproducible seeds. The same seed should
recreate the same generated starting world when the code version, JSON tables,
and cleaned name data are also the same. Different seeds generally produce
different settlements, NPCs, locations, dungeon details, wilderness content,
and hook combinations. Seed control is intentionally scoped to generated world
setup rather than every later player action or future code revision.

The current working tree also adds a simple weird-fantasy calendar and
strategic downtime framework on top of the existing tactical loop. Local
actions still advance through Morning, Afternoon, Evening, and Night, but
those turns now map to an in-world calendar with year, season, and day. The
same framework also supports long-term downtime tasks such as training,
research, recovery, relationship-building, maintenance, and rumor
investigation without introducing full skill, spell, crafting, or economy
systems.

Characters now track a simple age in years plus a narrative age band. Time
passing through normal play and downtime can eventually advance age, but the
effects remain light and rules-neutral. Older saves still load safely with
default age and downtime state.

Conversation, searching, exploring, inspecting, retreating, and wilderness
encounter resolution now produce more varied narrative results while staying
rules-neutral. The text for these interaction outcomes is editable through
JSON tables rather than hard-coded bulk prose.

Editable JSON generation tables are also not fixed `d30` tables. Any practical
non-empty category size works, including one-entry tables, categories shorter
than 30 entries, categories longer than 30 entries, and weighted categories.

Version 0.5 adds a generic `1d20 + bonus vs difficulty` action resolver. Easy,
Standard, Hard, and Severe checks use the character's combat, exploration,
social, lore, survival, or stealth bonus. Outcomes range from critical failure
to critical success and can cost time or supplies, inflict wounds, attract
attention, reveal clues, or alter the character's position. This is still an
exploration framework rather than a full combat ruleset.

Strategic downtime remains intentionally lightweight. The JSON-driven task
definitions in `data/tables/downtime_tables.json` describe duration, context,
progress text, completion text, complication text, and tags. The current
implementation supports starting one active task at a time, advancing it by
days, logging progress, and applying a few minimal completion effects such as
recovery, coin, supplies, or new leads. This is a framework for future
strategic play, not a complete subsystem.

Downtime progress text now caps visible progress at the task requirement, so a
completed task reads cleanly instead of showing awkward overflow like `6/5`
days. Training and other completions also produce more concrete gameplay-facing
follow-up, such as a recorded training edge, a new contact, or a clearer lead
for the next field action.

Downtime outcomes are now a little more world-aware without becoming a full
faction, economy, crafting, or relationship system. Optional JSON-driven
`progress_outcomes`, `completion_outcomes`, and `complication_outcomes` can
reference the current settlement, season, known NPCs, locations, rumors,
threats, dungeon clues, wilderness clues, quest notes, leads, and simple
inventory context. These outcome hooks remain lightweight and mostly feed the
existing event log, quest log, leads list, supplies/coin counters, or
quest-flavored inventory clues.

Version 0.8.0 adds a reusable timeline and recurring-NPC framework on top of
the existing event log. The immediate event log still records play in plain
text, but the app now also stores structured timeline entries with calendar
date, action type, location context, and lightweight NPC/location/lead
references. Those entries power both the new verbose timeline view and a simple
journal-style summary.

NPC conversations now track repeated interaction counts. After a few
meaningful talks with the same NPC, they become a prominent recurring figure.
Prominent NPCs receive lightweight placeholder depth such as a deeper
backstory, personal motive, hidden pressure, relationship note, ongoing
thread, and recent interaction notes. These details remain generic and
rules-neutral for now.

Plain-text exports now include the current journal summary, verbose timeline
sections where appropriate, and prominent recurring NPC notes. Older saves
still load safely when timeline or NPC-prominence fields are missing.

Current save compatibility is intentionally scoped to the modern data model.
The oldest supported baseline is now Version 0.8.4-era saves. Earlier
pre-0.8.4 save shapes are no longer a guaranteed compatibility target for new
milestones.

The repository also now includes monster-manual import tooling under
`tools/importers/`. The stable stat-block pipeline in
`tools/importers/monster_manual_importer.py` reads the combined PDF page by
page, extracts only monster-entry pages, detects uppercase monster headings
followed by `SIZE:`, and writes an editable JSON catalog plus a text import
report. A separate appendix pipeline in
`tools/importers/monster_appendix_importer.py` parses the level, rarity, and
terrain appendices into a second JSON catalog without disturbing the main
monster catalog.

Before running importer tooling, validate local source setup with the new
source registry command:

```powershell
python tools/validate_sources.py
```

Then check the monster-specific readiness summary with:

```powershell
python tools/monster_import_status.py
```

The editable source registry lives at:

```text
data/source_registry.json
```

The source registry is Step 1 of the current 8-step source/import roadmap.
Version 0.8.14 completes Step 2 importer-readiness hardening for monsters
without adding a new content domain importer. The registry itself does not
import content by itself. Instead, it records:

- source identity
- source domain
- source role
- source status
- expected local path
- importer family
- whether a missing file should be treated as required or optional

Current status labels are intentionally lightweight:

- `active`: currently relevant source for importer or rules-reference work
- `inactive`: intentionally removed from active work
- `comparison_only`: usable for comparison/reference, not as the main baseline
- `placeholder`: future-domain or future-source placeholder

The registry is designed to be hand-edited. When adding a new source entry,
preserve:

- original source title
- expected local path
- domain separation
- source role
- whether it is active for rules, active for content, both, or neither

Missing local PDFs do not automatically break normal development. The
validation command reports them clearly, but optional active sources and
inactive sources remain warnings or informational setup notes rather than hard
failures. `data/import_sources/` remains intentionally untracked so local PDFs
do not enter version control.

Expected default source PDF location:

```text
data/import_sources/mandbmaster.pdf
```

Run the importer from the project directory with:

```powershell
python tools/importers/monster_manual_importer.py
```

The manual importer is now source-registry aware. It defaults to the
registered source ID `mandbmaster_combined_monster_manual`, reports the
registered source title/status/path in its text report, and still allows a
direct path override when needed:

```powershell
python tools/importers/monster_manual_importer.py C:\path\to\other_manual.pdf --source-id mandbmaster_combined_monster_manual
```

Run the appendix importer from the project directory with:

```powershell
python tools/importers/monster_appendix_importer.py
```

Like the main manual importer, the appendix importer now reports source ID,
source title, source status, input path mode, and output paths in its report.

The appendix importer writes:

```text
data/catalogs/monsters/monster_appendix_catalog.json
data/import_reports/monster_appendix_import_report.txt
data/import_reports/monster_appendix_unmatched_review.txt
```

Appendix rows keep source page numbers, section and table titles, region /
terrain / climate context, raw row text, and conservative monster-reference
matching against the existing monster catalog. Exact normalized matches are
linked to known monster IDs. Unmatched rows are preserved and reported rather
than guessed. The separate unmatched-review report groups repeated unresolved
names and highlights likely encoding/OCR variants versus appendix-only or
missing-catalog names. `data/import_sources/` remains intentionally untracked
so local PDFs do not enter version control.

The importer tooling now also includes an early multi-source JSON import path:

```powershell
python tools/importers/monster_json_importer.py path/to/monsters.json
```

If the JSON file belongs to a registered monster source, preserve that source
identity explicitly:

```powershell
python tools/importers/monster_json_importer.py path/to/monsters.json --source-id mandbmaster_combined_monster_manual
```

By default this is a dry-run preview. It normalizes JSON monster records into
the canonical catalog shape, records source metadata, detects duplicates and
conflicts against the existing monster catalog, and writes:

```text
data/import_reports/monster_json_import_report.txt
data/import_reports/monster_json_import_preview.json
```

Dry-run mode does not overwrite the main monster catalog. If you later want to
apply safe additions only, use:

```powershell
python tools/importers/monster_json_importer.py path/to/monsters.json --write-catalog
```

Even in explicit write mode, conflicting or protected records are not silently
overwritten. They remain report-only for later review. This milestone is
preparing the import architecture for a later editable Bestiary flow, not
building the full Bestiary GUI yet.

The monster-import tooling now also includes a dedicated Milestone 1 path for
the *Adventures Dark and Deep Bestiary* PDF:

Expected local source path:

```text
data/import_sources/adventures_dark_and_deep_bestiary/Adventures Dark and Deep Bestiaryforingestion.pdf
```

Run from the project directory with:

```powershell
python tools/import_add_bestiary.py
```

The ADD importer is also source-registry aware and now includes the registry
source ID, title, status, input path mode, and output paths in its report.

Milestone 1 behavior:

- scans actual PDF pages 4 through 438 only
- skips actual PDF pages 1 through 3
- skips appendices and index beginning at actual PDF page 439
- writes raw page text to
  `import_work/adventures_dark_and_deep_bestiary/raw_pages/page_###.txt`
- writes a draft content pack to
  `data/content_packs/imported/adventures_dark_and_deep_bestiary/`
- writes a report to
  `import_work/adventures_dark_and_deep_bestiary/import_report.txt`

Milestone 1 intentionally supports only likely single-entry monster records.
Entries with repeated stat-block labels or multi-variant layouts are deferred
and reported as `multi_variant_stat_block_not_supported_yet` instead of being
split into unreliable records. Appendices and index content are skipped.

The imported ADD content pack is intended to live beside the earlier monster
manual import output rather than overwrite it. Combined monster views can now
load the core monster catalog together with imported content packs and sort the
records alphabetically by display name while keeping same-name, different-source
records distinct by ID and source.

Current catalog-loading behavior is intentionally conservative:

- `app/monster_catalog.py` loads the stable core monster catalog by default
- imported monster packs under `data/content_packs/imported/*/monsters.json`
  are opt-in
- malformed imported packs warn and are skipped instead of replacing live
  catalog data

The long-term direction is broader than optional side packs. The final target
is one unified master monster catalog built from multiple approved sources.
Source-specific parsers, dry-run previews, content-pack outputs, and opt-in
pack loading are staging layers for that larger workflow.

Planned monster-import workflow:

1. Parse each source with a source-specific parser.
2. Preserve source-facing output with raw text and provenance.
3. Map parsed records into one shared normalized monster schema.
4. Flag low-confidence, ambiguous, or placeholder fields for later review.
5. Eventually merge reviewed normalized monsters into one master monster list
   while still preserving source variants and user corrections.

Proposed standard normalized monster fields include:

- `id`
- `canonical_name`
- `display_name`
- `aliases`
- `source_id`
- `source_title`
- `source_file`
- `source_page_start`
- `source_page_end`
- `source_entry_id`
- `source_slug`
- `armor_class`
- `hit_dice`
- `hit_points`
- `movement`
- `attacks`
- `damage`
- `special_attacks`
- `special_defenses`
- `save`
- `morale`
- `alignment`
- `intelligence`
- `size`
- `type`
- `category`
- `environment`
- `terrain`
- `region`
- `number_appearing`
- `no_enc`
- `treasure`
- `xp`
- `challenge`
- `level`
- `description`
- `raw_stat_block`
- `raw_text`
- `normalized_fields`
- `missing_fields`
- `placeholder_fields`
- `mapping_confidence`
- `review_status`
- `review_notes`
- `user_corrections`

Normalization and placeholder policy:

- missing values should not block import
- use explicit placeholders such as `null`, `unknown`, or `not_provided`
- do not invent exact values when the source does not provide them
- logical guesses are allowed only when marked with confidence and review
  status
- retain ambiguous raw source text rather than forcing a misleading exact
  field value

Expected mapping examples:

- `No. Enc` -> `number_appearing`
- `Movement` / `Move` -> `movement`
- `Armor Class` / `AC` -> `armor_class`
- `Hit Dice` / `HD` -> `hit_dice`
- `Treasure Type` / `Treasure` -> `treasure`
- `LEVEL/X.P.` / `XP` -> `xp` and optionally `level`

Confidence guidance for the future mapper:

- `high`: direct field match
- `medium`: clear alias or format conversion
- `low`: inferred or guessed value
- `missing`: placeholder used

Future review/correction expectations:

- uncertain mappings should feed a user-reviewable queue or report
- user corrections should be stored separately from raw imported data when
  practical
- user corrections should override parser guesses without deleting original
  source text
- duplicate or same-name monsters from different sources should remain
  distinct until canonical grouping and preferred-variant handling exist

Imported JSON records may carry optional source metadata and later-edit
protection hints such as:

- `import_metadata.source_id`
- `import_metadata.source_name`
- `import_metadata.source_type`
- `import_metadata.source_file`
- `import_metadata.source_page`
- `import_metadata.source_record_id`
- `import_metadata.import_method`
- `import_metadata.import_version`
- `import_metadata.original_name`
- `import_metadata.normalized_name`
- `custom_record`
- `manual_override`
- `protected_fields`

These fields are forward-looking compatibility hooks for multi-source monster
catalog work. They are optional and backward-compatible with the current app
because the gameplay layer does not yet depend on a full Bestiary editor.

If the Python runtime used for the import command does not have a PDF reader
available, the importer exits with a clear message. The core game itself
remains dependency-free; this importer is optional tooling for building the
editable monster catalog.

Current source/import roadmap:

1. Source registry / source-path validation
2. Monster importer baseline continuation and import readiness
3. Normalized monster schema and mapping layer
4. Magic item importer
5. Mundane equipment importer
6. Spell importer
7. Treasure-table importer
8. Module / keyed-location importer, then generator/world-system importers
   later

Version 0.8.13 completed Step 1. Version 0.8.14 keeps the current
monster/manual/appendix/JSON/ADD parser behavior stable while adding
source-registry-aware command/report behavior, a dedicated monster import
status helper, and clearer import-readiness documentation.

Version 0.8.1 adds a lightweight key-NPC and faction-interaction phase
framework. Once a recurring NPC becomes prominent enough, they can be promoted
to a key NPC with a key date, reason, notes, and a simple placeholder faction
tag. Key NPCs are then compared against one another to create lightweight
relationship records such as ally, at odds, neutral, or unknown.

The new relationship phase is intentionally small and rules-neutral. It can run
after downtime completion and after travel or rest when a new day begins. Phase
results produce concise event-log and timeline entries, along with small follow
ups such as leads, quest notes, or lightweight faction-status notes. This is a
foundation for later world dynamics, not a full faction simulator.

World exports now include key NPCs, relationship records, and simple
faction-status notes when present. NPC detail views also show key-NPC metadata
without adding a separate faction screen. Older saves still load safely when
key-NPC, relationship, or faction-phase fields are missing.

Version 0.8.2 focuses on usability rather than a new subsystem. `Town Mode`
groups character creation, settlement views, location and NPC browsing, social
actions, rest, and downtime. `Adventure Mode` groups world generation, travel,
wilderness and dungeon inspection, encounter-facing choices, retreat, and
action checks. Shared actions such as save/load, character viewing, recap,
exports, and diagnostics remain available in both modes.

Current GUI mode split:

- `Town Mode`: Create Character, Settlement Overview, NPC List, Location List,
  Journal Summary, Talk/Socialize, Inspect Town/Current Location, Search Town,
  Rest/Recover, Full Rest, Start Downtime, and Advance Downtime.
- `Adventure Mode`: Generate New Region, Wilderness Overview, Dungeon
  Overview, Dungeon Rooms, Encounter List, Adventure Hook, Verbose Timeline,
  Return to Town, Travel, Explore, Search, Inspect, Talk, Move to Room,
  Inspect Room, Rest, Retreat, encounter choices, and action checks.
- Shared in both modes: View Character, Journal / World Recap, Event Log,
  Export Event Log, Export World, Export Character, Save World, Load World,
  Data Diagnostics, plus the always-visible player state, seed field, status,
  and output panel.

Initial usability rules:

- Before a world exists, **Generate New Region**, **Load World**,
  **Data Diagnostics**, **Clear Output**, and the friendly empty-state
  **Journal / World Recap** remain available.
- Most world-dependent browsing, exploration, downtime, export, and overview
  actions stay disabled until a world exists.
- Character-dependent actions such as **View Character**, **Export Character**,
  **Start Downtime**, **Advance Downtime**, and action checks stay disabled
  until a character exists.
- **Follow Open Lead** is available once a world exists and gives a minimal
  prompt for choosing among current unresolved leads when more than one is
  available.

Simulated-time or fast-forward controls were intentionally deferred in this
milestone. The current calendar, downtime, and faction-phase foundations remain
available for a later small follow-up once the GUI split has settled.

The database is created automatically at:

```text
data/saves/worlds.db
```

Deleting that file removes all saves. The application will create a fresh
database on its next launch.

## Project layout

- `main.py`: application entry point
- `app/gui.py`: Tkinter interface and text rendering
- `app/game_state.py`: active-world coordination
- `app/models.py`: dataclass domain models
- `app/database.py`: SQLite schema and persistence
- `app/table_loader.py`: JSON loading, validation, and fallbacks
- `app/dice.py`: dice formulas, reaction rolls, and morale checks
- `app/characters.py`: rules-light class loading and character creation
- `app/character_profiles.py`: JSON-driven personal background details
- `app/inventory.py`: item catalog and class starting-loadout construction
- `app/calendar.py`: shared calendar, aging, and timeline helpers
- `app/downtime.py`: strategic downtime task engine
- `app/key_npcs.py`: key-NPC promotion and faction-phase helpers
- `app/interaction_text.py`: interaction template formatting helpers
- `app/exporters.py`: plain-text export formatting helpers
- `app/source_registry.py`: source registry loading and validation helpers
- `app/timeline.py`: structured timeline logging and recurring-NPC helpers
- `app/checks.py`: generic d20 checks, outcomes, and state consequences
- `app/generators/`: focused procedural generators
- `data/tables/`: editable generation content
- `data/tables/interaction_tables.json`: dialogue, encounter, and action text
- `data/tables/downtime_tables.json`: downtime task definitions
- `data/tables/key_npc_tables.json`: key-NPC and relationship-phase text
- `data/tables/npc_depth_tables.json`: placeholder recurring-NPC depth text
- `data/saves/`: local SQLite saves
- `data/source_registry.json`: editable source registry for local import
  sources
- `tools/importers/`: monster manual import tooling
- `tools/monster_import_status.py`: monster-source readiness and recommended
  import commands
- `tools/validate_sources.py`: source-registry and source-path validation
  command
- `tests/`: standard-library unit tests

## Editing generation tables

Each file in `data/tables` is a JSON object whose category values are non-empty
lists. Add, remove, or rewrite list entries to change generated content without
changing Python code. Files are loaded when the app starts.

These editable JSON generation tables are not fixed `d30` tables. A category
may contain any practical non-empty number of entries:

- 1 entry works
- fewer than 30 entries work
- more than 30 entries work
- weighted entries still work

Generation code selects from the actual list length provided by the JSON data
rather than assuming 30 rows or a fixed dice index.

Interaction text follows the same pattern. Dialogue lead variety and encounter
resolution flavor live in editable JSON categories, so the narrative range can
grow without moving large prose lists into Python code.

Downtime tasks follow the same JSON-driven pattern. Add or edit task
definitions in `data/tables/downtime_tables.json` to change the available
strategic actions, their default durations, contexts, and log text without
rewriting Python logic.

Downtime tasks may also include optional world-aware consequence lists:

- `progress_outcomes`
- `completion_outcomes`
- `complication_outcomes`

Each outcome entry stays small and rules-neutral. Current supported kinds are
`event`, `lead`, `quest_note`, `coin`, `supplies`, and `inventory`.

Recurring-NPC placeholder depth follows the same JSON-driven pattern. Edit
`data/tables/npc_depth_tables.json` to expand generic backstory, motive,
pressure, relationship, and ongoing-thread text without hard-coding larger
lists into Python.

Key-NPC promotion and relationship-phase text also follow the JSON-driven
pattern. Edit `data/tables/key_npc_tables.json` to tune promotion reasons,
key-NPC notes, and lightweight ally/at-odds/neutral event phrasing without
rewriting Python logic.

Simple lists choose entries uniformly. The loader also accepts weighted entries:

```json
[
  {"value": "common result", "weight": 4},
  {"value": "rare result", "weight": 1}
]
```

The loader validates required files and categories when the app starts. Entries
must be non-empty text, valid weighted text objects, or (for character classes)
objects containing all required resource and bonus fields. Missing files,
malformed JSON, invalid entries, empty categories, and missing category names
are reported as warnings. Invalid entries are skipped, and small type-safe
fallbacks prevent bad local data from crashing generation or character
creation. Use **Data Diagnostics** in the GUI to inspect the complete report.

When adding table data safely:

1. Keep the JSON root as an object and every category as a non-empty list.
2. Use non-blank strings or `{"value": "...", "weight": 1}` entries.
3. Keep weights numeric and greater than zero.
4. Preserve all six class bonus keys and use integer resource values.
5. Run the full test command below before relying on the edited tables.

Generator modules in `app/generators/` share `TableLoader` through the small
`BaseGenerator` helper. Table content remains in JSON; Python modules coordinate
selection and relationships without embedding normal setting content.

## Large name files

Place newline-delimited raw personal names in the current preferred filenames:

```text
data/names/firstnames.txt
data/names/surnames.txt
```

The older filenames `raw_first_names.txt` and `raw_last_names.txt` are also
accepted for compatibility. If both forms exist, the preferred filename above
is used.

Clean them from the project directory with:

```powershell
python tools/clean_names.py
```

The tool trims blank lines and whitespace, applies title case, removes
duplicates, sorts the results, and writes:

```text
data/names/first_names.txt
data/names/last_names.txt
```

The cleaned text files are read once and cached by `app/name_generator.py`.
That module provides random first names, last names, full names, and batches of
full names. NPC generation and the **Random Name** button in character creation
use the same cached generator. If either cleaned file is missing, empty, or
unreadable, the smaller editable JSON name tables remain as safe fallbacks.
The current repository tracks both raw and cleaned name datasets. Avoid
duplicating these large lists in Python or JSON.

If the source data contains replacement characters or obvious mojibake, scrub
the cleaned files in place with:

```powershell
python tools/scrub_names.py
```

The scrubber preserves normal accented Unicode names, removes suspicious
corrupted lines, safely replaces each cleaned file through a temporary file,
and reports how many names were kept and removed. Raw source files are not
modified.

## Tests

From the project directory:

```powershell
python -m unittest discover -s tests -v
```

Tests cover dice formulas, name cleanup and generation, character background
profiles, structured inventory, schema-aware table validation, generation with
missing data, generated counts and references, dungeon connectivity, SQLite
child records, calendar and downtime flow, exporter output, save/load
reconstruction, reproducible seed behavior, downtime consequence outcomes,
timeline logging, recurring-NPC promotion, key-NPC promotion, relationship
records, faction-phase behavior, GUI mode helper routing, recap formatting,
equipment slots, bulk and encumbrance behavior, monster-manual stat-block
parsing/import tooling, monster appendix parsing/import tooling, and
older-save compatibility from the supported v0.8.4+ baseline. Source-registry
coverage also validates editable source entries, duplicate detection, allowed
domains/statuses, required-vs-optional missing paths, and summary reporting
without requiring real PDFs.

Stress coverage now also exercises messy user behavior through the public game
state API: actions before world generation, actions before character creation,
repeated searches/talk/rest/retreat/save/load/export sequences, illogical
encounter and downtime choices, corrupt calendar-like save data, malformed
table data, malformed timeline/NPC/key-NPC state, and a deterministic
randomized action sequence with invariant checks after every step.

Minimal guard behavior added for this coverage:

- downtime now requires a created character
- invalid loaded calendar fields fall back safely
- invalid public inventory quantities raise clear `ValueError` messages
- mode-specific GUI layouts still route through the same guarded public
  handlers, so hidden buttons are not the only protection against invalid
  state
- GUI action availability now reflects world and character prerequisites before
  the player clicks into most unavailable flows

## Current boundaries

The app has a lightweight exploration game loop, calendar/downtime framework,
and character scaffold, but not tactical combat. Visual maps, detailed combat
resolution, multiplayer, and web/server features are intentionally deferred.

Monster-system direction is also intentionally staged. The current codebase
now has a stable MandBmaster baseline import, a Megadungeon parser and
content-pack path, and opt-in imported-pack loading. The next architectural
target is not more permanent side packs by themselves; it is a shared
normalized monster schema and mapping layer that can feed one future master
monster catalog while preserving source provenance, review flags, and user
corrections. Region/rarity monster selection should wait until that
normalization and canonical-grouping work is stable. Spells, gear, arms,
armor, and all image support remain deferred until that monster-data pipeline
is stable.

Future direction: a player character may eventually retire and remain in the
same generated world as an NPC. That should build on the existing world and NPC
structures in a later milestone rather than being folded into the first-pass
calendar/downtime implementation.

The domain and persistence layers do not depend on Tkinter, which keeps later
migration to a web or server interface practical.

## AI Agent Workflow

This is a solo-developed project supported by AI coding agents. Atlas, Forge,
Scribe, Windowwright, Keeper, Warden, Redline, and Ledger are named roles used
to organize Codex work; they are not separate uncontrolled developers.

The standard workflow is:

1. **Atlas** plans the milestone.
2. **Forge**, **Scribe**, **Windowwright**, or **Keeper** implements the
   requested logic, data, interface, or persistence work.
3. **Warden** runs tests, compilation, and data validation.
4. **Redline** reviews the full diff for scope, quality, and compatibility.
5. **Ledger** updates documentation and release notes.

One Codex session may play several roles in sequence for a small change. Larger
features should be split into separate prompts or milestones. This structure
prevents chaotic edits, protects older saves, and keeps features testable.

Example milestone: **"Add procedural towns."**

- Atlas proposes the town system structure.
- Forge implements the town generator and game-state model.
- Scribe adds town name, shop, rumor, and government tables.
- Keeper ensures towns save/load correctly and older saves still load.
- Windowwright adds GUI display for towns.
- Warden adds and runs tests.
- Redline reviews the full diff.
- Ledger updates README/changelog and prepares the release notes.
