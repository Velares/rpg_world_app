from __future__ import annotations

import random
from dataclasses import dataclass

from app.calendar import advance_time, format_timeline_prefix
from app.interaction_text import choose_interaction_text
from app.leads import add_lead
from app.models import CheckResult, World
from app.timeline import add_timeline_entry
from app.table_loader import TableLoader


DIFFICULTIES = {
    "Easy": 8,
    "Standard": 12,
    "Hard": 16,
    "Severe": 20,
}


@dataclass(frozen=True)
class ActionCheckDefinition:
    action_name: str
    bonus_type: str
    success_text: str


COMMON_CHECKS = {
    "search_area": ActionCheckDefinition(
        "Search Area", "exploration", "You identify the detail that does not belong."
    ),
    "sneak_past_danger": ActionCheckDefinition(
        "Sneak Past Danger", "stealth", "You pass through the danger's blind angle."
    ),
    "read_ancient_markings": ActionCheckDefinition(
        "Read Ancient Markings", "lore", "The dead script yields a useful warning."
    ),
    "negotiate_with_npc": ActionCheckDefinition(
        "Negotiate with NPC", "social", "You find terms the other party can accept."
    ),
    "track_creature": ActionCheckDefinition(
        "Track Creature", "survival", "The trail reveals where the creature feels safe."
    ),
    "force_dangerous_action": ActionCheckDefinition(
        "Force Dangerous Action", "combat", "You use timing and force without committing to battle."
    ),
}


class ActionResolver:
    """Rules-light d20 resolution that can be replaced without changing world generation."""

    def __init__(self, world: World, rng: random.Random, tables: TableLoader):
        self.world = world
        self.rng = rng
        self.tables = tables

    @property
    def player(self):
        return self.world.player_state

    def resolve(
        self,
        action_key: str,
        difficulty_name: str = "Standard",
        roll_override: int | None = None,
        consequence_override: str | None = None,
    ) -> CheckResult:
        if action_key not in COMMON_CHECKS:
            raise ValueError(f"Unknown check action: {action_key}")
        if difficulty_name not in DIFFICULTIES:
            raise ValueError(f"Unknown difficulty: {difficulty_name}")
        self._validate_context(action_key)

        definition = COMMON_CHECKS[action_key]
        roll_result = roll_override if roll_override is not None else self.rng.randint(1, 20)
        if not 1 <= roll_result <= 20:
            raise ValueError("A d20 roll must be between 1 and 20.")
        character = self.player.character
        bonus = character.bonuses.get(definition.bonus_type, 0) if character else 0
        difficulty = DIFFICULTIES[difficulty_name]
        total = roll_result + bonus
        outcome = self._outcome(roll_result, total, difficulty)
        consequence = consequence_override or self._consequence(action_key, outcome)
        narrative = self._narrative(definition, outcome)

        self._advance_time()
        applied = self._apply_consequence(consequence, outcome)
        result = CheckResult(
            action_name=definition.action_name,
            bonus_type=definition.bonus_type,
            roll_result=roll_result,
            bonus_used=bonus,
            total=total,
            difficulty_name=difficulty_name,
            difficulty_class=difficulty,
            outcome=outcome,
            narrative_result=narrative,
            consequence=applied,
        )
        self.player.last_check = result
        self.player.last_consequence = applied
        self._log(result)
        return result

    @staticmethod
    def _outcome(roll_result: int, total: int, difficulty: int) -> str:
        if roll_result == 1 or total <= difficulty - 8:
            return "critical failure"
        if roll_result == 20 or total >= difficulty + 5:
            return "critical success"
        if total >= difficulty:
            return "success"
        if total >= difficulty - 3:
            return "partial success"
        return "failure"

    def _consequence(self, action_key: str, outcome: str) -> str:
        tables = {
            "critical failure": {
                "search_area": "attract attention",
                "sneak_past_danger": "gain wound",
                "read_ancient_markings": "attract attention",
                "negotiate_with_npc": "worsen position",
                "track_creature": "gain wound",
                "force_dangerous_action": "gain wound",
            },
            "failure": {
                "search_area": "lose time",
                "sneak_past_danger": "attract attention",
                "read_ancient_markings": "lose time",
                "negotiate_with_npc": "worsen position",
                "track_creature": "lose supplies",
                "force_dangerous_action": "lose supplies",
            },
            "partial success": {
                "search_area": "lose supplies",
                "sneak_past_danger": "lose time",
                "read_ancient_markings": "attract attention",
                "negotiate_with_npc": "lose time",
                "track_creature": "lose time",
                "force_dangerous_action": "worsen position",
            },
            "success": {key: "reveal clue" for key in COMMON_CHECKS},
            "critical success": {key: "improve position" for key in COMMON_CHECKS},
        }
        return tables[outcome][action_key]

    def _narrative(self, definition: ActionCheckDefinition, outcome: str) -> str:
        if outcome == "critical failure":
            base = "The attempt exposes you to exactly the danger preparation was meant to avoid."
            category = "check_critical_failure_additions"
        elif outcome == "failure":
            base = "The evidence resists you, and the situation grows less forgiving."
            category = "check_failure_additions"
        elif outcome == "partial success":
            base = f"{definition.success_text} The price becomes clear immediately."
            category = "check_partial_success_additions"
        elif outcome == "success":
            base = definition.success_text
            category = "check_success_additions"
        else:
            base = f"{definition.success_text} You also gain leverage for what comes next."
            category = "check_critical_success_additions"
        addition = choose_interaction_text(
            self.tables,
            self.rng,
            category,
            settlement=self.world.settlement.name,
            dungeon=self.world.dungeon.name,
            wilderness=self.world.wilderness.name,
            clue=self.world.adventure_hook.first_clue,
            action_name=definition.action_name,
        )
        return f"{base} {addition}"

    def _apply_consequence(self, consequence: str, outcome: str) -> str:
        player = self.player
        if consequence == "lose time":
            self._advance_time()
            return "Lose time: another period passes."
        if consequence == "lose supplies":
            loss = min(player.supplies, 1 if outcome == "partial success" else 2)
            player.supplies -= loss
            return f"Lose supplies: {loss} removed."
        if consequence == "gain wound":
            player.wounds = min(6, player.wounds + 1)
            return "Gain wound: dangerous exposure leaves a lasting injury."
        if consequence == "attract attention":
            player.attention += 1
            return "Attract attention: nearby danger is now more alert."
        if consequence == "reveal clue":
            clue = self._reveal_clue()
            return f"Reveal clue: {clue}"
        if consequence == "improve position":
            player.position = min(3, player.position + 1)
            clue = self._reveal_clue()
            return f"Improve position: gain leverage and reveal {clue}"
        if consequence == "worsen position":
            player.position = max(-3, player.position - 1)
            return "Worsen position: the next risk begins from a disadvantage."
        raise ValueError(f"Unknown consequence: {consequence}")

    def _reveal_clue(self) -> str:
        player = self.player
        if player.current_location == "dungeon" and player.current_room_id:
            clue = self.world.dungeon.rooms[player.current_room_id - 1].clue
        elif player.current_location == "wilderness":
            clue = self.rng.choice(self.world.wilderness.encounter_table).reward_or_clue
        elif player.current_location == "town":
            clue = self.rng.choice(self.world.settlement.rumors)
        else:
            clue = self.world.adventure_hook.first_clue
        add_lead(
            player,
            f"Check result: investigate {clue}",
            source="Action check",
            location=player.current_location,
            status="new",
            suggested_action=f"Investigate {clue}.",
            category="investigate",
        )
        return clue

    def _advance_time(self) -> None:
        advance_time(self.player, 1)

    def _validate_context(self, action_key: str) -> None:
        location = self.player.current_location
        if action_key == "negotiate_with_npc" and location != "town":
            raise RuntimeError("Return to town to negotiate with an NPC.")
        if action_key == "track_creature" and location != "wilderness":
            raise RuntimeError("Travel to the wilderness to track a creature.")
        if action_key == "read_ancient_markings" and location not in {
            "dungeon",
            "dungeon_entrance",
        }:
            raise RuntimeError("Ancient markings are available at the dungeon.")
        if action_key == "sneak_past_danger" and not (
            self.player.pending_encounter_id or location in {"wilderness", "dungeon"}
        ):
            raise RuntimeError("There is no immediate danger to sneak past.")

    def _log(self, result: CheckResult) -> None:
        player = self.player
        entry = (
            f"{format_timeline_prefix(player)} - CHECK: {result.action_name} "
            f"[{result.bonus_type.title()}] d20 {result.roll_result} "
            f"{result.bonus_used:+d} = {result.total} vs "
            f"{result.difficulty_name} DC {result.difficulty_class}: "
            f"{result.outcome.upper()}. {result.narrative_result} "
            f"Consequence: {result.consequence}"
        )
        player.action_log.append(entry)
        player.event_log.append(entry)
        add_timeline_entry(
            player,
            result.narrative_result,
            action_type="check",
            location_context=player.current_location,
            resource_impact=result.consequence,
        )
