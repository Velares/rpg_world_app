from __future__ import annotations

import random
from dataclasses import asdict

from app.calendar import advance_days, append_timeline_entry
from app.models import ActiveDowntimeTask, World
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
        if remaining > 0 and self.rng.random() < 0.2:
            complication = self._format(
                active.complication_text,
                active=active,
                days=days,
                remaining=remaining,
            )
            append_timeline_entry(self.player, complication)
            parts.append(complication)
        if active.progress_days >= active.required_days:
            completion = self._format(
                active.completion_text,
                active=active,
                days=days,
                remaining=0,
            )
            effect_note = self._apply_completion_effect(active)
            full_completion = (
                f"{completion} {effect_note}".strip()
                if effect_note
                else completion
            )
            append_timeline_entry(self.player, full_completion)
            parts.append(full_completion)
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
