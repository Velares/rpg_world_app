from __future__ import annotations

"""Small, rules-neutral schemas for data consumed by procedural generators."""

BONUS_NAMES = ("combat", "exploration", "social", "lore", "survival", "stealth")
ITEM_CATEGORIES = (
    "Weapon",
    "Armor",
    "Container",
    "Tool",
    "Supply",
    "Food",
    "Water",
    "Light",
    "Treasure",
    "Quest",
    "Miscellaneous",
)

# These are the categories directly consumed by the current generators. Extra
# categories remain valid and editable, but missing required data is reported.
REQUIRED_CATEGORIES: dict[str, tuple[str, ...]] = {
    "adventure_tables": (
        "triggers",
        "major_goals",
        "obstacles",
        "locales",
        "locale_features",
        "phenomena",
        "villain_goals",
        "artifacts_or_relics",
        "themes",
        "key_npcs",
        "first_clues",
        "failure_consequences",
        "time_pressures",
        "noncombat_paths",
    ),
    "class_tables": ("backgrounds", "classes"),
    "downtime_tables": ("tasks",),
    "item_tables": ("item_definitions", "common_loadout", "class_loadouts"),
    "key_npc_tables": (
        "key_npc_reasons",
        "key_npc_notes",
        "ally_phase_events",
        "at_odds_phase_events",
        "neutral_phase_events",
    ),
    "interaction_tables": (
        "npc_dialogue_rumor",
        "npc_dialogue_warning",
        "npc_dialogue_request",
        "npc_dialogue_secret",
        "npc_dialogue_local_trouble",
        "npc_dialogue_faction_hint",
        "npc_dialogue_dungeon_clue",
        "npc_dialogue_wilderness_clue",
        "npc_dialogue_trade_lead",
        "npc_dialogue_personal_oddity",
        "encounter_avoid_success",
        "encounter_approach_success",
        "encounter_approach_trade",
        "encounter_approach_help",
        "encounter_investigate_success",
        "encounter_investigate_follow",
        "encounter_failed_forward",
        "encounter_costly_success",
        "encounter_strange_omen",
        "search_discovery",
        "inspect_discovery",
        "town_explore_discovery",
        "wilderness_explore_discovery",
        "retreat_consequences",
        "check_critical_failure_additions",
        "check_failure_additions",
        "check_partial_success_additions",
        "check_success_additions",
        "check_critical_success_additions",
    ),
    "player_background_tables": (
        "origins",
        "formative_events",
        "personality_traits",
        "ideals",
        "bonds",
        "flaws",
    ),
    "dungeon_tables": (
        "dungeon_names",
        "cave_descriptions",
        "dungeon_themes",
        "room_names",
        "room_descriptions",
        "exits",
        "hazards",
        "traps",
        "clues",
        "treasures",
        "dungeon_monsters",
        "weird_room_details",
        "retreat_options",
    ),
    "monster_tables": (
        "monster_names",
        "monster_types",
        "monster_intents",
        "monster_signs",
        "monster_weaknesses",
        "monster_morale",
        "monster_reactions",
        "noncombat_options",
        "avoidance_options",
        "safe_combat_options",
    ),
    "npc_tables": (
        "male_names",
        "female_names",
        "neutral_names",
        "surnames",
        "ancestries",
        "professions",
        "appearances",
        "personalities",
        "motivations",
        "fears",
        "secrets",
        "relationships",
        "attitudes",
        "useful_information",
        "possible_services",
    ),
    "npc_depth_tables": (
        "deeper_backstories",
        "personal_motives",
        "hidden_pressures",
        "relationship_to_player",
        "ongoing_threads",
        "prominence_notes",
    ),
    "settlement_tables": (
        "settlement_names_prefix",
        "settlement_names_suffix",
        "settlement_types",
        "government_types",
        "wealth_levels",
        "industries",
        "settlement_conditions",
        "local_problems",
        "local_secrets",
        "nearby_dangers",
        "building_types",
        "tavern_names",
        "inn_names",
        "shop_names",
        "local_laws",
        "local_events",
        "rumors",
        "location_descriptions",
        "useful_resources",
    ),
    "treasure_tables": (
        "coins",
        "mundane_treasure",
        "useful_items",
        "weird_relics",
        "minor_magic_items",
        "cursed_items",
        "clue_items",
    ),
    "weird_tables": (
        "ominous_signs",
        "disturbing_sights",
        "weird_mutations",
        "forbidden_magic_effects",
        "dark_prophecies",
        "strange_weather",
        "eerie_sounds",
        "supernatural_marks",
    ),
    "wilderness_tables": (
        "wilderness_names",
        "terrain_types",
        "weather",
        "dominant_features",
        "resources",
        "travel_hazards",
        "animal_encounters",
        "monster_encounters",
        "npc_encounters",
        "landmarks",
        "tracks_and_signs",
        "camp_events",
    ),
}

DEFAULT_CHARACTER_CLASS = {
    "class_name": "Explorer",
    "role_description": "A cautious wanderer prepared to investigate uncertain places.",
    "starting_supplies": 10,
    "starting_food": 7,
    "starting_water": 7,
    "starting_torches": 6,
    "starting_coin": 12,
    "bonuses": {
        "combat": 0,
        "exploration": 1,
        "social": 0,
        "lore": 0,
        "survival": 1,
        "stealth": 0,
    },
    "special_ability_placeholder": "Expedition planning placeholder.",
    "class_role": "specialist",
    "class_type": "scout",
    "class_subtype": "delver",
}

# Structural tables need structural fallbacks. Most prose categories can safely
# use the generic omen without encoding game rules in Python.
FALLBACKS: dict[tuple[str, str], list[object]] = {
    ("class_tables", "backgrounds"): ["Wanderer"],
    ("class_tables", "classes"): [DEFAULT_CHARACTER_CLASS],
    ("downtime_tables", "tasks"): [
        {
            "task_key": "recover_from_injury",
            "name": "Recover from Injury",
            "category": "recovery",
            "description": "Set aside time to heal, reorganize, and recover your nerve.",
            "default_duration_days": 3,
            "allowed_contexts": ["town", "any"],
            "progress_text": "{task_name}: {progress_days}/{total_days} recovery days completed.",
            "completion_text": "{task_name} is complete. You can re-enter the field with steadier footing.",
            "complication_text": "{task_name}: a setback costs time and forces slower recovery.",
            "tags": ["recovery", "fallback"],
            "progress_outcomes": [],
            "completion_outcomes": [],
            "complication_outcomes": [],
        }
    ],
    ("item_tables", "item_definitions"): [
        {
            "item_key": "basic_gear",
            "name": "Basic Gear",
            "category": "Supply",
            "description": "A small bundle of ordinary travel necessities.",
            "tags": ["fallback"],
            "equipped": False,
            "carried": True,
            "consumable": False,
            "quest_related": False,
            "tradeable": True,
            "bulk": 1.0,
            "valid_slots": [],
            "handedness": "",
            "speed_factor": 0,
            "range_profile": "",
            "mode": "",
            "placeholder_damage": "",
            "placeholder_special_rules": "",
            "placeholder_value": "",
            "placeholder_condition": "",
            "capacity_bulk": 0.0,
        }
    ],
    ("item_tables", "common_loadout"): [
        {"item_key": "basic_gear", "quantity": 1}
    ],
    ("key_npc_tables", "key_npc_reasons"): [
        "{npc} now sits close enough to the region's trouble that other powers must account for them."
    ],
    ("key_npc_tables", "key_npc_notes"): [
        "{npc} carries enough influence to alter rumors, opportunities, and local tensions."
    ],
    ("key_npc_tables", "ally_phase_events"): [
        "Word spreads that {npc_a} and {npc_b} are quietly coordinating matters in {settlement_name}."
    ],
    ("key_npc_tables", "at_odds_phase_events"): [
        "Rumors suggest {npc_a} and {npc_b} are working against one another in {settlement_name}."
    ],
    ("key_npc_tables", "neutral_phase_events"): [
        "A cautious meeting between {npc_a} and {npc_b} changes little openly, but people in {settlement_name} take note."
    ],
    ("item_tables", "class_loadouts"): [
        {"class_name": "Explorer", "items": []}
    ],
    ("player_background_tables", "origins"): [
        "Your early life left few reliable records."
    ],
    ("player_background_tables", "formative_events"): [
        "You survived a journey that taught you to prepare before acting."
    ],
    ("player_background_tables", "personality_traits"): [
        "Cautious, observant, and slow to trust easy answers."
    ],
    ("player_background_tables", "ideals"): [
        "Survival: living people can repair what dead heroes cannot."
    ],
    ("player_background_tables", "bonds"): [
        "You owe a debt to someone who once offered shelter without questions."
    ],
    ("player_background_tables", "flaws"): [
        "You sometimes mistake careful preparation for certainty."
    ],
    ("npc_tables", "male_names"): ["Nameless"],
    ("npc_tables", "female_names"): ["Nameless"],
    ("npc_tables", "neutral_names"): ["Nameless"],
    ("npc_tables", "surnames"): ["Wanderer"],
    ("npc_depth_tables", "deeper_backstories"): [
        "They carry an old debt from before the current troubles sharpened."
    ],
    ("npc_depth_tables", "personal_motives"): [
        "They want to protect their place in the settlement without drawing open blame."
    ],
    ("npc_depth_tables", "hidden_pressures"): [
        "A private obligation keeps twisting their public choices."
    ],
    ("npc_depth_tables", "relationship_to_player"): [
        "They treat you as a useful but unsettling ally."
    ],
    ("npc_depth_tables", "ongoing_threads"): [
        "Their future choices keep crossing your unfinished business."
    ],
    ("npc_depth_tables", "prominence_notes"): [
        "They now matter often enough to reshape later leads and choices."
    ],
    ("settlement_tables", "settlement_names_prefix"): ["Gloam"],
    ("settlement_tables", "settlement_names_suffix"): ["rest"],
    ("settlement_tables", "settlement_types"): ["village"],
    ("settlement_tables", "building_types"): ["shrine"],
}
