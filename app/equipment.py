from __future__ import annotations

EQUIPMENT_SLOTS = (
    "Head",
    "Face",
    "Earring 1",
    "Earring 2",
    "Necklace",
    "Chest",
    "Legs",
    "Hands",
    "Ring Finger 1",
    "Ring Finger 2",
    "Ring Finger 3",
    "Ring Finger 4",
    "Belt",
    "Back",
    "Main Hand",
    "Off Hand",
    "Backpack / Container",
)

HAND_SLOTS = ("Main Hand", "Off Hand")
COIN_PER_POUND = 20
ENCUMBRANCE_STATES = (
    "unencumbered",
    "burdened",
    "heavily_burdened",
    "overloaded",
)


def default_equipment_slots() -> dict[str, str]:
    return {slot: "" for slot in EQUIPMENT_SLOTS}


def encumbrance_thresholds(strength_score: int) -> dict[str, int]:
    safe_strength = max(1, int(strength_score))
    return {
        "unencumbered_max": safe_strength,
        "burdened_max": safe_strength + 4,
        "heavily_burdened_max": safe_strength + 8,
    }


def encumbrance_state(total_bulk: float, strength_score: int) -> str:
    thresholds = encumbrance_thresholds(strength_score)
    if total_bulk <= thresholds["unencumbered_max"]:
        return "unencumbered"
    if total_bulk <= thresholds["burdened_max"]:
        return "burdened"
    if total_bulk <= thresholds["heavily_burdened_max"]:
        return "heavily_burdened"
    return "overloaded"


def encumbrance_effects(state: str) -> dict[str, str]:
    effects = {
        "unencumbered": {
            "movement": "No penalty.",
            "initiative": "No penalty.",
            "combat": "No penalty.",
            "travel_fatigue": "Normal travel pace.",
        },
        "burdened": {
            "movement": "Minor movement penalty placeholder.",
            "initiative": "Minor initiative penalty placeholder.",
            "combat": "No direct combat penalty yet.",
            "travel_fatigue": "Travel fatigue rises sooner.",
        },
        "heavily_burdened": {
            "movement": "Movement penalty placeholder.",
            "initiative": "Initiative penalty placeholder.",
            "combat": "Combat penalty placeholder.",
            "travel_fatigue": "Travel becomes tiring quickly.",
        },
        "overloaded": {
            "movement": "Severe movement restriction placeholder.",
            "initiative": "Severe initiative penalty placeholder.",
            "combat": "Severe combat penalty placeholder.",
            "travel_fatigue": "Travel is barely sustainable.",
        },
    }
    return effects.get(state, effects["unencumbered"])


def slot_label(slot_name: str) -> str:
    return slot_name.replace("_", " ")
