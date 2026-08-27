"""
run_pipeline.py — Unified BD Propensity Scanner CLI

Usage:
    python run_pipeline.py --company "Herbalife"
    python run_pipeline.py --company "OmniActive Health Technologies" --linkedin "https://www.linkedin.com/company/omniactive-health-technologies"
"""

import argparse
import warnings
warnings.filterwarnings("ignore")

from bd_engine.collectors.serper_collector import SerperCollector
from bd_engine.collectors.openfda_collector import OpenFDACollector
from bd_engine.collectors.apify_collector import ApifyCollector
from bd_engine.collectors.growjo_collector import GrowjoCollector
from bd_engine.collectors.owler_collector import OwlerCollector
from bd_engine.collectors.career_traffic_collector import CareerTrafficCollector
from bd_engine.bd_scorer import PropensityScorer

import os
APIFY_TOKEN = os.environ.get("APIFY_API_TOKEN", "")


def run_360_scan(company_name: str, domain: str = None, linkedin_url: str = None, prev_headcount: int = None):
    print("\n" + "=" * 80)
    print(f"  360 BD PROPENSITY INTELLIGENCE SCAN: {company_name}")
    print("=" * 80)

    # 1. openFDA Compliance
    print("\n  [1/6] openFDA compliance scan...")
    fda = OpenFDACollector()
    fda_data = fda.analyze_company(company_name, lookback_years=3)

    # 2. Serper 6-Month Market Signals
    print("  [2/6] Serper market intelligence...")
    serper = SerperCollector()
    serper_data = serper.analyze_company(company_name)

    # 3. Apify LinkedIn Headcount (snapshot baseline)
    print("  [3/6] Apify LinkedIn headcount snapshot...")
    apify = ApifyCollector(api_token=APIFY_TOKEN)
    apify_data = apify.analyze_company(
        company_name=company_name,
        linkedin_url=linkedin_url,
        previous_headcount=prev_headcount,
    )

    # 4. Growjo YoY Employee Growth % (primary growth signal)
    print("  [4/6] Growjo YoY headcount growth...")
    growjo = GrowjoCollector(api_token=APIFY_TOKEN)
    growjo_data = growjo.fetch_company(company_name)
    if growjo_data:
        print(
            f"        -> Growth: {growjo_data.get('employee_growth_pct', 'N/A')}% YoY | "
            f"Revenue: ${growjo_data.get('estimated_revenue', 0):,} | "
            f"Funding: {growjo_data.get('total_funding', 'N/A')}"
        )
    else:
        print("        -> Not found on Growjo.")

    # 5. Owler Firmographic Intelligence (revenue, acquisitions, competitors)
    print("  [5/6] Owler firmographic intelligence...")
    owler = OwlerCollector(api_token=APIFY_TOKEN)
    owler_data = owler.fetch_company(company_name)
    if owler_data:
        print(
            f"        -> Revenue: {owler_data.get('estimated_annual_revenue', 'N/A')} | "
            f"Acquisitions: {owler_data.get('total_acquisitions', 0)} | "
            f"Competitors tracked: {owler_data.get('total_competitors', 0)}"
        )
    else:
        print("        -> Not found on Owler.")

    # 6. Career Page Traffic & Hiring Velocity
    print("  [6/6] Career page traffic & hiring velocity scan...")
    career = CareerTrafficCollector()
    hc_val = (growjo_data or {}).get("current_employees") or (apify_data.get("firmographics") or {}).get("employee_count")
    g_growth = (growjo_data or {}).get("employee_growth_pct")
    career_data = career.analyze_career_and_hiring(
        company_name=company_name,
        domain=domain,
        current_headcount=int(hc_val) if hc_val else None,
        growjo_growth_pct=float(g_growth) if g_growth is not None else None,
    )
    print(
        f"        -> Activity: {career_data.get('career_page_traffic_activity')} | "
        f"30D Open Roles: {career_data.get('active_job_openings_30d')} | "
        f"ATS: {career_data.get('ats_platform')}"
    )

    # 7. Master Propensity Scorer
    scorer = PropensityScorer()
    scorecard = scorer.score_company(
        company_name=company_name,
        apify_data=apify_data,
        serper_data=serper_data,
        openfda_data=fda_data,
        growjo_data=growjo_data,
        owler_data=owler_data,
        career_data=career_data,
    )

    # --- Display ---
    print("\n" + "=" * 80)
    print(f"  MASTER BD PROPENSITY SCORECARD")
    print("=" * 80)
    print(f"  Company               : {scorecard['company_name']}")
    print(f"  Propensity Score      : {scorecard['propensity_score']} / 100")
    print(f"  Tier                  : [{scorecard['tier']}]")
    print(f"  Urgency               : {scorecard['urgency_label']}")
    print(f"  Talking Point         : {scorecard['primary_talking_point']}")

    # Growjo / Owler summary lines
    if growjo_data:
        print(f"\n  Growjo Intelligence:")
        print(f"    YoY Growth          : {growjo_data.get('employee_growth_pct', 'N/A')}%")
        print(f"    Trajectory          : {growjo_data.get('trajectory', 'N/A')}")
        print(f"    Current Employees   : {growjo_data.get('current_employees', 'N/A')}")
        print(f"    Open Job Postings   : {growjo_data.get('job_openings', 'N/A')}")
        print(f"    Est. Revenue        : ${growjo_data.get('estimated_revenue') or 0:,}")
        print(f"    Total Funding       : {growjo_data.get('total_funding', 'N/A')}")
        print(f"    Lead Score          : {growjo_data.get('lead_score', 'N/A')}")

    if owler_data:
        print(f"\n  Owler Intelligence:")
        print(f"    Est. Annual Revenue : {owler_data.get('estimated_annual_revenue', 'N/A')}")
        print(f"    Total Funding       : ${owler_data.get('total_funding') or 0:,}")
        print(f"    Acquisitions        : {owler_data.get('total_acquisitions', 0)}")
        print(f"    Competitors Tracked : {owler_data.get('total_competitors', 0)}")
        print(f"    Ticker              : {owler_data.get('ticker') or 'Private'}")

    print("\n  Score Breakdown:")
    b = scorecard["score_breakdown"]
    src = b["headcount_growth"]["details"].get("data_source", "")
    print(f"    Headcount Growth  : {b['headcount_growth']['score']:>4.1f} / {b['headcount_growth']['max_points']:.0f}  [{src}]  {b['headcount_growth']['details'].get('detail', '')}")
    print(f"    Plant Expansions  : {b['facility_expansions']['score']:>4.1f} / {b['facility_expansions']['max_points']:.0f}  {b['facility_expansions']['details'].get('detail', '')}")
    print(f"    Exec Turnover     : {b['executive_turnover']['score']:>4.1f} / {b['executive_turnover']['max_points']:.0f}  {b['executive_turnover']['details'].get('detail', '')}")
    print(f"    Regulatory Risk   : {b['regulatory_pressure']['score']:>4.1f} / {b['regulatory_pressure']['max_points']:.0f}  Recalls: {b['regulatory_pressure']['details'].get('total_recalls', 0)}")
    print(f"    Domain Alignment  : {b['domain_alignment']['score']:>4.1f} / {b['domain_alignment']['max_points']:.0f}  Nutra Sector Fit")
    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Run 360 BD Signal Intelligence & Propensity Scorecard")
    parser.add_argument("--company", type=str, required=True, help="Target company name")
    parser.add_argument("--linkedin", type=str, default=None, help="Company LinkedIn URL")
    parser.add_argument("--prev_headcount", type=int, default=None, help="Previous headcount baseline")
    args = parser.parse_args()

    run_360_scan(args.company, args.linkedin, args.prev_headcount)


if __name__ == "__main__":
    main()

