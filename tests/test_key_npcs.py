"""Unit tests for app.key_npcs module."""

import random
import unittest
from pathlib import Path

from app.key_npcs import (
    FACTION_TAGS,
    KEY_NPC_THRESHOLD,
    RELATIONSHIP_STATES,
    determine_relationship,
    ensure_relationship_record,
    ensure_relationships_for_key_npc,
    infer_faction_tag,
    promote_key_npc_if_needed,
)
from app.models import (
    AdventureHook,
    Dungeon,
    Encounter,
    Location,
    NPC,
    NpcRelationship,
    PlayerState,
    Settlement,
    WildernessArea,
    World,
)
from app.table_loader import TableLoader


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "data" / "tables"


def _make_npc(
    name="Test NPC",
    profession="farmer",
    entity_id="npc_001",
    location="Market",
    location_id="loc_001",
    useful_information="",
    secret="",
    fear="",
    is_key_npc=False,
    prominence_score=0,
    faction_tag="unknown",
):
    return NPC(
        name=name,
        age=30,
        ancestry="Human",
        profession=profession,
        location=location,
        appearance="Average",
        personality="Calm",
        motivation="Survive",
        fear=fear,
        secret=secret,
        relationship_to_town="Resident",
        attitude_toward_player="Neutral",
        useful_information=useful_information,
        possible_service="None",
        danger_level="Low",
        entity_id=entity_id,
        location_id=location_id,
        is_key_npc=is_key_npc,
        prominence_score=prominence_score,
        faction_tag=faction_tag,
    )


def _make_world(npcs=None, locations=None):
    if npcs is None:
        npcs = [_make_npc()]
    if locations is None:
        locations = [
            Location(
                name="Market",
                type="market",
                condition="Good",
                owner_or_keeper="Bob",
                public_description="A busy market",
                hidden_detail="Secret passage",
                rumor_connected="Something odd",
                possible_encounter="Thief",
                useful_resource="Supplies",
                entity_id="loc_001",
            )
        ]
    return World(
        name="Test World",
        settlement=Settlement(
            name="Testville",
            type="Village",
            population=200,
            wealth_level="Modest",
            government_type="Council",
            main_industry="Farming",
            secondary_industry="Trade",
            condition="Fair",
            local_problem="Rats",
            local_secret="Hidden cave",
            nearby_danger="Goblins",
            weird_fantasy_detail="Floating stones",
            important_locations=locations,
            rumors=["A rumor", "Another rumor"],
        ),
        npcs=npcs,
        dungeon=Dungeon(
            name="Dark Caves",
            entrance_description="A dark opening",
            theme="Horror",
            danger_level="High",
            number_of_rooms=5,
            boss_or_final_threat="Dragon",
            treasure_or_secret="Gold",
            connection_to_town="Old mine",
        ),
        wilderness=WildernessArea(
            name="Wild Forest",
            terrain_type="Forest",
            weather="Rainy",
            dominant_feature="Ancient trees",
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
                    how_to_avoid="Stay quiet",
                    how_to_negotiate="Impossible",
                    how_to_fight_safely="Use fire",
                    preparation_that_helps="Torches",
                    reward_or_clue="Pelt",
                    morale=7,
                    reaction_roll_result="Hostile",
                    entity_id="enc_001",
                )
            ],
        ),
        adventure_hook=AdventureHook(
            trigger="Mysterious letter",
            major_goal="Find the artifact",
            obstacle="A guardian",
            location="The Temple",
            location_feature="Altar",
            phenomenon="Magic surge",
            villain_goal="World domination",
            artifact_or_relic="Crystal Orb",
            theme="Mystery",
            key_npc="Sage",
            first_clue="A torn map",
            time_pressure="Moon cycle",
            failure_consequence="Destruction",
            noncombat_paths="Diplomacy",
            entity_id="hook_001",
        ),
        local_threat="Goblins",
        player_state=PlayerState(),
        created_at="2024-01-01",
    )


class InferFactionTagTests(unittest.TestCase):
    def test_guard_is_settlement_authority(self):
        world = _make_world()
        npc = _make_npc(profession="Town Guard", location_id="loc_001")
        self.assertEqual(infer_faction_tag(world, npc), "settlement_authority")

    def test_merchant_is_local_traders(self):
        world = _make_world()
        npc = _make_npc(profession="Merchant", location_id="loc_001")
        self.assertEqual(infer_faction_tag(world, npc), "local_traders")

    def test_priest_is_shrine_or_cult(self):
        world = _make_world()
        npc = _make_npc(profession="Priest", location_id="loc_001")
        self.assertEqual(infer_faction_tag(world, npc), "shrine_or_cult")

    def test_dungeon_info_is_dungeon_interest(self):
        world = _make_world()
        npc = _make_npc(
            profession="Scholar",
            useful_information="knows about the dungeon depths",
        )
        self.assertEqual(infer_faction_tag(world, npc), "dungeon_interest")

    def test_wilderness_info_is_wilderness_threat(self):
        world = _make_world()
        npc = _make_npc(
            profession="Scout",
            useful_information="knows the forest trails well",
        )
        self.assertEqual(infer_faction_tag(world, npc), "wilderness_threat")

    def test_market_location_is_local_traders(self):
        locations = [
            Location(
                name="Market Square",
                type="market",
                condition="Good",
                owner_or_keeper="Alice",
                public_description="Busy",
                hidden_detail="None",
                rumor_connected="",
                possible_encounter="",
                useful_resource="",
                entity_id="loc_002",
            )
        ]
        world = _make_world(locations=locations)
        npc = _make_npc(
            profession="Artisan",
            location_id="loc_002",
            location="Market Square",
        )
        self.assertEqual(infer_faction_tag(world, npc), "local_traders")

    def test_independent_fallback(self):
        world = _make_world(locations=[])
        npc = _make_npc(
            profession="Hermit",
            location_id="",
            location="Nowhere",
            useful_information="nothing special",
            secret="nothing hidden",
        )
        self.assertEqual(infer_faction_tag(world, npc), "independent")


class DetermineRelationshipTests(unittest.TestCase):
    def setUp(self):
        self.rng = random.Random(42)
        self.world = _make_world()

    def test_shared_faction_gives_ally(self):
        npc_a = _make_npc(entity_id="a", faction_tag="local_traders")
        npc_b = _make_npc(entity_id="b", faction_tag="local_traders")
        state, score, reason = determine_relationship(self.world, npc_a, npc_b, self.rng)
        self.assertEqual(state, "ally")
        self.assertGreaterEqual(score, 2)
        self.assertIn("shared faction ties", reason)

    def test_competing_factions_gives_at_odds(self):
        npc_a = _make_npc(entity_id="a", faction_tag="settlement_authority")
        npc_b = _make_npc(entity_id="b", faction_tag="wilderness_threat")
        state, score, reason = determine_relationship(self.world, npc_a, npc_b, self.rng)
        self.assertEqual(state, "at_odds")
        self.assertLessEqual(score, -1)
        self.assertIn("competing local priorities", reason)

    def test_known_npcs_bonus(self):
        npc_a = _make_npc(entity_id="a", faction_tag="unknown")
        npc_b = _make_npc(entity_id="b", faction_tag="unknown")
        self.world.player_state.known_npc_ids = ["a", "b"]
        state, score, reason = determine_relationship(self.world, npc_a, npc_b, self.rng)
        self.assertIn("both known to the player", reason)

    def test_shared_location_bonus(self):
        npc_a = _make_npc(entity_id="a", location_id="loc_001", faction_tag="unknown")
        npc_b = _make_npc(entity_id="b", location_id="loc_001", faction_tag="unknown")
        state, score, reason = determine_relationship(self.world, npc_a, npc_b, self.rng)
        self.assertIn("shared location", reason)

    def test_fear_distrust(self):
        npc_a = _make_npc(entity_id="a", fear="wolves", faction_tag="unknown")
        npc_b = _make_npc(entity_id="b", useful_information="wolves", faction_tag="unknown")
        state, score, reason = determine_relationship(self.world, npc_a, npc_b, self.rng)
        self.assertIn("personal distrust", reason)


class EnsureRelationshipRecordTests(unittest.TestCase):
    def setUp(self):
        self.rng = random.Random(1)
        self.world = _make_world()

    def test_creates_new_relationship(self):
        npc_a = _make_npc(entity_id="a", faction_tag="local_traders", is_key_npc=True)
        npc_b = _make_npc(entity_id="b", faction_tag="local_traders", is_key_npc=True)
        self.world.npcs = [npc_a, npc_b]
        rel = ensure_relationship_record(self.world, npc_a, npc_b, self.rng)
        self.assertIsNotNone(rel)
        self.assertEqual(len(self.world.npc_relationships), 1)
        self.assertIn(rel.relationship_state, RELATIONSHIP_STATES)

    def test_returns_existing_relationship(self):
        npc_a = _make_npc(entity_id="a", faction_tag="local_traders", is_key_npc=True)
        npc_b = _make_npc(entity_id="b", faction_tag="local_traders", is_key_npc=True)
        self.world.npcs = [npc_a, npc_b]
        rel1 = ensure_relationship_record(self.world, npc_a, npc_b, self.rng)
        rel2 = ensure_relationship_record(self.world, npc_a, npc_b, self.rng)
        self.assertIs(rel1, rel2)
        self.assertEqual(len(self.world.npc_relationships), 1)

    def test_pair_ids_sorted(self):
        npc_a = _make_npc(entity_id="z_npc", faction_tag="independent", is_key_npc=True)
        npc_b = _make_npc(entity_id="a_npc", faction_tag="independent", is_key_npc=True)
        self.world.npcs = [npc_a, npc_b]
        rel = ensure_relationship_record(self.world, npc_a, npc_b, self.rng)
        self.assertEqual(rel.npc_a_id, "a_npc")
        self.assertEqual(rel.npc_b_id, "z_npc")


class EnsureRelationshipsForKeyNpcTests(unittest.TestCase):
    def setUp(self):
        self.rng = random.Random(1)

    def test_creates_relationships_with_other_key_npcs(self):
        npc_a = _make_npc(entity_id="a", is_key_npc=True, faction_tag="independent")
        npc_b = _make_npc(entity_id="b", is_key_npc=True, faction_tag="independent")
        npc_c = _make_npc(entity_id="c", is_key_npc=False, faction_tag="independent")
        world = _make_world(npcs=[npc_a, npc_b, npc_c])
        new_key = _make_npc(entity_id="d", is_key_npc=True, faction_tag="independent")
        world.npcs.append(new_key)
        ensure_relationships_for_key_npc(world, new_key, self.rng)
        self.assertEqual(len(world.npc_relationships), 2)


class PromoteKeyNpcTests(unittest.TestCase):
    def setUp(self):
        self.rng = random.Random(1)
        self.tables = TableLoader(TABLES)

    def test_no_promotion_below_threshold(self):
        world = _make_world()
        npc = world.npcs[0]
        npc.prominence_score = KEY_NPC_THRESHOLD - 1
        result = promote_key_npc_if_needed(world, npc, self.rng, self.tables)
        self.assertEqual(result, [])
        self.assertFalse(npc.is_key_npc)

    def test_no_promotion_if_already_key(self):
        world = _make_world()
        npc = world.npcs[0]
        npc.is_key_npc = True
        npc.prominence_score = KEY_NPC_THRESHOLD + 5
        result = promote_key_npc_if_needed(world, npc, self.rng, self.tables)
        self.assertEqual(result, [])

    def test_promotion_at_threshold(self):
        world = _make_world()
        npc = world.npcs[0]
        npc.prominence_score = KEY_NPC_THRESHOLD
        result = promote_key_npc_if_needed(world, npc, self.rng, self.tables)
        self.assertEqual(len(result), 1)
        self.assertTrue(npc.is_key_npc)
        self.assertTrue(npc.key_npc_since)
        self.assertIn(npc.faction_tag, FACTION_TAGS)


if __name__ == "__main__":
    unittest.main()
