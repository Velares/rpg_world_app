from __future__ import annotations


EDITOR_CATEGORIES = [
    ("Monster Editor / Monster Import Review", "monsters"),
    ("NPC Editor", "npcs"),
    ("PC Editor", "pcs"),
    ("Item Editor", "items"),
    ("Spell Editor", "spells"),
]

_PLACEHOLDER_TEXT = {
    "npcs": (
        "NPC Editor\n==========\n\n"
        "Not implemented yet.\n\n"
        "Future purpose: review and edit imported and generated NPC records, "
        "including names, roles, affiliations, and derived stats."
    ),
    "pcs": (
        "PC Editor\n=========\n\n"
        "Not implemented yet.\n\n"
        "Future purpose: review and edit player character records, "
        "including class, level, equipment, and campaign history."
    ),
    "items": (
        "Item Editor\n===========\n\n"
        "Not implemented yet.\n\n"
        "Future purpose: review and edit imported magic, mundane, and treasure items, "
        "including source variants and normalized attributes."
    ),
    "spells": (
        "Spell Editor\n============\n\n"
        "Not implemented yet.\n\n"
        "Future purpose: review and edit imported spell records, "
        "including source variants, level, range, duration, and effects."
    ),
}


def get_editor_categories() -> list[tuple[str, str]]:
    """Return the list of editor category labels and keys."""
    return list(EDITOR_CATEGORIES)


def get_editor_placeholder_text(key: str) -> str:
    """Return the placeholder message for an editor category that is not yet implemented."""
    return _PLACEHOLDER_TEXT.get(
        key,
        "Not implemented yet.\n\nFuture purpose: review and edit this category of records.",
    )


def editors_hub_summary_text() -> str:
    """Return the summary text for the Editors hub screen."""
    lines = [
        "EDITORS HUB",
        "============",
        "",
        "Select an editor category from the list.",
        "",
        "- Monster Editor / Monster Import Review: inspect and approve/reject "
        "monster canonical-group candidates.",
        "- NPC Editor, PC Editor, Item Editor, Spell Editor: placeholders for future work.",
    ]
    return "\n".join(lines)
