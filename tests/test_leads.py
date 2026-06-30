"""Unit tests for app.leads module."""

import random
import unittest
from pathlib import Path

from app.leads import (
    CLOSED_LEAD_STATUSES,
    LEAD_CATEGORY_TITLES,
    LEAD_STATUS_TITLES,
    OPEN_LEAD_STATUSES,
    add_lead,
    follow_lead,
    format_open_leads,
    format_recent_lead_changes,
    format_suggested_next_actions,
    open_leads,
    recent_lead_changes,
    set_lead_status,
    sync_legacy_leads,
)
from app.models import (
    AdventureHook,
    Dungeon,
    Encounter,
    LeadRecord,
    Location,
    NPC,
    PlayerCharacter,
    PlayerState,
    Settlement,
    WildernessArea,
    World,
)


def _make_player():
    return PlayerState(
        character=PlayerCharacter(
            name="Hero",
            character_class="Fighter",
            background="Soldier",
            starting_supplies=10,
        )
    )


def _make_world(player=None):
    if player is None:
        player = _make_player()
    return World(
        name="Test World",
        settlement=Settlement(
            name="Testville",
            type="Village",
            population=100,
            wealth_level="Modest",
            government_type="Council",
            main_industry="Farming",
            secondary_industry="Trade",
            condition="Fair",
            local_problem="Rats",
            local_secret="Cave",
            nearby_danger="Goblins",
            weird_fantasy_detail="Stones",
            important_locations=[
                Location(
                    name="Market",
                    type="market",
                    condition="Good",
                    owner_or_keeper="Bob",
                    public_description="Busy",
                    hidden_detail="Passage",
                    rumor_connected="",
                    possible_encounter="Thief",
                    useful_resource="Supplies",
                    entity_id="loc_001",
                )
            ],
            rumors=["First rumor"],
        ),
        npcs=[
            NPC(
                name="Bob",
                age=40,
                ancestry="Human",
                profession="Merchant",
                location="Market",
                appearance="Stout",
                personality="Jovial",
                motivation="Profit",
                fear="Bandits",
                secret="Smuggler",
                relationship_to_town="Resident",
                attitude_toward_player="Friendly",
                useful_information="Knows roads",
                possible_service="Trade",
                danger_level="Low",
                entity_id="npc_001",
                location_id="loc_001",
            )
        ],
        dungeon=Dungeon(
            name="Caves",
            entrance_description="Dark",
            theme="Horror",
            danger_level="High",
            number_of_rooms=3,
            boss_or_final_threat="Dragon",
            treasure_or_secret="Gold",
            connection_to_town="Mine",
        ),
        wilderness=WildernessArea(
            name="Forest",
            terrain_type="Forest",
            weather="Rainy",
            dominant_feature="Trees",
            resources="Wood",
            travel_hazards="Mud",
            encounter_table=[
                Encounter(
                    what_player_notices_first="Rustling",
                    encounter_type="Beast",
                    creature_or_npc="Wolf",
                    intent="Hunt",
                    danger_level="Medium",
                    signs_or_foreshadowing="Tracks",
                    how_to_avoid="Quiet",
                    how_to_negotiate="No",
                    how_to_fight_safely="Fire",
                    preparation_that_helps="Torches",
                    reward_or_clue="Pelt",
                    morale=7,
                    reaction_roll_result="Hostile",
                    entity_id="enc_001",
                )
            ],
        ),
        adventure_hook=AdventureHook(
            trigger="Letter",
            major_goal="Artifact",
            obstacle="Guardian",
            location="Temple",
            location_feature="Altar",
            phenomenon="Magic",
            villain_goal="Domination",
            artifact_or_relic="Orb",
            theme="Mystery",
            key_npc="Sage",
            first_clue="Map",
            time_pressure="Moon",
            failure_consequence="Doom",
            noncombat_paths="Talk",
            entity_id="hook_001",
        ),
        local_threat="Goblins",
        player_state=player,
        created_at="2024-01-01",
    )


class AddLeadTests(unittest.TestCase):
    def setUp(self):
        self.player = _make_player()

    def test_add_new_lead(self):
        lead, is_new = add_lead(self.player, "Find the cave")
        self.assertTrue(is_new)
        self.assertEqual(lead.text, "Find the cave")
        self.assertEqual(lead.status, "active")

    def test_blank_lead_raises(self):
        with self.assertRaises(ValueError):
            add_lead(self.player, "   ")

    def test_duplicate_lead_not_added(self):
        add_lead(self.player, "Find the cave")
        lead, is_new = add_lead(self.player, "Find the cave")
        self.assertFalse(is_new)
        self.assertEqual(len(self.player.lead_records), 1)

    def test_duplicate_case_insensitive(self):
        add_lead(self.player, "Find The Cave")
        lead, is_new = add_lead(self.player, "find the cave")
        self.assertFalse(is_new)
        self.assertEqual(len(self.player.lead_records), 1)

    def test_source_merged_on_duplicate(self):
        add_lead(self.player, "Lead text", source="Source A")
        add_lead(self.player, "Lead text", source="Source B")
        self.assertIn("Source A", self.player.lead_records[0].source)
        self.assertIn("Source B", self.player.lead_records[0].source)

    def test_corroborated_on_multiple_sources(self):
        add_lead(self.player, "Lead text", source="Source A")
        add_lead(self.player, "Lead text", source="Source B")
        self.assertEqual(self.player.lead_records[0].status, "corroborated")

    def test_custom_status(self):
        lead, _ = add_lead(self.player, "A lead", status="new")
        self.assertEqual(lead.status, "new")

    def test_custom_category(self):
        lead, _ = add_lead(self.player, "A lead", category="talk")
        self.assertEqual(lead.category, "talk")

    def test_suggested_action_defaults_to_text(self):
        lead, _ = add_lead(self.player, "Follow the trail")
        self.assertEqual(lead.suggested_action, "Follow the trail")

    def test_explicit_suggested_action(self):
        lead, _ = add_lead(self.player, "Lead text", suggested_action="Do this")
        self.assertEqual(lead.suggested_action, "Do this")

    def test_syncs_legacy_leads(self):
        add_lead(self.player, "Active lead", status="active")
        self.assertIn("Active lead", self.player.leads)

    def test_location_set_on_duplicate_if_missing(self):
        add_lead(self.player, "Lead")
        add_lead(self.player, "Lead", location="Market")
        self.assertEqual(self.player.lead_records[0].location, "Market")

    def test_related_npc_set_on_duplicate_if_missing(self):
        add_lead(self.player, "Lead")
        add_lead(self.player, "Lead", related_npc="Bob")
        self.assertEqual(self.player.lead_records[0].related_npc, "Bob")


class OpenLeadsTests(unittest.TestCase):
    def setUp(self):
        self.player = _make_player()

    def test_empty_returns_empty(self):
        self.assertEqual(open_leads(self.player), [])

    def test_returns_open_statuses(self):
        add_lead(self.player, "Active one", status="active")
        add_lead(self.player, "New one", status="new")
        add_lead(self.player, "Resolved one", status="resolved")
        result = open_leads(self.player)
        self.assertEqual(len(result), 2)

    def test_excludes_resolved(self):
        add_lead(self.player, "Done", status="resolved")
        self.assertEqual(open_leads(self.player), [])


class SetLeadStatusTests(unittest.TestCase):
    def setUp(self):
        self.player = _make_player()
        add_lead(self.player, "Test lead")

    def test_set_status_resolved(self):
        lead = set_lead_status(self.player, "Test lead", "resolved")
        self.assertEqual(lead.status, "resolved")

    def test_set_status_failed(self):
        lead = set_lead_status(self.player, "Test lead", "failed")
        self.assertEqual(lead.status, "failed")

    def test_unknown_lead_raises(self):
        with self.assertRaises(ValueError):
            set_lead_status(self.player, "Nonexistent", "resolved")

    def test_accepts_lead_record_directly(self):
        record = self.player.lead_records[0]
        lead = set_lead_status(self.player, record, "stale")
        self.assertEqual(lead.status, "stale")


class RecentLeadChangesTests(unittest.TestCase):
    def setUp(self):
        self.player = _make_player()

    def test_empty_returns_empty(self):
        self.assertEqual(recent_lead_changes(self.player), [])

    def test_shows_closed_leads(self):
        self.player.day = 5
        add_lead(self.player, "Lead A")
        set_lead_status(self.player, "Lead A", "resolved")
        changes = recent_lead_changes(self.player)
        self.assertEqual(len(changes), 1)

    def test_respects_limit(self):
        for i in range(10):
            self.player.day = i + 1
            add_lead(self.player, f"Lead {i}")
            set_lead_status(self.player, f"Lead {i}", "resolved")
        changes = recent_lead_changes(self.player, limit=3)
        self.assertEqual(len(changes), 3)


class SyncLegacyLeadsTests(unittest.TestCase):
    def test_syncs_open_lead_texts(self):
        player = _make_player()
        add_lead(player, "Open lead A", status="active")
        add_lead(player, "Closed lead B", status="resolved")
        sync_legacy_leads(player)
        self.assertIn("Open lead A", player.leads)
        self.assertNotIn("Closed lead B", player.leads)


class FollowLeadTests(unittest.TestCase):
    def setUp(self):
        self.world = _make_world()
        self.rng = random.Random(42)

    def test_no_leads_raises(self):
        with self.assertRaises(RuntimeError):
            follow_lead(self.world, self.rng)

    def test_invalid_index_raises(self):
        add_lead(self.world.player_state, "A lead", category="talk")
        with self.assertRaises(ValueError):
            follow_lead(self.world, self.rng, index=5)

    def test_negative_index_raises(self):
        add_lead(self.world.player_state, "A lead", category="talk")
        with self.assertRaises(ValueError):
            follow_lead(self.world, self.rng, index=-1)

    def test_follow_talk_lead(self):
        add_lead(
            self.world.player_state,
            "Ask about the roads",
            category="talk",
            related_npc="Bob",
            location="Market",
        )
        result = follow_lead(self.world, self.rng, index=0)
        self.assertIsInstance(result, str)
        self.assertTrue(len(result) > 0)

    def test_follow_investigate_lead(self):
        add_lead(
            self.world.player_state,
            "Check the passage",
            category="investigate",
            location="Market",
            source="Bob",
        )
        result = follow_lead(self.world, self.rng, index=0)
        self.assertIsInstance(result, str)

    def test_follow_explore_lead(self):
        add_lead(
            self.world.player_state,
            "Explore the forest",
            category="explore",
            location="Market",
        )
        initial_supplies = self.world.player_state.supplies
        result = follow_lead(self.world, self.rng, index=0)
        self.assertIsInstance(result, str)
        self.assertLessEqual(self.world.player_state.supplies, initial_supplies)

    def test_follow_faction_lead(self):
        add_lead(
            self.world.player_state,
            "Investigate faction pressure",
            category="faction",
            related_npc="Bob",
        )
        result = follow_lead(self.world, self.rng, index=0)
        self.assertIsInstance(result, str)

    def test_follow_downtime_lead(self):
        add_lead(
            self.world.player_state,
            "Follow up on downtime",
            category="downtime",
        )
        result = follow_lead(self.world, self.rng, index=0)
        self.assertIsInstance(result, str)

    def test_follow_generic_lead(self):
        add_lead(
            self.world.player_state,
            "Check that old clue",
            category="other",
        )
        result = follow_lead(self.world, self.rng, index=0)
        self.assertIsInstance(result, str)


class FormatOpenLeadsTests(unittest.TestCase):
    def test_no_world(self):
        self.assertEqual(format_open_leads(None), "No active world.")

    def test_no_leads(self):
        world = _make_world()
        self.assertEqual(format_open_leads(world), "No open leads.")

    def test_formats_leads(self):
        world = _make_world()
        add_lead(world.player_state, "Find the cave", category="explore")
        text = format_open_leads(world)
        self.assertIn("Find the cave", text)
        self.assertIn("Explore", text)


class FormatRecentLeadChangesTests(unittest.TestCase):
    def test_no_world(self):
        self.assertEqual(format_recent_lead_changes(None), "No active world.")

    def test_no_changes(self):
        world = _make_world()
        result = format_recent_lead_changes(world)
        self.assertEqual(result, "No recently advanced leads.")

    def test_shows_changes(self):
        world = _make_world()
        world.player_state.day = 3
        add_lead(world.player_state, "Lead X")
        set_lead_status(world.player_state, "Lead X", "resolved")
        result = format_recent_lead_changes(world)
        self.assertIn("Lead X", result)


class FormatSuggestedNextActionsTests(unittest.TestCase):
    def test_no_world(self):
        self.assertEqual(format_suggested_next_actions(None), "No active world.")

    def test_no_leads_no_actions(self):
        world = _make_world()
        result = format_suggested_next_actions(world)
        self.assertEqual(result, "No suggested next actions.")

    def test_groups_by_category(self):
        world = _make_world()
        add_lead(world.player_state, "Talk to Bob", category="talk")
        add_lead(world.player_state, "Explore cave", category="explore")
        result = format_suggested_next_actions(world)
        self.assertIn("Talk:", result)
        self.assertIn("Explore:", result)


if __name__ == "__main__":
    unittest.main()
