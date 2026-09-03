import unittest
from unittest.mock import patch

import strict_manager
import strict_search


class StrictSearchTests(unittest.TestCase):
    def test_submit_requires_real_search_button_and_never_uses_enter(self):
        class Field:
            def __init__(self): self.entered = False
            def get_attribute(self, name): return "10121" if name == "value" else ""
            def send_keys(self, *_args): self.entered = True
        field = Field()

        with patch.object(strict_search.legacy, "_ensure_search", return_value=True), \
             patch.object(strict_search.legacy, "_find_input", return_value=field), \
             patch.object(strict_search.legacy, "_replace_input_value", return_value=True), \
             patch.object(strict_search, "_click_search_button", return_value=False):
            self.assertFalse(strict_search.submit_class_code_search(object(), "10121"))
        self.assertFalse(field.entered)

        with patch.object(strict_search.legacy, "_ensure_search", return_value=True), \
             patch.object(strict_search.legacy, "_find_input", return_value=field), \
             patch.object(strict_search.legacy, "_replace_input_value", return_value=True), \
             patch.object(strict_search, "_click_search_button", return_value=True), \
             patch.object(strict_search.time, "sleep"):
            self.assertTrue(strict_search.submit_class_code_search(object(), "10121"))
        self.assertFalse(field.entered)

    def test_result_row_click_recovers_direct_url_from_navigation(self):
        url = "https://syllabus.apu.ac.jp/syllabus/s/a-syllabus/a0ZABC/202610121?language=en_US"
        class Row:
            def is_displayed(self): return True
            def is_enabled(self): return True
        row = Row()
        class Driver:
            current_url = "https://syllabus.apu.ac.jp/syllabus/s/?language=en_US"
            page_source = "<html></html>"
            def execute_script(self, script, *args):
                if "const selector = arguments[0]" in script: return [row]
                if "const el = arguments[0]" in script: return "Class Code 10121 Psychology"
                if "scrollIntoView" in script:
                    self.current_url = url
                    return None
                return None
        with patch.object(strict_search.time, "sleep"):
            self.assertEqual(strict_search.open_result_for_code(Driver(), "10121", 2026), url)

    def test_runtime_manager_search_uses_only_class_code(self):
        mgr = strict_manager.CollectionManager.__new__(strict_manager.CollectionManager)
        mgr.logs = []
        mgr.lock = __import__("threading").RLock()
        mgr.log_file = __import__("pathlib").Path("/nonexistent/collector.log")
        calls = []
        class Driver:
            def get(self, url): calls.append(("get", url))
        def submit(_driver, code): calls.append(("code", code)); return True
        with patch.object(strict_manager, "submit_class_code_search", side_effect=submit), \
             patch.object(strict_manager.CollectionManager, "_collect_wanted", return_value=None), \
             patch.object(strict_manager.time, "sleep"):
            found, method = mgr._search(Driver(), year=2026, code="10725")
        self.assertIsNone(found)
        self.assertEqual(method, "class-code-result-not-found")
        self.assertEqual([call for call in calls if call[0] == "code"], [("code", "10725"), ("code", "10725")])


if __name__ == "__main__":
    unittest.main()
