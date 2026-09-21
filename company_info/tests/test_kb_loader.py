"""
test_kb_loader.py — Tests for Knowledge Base Loader & Filters
company_info / tests
"""

import unittest
from company_info.pipeline import get_kb_loader


class TestKBLoader(unittest.TestCase):

    def setUp(self):
        self.kb = get_kb_loader()

    def test_kb_loaded_successfully(self):
        self.assertGreater(self.kb.total_count, 1000, f"KB should load >1000 records, loaded {self.kb.total_count}")

    def test_find_by_name(self):
        # Test exact match
        p1 = self.kb.find_by_name("4POTENTIA")
        self.assertIsNotNone(p1)
        self.assertEqual(p1.company_name, "4POTENTIA")
        self.assertIn("4potentia.com", p1.domain or "")

        # Test fuzzy / case-insensitive match
        p2 = self.kb.find_by_name("Vital Proteins")
        self.assertIsNotNone(p2)
        self.assertTrue("vital" in p2.company_name.lower())

        p3 = self.kb.find_by_name("Gencor")
        self.assertIsNotNone(p3)
        self.assertTrue("gencor" in p3.company_name.lower())

    def test_filter_by_segment(self):
        brands = self.kb.filter_by_segment("supplement_brand")
        self.assertGreater(len(brands), 0)

        suppliers = self.kb.filter_by_segment("ingredient_supplier")
        self.assertGreater(len(suppliers), 0)

        cmos = self.kb.filter_by_segment("contract_manufacturer")
        self.assertGreater(len(cmos), 0)

    def test_top_cohort(self):
        cohort = self.kb.get_top_cohort(limit=25)
        self.assertEqual(len(cohort), 25)
        for c in cohort:
            self.assertIsNotNone(c.company_name)
            self.assertIsNotNone(c.domain)


if __name__ == "__main__":
    unittest.main()
