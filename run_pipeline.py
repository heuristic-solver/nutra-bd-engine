"""
run_pipeline.py — Unified BD Signal Runner

Usage:
    python run_pipeline.py --company "Herbalife"
    python run_pipeline.py --company "NOW Health Group"
    python run_pipeline.py --company "OmniActive Health Technologies"
"""

import argparse
import json
import warnings
warnings.filterwarnings("ignore")

from bd_engine.collectors.theirstack_collector import TheirStackCollector
from bd_engine.collectors.serper_collector import SerperCollector
from bd_engine.collectors.openfda_collector import OpenFDACollector
from bd_engine.collectors.apify_collector import ApifyCollector
import run_theirstack


def run_360_scan(company_name: str, domain: str = None, linkedin_url: str = None):
    print("\n" + "=" * 75)
    print(f"  360° BD INTELLIGENCE SCAN: {company_name}")
    print("=" * 75)

    # 1. openFDA Collector
    fda = OpenFDACollector()
    fda_data = fda.analyze_company(company_name, lookback_years=5)
    fda_sum = fda_data["summary"]

    print("\n[1. REGULATORY & FDA COMPLIANCE]")
    print(f"   • Total Recalls (5 Yrs):   {fda_sum['total_recalls']}")
    print(f"   • Critical (Class I):      {fda_sum['class_1_critical']}")
    print(f"   • Moderate (Class II):     {fda_sum['class_2_moderate']}")
    print(f"   • Minor (Class III):       {fda_sum['class_3_minor']}")
    print(f"   • Regulatory Risk Score:   {fda_sum['regulatory_risk_score']} / 100")
    print(f"   • Recruiter Hook:          {fda_data['recruiter_hook']}")
    if fda_data["recalls"]:
        print("   • Recent Recall Records:")
        for r in fda_data["recalls"][:2]:
            print(f"     ► [{r['classification']}] {r['product_description'][:75]}... ({r['report_date']})")
            print(f"       Reason: {r['reason_for_recall'][:100]}...")

    # 2. Serper 6-Month Market Signals
    serper = SerperCollector()
    serper_data = serper.analyze_company(company_name)
    s_sum = serper_data["signal_summary"]

    print("\n[2. RECENT MARKET SIGNALS (PAST 6 MONTHS)]")
    print(f"   • Facility / Plant Expansions: {s_sum['facility_count']}")
    print(f"   • M&A / Capital Funding:       {s_sum['funding_ma_count']}")
    print(f"   • Executive Appointments:      {s_sum['exec_signals_count']}")
    print(f"   • Trade Press Mentions:        {s_sum['trade_press_count']}")

    for cat in ["facility_expansion", "funding_ma", "exec_appointments", "trade_press"]:
        items = serper_data["signals"].get(cat, [])
        if items:
            print(f"\n   ► Top {cat.upper().replace('_', ' ')} Event:")
            print(f"     • {items[0]['title']}")
            print(f"       Date: {items[0]['date']} | Source: {items[0]['source']}")
            if items[0].get("url"):
                print(f"       Link: {items[0]['url'][:80]}")

    # 3. Apify LinkedIn Headcount & Growth
    apify = ApifyCollector()
    if apify.is_configured():
        print("\n[3. LINKEDIN HEADCOUNT & GROWTH TRAJECTORY]")
        apify_res = apify.analyze_company(company_name, linkedin_url=linkedin_url)
        if apify_res.get("firmographics"):
            fg = apify_res["firmographics"]
            print(f"   • Exact Headcount:         {fg.get('employee_count')} employees")
            print(f"   • Follower Count:          {fg.get('follower_count')}")
            print(f"   • Industry:                {fg.get('industry')}")
            print(f"   • LinkedIn URL:            {fg.get('linkedin_url')}")

    print("\n" + "=" * 75)
    print("  SCAN COMPLETE")
    print("=" * 75 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Run 360° BD Signal Intelligence on a Target Account")
    parser.add_argument("--company", type=str, required=True, help="Target company name")
    parser.add_argument("--domain", type=str, default=None, help="Company website domain")
    parser.add_argument("--linkedin", type=str, default=None, help="Company LinkedIn URL")
    args = parser.parse_args()

    run_360_scan(args.company, args.domain, args.linkedin)


if __name__ == "__main__":
    main()
