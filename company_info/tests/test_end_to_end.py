"""
test_end_to_end.py — End-to-End Integration Tests for Company Intelligence Pipeline
company_info / tests
"""

import os
import unittest
from company_info.models import CompanyProfile, MovementType
from company_info.pipeline import CompanyIntelligenceEngine, get_kb_loader
from company_info.exporters import CSVExporter, JSONExporter, MarkdownReporter


class TestEndToEndPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.engine = CompanyIntelligenceEngine(max_workers=3)
        cls.kb = get_kb_loader()
        cls.output_dir = "test_output_company_info"
        os.makedirs(cls.output_dir, exist_ok=True)

    def test_single_company_scan(self):
        # Scan a prominent nutraceutical company: ChromaDex / Niagen Bioscience
        profile = CompanyProfile(
            company_name="ChromaDex",
            domain="niagenbioscience.com",
            headquarters="Los Angeles, CA",
            specialty="NAD+ / Niagen / Branded Ingredients",
        )

        report = self.engine.scan_company(profile)

        self.assertIsNotNone(report)
        self.assertEqual(report.company_name, "ChromaDex")
        self.assertGreaterEqual(report.total_signals_discovered, 0)

        print(f"\n[Test Result] ChromaDex Scan:")
        print(f"  • Total Signals: {report.total_signals_discovered}")
        print(f"  • Role Changes: {len(report.role_changes)}")
        print(f"  • Funding Events: {len(report.funding_events)}")
        print(f"  • Strategic Movements: {len(report.strategic_movements)}")
        print(f"  • Scraped Sources: {', '.join(report.data_sources_scraped)}")

    def test_batch_scan_and_exports(self):
        # Scan a 3-company cohort
        cohort = [
            CompanyProfile(company_name="Vitaquest International", domain="vitaquest.com", specialty="Contract Manufacturing"),
            CompanyProfile(company_name="Gencor Pacific", domain="gencorpacific.com", specialty="Branded Botanical Extracts"),
            CompanyProfile(company_name="Lief Labs", domain="lieflabs.com", specialty="Contract Manufacturing & Formulation"),
        ]

        reports = self.engine.scan_batch(cohort)
        self.assertEqual(len(reports), 3)

        # Verify all exports
        master_csv = os.path.join(self.output_dir, "master_summary.csv")
        roles_csv = os.path.join(self.output_dir, "roles_events.csv")
        funding_csv = os.path.join(self.output_dir, "funding_events.csv")
        movements_csv = os.path.join(self.output_dir, "movements_events.csv")
        brief_md = os.path.join(self.output_dir, "briefings.md")
        data_json = os.path.join(self.output_dir, "intelligence.json")

        CSVExporter.export_master_summary(reports, master_csv)
        CSVExporter.export_role_changes(reports, roles_csv)
        CSVExporter.export_funding_events(reports, funding_csv)
        CSVExporter.export_strategic_movements(reports, movements_csv)
        MarkdownReporter.export(reports, brief_md)
        JSONExporter.export(reports, data_json)

        self.assertTrue(os.path.exists(master_csv))
        self.assertTrue(os.path.exists(roles_csv))
        self.assertTrue(os.path.exists(funding_csv))
        self.assertTrue(os.path.exists(movements_csv))
        self.assertTrue(os.path.exists(brief_md))
        self.assertTrue(os.path.exists(data_json))

        # Check non-empty files
        self.assertGreater(os.path.getsize(master_csv), 50)
        self.assertGreater(os.path.getsize(brief_md), 100)


if __name__ == "__main__":
    unittest.main()
