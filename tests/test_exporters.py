"""Unit tests for app.exporters module."""

import unittest
from pathlib import Path

from app.exporters import (
    export_character_text,
    export_event_log_text,
    export_world_summary,
    inventory_item_text,
)
from app.models import (
    AdventureHook,
    Dungeon,
    DungeonRoom,
    Encounter,
    InventoryItem,
    Location,
    NPC,
    NpcRelationship,
    PlayerCharacter,
    PlayerState,
    Settlement,
    WildernessArea,
    World,
)


def _make_character():
    return PlayerCharacter(
        name="Hero",
        character_class="Fighter",
        background="Soldier",
        starting_supplies=10,
        bonuses={"combat": 2, "exploration": 1, "social": 0, "lore": 0, "survival": 1, "stealth": 0},
        role_description="Frontline warrior",
        special_ability_placeholder="Shield bash (placeholder)",
        origin_detail="Border town",
        formative_event="Survived a siege",
        personality_trait="Cautious",
        ideal="Justice",
        bond="Mentor",
        flaw="Stubborn",
    )


def _make_world(player=None):
    if player is None:
        char = _make_character()
        player = PlayerState(character=char)
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
                    useful_resource="",
                    entity_id="loc_001",
                )
            ],
            rumors=["First rumor", "Second rumor"],
            problem_connection="Linked to dungeon",
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
                prominent=True,
                prominence_notes="Recurring merchant",
                relationship_to_player="Friendly",
                ongoing_thread="Trade deal pending",
                is_key_npc=True,
                faction_tag="local_traders",
                key_npc_reason="Runs the market",
                key_npc_notes="Influential trader",
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
            rooms=[
                DungeonRoom(
                    room_id=1,
                    name="Hall",
                    description="Dark hall",
                    exits=[2],
                    what_player_notices_first="Dark",
                    contents="Empty",
                    danger="None",
                    monster_or_npc="None",
                    trap_or_hazard="None",
                    clue="Scratches",
                    treasure="None",
                    noncombat_resolution_options="None",
                    preparation_that_helps="Torch",
                    retreat_option="Back",
                    entity_id="room_001",
                )
            ],
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
            major_goal="Find artifact",
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
        npc_relationships=[
            NpcRelationship(
                npc_a_id="npc_001",
                npc_b_id="npc_002",
                relationship_state="ally",
                affinity_score=3,
                reason_text="shared faction ties",
                recent_event_notes=["Day 1 - Cooperated on trade"],
            )
        ],
        faction_status_notes={"local_traders": "allied"},
    )


class InventoryItemTextTests(unittest.TestCase):
    def test_basic_item(self):
        item = InventoryItem(
            item_key="sword",
            name="Iron Sword",
            category="Weapon",
            quantity=1,
            bulk=1.0,
        )
        text = inventory_item_text(item)
        self.assertIn("Iron Sword", text)
        self.assertIn("x1", text)
        self.assertIn("Weapon", text)

    def test_equipped_flag(self):
        item = InventoryItem(
            item_key="sword",
            name="Sword",
            category="Weapon",
            quantity=1,
            equipped=True,
            bulk=1.0,
        )
        text = inventory_item_text(item)
        self.assertIn("equipped", text)

    def test_consumable_flag(self):
        item = InventoryItem(
            item_key="potion",
            name="Potion",
            category="Consumable",
            quantity=3,
            consumable=True,
            bulk=0.5,
        )
        text = inventory_item_text(item)
        self.assertIn("consumable", text)

    def test_quest_flag(self):
        item = InventoryItem(
            item_key="gem",
            name="Magic Gem",
            category="Quest",
            quantity=1,
            quest_related=True,
            bulk=0.1,
        )
        text = inventory_item_text(item)
        self.assertIn("quest", text)

    def test_stored_flag(self):
        item = InventoryItem(
            item_key="pack",
            name="Extra Pack",
            category="Container",
            quantity=1,
            carried=False,
            bulk=2.0,
        )
        text = inventory_item_text(item)
        self.assertIn("stored", text)

    def test_detailed_includes_description(self):
        item = InventoryItem(
            item_key="ring",
            name="Ring",
            category="Accessory",
            quantity=1,
            description="A shiny ring",
            bulk=0.0,
        )
        text = inventory_item_text(item, detailed=True)
        self.assertIn("A shiny ring", text)

    def test_not_detailed_excludes_description(self):
        item = InventoryItem(
            item_key="ring",
            name="Ring",
            category="Accessory",
            quantity=1,
            description="A shiny ring",
            bulk=0.0,
        )
        text = inventory_item_text(item, detailed=False)
        self.assertNotIn("A shiny ring", text)

    def test_bulk_displayed(self):
        item = InventoryItem(
            item_key="heavy",
            name="Heavy Thing",
            category="Misc",
            quantity=2,
            bulk=1.5,
        )
        text = inventory_item_text(item)
        self.assertIn("bulk 3", text)


class ExportWorldSummaryTests(unittest.TestCase):
    def test_none_world(self):
        text = export_world_summary(None)
        self.assertIn("NO ACTIVE WORLD", text)
        self.assertIn("Generate or load", text)

    def test_has_settlement_name(self):
        world = _make_world()
        text = export_world_summary(world)
        self.assertIn("Testville", text)

    def test_has_dungeon_name(self):
        world = _make_world()
        text = export_world_summary(world)
        self.assertIn("Caves", text)

    def test_has_wilderness_name(self):
        world = _make_world()
        text = export_world_summary(world)
        self.assertIn("Forest", text)

    def test_has_adventure_goal(self):
        world = _make_world()
        text = export_world_summary(world)
        self.assertIn("Find artifact", text)

    def test_has_calendar(self):
        world = _make_world()
        text = export_world_summary(world)
        self.assertIn("Year", text)

    def test_has_prominent_npc_section(self):
        world = _make_world()
        text = export_world_summary(world)
        self.assertIn("PROMINENT NPCS", text)
        self.assertIn("Bob", text)

    def test_has_key_npc_section(self):
        world = _make_world()
        text = export_world_summary(world)
        self.assertIn("KEY NPCS AND RELATIONSHIPS", text)

    def test_has_relationship_section(self):
        world = _make_world()
        text = export_world_summary(world)
        self.assertIn("RELATIONSHIP RECORDS", text)

    def test_has_faction_section(self):
        world = _make_world()
        text = export_world_summary(world)
        self.assertIn("FACTION STATUS NOTES", text)
        self.assertIn("local_traders", text)

    def test_seed_text_when_none(self):
        world = _make_world()
        world.generation_seed = None
        text = export_world_summary(world)
        self.assertIn("Random / not recorded", text)

    def test_seed_text_when_set(self):
        world = _make_world()
        world.generation_seed = "myseed"
        text = export_world_summary(world)
        self.assertIn("myseed", text)


class ExportCharacterTextTests(unittest.TestCase):
    def test_none_world(self):
        text = export_character_text(None)
        self.assertIn("NO ACTIVE WORLD", text)

    def test_no_character(self):
        world = _make_world(player=PlayerState())
        text = export_character_text(world)
        self.assertIn("NO PLAYER CHARACTER", text)

    def test_has_character_name(self):
        world = _make_world()
        text = export_character_text(world)
        self.assertIn("HERO", text)

    def test_has_class_and_background(self):
        world = _make_world()
        text = export_character_text(world)
        self.assertIn("Fighter", text)
        self.assertIn("Soldier", text)

    def test_has_resources(self):
        world = _make_world()
        text = export_character_text(world)
        self.assertIn("Supplies:", text)
        self.assertIn("Coin:", text)
        self.assertIn("Wounds:", text)

    def test_has_bonuses(self):
        world = _make_world()
        text = export_character_text(world)
        self.assertIn("Combat:", text)

    def test_has_background_details(self):
        world = _make_world()
        text = export_character_text(world)
        self.assertIn("Border town", text)
        self.assertIn("Survived a siege", text)

    def test_has_inventory_section(self):
        world = _make_world()
        text = export_character_text(world)
        self.assertIn("CARRIED INVENTORY", text)

    def test_has_encumbrance(self):
        world = _make_world()
        text = export_character_text(world)
        self.assertIn("Encumbrance:", text)


class ExportEventLogTextTests(unittest.TestCase):
    def test_none_world(self):
        text = export_event_log_text(None)
        self.assertIn("NO ACTIVE WORLD", text)

    def test_no_events(self):
        world = _make_world()
        text = export_event_log_text(world)
        self.assertIn("No events recorded yet.", text)

    def test_with_events(self):
        world = _make_world()
        world.player_state.event_log = ["Day 1 - Arrived at Testville"]
        text = export_event_log_text(world)
        self.assertIn("Arrived at Testville", text)

    def test_pending_encounter_warning(self):
        world = _make_world()
        world.player_state.pending_encounter_id = "enc_001"
        text = export_event_log_text(world)
        self.assertIn("DANGER IS PENDING", text)

    def test_no_pending_encounter(self):
        world = _make_world()
        world.player_state.pending_encounter_id = ""
        text = export_event_log_text(world)
        self.assertNotIn("DANGER IS PENDING", text)

    def test_has_timeline_sections(self):
        world = _make_world()
        text = export_event_log_text(world)
        self.assertIn("TIMELINE SUMMARY", text)
        self.assertIn("VERBOSE TIMELINE", text)

    def test_has_lead_sections(self):
        world = _make_world()
        text = export_event_log_text(world)
        self.assertIn("OPEN LEADS", text)
        self.assertIn("RECENT LEAD CHANGES", text)


if __name__ == "__main__":
    unittest.main()
