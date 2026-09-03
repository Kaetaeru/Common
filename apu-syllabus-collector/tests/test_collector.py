import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from openpyxl import Workbook

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import data_source
import mapping
import manager as manager_module
import syllabus_sync


class CollectorTests(unittest.TestCase):
    def test_direct_url_requires_exact_year_and_class(self):
        url = "https://syllabus.apu.ac.jp/syllabus/s/a-syllabus/a0ZQ8000004S4L9MAK/202610121?language=en_US"
        self.assertTrue(mapping.valid_direct_url(url, 2026, "10121"))
        self.assertFalse(mapping.valid_direct_url(url, 2026, "10122"))
        self.assertFalse(mapping.valid_direct_url(url, 2027, "10121"))

    def test_parse_timetable_builds_unique_class_list_and_term(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "2023APM_Curriculum_26Fall.xlsx"
            wb = Workbook(); ws = wb.active
            ws.append(["AY2026 Fall Timetable"])
            ws.append(["Term", "Course code", "Subject Name", "Instructor"])
            ws.append(["Semester", 10121, "Psychology", "Prof A"])
            ws.append(["Semester", 10121, "Psychology", "Prof A"])
            ws.append(["1Q", 10009, "A World History of Interaction", "Prof B"])
            wb.save(path)
            data = data_source.parse_timetable(path, "APM")
            self.assertEqual(data["term"], "AY2026 Fall")
            self.assertEqual({c["classCode"] for c in data["classes"]}, {"10121", "10009"})

    def test_load_mapping_drops_invalid_or_mismatched_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "links.json"
            output.write_text(json.dumps({
                "2026:10121": "https://syllabus.apu.ac.jp/syllabus/s/a-syllabus/a0ZABC/202610121?language=en_US",
                "2026:99999": "https://example.com/not-apu",
                "bad": "https://syllabus.apu.ac.jp/syllabus/s/a-syllabus/a0ZABC/202610121",
            }), encoding="utf-8")
            self.assertEqual(list(mapping.load_mapping(output)), ["2026:10121"])

    def test_search_uses_subject_only_after_two_class_code_attempts(self):
        with tempfile.TemporaryDirectory() as tmp:
            mgr = manager_module.CollectionManager(Path(tmp))
            calls = []
            class Driver:
                def get(self, url): calls.append(("get", url))
            url = "https://syllabus.apu.ac.jp/syllabus/s/a-syllabus/a0ZABC/202610121?language=en_US"
            def submit(_driver, value, mode): calls.append((mode, value)); return True
            def page_links(_driver, wanted, year):
                if calls[-1] == ("subject", "Psychology"):
                    return {"2026:10121": url}
                return {}
            with patch.object(manager_module, "_submit_search", side_effect=submit), patch.object(manager_module, "_page_links", side_effect=page_links), patch.object(manager_module, "_click_text", return_value=False), patch.object(manager_module.time, "sleep"):
                found, method = mgr._search(Driver(), year=2026, code="10121", subject="Psychology")
            self.assertEqual(found, url)
            self.assertEqual(method, "subject-fallback")
            self.assertEqual([c for c in calls if c[0] in {"code", "subject"}], [("code", "10121"), ("code", "10121"), ("subject", "Psychology")])

    def test_manager_status_marks_mapped_failed_and_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / "data").mkdir()
            mapping.save_mapping(root / "data/syllabus_links.json", {"2026:10121": "https://syllabus.apu.ac.jp/syllabus/s/a-syllabus/a0ZABC/202610121?language=en_US"})
            mgr = manager_module.CollectionManager(root)
            mgr.dataset = {
                "college": "APM", "academicYear": 2026, "term": "AY2026 Fall",
                "classes": [
                    {"classCode": "10121", "name": "Psychology", "instructor": "", "term": "Semester"},
                    {"classCode": "10009", "name": "World", "instructor": "", "term": "Semester"},
                    {"classCode": "10010", "name": "Other", "instructor": "", "term": "Semester"},
                ],
            }
            mgr.failed = {"2026:10009": "not-found"}
            status = mgr.status("APM")
            states = {row["classCode"]: row["status"] for row in status["rows"]}
            self.assertEqual(states, {"10121": "mapped", "10009": "failed", "10010": "pending"})
            self.assertEqual(status["mapped"], 1); self.assertEqual(status["failed"], 1)

    def test_shadow_dom_input_is_considered_for_class_code_search(self):
        class Element:
            def __init__(self): self.attrs = {"type": "text"}
            def is_displayed(self): return True
            def is_enabled(self): return True
            def get_attribute(self, name): return self.attrs.get(name, "")
        element = Element()
        class Driver:
            def execute_script(self, script, *args):
                if "const selector = arguments[0]" in script: return [element] if str(args[0]).startswith("input") else []
                if "const start = arguments[0]" in script: return "Class Code"
                return None
        self.assertIs(syllabus_sync._find_input(Driver(), "code"), element)

    def test_shadow_dom_direct_link_is_collected(self):
        url = "https://syllabus.apu.ac.jp/syllabus/s/a-syllabus/a0ZQ8000004S4L9MAK/202610121?language=en_US"
        class Anchor:
            def get_attribute(self, name): return url if name == "href" else ""
        anchor = Anchor()
        class Driver:
            page_source = "<html></html>"
            def execute_script(self, script, *args):
                if "const selector = arguments[0]" in script and str(args[0]).startswith("a[href"): return [anchor]
                return []
        found = syllabus_sync._page_links(Driver(), {"10121"}, 2026)
        self.assertEqual(found["2026:10121"], url)

    def test_replace_input_value_verifies_new_class_code(self):
        class Element:
            def __init__(self): self.attrs = {"value": "A World History of Interaction"}
            def click(self): pass
            def get_attribute(self, name): return self.attrs.get(name, "")
        element = Element()
        class Driver:
            def execute_script(self, script, *args):
                if "Object.getOwnPropertyDescriptor" in script: args[0].attrs["value"] = args[1]
        self.assertTrue(syllabus_sync._replace_input_value(Driver(), element, "10009"))
        self.assertEqual(element.get_attribute("value"), "10009")


if __name__ == "__main__": unittest.main()
