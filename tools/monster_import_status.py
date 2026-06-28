from __future__ import annotations

import argparse
import sys
from pathlib import Path


if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.source_registry import (
    DEFAULT_SOURCE_REGISTRY_PATH,
    PROJECT_ROOT,
    list_source_registry_entry_statuses,
    validate_source_registry,
)
from tools.importers.monster_manual_schema import (
    ADD_BESTIARY_SOURCE_ID,
    DEFAULT_ADD_BESTIARY_IMPORT_REPORT,
    DEFAULT_ADD_BESTIARY_MONSTERS_JSON,
    DEFAULT_ADD_BESTIARY_PACK_JSON,
    DEFAULT_MONSTER_APPENDIX_CATALOG_JSON,
    DEFAULT_MONSTER_APPENDIX_IMPORT_REPORT,
    DEFAULT_MONSTER_CATALOG_JSON,
    DEFAULT_MONSTER_IMPORT_REPORT,
    MEGADUNGEON_MONSTER_SOURCE_ID,
    MONSTER_MANUAL_SOURCE_ID,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Show local readiness for registered monster import sources."
    )
    parser.add_argument(
        "--registry",
        default=str(DEFAULT_SOURCE_REGISTRY_PATH),
        help="Path to the editable source registry JSON.",
    )
    parser.add_argument(
        "--root",
        default=str(PROJECT_ROOT),
        help="Project root used to resolve relative expected paths.",
    )
    return parser.parse_args(argv)


def recommended_commands(source_id: str) -> list[str]:
    if source_id == MONSTER_MANUAL_SOURCE_ID:
        return [
            "python tools/importers/monster_manual_importer.py",
            "python tools/importers/monster_appendix_importer.py",
        ]
    if source_id == ADD_BESTIARY_SOURCE_ID:
        return ["python tools/import_add_bestiary.py"]
    if source_id == MEGADUNGEON_MONSTER_SOURCE_ID:
        return [
            "python tools/importers/megadungeon_monster_importer.py --dry-run-preview",
            "python tools/importers/megadungeon_monster_importer.py --write-content-pack",
        ]
    return ["No importer command assigned yet."]


def output_paths(source_id: str) -> list[str]:
    if source_id == MONSTER_MANUAL_SOURCE_ID:
        return [
            str(DEFAULT_MONSTER_CATALOG_JSON),
            str(DEFAULT_MONSTER_IMPORT_REPORT),
            str(DEFAULT_MONSTER_APPENDIX_CATALOG_JSON),
            str(DEFAULT_MONSTER_APPENDIX_IMPORT_REPORT),
        ]
    if source_id == ADD_BESTIARY_SOURCE_ID:
        return [
            str(DEFAULT_ADD_BESTIARY_PACK_JSON),
            str(DEFAULT_ADD_BESTIARY_MONSTERS_JSON),
            str(DEFAULT_ADD_BESTIARY_IMPORT_REPORT),
        ]
    if source_id == MEGADUNGEON_MONSTER_SOURCE_ID:
        from tools.importers.megadungeon_monster_importer import (
            DEFAULT_CONTENT_MONSTERS_JSON,
            DEFAULT_CONTENT_PACK_JSON,
            DEFAULT_CONTENT_PACK_REPORT_PATH,
            DEFAULT_PREVIEW_OUTPUT_PATH,
            DEFAULT_PREVIEW_REPORT_PATH,
        )
        return [
            str(DEFAULT_PREVIEW_OUTPUT_PATH),
            str(DEFAULT_PREVIEW_REPORT_PATH),
            str(DEFAULT_CONTENT_PACK_JSON),
            str(DEFAULT_CONTENT_MONSTERS_JSON),
            str(DEFAULT_CONTENT_PACK_REPORT_PATH),
        ]
    return []


def build_status_report(registry_path: Path, project_root: Path) -> str:
    validation = validate_source_registry(registry_path, project_root=project_root)
    statuses = list_source_registry_entry_statuses(
        path=registry_path,
        project_root=project_root,
        domain="monsters",
    )
    lines = [
        "Monster Import Readiness",
        "========================",
        "",
        f"Registry path: {registry_path}",
        f"Project root: {project_root}",
        f"Registered monster sources: {len(statuses)}",
        f"Validation warnings: {len(validation.warnings)}",
        f"Validation errors: {len(validation.errors)}",
    ]
    if validation.errors:
        lines.extend(["", "Registry errors:"])
        lines.extend(f"- {error}" for error in validation.errors)
        return "\n".join(lines) + "\n"

    for status in statuses:
        lines.extend(
            [
                "",
                f"{status.title} [{status.source_id}]",
                "-" * (len(status.title) + len(status.source_id) + 3),
                f"Status: {status.status}",
                f"Role: {status.role}",
                f"Importer family: {status.importer_family}",
                f"Expected path: {status.expected_path}",
                f"Resolved path: {status.resolved_path}",
                f"Present locally: {'yes' if status.exists else 'no'}",
                f"Required file: {'yes' if status.file_required else 'no'}",
            ]
        )
        commands = recommended_commands(status.source_id)
        lines.append("Recommended command(s):")
        lines.extend(f"- {command}" for command in commands)
        targets = output_paths(status.source_id)
        if targets:
            lines.append("Primary output path(s):")
            lines.extend(f"- {target}" for target in targets)
        if status.notes:
            lines.append(f"Notes: {status.notes}")

    if validation.warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- {warning}" for warning in validation.warnings)
    else:
        lines.extend(["", "Warnings:", "- None"])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    registry_path = Path(args.registry)
    project_root = Path(args.root)
    report = build_status_report(registry_path, project_root)
    print(report, end="")
    validation = validate_source_registry(registry_path, project_root=project_root)
    return 1 if validation.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
