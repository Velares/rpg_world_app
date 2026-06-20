from __future__ import annotations

import random
from dataclasses import asdict

from app.calendar import advance_days, append_timeline_entry, calendar_date
from app.models import ActiveDowntimeTask, InventoryItem, World
from app.table_loader import TableLoader


class DowntimeEngine:
    def __init__(self, world: World, tables: TableLoader, rng: random.Random):
        self.world = world
        self.tables = tables
        self.rng = rng

    @property
    def player(self):
        return self.world.player_state

    def available_tasks(self) -> list[dict]:
        context = self.player.current_location
        tasks = []
        for task in self.tables.get("downtime_tables", "tasks"):
            if not isinstance(task, dict):
                continue
            contexts = task.get("allowed_contexts", [])
            if "any" in contexts or context in contexts:
                tasks.append(dict(task))
        return tasks

    def start_task(self, task_key: str) -> str:
        if self.player.character is None:
            raise RuntimeError("Create a character before starting downtime.")
        if self.player.active_downtime_task is not None:
            active = self.player.active_downtime_task
            raise RuntimeError(
                f"Finish or replace the active downtime task first: {active.name}."
            )
        definition = next(
            (task for task in self.available_tasks() if task.get("task_key") == task_key),
            None,
        )
        if definition is None:
            raise ValueError("Unknown or unavailable downtime task.")
        active = ActiveDowntimeTask(
            task_key=definition["task_key"],
            name=definition["name"],
            category=definition["category"],
            description=definition["description"],
            required_days=definition["default_duration_days"],
            allowed_contexts=list(definition.get("allowed_contexts", [])),
            progress_text=definition["progress_text"],
            completion_text=definition["completion_text"],
            complication_text=definition["complication_text"],
            tags=list(definition.get("tags", [])),
            progress_outcomes=list(definition.get("progress_outcomes", [])),
            completion_outcomes=list(definition.get("completion_outcomes", [])),
            complication_outcomes=list(definition.get("complication_outcomes", [])),
        )
        self.player.active_downtime_task = active
        append_timeline_entry(
            self.player,
            f"Downtime begins: {active.name}. {active.description}",
        )
        return f"Started downtime task: {active.name}."

    def advance_task(self, days: int = 1) -> str:
        if days <= 0:
            raise ValueError("Downtime must advance by at least one day.")
        if self.player.character is None:
            raise RuntimeError("Create a character before advancing downtime.")
        active = self.player.active_downtime_task
        if active is None:
            raise RuntimeError("Start a downtime task first.")

        advance_days(self.player, days)
        active.progress_days += days
        remaining = max(0, active.required_days - active.progress_days)
        progress_message = self._format(
            active.progress_text,
            active=active,
            days=days,
            remaining=remaining,
        )
        append_timeline_entry(self.player, progress_message)

        parts = [progress_message]
        progress_outcome = self._apply_outcome(
            active.progress_outcomes,
            active=active,
            days=days,
            remaining=remaining,
        )
        if progress_outcome:
            parts.append(progress_outcome)
        if remaining > 0 and self.rng.random() < 0.2:
            complication = self._format(
                active.complication_text,
                active=active,
                days=days,
                remaining=remaining,
            )
            append_timeline_entry(self.player, complication)
            parts.append(complication)
            complication_outcome = self._apply_outcome(
                active.complication_outcomes,
                active=active,
                days=days,
                remaining=remaining,
            )
            if complication_outcome:
                parts.append(complication_outcome)
        if active.progress_days >= active.required_days:
            completion = self._format(
                active.completion_text,
                active=active,
                days=days,
                remaining=0,
            )
            effect_note = self._apply_completion_effect(active)
            outcome_note = self._apply_outcome(
                active.completion_outcomes,
                active=active,
                days=days,
                remaining=0,
            )
            full_completion = (
                f"{completion} {effect_note}".strip()
                if effect_note
                else completion
            )
            append_timeline_entry(self.player, full_completion)
            parts.append(full_completion)
            if outcome_note:
                parts.append(outcome_note)
            self.player.active_downtime_task = None
        return " ".join(parts)

    @staticmethod
    def summarize(active: ActiveDowntimeTask | None) -> str:
        if active is None:
            return "None"
        remaining = max(0, active.required_days - active.progress_days)
        return (
            f"{active.name} ({active.progress_days}/{active.required_days} days, "
            f"{remaining} remaining)"
        )

    @staticmethod
    def serialize(active: ActiveDowntimeTask | None):
        return asdict(active) if active is not None else None

    def _apply_completion_effect(self, active: ActiveDowntimeTask) -> str:
        player = self.player
        if active.category == "recovery":
            recovered = min(player.wounds, 1)
            player.wounds -= recovered
            if recovered:
                return f"You recover {recovered} wound."
            return "The recovery still steadies your nerves."
        if active.category == "labor":
            earnings = max(1, active.required_days)
            player.coin += earnings
            return f"You gain {earnings} coin."
        if active.category in {"craft", "maintenance"}:
            player.supplies += 1
            return "You restore order to your kit and gain 1 supply."
        lead = f"Downtime result: follow up on {active.name.lower()}."
        if lead not in player.leads:
            player.leads.append(lead)
        return "You gain a new lead for future action."

    def _apply_outcome(
        self,
        outcomes: list[dict],
        active: ActiveDowntimeTask,
        days: int,
        remaining: int,
    ) -> str:
        if not outcomes:
            return ""
        outcome = dict(self.rng.choice(outcomes))
        context = self._context(active, outcome.get("discover"), days, remaining)
        text = self._format_outcome_text(
            outcome["text"],
            active=active,
            days=days,
            remaining=remaining,
            context=context,
            amount=outcome.get("amount"),
        )
        kind = outcome["kind"]
        if kind == "lead":
            self._append_unique(self.player.leads, text)
        elif kind == "quest_note":
            self._append_unique(self.player.quest_log, text)
        elif kind == "coin":
            self.player.coin = max(0, self.player.coin + outcome["amount"])
        elif kind == "supplies":
            self.player.supplies = max(0, self.player.supplies + outcome["amount"])
        elif kind == "inventory":
            self.player.add_inventory_item(
                InventoryItem(
                    item_key=outcome["item_key"],
                    name=outcome["item_name"],
                    category=outcome["item_category"],
                    quantity=outcome["quantity"],
                    description=outcome.get("description", ""),
                    tags=list(outcome.get("tags", [])),
                    quest_related=True,
                )
            )
        append_timeline_entry(self.player, text)
        return text

    def _context(
        self,
        active: ActiveDowntimeTask,
        discover: str | None,
        days: int,
        remaining: int,
    ) -> dict[str, object]:
        player = self.player
        world = self.world
        today = calendar_date(player.day, player.time_period)
        npc = self._choose_npc(discover == "npc")
        location = self._choose_location(discover == "location")
        rumor_index, rumor_text = self._choose_rumor(discover == "rumor")
        threat_name = self._choose_threat(discover == "threat")
        room = self._choose_room()
        encounter = self._choose_encounter()
        inventory_item = player.inventory[0] if player.inventory else None
        return {
            "settlement_name": world.settlement.name,
            "calendar_label": today.full_label(),
            "season": today.season,
            "day_of_season": today.day_of_season,
            "year": today.year,
            "npc_name": npc.name if npc else "a cautious local",
            "location_name": location.name if location else world.settlement.name,
            "rumor_text": rumor_text,
            "threat_name": threat_name,
            "dungeon_name": world.dungeon.name,
            "dungeon_room_name": room.name if room else world.dungeon.name,
            "wilderness_name": world.wilderness.name,
            "wilderness_clue": (
                encounter.reward_or_clue if encounter else world.wilderness.dominant_feature
            ),
            "lead_text": player.leads[0] if player.leads else f"Investigate {world.dungeon.name}",
            "quest_text": player.quest_log[0] if player.quest_log else "No standing quest",
            "character_name": (
                player.character.name if player.character else "the traveler"
            ),
            "character_class": (
                player.character.character_class if player.character else "wanderer"
            ),
            "background": (
                player.character.background if player.character else "unknown"
            ),
            "origin_detail": (
                player.character.origin_detail if player.character else "not recorded"
            ),
            "inventory_item_name": (
                inventory_item.name if inventory_item else "travel gear"
            ),
            "_reveal": {
                "npc_id": npc.entity_id if npc else "",
                "location_id": location.entity_id if location else "",
                "rumor_index": rumor_index,
                "threat_name": threat_name,
            },
        }

    def _choose_npc(self, prefer_unknown: bool):
        candidates = self.world.npcs
        if prefer_unknown:
            unknown = [
                npc for npc in candidates if npc.entity_id not in self.player.known_npc_ids
            ]
            if unknown:
                npc = self.rng.choice(unknown)
                self._append_unique(self.player.known_npc_ids, npc.entity_id)
                return npc
        known = [npc for npc in candidates if npc.entity_id in self.player.known_npc_ids]
        return self.rng.choice(known or candidates) if candidates else None

    def _choose_location(self, prefer_unknown: bool):
        candidates = self.world.settlement.important_locations
        if prefer_unknown:
            unknown = [
                location
                for location in candidates
                if location.entity_id not in self.player.known_location_ids
            ]
            if unknown:
                location = self.rng.choice(unknown)
                self._append_unique(self.player.known_location_ids, location.entity_id)
                return location
        known = [
            location
            for location in candidates
            if location.entity_id in self.player.known_location_ids
        ]
        return self.rng.choice(known or candidates) if candidates else None

    def _choose_rumor(self, prefer_unknown: bool) -> tuple[int, str]:
        rumors = self.world.settlement.rumors
        if not rumors:
            return (0, "No rumor is currently recorded.")
        known = set(self.player.known_rumor_indices)
        if prefer_unknown:
            unknown = [index for index in range(len(rumors)) if index not in known]
            if unknown:
                index = self.rng.choice(unknown)
                self._append_unique(self.player.known_rumor_indices, index)
                return (index, rumors[index])
        indices = list(known) or list(range(len(rumors)))
        index = self.rng.choice(indices)
        return (index, rumors[index])

    def _choose_threat(self, prefer_unknown: bool) -> str:
        if prefer_unknown:
            unknown = [
                encounter.creature_or_npc
                for encounter in self.world.wilderness.encounter_table
                if encounter.creature_or_npc not in self.player.known_threats
            ]
            if unknown:
                threat = self.rng.choice(unknown)
                self._append_unique(self.player.known_threats, threat)
                return threat
        if self.player.known_threats:
            return self.rng.choice(self.player.known_threats)
        if self.world.wilderness.encounter_table:
            return self.rng.choice(self.world.wilderness.encounter_table).creature_or_npc
        return self.world.local_threat

    def _choose_room(self):
        if self.world.dungeon.rooms:
            return self.rng.choice(self.world.dungeon.rooms)
        return None

    def _choose_encounter(self):
        if self.world.wilderness.encounter_table:
            return self.rng.choice(self.world.wilderness.encounter_table)
        return None

    @staticmethod
    def _append_unique(values: list, value) -> None:
        if value not in values:
            values.append(value)

    def _format_outcome_text(
        self,
        template: str,
        active: ActiveDowntimeTask,
        days: int,
        remaining: int,
        context: dict[str, object],
        amount: int | None = None,
    ) -> str:
        clean_context = {key: value for key, value in context.items() if not key.startswith("_")}
        return template.format(
            task_name=active.name,
            category=active.category,
            days=days,
            total_days=active.required_days,
            progress_days=active.progress_days,
            remaining_days=remaining,
            amount=amount if amount is not None else "",
            **clean_context,
        )

    @staticmethod
    def _format(template: str, active: ActiveDowntimeTask, days: int, remaining: int) -> str:
        return template.format(
            task_name=active.name,
            category=active.category,
            days=days,
            total_days=active.required_days,
            progress_days=active.progress_days,
            remaining_days=remaining,
        )
