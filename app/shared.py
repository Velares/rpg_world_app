"""Shared utility functions used across multiple modules.

Consolidates small helpers that were previously duplicated in exporters,
gui, timeline, leads, downtime, exploration, and key_npcs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models import Encounter, Location, NPC, World


# ---------------------------------------------------------------------------
# Guard text
# ---------------------------------------------------------------------------

NO_WORLD_TEXT = (
    "NO ACTIVE WORLD\n"
    "===============\n"
    "Generate or load a world first."
)


# ---------------------------------------------------------------------------
# List helpers
# ---------------------------------------------------------------------------

def append_unique(values: list, value) -> None:
    """Append *value* to *values* only if it is not already present."""
    if value not in values:
        values.append(value)


# ---------------------------------------------------------------------------
# Text formatting
# ---------------------------------------------------------------------------

def seed_text(world: "World") -> str:
    """Human-readable seed string for display."""
    return world.generation_seed or "Random / not recorded"


def bulleted_lines(values: list[str]) -> str:
    """Return values as a bulleted list string."""
    return "\n".join(f"- {value}" for value in values)


def numbered_lines(values: list[str]) -> str:
    """Return values as a numbered list string."""
    return "\n".join(f"{i}. {v}" for i, v in enumerate(values, 1))


def bulleted_or_fallback(values: list[str], fallback: str) -> str:
    """Return a bulleted list or *fallback* when empty."""
    return "\n".join(f"- {v}" for v in values if v) or fallback


def numbered_or_fallback(values: list[str], fallback: str) -> str:
    """Return a numbered list or *fallback* when empty."""
    return "\n".join(
        f"{i}. {v}" for i, v in enumerate((v for v in values if v), 1)
    ) or fallback


def body_only(text: str) -> str:
    """Strip the first 4 header lines from a formatted text block."""
    lines = text.splitlines()
    if len(lines) <= 3:
        return text
    return "\n".join(lines[4:]).strip() or text


def body_lines(text: str) -> list[str]:
    """Return the body portion (after the first 4 header lines) as a list."""
    lines = text.splitlines()
    if len(lines) <= 4:
        return lines
    return lines[4:] or lines


# ---------------------------------------------------------------------------
# World query helpers
# ---------------------------------------------------------------------------

def find_npc_by_id(world: "World", npc_id: str) -> "NPC | None":
    """Find an NPC in *world* by entity_id, or return None."""
    return next((npc for npc in world.npcs if npc.entity_id == npc_id), None)


def find_location_by_id(world: "World", location_id: str) -> "Location | None":
    """Find a settlement location in *world* by entity_id, or return None."""
    return next(
        (loc for loc in world.settlement.important_locations
         if loc.entity_id == location_id),
        None,
    )


def find_encounter_by_id(world: "World", encounter_id: str) -> "Encounter | None":
    """Find a wilderness encounter in *world* by entity_id, or return None."""
    return next(
        (enc for enc in world.wilderness.encounter_table
         if enc.entity_id == encounter_id),
        None,
    )


def prominent_npcs(world: "World") -> list["NPC"]:
    """Return NPCs marked as prominent."""
    return [npc for npc in world.npcs if npc.prominent]


def key_npcs(world: "World") -> list["NPC"]:
    """Return NPCs marked as key NPCs."""
    return [npc for npc in world.npcs if npc.is_key_npc]
