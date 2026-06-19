from __future__ import annotations

import os
import unicodedata
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NAMES_DIR = PROJECT_ROOT / "data" / "names"

# These characters appeared in the damaged source data. Keep ordinary accented
# Unicode (Å, Ä, José, etc.); reject replacement/mojibake and box-drawing text.
SUSPICIOUS_CHARACTERS = frozenset(
    {
        "\ufffd",  # Unicode replacement character
        "Ã",
        "Â",
        "â",
        "ð",
        "├",
        "┬",
    }
)


def is_suspicious_name(name: str) -> bool:
    if any(character in name for character in SUSPICIOUS_CHARACTERS):
        return True
    # Names should not contain control, surrogate, private-use, or unassigned
    # characters. Normal letters, combining marks, spaces, apostrophes, and
    # hyphens remain valid.
    return any(unicodedata.category(character).startswith("C") for character in name)


def scrub_name_file(path: Path) -> tuple[int, int] | None:
    """Remove suspicious lines and atomically replace one cleaned name file."""
    if not path.exists():
        print(f"Missing cleaned name file: {path}")
        return None

    temporary_path = path.with_suffix(path.suffix + ".tmp")
    kept = 0
    removed = 0
    try:
        with path.open("r", encoding="utf-8", errors="ignore") as source:
            with temporary_path.open("w", encoding="utf-8", newline="\n") as destination:
                for line in source:
                    name = line.strip()
                    if not name or is_suspicious_name(name):
                        removed += 1
                        continue
                    destination.write(f"{name}\n")
                    kept += 1
        os.replace(temporary_path, path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()

    print(f"Scrubbed {path}: kept {kept}, removed {removed}")
    return kept, removed


def main() -> None:
    NAMES_DIR.mkdir(parents=True, exist_ok=True)
    scrub_name_file(NAMES_DIR / "first_names.txt")
    scrub_name_file(NAMES_DIR / "last_names.txt")


if __name__ == "__main__":
    main()
