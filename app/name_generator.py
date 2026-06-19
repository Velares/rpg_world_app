from __future__ import annotations

import random
from pathlib import Path
from typing import Iterable


class NameDataError(RuntimeError):
    """Raised when a requested name type has no file data or fallback data."""


class NameGenerator:
    """Cached newline-delimited name loader for large plain-text datasets."""

    def __init__(
        self,
        names_dir: Path,
        rng: random.Random | None = None,
        fallback_first_names: Iterable[str] = (),
        fallback_last_names: Iterable[str] = (),
    ):
        self.names_dir = Path(names_dir)
        self.rng = rng or random.Random()
        self._fallback_first_names = tuple(
            str(name).strip() for name in fallback_first_names if str(name).strip()
        )
        self._fallback_last_names = tuple(
            str(name).strip() for name in fallback_last_names if str(name).strip()
        )
        # Files are loaded once per generator instance, not on each name request.
        self._first_names = self._load_names(
            self.names_dir / "first_names.txt",
            self._fallback_first_names,
        )
        self._last_names = self._load_names(
            self.names_dir / "last_names.txt",
            self._fallback_last_names,
        )

    @staticmethod
    def _load_names(path: Path, fallback: tuple[str, ...]) -> tuple[str, ...]:
        if path.exists():
            with path.open("r", encoding="utf-8", errors="ignore") as source:
                names = tuple(line.strip() for line in source if line.strip())
            if names:
                return names
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
