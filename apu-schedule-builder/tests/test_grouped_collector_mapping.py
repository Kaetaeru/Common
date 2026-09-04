import json
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from syllabus_mapping import scan_mapping_sources


GROUP_URL = "https://syllabus.apu.ac.jp/syllabus/s/a-syllabus/a0ZQ8000005G8q3MAC/202612347"


class GroupedCollectorMappingTests(unittest.TestCase):
    def test_collector_alias_is_accepted_with_matching_canonical_entry(self):
        with tempfile.TemporaryDirectory() as td:
            common = Path(td)
            data_dir = common / "apu-schedule-builder" / "data"
            data_dir.mkdir(parents=True)
            collector = common / "apu-syllabus-collector" / "data" / "syllabus_links.json"
            collector.parent.mkdir(parents=True)
            collector.write_text(json.dumps({
                "2026:12347": GROUP_URL,
                "2026:12349": GROUP_URL,
            }), encoding="utf-8")

            report = scan_mapping_sources(data_dir)
            self.assertEqual(report["mapping"]["2026:12347"], GROUP_URL)
            self.assertEqual(report["mapping"]["2026:12349"], GROUP_URL)
            self.assertFalse(report["problems"])

    def test_manual_batch_mismatch_remains_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            data_dir = Path(td)
            batch = data_dir / "syllabus-links" / "2026-fall" / "batch.json"
            batch.parent.mkdir(parents=True)
            batch.write_text(json.dumps({
                "2026:12347": GROUP_URL,
                "2026:12349": GROUP_URL,
            }), encoding="utf-8")

            report = scan_mapping_sources(data_dir)
            self.assertEqual(report["mapping"], {"2026:12347": GROUP_URL})
            self.assertEqual(len(report["problems"]), 1)
            self.assertEqual(report["problems"][0]["key"], "2026:12349")


if __name__ == "__main__":
    unittest.main()
