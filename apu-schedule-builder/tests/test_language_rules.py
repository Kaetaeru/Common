import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from language_rules import annotate_schedule_data, classify_language_course, filter_candidate_subjects, language_eligibility_reason


class LanguageRuleTests(unittest.TestCase):
    def test_classifies_japanese_core_ladder_in_order(self):
        expected = [
            ("Foundation Japanese I", 1),
            ("Foundation Japanese II", 2),
            ("Foundation Japanese Ⅲ", 3),
            ("Intermediate Japanese", 4),
            ("Pre-Advanced Japanese", 5),
            ("Advanced Japanese", 6),
        ]
        for name, rank in expected:
            with self.subTest(name=name):
                self.assertEqual(classify_language_course(name)[:2], ("JA", rank))

    def test_classifies_english_core_ladder(self):
        expected = {
            "Elementary English A": 1,
            "Pre-Intermediate English B": 2,
            "Intermediate English A": 3,
            "Upper-Intermediate English B": 4,
            "Advanced English 1A": 5,
            "Advanced English 2B": 6,
        }
        for name, rank in expected.items():
            with self.subTest(name=name):
                self.assertEqual(classify_language_course(name)[:2], ("EN", rank))

    def test_specialized_electives_are_not_core_levels(self):
        for name in ["Career Japanese", "English for Business Writing", "TESOL", "Japanese Communication Skills"]:
            with self.subTest(name=name):
                self.assertIsNone(classify_language_course(name))

    def test_annotation_reaches_subject_and_top_level_section(self):
        data = {
            "subjects": [{"subjectCode": "J1", "name": "Foundation Japanese II", "sections": [{"classCode": "10001", "subjectCode": "J1", "name": "Foundation Japanese II"}]}],
            "sections": [{"classCode": "10001", "subjectCode": "J1", "name": "Foundation Japanese II"}],
        }
        annotate_schedule_data(data)
        self.assertEqual(data["subjects"][0]["languageLevelRank"], 2)
        self.assertEqual(data["sections"][0]["languageCore"], "JA")

    def subject(self, core, rank, label):
        return {"subjectCode": label, "name": label, "languageCore": core, "languageLevelRank": rank, "languageLevelLabel": label, "sections": []}

    def test_basis_and_completed_level_filters(self):
        english = self.subject("EN", 3, "Intermediate English")
        japanese2 = self.subject("JA", 2, "Foundation Japanese II")
        japanese3 = self.subject("JA", 3, "Foundation Japanese III")
        self.assertTrue(language_eligibility_reason(english, {"track": "E"}))
        self.assertTrue(language_eligibility_reason(self.subject("JA", 4, "Intermediate Japanese"), {"track": "JST"}))
        self.assertTrue(language_eligibility_reason(japanese2, {"track": "E", "languageLevel": 2}))
        self.assertFalse(language_eligibility_reason(japanese3, {"track": "E", "languageLevel": 2}))

    def test_jat_starts_above_standard_english_levels(self):
        self.assertTrue(language_eligibility_reason(self.subject("EN", 4, "Upper-Intermediate English"), {"track": "JAT", "languageLevel": 0}))
        self.assertFalse(language_eligibility_reason(self.subject("EN", 5, "Advanced English 1"), {"track": "JAT", "languageLevel": 0}))

    def test_filter_keeps_top_level_sections_for_fixed_university_classes(self):
        subject = self.subject("EN", 2, "Pre-Intermediate English")
        data = {"subjects": [subject], "sections": [{"classCode": "12345", "subjectCode": subject["subjectCode"]}]}
        filtered = filter_candidate_subjects(data, {"track": "E"})
        self.assertEqual(filtered["subjects"], [])
        self.assertEqual(filtered["sections"], data["sections"])


if __name__ == "__main__":
    unittest.main()
