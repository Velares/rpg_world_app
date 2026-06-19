from __future__ import annotations

import random
from pathlib import Path
from typing import Iterable


class NameDataError(RuntimeError):
    """Raised when a requested name type has no file data or fallback data."""


class NameGenerator:
    """Cached newline-delimited name loader for large plain-text datasets."""

    # A process-wide cache avoids parsing and allocating the same very large
    # local files again when GameState or tests create another generator.
    _file_cache: dict[Path, tuple[tuple[int, int], tuple[str, ...]]] = {}

    def __init__(
        self,
        names_dir: Path,
        rng: random.Random | None = None,
        fallback_first_names: Iterable[str] = (),
        fallback_last_names: Iterable[str] = (),
    ):
        self.names_dir = Path(names_dir)
        self.rng = rng or random.Random()
        self.warnings: list[str] = []
        self._fallback_first_names = tuple(
            str(name).strip() for name in fallback_first_names if str(name).strip()
        )
        self._fallback_last_names = tuple(
            str(name).strip() for name in fallback_last_names if str(name).strip()
        )
        # Large files are read once per generator instance, never per generated
        # name. Tuples keep the cached collection compact and immutable.
        self._first_names = self._load_names(
            self.names_dir / "first_names.txt",
            self._fallback_first_names,
            "first",
        )
        self._last_names = self._load_names(
            self.names_dir / "last_names.txt",
            self._fallback_last_names,
            "last",
        )

    def _load_names(
        self, path: Path, fallback: tuple[str, ...], label: str
    ) -> tuple[str, ...]:
        try:
            if path.exists():
                resolved = path.resolve()
                stat = path.stat()
                signature = (stat.st_mtime_ns, stat.st_size)
                cached = self._file_cache.get(resolved)
                if cached and cached[0] == signature:
                    return cached[1]
                names = []
                with path.open("r", encoding="utf-8", errors="ignore") as source:
                    for line in source:
                        name = line.strip()
                        if name:
                            names.append(name)
                if names:
                    loaded = tuple(names)
                    self._file_cache[resolved] = (signature, loaded)
                    return loaded
                self.warnings.append(f"Cleaned {label}-name file is empty: {path}")
            else:
                self.warnings.append(f"Cleaned {label}-name file is missing: {path}")
        except OSError as exc:
            self.warnings.append(f"Could not read {label}-name file {path}: {exc}")
        return fallback

    def _choose(self, names: tuple[str, ...], label: str) -> str:
        if not names:
            raise NameDataError(
                f"No {label} names are available. Run tools/clean_names.py or "
                f"provide fallback {label} names."
            )
        return self.rng.choice(names)

    def first_name(self) -> str:
        return self._choose(self._first_names, "first")

    def last_name(self) -> str:
        return self._choose(self._last_names, "last")

    def full_name(self) -> str:
        return f"{self.first_name()} {self.last_name()}"

    def full_names(self, count: int) -> list[str]:
        if count < 0:
            raise ValueError("Name count cannot be negative.")
        return [self.full_name() for _ in range(count)]

    def source_summary(self) -> str:
        """Return a concise diagnostic suitable for a GUI or support report."""
        return (
            f"First names available: {len(self._first_names):,}\n"
            f"Last names available: {len(self._last_names):,}"
        )
