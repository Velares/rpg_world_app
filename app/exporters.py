from __future__ import annotations

from app.calendar import age_band, format_calendar
from app.downtime import DowntimeEngine
from app.leads import (
    format_open_leads,
    format_recent_lead_changes,
    format_suggested_next_actions,
)
from app.models import InventoryItem, World
from app.timeline import format_summary_timeline, format_verbose_timeline


def inventory_item_text(item: InventoryItem, detailed: bool = False) -> str:
    flags = []
    if item.equipped:
        flags.append("equipped")
    if item.consumable:
        flags.append("consumable")
    if item.quest_related:
        flags.append("quest")
    if not item.carried:
        flags.append("stored")
    suffix = f" [{', '.join(flags)}]" if flags else ""
    base = f"{item.name} x{item.quantity} ({item.category}){suffix}"
    if detailed and item.description:
        return f"{base} - {item.description}"
    return base


def export_world_summary(world: World | None) -> str:
    if world is None:
        return (
            "NO ACTIVE WORLD\n"
            "===============\n"
            "Generate or load a world first."
        )
    settlement = world.settlement
    player = world.player_state
    threats = ", ".join(player.known_threats) or "Unknown"
    known_rumors = [
        settlement.rumors[index]
        for index in player.known_rumor_indices
        if index < len(settlement.rumors)
    ]
    prominent_npcs = [npc for npc in world.npcs if npc.prominent]
    key_npcs = [npc for npc in world.npcs if npc.is_key_npc]
    return (
        f"{world.name.upper()}\n{'=' * len(world.name)}\n"
        f"Created: {world.created_at}\n"
        f"Seed: {_seed_text(world)}\n"
        f"Calendar: {format_calendar(player.day, player.time_period)}\n"
        f"Downtime: {DowntimeEngine.summarize(player.active_downtime_task)}\n"
        f"Settlement: {settlement.name} ({settlement.type})\n"
        f"Condition: {settlement.condition}\n"
        f"Population: {settlement.population}\n"
        f"Local problem: {settlement.local_problem}\n"
        f"Problem connection: {settlement.problem_connection or 'Unknown'}\n"
        f"Nearby danger: {settlement.nearby_danger}\n"
        f"Known threats: {threats}\n"
        f"Wilderness: {world.wilderness.name} ({world.wilderness.terrain_type})\n"
        f"Dungeon lead: {world.dungeon.name}\n"
        f"Adventure goal: {world.adventure_hook.major_goal}\n"
        f"Quest: {player.quest_log[0] if player.quest_log else 'None recorded'}\n\n"
        f"KNOWN CONTACTS AND LEADS\n"
        f"========================\n"
        f"Known NPCs: {len(player.known_npc_ids)} of {len(world.npcs)}\n"
        f"Known locations: {len(player.known_location_ids)} of "
        f"{len(settlement.important_locations)}\n"
        f"Known rumors: {len(known_rumors)} of {len(settlement.rumors)}\n"
        f"Discovered rooms: {len(player.discovered_room_ids)} of {len(world.dungeon.rooms)}\n\n"
        f"RUMOR LEADS\n"
        f"===========\n"
        f"{_numbered_lines(known_rumors) or 'No rumors learned yet.'}\n\n"
        f"OPEN LEADS\n"
        f"==========\n"
        f"{format_open_leads(world)}\n\n"
        f"RECENT LEAD CHANGES\n"
        f"===================\n"
        f"{format_recent_lead_changes(world)}\n\n"
        f"SUGGESTED NEXT ACTIONS\n"
        f"======================\n"
        f"{format_suggested_next_actions(world)}\n\n"
        f"JOURNAL SUMMARY\n"
        f"===============\n"
        f"{_body_only(format_summary_timeline(world))}\n\n"
        f"PROMINENT NPCS\n"
        f"==============\n"
        f"{_prominent_npc_lines(prominent_npcs)}\n\n"
        f"KEY NPCS AND RELATIONSHIPS\n"
        f"==========================\n"
        f"{_key_npc_lines(key_npcs)}\n\n"
        f"RELATIONSHIP RECORDS\n"
        f"====================\n"
        f"{_relationship_lines(world)}\n\n"
        f"FACTION STATUS NOTES\n"
        f"====================\n"
        f"{_faction_status_lines(world)}"
    )


def export_character_text(world: World | None) -> str:
    if world is None:
        return (
            "NO ACTIVE WORLD\n"
            "===============\n"
            "Generate or load a world first."
        )
    player = world.player_state
    character = player.character
    if character is None:
        return (
            "NO PLAYER CHARACTER\n"
            "===================\n"
            "Use Create Character to choose a name, class, and background."
        )
    bonuses = "\n".join(
        f"{name.title()}: {value:+d}" for name, value in character.bonuses.items()
    )
    inventory = "\n".join(
        f"- {inventory_item_text(item, detailed=True)}" for item in player.inventory
    ) or "- Empty"
    recent_actions = [
        entry.result_text
        for entry in player.timeline_entries
        if entry.action_type in {"travel", "explore", "search", "talk", "encounter", "downtime"}
    ]
    return (
        f"{character.name.upper()}\n{'=' * len(character.name)}\n"
        f"Class: {character.character_class}\n"
        f"Background: {character.background}\n"
        f"Seed: {_seed_text(world)}\n"
        f"Age: {character.age_years}\n"
        f"Age Band: {age_band(character.age_years)}\n"
        f"Current Calendar: {format_calendar(player.day, player.time_period)}\n"
        f"Downtime: {DowntimeEngine.summarize(player.active_downtime_task)}\n"
        f"Role: {character.role_description}\n"
        f"Starting Supplies: {character.starting_supplies}\n\n"
        f"BACKGROUND DETAILS\n"
        f"==================\n"
        f"Origin: {character.origin_detail or 'Not recorded'}\n"
        f"Formative Event: {character.formative_event or 'Not recorded'}\n"
        f"Personality: {character.personality_trait or 'Not recorded'}\n"
        f"Ideal: {character.ideal or 'Not recorded'}\n"
        f"Bond: {character.bond or 'Not recorded'}\n"
        f"Flaw: {character.flaw or 'Not recorded'}\n\n"
        f"EQUIPMENT AND INVENTORY\n"
        f"=======================\n"
        f"{inventory}\n\n"
        f"RESOURCES\n"
        f"=========\n"
        f"Supplies: {player.supplies}\n"
        f"Food: {player.food}\n"
        f"Water: {player.water}\n"
        f"Torches: {player.torches}\n"
        f"Coin: {player.coin}\n"
        f"Wounds: {player.wounds}\n\n"
        f"Resource counters remain separate from inventory records so food, water, "
        f"torches, coin, and supplies are not duplicated as consumable inventory quantities.\n\n"
        f"BONUSES\n"
        f"=======\n"
        f"{bonuses}\n\n"
        f"SPECIAL ABILITY PLACEHOLDER\n"
        f"===========================\n"
        f"{character.special_ability_placeholder}\n\n"
        f"RECENT MAJOR ACTIONS\n"
        f"====================\n"
        f"{_bulleted_lines(recent_actions[-5:]) or 'No major actions recorded yet.'}\n\n"
        f"OPEN LEADS\n"
        f"==========\n"
        f"{format_open_leads(world)}\n\n"
        f"RECENT LEAD CHANGES\n"
        f"===================\n"
        f"{format_recent_lead_changes(world)}\n\n"
        f"JOURNAL SUMMARY\n"
        f"===============\n"
        f"{_body_only(format_summary_timeline(world))}"
    )


def export_event_log_text(world: World | None) -> str:
    if world is None:
        return (
            "NO ACTIVE WORLD\n"
            "===============\n"
            "Generate or load a world first."
        )
    player = world.player_state
    lines = [
        "EVENT LOG",
        "=========",
        "",
        f"Seed: {_seed_text(world)}",
        f"Calendar: {format_calendar(player.day, player.time_period)}",
        f"Downtime: {DowntimeEngine.summarize(player.active_downtime_task)}",
        "",
    ]
    if player.event_log:
        lines.extend(
            f"{index}. {entry}" for index, entry in enumerate(player.event_log, 1)
        )
    else:
        lines.append("No events recorded yet.")
    if player.pending_encounter_id:
        lines.extend(
            [
                "",
                "DANGER IS PENDING",
                "Use Avoid, Approach, Investigate, or Retreat from Encounter.",
            ]
        )
    lines.extend(
        [
            "",
            "OPEN LEADS",
            "==========",
            format_open_leads(world),
            "",
            "RECENT LEAD CHANGES",
            "===================",
            format_recent_lead_changes(world),
            "",
            "TIMELINE SUMMARY",
            "================",
            _body_only(format_summary_timeline(world)),
            "",
            "VERBOSE TIMELINE",
            "================",
            _body_only(format_verbose_timeline(world)),
        ]
    )
    return "\n".join(lines)


def _bulleted_lines(values: list[str]) -> str:
    return "\n".join(f"- {value}" for value in values)


def _numbered_lines(values: list[str]) -> str:
    return "\n".join(f"{index}. {value}" for index, value in enumerate(values, 1))


def _seed_text(world: World) -> str:
    return world.generation_seed or "Random / not recorded"


def _body_only(text: str) -> str:
    lines = text.splitlines()
    if len(lines) <= 3:
        return text
    return "\n".join(lines[4:]).strip() or text


def _prominent_npc_lines(npcs) -> str:
    if not npcs:
        return "No prominent recurring NPCs yet."
    lines = []
    for npc in npcs:
        lines.append(
            f"- {npc.name}: {npc.prominence_notes or 'Recurring figure.'}"
        )
        if npc.relationship_to_player:
            lines.append(f"  Relationship: {npc.relationship_to_player}")
        if npc.ongoing_thread:
            lines.append(f"  Ongoing Thread: {npc.ongoing_thread}")
        if npc.recent_interaction_notes:
            lines.append(f"  Recent Note: {npc.recent_interaction_notes[-1]}")
    return "\n".join(lines)


def _key_npc_lines(npcs) -> str:
    if not npcs:
        return "No key NPCs yet."
    lines = []
    for npc in npcs:
        lines.append(
            f"- {npc.name} [{npc.faction_tag}]: {npc.key_npc_reason or 'No recorded reason.'}"
        )
        if npc.key_npc_notes:
            lines.append(f"  Notes: {npc.key_npc_notes}")
    return "\n".join(lines)


def _relationship_lines(world: World) -> str:
    if not world.npc_relationships:
        return "No key-NPC relationships recorded yet."
    npc_names = {npc.entity_id: npc.name for npc in world.npcs}
    lines = []
    for relationship in world.npc_relationships:
        name_a = npc_names.get(relationship.npc_a_id, relationship.npc_a_id)
        name_b = npc_names.get(relationship.npc_b_id, relationship.npc_b_id)
        lines.append(
            f"- {name_a} / {name_b}: {relationship.relationship_state} "
            f"(score {relationship.affinity_score:+d})"
        )
        if relationship.reason_text:
            lines.append(f"  Reason: {relationship.reason_text}")
        if relationship.recent_event_notes:
            lines.append(f"  Recent: {relationship.recent_event_notes[-1]}")
    return "\n".join(lines)


def _faction_status_lines(world: World) -> str:
    if not world.faction_status_notes:
        return "No faction status notes recorded yet."
    return "\n".join(
        f"- {tag}: {status}" for tag, status in sorted(world.faction_status_notes.items())
    )
