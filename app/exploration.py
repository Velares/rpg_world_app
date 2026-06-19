from __future__ import annotations

import random

from app.models import DungeonRoom, Encounter, NPC, World


class ExplorationEngine:
    """Small stateful action engine for Version 0.3's abstract exploration loop."""

    def __init__(self, world: World, rng: random.Random):
        self.world = world
        self.rng = rng

    @property
    def player(self):
        return self.world.player_state

    def log(self, message: str) -> str:
        self.player.action_log.append(message)
        return message

    def _spend_turn(self, supplies: int = 1, food: int = 0, water: int = 1) -> None:
        player = self.player
        player.turns_elapsed += 1
        player.supplies = max(0, player.supplies - supplies)
        player.food = max(0, player.food - food)
        player.water = max(0, player.water - water)
        if player.current_location == "dungeon":
            self._consume_light()

    def _consume_light(self) -> None:
        player = self.player
        if player.light_turns_remaining <= 0 and player.torches > 0:
            player.torches -= 1
            player.light_turns_remaining = 6
            self.log("A torch is lit. Its smoke coils toward passages with no wind.")
        if player.light_turns_remaining > 0:
            player.light_turns_remaining -= 1

    def _hardship(self, reason: str, severe: bool = False) -> str:
        player = self.player
        roll = self.rng.random()
        if severe or roll < 0.35:
            if player.wounds < 6:
                player.wounds += 1
                consequence = "You suffer a wound."
            else:
                loss = min(player.supplies, 2)
                player.supplies -= loss
                consequence = (
                    "Already critically wounded, you abandon gear and lose "
                    f"{loss} supplies to escape."
                )
        elif roll < 0.7:
            loss = min(player.supplies, self.rng.randint(1, 2))
            player.supplies -= loss
            consequence = f"You lose {loss} supplies."
        else:
            player.current_location = "wilderness"
            player.current_room_id = None
            consequence = "You are driven into a worse position in the wilderness."
        return self.log(f"{reason} {consequence}")

    def travel(self, destination: str) -> str:
        if destination not in {"town", "wilderness", "dungeon_entrance"}:
            raise ValueError("Unknown travel destination.")
        player = self.player
        player.pending_encounter_id = ""
        player.current_room_id = None
        player.current_location = destination
        self._spend_turn(supplies=1, water=1)
        names = {
            "town": self.world.settlement.name,
            "wilderness": self.world.wilderness.name,
            "dungeon_entrance": self.world.dungeon.name,
        }
        return self.log(f"You travel to {names[destination]}. The journey costs supplies and water.")

    def explore(self) -> str:
        player = self.player
        if player.current_location == "town":
            self._spend_turn(supplies=0, water=0)
            location = self.rng.choice(self.world.settlement.important_locations)
            return self.log(
                f"You explore {location.name}. {location.public_description} "
                f"Its keeper is {location.owner_or_keeper}."
            )
        if player.current_location == "wilderness":
            return self._explore_wilderness()
        if player.current_location == "dungeon_entrance":
            player.current_location = "dungeon"
            player.current_room_id = 1
            player.discovered_room_ids = sorted(set(player.discovered_room_ids + [1]))
            self._spend_turn()
            return self.log(
                f"You enter {self.world.dungeon.name}. "
                f"{self.world.dungeon.rooms[0].what_player_notices_first}"
            )
        if player.current_location == "dungeon":
            self._spend_turn()
            return self.inspect_room()
        raise RuntimeError("The current location cannot be explored.")

    def _explore_wilderness(self) -> str:
        self._spend_turn()
        if self.player.pending_encounter_id:
            encounter = self.pending_encounter()
            return self.log(
                f"The signs persist: {encounter.signs_or_foreshadowing} "
                "Choose avoid, approach, investigate, or retreat."
            )
        if self.rng.random() < 0.55:
            encounter = self.rng.choice(self.world.wilderness.encounter_table)
            self.player.pending_encounter_id = encounter.entity_id
            return self.log(
                f"You find warning signs before the danger: {encounter.what_player_notices_first} "
                f"{encounter.signs_or_foreshadowing} Choose avoid, approach, investigate, or retreat."
            )
        return self.log(
            f"You scout {self.world.wilderness.name} without immediate contact. "
            f"You mark {self.world.wilderness.dominant_feature} as a useful landmark."
        )

    def pending_encounter(self) -> Encounter:
        encounter = next(
            (
                item
                for item in self.world.wilderness.encounter_table
                if item.entity_id == self.player.pending_encounter_id
            ),
            None,
        )
        if encounter is None:
            raise RuntimeError("There is no pending wilderness encounter.")
        return encounter

    def resolve_encounter(self, choice: str) -> str:
        encounter = self.pending_encounter()
        player = self.player
        choice = choice.lower()
        if choice == "avoid":
            self._spend_turn(supplies=1, water=0)
            result = f"You avoid {encounter.creature_or_npc}: {encounter.how_to_avoid}"
        elif choice == "retreat":
            player.current_location = "town"
            self._spend_turn(supplies=1, water=1)
            result = f"You retreat to {self.world.settlement.name} before the danger closes."
        elif choice == "investigate":
            self._spend_turn()
            if self.rng.random() < 0.7:
                if encounter.reward_or_clue not in player.inventory:
                    player.inventory.append(encounter.reward_or_clue)
                result = (
                    f"Careful scouting reveals: {encounter.reward_or_clue}. "
                    f"Preparation that helps: {encounter.preparation_that_helps}"
                )
            else:
                result = self._hardship("Your investigation exposes you.", severe=False)
        elif choice == "approach":
            self._spend_turn()
            if self.rng.random() < 0.55:
                result = (
                    f"You approach without drawing steel. {encounter.how_to_negotiate} "
                    f"Reaction: {encounter.reaction_roll_result}"
                )
            else:
                result = self._hardship(
                    f"The approach to {encounter.creature_or_npc} goes badly.", severe=True
                )
        else:
            raise ValueError("Choose avoid, approach, investigate, or retreat.")
        player.pending_encounter_id = ""
        if result not in player.action_log:
            self.log(result)
        return result

    def current_room(self) -> DungeonRoom:
        if self.player.current_location != "dungeon" or self.player.current_room_id is None:
            raise RuntimeError("You are not inside the dungeon.")
        return self.world.dungeon.rooms[self.player.current_room_id - 1]

    def inspect_room(self) -> str:
        room = self.current_room()
        return self.log(
            f"Room {room.room_id}, {room.name}: {room.description} "
            f"First impression: {room.what_player_notices_first} "
            f"Visible exits: {', '.join(map(str, room.exits))}."
        )

    def move_room(self, room_id: int) -> str:
        room = self.current_room()
        if room_id not in room.exits:
            raise ValueError(f"Room {room_id} is not reachable from this room.")
        self._spend_turn()
        self.player.current_room_id = room_id
        self.player.discovered_room_ids = sorted(
            set(self.player.discovered_room_ids + [room_id])
        )
        destination = self.current_room()
        if self.player.light_turns_remaining == 0 and self.player.torches == 0:
            return self._hardship(
                "Darkness takes the passage before you reach secure footing.", severe=True
            )
        return self.log(
            f"You move to room {room_id}, {destination.name}. "
            f"{destination.what_player_notices_first}"
        )

    def search(self) -> str:
        player = self.player
        self._spend_turn()
        if player.current_location == "dungeon":
            room = self.current_room()
            if self.rng.random() < 0.7:
                if room.clue not in player.inventory:
                    player.inventory.append(room.clue)
                return self.log(
                    f"You search cautiously and find {room.clue}. Danger detected: "
                    f"{room.trap_or_hazard}. Preparation: {room.preparation_that_helps}"
                )
            return self._hardship(f"Searching triggers {room.trap_or_hazard}.")
        if player.current_location == "wilderness":
            return self.log(
                f"You find {self.world.wilderness.resources}, but note the hazard: "
                f"{self.world.wilderness.travel_hazards}."
            )
        if player.current_location == "town":
            location = self.rng.choice(self.world.settlement.important_locations)
            return self.log(f"A search around {location.name} reveals: {location.hidden_detail}")
        return self.log(f"You search the entrance and find signs: {self.world.dungeon.entrance_description}")

    def talk_to_npc(self) -> str:
        if self.player.current_location != "town":
            raise RuntimeError("Return to town to talk to its NPCs.")
        npc: NPC = self.rng.choice(self.world.npcs)
        self._spend_turn(supplies=0, water=0)
        return self.log(
            f"You speak with {npc.name} at {npc.location}. Attitude: "
            f"{npc.attitude_toward_player}. They reveal: {npc.useful_information}. "
            f"Possible service: {npc.possible_service}."
        )

    def rest(self) -> str:
        player = self.player
        player.turns_elapsed += 1
        if player.food <= 0 or player.water <= 0:
            return self._hardship("Rest without food or water brings no recovery.", severe=True)
        player.food -= 1
        player.water -= 1
        risk = 0.1 if player.current_location == "town" else 0.35
        if player.current_location == "dungeon":
            risk = 0.55
            self._consume_light()
        player.rest_risk = f"{int(risk * 100)}% interruption risk"
        if self.rng.random() < risk:
            return self._hardship("The rest is interrupted by signs of nearby danger.")
        recovered = player.wounds > 0
        if recovered:
            player.wounds -= 1
        recovery = "recover one wound" if recovered else "steady your nerves"
        return self.log(f"You rest, consume food and water, and {recovery}.")

    def retreat(self) -> str:
        player = self.player
        if player.current_location == "dungeon":
            player.current_location = "dungeon_entrance"
            player.current_room_id = None
            player.pending_encounter_id = ""
            self._spend_turn(supplies=1, water=0)
            return self.log(
                f"You retreat to the entrance. {self.world.dungeon.rooms[0].retreat_option}"
            )
        if player.current_location in {"wilderness", "dungeon_entrance"}:
            return self.travel("town")
        return self.log("You are already within the relative safety of town.")
