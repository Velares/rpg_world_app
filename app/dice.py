from __future__ import annotations

import random
import re

SUPPORTED_DICE = {4, 6, 8, 10, 12, 20, 30}
FORMULA = re.compile(r"^\s*(\d+)d(\d+)(?:\s*([+-])\s*(\d+))?\s*$", re.IGNORECASE)


def roll(formula: str, rng: random.Random | None = None) -> int:
    rng = rng or random.Random()
    match = FORMULA.match(formula)
    if not match:
        raise ValueError(f"Invalid dice formula: {formula!r}")
    count, sides = int(match.group(1)), int(match.group(2))
    if count < 1 or count > 100:
        raise ValueError("Dice count must be between 1 and 100")
    if sides not in SUPPORTED_DICE:
        raise ValueError(f"Unsupported die: d{sides}")
    modifier = int(match.group(4) or 0)
    if match.group(3) == "-":
        modifier = -modifier
    return sum(rng.randint(1, sides) for _ in range(count)) + modifier


def reaction_roll(rng: random.Random | None = None) -> str:
    total = roll("2d6", rng)
    if total <= 2:
        return "Hostile; attacks or issues an ultimatum"
    if total <= 5:
        return "Unfriendly; suspicious and demanding"
    if total <= 8:
        return "Uncertain; watches and waits"
    if total <= 11:
        return "Talkative; open to a reasonable offer"
    return "Helpful; offers aid or useful information"


def morale_check(morale: int, rng: random.Random | None = None) -> bool:
    if not 2 <= morale <= 12:
        raise ValueError("Morale must be between 2 and 12")
    return roll("2d6", rng) <= morale
