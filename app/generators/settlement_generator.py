from __future__ import annotations

from app.generators.common import BaseGenerator
from app.ids import new_id
from app.models import Location, Settlement


class SettlementGenerator(BaseGenerator):
    def generate_location(self, owner: str = "an unnamed keeper") -> Location:
        kind = self.pick("settlement_tables", "building_types")
        special_names = {
            "tavern": "tavern_names",
            "inn": "inn_names",
            "shop": "shop_names",
        }
        category = special_names.get(str(kind).lower())
        name = self.pick("settlement_tables", category) if category else f"The {kind.title()}"
        return Location(
            name=name,
            type=kind,
            condition=self.pick("settlement_tables", "settlement_conditions"),
            owner_or_keeper=owner,
            public_description=self.pick("settlement_tables", "location_descriptions"),
            hidden_detail=self.pick("settlement_tables", "local_secrets"),
            rumor_connected=self.pick("settlement_tables", "rumors"),
            possible_encounter=self.pick("settlement_tables", "local_events"),
            useful_resource=self.pick("settlement_tables", "useful_resources"),
            entity_id=new_id("loc"),
        )

    def generate(self) -> Settlement:
        settlement_type = self.pick("settlement_tables", "settlement_types")
        population_ranges = {
            "thorpe": (20, 80),
            "hamlet": (60, 180),
            "village": (150, 700),
            "town": (600, 2400),
        }
        low, high = population_ranges.get(settlement_type, (100, 600))
        locations = [self.generate_location() for _ in range(8)]
        # Keep generated names unique so NPC and rumor references are unambiguous.
        seen_names: dict[str, int] = {}
        for location in locations:
            seen_names[location.name] = seen_names.get(location.name, 0) + 1
            if seen_names[location.name] > 1:
                location.name = f"{location.name} ({seen_names[location.name]})"
        return Settlement(
            name=self.settlement_name(),
            type=settlement_type,
            population=self.rng.randint(low, high),
            wealth_level=self.pick("settlement_tables", "wealth_levels"),
            government_type=self.pick("settlement_tables", "government_types"),
            main_industry=self.pick("settlement_tables", "industries"),
            secondary_industry=self.pick("settlement_tables", "industries"),
            condition=self.pick("settlement_tables", "settlement_conditions"),
            local_problem=self.pick("settlement_tables", "local_problems"),
            local_secret=self.pick("settlement_tables", "local_secrets"),
            nearby_danger=self.pick("settlement_tables", "nearby_dangers"),
            weird_fantasy_detail=self.pick("weird_tables", "supernatural_marks"),
            important_locations=locations,
            rumors=[self.pick("settlement_tables", "rumors") for _ in range(6)],
        )
