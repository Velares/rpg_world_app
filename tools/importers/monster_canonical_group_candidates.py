from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from tools.importers.monster_catalog_import import normalize_monster_name
from tools.importers.monster_manual_schema import PROJECT_ROOT


DEFAULT_MANDBMASTER_PREVIEW_PATH = (
    PROJECT_ROOT / "data" / "import_reports" / "mandbmaster_normalized_monster_preview.json"
)
DEFAULT_MEGADUNGEON_PREVIEW_PATH = (
    PROJECT_ROOT / "data" / "import_reports" / "megadungeon_normalized_monster_preview.json"
)
DEFAULT_OUTPUT_JSON_PATH = (
    PROJECT_ROOT / "data" / "import_reports" / "monster_canonical_group_candidates.json"
)
DEFAULT_OUTPUT_REPORT_PATH = (
    PROJECT_ROOT / "data" / "import_reports" / "monster_canonical_group_candidates_report.txt"
)

CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"
REVIEW_STATUS_NEEDS_REVIEW = "needs_review"

SOURCE_PDF_ROOT = PROJECT_ROOT / "data" / "import_sources"
EXPECTED_SOURCE_PDFS = {
    "mandbmaster.pdf": "MandBmaster Combined Monster Manual",
    "MegadungeonMonsterManual.pdf": "Megadungeon Monster Manual",
    "Adventures Dark and Deep Bestiaryforingestion.pdf": "Adventures Dark and Deep Bestiary",
    "advanced_labyrinth_lord/Advanced Labyrinth Lord.pdf": "Advanced Labyrinth Lord",
    "labyrinth_lord_revised_edition/Labyrinth Lord Revised Edition.pdf": "Labyrinth Lord Revised Edition",
}


def now_utc_iso() -> str:
    return datetime.now(UTC).isoformat()


def _write_json_file(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def _write_text_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _load_normalized_preview(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Preview file must contain a JSON object: {path}")
    monsters = payload.get("normalized_monsters", [])
    if not isinstance(monsters, list):
        raise ValueError(f"Preview file must contain a 'normalized_monsters' list: {path}")
    return [m for m in monsters if isinstance(m, dict)], payload


def _strip_key(key: str) -> str:
    return key.strip()


def _token_set(name: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", name.casefold()))


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 1.0
    if not left or not right:
        return 0.0
    intersection = len(left & right)
    union = len(left | right)
    return intersection / union if union else 0.0


def _name_variants(name: str) -> dict[str, str]:
    """Return a map of variant key -> reason for the variant."""
    normalized = normalize_monster_name(name)
    variants: dict[str, str] = {}
    if normalized:
        variants[normalized] = "normalized_name"
    # Singular/plural: strip trailing 's' if present.
    if normalized.endswith("s") and len(normalized) > 1:
        variants[normalized[:-1]] = "singular_plural"
    if normalized and not normalized.endswith("s"):
        variants[normalized + "s"] = "singular_plural"
    # Parenthetical variant: remove content inside parentheses.
    cleaned = re.sub(r"\s*\([^)]*\)", "", name.strip()).strip()
    if cleaned and cleaned != name.strip():
        cleaned_key = normalize_monster_name(cleaned)
        if cleaned_key and cleaned_key not in variants:
            variants[cleaned_key] = "parenthetical"
    return variants


def _field_match(record_a: dict[str, Any], record_b: dict[str, Any]) -> tuple[bool, list[str]]:
    fields = ("armor_class", "hit_dice", "movement", "xp")
    matched: list[str] = []
    for field in fields:
        a = record_a.get(field)
        b = record_b.get(field)
        if a is not None and b is not None and str(a).strip() and str(b).strip():
            if str(a).strip().casefold() == str(b).strip().casefold():
                matched.append(field)
    return bool(matched), matched


def _record_summary(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": record.get("id"),
        "display_name": record.get("display_name"),
        "canonical_name": record.get("canonical_name"),
        "source_id": record.get("source_id"),
        "source_title": record.get("source_title"),
        "source_page_start": record.get("source_page_start"),
        "source_page_end": record.get("source_page_end"),
        "armor_class": record.get("armor_class"),
        "hit_dice": record.get("hit_dice"),
        "movement": record.get("movement"),
        "xp": record.get("xp"),
        "review_status": record.get("review_status"),
    }


def _group_id(proposed_name: str, existing: set[str]) -> str:
    base = re.sub(r"[^a-z0-9_]+", "_", proposed_name.casefold().strip())[:60].strip("_")
    candidate = f"cg_{base}"
    if candidate not in existing:
        return candidate
    counter = 1
    while f"{candidate}_{counter}" in existing:
        counter += 1
    return f"{candidate}_{counter}"


def _classify_pair(
    left: dict[str, Any],
    right: dict[str, Any],
) -> tuple[str, float, list[str]] | None:
    """Classify a pair of records into a candidate confidence and reasons.

    Returns None when the pair is not a meaningful candidate.
    """
    left_name = str(left.get("display_name") or left.get("canonical_name") or "").strip()
    right_name = str(right.get("display_name") or right.get("canonical_name") or "").strip()
    if not left_name or not right_name:
        return None

    left_variants = _name_variants(left_name)
    right_variants = _name_variants(right_name)
    right_keys = set(right_variants.keys())

    # Check shared name variants first.
    for key in left_variants:
        if key not in right_keys:
            continue
        left_reason = left_variants[key]
        right_reason = right_variants[key]

        # Singular/plural variant is always medium confidence.
        if left_reason == "singular_plural" or right_reason == "singular_plural":
            return CONFIDENCE_MEDIUM, 0.75, ["singular_plural_variant"]

        # Parenthetical variant is always medium confidence.
        if left_reason == "parenthetical" or right_reason == "parenthetical":
            return CONFIDENCE_MEDIUM, 0.7, ["parenthetical_variant"]

        # Both sides normalize to the same key without variant expansion.
        if left_name == right_name:
            return CONFIDENCE_HIGH, 1.0, ["exact_name_match"]
        return CONFIDENCE_HIGH, 0.95, ["case_punctuation_spacing_insensitive_name_match"]

    # Name similarity plus field match.
    left_tokens = _token_set(left_name)
    right_tokens = _token_set(right_name)
    similarity = _jaccard(left_tokens, right_tokens)
    field_matches, matched_fields = _field_match(left, right)

    if similarity >= 0.5 and field_matches:
        return CONFIDENCE_MEDIUM, round(similarity, 3), [
            "name_similarity_with_field_match",
            f"matched_fields: {', '.join(matched_fields)}",
        ]

    # Name similarity only.
    if similarity >= 0.6:
        return CONFIDENCE_LOW, round(similarity, 3), ["name_similarity_only"]

    return None


def _build_candidate_groups(
    mandbmaster_records: list[dict[str, Any]],
    megadungeon_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build cross-source candidate groups without merging records."""
    seen_pairs: set[tuple[str, str]] = set()
    groups: list[dict[str, Any]] = []
    used_ids: set[str] = set()

    for left in mandbmaster_records:
        left_id = str(left.get("id") or "")
        if not left_id:
            continue
        for right in megadungeon_records:
            right_id = str(right.get("id") or "")
            if not right_id:
                continue
            pair_key = tuple(sorted([left_id, right_id]))
            if pair_key in seen_pairs:
                continue
            classification = _classify_pair(left, right)
            if classification is None:
                continue
            confidence, score, reasons = classification
            seen_pairs.add(pair_key)

            proposed_name = str(left.get("canonical_name") or left.get("display_name") or "Unknown")
            group_id = _group_id(proposed_name, used_ids)
            used_ids.add(group_id)

            notes = [
                "Candidate group generated by cross-source comparison.",
                "This is a review suggestion only; source variants are preserved.",
            ]
            if confidence != CONFIDENCE_HIGH:
                notes.append("Low or medium confidence: manual review recommended.")

            groups.append(
                {
                    "candidate_group_id": group_id,
                    "proposed_canonical_name": proposed_name,
                    "match_score": score,
                    "confidence": confidence,
                    "match_reasons": reasons,
                    "review_status": REVIEW_STATUS_NEEDS_REVIEW,
                    "user_decision": None,
                    "notes": notes,
                    "records": [_record_summary(left), _record_summary(right)],
                }
            )

    # Sort by confidence (high -> medium -> low) then descending score.
    confidence_order = {CONFIDENCE_HIGH: 0, CONFIDENCE_MEDIUM: 1, CONFIDENCE_LOW: 2}
    groups.sort(key=lambda g: (confidence_order.get(g["confidence"], 3), -g["match_score"]))
    return groups


def _build_text_report(
    *,
    mandbmaster_count: int,
    megadungeon_count: int,
    groups: list[dict[str, Any]],
    output_json_path: Path,
    output_report_path: Path,
    source_pdf_status: list[str],
) -> str:
    confidence_counts = defaultdict(int)
    for group in groups:
        confidence_counts[group["confidence"]] += 1

    exact_count = sum(
        1 for group in groups if "exact_name_match" in group["match_reasons"]
    )

    lines = [
        "Monster Canonical Group Candidates",
        "==================================",
        "",
        f"Generated at: {now_utc_iso()}",
        f"MandBmaster records read: {mandbmaster_count}",
        f"Megadungeon records read: {megadungeon_count}",
        f"Total candidate groups emitted: {len(groups)}",
        f"High-confidence candidates: {confidence_counts.get(CONFIDENCE_HIGH, 0)}",
        f"Medium-confidence candidates: {confidence_counts.get(CONFIDENCE_MEDIUM, 0)}",
        f"Low-confidence candidates: {confidence_counts.get(CONFIDENCE_LOW, 0)}",
        f"Exact-name match count: {exact_count}",
        "",
        "Output paths:",
        f"- JSON: {output_json_path}",
        f"- Report: {output_report_path}",
        "",
        "Source PDF folder status:",
    ]
    lines.extend(f"- {line}" for line in source_pdf_status)
    lines.extend(
        [
            "",
            "IMPORTANT: This report is a review aid only.",
            "- No records were merged.",
            "- No live catalog JSON was modified.",
            "- No final master monster catalog was created or changed.",
            "- Each candidate group defaults to review_status='needs_review'.",
            "- A user_decision field is reserved for later approval/rejection.",
            "",
            "Top 20 candidate groups by confidence and score:",
            "------------------------------------------------",
        ]
    )

    for index, group in enumerate(groups[:20], 1):
        lines.append("")
        lines.append(f"{index}. [{group['confidence'].upper()}] {group['proposed_canonical_name']} "
                     f"(score={group['match_score']})")
        lines.append(f"    Group ID: {group['candidate_group_id']}")
        lines.append(f"    Reasons: {', '.join(group['match_reasons'])}")
        for record in group["records"]:
            lines.append(
                f"    - {record['display_name']} [{record['source_id']}] "
                f"AC={record['armor_class']}, HD={record['hit_dice']}, "
                f"MV={record['movement']}, XP={record['xp']}"
            )

    ambiguous = [group for group in groups if group["confidence"] != CONFIDENCE_HIGH]
    lines.extend(
        [
            "",
            f"Ambiguous / needs-review cases: {len(ambiguous)}",
            "------------------------------------------------",
        ]
    )
    for group in ambiguous[:20]:
        lines.append("")
        lines.append(f"- [{group['confidence'].upper()}] {group['proposed_canonical_name']} "
                     f"(score={group['match_score']})")
        lines.append(f"  Reasons: {', '.join(group['match_reasons'])}")
        for record in group["records"]:
            lines.append(f"    * {record['display_name']} [{record['source_id']}]")

    return "\n".join(lines) + "\n"


def _check_source_pdf_status() -> list[str]:
    status: list[str] = []
    for relative_path, title in EXPECTED_SOURCE_PDFS.items():
        path = SOURCE_PDF_ROOT / relative_path
        if path.exists():
            status.append(f"PRESENT: {title} ({relative_path})")
        else:
            status.append(f"MISSING: {title} ({relative_path})")
    return status


def generate_canonical_group_candidates(
    *,
    mandbmaster_preview_path: Path = DEFAULT_MANDBMASTER_PREVIEW_PATH,
    megadungeon_preview_path: Path = DEFAULT_MEGADUNGEON_PREVIEW_PATH,
    output_json_path: Path = DEFAULT_OUTPUT_JSON_PATH,
    output_report_path: Path = DEFAULT_OUTPUT_REPORT_PATH,
) -> tuple[dict[str, Any], str]:
    mandbmaster_records, mandbmaster_payload = _load_normalized_preview(mandbmaster_preview_path)
    megadungeon_records, megadungeon_payload = _load_normalized_preview(megadungeon_preview_path)
    groups = _build_candidate_groups(mandbmaster_records, megadungeon_records)

    payload = {
        "generated_at": now_utc_iso(),
        "mandbmaster_preview": str(mandbmaster_preview_path),
        "megadungeon_preview": str(megadungeon_preview_path),
        "mandbmaster_record_count": len(mandbmaster_records),
        "megadungeon_record_count": len(megadungeon_records),
        "total_candidate_groups": len(groups),
        "confidence_counts": {
            CONFIDENCE_HIGH: sum(1 for g in groups if g["confidence"] == CONFIDENCE_HIGH),
            CONFIDENCE_MEDIUM: sum(1 for g in groups if g["confidence"] == CONFIDENCE_MEDIUM),
            CONFIDENCE_LOW: sum(1 for g in groups if g["confidence"] == CONFIDENCE_LOW),
        },
        "no_merge_warning": "Candidate groups are review suggestions only. Do not merge records without review.",
        "candidate_groups": groups,
    }

    source_pdf_status = _check_source_pdf_status()
    report_text = _build_text_report(
        mandbmaster_count=len(mandbmaster_records),
        megadungeon_count=len(megadungeon_records),
        groups=groups,
        output_json_path=output_json_path,
        output_report_path=output_report_path,
        source_pdf_status=source_pdf_status,
    )

    _write_json_file(output_json_path, payload)
    _write_text_file(output_report_path, report_text)
    return payload, report_text


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a non-merging cross-source canonical-group candidate report "
                    "for normalized monster previews."
    )
    parser.add_argument(
        "--mandbmaster-preview",
        default=str(DEFAULT_MANDBMASTER_PREVIEW_PATH),
        help="Path to the MandBmaster normalized monster preview JSON.",
    )
    parser.add_argument(
        "--megadungeon-preview",
        default=str(DEFAULT_MEGADUNGEON_PREVIEW_PATH),
        help="Path to the Megadungeon normalized monster preview JSON.",
    )
    parser.add_argument(
        "--output-json",
        default=str(DEFAULT_OUTPUT_JSON_PATH),
        help="Path for the candidate groups JSON output.",
    )
    parser.add_argument(
        "--output-report",
        default=str(DEFAULT_OUTPUT_REPORT_PATH),
        help="Path for the candidate groups text report output.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload, report_text = generate_canonical_group_candidates(
        mandbmaster_preview_path=Path(args.mandbmaster_preview),
        megadungeon_preview_path=Path(args.megadungeon_preview),
        output_json_path=Path(args.output_json),
        output_report_path=Path(args.output_report),
    )
    print(report_text, end="")
    return 0 if payload["total_candidate_groups"] >= 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
