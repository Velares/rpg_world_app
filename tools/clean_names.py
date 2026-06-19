from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
NAMES_DIR = PROJECT_ROOT / "data" / "names"


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


def main() -> None:
    NAMES_DIR.mkdir(parents=True, exist_ok=True)
    clean_name_file(
        NAMES_DIR / "raw_first_names.txt",
        NAMES_DIR / "first_names.txt",
    )
    clean_name_file(
        NAMES_DIR / "raw_last_names.txt",
        NAMES_DIR / "last_names.txt",
    )


if __name__ == "__main__":
    main()
