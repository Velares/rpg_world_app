from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from tools.importers.megadungeon_monster_importer import (
    DEFAULT_MEGADUNGEON_MONSTER_PDF,
    DEFAULT_PREVIEW_OUTPUT_PATH,
    DEFAULT_PREVIEW_REPORT_PATH,
    DISPLAY_LABELS,
    MEGADUNGEON_MONSTER_SOURCE_ID,
    ProbePage,
    extract_probe_pages,
    generate_dry_run_preview,
    main,
    probe_megadungeon,
    split_entries_from_pages,
)
from tools.importers.monster_manual_schema import (
    DEFAULT_MONSTER_APPENDIX_CATALOG_JSON,
    DEFAULT_MONSTER_CATALOG_JSON,
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
        entries, _, _ = split_entries_from_pages(pages)
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

    def test_dry_run_preview_writes_separate_preview_outputs(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            preview_path = temp_root / "megadungeon_preview.json"
            report_path = temp_root / "megadungeon_preview_report.txt"
            result = generate_dry_run_preview(
                actual_pages=[9, 11, 83],
                preview_output_path=preview_path,
                preview_report_path=report_path,
            )
            self.assertTrue(preview_path.exists())
            self.assertTrue(report_path.exists())
            self.assertNotEqual(preview_path.resolve(), DEFAULT_MONSTER_CATALOG_JSON.resolve())
            self.assertNotEqual(report_path.resolve(), DEFAULT_MONSTER_APPENDIX_CATALOG_JSON.resolve())
            payload = json.loads(preview_path.read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(payload), 2)
            self.assertEqual(result.preview_path, preview_path)
            self.assertEqual(result.report_path, report_path)

    def test_aarakocra_appears_in_preview_with_expected_fields(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            result = generate_dry_run_preview(
                actual_pages=[9],
                preview_output_path=temp_root / "preview.json",
                preview_report_path=temp_root / "preview_report.txt",
            )
            by_name = {record["name"]: record for record in result.preview_records}
            self.assertIn("Aarakocra", by_name)
            aarakocra = by_name["Aarakocra"]
            self.assertEqual(aarakocra["source_id"], MEGADUNGEON_MONSTER_SOURCE_ID)
            self.assertEqual(aarakocra["actual_page_start"], 9)
            self.assertEqual(aarakocra["actual_page_end"], 9)
            self.assertEqual(aarakocra["no_enc"], "2d4")
            self.assertEqual(aarakocra["movement"], "30 (Fly 120)")
            self.assertEqual(aarakocra["status"], "parsed")

    def test_rock_manta_preview_preserves_multiple_xp_values(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            result = generate_dry_run_preview(
                actual_pages=[83],
                preview_output_path=temp_root / "preview.json",
                preview_report_path=temp_root / "preview_report.txt",
            )
            by_name = {record["name"]: record for record in result.preview_records}
            self.assertIn("Rock Manta", by_name)
            rock_manta = by_name["Rock Manta"]
            self.assertEqual(rock_manta["source_title"], "Megadungeon Monster Manual")
            self.assertEqual(rock_manta["actual_page_start"], 83)
            self.assertEqual(rock_manta["actual_page_end"], 83)
            self.assertEqual(rock_manta["xp"], "47 , 95, 220, 650")
            self.assertEqual(rock_manta["status"], "parsed")

    def test_dry_run_preview_does_not_modify_live_catalog_files(self):
        before_catalog = DEFAULT_MONSTER_CATALOG_JSON.read_text(encoding="utf-8")
        before_appendix = DEFAULT_MONSTER_APPENDIX_CATALOG_JSON.read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            generate_dry_run_preview(
                actual_pages=[9, 11, 83],
                preview_output_path=temp_root / "preview.json",
                preview_report_path=temp_root / "preview_report.txt",
            )
        after_catalog = DEFAULT_MONSTER_CATALOG_JSON.read_text(encoding="utf-8")
        after_appendix = DEFAULT_MONSTER_APPENDIX_CATALOG_JSON.read_text(encoding="utf-8")
        self.assertEqual(before_catalog, after_catalog)
        self.assertEqual(before_appendix, after_appendix)

    def test_preview_output_path_defaults_are_separate_from_live_catalog_paths(self):
        self.assertNotEqual(DEFAULT_PREVIEW_OUTPUT_PATH.resolve(), DEFAULT_MONSTER_CATALOG_JSON.resolve())
        self.assertNotEqual(DEFAULT_PREVIEW_REPORT_PATH.resolve(), DEFAULT_MONSTER_APPENDIX_CATALOG_JSON.resolve())

    def test_preview_records_include_metadata_and_page_numbers(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            result = generate_dry_run_preview(
                actual_pages=[9, 11],
                preview_output_path=temp_root / "preview.json",
                preview_report_path=temp_root / "preview_report.txt",
            )
            record = result.preview_records[0]
            self.assertIn("source_id", record)
            self.assertIn("source_title", record)
            self.assertIn("slug", record)
            self.assertIn("actual_page_start", record)
            self.assertIn("actual_page_end", record)
            self.assertIn("raw_stat_block", record)
            self.assertIn("raw_text_excerpt", record)
            self.assertIn("status", record)
            self.assertIn("confidence", record)

    def test_brobdingnagian_fungi_is_parsed_with_treasure_type_alias(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            result = generate_dry_run_preview(
                actual_pages=[21],
                preview_output_path=temp_root / "preview.json",
                preview_report_path=temp_root / "preview_report.txt",
            )
            by_name = {record["name"]: record for record in result.preview_records}
            self.assertIn("Brobdingnagian Fungi", by_name)
            record = by_name["Brobdingnagian Fungi"]
            self.assertEqual(record["treasure"], "See below")
            self.assertEqual(record["xp"], "38, 110, 145, 650")
            self.assertEqual(record["status"], "parsed")

    def test_cerepod_is_parsed_with_parenthetical_attack_continuation(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            result = generate_dry_run_preview(
                actual_pages=[25],
                preview_output_path=temp_root / "preview.json",
                preview_report_path=temp_root / "preview_report.txt",
            )
            by_name = {record["name"]: record for record in result.preview_records}
            self.assertIn("Cerepod", by_name)
            record = by_name["Cerepod"]
            self.assertEqual(record["attacks"], "11 (10 tentacles & beak)")
            self.assertEqual(record["damage"], "See below")
            self.assertEqual(record["save"], "F6")
            self.assertEqual(record["morale"], "10")
            self.assertEqual(record["treasure"], "W (Lair)")
            self.assertEqual(record["xp"], "1,250")
            self.assertEqual(record["status"], "parsed")

    def test_full_preview_counts_are_tracked(self):
        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            result = generate_dry_run_preview(
                preview_output_path=temp_root / "preview.json",
                preview_report_path=temp_root / "preview_report.txt",
            )
            self.assertEqual(result.detected_entries, 253)
            self.assertGreaterEqual(result.parsed_entries, 251)
            self.assertLessEqual(result.partial_entries, 2)
            self.assertGreaterEqual(result.rejected_headings, 1)

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
        entries, _, _ = split_entries_from_pages(pages)
        self.assertEqual(entries, [])


if __name__ == "__main__":
    unittest.main()
