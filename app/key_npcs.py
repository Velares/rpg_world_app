from __future__ import annotations

import random

from app.calendar import append_timeline_entry, format_calendar
from app.models import NPC, NpcRelationship, World
from app.shared import find_npc_by_id, key_npcs as get_key_npcs
from app.table_loader import TableLoader


KEY_NPC_THRESHOLD = 5
RECENT_RELATIONSHIP_NOTES_LIMIT = 5
RELATIONSHIP_STATES = ("ally", "at_odds", "neutral", "unknown")
FACTION_TAGS = (
    "settlement_authority",
    "local_traders",
    "shrine_or_cult",
    "wilderness_threat",
    "dungeon_interest",
    "independent",
    "unknown",
)


def promote_key_npc_if_needed(
    world: World,
    npc: NPC,
    rng: random.Random,
    tables: TableLoader,
) -> list[str]:
    if npc.is_key_npc or npc.prominence_score < KEY_NPC_THRESHOLD:
        return []
    current_date = format_calendar(world.player_state.day, world.player_state.time_period)
    npc.is_key_npc = True
    npc.key_npc_since = current_date
    npc.faction_tag = infer_faction_tag(world, npc)
    npc.key_npc_reason = _format_text(
        tables,
        rng,
        "key_npc_tables",
        "key_npc_reasons",
        npc=npc.name,
        settlement_name=world.settlement.name,
        faction_tag=npc.faction_tag,
    )
    npc.key_npc_notes = _format_text(
        tables,
        rng,
        "key_npc_tables",
        "key_npc_notes",
        npc=npc.name,
        settlement_name=world.settlement.name,
        faction_tag=npc.faction_tag,
    )
    ensure_relationships_for_key_npc(world, npc, rng)
    return [
        (
            f"{npc.name} has become a key figure in {world.settlement.name}. "
            f"{npc.key_npc_reason}"
        )
    ]


def run_key_npc_interaction_phase(
    world: World,
    rng: random.Random,
    tables: TableLoader,
    trigger: str = "manual",
) -> str:
    key_npc_list = get_key_npcs(world)
    if len(key_npc_list) < 2:
        return ""
    for index, npc_a in enumerate(key_npc_list):
        for npc_b in key_npc_list[index + 1 :]:
            ensure_relationship_record(world, npc_a, npc_b, rng)
    relationships = [item for item in world.npc_relationships if _relationship_live(world, item)]
    if not relationships:
        return ""
    if world.last_key_npc_phase_day >= world.player_state.day:
        return ""
    relationship = rng.choice(relationships)
    chance = {
        "ally": 0.6,
        "at_odds": 0.7,
        "neutral": 0.35,
        "unknown": 0.2,
    }[relationship.relationship_state]
    if rng.random() > chance:
        world.last_key_npc_phase_day = world.player_state.day
        relationship.last_checked_date = format_calendar(
            world.player_state.day, world.player_state.time_period
        )
        return ""

    npc_a = _find_npc(world, relationship.npc_a_id)
    npc_b = _find_npc(world, relationship.npc_b_id)
    if npc_a is None or npc_b is None:
        return ""
    current_date = format_calendar(world.player_state.day, world.player_state.time_period)
    relationship.last_checked_date = current_date
    template_category = {
        "ally": "ally_phase_events",
        "at_odds": "at_odds_phase_events",
        "neutral": "neutral_phase_events",
        "unknown": "neutral_phase_events",
    }[relationship.relationship_state]
    text = _format_text(
        tables,
        rng,
        "key_npc_tables",
        template_category,
        npc_a=npc_a.name,
        npc_b=npc_b.name,
        settlement_name=world.settlement.name,
        faction_a=npc_a.faction_tag,
        faction_b=npc_b.faction_tag,
        trigger=trigger,
    )
    relationship.recent_event_notes.append(f"{current_date} - {text}")
    relationship.recent_event_notes = relationship.recent_event_notes[
        -RECENT_RELATIONSHIP_NOTES_LIMIT:
    ]
    _apply_phase_consequences(world, relationship, npc_a, npc_b, text)
    append_timeline_entry(
        world.player_state,
        text,
        action_type="faction_phase",
        npc_id=npc_a.entity_id,
        npc_name=f"{npc_a.name} / {npc_b.name}",
        location_context="town",
        resource_impact="",
    )
    world.last_key_npc_phase_day = world.player_state.day
    return text


def ensure_relationships_for_key_npc(
    world: World,
    new_key_npc: NPC,
    rng: random.Random,
) -> None:
    for other in world.npcs:
        if other.entity_id == new_key_npc.entity_id or not other.is_key_npc:
            continue
        ensure_relationship_record(world, new_key_npc, other, rng)


def ensure_relationship_record(
    world: World,
    npc_a: NPC,
    npc_b: NPC,
    rng: random.Random,
) -> NpcRelationship:
    pair = tuple(sorted((npc_a.entity_id, npc_b.entity_id)))
    for relationship in world.npc_relationships:
        if (relationship.npc_a_id, relationship.npc_b_id) == pair:
            return relationship
    current_date = format_calendar(world.player_state.day, world.player_state.time_period)
    state, affinity, reason = determine_relationship(world, npc_a, npc_b, rng)
    relationship = NpcRelationship(
        npc_a_id=pair[0],
        npc_b_id=pair[1],
        relationship_state=state,
        affinity_score=affinity,
        first_established_date=current_date,
        last_checked_date=current_date,
        reason_text=reason,
    )
    world.npc_relationships.append(relationship)
    world.normalize_relationship_records()
    return relationship


def infer_faction_tag(world: World, npc: NPC) -> str:
    location = next(
        (
            item
            for item in world.settlement.important_locations
            if item.entity_id == npc.location_id or item.name == npc.location
        ),
        None,
    )
    location_type = (location.type if location else "").casefold()
    profession = npc.profession.casefold()
    useful = npc.useful_information.casefold()
    secret = npc.secret.casefold()

    if any(word in profession for word in ("guard", "captain", "warden", "constable", "mayor")):
        return "settlement_authority"
    if any(word in profession for word in ("merchant", "trader", "innkeeper", "shopkeeper", "broker")):
        return "local_traders"
    if "shrine" in location_type or any(word in profession for word in ("priest", "acolyte", "oracle")):
        return "shrine_or_cult"
    if any(word in useful or word in secret for word in ("dungeon", "relic", "artifact", "ruin")):
        return "dungeon_interest"
    if any(word in useful or word in secret for word in ("forest", "road", "beast", "wilderness", "trail")):
        return "wilderness_threat"
    if any(word in location_type for word in ("market", "shop", "inn", "warehouse")):
        return "local_traders"
    if any(word in location_type for word in ("hall", "watch", "court")):
        return "settlement_authority"
    return "independent"


def determine_relationship(
    world: World,
    npc_a: NPC,
    npc_b: NPC,
    rng: random.Random,
) -> tuple[str, int, str]:
    score = 0
    reasons: list[str] = []
    if npc_a.faction_tag == npc_b.faction_tag and npc_a.faction_tag != "unknown":
        score += 2
        reasons.append("shared faction ties")
    if npc_a.location_id and npc_a.location_id == npc_b.location_id:
        score += 1
        reasons.append("shared location")
    if (
        {"settlement_authority", "local_traders"} & {npc_a.faction_tag, npc_b.faction_tag}
        and {"wilderness_threat", "dungeon_interest"} & {npc_a.faction_tag, npc_b.faction_tag}
    ):
        score -= 2
        reasons.append("competing local priorities")
    if (
        npc_a.entity_id in world.player_state.known_npc_ids
        and npc_b.entity_id in world.player_state.known_npc_ids
    ):
        score += 1
        reasons.append("both known to the player")
    if npc_a.fear and npc_a.fear == npc_b.useful_information:
        score -= 1
        reasons.append("personal distrust")
    if score >= 2:
        return ("ally", score, ", ".join(reasons) or "mutual interest")
    if score <= -1:
        return ("at_odds", score, ", ".join(reasons) or "clashing interests")
    roll = rng.random()
    if roll < 0.2:
        return ("ally", 1, ", ".join(reasons) or "quiet coordination")
    if roll > 0.8:
        return ("at_odds", -1, ", ".join(reasons) or "smoldering friction")
    return ("neutral", 0, ", ".join(reasons) or "no clear alignment")


def _apply_phase_consequences(
    world: World,
    relationship: NpcRelationship,
    npc_a: NPC,
    npc_b: NPC,
    text: str,
) -> None:
    if relationship.relationship_state == "ally":
        lead = f"Follow the cooperation between {npc_a.name} and {npc_b.name}."
        if lead not in world.player_state.leads:
            world.player_state.leads.append(lead)
        for tag in {npc_a.faction_tag, npc_b.faction_tag} - {"unknown"}:
            world.faction_status_notes[tag] = "allied"
    elif relationship.relationship_state == "at_odds":
        note = f"Rumor: {npc_a.name} and {npc_b.name} are pulling the settlement in different directions."
        if note not in world.player_state.quest_log:
            world.player_state.quest_log.append(note)
        for tag in {npc_a.faction_tag, npc_b.faction_tag} - {"unknown"}:
            world.faction_status_notes[tag] = "tense"
    else:
        if text not in world.player_state.leads:
            world.player_state.leads.append(f"Watch how {npc_a.name} and {npc_b.name} move next.")
        for tag in {npc_a.faction_tag, npc_b.faction_tag} - {"unknown"}:
            world.faction_status_notes.setdefault(tag, "stable")


def _relationship_live(world: World, relationship: NpcRelationship) -> bool:
    return _find_npc(world, relationship.npc_a_id) is not None and _find_npc(
        world, relationship.npc_b_id
    ) is not None


def _find_npc(world: World, npc_id: str) -> NPC | None:
    return find_npc_by_id(world, npc_id)


def _format_text(
    tables: TableLoader,
    rng: random.Random,
    table_name: str,
    category: str,
    **context,
) -> str:
    template = tables.choose(table_name, category, rng)
    try:
        return str(template).format(**context)
    except KeyError:
        return str(template)
