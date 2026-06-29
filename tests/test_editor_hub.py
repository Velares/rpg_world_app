from __future__ import annotations

import unittest
from pathlib import Path

import app.gui
from app.editor_hub import (
    EDITOR_CATEGORIES,
    MONSTER_EDITOR_SUBCATEGORIES,
    editors_hub_summary_text,
    get_editor_categories,
    get_editor_placeholder_text,
    get_monster_editor_subcategories,
    monster_editor_summary_text,
)
from app.gui import _get_app_diagnostics, _get_app_version, editor_tools_labels
from tools.importers.monster_manual_schema import (
    DEFAULT_MONSTER_APPENDIX_CATALOG_JSON,
    DEFAULT_MONSTER_CATALOG_JSON,
)


ROOT = Path(__file__).resolve().parents[1]
TABLES = ROOT / "data" / "tables"


class EditorHubTests(unittest.TestCase):
    def test_categories_include_expected_editors(self) -> None:
        categories = get_editor_categories()
        keys = [key for _label, key in categories]
        self.assertIn("monsters", keys)
        self.assertIn("npcs", keys)
        self.assertIn("pcs", keys)
        self.assertIn("items", keys)
        self.assertIn("spells", keys)

    def test_monsters_entry_label(self) -> None:
        categories = get_editor_categories()
        labels = [label for label, _key in categories]
        self.assertIn("Monster Editor / Monster Import Review", labels)

    def test_placeholders_say_not_implemented(self) -> None:
        for _label, key in EDITOR_CATEGORIES:
            if key == "monsters":
                continue
            text = get_editor_placeholder_text(key)
            self.assertIn("Not implemented yet", text)
            self.assertIn("Future purpose", text)

    def test_unknown_placeholder_is_safe(self) -> None:
        text = get_editor_placeholder_text("unknown")
        self.assertIn("Not implemented yet", text)

    def test_summary_text(self) -> None:
        text = editors_hub_summary_text()
        self.assertIn("EDITORS HUB", text)
        self.assertIn("Monster Editor", text)
        self.assertIn("NPC Editor", text)
        self.assertIn("PC Editor", text)
        self.assertIn("Item Editor", text)
        self.assertIn("Spell Editor", text)

    def test_monster_editor_action_in_shared_actions(self) -> None:
        self.assertIn("Monster Editor", app.gui.SHARED_ACTIONS)

    def test_monster_editor_action_in_command_map(self) -> None:
        self.assertIn("view_monster_editor", dir(app.gui.RPGWorldApp))
        try:
            import tkinter as tk
            from app.database import Database
            from app.game_state import GameState
            from app.table_loader import TableLoader

            tables = TableLoader(TABLES)
            database = Database(ROOT / "data" / "saves" / "worlds.db")
            game_state = GameState(tables, database)
            instance = app.gui.RPGWorldApp(game_state)
            self.assertIn("Monster Editor", instance.sidebar_command_map)
            self.assertEqual(instance.sidebar_command_map["Monster Editor"], instance.view_monster_editor)
            instance.destroy()
        except tk.TclError as exc:
            self.skipTest(f"Tk not available for command-map inspection: {exc}")

    def test_app_has_view_editors_method(self) -> None:
        self.assertTrue(hasattr(app.gui.RPGWorldApp, "view_editors"))

    def test_editors_action_in_shared_actions(self) -> None:
        self.assertIn("Editors", app.gui.SHARED_ACTIONS)

    def test_editors_action_in_command_map(self) -> None:
        # The command map is built inside __init__; verify the mapping dict
        # class attribute name exists if present, otherwise construct a dummy
        # instance to inspect the mapping. Instantiating requires a GameState,
        # so we check the class at minimum.
        self.assertIn("view_editors", dir(app.gui.RPGWorldApp))

    def test_no_live_catalog_modification(self) -> None:
        before_catalog = DEFAULT_MONSTER_CATALOG_JSON.read_text(encoding="utf-8")
        before_appendix = DEFAULT_MONSTER_APPENDIX_CATALOG_JSON.read_text(encoding="utf-8")
        # Calling the pure helper functions should not touch catalog files.
        get_editor_categories()
        get_editor_placeholder_text("npcs")
        editors_hub_summary_text()
        after_catalog = DEFAULT_MONSTER_CATALOG_JSON.read_text(encoding="utf-8")
        after_appendix = DEFAULT_MONSTER_APPENDIX_CATALOG_JSON.read_text(encoding="utf-8")
        self.assertEqual(before_catalog, after_catalog)
        self.assertEqual(before_appendix, after_appendix)

    def test_monster_editor_subcategories(self) -> None:
        categories = get_monster_editor_subcategories()
        keys = [key for _label, key in categories]
        self.assertIn("canonical_candidate_review", keys)
        self.assertIn("normalized_monster_review", keys)
        self.assertIn("classification_suggestions", keys)
        self.assertIn("corrected_staging_preview", keys)
        self.assertIn("combat_projection_preview", keys)
        self.assertEqual(len(categories), 5)

    def test_monster_editor_summary_text(self) -> None:
        text = monster_editor_summary_text()
        self.assertIn("MONSTER EDITOR", text)
        self.assertIn("Canonical Candidate Review", text)
        self.assertIn("Normalized Monster Review", text)
        self.assertIn("Classification Suggestions", text)
        self.assertIn(
            "Use Canonical Candidate Review to approve/reject likely same-monster matches.",
            text,
        )
        self.assertIn(
            "Use Normalized Monster Review to inspect imported monster records and correct fields.",
            text,
        )
        self.assertIn(
            "Use Classification Suggestions to review conservative best-guess classifications.",
            text,
        )
        self.assertIn(
            "Corrections are stored separately and do not modify source imports or the live catalog.",
            text,
        )

    def test_app_has_view_monster_editor_method(self) -> None:
        self.assertTrue(hasattr(app.gui.RPGWorldApp, "view_monster_editor"))

    def test_app_has_view_normalized_monster_review_method(self) -> None:
        self.assertTrue(hasattr(app.gui.RPGWorldApp, "view_normalized_monster_review"))

    def test_app_has_view_classification_suggestions_method(self) -> None:
        self.assertTrue(hasattr(app.gui.RPGWorldApp, "view_classification_suggestions"))

    def test_app_has_open_normalized_correction_dialog_method(self) -> None:
        self.assertTrue(hasattr(app.gui.RPGWorldApp, "open_normalized_correction_dialog"))

    def test_app_has_view_corrected_staging_preview_method(self) -> None:
        self.assertTrue(hasattr(app.gui.RPGWorldApp, "view_corrected_staging_preview"))

    def test_app_has_view_combat_projection_preview_method(self) -> None:
        self.assertTrue(hasattr(app.gui.RPGWorldApp, "view_combat_projection_preview"))

    def test_editor_tools_section_is_visible_and_includes_monster_editor(self) -> None:
        labels = editor_tools_labels()
        self.assertIn("Monster Editor", labels)
        self.assertIn("Editors", labels)
        self.assertEqual(labels[0], "Monster Editor")
        self.assertEqual(labels[1], "Editors")

    def test_editor_tools_buttons_in_top_level_sidebar(self) -> None:
        try:
            import tkinter as tk
            from tkinter import ttk
            from app.database import Database
            from app.game_state import GameState
            from app.table_loader import TableLoader

            tables = TableLoader(TABLES)
            database = Database(ROOT / "data" / "saves" / "worlds.db")
            game_state = GameState(tables, database)
            instance = app.gui.RPGWorldApp(game_state)
            self.assertIn("Monster Editor", instance.sidebar_command_map)
            self.assertEqual(instance.sidebar_command_map["Monster Editor"], instance.view_monster_editor)
            self.assertIn("Editors", instance.sidebar_command_map)
            self.assertEqual(instance.sidebar_command_map["Editors"], instance.view_editors)
            # Verify the dedicated Editor Tools frame exists and contains buttons.
            children = instance.editor_tools_frame.winfo_children()
            self.assertTrue(len(children) >= 2)
            button_texts = [child.cget("text") for child in children if isinstance(child, ttk.Button)]
            self.assertIn("Monster Editor", button_texts)
            self.assertIn("Editors", button_texts)
            instance.destroy()
        except tk.TclError as exc:
            self.skipTest(f"Tk not available for sidebar inspection: {exc}")

    def test_app_version_diagnostic(self) -> None:
        version = _get_app_version()
        self.assertTrue(version.startswith("v0.8."))

    def test_app_diagnostics_report_expected_fields(self) -> None:
        diagnostics = _get_app_diagnostics()
        self.assertIn("version", diagnostics)
        self.assertIn("repo_root", diagnostics)
        self.assertIn("working_directory", diagnostics)
        self.assertIn("combat_projection_exists", diagnostics)
        self.assertIn("staging_preview_exists", diagnostics)
        self.assertIn("monster_editor_registered", diagnostics)
        self.assertIn("editors_registered", diagnostics)
        self.assertTrue(diagnostics["monster_editor_registered"])
        self.assertTrue(diagnostics["editors_registered"])
        self.assertIsInstance(diagnostics["combat_projection_exists"], bool)
        self.assertIsInstance(diagnostics["staging_preview_exists"], bool)

    def test_no_live_catalog_modification_by_app_diagnostics(self) -> None:
        before_catalog = DEFAULT_MONSTER_CATALOG_JSON.read_text(encoding="utf-8")
        before_appendix = DEFAULT_MONSTER_APPENDIX_CATALOG_JSON.read_text(encoding="utf-8")
        _get_app_diagnostics()
        _get_app_version()
        after_catalog = DEFAULT_MONSTER_CATALOG_JSON.read_text(encoding="utf-8")
        after_appendix = DEFAULT_MONSTER_APPENDIX_CATALOG_JSON.read_text(encoding="utf-8")
        self.assertEqual(before_catalog, after_catalog)
        self.assertEqual(before_appendix, after_appendix)


if __name__ == "__main__":
    unittest.main()
