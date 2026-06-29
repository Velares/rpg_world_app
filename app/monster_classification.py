from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OPTIONS_JSON = DEFAULT_PROJECT_ROOT / "data" / "tables" / "monster_classification_options.json"
DEFAULT_AFFINITIES_JSON = DEFAULT_PROJECT_ROOT / "data" / "configs" / "monster_classification_affinities.json"


class ClassificationOptions:
    """Controlled vocabulary for monster classification fields.

    Intended for:
    - editor dropdowns
    - classification suggestions
    - encounter placement
    - future import best-guess logic
    """

    def __init__(self, options: dict[str, list[str]]):
        self._options = options

    def get(self, field: str) -> list[str]:
        """Return the option list for a classification field."""
        return list(self._options.get(field, []))

    def __contains__(self, item: str) -> bool:
        return item in self._options

    def __getitem__(self, item: str) -> list[str]:
        return self.get(item)

    def keys(self) -> list[str]:
        return list(self._options.keys())


def load_classification_options(
    path: Path | None = None,
) -> ClassificationOptions:
    """Load controlled monster classification options from JSON.

    The file is expected to be a JSON object mapping field names to lists of
    option strings, for example:

        {
            "monster_types": ["undead", "aquatic", ...],
            "environments": ["swamp", "forest", ...],
            "terrains": ["marsh", "aerial", ...],
            "regions": ["grave-realm", "underground", ...],
            "affinity_values": ["always", "usually", ...]
        }
    """
    path = path or DEFAULT_OPTIONS_JSON
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.name}: root must be a JSON object")
    normalized: dict[str, list[str]] = {}
    for key, value in data.items():
        if not isinstance(value, list):
            raise ValueError(f"{path.name}:{key} must be a list")
        normalized[key] = [str(item).strip() for item in value if str(item).strip()]
    return ClassificationOptions(normalized)


def get_classification_option_list(
    field: str, path: Path | None = None
) -> list[str]:
    """Return a single classification option list by field name."""
    return load_classification_options(path).get(field)


def classification_fields() -> list[str]:
    """Return the classification field names available in the default table."""
    return load_classification_options().keys()


CLASSIFICATION_OPTION_FIELDS = {
    "environment": "environments",
    "terrain": "terrains",
    "region": "regions",
    "monster_type": "monster_types",
}


def dropdown_values_for_field(
    field: str,
    current_value: str | None,
    fallback: str = "unknown",
    path: Path | None = None,
) -> tuple[list[str], str]:
    """Return dropdown values and a default for a classification field.

    - Select known option if current value matches.
    - Default to ``fallback`` if missing/blank.
    - Preserve existing value if not in option list by appending it to the list.
    """
    options = load_classification_options(path)
    option_key = CLASSIFICATION_OPTION_FIELDS.get(field, field)
    values = list(options.get(option_key))
    if fallback not in values:
        values.append(fallback)
    normalized = (current_value or "").strip()
    if not normalized:
        selected = fallback
    elif normalized in values:
        selected = normalized
    else:
        values.append(normalized)
        selected = normalized
    return values, selected


class ClassificationAffinities:
    """Affinity rules assigning monster types to environments, terrains, and regions."""

    def __init__(self, data: dict[str, Any]):
        self.schema_version = data.get("schema_version", 1)
        self.affinity_values = list(data.get("affinity_values", []))
        self.monster_type_affinities = dict(
            data.get("monster_type_affinities", {})
        )

    def get_affinity(
        self, monster_type: str, field: str, value: str
    ) -> str | None:
        """Return the affinity for a monster type/field/value, or None."""
        return self.monster_type_affinities.get(monster_type, {}).get(field, {}).get(value)

    def get_all_for_type(self, monster_type: str) -> dict[str, dict[str, str]]:
        """Return all affinities for a monster type, grouped by field."""
        return dict(self.monster_type_affinities.get(monster_type, {}))


def load_classification_affinities(
    path: Path | None = None,
) -> ClassificationAffinities:
    """Load monster classification affinity rules from JSON.

    The file is expected to follow the schema:

        {
            "schema_version": 1,
            "affinity_values": ["always", "usually", ...],
            "monster_type_affinities": {
                "undead": {
                    "environment": {"graveyard": "usually", ...},
                    "terrain": {"crypt": "usually", ...},
                    "region": {"grave-realm": "usually", ...}
                }
            }
        }
    """
    path = path or DEFAULT_AFFINITIES_JSON
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.name}: root must be a JSON object")
    return ClassificationAffinities(data)


def validate_affinities_against_options(
    affinities: ClassificationAffinities | None = None,
    options: ClassificationOptions | None = None,
) -> list[str]:
    """Return warnings for any affinity values that reference unknown options."""
    affinities = affinities or load_classification_affinities()
    options = options or load_classification_options()
    warnings: list[str] = []
    valid_affinity_values = set(options.get("affinity_values"))
    valid_fields = {
        "environment": set(options.get("environments")),
        "terrain": set(options.get("terrains")),
        "region": set(options.get("regions")),
    }
    valid_monster_types = set(options.get("monster_types"))
    for monster_type in affinities.monster_type_affinities:
        if monster_type not in valid_monster_types:
            warnings.append(
                f"affinity references unknown monster_type: {monster_type}"
            )
        for field, values in affinities.monster_type_affinities[monster_type].items():
            if field not in valid_fields:
                warnings.append(
                    f"affinity uses unknown field: {monster_type}.{field}"
                )
                continue
            for value, affinity in values.items():
                if value not in valid_fields[field]:
                    warnings.append(
                        f"affinity references unknown {field}: {monster_type}.{field}.{value}"
                    )
                if affinity not in valid_affinity_values:
                    warnings.append(
                        f"affinity uses unknown affinity value: {monster_type}.{field}.{value}={affinity}"
                    )
    return warnings
