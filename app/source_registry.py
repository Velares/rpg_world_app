from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_REGISTRY_PATH = PROJECT_ROOT / "data" / "source_registry.json"
ALLOWED_DOMAINS = {
    "rules_references",
    "monsters",
    "spells",
    "magic_items",
    "mundane_equipment",
    "treasure_tables",
    "modules_keyed_locations",
    "generator_tables",
    "factions_religions_cults",
}
ALLOWED_STATUSES = {
    "active",
    "inactive",
    "comparison_only",
    "placeholder",
    "deprecated",
}
REQUIRED_ENTRY_FIELDS = (
    "source_id",
    "title",
    "domain",
    "role",
    "status",
    "expected_path",
    "file_required",
    "importer_family",
    "priority",
    "notes",
    "active_for_rules",
    "active_for_content",
)


@dataclass
class SourceRegistryPathStatus:
    source_id: str
    title: str
    domain: str
    role: str
    status: str
    expected_path: str
    resolved_path: Path
    exists: bool
    file_required: bool
    active_for_rules: bool
    active_for_content: bool


@dataclass
class SourceRegistryValidationResult:
    registry_path: Path
    project_root: Path
    payload: dict[str, Any]
    entries: list[dict[str, Any]]
    path_statuses: list[SourceRegistryPathStatus]
    warnings: list[str]
    errors: list[str]

    @property
    def total_sources(self) -> int:
        return len(self.entries)

    @property
    def present_files(self) -> int:
        return sum(1 for item in self.path_statuses if item.exists)

    @property
    def missing_expected_files(self) -> int:
        return sum(1 for item in self.path_statuses if not item.exists)

    @property
    def active_sources(self) -> int:
        return sum(1 for item in self.path_statuses if item.status == "active")

    @property
    def inactive_sources(self) -> int:
        return sum(1 for item in self.path_statuses if item.status in {"inactive", "deprecated"})

    @property
    def comparison_only_sources(self) -> int:
        return sum(1 for item in self.path_statuses if item.status == "comparison_only")

    @property
    def placeholder_sources(self) -> int:
        return sum(1 for item in self.path_statuses if item.status == "placeholder")

    @property
    def counts_by_domain(self) -> dict[str, int]:
        return dict(sorted(Counter(item.domain for item in self.path_statuses).items()))

    @property
    def counts_by_status(self) -> dict[str, int]:
        return dict(sorted(Counter(item.status for item in self.path_statuses).items()))


def load_source_registry_payload(path: Path = DEFAULT_SOURCE_REGISTRY_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Source registry root must be a JSON object.")
    return payload


def get_source_registry_entries(payload: dict[str, Any]) -> list[dict[str, Any]]:
    entries = payload.get("sources")
    if not isinstance(entries, list):
        raise ValueError("Source registry must contain a top-level 'sources' list.")
    return entries


def validate_source_registry(
    path: Path = DEFAULT_SOURCE_REGISTRY_PATH,
    *,
    project_root: Path = PROJECT_ROOT,
) -> SourceRegistryValidationResult:
    payload = load_source_registry_payload(path)
    entries = get_source_registry_entries(payload)
    return validate_source_registry_entries(
        entries,
        registry_path=path,
        project_root=project_root,
        payload=payload,
    )


def validate_source_registry_entries(
    entries: list[dict[str, Any]],
    *,
    registry_path: Path,
    project_root: Path,
    payload: dict[str, Any] | None = None,
) -> SourceRegistryValidationResult:
    warnings: list[str] = []
    errors: list[str] = []
    path_statuses: list[SourceRegistryPathStatus] = []
    seen_source_ids: set[str] = set()

    for index, entry in enumerate(entries, start=1):
        prefix = f"Entry {index}"
        if not isinstance(entry, dict):
            errors.append(f"{prefix}: registry entry must be a JSON object.")
            continue

        missing_fields = [field_name for field_name in REQUIRED_ENTRY_FIELDS if field_name not in entry]
        if missing_fields:
            errors.append(f"{prefix}: missing required fields: {', '.join(missing_fields)}")
            continue

        source_id = _non_empty_text(entry.get("source_id"))
        title = _non_empty_text(entry.get("title"))
        domain = _non_empty_text(entry.get("domain"))
        role = _non_empty_text(entry.get("role"))
        status = _non_empty_text(entry.get("status"))
        expected_path = _non_empty_text(entry.get("expected_path"))
        importer_family = _non_empty_text(entry.get("importer_family"))
        notes = _non_empty_text(entry.get("notes"))
        file_required = entry.get("file_required")
        priority = entry.get("priority")
        active_for_rules = entry.get("active_for_rules")
        active_for_content = entry.get("active_for_content")

        malformed_fields: list[str] = []
        for field_name, value in (
            ("source_id", source_id),
            ("title", title),
            ("domain", domain),
            ("role", role),
            ("status", status),
            ("expected_path", expected_path),
            ("importer_family", importer_family),
            ("notes", notes),
        ):
            if value is None:
                malformed_fields.append(field_name)
        if malformed_fields:
            errors.append(f"{prefix}: required text fields must be non-empty: {', '.join(malformed_fields)}")
            continue

        if source_id in seen_source_ids:
            errors.append(f"{prefix}: duplicate source_id '{source_id}'")
        else:
            seen_source_ids.add(source_id)

        if domain not in ALLOWED_DOMAINS:
            errors.append(
                f"{prefix}: unknown domain '{domain}'. Allowed domains: {', '.join(sorted(ALLOWED_DOMAINS))}"
            )
        if status not in ALLOWED_STATUSES:
            errors.append(
                f"{prefix}: unknown status '{status}'. Allowed statuses: {', '.join(sorted(ALLOWED_STATUSES))}"
            )
        if not isinstance(file_required, bool):
            errors.append(f"{prefix}: file_required must be a boolean.")
        if not isinstance(priority, int):
            errors.append(f"{prefix}: priority must be an integer.")
        if not isinstance(active_for_rules, bool):
            errors.append(f"{prefix}: active_for_rules must be a boolean.")
        if not isinstance(active_for_content, bool):
            errors.append(f"{prefix}: active_for_content must be a boolean.")
        if importer_family is not None and "/" in importer_family:
            warnings.append(f"{source_id}: importer_family should stay a compact identifier.")

        resolved_path = project_root / Path(expected_path)
        exists = resolved_path.exists()
        path_statuses.append(
            SourceRegistryPathStatus(
                source_id=source_id,
                title=title,
                domain=domain,
                role=role,
                status=status,
                expected_path=expected_path,
                resolved_path=resolved_path,
                exists=exists,
                file_required=bool(file_required),
                active_for_rules=bool(active_for_rules),
                active_for_content=bool(active_for_content),
            )
        )

        if exists and resolved_path.is_dir():
            warnings.append(f"{source_id}: expected_path resolves to a directory, not a file: {expected_path}")
        if not exists:
            if status == "active" and bool(file_required):
                errors.append(f"{source_id}: required active source file missing at {expected_path}")
            elif status == "active" and (bool(active_for_rules) or bool(active_for_content)):
                warnings.append(f"{source_id}: active source file not found at {expected_path}")

    return SourceRegistryValidationResult(
        registry_path=registry_path,
        project_root=project_root,
        payload=payload or {"sources": entries},
        entries=entries,
        path_statuses=path_statuses,
        warnings=warnings,
        errors=errors,
    )


def build_source_validation_report(result: SourceRegistryValidationResult) -> str:
    lines = [
        "Source Registry Validation",
        "==========================",
        "",
        f"Registry path: {result.registry_path}",
        f"Project root: {result.project_root}",
        f"Total sources: {result.total_sources}",
        f"Active sources: {result.active_sources}",
        f"Inactive sources: {result.inactive_sources}",
        f"Comparison-only sources: {result.comparison_only_sources}",
        f"Placeholder sources: {result.placeholder_sources}",
        f"Present files: {result.present_files}",
        f"Missing expected files: {result.missing_expected_files}",
        f"Warnings: {len(result.warnings)}",
        f"Errors: {len(result.errors)}",
        "",
        "Sources by domain:",
    ]
    for domain, count in result.counts_by_domain.items():
        lines.append(f"- {domain}: {count}")
    lines.extend(["", "Sources by status:"])
    for status, count in result.counts_by_status.items():
        lines.append(f"- {status}: {count}")

    lines.extend(["", "Present source files:"])
    present = [item for item in result.path_statuses if item.exists]
    if present:
        for item in present:
            lines.append(f"- {item.source_id}: {item.expected_path}")
    else:
        lines.append("- None")

    lines.extend(["", "Missing active sources:"])
    missing_active = [
        item
        for item in result.path_statuses
        if not item.exists and item.status == "active"
    ]
    if missing_active:
        for item in missing_active:
            requirement = "required" if item.file_required else "optional"
            lines.append(f"- {item.source_id} ({requirement}): {item.expected_path}")
    else:
        lines.append("- None")

    lines.extend(["", "Warnings:"])
    if result.warnings:
        lines.extend(f"- {item}" for item in result.warnings)
    else:
        lines.append("- None")

    lines.extend(["", "Errors:"])
    if result.errors:
        lines.extend(f"- {item}" for item in result.errors)
    else:
        lines.append("- None")

    return "\n".join(lines) + "\n"


def _non_empty_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None
