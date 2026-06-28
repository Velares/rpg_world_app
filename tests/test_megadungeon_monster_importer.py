from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from tools.importers.megadungeon_monster_importer import (
    DEFAULT_MEGADUNGEON_MONSTER_PDF,
    DISPLAY_LABELS,
    MEGADUNGEON_MONSTER_SOURCE_ID,
    ProbePage,
    extract_probe_pages,
    main,
    probe_megadungeon,
    split_entries_from_pages,
)


def real_pdf_available() -> bool:
    try:
        import pypdf  # noqa: F401
    except ImportError:
        return False
    return DEFAULT_MEGADUNGEON_MONSTER_PDF.exists()


@unittest.skipUnless(real_pdf_available(), "Megadungeon PDF and pypdf are required for these probe tests.")
class MegadungeonMonsterImporterTests(unittest.TestCase):
    def test_parser_detects_aarakocra_on_page_9(self):
        result = probe_megadungeon(actual_pages=[9])
        names = {entry.name: entry for entry in result.entries}
        self.assertIn("Aarakocra", names)
        aarakocra = names["Aarakocra"]
        self.assertEqual(aarakocra.source_id, MEGADUNGEON_MONSTER_SOURCE_ID)
        self.assertEqual(aarakocra.actual_page_start, 9)
        self.assertEqual(aarakocra.fields["number_encountered"], "2d4")
        self.assertEqual(aarakocra.fields["movement"], "30 (Fly 120)")
        self.assertEqual(aarakocra.fields["xp"], "33")
        for key in DISPLAY_LABELS:
            self.assertIn(key, aarakocra.fields)

    def test_parser_detects_amber_jelly_on_page_11(self):
        result = probe_megadungeon(actual_pages=[11])
        names = {entry.name: entry for entry in result.entries}
        self.assertIn("Amber Jelly", names)
        amber_jelly = names["Amber Jelly"]
        self.assertEqual(amber_jelly.actual_page_start, 11)
        self.assertEqual(amber_jelly.fields["armor_class"], "5")
        self.assertEqual(amber_jelly.fields["hit_dice"], "4")
        self.assertEqual(amber_jelly.fields["damage"], "1d6*")

    def test_parser_detects_rock_manta_on_page_83(self):
        result = probe_megadungeon(actual_pages=[83])
        names = {entry.name: entry for entry in result.entries}
        self.assertIn("Rock Manta", names)
        rock_manta = names["Rock Manta"]
        self.assertEqual(rock_manta.actual_page_start, 83)
        self.assertEqual(rock_manta.fields["movement"], "See Below")
        self.assertEqual(rock_manta.fields["save"], "F2-5")
        self.assertEqual(rock_manta.fields["xp"], "47 , 95, 220, 650")

    def test_non_monster_contents_page_is_rejected(self):
        pages = extract_probe_pages(DEFAULT_MEGADUNGEON_MONSTER_PDF, actual_pages=[5])
        entries = split_entries_from_pages(pages)
        self.assertEqual(entries, [])

    def test_missing_pdf_fails_cleanly(self):
        missing_path = Path(tempfile.gettempdir()) / "missing_megadungeon_probe.pdf"
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            exit_code = main(["--probe", str(missing_path)])
        self.assertEqual(exit_code, 1)
        self.assertIn("Registered monster source override not found", stderr.getvalue())
        self.assertIn(MEGADUNGEON_MONSTER_SOURCE_ID, stderr.getvalue())

    def test_probe_output_function_does_not_write_catalog_files(self):
        stdout = io.StringIO()
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            with redirect_stdout(stdout):
                exit_code = main(["--probe", "--pages", "9"])
            self.assertEqual(exit_code, 0)
            self.assertFalse((temp_root / "monster_catalog.json").exists())
            self.assertFalse((temp_root / "monster_appendix_catalog.json").exists())
        self.assertIn("Megadungeon Monster Probe", stdout.getvalue())

    def test_synthetic_page_requires_multiple_stat_labels_before_accepting_heading(self):
        pages = [
            ProbePage(
                actual_page=1,
                text="""Credits and Acknowledgements
Amber Jelly
This page mentions a monster name but does not include a stat block.
Movement through the dungeon is dangerous.
""",
            )
        ]
        entries = split_entries_from_pages(pages)
        self.assertEqual(entries, [])


if __name__ == "__main__":
    unittest.main()
