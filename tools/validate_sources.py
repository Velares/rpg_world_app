from __future__ import annotations

import argparse
import sys
from pathlib import Path


if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.source_registry import (
    DEFAULT_SOURCE_REGISTRY_PATH,
    PROJECT_ROOT,
    build_source_validation_report,
    validate_source_registry,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the editable source registry and local source-file paths."
    )
    parser.add_argument(
        "--registry",
        default=str(DEFAULT_SOURCE_REGISTRY_PATH),
        help="Path to the source registry JSON file.",
    )
    parser.add_argument(
        "--root",
        default=str(PROJECT_ROOT),
        help="Project root used to resolve expected_path entries.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    registry_path = Path(args.registry)
    project_root = Path(args.root)
    try:
        result = validate_source_registry(registry_path, project_root=project_root)
    except (FileNotFoundError, ValueError) as exc:
        print(exc)
        return 1
    report = build_source_validation_report(result)
    print(report, end="")
    return 1 if result.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
