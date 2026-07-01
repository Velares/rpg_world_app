from __future__ import annotations

import json
import re
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


# Keywords that earn "high" confidence when they appear as whole-word tokens in
# the monster's title/name. These are extremely explicit identity words.
_HIGH_CONFIDENCE_NAME_KEYWORDS: dict[str, dict[str, list[str]]] = {
    "monster_type": {
        "undead": ["skeleton", "zombie", "ghoul", "wight", "vampire", "lich", "mummy", "spectre", "ghost", "phantom", "wraith"],
        "construct": ["golem", "automaton", "animated statue"],
        "demon": ["demon"],
        "devil": ["devil"],
        "elemental": ["elemental"],
        "fungus": ["fungus", "mold", "spore"],
        "arachnid": ["spider", "scorpion"],
        "amphibian": ["frog", "toad", "salamander"],
        "fish": ["fish", "shark", "eel", "squid", "octopus"],
        "plant": ["shambling mound"],
        "insect": ["insect"],
    },
}


def _keyword_map() -> dict[str, dict[str, list[str]]]:
    """Return token- and phrase-aware keyword hints for classification fields.

    `monster_type` is the primary nature/body/origin of the monster. `category`
    is a broader future gameplay/catalog bucket and is intentionally left out
    of this mapping; it may become controlled later.

    Keywords are matched with word-boundary checks so that short roots like
    ``ant`` do not match inside unrelated words. Phrases (e.g.
    ``shambling mound``) are matched as exact substrings. Title/name matches
    are stronger than description matches. These hints are still conservative
    and are not a replacement for human review.
    """
    return {
        "environment": {
            "swamp": ["swamp", "marsh", "bog", "fen"],
            "forest": ["forest", "wood", "glade", "thicket"],
            "mountain": ["mountain", "peak", "crag", "highland"],
            "underground": ["cave", "cavern", "underground", "subterranean"],
            "aquatic": ["water", "river", "lake", "sea", "ocean"],
            "graveyard": ["grave", "tomb", "crypt", "cemetery"],
            "ruins": ["ruins", "ruined", "ancient"],
            "dungeon": ["dungeon", "labyrinth"],
            "sky": ["sky", "cloud"],
            "river": ["river"],
            "lake": ["lake"],
            "sea": ["sea"],
            "volcanic": ["volcano", "volcanic", "lava", "fire"],
            "shadow": ["shadow"],
            "faerie": ["faerie", "fae"],
        },
        "terrain": {
            "marsh": ["swamp", "marsh", "bog"],
            "wooded": ["forest", "wood", "tree"],
            "aerial": ["wing", "wings", "flying", "fly", "bird", "eagle", "harpy", "roc", "bat"],
            "subterranean": ["cave", "underground", "tunnel"],
            "flooded": ["flood", "flooded", "aquatic"],
            "rocky": ["mountain", "rock", "stone"],
            "vertical": ["cliff", "climb"],
            "crypt": ["grave", "tomb", "crypt"],
            "underwater": ["underwater", "sea", "ocean", "river", "lake"],
            "ice": ["ice", "frozen"],
            "snow": ["snow"],
            "sand": ["sand"],
            "dune": ["dune"],
            "lava": ["lava", "fire"],
            "burrow": ["burrow"],
            "reef": ["reef"],
            "canopy": ["canopy"],
            "rubble": ["rubble", "ruins"],
        },
        "region": {
            "swamp": ["swamp", "marsh", "bog"],
            "forest": ["forest", "wood"],
            "mountain": ["mountain", "peak"],
            "underground": ["cave", "underground"],
            "coastal": ["sea", "ocean", "coast"],
            "grave-realm": ["grave", "tomb", "undead", "wight", "zombie", "skeleton", "ghost"],
            "ocean": ["ocean", "sea"],
            "riverlands": ["river"],
            "volcanic": ["volcano", "volcanic", "lava"],
            "sky-realm": ["sky", "cloud"],
            "faerie": ["faerie", "fae"],
            "shadow-realm": ["shadow"],
            "elemental plane": ["elemental"],
            "hell": ["devil"],
            "abyss": ["demon"],
        },
        "monster_type": {
            "undead": ["undead", "zombie", "skeleton", "ghoul", "wight", "ghost", "vampire", "lich", "mummy", "spectre", "phantom", "wraith"],
            "aquatic": ["crab", "lobster"],
            "fish": ["fish", "shark", "eel", "squid", "octopus"],
            "amphibian": ["frog", "toad", "newt", "salamander"],
            "avian": ["bird", "eagle", "harpy", "roc"],
            "construct": ["construct", "golem", "automaton", "animated statue"],
            "demon": ["demon"],
            "devil": ["devil"],
            "elemental": ["elemental"],
            "plant": ["plant", "vine", "shambling mound", "lichen", "creeper", "moss"],
            "fungus": ["fungus", "fungal", "mold", "spore", "mycelium"],
            "insect": ["insect", "beetle", "ant", "wasp", "bee", "mosquito"],
            "arachnid": ["spider", "scorpion", "tick"],
            "giant": ["giant", "troll", "ogre", "cyclops"],
            "humanoid": ["humanoid", "goblin", "orc", "hobgoblin", "kobold"],
            "worm": ["worm", "wurm", "leech"],
            "vermin": ["vermin"],
            "shapechanger": ["shapechanger", "shapeshifter"],
            "lycanthrope": ["lycanthrope", "werewolf", "werebear", "weretiger"],
            "celestial": ["celestial", "angel"],
            "dragon": ["dragon"],
        },
    }


def _missing_or_unknown(value: Any) -> bool:
    """Return True if a value is missing, blank, or explicitly unknown."""
    if value is None:
        return True
    text = str(value).strip()
    return not text or text.casefold() == "unknown"


def _record_title_text(record: dict[str, Any]) -> str:
    """Return a single title/name string for keyword matching.

    Real normalized/staged records may use ``display_name`` or ``canonical_name``
    instead of (or in addition to) ``name``. Synthetic test records may rely on
    ``name`` alone. Effective/derived records can also nest the name under an
    ``effective`` object. We concatenate all available sources, separated by spaces,
    so that title evidence works for every supported record shape.
    """
    parts: list[str] = []
    for key in ("name", "display_name", "canonical_name"):
        value = record.get(key)
        if value and str(value).strip():
            parts.append(str(value).strip())
    effective = record.get("effective") or {}
    if isinstance(effective, dict):
        for key in ("display_name", "canonical_name", "name"):
            value = effective.get(key)
            if value and str(value).strip():
                parts.append(str(value).strip())
    return " ".join(parts)


_WORD_BOUNDARY_RE_CACHE: dict[str, re.Pattern[str]] = {}


def _compile_word_pattern(keyword: str) -> re.Pattern[str]:
    """Compile a case-insensitive whole-word regex for a single keyword."""
    if keyword in _WORD_BOUNDARY_RE_CACHE:
        return _WORD_BOUNDARY_RE_CACHE[keyword]
    escaped = re.escape(keyword)
    pattern = re.compile(rf"\b{escaped}\b", re.IGNORECASE)
    _WORD_BOUNDARY_RE_CACHE[keyword] = pattern
    return pattern


def _text_contains_keyword(text: str, keyword: str) -> bool:
    """Return True if ``keyword`` appears in ``text`` with sensible boundaries.

    * Multi-word phrases are matched as exact substrings.
    * Single-word keywords are matched as whole words (``\b``).
    * Underscores and hyphens are treated as word boundaries.
    """
    if not text or not keyword:
        return False
    normalized = re.sub(r"[_-]", " ", text)
    if " " in keyword:
        return keyword.lower() in normalized.lower()
    return bool(_compile_word_pattern(keyword).search(normalized))


def _keyword_matches_in_text(
    text: str, keyword_map: dict[str, dict[str, list[str]]], options: ClassificationOptions
) -> dict[str, list[tuple[str, str]]]:
    """Return keyword-based (value, affinity) hits for each classification field.

    This only records that a keyword matched; confidence is assigned later based on
    whether the match was in the title/name or the description.
    """
    result: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for field, candidates in keyword_map.items():
        option_key = field + "s" if field != "monster_type" else "monster_types"
        for value, keywords in candidates.items():
            if value not in options.get(option_key):
                continue
            if any(_text_contains_keyword(text, keyword) for keyword in keywords):
                result[field].append((value, "sometimes"))
    return result


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
    corrections: dict[str, Any],
    record_id: str,
    field: str,
    options: ClassificationOptions | None = None,
) -> str | None:
    """Return the corrected value for a field if one exists and is valid.

    Corrected classification values are normalized to lowercase and accepted
    only when they exist in the controlled options. Invalid corrections are
    ignored so they cannot corrupt suggestions.
    """
    entry = corrections.get("corrections", {}).get(record_id, {})
    field_correction = entry.get("fields", {}).get(field)
    if not field_correction:
        return None
    raw = str(field_correction.get("corrected_value", "")).strip()
    if not raw:
        return None
    if field in CLASSIFICATION_FIELDS and options:
        option_key = field + "s" if field != "monster_type" else "monster_types"
        allowed = {v.casefold(): v for v in options.get(option_key)}
        normalized = raw.casefold()
        if normalized in allowed:
            return allowed[normalized]
        return None
    return raw


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


def _description_has_undead_evidence(description: str, keyword_map: dict[str, dict[str, list[str]]]) -> bool:
    """Return True if the description explicitly contains undead keywords."""
    undead_keywords = keyword_map.get("monster_type", {}).get("undead", [])
    return any(_text_contains_keyword(description, kw) for kw in undead_keywords)


def _apply_title_priority_rules(
    result: dict[str, list[tuple[str, str, str]]],
    title_text: str,
    description: str,
    keyword_map: dict[str, dict[str, list[str]]],
) -> dict[str, list[tuple[str, str, str]]]:
    """Apply narrow, deterministic priority rules to keyword candidates.

    These rules are intentionally conservative and only override obviously
    weaker candidates. They do not build a full taxonomy engine.
    """
    title_lower = title_text.lower()
    monster_hits = {value for value, _affinity, _location in result.get("monster_type", [])}

    # Golem title: construct outranks elemental/dragon/undead unless stronger text
    # explicitly says otherwise. The title itself is the strong text here.
    if "golem" in title_lower and "construct" in monster_hits:
        result["monster_type"] = [
            (value, affinity, location)
            for value, affinity, location in result["monster_type"]
            if value not in ("elemental", "dragon", "undead")
        ]

    # Fire toad: amphibian stays primary; fire/elemental may influence placement
    # or appear as alternatives, but it should not override toad.
    if "toad" in title_lower and "amphibian" in monster_hits:
        result["monster_type"] = [
            (value, affinity, location)
            for value, affinity, location in result["monster_type"]
            if value != "elemental"
        ]

    # Fungal ant: preserve insect/fungus candidates over unrelated undead unless
    # the description explicitly mentions undead evidence.
    if "fungal" in title_lower and "ant" in title_lower:
        if not _description_has_undead_evidence(description, keyword_map):
            result["monster_type"] = [
                (value, affinity, location)
                for value, affinity, location in result["monster_type"]
                if value != "undead"
            ]

    # Giant as a size prefix: if the title also carries a more specific creature
    # keyword, drop the generic giant match (e.g. Giant Crab, Giant Leech).
    if "giant" in {value for value, _affinity, _location in result.get("monster_type", [])}:
        specific_hits = {
            value
            for value, _affinity, _location in result["monster_type"]
            if value != "giant"
        }
        if specific_hits:
            result["monster_type"] = [
                (value, affinity, location)
                for value, affinity, location in result["monster_type"]
                if value != "giant"
            ]
    return result


def _keyword_suggestions(
    title_text: str,
    description: str,
    keyword_map: dict[str, dict[str, list[str]]],
    options: ClassificationOptions,
) -> dict[str, list[tuple[str, str, str]]]:
    """Return keyword-based suggestions for each classification field.

    Each candidate is a tuple of (value, affinity, location). ``location`` is
    either ``"name"`` or ``"description"`` and is used later to set confidence.
    ``title_text`` combines ``name``, ``display_name``, ``canonical_name``, and
    any nested ``effective`` values so that real normalized records receive
    title-level confidence.
    """
    result: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    title_hits = _keyword_matches_in_text(title_text, keyword_map, options)
    description_hits = _keyword_matches_in_text(description, keyword_map, options)
    for field in keyword_map:
        for value, affinity in title_hits.get(field, []):
            result[field].append((value, affinity, "name"))
        for value, affinity in description_hits.get(field, []):
            # Only record description hits if the same value was not already
            # matched in the title, to avoid double-counting.
            title_values = {v for v, _ in title_hits.get(field, [])}
            if value not in title_values:
                result[field].append((value, affinity, "description"))

    return _apply_title_priority_rules(result, title_text, description, keyword_map)


CONFIDENCE_BY_AFFINITY: dict[str, str] = {
    "always": "high",
    "usually": "medium",
    "sometimes": "low",
    "rarely": "low",
    "never": "very_low",
    "unknown": "low",
}


def _affinity_to_confidence(affinity: str, evidence_source: str = "imported") -> str:
    """Map an affinity value to a suggestion confidence.

    Affinities derived from a user-corrected monster_type are stronger evidence
    than those derived from an imported/generated value. A keyword-derived type
    that came from the title/name is stronger than imported but weaker than
    corrected.
    """
    base = CONFIDENCE_BY_AFFINITY.get(affinity, "low")
    if evidence_source == "corrected" and base == "low":
        return "medium"
    if evidence_source == "title" and base in ("always", "usually"):
        return "medium"
    if evidence_source in ("imported", "title") and base == "high":
        # Imported/generated/title types are strong but not definitive.
        return "medium"
    return base


def _keyword_to_confidence(
    field: str, value: str, location: str, title_text: str
) -> str:
    """Map a keyword hit location to a suggestion confidence."""
    if location == "name":
        high_keywords = _HIGH_CONFIDENCE_NAME_KEYWORDS.get(field, {}).get(value, [])
        if high_keywords and any(
            _text_contains_keyword(title_text, keyword) for keyword in high_keywords
        ):
            return "high"
        return "medium"
    # description-only matches are low-confidence hints
    return "low"


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
            alternatives = suggestions[field].get("alternatives")
            lines.append(f"  {field}: {value}  [{confidence}]  {reason}")
            if alternatives:
                alt_text = ", ".join(
                    f"{alt['value']} [{alt['confidence']}]" for alt in alternatives
                )
                lines.append(f"      alternatives: {alt_text}")
    return "\n".join(lines)


def _suggest_for_record(
    record: dict[str, Any],
    corrections: dict[str, Any],
    options: ClassificationOptions,
    affinities: ClassificationAffinities,
    keyword_map: dict[str, dict[str, list[str]]],
) -> tuple[dict[str, Any], int]:
    """Return suggestion dictionary and suggestion count for a single record."""
    record_id = record.get("id", "")
    display_name = record.get("display_name", "Unknown")
    source_id = record.get("source_id", "unknown")
    description = record.get("description", "")
    title_text = _record_title_text(record)

    corrected_monster_type = _get_corrected_value(
        corrections, record_id, "monster_type", options
    )
    imported_monster_type = record.get("monster_type", "unknown")
    current_monster_type = corrected_monster_type or imported_monster_type
    type_evidence_source = "corrected" if corrected_monster_type else "imported"

    record_suggestion: dict[str, Any] = {
        "record_id": record_id,
        "display_name": display_name,
        "source_id": source_id,
        "suggestions": {},
    }

    # Keyword-based suggestions from title/name/description, treated separately.
    keyword_candidates = _keyword_suggestions(
        title_text, description, keyword_map, options
    )

    # If the imported/corrected type is unknown, use a keyword-suggested type
    # as a weak basis for affinity-based placement suggestions. This lets a
    # name like "Giant Frog" produce both monster_type: amphibian and the
    # marsh/swamp placement that follows from amphibian affinities. Keyword types
    # matched in the title/name are treated as stronger evidence than types only
    # seen in the description.
    affinity_type = current_monster_type
    affinity_evidence_source = type_evidence_source
    if _missing_or_unknown(current_monster_type):
        keyword_type_hits = keyword_candidates.get("monster_type", [])
        if keyword_type_hits:
            confidence_order = ("high", "medium", "low", "very_low")
            best = sorted(
                keyword_type_hits,
                key=lambda x: (
                    confidence_order.index(
                        _keyword_to_confidence("monster_type", x[0], x[2], title_text)
                    )
                    if _keyword_to_confidence("monster_type", x[0], x[2], title_text)
                    in confidence_order
                    else 99,
                    -ord(x[0][0]),
                ),
            )[0]
            best_confidence = _keyword_to_confidence(
                "monster_type", best[0], best[2], title_text
            )
            if best_confidence in ("high", "medium"):
                affinity_type = best[0]
                affinity_evidence_source = "title" if best[2] == "name" else "imported"

    # Affinity-based suggestions derived from the current monster type.
    affinity_candidates: dict[str, list[tuple[str, str]]] = {}
    if not _missing_or_unknown(affinity_type):
        affinity_candidates = _affinity_suggestions(
            affinity_type, affinities, options
        )

    total_suggestions = 0
    for field in CLASSIFICATION_FIELDS:
        # Do not suggest if the user has already corrected this field.
        if _get_corrected_value(corrections, record_id, field, options):
            continue

        current_value = record.get(field, "unknown")
        if not _missing_or_unknown(current_value):
            continue

        # Candidate tuples: (value, confidence, reason, source). ``source`` is used
        # only for tie-breaking so that affinity-derived placement outranks a raw
        # keyword tie at the same confidence (e.g. amphibian swamp vs. fire volcanic).
        candidates: list[tuple[str, str, str, str]] = []
        for value, affinity in affinity_candidates.get(field, []):
            confidence = _affinity_to_confidence(affinity, affinity_evidence_source)
            if affinity_evidence_source == "corrected":
                reason = f"affinity from corrected monster_type '{affinity_type}'"
            elif affinity_evidence_source == "title":
                reason = f"affinity from title-derived monster_type '{affinity_type}'"
            else:
                reason = f"affinity from imported monster_type '{affinity_type}'"
            candidates.append((value, confidence, reason, "affinity"))
        for value, _affinity, location in keyword_candidates.get(field, []):
            confidence = _keyword_to_confidence(field, value, location, title_text)
            reason = f"keyword match in {location}"
            candidates.append((value, confidence, reason, "keyword"))

        if not candidates:
            continue

        # Prefer the highest-confidence candidate. Preserve ties as alternatives.
        confidence_order = ("high", "medium", "low", "very_low")
        source_order = {"affinity": 0, "keyword": 1}
        ordered = sorted(
            candidates,
            key=lambda x: (
                confidence_order.index(x[1]) if x[1] in confidence_order else 99,
                source_order.get(x[3], 99),
                -ord(x[0][0]),
            ),
        )
        chosen_value, chosen_confidence, chosen_reason, _chosen_source = ordered[0]
        alternatives = [
            {"value": value, "confidence": confidence, "reason": reason}
            for value, confidence, reason, _source in ordered[1:]
            if confidence == chosen_confidence
        ]
        total_suggestions += 1
        record_suggestion["suggestions"][field] = {
            "suggested_value": chosen_value,
            "confidence": chosen_confidence,
            "reason": chosen_reason,
            "original_value": current_value,
        }
        if alternatives:
            record_suggestion["suggestions"][field]["alternatives"] = alternatives

    return record_suggestion, total_suggestions


def suggest_for_record(
    record: dict[str, Any],
    corrections: dict[str, Any] | None = None,
    options: ClassificationOptions | None = None,
    affinities: ClassificationAffinities | None = None,
) -> dict[str, Any]:
    """Public test helper: build suggestions for a single synthetic record.

    Corrections default to empty. This does not read or write any files.
    """
    options = options or load_classification_options()
    affinities = affinities or load_classification_affinities()
    corrections = corrections or {}
    keyword_map = _keyword_map()
    suggestions, _count = _suggest_for_record(
        record, corrections, options, affinities, keyword_map
    )
    return suggestions


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

    for _metadata, record in records:
        # The source_id is stored in record for the helper.
        record_suggestion, count = _suggest_for_record(
            record, corrections, options, affinities, keyword_map
        )
        if record_suggestion["suggestions"]:
            record_suggestions.append(record_suggestion)
            total_suggestions += count

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
) -> tuple[Path, Path]:
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
    return json_path, report_path


def main() -> int:
    suggestions = generate_suggestions()
    json_path, report_path = write_suggestions(suggestions)
    print(f"Wrote suggestions to {json_path}")
    print(f"Wrote suggestions report to {report_path}")
    print(
        f"Generated {suggestions['total_suggestions']} suggestions "
        f"across {suggestions['record_count']} records"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
