"""
test_extractors.py — Unit Tests for Precision Extractors & Cleaners
company_info / tests
"""

import unittest
from company_info.extractors import (
    clean_person_name,
    extract_person_name_from_headline,
    clean_role_title,
    extract_role_from_text,
    parse_funding_amount,
    classify_round_type,
    extract_investors,
    classify_person_movement,
    classify_strategic_movement,
)
from company_info.models import MovementType, FundingRoundType, MovementCategory


class TestExtractors(unittest.TestCase):

    def test_clean_person_name_valid(self):
        self.assertEqual(clean_person_name("Tim Condron"), "Tim Condron")
        self.assertEqual(clean_person_name("Dr. Luigi Cappello Ph.D."), "Luigi Cappello")
        self.assertEqual(clean_person_name("Kat Schneider, MBA"), "Kat Schneider")
        self.assertEqual(clean_person_name("Ozan Pamir - CFO"), "Ozan Pamir")

    def test_clean_person_name_blacklist_and_noise(self):
        # Brand and company names must be rejected
        self.assertIsNone(clean_person_name("Msi Express"))
        self.assertIsNone(clean_person_name("Nutri Advanced"))
        self.assertIsNone(clean_person_name("Standard Process"))
        self.assertIsNone(clean_person_name("Campden Bri"))
        self.assertIsNone(clean_person_name("Simple Eats"))
        # Sentence fragments must be rejected
        self.assertIsNone(clean_person_name("Appointed New CEO"))
        self.assertIsNone(clean_person_name("Leading The Industry"))
        self.assertIsNone(clean_person_name("Steps Down Today"))
        # Target company overlap rejection
        self.assertIsNone(clean_person_name("Thorne Health", target_company="Thorne HealthTech"))

    def test_extract_person_name_from_headline(self):
        h1 = "Vitaquest International Appoints Tim Condron as Chief Executive Officer"
        self.assertEqual(extract_person_name_from_headline(h1, "Vitaquest"), "Tim Condron")

        h2 = "ChromaDex Appoints Ozan Pamir as Chief Financial Officer"
        self.assertEqual(extract_person_name_from_headline(h2, "ChromaDex"), "Ozan Pamir")

        h3 = "David Schwendimann Appointed as Chief Executive Officer at Lief Labs"
        self.assertEqual(extract_person_name_from_headline(h3, "Lief Labs"), "David Schwendimann")

    def test_clean_role_title(self):
        self.assertEqual(clean_role_title("chief executive officer"), "Chief Executive Officer (CEO)")
        self.assertEqual(clean_role_title("vp of research and development"), "Vice President of Research and Development")
        self.assertEqual(clean_role_title("Chief Commercial Officer on a day to create"), "Chief Commercial Officer (CCO)")
        self.assertEqual(clean_role_title("Director of Quality Assurance | 1099 Remote"), "Director of Quality Assurance")
        # Invalid fragments without role words
        self.assertIsNone(clean_role_title("on a day to create something new"))

    def test_extract_role_from_text(self):
        r1 = extract_role_from_text("ADM appoints Jeff Rowe as Executive Vice President and Chief Operating Officer - Capitol City Now", "Jeff Rowe")
        self.assertEqual(r1, "Executive Vice President and Chief Operating Officer (COO)")

        r2 = extract_role_from_text("Vitaquest Names Tim Condron as Chief Executive Officer", "Tim Condron")
        self.assertEqual(r2, "Chief Executive Officer (CEO)")

        r3 = extract_role_from_text("David Schwendimann Appointed as Chief Executive Officer at Lief Labs", "David Schwendimann")
        self.assertEqual(r3, "Chief Executive Officer (CEO)")

    def test_parse_funding_amount(self):
        raw, amt = parse_funding_amount("Company raised $25 million in Series B financing")
        self.assertEqual(raw, "$25M")
        self.assertEqual(amt, 25_000_000.0)

        raw2, amt2 = parse_funding_amount("Secured $1.5B valuation in latest growth equity round")
        self.assertEqual(raw2, "$1.5B")
        self.assertEqual(amt2, 1_500_000_000.0)

        raw3, amt3 = parse_funding_amount("Closed €10M seed round")
        self.assertEqual(raw3, "€10M")
        self.assertEqual(amt3, 10_800_000.0)

    def test_classify_movements(self):
        # Role movements
        self.assertEqual(classify_person_movement("Appointed new VP of Regulatory Affairs"), MovementType.JOINED)
        self.assertEqual(classify_person_movement("Steps down after 5 years as CEO"), MovementType.DEPARTED)
        self.assertEqual(classify_person_movement("Promoted to Senior Director of Formulation"), MovementType.PROMOTED)
        self.assertEqual(classify_person_movement("Elected to the Board of Directors"), MovementType.BOARD_APPOINTMENT)

        # Strategic movements
        self.assertEqual(classify_strategic_movement("Acquired powder processing facility from Ashland"), MovementCategory.MERGER_ACQUISITION)
        self.assertEqual(classify_strategic_movement("Expands manufacturing capacity with new 100,000 sq ft plant"), MovementCategory.FACILITY_EXPANSION)
        self.assertEqual(classify_strategic_movement("Announces strategic distribution partnership with Gencor"), MovementCategory.STRATEGIC_PARTNERSHIP)
        self.assertEqual(classify_strategic_movement("Launches clinically validated brain health ingredient"), MovementCategory.PRODUCT_LAUNCH)


if __name__ == "__main__":
    unittest.main()
