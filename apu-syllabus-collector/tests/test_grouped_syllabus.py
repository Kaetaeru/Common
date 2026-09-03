import json
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import mapping
import strict_search


GROUP_URL = "https://syllabus.apu.ac.jp/syllabus/s/a-syllabus/a0ZQ8000005G8q3MAC/202612347"
GROUP_TEXT = "12347:Undergraduate Project in AF (Accounting and Finance)(74) §12348:Undergraduate Thesis(74) §12349:Undergraduate Thesis AF (Accounting and Finance)"


class GroupedSyllabusTests(unittest.TestCase):
    def test_grouped_anchor_accepts_target_with_canonical_url(self):
        class Anchor:
            def is_displayed(self): return True
            def get_attribute(self, name): return GROUP_URL if name == "href" else ""

        anchor = Anchor()

        class Driver:
            def execute_script(self, script, *args):
                if "const selector = arguments[0]" in script:
                    return [anchor]
                if "const el = arguments[0]" in script:
                    return GROUP_TEXT
                return None

        found = strict_search.grouped_anchor_url(Driver(), "12349", 2026)
        self.assertEqual(str(found), GROUP_URL)
        self.assertEqual(found.group_codes, ("12347", "12348", "12349"))
        self.assertTrue(mapping.valid_direct_url(found, 2026, "12349"))

    def test_grouped_anchor_rejects_unlisted_target(self):
        class Anchor:
            def is_displayed(self): return True
            def get_attribute(self, name): return GROUP_URL if name == "href" else ""

        anchor = Anchor()

        class Driver:
            def execute_script(self, script, *args):
                if "const selector = arguments[0]" in script:
                    return [anchor]
                if "const el = arguments[0]" in script:
                    return GROUP_TEXT
                return None

        self.assertIsNone(strict_search.grouped_anchor_url(Driver(), "12350", 2026))

    def test_save_and_reload_preserve_verified_group_alias(self):
        grouped = strict_search.SearchURL(GROUP_URL, ("12347", "12348", "12349"))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "syllabus_links.json"
            mapping.save_mapping(path, {"2026:12349": grouped})
            raw = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(raw["2026:12347"], GROUP_URL)
            self.assertEqual(raw["2026:12349"], GROUP_URL)
            loaded = mapping.load_mapping(path)
            self.assertEqual(loaded["2026:12347"], GROUP_URL)
            self.assertEqual(loaded["2026:12349"], GROUP_URL)

    def test_reload_rejects_mismatch_without_canonical_companion(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "syllabus_links.json"
            path.write_text(json.dumps({"2026:12349": GROUP_URL}), encoding="utf-8")
            self.assertEqual(mapping.load_mapping(path), {})


if __name__ == "__main__":
    unittest.main()
