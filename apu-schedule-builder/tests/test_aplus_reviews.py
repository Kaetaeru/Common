import unittest
from unittest.mock import patch

import aplus_reviews


SUBJECTS = {
    "data": [
        {"subjectCode": "027019", "name": "Psychology", "id": 110},
    ]
}
COURSES = {
    "data": [
        {
            "instructorId": 343,
            "subjectId": 110,
            "description": "Course section taught by Fumihiko YOKOTA.",
            "reviews": [
                {"id": 198, "rating": 3, "isRecommended": True},
                {"id": 200, "rating": 5, "isRecommended": True},
                {"id": 558, "rating": 5, "isRecommended": True},
            ],
            "id": 433,
        },
        {
            "instructorId": 260,
            "subjectId": 110,
            "description": "Course section taught by Tomoko SAITO.",
            "reviews": [],
            "id": 432,
        },
    ]
}


class AplusReviewTests(unittest.TestCase):
    def test_psychology_yokota_rating_matches_api_data(self):
        index = aplus_reviews.build_review_index(SUBJECTS, COURSES)
        review = index[("027019", aplus_reviews.instructor_signature("YOKOTA Fumihiko"))]
        self.assertEqual(review["courseId"], 433)
        self.assertEqual(review["rating"], 4.3)
        self.assertEqual(review["reviewCount"], 3)
        self.assertEqual(review["recommendPercent"], 100)
        self.assertEqual(review["sourceUrl"], "https://apluscoursereview.com/subject/110")

    def test_name_order_is_normalized_but_different_instructor_is_not_matched(self):
        index = aplus_reviews.build_review_index(SUBJECTS, COURSES)
        yokota = ("027019", aplus_reviews.instructor_signature("YOKOTA Fumihiko"))
        other = ("027019", aplus_reviews.instructor_signature("YOKOTA Hanako"))
        self.assertIn(yokota, index)
        self.assertNotIn(other, index)

    def test_enrichment_updates_top_level_and_nested_sections(self):
        index = aplus_reviews.build_review_index(SUBJECTS, COURSES)
        data = {
            "sections": [{"classCode": "10121", "subjectCode": "027019", "instructor": "YOKOTA Fumihiko"}],
            "subjects": [{"sections": [{"classCode": "10121", "subjectCode": "027019", "instructor": "YOKOTA Fumihiko"}]}],
        }
        snapshot = {"available": True, "index": index, "subjectCount": 1, "courseCount": 2}
        with patch.object(aplus_reviews, "get_review_snapshot", return_value=snapshot):
            result = aplus_reviews.enrich_schedule_data(data)
        for section in [result["sections"][0], result["subjects"][0]["sections"][0]]:
            self.assertEqual(section["aplusReview"]["rating"], 4.3)
            self.assertEqual(section["aplusReview"]["reviewCount"], 3)
        self.assertEqual(result["aplusReviewStatus"]["matchedSections"], 1)

    def test_api_failure_leaves_schedule_usable(self):
        data = {"sections": [{"classCode": "10121", "subjectCode": "027019", "instructor": "YOKOTA Fumihiko"}], "subjects": []}
        with patch.object(aplus_reviews, "get_review_snapshot", return_value={"available": False, "index": {}}):
            result = aplus_reviews.enrich_schedule_data(data)
        self.assertNotIn("aplusReview", result["sections"][0])
        self.assertFalse(result["aplusReviewStatus"]["available"])

    def test_duplicate_review_ids_are_not_double_counted(self):
        courses = {"data": [COURSES["data"][0], {**COURSES["data"][0], "id": 999}]}
        index = aplus_reviews.build_review_index(SUBJECTS, courses)
        review = index[("027019", aplus_reviews.instructor_signature("YOKOTA Fumihiko"))]
        self.assertEqual(review["reviewCount"], 3)


if __name__ == "__main__":
    unittest.main()
