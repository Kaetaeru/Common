import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import app
import syllabus_collector
from syllabus_mapping import load_verified_mapping, parse_direct_syllabus_url, scan_mapping_sources


PSYCHOLOGY = "https://syllabus.apu.ac.jp/syllabus/s/a-syllabus/a0ZQ8000004S4L9MAK/202610121?language=en_US"
OTHER = "https://syllabus.apu.ac.jp/syllabus/s/a-syllabus/a0ZQ8000004S4QvMAK/202611330?language=en_US"


class SyllabusMappingTests(unittest.TestCase):
    def write_json(self, path: Path, payload):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def test_direct_url_parser_extracts_year_and_class_code(self):
        self.assertEqual(parse_direct_syllabus_url(PSYCHOLOGY), (2026, "10121"))
        self.assertIsNone(parse_direct_syllabus_url("https://example.com/202610121"))

    def test_legacy_and_batch_files_merge(self):
        with tempfile.TemporaryDirectory() as td:
            data_dir = Path(td)
            self.write_json(data_dir / "syllabus_links.json", {"2026:10121": PSYCHOLOGY})
            self.write_json(data_dir / "syllabus-links/2026-fall/batch-001.json", {"2026:11330": OTHER})
            report = scan_mapping_sources(data_dir)
            self.assertEqual(report["mapping"], {"2026:10121": PSYCHOLOGY, "2026:11330": OTHER})
            self.assertEqual(len(report["sources"]), 2)
            self.assertFalse(report["problems"])
            self.assertFalse(report["conflicts"])

    def test_same_key_same_url_is_safe_duplicate(self):
        with tempfile.TemporaryDirectory() as td:
            data_dir = Path(td)
            self.write_json(data_dir / "syllabus_links.json", {"2026:10121": PSYCHOLOGY})
            self.write_json(data_dir / "syllabus-links/2026-fall/batch-001.json", {"2026:10121": PSYCHOLOGY})
            report = scan_mapping_sources(data_dir)
            self.assertEqual(report["mapping"]["2026:10121"], PSYCHOLOGY)
            self.assertEqual(report["duplicateCount"], 1)

    def test_conflicting_urls_are_excluded_instead_of_silently_overridden(self):
        with tempfile.TemporaryDirectory() as td:
            data_dir = Path(td)
            bad_other = "https://syllabus.apu.ac.jp/syllabus/s/a-syllabus/DIFFERENT/202610121?language=en_US"
            self.write_json(data_dir / "syllabus_links.json", {"2026:10121": PSYCHOLOGY})
            self.write_json(data_dir / "syllabus-links/2026-fall/batch-001.json", {"2026:10121": bad_other})
            report = scan_mapping_sources(data_dir)
            self.assertNotIn("2026:10121", report["mapping"])
            self.assertEqual(len(report["conflicts"]), 1)

    def test_invalid_key_url_pair_is_reported(self):
        with tempfile.TemporaryDirectory() as td:
            data_dir = Path(td)
            self.write_json(data_dir / "syllabus-links/2026-fall/batch-001.json", {"2026:99999": PSYCHOLOGY})
            report = scan_mapping_sources(data_dir)
            self.assertFalse(report["mapping"])
            self.assertEqual(len(report["problems"]), 1)

    def test_mapping_change_rebuilds_cached_normalized_data_when_sources_exist(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            data_dir = root / "data"
            data_dir.mkdir()
            batch = data_dir / "syllabus-links/2026-fall/batch-001.json"
            self.write_json(batch, {"2026:10121": PSYCHOLOGY})
            cached = root / "APM.json"
            cached.write_text(json.dumps({"schemaVersion": 2, "syllabusMappingFingerprint": "old"}), encoding="utf-8")
            timetable = root / "timetable.xlsx"
            subjects = root / "subjects.xlsx"
            timetable.write_bytes(b"source")
            subjects.write_bytes(b"source")

            def fake_loader(college, allow_download=True):
                self.assertFalse(cached.exists(), "stale normalized cache should be removed before rebuild")
                return {"schemaVersion": 2, "sections": [], "subjects": []}

            with patch.object(app._backend, "DATA_DIR", data_dir), \
                 patch.object(app._backend, "normalized_path", return_value=cached), \
                 patch.object(app._backend, "source_paths", return_value=(timetable, subjects)), \
                 patch.object(app, "_original_load_or_build_data", side_effect=fake_loader):
                result = app.load_or_build_data("APM", allow_download=False)

            self.assertTrue(result["syllabusMappingCacheVerified"])
            self.assertNotEqual(result["syllabusMappingFingerprint"], "old")
            self.assertTrue(cached.exists())

    def test_schedule_app_uses_the_same_repository_reader(self):
        with tempfile.TemporaryDirectory() as td:
            data_dir = Path(td)
            self.write_json(data_dir / "syllabus-links/2026-fall/batch-001.json", {"2026:10121": PSYCHOLOGY})
            with patch.object(app._backend, "DATA_DIR", data_dir):
                self.assertEqual(app.load_syllabus_link_overrides(), {"2026:10121": PSYCHOLOGY})


class CollectorRegressionTests(unittest.TestCase):
    def test_plain_direct_url_input_becomes_mapping_pair(self):
        pairs, errors = syllabus_collector._parse_input_pairs(PSYCHOLOGY)
        self.assertFalse(errors)
        self.assertEqual(pairs, [("2026:10121", PSYCHOLOGY)])

    def test_collector_status_proves_mapping_is_attached_to_app_data(self):
        with tempfile.TemporaryDirectory() as td:
            data_dir = Path(td)
            (data_dir / "syllabus-links/2026-fall").mkdir(parents=True)
            (data_dir / "syllabus-links/2026-fall/batch-001.json").write_text(
                json.dumps({"2026:10121": PSYCHOLOGY}), encoding="utf-8"
            )
            fake_data = {
                "term": "AY2026 Fall",
                "academicYear": 2026,
                "academicSeason": "FALL",
                "sections": [{
                    "classCode": "10121",
                    "name": "Psychology",
                    "instructor": "Prof P",
                    "term": "SEMESTER",
                    "syllabusUrl": PSYCHOLOGY,
                }],
            }
            with patch.object(syllabus_collector, "DATA_DIR", data_dir), patch.object(
                syllabus_collector, "_dataset", return_value=fake_data
            ):
                status = syllabus_collector.collector_status("APM")
            self.assertTrue(status["readerVerified"])
            self.assertEqual(status["readerExpected"], 1)
            self.assertEqual(status["readerAttached"], 1)


if __name__ == "__main__":
    unittest.main()
