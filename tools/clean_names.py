from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NAMES_DIR = PROJECT_ROOT / "data" / "names"
RAW_FIRST_NAME_CANDIDATES = ("firstnames.txt", "raw_first_names.txt")
RAW_LAST_NAME_CANDIDATES = ("surnames.txt", "raw_last_names.txt")


def clean_name_file(input_path: Path, output_path: Path) -> int | None:
    """Clean one newline-delimited name file without keeping duplicates."""
    if not input_path.exists():
        print(f"Missing raw input file: {input_path}")
        return None

    names: set[str] = set()
    with input_path.open("r", encoding="utf-8", errors="ignore") as source:
        for line in source:
            clean_name = line.strip().title()
            if clean_name:
                names.add(clean_name)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "".join(f"{name}\n" for name in sorted(names)),
        encoding="utf-8",
    )
    print(f"Saved {len(names)} names to {output_path}")
    return len(names)


def find_raw_name_file(names_dir: Path, candidates: tuple[str, ...]) -> Path:
    """Prefer the first existing supported source filename."""
    for filename in candidates:
        path = names_dir / filename
        if path.exists():
            return path
    return names_dir / candidates[0]


def main() -> None:
    NAMES_DIR.mkdir(parents=True, exist_ok=True)
    clean_name_file(
        find_raw_name_file(NAMES_DIR, RAW_FIRST_NAME_CANDIDATES),
        NAMES_DIR / "first_names.txt",
    )
    clean_name_file(
        find_raw_name_file(NAMES_DIR, RAW_LAST_NAME_CANDIDATES),
        NAMES_DIR / "last_names.txt",
    )


if __name__ == "__main__":
    main()
