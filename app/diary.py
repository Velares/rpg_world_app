from __future__ import annotations

from collections import defaultdict
from uuid import uuid4

from app.calendar import calendar_date, format_calendar
from app.models import DiaryEntry

DIARY_SCOPES = ("daily", "weekly", "monthly", "yearly")
PROTECTED_IMPORTANCE_LEVELS = {"high", "critical"}
IMPORTANT_ACTION_LEVELS = {
    "world_start": "critical",
    "character": "high",
    "downtime": "medium",
    "encounter": "medium",
    "lead": "medium",
    "quest": "high",
    "npc_prominence": "high",
    "key_npc": "high",
    "faction_phase": "high",
}
IMPORTANCE_TITLES = {
    "ordinary": "Ordinary",
    "low": "Low",
    "medium": "Medium",
    "high": "High",
    "critical": "Critical",
}
ACTION_TITLES = {
    "world_start": "World Begins",
    "character": "Character Milestone",
    "downtime": "Downtime Progress",
    "encounter": "Encounter Development",
    "lead": "Lead Development",
    "quest": "Quest Development",
    "npc_prominence": "Prominent NPC",
    "key_npc": "Key NPC Milestone",
    "faction_phase": "Faction Shift",
}


def diary_entry(player, entry_id: str) -> DiaryEntry | None:
    return next(
        (entry for entry in player.diary_entries if entry.entry_id == entry_id),
        None,
    )


def create_diary_entry(
    player,
    title: str,
    text: str,
    *,
    player_notes: str = "",
    importance: str = "ordinary",
    source_action: str = "",
    protected: bool = False,
    auto_generated: bool = False,
) -> DiaryEntry:
    entry = DiaryEntry(
        entry_id=f"diary_{uuid4().hex[:12]}",
        title=title.strip() or "Diary Entry",
        text=text.strip() or "No text recorded.",
        created_day=max(1, int(player.day)),
        created_time_period=player.time_period,
        player_notes=player_notes.strip(),
        importance=importance,
        source_action=source_action,
        protected=protected,
        hidden=False,
        auto_generated=auto_generated,
    )
    player.diary_entries.append(entry)
    return entry


def add_manual_entry(player, title: str, text: str) -> DiaryEntry:
    if not title.strip():
        raise ValueError("Diary entry title is required.")
    if not text.strip():
        raise ValueError("Diary entry text is required.")
    return create_diary_entry(player, title, text)


def update_entry(
    player,
    entry_id: str,
    *,
    title: str | None = None,
    text: str | None = None,
    player_notes: str | None = None,
) -> DiaryEntry:
    entry = _require_entry(player, entry_id)
    if entry.protected:
        if title is not None and title.strip() != entry.title:
            raise RuntimeError("Protected diary milestones cannot change title.")
        if text is not None and text.strip() != entry.text:
            raise RuntimeError("Protected diary milestones cannot change original text.")
    else:
        if title is not None:
            clean_title = title.strip()
            if not clean_title:
                raise ValueError("Diary entry title is required.")
            entry.title = clean_title
        if text is not None:
            clean_text = text.strip()
            if not clean_text:
                raise ValueError("Diary entry text is required.")
            entry.text = clean_text
    if player_notes is not None:
        entry.player_notes = player_notes.strip()
    return entry


def hide_entry(player, entry_id: str) -> DiaryEntry:
    entry = _require_entry(player, entry_id)
    if entry.protected:
        raise RuntimeError("Protected diary milestones cannot be hidden.")
    entry.hidden = True
    return entry


def delete_entry(player, entry_id: str) -> None:
    entry = _require_entry(player, entry_id)
    if entry.protected:
        raise RuntimeError("Protected diary milestones cannot be deleted.")
    player.diary_entries = [
        item for item in player.diary_entries if item.entry_id != entry_id
    ]


def visible_entries(player) -> list[DiaryEntry]:
    return [entry for entry in player.diary_entries if not entry.hidden]


def entries_for_scope(player, scope: str) -> list[DiaryEntry]:
    if scope not in DIARY_SCOPES:
        raise ValueError(f"Unknown diary scope: {scope}")
    entries = visible_entries(player)
    return sorted(
        entries,
        key=lambda entry: (entry.created_day, entry.created_time_period, entry.entry_id),
        reverse=True,
    )


def format_entry(entry: DiaryEntry) -> str:
    lines = [
        entry.title,
        "-" * len(entry.title),
        f"When: {format_calendar(entry.created_day, entry.created_time_period)}",
        f"Importance: {IMPORTANCE_TITLES.get(entry.importance, entry.importance.title())}",
        f"Type: {'Protected milestone' if entry.protected else 'Ordinary entry'}",
        "",
        entry.text,
    ]
    if entry.player_notes:
        lines.extend(["", "Player Notes", "------------", entry.player_notes])
    return "\n".join(lines)


def format_scope_text(player, scope: str) -> str:
    if scope not in DIARY_SCOPES:
        raise ValueError(f"Unknown diary scope: {scope}")
    entries = entries_for_scope(player, scope)
    header = f"{scope.title()} Diary"
    lines = [header.upper(), "=" * len(header), ""]
    if not entries:
        lines.append("No diary entries recorded yet.")
        return "\n".join(lines)
    grouped: dict[str, list[DiaryEntry]] = defaultdict(list)
    for entry in entries:
        grouped[scope_label(entry, scope)].append(entry)
    for group_name in sorted(grouped.keys(), reverse=True):
        lines.append(group_name)
        lines.append("-" * len(group_name))
        for entry in grouped[group_name]:
            marker = "[Milestone] " if entry.protected else ""
            note_suffix = " (+notes)" if entry.player_notes else ""
            lines.append(
                f"- {marker}{entry.title}: {entry.text}{note_suffix}"
            )
        lines.append("")
    return "\n".join(lines).rstrip()


def recent_entries_text(player, limit: int = 5) -> str:
    entries = entries_for_scope(player, "daily")[:limit]
    if not entries:
        return "No diary entries recorded yet."
    lines = []
    for entry in entries:
        marker = "[Milestone] " if entry.protected else ""
        lines.append(
            f"- {marker}{entry.title} ({format_calendar(entry.created_day, entry.created_time_period)}): {entry.text}"
        )
    return "\n".join(lines)


def record_event_entry(player, action_type: str, result_text: str) -> DiaryEntry | None:
    importance = IMPORTANT_ACTION_LEVELS.get(action_type)
    if importance is None:
        return None
    protected = importance in PROTECTED_IMPORTANCE_LEVELS
    if player.diary_entries:
        recent = player.diary_entries[-1]
        if (
            recent.source_action == action_type
            and recent.text == result_text
            and recent.created_day == player.day
            and recent.created_time_period == player.time_period
        ):
            return recent
    return create_diary_entry(
        player,
        ACTION_TITLES.get(action_type, "Milestone"),
        result_text,
        importance=importance,
        source_action=action_type,
        protected=protected,
        auto_generated=True,
    )


def scope_label(entry: DiaryEntry, scope: str) -> str:
    date = calendar_date(entry.created_day, entry.created_time_period)
    if scope == "daily":
        return date.full_label()
    if scope == "weekly":
        week_of_year = ((date.absolute_day - 1) // 7) + 1
        return f"Year {date.year}, Week {week_of_year}"
    if scope == "monthly":
        return f"Year {date.year}, {date.season}"
    if scope == "yearly":
        return f"Year {date.year}"
    raise ValueError(f"Unknown diary scope: {scope}")


def _require_entry(player, entry_id: str) -> DiaryEntry:
    entry = diary_entry(player, entry_id)
    if entry is None:
        raise KeyError(f"No diary entry with id {entry_id}")
    return entry
