from __future__ import annotations

import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if __name__ == "__main__":
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.monster_classification import (
    ClassificationAffinities,
    ClassificationOptions,
    load_classification_affinities,
    load_classification_options,
)
from app.monster_editor import (
    DEFAULT_CORRECTIONS_PATH,
    DEFAULT_MANDBMASTER_PREVIEW_PATH,
    DEFAULT_MEGADUNGEON_PREVIEW_PATH,
    load_all_normalized_previews,
    load_corrections,
)
from tools.importers.monster_manual_schema import PROJECT_ROOT


DEFAULT_SUGGESTIONS_JSON = (
    PROJECT_ROOT / "data" / "import_reports" / "monster_classification_suggestions.json"
)
DEFAULT_SUGGESTIONS_REPORT = (
    PROJECT_ROOT / "data" / "import_reports" / "monster_classification_suggestions_report.txt"
)


CLASSIFICATION_FIELDS = ("environment", "terrain", "region", "monster_type")


def _keyword_map() -> dict[str, dict[str, list[str]]]:
    """Return crude keyword hints for classification fields.

    These are deliberately conservative: they only suggest a value when the
    monster name or description contains a strong signal.  They are not a
    replacement for human review.
    """
    return {
        "environment": {
            "swamp": ["swamp", "marsh", "bog", "fen"],
            "forest": ["forest", "wood", "glade", "thicket"],
            "mountain": ["mountain", "peak", "crag", "highland"],
            "underground": ["cave", "cavern", "underground", "subterranean"],
            "aquatic": ["water", "river", "lake", "sea", "ocean"],
            "graveyard": ["grave", "tomb", "crypt", "cemetery"],
            "ruins": ["ruin", "ruined", "ancient"],
            "dungeon": ["dungeon", "labyrinth"],
        },
        "terrain": {
            "marsh": ["swamp", "marsh", "bog"],
            "wooded": ["forest", "wood", "tree"],
            "aerial": ["wing", "fly", "flying", "bird"],
            "subterranean": ["cave", "underground", "tunnel"],
            "flooded": ["water", "flood", "aquatic"],
            "rocky": ["mountain", "rock", "stone"],
            "vertical": ["cliff", "climb"],
            "crypt": ["grave", "tomb", "crypt"],
        },
        "region": {
            "swamp": ["swamp", "marsh", "bog"],
            "forest": ["forest", "wood"],
            "mountain": ["mountain", "peak"],
            "underground": ["cave", "underground"],
            "coastal": ["sea", "ocean", "coast"],
            "grave-realm": ["grave", "tomb", "undead", "wight", "zombie", "skeleton", "ghost"],
        },
        "monster_type": {
            "undead": ["undead", "zombie", "skeleton", "wight", "ghost", "vampire", "lich"],
            "aquatic": ["fish", "shark", "eel", "octopus", "kraken", "water"],
            "amphibian": ["frog", "toad", "newt", "salamander"],
            "aerial": ["bird", "bat", "wing", "fly", "harpy", "roc"],
            "construct": ["construct", "golem", "automaton", "statue"],
            "demon": ["demon"],
            "devil": ["devil"],
            "elemental": ["elemental"],
            "plant": ["plant", "vine", "shambling mound"],
            "fungus": ["fungus", "fungal", "mold", "spore"],
            "insect": ["insect", "beetle", "ant", "wasp"],
            "arachnid": ["spider", "scorpion", "tick"],
            "giant": ["giant", "troll", "ogre", "cyclops"],
            "humanoid": ["humanoid", "goblin", "orc", "hobgoblin", "kobold"],
        },
    }


def _missing_or_unknown(value: Any) -> bool:
    """Return True if a value is missing, blank, or explicitly unknown."""
    if value is None:
        return True
    text = str(value).strip()
    return not text or text.casefold() == "unknown"


def _load_preview_records(
    preview_paths: list[Path] | None = None,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    """Load all normalized monster records with their source metadata."""
    if preview_paths is None:
        preview_paths = [
            DEFAULT_MANDBMASTER_PREVIEW_PATH,
            DEFAULT_MEGADUNGEON_PREVIEW_PATH,
        ]
    return load_all_normalized_previews(preview_paths)


def _get_corrected_value(
    corrections: dict[str, Any], record_id: str, field: str
) -> str | None:
    """Return the corrected value for a field if one exists, otherwise None."""
    entry = corrections.get("corrections", {}).get(record_id, {})
    field_correction = entry.get("fields", {}).get(field)
    if field_correction:
        return str(field_correction.get("corrected_value", "")).strip() or None
    return None


def _affinity_suggestions(
    monster_type: str,
    affinities: ClassificationAffinities,
    options: ClassificationOptions,
) -> dict[str, list[tuple[str, str]]]:
    """Return candidate suggestions from the affinity table for a monster type."""
    result: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for field in ("environment", "terrain", "region"):
        values = affinities.get_all_for_type(monster_type).get(field, {})
        for value, affinity in values.items():
            if value in options.get(field + "s"):
                result[field].append((value, affinity))
    return result


def _keyword_suggestions(
    text: str, keyword_map: dict[str, dict[str, list[str]]], options: ClassificationOptions
) -> dict[str, list[tuple[str, str]]]:
    """Return keyword-based suggestions for each classification field."""
    result: dict[str, list[tuple[str, str]]] = defaultdict(list)
    lowered = text.lower()
    for field, candidates in keyword_map.items():
        option_key = field + "s" if field != "monster_type" else "monster_types"
        for value, keywords in candidates.items():
            if value not in options.get(option_key):
                continue
            if any(keyword in lowered for keyword in keywords):
                # Keyword matches are at best a low-confidence hint.
                result[field].append((value, "sometimes"))
    return result


CONFIDENCE_BY_AFFINITY: dict[str, str] = {
    "always": "high",
    "usually": "medium",
    "sometimes": "low",
    "rarely": "low",
    "never": "very_low",
    "unknown": "low",
}


def _affinity_to_confidence(affinity: str) -> str:
    return CONFIDENCE_BY_AFFINITY.get(affinity, "low")


def _record_suggestion_text(
    record_id: str,
    display_name: str,
    source_id: str,
    suggestions: dict[str, dict[str, Any]],
) -> str:
    """Format suggestions for one record as text."""
    lines = [
        f"{display_name}  (id={record_id}, source={source_id})",
    ]
    for field in CLASSIFICATION_FIELDS:
        if field in suggestions:
            value = suggestions[field]["suggested_value"]
            confidence = suggestions[field]["confidence"]
            reason = suggestions[field]["reason"]
            lines.append(f"  {field}: {value}  [{confidence}]  {reason}")
    return "\n".join(lines)


def generate_suggestions(
    preview_paths: list[Path] | None = None,
    corrections_path: Path | None = None,
    options: ClassificationOptions | None = None,
    affinities: ClassificationAffinities | None = None,
) -> dict[str, Any]:
    """Build conservative classification suggestions for all normalized records.

    Suggestions are produced only when a field is missing/unknown and there is a
    reasonable basis (affinity table or keyword match).  They do not overwrite any
    existing corrections or preview records.
    """
    options = options or load_classification_options()
    affinities = affinities or load_classification_affinities()
    corrections = load_corrections(corrections_path or DEFAULT_CORRECTIONS_PATH)
    keyword_map = _keyword_map()
    records = _load_preview_records(preview_paths)

    record_suggestions: list[dict[str, Any]] = []
    total_suggestions = 0

    for metadata, record in records:
        record_id = record.get("id", "")
        display_name = record.get("display_name", "Unknown")
        source_id = metadata.get("source_id", "unknown")
        description = record.get("description", "")
        name = record.get("name", "")
        search_text = f"{name} {display_name} {description}".lower()

        current_monster_type = _get_corrected_value(
            corrections, record_id, "monster_type"
        ) or record.get("monster_type", "unknown")

        record_suggestion: dict[str, Any] = {
            "record_id": record_id,
            "display_name": display_name,
            "source_id": source_id,
            "suggestions": {},
        }

        # Affinity-based suggestions derived from the current monster type.
        affinity_candidates: dict[str, list[tuple[str, str]]] = {}
        if not _missing_or_unknown(current_monster_type):
            affinity_candidates = _affinity_suggestions(
                current_monster_type, affinities, options
            )

        # Keyword-based suggestions from name/description.
        keyword_candidates = _keyword_suggestions(search_text, keyword_map, options)

        for field in CLASSIFICATION_FIELDS:
            # Do not suggest if the user has already corrected this field.
            if _get_corrected_value(corrections, record_id, field):
                continue

            current_value = record.get(field, "unknown")
            if not _missing_or_unknown(current_value):
                continue

            candidates: list[tuple[str, str, str]] = []
            for value, affinity in affinity_candidates.get(field, []):
                candidates.append(
                    (value, _affinity_to_confidence(affinity), f"affinity from monster_type '{current_monster_type}'")
                )
            for value, _affinity in keyword_candidates.get(field, []):
                candidates.append((value, "low", "keyword match in name/description"))

            if not candidates:
                continue

            # Prefer the highest-confidence candidate.  "always" beats "usually" etc.
            confidence_order = ("high", "medium", "low", "very_low")
            ordered = sorted(
                candidates,
                key=lambda x: (
                    confidence_order.index(x[1]) if x[1] in confidence_order else 99,
                    -ord(x[0][0]),
                ),
            )
            chosen_value, chosen_confidence, chosen_reason = ordered[0]
            total_suggestions += 1
            record_suggestion["suggestions"][field] = {
                "suggested_value": chosen_value,
                "confidence": chosen_confidence,
                "reason": chosen_reason,
                "original_value": current_value,
            }

        if record_suggestion["suggestions"]:
            record_suggestions.append(record_suggestion)

    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "monster_classification_suggestions",
        "record_count": len(record_suggestions),
        "total_suggestions": total_suggestions,
        "suggestions": record_suggestions,
    }


def format_suggestions_report(suggestions: dict[str, Any]) -> str:
    """Render a human-readable report from the suggestions container."""
    lines = [
        "Monster Classification Suggestions Report",
        "=========================================",
        "",
        f"Generated at: {suggestions.get('generated_at', 'unknown')}",
        f"Records with suggestions: {suggestions.get('record_count', 0)}",
        f"Total suggestions: {suggestions.get('total_suggestions', 0)}",
        "",
        "These suggestions are conservative best-guesses only. They do not modify",
        "source previews, live catalogs, or existing user corrections. Review each",
        "suggestion before applying it through the Normalized Monster Review dialog.",
        "",
    ]
    for record in suggestions.get("suggestions", []):
        lines.append(
            _record_suggestion_text(
                record["record_id"],
                record["display_name"],
                record["source_id"],
                record["suggestions"],
            )
        )
        lines.append("")
    return "\n".join(lines)


def write_suggestions(
    suggestions: dict[str, Any] | None = None,
    json_path: Path | None = None,
    report_path: Path | None = None,
) -> dict[str, Any]:
    """Write suggestion JSON and report to the import_reports directory."""
    suggestions = suggestions or generate_suggestions()
    json_path = json_path or DEFAULT_SUGGESTIONS_JSON
    report_path = report_path or DEFAULT_SUGGESTIONS_REPORT
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(suggestions, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(format_suggestions_report(suggestions), encoding="utf-8")
    return suggestions


def main() -> int:
    suggestions = write_suggestions()
    print(f"Wrote suggestions to {DEFAULT_SUGGESTIONS_JSON}")
    print(f"Wrote suggestions report to {DEFAULT_SUGGESTIONS_REPORT}")
    print(
        f"Generated {suggestions['total_suggestions']} suggestions "
        f"across {suggestions['record_count']} records"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
