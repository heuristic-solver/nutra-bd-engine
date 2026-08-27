"""
run_pipeline.py — Unified BD Propensity Scanner CLI

Usage:
    python run_pipeline.py --company "Herbalife"
    python run_pipeline.py --company "OmniActive Health Technologies" --linkedin "https://www.linkedin.com/company/omniactive-health-technologies"
"""

import argparse
import json
import warnings
warnings.filterwarnings("ignore")

from bd_engine.collectors.serper_collector import SerperCollector
from bd_engine.collectors.openfda_collector import OpenFDACollector
from bd_engine.collectors.apify_collector import ApifyCollector
from bd_engine.bd_scorer import PropensityScorer


def run_360_scan(company_name: str, linkedin_url: str = None, prev_headcount: int = None):
    print("\n" + "=" * 80)
    print(f"  360° BD PROPENSITY INTELLIGENCE SCAN: {company_name}")
    print("=" * 80)

    # 1. openFDA Collector
    fda = OpenFDACollector()
    fda_data = fda.analyze_company(company_name, lookback_years=3)

    # 2. Serper 6-Month Market Signals
    serper = SerperCollector()
    serper_data = serper.analyze_company(company_name)

    # 3. Apify LinkedIn Collector
    apify = ApifyCollector()
    apify_data = apify.analyze_company(
        company_name=company_name,
        linkedin_url=linkedin_url,
        previous_headcount=prev_headcount,
    )

    # 4. Master Propensity Scorer
    scorer = PropensityScorer()
    scorecard = scorer.score_company(
        company_name=company_name,
        apify_data=apify_data,
        serper_data=serper_data,
        openfda_data=fda_data,
    )

    # Display Master BD Scorecard
    print("\n" + "=" * 80)
    print(f"  🏆 MASTER BD PROPENSITY SCORECARD")
    print("=" * 80)
    print(f"  Company Name          : {scorecard['company_name']}")
    print(f"  Propensity Score      : {scorecard['propensity_score']} / 100")
    print(f"  Outreach Priority Tier: [{scorecard['tier']}]")
    print(f"  Urgency Label         : {scorecard['urgency_label']}")
    print(f"  Primary Talking Point : {scorecard['primary_talking_point']}")

    print("\n  ► SCORE BREAKDOWN (By Dimension):")
    b = scorecard["score_breakdown"]
    print(f"    1. Headcount Growth  : {b['headcount_growth']['score']:>4.1f} / {b['headcount_growth']['max_points']:.0f} pts | {b['headcount_growth']['details'].get('detail', '')}")
    print(f"    2. Plant Expansions  : {b['facility_expansions']['score']:>4.1f} / {b['facility_expansions']['max_points']:.0f} pts | {b['facility_expansions']['details'].get('detail', '')}")
    print(f"    3. Exec Turnover     : {b['executive_turnover']['score']:>4.1f} / {b['executive_turnover']['max_points']:.0f} pts | {b['executive_turnover']['details'].get('detail', '')}")
    print(f"    4. Regulatory Risk   : {b['regulatory_pressure']['score']:>4.1f} / {b['regulatory_pressure']['max_points']:.0f} pts | Recalls: {b['regulatory_pressure']['details'].get('total_recalls', 0)}")
    print(f"    5. Domain Alignment  : {b['domain_alignment']['score']:>4.1f} / {b['domain_alignment']['max_points']:.0f} pts | Nutra Sector Fit")

    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Run 360° BD Signal Intelligence & Propensity Scorecard")
    parser.add_argument("--company", type=str, required=True, help="Target company name")
    parser.add_argument("--linkedin", type=str, default=None, help="Company LinkedIn URL")
    parser.add_argument("--prev_headcount", type=int, default=None, help="Previous headcount baseline")
    args = parser.parse_args()

    run_360_scan(args.company, args.linkedin, args.prev_headcount)


if __name__ == "__main__":
    main()
