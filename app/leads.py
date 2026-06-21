from __future__ import annotations

from collections import defaultdict

from app.models import LeadRecord, World


OPEN_LEAD_STATUSES = {"new", "active", "uncorroborated", "corroborated"}
LEAD_CATEGORY_TITLES = {
    "talk": "Talk",
    "investigate": "Investigate",
    "explore": "Explore",
    "faction": "Faction",
    "downtime": "Downtime",
    "other": "Other",
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


def sync_legacy_leads(player) -> None:
    player.leads = [lead.text for lead in open_leads(player)]


def format_open_leads(world: World | None) -> str:
    if world is None:
        return "No active world."
    leads = open_leads(world.player_state)
    if not leads:
        return "No open leads."
    return "\n".join(f"- {lead.suggested_action or lead.text}" for lead in leads)


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


def _normalize(value: str) -> str:
    return " ".join(str(value).strip().casefold().split())


def _normalize_status(value: str) -> str:
    clean = _normalize(value)
    if clean in OPEN_LEAD_STATUSES | {"resolved", "false"}:
        return clean
    return "active"


def _normalize_category(value: str) -> str:
    clean = _normalize(value)
    if clean in LEAD_CATEGORY_TITLES:
        return clean
    return "other"
