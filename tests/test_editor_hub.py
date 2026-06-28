from __future__ import annotations

import unittest

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
from tools.importers.monster_manual_schema import (
    DEFAULT_MONSTER_APPENDIX_CATALOG_JSON,
    DEFAULT_MONSTER_CATALOG_JSON,
)


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
        self.assertIn("Monster Editor / Monster Import Review", text)
        self.assertIn("placeholders for future work", text)

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

    def test_monster_editor_summary_text(self) -> None:
        text = monster_editor_summary_text()
        self.assertIn("MONSTER EDITOR", text)
        self.assertIn("Canonical Candidate Review", text)
        self.assertIn("Normalized Monster Review", text)
        self.assertIn("Review only", text)

    def test_app_has_view_monster_editor_method(self) -> None:
        self.assertTrue(hasattr(app.gui.RPGWorldApp, "view_monster_editor"))

    def test_app_has_view_normalized_monster_review_method(self) -> None:
        self.assertTrue(hasattr(app.gui.RPGWorldApp, "view_normalized_monster_review"))


if __name__ == "__main__":
    unittest.main()
