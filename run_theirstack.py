"""
run_theirstack.py — BD Engine: TheirStack Pipeline Runner

Usage:
    python run_theirstack.py                    # Broad nutra market prospect
    python run_theirstack.py --company "Amway"  # Deep-dive on a specific company
    python run_theirstack.py --company "Garden of Life" --domain gardenoflife.com
    python run_theirstack.py --output results.json  # Save output to file
"""

import argparse
import json
import os
import sys

from bd_engine.collectors.theirstack_collector import TheirStackCollector

# -------------------------------------------------------
# API TOKEN — set via env var or hardcode for quick test
# -------------------------------------------------------
API_TOKEN = os.environ.get(
    "THEIRSTACK_API_TOKEN",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ2ZXIiOjEsImp0aSI6IjUxOWIwZTA5LTYwY2EtNGFlNS1hMjQyLTgzNWYyOThhYTE3OSIsImNyZWF0ZWRfYnkiOjIwMDA5OCwicGVybWlzc2lvbnMiOltdLCJhdWQiOiJhcGkiLCJpYXQiOjE3ODcyODc5MDcsInN1YiI6IjE5NTk3MyIsIm5hbWUiOiJWb2x1bWUiLCJlbWFpbCI6Impvam9lODY1NkBnbWFpbC5jb20ifQ.3S_tECXZWnqn2uXibv__uJNGSgxDiDojVI-2t3EtfK8",
)


def print_company_signals(data: dict):
    """Pretty-print a single company's TheirStack signal analysis."""
    print("\n" + "=" * 70)
    print(f"  COMPANY: {data.get('company_name', 'N/A')}")
    print(f"  Domain:  {data.get('company_domain', 'N/A')}")
    print(f"  As of:   {data.get('analysis_timestamp', 'N/A')}")
    print("=" * 70)

    if "error" in data:
        print(f"  [ERROR] {data['error']}")
        return

    # Job volume windows
    counts = data.get("job_counts", {})
    print("\n  JOB VOLUME")
    print(f"    Last 7d:        {counts.get('last_7d', 0)}")
    print(f"    Last 30d:       {counts.get('last_30d', 0)}")
    print(f"    Days 31-90:     {counts.get('days_31_to_90', 0)}")
    print(f"    Days 91-180:    {counts.get('days_91_to_180', 0)}")
    print(f"    Total 90d:      {counts.get('total_90d', 0)}")
    print(f"    Total 180d:     {counts.get('total_180d', 0)}")

    # Velocity
    vel = data.get("velocity", {})
    print("\n  HIRING VELOCITY")
    print(f"    Raw V_R:        {vel.get('raw_velocity_ratio', 0)}")
    print(f"    Sample Flag:    {vel.get('sample_size_flag', 'N/A').upper()}")
    print(f"    Confidence:     {vel.get('confidence_multiplier', 0)}")
    print(f"    Adj V_R:        {vel.get('adjusted_velocity_ratio', 0)}  ← USE THIS FOR SCORING")

    # TPI
    pain = data.get("talent_pain", {})
    print("\n  TALENT PAIN INDEX")
    print(f"    TPI Score:      {pain.get('tpi_score', 0)}")
    print(f"    Stale Roles:    {pain.get('stale_roles_count', 0)}")
    print(f"    Critical (90d+):{len(pain.get('critical_roles', []))}")
    print(f"    High (60-90d):  {len(pain.get('high_pain_roles', []))}")
    print(f"    Watch (30-60d): {len(pain.get('watch_roles', []))}")

    if pain.get("critical_roles"):
        print("\n  CRITICAL STALE ROLES (90d+):")
        for r in pain["critical_roles"][:5]:
            niche = " [NICHE]" if r["is_niche_role"] else ""
            print(f"    • {r['title']}{niche} — {r['days_open']}d open | Weight: {r['seniority_weight']}x")
            if r.get("url"):
                print(f"      {r['url']}")

    if pain.get("high_pain_roles"):
        print("\n  HIGH PAIN ROLES (60-90d):")
        for r in pain["high_pain_roles"][:5]:
            niche = " [NICHE]" if r["is_niche_role"] else ""
            print(f"    • {r['title']}{niche} — {r['days_open']}d open | Weight: {r['seniority_weight']}x")

    # Department breakdown
    dept = data.get("department_breakdown", {})
    if dept:
        print("\n  DEPARTMENT BREAKDOWN")
        for d, count in sorted(dept.items(), key=lambda x: x[1], reverse=True):
            print(f"    {d:<35} {count}")

    # Role diversity
    print("\n  ROLE DIVERSITY")
    print(f"    Unique Role Titles: {data.get('unique_role_diversity', 0)}")
    print(f"    Niche Nutra Roles:  {data.get('niche_role_count', 0)}")

    # Channel diversity
    channels = data.get("posting_channel_diversity", [])
    if channels:
        print(f"\n  POSTING CHANNELS ({len(channels)} total)")
        print(f"    {', '.join(channels[:10])}")

    print()


def print_market_prospect(ranked: dict, top_n: int = 20):
    """Pretty-print the broad market prospecting leaderboard."""
    print("\n" + "=" * 70)
    print("  NUTRACEUTICAL BD TARGET LEADERBOARD (by TPI Score)")
    print("=" * 70)
    print(f"  {'Rank':<5} {'Company':<35} {'TPI':>6} {'Total':>6} {'Stale':>6} {'Niche':>6}")
    print("  " + "-" * 65)

    for i, (company, signals) in enumerate(list(ranked.items())[:top_n], 1):
        print(
            f"  {i:<5} {company[:34]:<35} "
            f"{signals['tpi_score']:>6.1f} "
            f"{signals['total_open_roles']:>6} "
            f"{signals['stale_roles_count']:>6} "
            f"{signals['niche_roles_count']:>6}"
        )

    print()
    print(f"  Showing top {min(top_n, len(ranked))} of {len(ranked)} companies found.")
    print()

    # Show top 5 with their stale roles
    print("  TOP 5 DETAILED SIGNAL BREAKDOWN:")
    for company, signals in list(ranked.items())[:5]:
        print(f"\n  ► {company}")
        for dept, count in sorted(signals["department_breakdown"].items(), key=lambda x: x[1], reverse=True)[:3]:
            print(f"      {dept}: {count} roles")
        for job in signals["sample_jobs"][:3]:
            niche = ""
            print(f"      • {job['title']} — {job['days_open']}d [{job['staleness']}] {job['url'][:60]}")


def main():
    parser = argparse.ArgumentParser(
        description="TheirStack BD Pipeline — Nutraceutical Talent Acquisition"
    )
    parser.add_argument("--company", type=str, help="Target company name for deep analysis")
    parser.add_argument("--domain", type=str, help="Target company domain (e.g. gardenoflife.com)")
    parser.add_argument("--days", type=int, default=90, help="Lookback window in days (default: 90)")
    parser.add_argument("--output", type=str, help="Save results to a JSON file")
    parser.add_argument("--top", type=int, default=20, help="Top N companies to show in leaderboard")
    args = parser.parse_args()

    collector = TheirStackCollector(API_TOKEN)

    if args.company:
        # Deep-dive on a single company
        result = collector.analyze_company(args.company, company_domain=args.domain)
        print_company_signals(result)

        if args.output:
            with open(args.output, "w") as f:
                json.dump(result, f, indent=2)
            print(f"  Saved to: {args.output}")

    else:
        # Broad nutra market prospect
        ranked = collector.prospect_nutra_market(max_age_days=args.days)
        print_market_prospect(ranked, top_n=args.top)

        if args.output:
            with open(args.output, "w") as f:
                json.dump(ranked, f, indent=2)
            print(f"  Saved to: {args.output}")


if __name__ == "__main__":
    main()
