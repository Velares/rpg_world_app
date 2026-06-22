from __future__ import annotations

import random
from collections import Counter

from app.calendar import calendar_date, format_calendar
from app.key_npcs import KEY_NPC_THRESHOLD, promote_key_npc_if_needed
from app.leads import (
    format_open_leads,
    format_recent_lead_changes,
    format_suggested_next_actions,
)
from app.models import NPC, TimelineEntry, World
from app.table_loader import TableLoader


PROMINENT_NPC_THRESHOLD = 3
RECENT_NPC_NOTES_LIMIT = 5

NPC_DEPTH_FALLBACKS = {
    "deeper_backstories": ["They carry an old debt from before the region knew your name."],
    "personal_motives": ["They want safety without surrendering influence."],
    "hidden_pressures": ["A private obligation keeps narrowing their choices."],
    "relationship_to_player": ["They see you as useful, worrying, and hard to ignore."],
    "ongoing_threads": ["Their future choices keep brushing against your unfinished work."],
    "prominence_notes": ["They have become a recurring figure in the region's unfolding troubles."],
}


def add_timeline_entry(
    player,
    result_text: str,
    action_type: str = "event",
    location_context: str = "",
    npc_id: str = "",
    npc_name: str = "",
    location_id: str = "",
    location_name: str = "",
    quest_ref: str = "",
    lead_ref: str = "",
    downtime_ref: str = "",
    resource_impact: str = "",
) -> TimelineEntry:
    entry = TimelineEntry(
        day=player.day,
        time_period=player.time_period,
        action_type=action_type,
        result_text=result_text,
        location_context=location_context or player.current_location,
        npc_id=npc_id,
        npc_name=npc_name,
        location_id=location_id,
        location_name=location_name,
        quest_ref=quest_ref,
        lead_ref=lead_ref,
        downtime_ref=downtime_ref,
        resource_impact=resource_impact,
    )
    player.timeline_entries.append(entry)
    from app.diary import record_event_entry

    record_event_entry(player, action_type, result_text)
    return entry


def format_verbose_timeline(world: World | None) -> str:
    if world is None:
        return (
            "NO ACTIVE WORLD\n"
            "===============\n"
            "Generate or load a world first."
        )
    entries = world.player_state.timeline_entries
    lines = [
        "VERBOSE TIMELINE",
        "================",
        "",
        f"Current Date: {format_calendar(world.player_state.day, world.player_state.time_period)}",
        "",
    ]
    if not entries:
        lines.append("No structured timeline entries recorded yet.")
        return "\n".join(lines)
    for index, entry in enumerate(entries, 1):
        refs = []
        if entry.npc_name:
            refs.append(f"NPC: {entry.npc_name}")
        if entry.location_name:
            refs.append(f"Location: {entry.location_name}")
        if entry.quest_ref:
            refs.append(f"Quest: {entry.quest_ref}")
        if entry.lead_ref:
            refs.append(f"Lead: {entry.lead_ref}")
        if entry.downtime_ref:
            refs.append(f"Downtime: {entry.downtime_ref}")
        if entry.resource_impact:
            refs.append(f"Resources: {entry.resource_impact}")
        ref_text = f" [{' | '.join(refs)}]" if refs else ""
        lines.append(
            f"{index}. Day {entry.day}, {entry.time_period} "
            f"({entry.location_context or 'unknown'}) - {entry.action_type.upper()}{ref_text}"
        )
        lines.append(f"   {entry.result_text}")
    return "\n".join(lines)


def format_summary_timeline(world: World | None) -> str:
    if world is None:
        return (
            "NO ACTIVE WORLD\n"
            "===============\n"
            "Generate or load a world first."
        )
    player = world.player_state
    entries = player.timeline_entries
    lines = [
        "JOURNAL SUMMARY",
        "===============",
        "",
        f"Current Date: {format_calendar(player.day, player.time_period)}",
        f"Seed: {world.generation_seed or 'Random / not recorded'}",
        "",
    ]
    if not entries:
        lines.append("No timeline activity has been summarized yet.")
        return "\n".join(lines)
    days = sorted({entry.day for entry in entries})
    counts = Counter(entry.action_type for entry in entries)
    lines.append(
        f"Activity spans {len(days)} day(s) with {len(entries)} logged timeline entries."
    )
    lines.append(
        "Action mix: "
        + ", ".join(f"{name} {counts[name]}" for name in sorted(counts))
    )
    major = [
        entry.result_text
        for entry in entries
        if entry.action_type
        in {
            "travel",
            "explore",
            "talk",
            "encounter",
            "downtime",
            "lead",
            "quest",
            "npc_prominence",
            "key_npc",
            "faction_phase",
        }
    ]
    lines.extend(["", "Recent Major Activity", "---------------------"])
    lines.extend(f"- {text}" for text in major[-5:]) if major else lines.append("- None yet.")
    lines.extend(["", "Open Leads", "----------"])
    open_leads_text = format_open_leads(world)
    if open_leads_text == "No open leads.":
        lines.append("- None yet.")
    else:
        lines.extend(open_leads_text.splitlines())
    lines.extend(["", "Suggested Next Actions", "----------------------"])
    next_actions_text = format_suggested_next_actions(world)
    if next_actions_text == "No suggested next actions.":
        lines.append("- None yet.")
    else:
        lines.extend(next_actions_text.splitlines())
    lines.extend(["", "Recent Lead Changes", "-------------------"])
    recent_changes_text = format_recent_lead_changes(world)
    if recent_changes_text == "No recently advanced leads.":
        lines.append("- None yet.")
    else:
        lines.extend(recent_changes_text.splitlines())
    prominent = [npc for npc in world.npcs if npc.prominent]
    lines.extend(["", "Prominent NPCs", "--------------"])
    if prominent:
        for npc in prominent:
            lines.append(
                f"- {npc.name}: {npc.interaction_count} interactions, "
                f"last seen {npc.last_interacted_date or 'unknown'}"
            )
    else:
        lines.append("- None yet.")
    key_npcs = [npc for npc in world.npcs if npc.is_key_npc]
    lines.extend(["", "Key NPCs", "--------"])
    if key_npcs:
        for npc in key_npcs:
            lines.append(
                f"- {npc.name}: {npc.faction_tag}, key since {npc.key_npc_since or 'unknown'}"
            )
    else:
        lines.append("- None yet.")
    return "\n".join(lines)


def record_npc_interaction(
    world: World,
    npc: NPC,
    note: str,
    rng: random.Random,
    tables: TableLoader,
) -> str:
    messages: list[str] = []
    npc.interaction_count = max(0, int(npc.interaction_count)) + 1
    npc.prominence_score = max(0, int(npc.prominence_score)) + 1
    current_date = format_calendar(world.player_state.day, world.player_state.time_period)
    if not npc.first_interacted_date:
        npc.first_interacted_date = current_date
    npc.last_interacted_date = current_date
    npc.recent_interaction_notes.append(f"{current_date} - {note}")
    npc.recent_interaction_notes = npc.recent_interaction_notes[-RECENT_NPC_NOTES_LIMIT:]
    if not npc.prominent and npc.interaction_count >= PROMINENT_NPC_THRESHOLD:
        npc.prominent = True
        npc.deeper_backstory = _choose_depth_text(tables, rng, "deeper_backstories")
        npc.personal_motive = _choose_depth_text(tables, rng, "personal_motives")
        npc.hidden_pressure = _choose_depth_text(tables, rng, "hidden_pressures")
        npc.relationship_to_player = _choose_depth_text(tables, rng, "relationship_to_player")
        npc.ongoing_thread = _choose_depth_text(tables, rng, "ongoing_threads")
        npc.prominence_notes = _choose_depth_text(tables, rng, "prominence_notes")
        messages.append(
            f"{npc.name} has become a prominent recurring figure. {npc.prominence_notes}"
        )
    if npc.prominence_score >= KEY_NPC_THRESHOLD:
        messages.extend(promote_key_npc_if_needed(world, npc, rng, tables))
    return "\n".join(messages)


def _choose_depth_text(tables: TableLoader, rng: random.Random, category: str) -> str:
    options = tables.get("npc_depth_tables", category)
    if options:
        return tables.choose("npc_depth_tables", category, rng)
    return NPC_DEPTH_FALLBACKS[category][0]
