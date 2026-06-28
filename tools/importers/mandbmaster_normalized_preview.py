from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from app.monster_catalog import load_core_monster_records
from app.monster_normalization import (
    MANDMASTER_SOURCE_ID,
    MANDMASTER_SOURCE_TITLE,
    map_mandbmaster_core_record_to_normalized,
)
from tools.importers.monster_manual_schema import DEFAULT_MONSTER_CATALOG_JSON, PROJECT_ROOT


DEFAULT_OUTPUT_PATH = (
    PROJECT_ROOT / "data" / "import_reports" / "mandbmaster_normalized_monster_preview.json"
)
DEFAULT_REPORT_PATH = (
    PROJECT_ROOT / "data" / "import_reports" / "mandbmaster_normalized_monster_preview_report.txt"
)


def now_utc_iso() -> str:
    return datetime.now(UTC).isoformat()


def write_json_file(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def write_text_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def build_preview_report(
    *,
    source_catalog_path: Path,
    normalized_records: list[dict[str, Any]],
    preview_output_path: Path,
    report_path: Path,
) -> str:
    status_counts = Counter(str(record.get("review_status") or "unknown") for record in normalized_records)
    by_name = {record["display_name"]: record for record in normalized_records}
    lines = [
        "MandBmaster Normalized Monster Preview",
        "======================================",
        "",
        f"Source ID: {MANDMASTER_SOURCE_ID}",
        f"Source title: {MANDMASTER_SOURCE_TITLE}",
        f"Source catalog: {source_catalog_path}",
        f"Normalized records: {len(normalized_records)}",
        f"Preview output: {preview_output_path}",
        f"Preview report: {report_path}",
        "",
        "Review status counts:",
    ]
    for key, value in sorted(status_counts.items()):
        lines.append(f"- {key}: {value}")

    for sample_name in ("Acanopyornis", "Book Guardian"):
        record = by_name.get(sample_name)
        if record is None:
            continue
        lines.extend(
            [
                "",
                f"{sample_name} normalized sample",
                f"- id: {record['id']}",
                f"- pages: {record['source_page_start']}-{record['source_page_end']}",
                f"- size: {record['size']}",
                f"- movement: {record['movement']}",
                f"- number_appearing: {record['number_appearing']}",
                f"- xp: {record['xp']}",
                f"- level: {record['level']}",
                f"- review_status: {record['review_status']}",
                f"- placeholders: {', '.join(record['placeholder_fields'][:8]) if record['placeholder_fields'] else 'None'}",
            ]
        )
    return "\n".join(lines) + "\n"


def generate_mandbmaster_normalized_preview(
    *,
    catalog_path: Path = DEFAULT_MONSTER_CATALOG_JSON,
    preview_output_path: Path = DEFAULT_OUTPUT_PATH,
    report_path: Path = DEFAULT_REPORT_PATH,
) -> tuple[dict[str, Any], str]:
    core_records = load_core_monster_records(catalog_path)
    normalized_records = [
        map_mandbmaster_core_record_to_normalized(record)
        for record in core_records
    ]
    status_counts = Counter(str(record.get("review_status") or "unknown") for record in normalized_records)
    payload = {
        "generated_at": now_utc_iso(),
        "source_id": MANDMASTER_SOURCE_ID,
        "source_title": MANDMASTER_SOURCE_TITLE,
        "source_catalog": str(catalog_path),
        "record_count": len(normalized_records),
        "review_status_counts": dict(status_counts),
        "normalized_monsters": normalized_records,
    }
    report_text = build_preview_report(
        source_catalog_path=catalog_path,
        normalized_records=normalized_records,
        preview_output_path=preview_output_path,
        report_path=report_path,
    )
    write_json_file(preview_output_path, payload)
    write_text_file(report_path, report_text)
    return payload, report_text


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a non-live normalized preview from the stable MandBmaster core monster catalog."
    )
    parser.add_argument(
        "--catalog-path",
        default=str(DEFAULT_MONSTER_CATALOG_JSON),
        help="Path to the MandBmaster core monster catalog JSON.",
    )
    parser.add_argument(
        "--preview-output",
        default=str(DEFAULT_OUTPUT_PATH),
        help="Path for the normalized preview JSON output.",
    )
    parser.add_argument(
        "--preview-report",
        default=str(DEFAULT_REPORT_PATH),
        help="Path for the normalized preview text report.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload, report_text = generate_mandbmaster_normalized_preview(
        catalog_path=Path(args.catalog_path),
        preview_output_path=Path(args.preview_output),
        report_path=Path(args.preview_report),
    )
    print(report_text, end="")
    return 0 if payload["record_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
