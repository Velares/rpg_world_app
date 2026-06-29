from __future__ import annotations


EDITOR_CATEGORIES = [
    ("Monster Editor / Monster Import Review", "monsters"),
    ("NPC Editor", "npcs"),
    ("PC Editor", "pcs"),
    ("Item Editor", "items"),
    ("Spell Editor", "spells"),
]

MONSTER_EDITOR_SUBCATEGORIES = [
    ("Canonical Candidate Review", "canonical_candidate_review"),
    ("Normalized Monster Review", "normalized_monster_review"),
    ("Corrected Staging Preview", "corrected_staging_preview"),
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
        "Available categories:",
        "",
        "- Monster Editor — inspect and correct monster records.",
        "- NPC Editor — not implemented yet.",
        "- PC Editor — not implemented yet.",
        "- Item Editor — not implemented yet.",
        "- Spell Editor — not implemented yet.",
    ]
    return "\n".join(lines)


def get_monster_editor_subcategories() -> list[tuple[str, str]]:
    """Return the list of monster editor sub-category labels and keys."""
    return list(MONSTER_EDITOR_SUBCATEGORIES)


def monster_editor_summary_text() -> str:
    """Return the summary text for the Monster Editor sub-hub."""
    lines = [
        "MONSTER EDITOR",
        "==============",
        "",
        "Select a review surface.",
        "",
        "- Canonical Candidate Review: approve/reject likely same-monster matches.",
        "- Normalized Monster Review: inspect imported monster records and correct fields.",
        "- Corrected Staging Preview: view a non-live corrected dataset built from "
        "normalized records and stored corrections.",
        "",
        "Use Canonical Candidate Review to approve/reject likely same-monster matches.",
        "Use Normalized Monster Review to inspect imported monster records and correct fields.",
        "Use Corrected Staging Preview to inspect a non-live corrected monster dataset.",
        "Corrections are stored separately and do not modify source imports or the live catalog.",
        "",
        "Review only. No source records or catalogs are modified.",
    ]
    return "\n".join(lines)
