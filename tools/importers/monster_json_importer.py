from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path


if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.source_registry import get_source_registry_entry_status
from tools.importers.monster_appendix_importer import load_monster_catalog
from tools.importers.monster_catalog_import import (
    JSON_IMPORT_VERSION,
    build_json_import_preview,
    build_json_import_report_text,
    load_json_monster_records,
    merge_monster_catalog,
)
from tools.importers.monster_manual_schema import (
    DEFAULT_MONSTER_CATALOG_JSON,
    DEFAULT_MONSTER_JSON_IMPORT_PREVIEW,
    DEFAULT_MONSTER_JSON_IMPORT_REPORT,
)


@dataclass
class MonsterJsonImportResult:
    preview: dict
    report_text: str
    wrote_catalog: bool


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preview or apply a JSON-based monster catalog import."
    )
    parser.add_argument(
        "json_path",
        help="Path to the JSON file containing one or more monster records.",
    )
    parser.add_argument(
        "--catalog",
        default=str(DEFAULT_MONSTER_CATALOG_JSON),
        help="Path to the existing canonical monster catalog JSON.",
    )
    parser.add_argument(
        "--report",
        default=str(DEFAULT_MONSTER_JSON_IMPORT_REPORT),
        help="Path to write the JSON import report text file.",
    )
    parser.add_argument(
        "--preview-output",
        default=str(DEFAULT_MONSTER_JSON_IMPORT_PREVIEW),
        help="Path to write the dry-run preview JSON.",
    )
    parser.add_argument(
        "--output-catalog",
        default=str(DEFAULT_MONSTER_CATALOG_JSON),
        help="Path to write the merged monster catalog when --write-catalog is used.",
    )
    parser.add_argument(
        "--source-name",
        default=None,
        help="Optional human-readable source name override.",
    )
    parser.add_argument(
        "--source-id",
        default=None,
        help="Optional registered monster source ID to preserve in import metadata and reports.",
    )
    parser.add_argument(
        "--source-type",
        default="json",
        help="Source type label to record in import metadata.",
    )
    parser.add_argument(
        "--write-catalog",
        action="store_true",
        help="Apply safe additions to the output catalog instead of leaving the run as a dry-run preview.",
    )
    return parser.parse_args(argv)


def import_monsters_from_json(
    json_path: Path,
    *,
    catalog_path: Path = DEFAULT_MONSTER_CATALOG_JSON,
    report_path: Path = DEFAULT_MONSTER_JSON_IMPORT_REPORT,
    preview_output_path: Path = DEFAULT_MONSTER_JSON_IMPORT_PREVIEW,
    output_catalog_path: Path = DEFAULT_MONSTER_CATALOG_JSON,
    source_id: str | None = None,
    source_name: str | None = None,
    source_type: str = "json",
    write_catalog: bool = False,
) -> MonsterJsonImportResult:
    if not json_path.exists():
        raise FileNotFoundError(f"JSON monster source not found: {json_path}")

    registry_status = None
    if source_id:
        registry_status = get_source_registry_entry_status(source_id)
        if registry_status is None:
            raise ValueError(f"Unknown source registry ID: {source_id}")
        if registry_status.domain != "monsters":
            raise ValueError(
                f"Source '{source_id}' is registered under domain '{registry_status.domain}', not 'monsters'."
            )

    effective_source_name = source_name or (
        registry_status.title if registry_status is not None else json_path.stem
    )
    existing_catalog = load_monster_catalog(catalog_path)
    normalized_records, warnings, errors = load_json_monster_records(
        json_path,
        source_id_override=registry_status.source_id if registry_status is not None else None,
        source_name=effective_source_name,
        source_type=source_type,
        import_version=JSON_IMPORT_VERSION,
    )
    merge_result = merge_monster_catalog(
        existing_catalog,
        normalized_records,
        apply_safe_additions=write_catalog,
    )
    preview = build_json_import_preview(
        source_path=json_path,
        source_id=registry_status.source_id if registry_status is not None else source_id,
        source_name=effective_source_name,
        source_type=source_type,
        source_status=registry_status.status if registry_status is not None else None,
        existing_catalog=existing_catalog,
        merge_result=merge_result,
        errors=errors,
        warnings=warnings,
    )
    report_text = build_json_import_report_text(
        source_path=json_path,
        source_id=registry_status.source_id if registry_status is not None else source_id,
        source_name=effective_source_name,
        source_type=source_type,
        source_status=registry_status.status if registry_status is not None else None,
        existing_catalog=existing_catalog,
        merge_result=merge_result,
        errors=errors,
        warnings=warnings,
        apply_safe_additions=write_catalog,
    )

    report_path.parent.mkdir(parents=True, exist_ok=True)
    preview_output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report_text, encoding="utf-8")
    preview_output_path.write_text(
        json.dumps(preview, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    if write_catalog:
        output_catalog_path.parent.mkdir(parents=True, exist_ok=True)
        output_catalog_path.write_text(
            json.dumps(merge_result.merged_catalog, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    return MonsterJsonImportResult(
        preview=preview,
        report_text=report_text,
        wrote_catalog=write_catalog,
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = import_monsters_from_json(
            Path(args.json_path),
            catalog_path=Path(args.catalog),
            report_path=Path(args.report),
            preview_output_path=Path(args.preview_output),
            output_catalog_path=Path(args.output_catalog),
            source_id=args.source_id,
            source_name=args.source_name,
            source_type=args.source_type,
            write_catalog=args.write_catalog,
        )
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(exc)
        return 1

    decision_counts = result.preview.get("decision_counts", {})
    print(
        "JSON monster import preview complete. "
        f"normalized={result.preview.get('normalized_record_count', 0)}, "
        f"would_add={decision_counts.get('would_add', 0)}, "
        f"would_update={decision_counts.get('would_update', 0)}, "
        f"conflicts={decision_counts.get('would_conflict', 0) + decision_counts.get('protected_conflict', 0)}."
    )
    if result.wrote_catalog:
        print(f"Wrote merged catalog: {args.output_catalog}")
    print(f"Wrote preview: {args.preview_output}")
    print(f"Wrote report: {args.report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
