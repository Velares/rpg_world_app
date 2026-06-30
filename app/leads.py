from __future__ import annotations

import random
from collections import defaultdict

from app.calendar import advance_time, append_timeline_entry
from app.models import LeadRecord, World
from app.shared import append_unique as _append_unique


OPEN_LEAD_STATUSES = {"new", "active", "uncorroborated", "corroborated"}
CLOSED_LEAD_STATUSES = {"resolved", "failed", "stale"}
LEAD_CATEGORY_TITLES = {
    "talk": "Talk",
    "investigate": "Investigate",
    "explore": "Explore",
    "faction": "Faction",
    "downtime": "Downtime",
    "other": "Other",
}
LEAD_STATUS_TITLES = {
    "new": "New",
    "active": "Open",
    "uncorroborated": "Uncorroborated",
    "corroborated": "Corroborated",
    "resolved": "Resolved",
    "failed": "Failed",
    "stale": "Stale",
}


def add_lead(
    player,
    text: str,
    *,
    source: str = "",
    location: str = "",
    related_npc: str = "",
    status: str = "active",
    suggested_action: str = "",
    category: str = "other",
) -> tuple[LeadRecord, bool]:
    clean_text = str(text).strip()
    if not clean_text:
        raise ValueError("Lead text must not be blank.")
    normalized = _normalize(clean_text)
    clean_status = _normalize_status(status)
    clean_category = _normalize_category(category)
    action_text = str(suggested_action).strip() or clean_text
    for lead in player.lead_records:
        if _normalize(lead.text) != normalized:
            continue
        previous_status = _normalize_status(lead.status)
        if source:
            _merge_source(lead, source)
        if location and not lead.location:
            lead.location = location
        if related_npc and not lead.related_npc:
            lead.related_npc = related_npc
        if action_text and not lead.suggested_action:
            lead.suggested_action = action_text
        if clean_category != "other" and lead.category == "other":
            lead.category = clean_category
        if clean_status == "corroborated" and lead.status in {"new", "active", "uncorroborated"}:
            lead.status = "corroborated"
        if _normalize_status(lead.status) != previous_status:
            lead.last_updated_day = max(0, int(getattr(player, "day", 0) or 0))
        sync_legacy_leads(player)
        return (lead, False)
    lead = LeadRecord(
        text=clean_text,
        source=str(source).strip(),
        location=str(location).strip(),
        related_npc=str(related_npc).strip(),
        status=clean_status,
        suggested_action=action_text,
        category=clean_category,
        last_updated_day=max(0, int(getattr(player, "day", 0) or 0)),
    )
    player.lead_records.append(lead)
    sync_legacy_leads(player)
    return (lead, True)


def open_leads(player) -> list[LeadRecord]:
    return [
        lead
        for lead in player.lead_records
        if lead.text and _normalize_status(lead.status) in OPEN_LEAD_STATUSES
    ]


def recent_lead_changes(player, limit: int = 5) -> list[LeadRecord]:
    changes = [
        lead
        for lead in player.lead_records
        if lead.text
        and (
            _normalize_status(lead.status) in CLOSED_LEAD_STATUSES
            or lead.last_updated_day > 0
            and _normalize_status(lead.status) == "corroborated"
        )
    ]
    if not changes:
        return []
    order = {id(lead): index for index, lead in enumerate(player.lead_records)}
    ranked = sorted(
        changes,
        key=lambda lead: (max(0, int(lead.last_updated_day or 0)), order[id(lead)]),
        reverse=True,
    )
    return ranked[:limit]


def sync_legacy_leads(player) -> None:
    player.leads = [lead.text for lead in open_leads(player)]


def set_lead_status(player, lead_ref, status: str) -> LeadRecord:
    lead = _resolve_lead(player, lead_ref)
    lead.status = _normalize_status(status)
    lead.last_updated_day = max(0, int(getattr(player, "day", 0) or 0))
    sync_legacy_leads(player)
    return lead


def follow_lead(world: World, rng: random.Random, index: int = 0) -> str:
    player = world.player_state
    leads = open_leads(player)
    if not leads:
        raise RuntimeError("There are no open leads to follow.")
    if index < 0 or index >= len(leads):
        raise ValueError("Choose a valid open lead.")
    lead = leads[index]
    advance_time(player, 1)
    if lead.category == "talk":
        message, resource_impact = _follow_talk_lead(world, lead, rng)
    elif lead.category == "investigate":
        message, resource_impact = _follow_investigate_lead(world, lead, rng)
    elif lead.category == "explore":
        message, resource_impact = _follow_explore_lead(world, lead, rng)
    elif lead.category == "faction":
        message, resource_impact = _follow_faction_lead(world, lead, rng)
    elif lead.category == "downtime":
        message, resource_impact = _follow_downtime_lead(world, lead, rng)
    else:
        message, resource_impact = _follow_generic_lead(world, lead, rng)
    append_timeline_entry(
        player,
        message,
        action_type="lead",
        location_context=player.current_location,
        npc_name=lead.related_npc,
        location_name=lead.location,
        lead_ref=lead.text,
        resource_impact=resource_impact,
    )
    return message


def format_open_leads(world: World | None) -> str:
    if world is None:
        return "No active world."
    leads = open_leads(world.player_state)
    if not leads:
        return "No open leads."
    return "\n".join(_format_lead_line(lead) for lead in leads)


def format_recent_lead_changes(world: World | None) -> str:
    if world is None:
        return "No active world."
    leads = recent_lead_changes(world.player_state)
    if not leads:
        return "No recently advanced leads."
    return "\n".join(_format_lead_change_line(lead) for lead in leads)


def format_suggested_next_actions(world: World | None) -> str:
    if world is None:
        return "No active world."
    grouped: dict[str, list[str]] = defaultdict(list)
    for lead in open_leads(world.player_state):
        grouped[_normalize_category(lead.category)].append(lead.suggested_action or lead.text)
    if not grouped:
        return "No suggested next actions."
    lines: list[str] = []
    for category in ("talk", "investigate", "explore", "faction", "downtime", "other"):
        actions = _dedupe(grouped.get(category, []))
        if not actions:
            continue
        lines.append(f"{LEAD_CATEGORY_TITLES[category]}:")
        lines.extend(f"- {action}" for action in actions)
        lines.append("")
    return "\n".join(lines[:-1] if lines and not lines[-1] else lines)


def _follow_talk_lead(world: World, lead: LeadRecord, rng: random.Random) -> tuple[str, str]:
    player = world.player_state
    npc = _npc_for_lead(world, lead) or rng.choice(world.npcs)
    _append_unique(player.known_npc_ids, npc.entity_id)
    if lead.status in {"new", "active", "uncorroborated"}:
        set_lead_status(player, lead, "corroborated")
        add_lead(
            player,
            f"Follow up on {npc.name}'s account: {npc.useful_information}",
            source=npc.name,
            location=npc.location,
            related_npc=npc.name,
            status="new",
            suggested_action=f"Investigate what {npc.name} revealed: {npc.useful_information}.",
            category="investigate",
        )
        return (
            f"Lead followed: you speak with {npc.name} at {npc.location}. Their account holds together, "
            f"so the lead is now corroborated. They point you toward a sharper clue: {npc.useful_information}.",
            "",
        )
    set_lead_status(player, lead, "resolved")
    add_lead(
        player,
        f"Search {npc.location} for signs tied to {npc.secret}.",
        source=npc.name,
        location=npc.location,
        related_npc=npc.name,
        status="new",
        suggested_action=f"Inspect {npc.location} for signs tied to {npc.secret}.",
        category="explore",
    )
    return (
        f"Lead followed: {npc.name} gives you a usable answer and this thread is resolved. "
        f"They leave you with a fresh place to inspect near {npc.location}.",
        "",
    )


def _follow_investigate_lead(world: World, lead: LeadRecord, rng: random.Random) -> tuple[str, str]:
    player = world.player_state
    location = _location_for_lead(world, lead)
    if location is not None:
        _append_unique(player.known_location_ids, location.entity_id)
    if not any((lead.location, lead.related_npc, lead.source)):
        set_lead_status(player, lead, "stale")
        return (
            "Lead followed: the trail goes cold before you can pin it to a person or place. "
            "Mark the lead as stale until new evidence appears.",
            "",
        )
    if lead.status in {"new", "active", "uncorroborated"}:
        set_lead_status(player, lead, "corroborated")
        warning = location.hidden_detail if location else world.local_threat
        return (
            f"Lead followed: your investigation confirms the thread. The lead is now corroborated, "
            f"and the strongest warning points to {warning}.",
            "",
        )
    set_lead_status(player, lead, "resolved")
    follow_up = location.hidden_detail if location else world.adventure_hook.first_clue
    add_lead(
        player,
        f"Press deeper on the clue: {follow_up}",
        source=lead.source or "Lead follow-up",
        location=location.name if location else world.settlement.name,
        related_npc=lead.related_npc,
        status="new",
        suggested_action=f"Investigate the newly confirmed clue: {follow_up}.",
        category="explore" if location else "investigate",
    )
    return (
        f"Lead followed: your investigation turns up a concrete result and resolves the original thread. "
        f"You leave with a sharper follow-up clue: {follow_up}.",
        "",
    )


def _follow_explore_lead(world: World, lead: LeadRecord, rng: random.Random) -> tuple[str, str]:
    player = world.player_state
    player.supplies = max(0, player.supplies - 1)
    player.water = max(0, player.water - 1)
    location = _location_for_lead(world, lead)
    if location is not None:
        _append_unique(player.known_location_ids, location.entity_id)
    if lead.status in {"new", "active", "uncorroborated"}:
        set_lead_status(player, lead, "corroborated")
        warning = world.local_threat if location is None else location.hidden_detail
        return (
            f"Lead followed: you spend supplies to scout the thread directly. The signs are real, so the lead is now corroborated. "
            f"The clearest warning is {warning}.",
            "supplies -1, water -1",
        )
    set_lead_status(player, lead, "resolved")
    npc = _npc_for_lead(world, lead) or rng.choice(world.npcs)
    _append_unique(player.known_npc_ids, npc.entity_id)
    add_lead(
        player,
        f"Bring what you learned to {npc.name} for interpretation.",
        source=lead.location or npc.location,
        location=npc.location,
        related_npc=npc.name,
        status="new",
        suggested_action=f"Speak with {npc.name} about what the exploration revealed.",
        category="talk",
    )
    return (
        f"Lead followed: the site yields something concrete and the original lead is resolved. "
        f"You pay for the trip in supplies, but now have a person worth consulting.",
        "supplies -1, water -1",
    )


def _follow_faction_lead(world: World, lead: LeadRecord, rng: random.Random) -> tuple[str, str]:
    player = world.player_state
    note = f"Faction note: {lead.text}"
    _append_unique(player.quest_log, note)
    if lead.status in {"new", "active", "uncorroborated"}:
        set_lead_status(player, lead, "corroborated")
        npc = _npc_for_lead(world, lead) or rng.choice(world.npcs)
        add_lead(
            player,
            f"Ask {npc.name} who profits from the local tension.",
            source=lead.source or world.settlement.name,
            location=npc.location,
            related_npc=npc.name,
            status="new",
            suggested_action=f"Speak with {npc.name} about the local faction pressure.",
            category="talk",
        )
        return (
            "Lead followed: quiet inquiries confirm that the tension is real. The lead is now corroborated, "
            "and you record a faction note for later use.",
            "",
        )
    set_lead_status(player, lead, "resolved")
    return (
        "Lead followed: the faction thread settles into a usable note and the immediate lead is resolved.",
        "",
    )


def _follow_downtime_lead(world: World, lead: LeadRecord, rng: random.Random) -> tuple[str, str]:
    player = world.player_state
    if lead.status in {"new", "active", "uncorroborated"}:
        set_lead_status(player, lead, "corroborated")
        _append_unique(
            player.quest_log,
            f"Downtime follow-up confirmed: {lead.text}",
        )
        return (
            "Lead followed: the downtime result proves useful in practice. The lead is now corroborated and recorded for later play.",
            "",
        )
    set_lead_status(player, lead, "resolved")
    return (
        "Lead followed: you turn the downtime thread into a concrete next step and mark it resolved.",
        "",
    )


def _follow_generic_lead(world: World, lead: LeadRecord, rng: random.Random) -> tuple[str, str]:
    player = world.player_state
    if lead.status in {"new", "active", "uncorroborated"}:
        set_lead_status(player, lead, "corroborated")
        return (
            "Lead followed: the thread survives closer scrutiny and is now corroborated.",
            "",
        )
    set_lead_status(player, lead, "failed")
    return (
        "Lead followed: the supposed thread collapses under scrutiny and is marked failed.",
        "",
    )


def _format_lead_line(lead: LeadRecord) -> str:
    category = LEAD_CATEGORY_TITLES[_normalize_category(lead.category)]
    status = LEAD_STATUS_TITLES[_normalize_status(lead.status)]
    return f"- [{status} | {category}] {lead.suggested_action or lead.text}"


def _format_lead_change_line(lead: LeadRecord) -> str:
    status = LEAD_STATUS_TITLES[_normalize_status(lead.status)]
    return f"- [{status}] {lead.text}"


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        clean = str(value).strip()
        key = _normalize(clean)
        if not clean or key in seen:
            continue
        seen.add(key)
        ordered.append(clean)
    return ordered


def _merge_source(lead: LeadRecord, source: str) -> None:
    clean = str(source).strip()
    if not clean:
        return
    sources = [item.strip() for item in lead.source.split(" | ") if item.strip()]
    if clean not in sources:
        sources.append(clean)
        lead.source = " | ".join(sources)
        if lead.status in {"new", "active", "uncorroborated"} and len(sources) > 1:
            lead.status = "corroborated"


def _resolve_lead(player, lead_ref) -> LeadRecord:
    if isinstance(lead_ref, LeadRecord):
        return lead_ref
    normalized = _normalize(str(lead_ref))
    for lead in player.lead_records:
        if _normalize(lead.text) == normalized:
            return lead
    raise ValueError("Unknown lead reference.")


def _npc_for_lead(world: World, lead: LeadRecord):
    preferred = {lead.related_npc.strip(), lead.source.strip()}
    preferred = {item for item in preferred if item}
    for npc in world.npcs:
        if npc.name in preferred:
            return npc
    if lead.location:
        for npc in world.npcs:
            if npc.location == lead.location:
                return npc
    return None


def _location_for_lead(world: World, lead: LeadRecord):
    for location in world.settlement.important_locations:
        if location.name == lead.location:
            return location
    return None



def _normalize(value: str) -> str:
    return " ".join(str(value).strip().casefold().split())


def _normalize_status(value: str) -> str:
    clean = _normalize(value)
    if clean == "false":
        return "failed"
    if clean in OPEN_LEAD_STATUSES | CLOSED_LEAD_STATUSES:
        return clean
    return "active"


def _normalize_category(value: str) -> str:
    clean = _normalize(value)
    if clean in LEAD_CATEGORY_TITLES:
        return clean
    return "other"
