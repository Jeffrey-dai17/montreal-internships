import unittest
from copy import deepcopy

import update


class ListingTests(unittest.TestCase):
    def setUp(self):
        self.job = {
            "terms": ["Summer 2027"], "active": True, "is_visible": True,
            "locations": ["Montréal, QC, Canada", "Toronto, ON, Canada"],
            "url": "https://example.com/jobs/1", "date_posted": 1793700000,
            "company_name": "Example | Company", "title": "Engineering Intern",
            "category": "Software Engineering",
        }

    def test_valid_multicity_listing_and_markdown_escape(self):
        result = update.render([self.job])
        self.assertIn("**1 open listings**", result)
        self.assertIn("Example &#124; Company", result)
        self.assertIn("[Apply](https://example.com/jobs/1)", result)

    def test_closed_hidden_wrong_term_and_other_city_are_excluded(self):
        cases = [
            {"active": False}, {"is_visible": False},
            {"terms": ["Summer 2026"]}, {"locations": ["Vancouver, BC"]},
            {"url": "javascript:alert(1)"},
        ]
        for changes in cases:
            with self.subTest(changes=changes):
                excluded = deepcopy(self.job)
                excluded.update(changes)
                excluded["title"] = "Excluded Role"
                self.assertNotIn("Excluded Role", update.render([self.job, excluded]))

    def test_duplicate_application_urls_collapse(self):
        self.assertIn("**1 open listings**", update.render([self.job, self.job]))

    def test_empty_or_broken_feed_fails(self):
        for feed in [[], {}, [{}], [dict(self.job, locations="Toronto")],
                     [dict(self.job, active="false")]]:
            with self.subTest(feed=feed), self.assertRaises(ValueError):
                update.render(feed)

    def test_valid_feed_with_no_local_matches_clears_list(self):
        self.job["locations"] = ["Vancouver, BC"]
        self.assertIn("**0 open listings**", update.render([self.job]))


if __name__ == "__main__":
    unittest.main()
