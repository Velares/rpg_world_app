from __future__ import annotations

import json
import warnings
from collections import defaultdict
from pathlib import Path
from typing import Any

from tools.importers.monster_catalog_import import normalize_monster_name
from tools.importers.monster_manual_schema import (
    DEFAULT_ADD_BESTIARY_PACK_DIR,
    DEFAULT_MONSTER_CATALOG_JSON,
)

DEFAULT_IMPORTED_MONSTER_PACKS_ROOT = DEFAULT_ADD_BESTIARY_PACK_DIR.parents[0]


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_core_monster_records(
    catalog_path: Path = DEFAULT_MONSTER_CATALOG_JSON,
) -> list[dict[str, Any]]:
    if not catalog_path.exists():
        return []
    payload = _load_json(catalog_path)
    monsters = payload.get("monsters", [])
    return [monster for monster in monsters if isinstance(monster, dict)]


def load_imported_monster_records(
    content_packs_root: Path = DEFAULT_IMPORTED_MONSTER_PACKS_ROOT,
) -> list[dict[str, Any]]:
    if not content_packs_root.exists():
        return []
    records: list[dict[str, Any]] = []
    for pack_dir in sorted(path for path in content_packs_root.iterdir() if path.is_dir()):
        pack_json = pack_dir / "pack.json"
        monsters_json = pack_dir / "monsters.json"
        if not pack_json.exists() or not monsters_json.exists():
            continue
        try:
            pack = _load_json(pack_json)
        except (OSError, json.JSONDecodeError) as exc:
            warnings.warn(f"Skipping imported monster pack at {pack_dir}: could not read pack.json ({exc}).")
            continue
        if not isinstance(pack, dict) or not pack.get("enabled", True):
            continue
        try:
            payload = _load_json(monsters_json)
        except (OSError, json.JSONDecodeError) as exc:
            warnings.warn(f"Skipping imported monster pack at {pack_dir}: could not read monsters.json ({exc}).")
            continue
        monsters = payload.get("monsters", []) if isinstance(payload, dict) else payload
        if not isinstance(monsters, list):
            warnings.warn(
                f"Skipping imported monster pack at {pack_dir}: monsters.json must contain a list or a top-level 'monsters' list."
            )
            continue
        for monster in monsters:
            if not isinstance(monster, dict):
                continue
            monster = dict(monster)
            monster.setdefault("source_pack", pack.get("id", pack_dir.name))
            source = monster.get("source")
            if isinstance(source, dict):
                source.setdefault("name", pack.get("source_title") or pack.get("name", pack_dir.name))
                source.setdefault("type", "content_pack")
                source.setdefault("source_id", pack.get("source_id", ""))
            else:
                monster["source"] = {
                    "name": pack.get("source_title") or pack.get("name", pack_dir.name),
                    "type": "content_pack",
                    "source_id": pack.get("source_id", ""),
                }
            monster.setdefault("source_id", pack.get("source_id", ""))
            monster.setdefault("source_title", pack.get("source_title") or pack.get("name", pack_dir.name))
            records.append(monster)
    return records


def load_monster_catalog(
    *,
    catalog_path: Path = DEFAULT_MONSTER_CATALOG_JSON,
    content_packs_root: Path = DEFAULT_IMPORTED_MONSTER_PACKS_ROOT,
    include_imported: bool = False,
) -> list[dict[str, Any]]:
    monsters = load_core_monster_records(catalog_path)
    if include_imported:
        monsters += load_imported_monster_records(content_packs_root)
    return monsters


def load_all_monster_records(
    *,
    catalog_path: Path = DEFAULT_MONSTER_CATALOG_JSON,
    content_packs_root: Path = DEFAULT_IMPORTED_MONSTER_PACKS_ROOT,
    include_imported: bool = False,
) -> list[dict[str, Any]]:
    return load_monster_catalog(
        catalog_path=catalog_path,
        content_packs_root=content_packs_root,
        include_imported=include_imported,
    )


def sort_monsters_by_name(monsters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        monsters,
        key=lambda monster: (
            normalize_monster_name(str(monster.get("name") or monster.get("sort_name") or "")),
            str(monster.get("source_pack") or monster.get("id") or ""),
        ),
    )


def get_monsters_sorted_by_name(
    *,
    catalog_path: Path = DEFAULT_MONSTER_CATALOG_JSON,
    content_packs_root: Path = DEFAULT_IMPORTED_MONSTER_PACKS_ROOT,
    include_imported: bool = False,
) -> list[dict[str, Any]]:
    return sort_monsters_by_name(
        load_monster_catalog(
            catalog_path=catalog_path,
            content_packs_root=content_packs_root,
            include_imported=include_imported,
        )
    )


def find_same_name_different_source_records(
    monsters: list[dict[str, Any]],
) -> list[str]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for monster in monsters:
        normalized_name = normalize_monster_name(
            str(monster.get("name") or monster.get("sort_name") or "")
        )
        if normalized_name:
            grouped[normalized_name].append(monster)

    warnings: list[str] = []
    for entries in grouped.values():
        if len(entries) < 2:
            continue
        source_packs = {
            str(entry.get("source_pack") or entry.get("source", {}).get("file") or entry.get("id"))
            for entry in entries
        }
        if len(source_packs) < 2:
            continue
        display_name = str(entries[0].get("name") or entries[0].get("sort_name") or "")
        warnings.append(
            f"{display_name}: same display name appears in multiple sources ({', '.join(sorted(source_packs))})"
        )
    return sorted(warnings)
