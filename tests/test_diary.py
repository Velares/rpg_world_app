"""Unit tests for app.diary module."""

import unittest

from app.calendar import format_calendar
from app.diary import (
    ACTION_TITLES,
    DIARY_SCOPES,
    IMPORTANCE_TITLES,
    IMPORTANT_ACTION_LEVELS,
    PROTECTED_IMPORTANCE_LEVELS,
    add_manual_entry,
    create_diary_entry,
    delete_entry,
    diary_entry,
    entries_for_scope,
    format_entry,
    format_scope_text,
    hide_entry,
    recent_entries_text,
    record_event_entry,
    scope_label,
    update_entry,
    visible_entries,
)
from app.models import DiaryEntry, PlayerState


class DiaryEntryLookupTests(unittest.TestCase):
    def setUp(self):
        self.player = PlayerState()

    def test_diary_entry_returns_none_when_empty(self):
        self.assertIsNone(diary_entry(self.player, "nonexistent"))

    def test_diary_entry_finds_by_id(self):
        entry = create_diary_entry(self.player, "Test", "Body text")
        found = diary_entry(self.player, entry.entry_id)
        self.assertIs(found, entry)

    def test_diary_entry_returns_none_for_wrong_id(self):
        create_diary_entry(self.player, "Test", "Body")
        self.assertIsNone(diary_entry(self.player, "wrong_id"))


class CreateDiaryEntryTests(unittest.TestCase):
    def setUp(self):
        self.player = PlayerState()

    def test_creates_entry_with_defaults(self):
        entry = create_diary_entry(self.player, "Title", "Text")
        self.assertTrue(entry.entry_id.startswith("diary_"))
        self.assertEqual(entry.title, "Title")
        self.assertEqual(entry.text, "Text")
        self.assertEqual(entry.created_day, 1)
        self.assertEqual(entry.created_time_period, "Morning")
        self.assertEqual(entry.player_notes, "")
        self.assertEqual(entry.importance, "ordinary")
        self.assertEqual(entry.source_action, "")
        self.assertFalse(entry.protected)
        self.assertFalse(entry.hidden)
        self.assertFalse(entry.auto_generated)

    def test_strips_whitespace_from_title_and_text(self):
        entry = create_diary_entry(self.player, "  Title  ", "  Text  ")
        self.assertEqual(entry.title, "Title")
        self.assertEqual(entry.text, "Text")

    def test_blank_title_becomes_default(self):
        entry = create_diary_entry(self.player, "   ", "Text")
        self.assertEqual(entry.title, "Diary Entry")

    def test_blank_text_becomes_default(self):
        entry = create_diary_entry(self.player, "Title", "   ")
        self.assertEqual(entry.text, "No text recorded.")

    def test_respects_player_day_and_time(self):
        self.player.day = 5
        self.player.time_period = "Evening"
        entry = create_diary_entry(self.player, "Title", "Text")
        self.assertEqual(entry.created_day, 5)
        self.assertEqual(entry.created_time_period, "Evening")

    def test_day_below_one_clamped(self):
        self.player.day = -3
        entry = create_diary_entry(self.player, "Title", "Text")
        self.assertEqual(entry.created_day, 1)

    def test_entry_appended_to_player(self):
        entry = create_diary_entry(self.player, "Title", "Text")
        self.assertIn(entry, self.player.diary_entries)

    def test_custom_kwargs_applied(self):
        entry = create_diary_entry(
            self.player,
            "Title",
            "Text",
            player_notes="note",
            importance="high",
            source_action="quest",
            protected=True,
            auto_generated=True,
        )
        self.assertEqual(entry.player_notes, "note")
        self.assertEqual(entry.importance, "high")
        self.assertEqual(entry.source_action, "quest")
        self.assertTrue(entry.protected)
        self.assertTrue(entry.auto_generated)


class AddManualEntryTests(unittest.TestCase):
    def setUp(self):
        self.player = PlayerState()

    def test_creates_entry_successfully(self):
        entry = add_manual_entry(self.player, "My Title", "My Text")
        self.assertEqual(entry.title, "My Title")
        self.assertEqual(entry.text, "My Text")

    def test_blank_title_raises(self):
        with self.assertRaises(ValueError):
            add_manual_entry(self.player, "   ", "Text")

    def test_blank_text_raises(self):
        with self.assertRaises(ValueError):
            add_manual_entry(self.player, "Title", "   ")


class UpdateEntryTests(unittest.TestCase):
    def setUp(self):
        self.player = PlayerState()
        self.entry = create_diary_entry(self.player, "Original", "Body")

    def test_update_title(self):
        update_entry(self.player, self.entry.entry_id, title="New Title")
        self.assertEqual(self.entry.title, "New Title")

    def test_update_text(self):
        update_entry(self.player, self.entry.entry_id, text="New Body")
        self.assertEqual(self.entry.text, "New Body")

    def test_update_player_notes(self):
        update_entry(self.player, self.entry.entry_id, player_notes="A note")
        self.assertEqual(self.entry.player_notes, "A note")

    def test_blank_title_raises(self):
        with self.assertRaises(ValueError):
            update_entry(self.player, self.entry.entry_id, title="   ")

    def test_blank_text_raises(self):
        with self.assertRaises(ValueError):
            update_entry(self.player, self.entry.entry_id, text="   ")

    def test_protected_entry_rejects_title_change(self):
        protected = create_diary_entry(
            self.player, "Milestone", "Important", protected=True
        )
        with self.assertRaises(RuntimeError):
            update_entry(self.player, protected.entry_id, title="Changed")

    def test_protected_entry_rejects_text_change(self):
        protected = create_diary_entry(
            self.player, "Milestone", "Important", protected=True
        )
        with self.assertRaises(RuntimeError):
            update_entry(self.player, protected.entry_id, text="Changed")

    def test_protected_entry_allows_player_notes(self):
        protected = create_diary_entry(
            self.player, "Milestone", "Important", protected=True
        )
        update_entry(self.player, protected.entry_id, player_notes="My note")
        self.assertEqual(protected.player_notes, "My note")

    def test_protected_entry_allows_same_title(self):
        protected = create_diary_entry(
            self.player, "Milestone", "Important", protected=True
        )
        result = update_entry(self.player, protected.entry_id, title="Milestone")
        self.assertEqual(result.title, "Milestone")

    def test_nonexistent_entry_raises(self):
        with self.assertRaises(KeyError):
            update_entry(self.player, "fake_id", title="X")


class HideEntryTests(unittest.TestCase):
    def setUp(self):
        self.player = PlayerState()

    def test_hides_normal_entry(self):
        entry = create_diary_entry(self.player, "Title", "Text")
        result = hide_entry(self.player, entry.entry_id)
        self.assertTrue(result.hidden)

    def test_protected_entry_cannot_be_hidden(self):
        entry = create_diary_entry(self.player, "M", "T", protected=True)
        with self.assertRaises(RuntimeError):
            hide_entry(self.player, entry.entry_id)


class DeleteEntryTests(unittest.TestCase):
    def setUp(self):
        self.player = PlayerState()

    def test_deletes_normal_entry(self):
        entry = create_diary_entry(self.player, "Title", "Text")
        delete_entry(self.player, entry.entry_id)
        self.assertEqual(len(self.player.diary_entries), 0)

    def test_protected_entry_cannot_be_deleted(self):
        entry = create_diary_entry(self.player, "M", "T", protected=True)
        with self.assertRaises(RuntimeError):
            delete_entry(self.player, entry.entry_id)

    def test_nonexistent_entry_raises(self):
        with self.assertRaises(KeyError):
            delete_entry(self.player, "nonexistent_id")


class VisibleEntriesTests(unittest.TestCase):
    def setUp(self):
        self.player = PlayerState()

    def test_empty_returns_empty(self):
        self.assertEqual(visible_entries(self.player), [])

    def test_excludes_hidden(self):
        entry = create_diary_entry(self.player, "A", "B")
        hidden = create_diary_entry(self.player, "C", "D")
        hidden.hidden = True
        result = visible_entries(self.player)
        self.assertEqual(len(result), 1)
        self.assertIs(result[0], entry)


class EntriesForScopeTests(unittest.TestCase):
    def setUp(self):
        self.player = PlayerState()

    def test_invalid_scope_raises(self):
        with self.assertRaises(ValueError):
            entries_for_scope(self.player, "invalid_scope")

    def test_returns_sorted_entries(self):
        self.player.day = 1
        create_diary_entry(self.player, "First", "A")
        self.player.day = 3
        create_diary_entry(self.player, "Second", "B")
        result = entries_for_scope(self.player, "daily")
        self.assertEqual(result[0].title, "Second")
        self.assertEqual(result[1].title, "First")

    def test_all_scopes_work(self):
        create_diary_entry(self.player, "Title", "Text")
        for scope in DIARY_SCOPES:
            result = entries_for_scope(self.player, scope)
            self.assertEqual(len(result), 1)


class FormatEntryTests(unittest.TestCase):
    def test_basic_format(self):
        entry = DiaryEntry(
            entry_id="diary_test",
            title="My Title",
            text="Entry body.",
            created_day=1,
            created_time_period="Morning",
        )
        text = format_entry(entry)
        self.assertIn("My Title", text)
        self.assertIn("Entry body.", text)
        self.assertIn("When:", text)
        self.assertIn("Importance:", text)

    def test_format_with_player_notes(self):
        entry = DiaryEntry(
            entry_id="diary_test",
            title="Title",
            text="Text",
            created_day=1,
            created_time_period="Morning",
            player_notes="Some notes",
        )
        text = format_entry(entry)
        self.assertIn("Player Notes", text)
        self.assertIn("Some notes", text)

    def test_protected_milestone_label(self):
        entry = DiaryEntry(
            entry_id="diary_test",
            title="Title",
            text="Text",
            created_day=1,
            created_time_period="Morning",
            protected=True,
        )
        text = format_entry(entry)
        self.assertIn("Protected milestone", text)


class FormatScopeTextTests(unittest.TestCase):
    def setUp(self):
        self.player = PlayerState()

    def test_invalid_scope_raises(self):
        with self.assertRaises(ValueError):
            format_scope_text(self.player, "nope")

    def test_empty_entries_message(self):
        text = format_scope_text(self.player, "daily")
        self.assertIn("No diary entries recorded yet.", text)

    def test_daily_scope_header(self):
        create_diary_entry(self.player, "Title", "Text")
        text = format_scope_text(self.player, "daily")
        self.assertIn("DAILY DIARY", text)

    def test_weekly_scope_grouping(self):
        create_diary_entry(self.player, "Title", "Text")
        text = format_scope_text(self.player, "weekly")
        self.assertIn("Week", text)

    def test_monthly_scope_grouping(self):
        create_diary_entry(self.player, "Title", "Text")
        text = format_scope_text(self.player, "monthly")
        self.assertIn("Year", text)

    def test_yearly_scope_grouping(self):
        create_diary_entry(self.player, "Title", "Text")
        text = format_scope_text(self.player, "yearly")
        self.assertIn("Year", text)

    def test_protected_entry_shows_milestone_marker(self):
        create_diary_entry(self.player, "Mile", "Body", protected=True)
        text = format_scope_text(self.player, "daily")
        self.assertIn("[Milestone]", text)


class RecentEntriesTextTests(unittest.TestCase):
    def setUp(self):
        self.player = PlayerState()

    def test_no_entries(self):
        text = recent_entries_text(self.player)
        self.assertEqual(text, "No diary entries recorded yet.")

    def test_respects_limit(self):
        for i in range(10):
            self.player.day = i + 1
            create_diary_entry(self.player, f"Entry {i}", f"Text {i}")
        text = recent_entries_text(self.player, limit=3)
        lines = [line for line in text.splitlines() if line.startswith("- ")]
        self.assertEqual(len(lines), 3)


class RecordEventEntryTests(unittest.TestCase):
    def setUp(self):
        self.player = PlayerState()

    def test_unknown_action_type_returns_none(self):
        result = record_event_entry(self.player, "unknown_type", "text")
        self.assertIsNone(result)

    def test_known_action_type_creates_entry(self):
        result = record_event_entry(self.player, "quest", "Quest completed!")
        self.assertIsNotNone(result)
        self.assertEqual(result.text, "Quest completed!")
        self.assertEqual(result.importance, "high")
        self.assertTrue(result.protected)
        self.assertTrue(result.auto_generated)

    def test_medium_importance_not_protected(self):
        result = record_event_entry(self.player, "downtime", "Downtime done.")
        self.assertIsNotNone(result)
        self.assertEqual(result.importance, "medium")
        self.assertFalse(result.protected)

    def test_deduplicates_same_entry(self):
        result1 = record_event_entry(self.player, "encounter", "Fight!")
        result2 = record_event_entry(self.player, "encounter", "Fight!")
        self.assertIs(result1, result2)
        self.assertEqual(len(self.player.diary_entries), 1)

    def test_different_text_not_deduplicated(self):
        record_event_entry(self.player, "encounter", "Fight!")
        record_event_entry(self.player, "encounter", "Run!")
        self.assertEqual(len(self.player.diary_entries), 2)

    def test_different_day_not_deduplicated(self):
        record_event_entry(self.player, "encounter", "Fight!")
        self.player.day = 2
        record_event_entry(self.player, "encounter", "Fight!")
        self.assertEqual(len(self.player.diary_entries), 2)


class ScopeLabelTests(unittest.TestCase):
    def test_daily_label(self):
        entry = DiaryEntry(
            entry_id="x", title="T", text="B",
            created_day=1, created_time_period="Morning",
        )
        label = scope_label(entry, "daily")
        self.assertIn("Year", label)
        self.assertIn("Morning", label)

    def test_weekly_label(self):
        entry = DiaryEntry(
            entry_id="x", title="T", text="B",
            created_day=1, created_time_period="Morning",
        )
        label = scope_label(entry, "weekly")
        self.assertIn("Week", label)

    def test_monthly_label(self):
        entry = DiaryEntry(
            entry_id="x", title="T", text="B",
            created_day=1, created_time_period="Morning",
        )
        label = scope_label(entry, "monthly")
        self.assertIn("Year", label)

    def test_yearly_label(self):
        entry = DiaryEntry(
            entry_id="x", title="T", text="B",
            created_day=1, created_time_period="Morning",
        )
        label = scope_label(entry, "yearly")
        self.assertIn("Year", label)

    def test_invalid_scope_raises(self):
        entry = DiaryEntry(
            entry_id="x", title="T", text="B",
            created_day=1, created_time_period="Morning",
        )
        with self.assertRaises(ValueError):
            scope_label(entry, "century")


if __name__ == "__main__":
    unittest.main()
