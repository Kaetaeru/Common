import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import mapping
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
        mgr.lock = threading.RLock()
        mgr.log_file = Path("/nonexistent/collector.log")
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

    def test_worker_count_is_configurable_but_bounded(self):
        self.assertEqual(strict_manager.CollectionManager._normalize_worker_count(1), 1)
        self.assertEqual(strict_manager.CollectionManager._normalize_worker_count("10"), 10)
        with self.assertRaises(ValueError):
            strict_manager.CollectionManager._normalize_worker_count(0)
        with self.assertRaises(ValueError):
            strict_manager.CollectionManager._normalize_worker_count(11)

    def test_partitioned_run_uses_configured_browsers_and_fixed_unique_parts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manager = strict_manager.CollectionManager(root)
            manager.worker_count = 4
            classes = [
                {"classCode": str(11000 + i), "name": f"Course {i}", "instructor": "", "term": "Semester"}
                for i in range(12)
            ]
            data = {"college": "APM", "academicYear": 2026, "term": "AY2026 Fall", "classes": classes}
            drivers = []
            seen = []
            seen_lock = threading.Lock()

            class Driver:
                def quit(self): pass

            def open_browser(worker_id, *, headless=False, restarted=False):
                driver = Driver()
                drivers.append((worker_id, driver))
                return driver

            def ensure_dataset(_college, refresh=False):
                manager.dataset = data
                manager.college = "APM"
                return data

            def search(_driver, *, year, code, worker=""):
                with seen_lock:
                    seen.append((worker, code))
                return f"https://syllabus.apu.ac.jp/syllabus/s/a-syllabus/a0ZABC/{year}{code}?language=en_US", "class-code"

            manager.running = True
            with patch.object(manager, "ensure_dataset", side_effect=ensure_dataset), \
                 patch.object(manager, "_open_browser", side_effect=open_browser), \
                 patch.object(manager, "_search", side_effect=search), \
                 patch.object(strict_manager.time, "sleep"):
                manager._run(college="APM", headless=False, refresh_data=False, retry_failed_only=False)

            self.assertEqual(len(drivers), 4)
            by_worker = {}
            for worker, code in seen:
                by_worker.setdefault(worker, []).append(code)
            self.assertEqual(by_worker["W01"], ["11000", "11001", "11002"])
            self.assertEqual(by_worker["W02"], ["11003", "11004", "11005"])
            self.assertEqual(by_worker["W03"], ["11006", "11007", "11008"])
            self.assertEqual(by_worker["W04"], ["11009", "11010", "11011"])
            self.assertEqual(len({code for _, code in seen}), len(classes))
            self.assertEqual(len(mapping.load_mapping(root / "data" / "syllabus_links.json")), len(classes))
            self.assertFalse(manager.running)
            self.assertEqual(manager.active_workers, {})

    def test_worker_restarts_browser_and_retries_same_class_after_session_crash(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manager = strict_manager.CollectionManager(root)
            item = {"classCode": "10121", "name": "Psychology", "instructor": "", "term": "Semester"}
            url = "https://syllabus.apu.ac.jp/syllabus/s/a-syllabus/a0ZABC/202610121?language=en_US"

            class Driver:
                def __init__(self): self.quit_calls = 0
                def quit(self): self.quit_calls += 1

            first = Driver()
            second = Driver()
            mapping_state = {}
            with patch.object(manager, "_open_browser", side_effect=[first, second]) as open_browser, \
                 patch.object(manager, "_search", side_effect=[RuntimeError("browser died"), (url, "class-code")]), \
                 patch.object(strict_manager.time, "sleep"):
                manager._browser_worker(
                    1,
                    [(1, item)],
                    queue_total=1,
                    year=2026,
                    mapping=mapping_state,
                    headless=False,
                )

            self.assertEqual(open_browser.call_count, 2)
            self.assertGreaterEqual(first.quit_calls, 1)
            self.assertGreaterEqual(second.quit_calls, 1)
            self.assertEqual(mapping.load_mapping(root / "data" / "syllabus_links.json")["2026:10121"], url)
            self.assertNotIn("2026:10121", manager.failed)


if __name__ == "__main__":
    unittest.main()
