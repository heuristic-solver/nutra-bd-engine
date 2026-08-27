"""
generate_bd_report.py -- Batch BD intelligence report with consolidated primary columns.
"""

import csv
import time
import warnings
warnings.filterwarnings("ignore")
from datetime import datetime, timezone

import os
APIFY_TOKEN = os.environ.get("APIFY_API_TOKEN", "")

from bd_engine.collectors.growjo_collector  import GrowjoCollector
from bd_engine.collectors.owler_collector   import OwlerCollector
from bd_engine.collectors.apify_collector   import ApifyCollector
from bd_engine.collectors.serper_collector  import SerperCollector
from bd_engine.collectors.openfda_collector import OpenFDACollector
from bd_engine.bd_scorer                    import PropensityScorer

COMPANIES = [
    {"name": "Nordic Naturals",           "linkedin": "nordic-naturals"},
    {"name": "Thorne Research",           "linkedin": "thorne-research"},
    {"name": "Garden of Life",            "linkedin": "garden-of-life"},
    {"name": "NOW Foods",                 "linkedin": "now-foods"},
    {"name": "Jarrow Formulas",           "linkedin": "jarrow-formulas"},
    {"name": "Solgar",                    "linkedin": "solgar"},
    {"name": "Pure Encapsulations",       "linkedin": "pure-encapsulations"},
    {"name": "Life Extension",            "linkedin": "life-extension"},
    {"name": "American Health Holdings",  "linkedin": "american-health-holdings"},
    {"name": "Natrol",                    "linkedin": "natrol"},
]

OUT_FILE = "bd_intelligence_report_10co.csv"
SEP = "=" * 70

BATCH_SIZE = 4
TIMEOUT    = 360

def format_currency(val):
    if not val:
        return "N/A"
    try:
        num = float(val)
        if num >= 1_000_000_000:
            return "${:.2f}B".format(num / 1_000_000_000)
        elif num >= 1_000_000:
            return "${:.1f}M".format(num / 1_000_000)
        elif num >= 1_000:
            return "${:.0f}K".format(num / 1_000)
        elif num > 0:
            return "${:,.0f}".format(num)
        return "$0"
    except (ValueError, TypeError):
        return str(val)

def format_growth(val):
    if val is None or val == "":
        return "Unindexed (Growjo)"
    try:
        num = float(val)
        return "{:+.2f}%".format(num)
    except (ValueError, TypeError):
        return str(val)

def run_in_subbatches(names, collector_fn):
    index = {}
    for i in range(0, len(names), BATCH_SIZE):
        chunk = names[i: i + BATCH_SIZE]
        results = collector_fn(chunk)
        for r in results:
            key = (r.get("company_name") or "").strip().lower()
            if key:
                index[key] = r
    return index

def run_apify_subbatch(companies):
    a = ApifyCollector(api_token=APIFY_TOKEN)
    index = {}
    for i in range(0, len(companies), BATCH_SIZE):
        chunk = companies[i: i + BATCH_SIZE]
        urls = ["https://www.linkedin.com/company/" + c["linkedin"] + "/" for c in chunk]
        raw = a.scrape_companies_batch(urls, timeout_secs=TIMEOUT)
        for r in raw:
            key = (r.get("company_name") or "").strip().lower()
            if key:
                index[key] = r
    return index

def fuzzy_match(name, index):
    key = name.strip().lower()
    if key in index:
        return index[key]
    for k, v in index.items():
        if key in k or k in key:
            return v
    return None

def build_row(company, g, o, a, serper_data, fda_data, scorecard):
    g = g or {}
    o = o or {}
    a = a or {}
    b = scorecard.get("score_breakdown", {})
    fda_sum    = (fda_data    or {}).get("summary", {})
    serper_sum = (serper_data or {}).get("signal_summary", {})

    # 1. Primary Headcount Consolidation
    g_hc = g.get("current_employees")
    li_hc = a.get("employee_count")
    ow_hc = o.get("employee_count")

    if g_hc and str(g_hc).isdigit() and int(g_hc) > 0:
        primary_hc = int(g_hc)
        hc_source = "Growjo"
    elif li_hc and str(li_hc).isdigit() and int(li_hc) > 0:
        primary_hc = int(li_hc)
        hc_source = "LinkedIn"
    elif ow_hc and str(ow_hc).isdigit() and int(ow_hc) > 0:
        primary_hc = int(ow_hc)
        hc_source = "Owler"
    else:
        primary_hc = "N/A"
        hc_source = "Not Found"

    # 2. Primary Revenue Consolidation
    g_rev = g.get("estimated_revenue")
    ow_rev_band = o.get("estimated_annual_revenue")
    ow_rev_raw = o.get("revenue")

    if g_rev and str(g_rev).isdigit() and int(g_rev) > 0:
        primary_rev = format_currency(g_rev)
        rev_source = "Growjo (modeled)"
    elif ow_rev_band:
        primary_rev = ow_rev_band
        rev_source = "Owler (band)"
    elif ow_rev_raw and str(ow_rev_raw).isdigit() and int(ow_rev_raw) > 0:
        primary_rev = format_currency(ow_rev_raw)
        rev_source = "Owler (estimate)"
    else:
        primary_rev = "N/A"
        rev_source = "N/A"

    # 3. Growth & Trajectory Consolidation
    raw_growth = g.get("employee_growth_pct")
    growth_formatted = format_growth(raw_growth)
    
    trajectory = g.get("trajectory")
    if not trajectory:
        trajectory = "STABLE (Baseline)" if primary_hc != "N/A" else "UNKNOWN"

    jobs = g.get("job_openings")
    open_jobs = int(jobs) if (jobs and str(jobs).isdigit()) else 0

    funding = g.get("total_funding") or o.get("total_funding")
    if not funding or str(funding) in ("0", "", "None"):
        funding = "Self-Funded / Private"

    return {
        # === PRIMARY CONSOLIDATED SIGNALS ===
        "company_name":             company["name"],
        "primary_headcount":        primary_hc,
        "headcount_source":         hc_source,
        "yoy_headcount_growth_pct": growth_formatted,
        "hiring_trajectory":        trajectory,
        "active_job_openings":      open_jobs,
        "estimated_annual_revenue": primary_rev,
        "revenue_source":           rev_source,
        "total_funding":            funding,
        "propensity_score":         scorecard.get("propensity_score", ""),
        "tier":                     scorecard.get("tier", ""),
        "urgency_label":            scorecard.get("urgency_label", ""),
        "primary_talking_point":    scorecard.get("primary_talking_point", ""),

        # === CONTACT & IDENTITY ===
        "domain":                   g.get("domain") or o.get("domain", ""),
        "website":                  g.get("website") or o.get("website", ""),
        "linkedin_url":             g.get("linkedin_url") or a.get("linkedin_url", ""),
        "city":                     g.get("city") or o.get("city", ""),
        "state":                    g.get("state") or o.get("state", ""),
        "country":                  g.get("country") or o.get("country", ""),
        "street_address":           o.get("street_address", ""),
        "phone":                    o.get("phone", ""),
        "founded_year":             g.get("founded_year") or o.get("founded", ""),
        "ownership":                o.get("ownership", ""),
        "ticker":                   o.get("ticker", ""),
        "exchange":                 o.get("exchange", ""),

        # === RAW VENDOR BREAKDOWN ===
        "growjo_current_employees": g.get("current_employees", ""),
        "growjo_last_employees":    g.get("last_employees", ""),
        "growjo_yoy_growth_pct":    g.get("employee_growth_pct", ""),
        "growjo_trajectory":        g.get("trajectory", ""),
        "growjo_job_openings":      g.get("job_openings", ""),
        "growjo_estimated_revenue": g.get("estimated_revenue", ""),
        "growjo_total_funding":     g.get("total_funding", ""),
        "growjo_valuation":         g.get("valuation", ""),
        "growjo_lead_score":        g.get("lead_score", ""),
        "owler_revenue":            o.get("revenue", ""),
        "owler_estimated_annual_revenue": o.get("estimated_annual_revenue", ""),
        "owler_total_funding":      o.get("total_funding", ""),
        "owler_total_acquisitions": o.get("total_acquisitions", ""),
        "owler_total_competitors":  o.get("total_competitors", ""),
        "owler_employee_count":     o.get("employee_count", ""),
        "owler_estimated_employees": o.get("estimated_employees", ""),
        "linkedin_employee_count":  a.get("employee_count", ""),
        "linkedin_follower_count":  a.get("follower_count", ""),
        "linkedin_employee_range":  a.get("employee_range", ""),
        "serper_facility_signals":  serper_sum.get("facility_count", 0),
        "serper_funding_ma_signals": serper_sum.get("funding_ma_count", 0),
        "serper_exec_turnover_signals": serper_sum.get("exec_signals_count", 0),
        "serper_regulatory_press_hits": serper_sum.get("regulatory_count", 0),
        "fda_total_recalls":        fda_sum.get("total_recalls", 0),
        "fda_class1_recalls":       fda_sum.get("class_1_critical", 0),
        "fda_ongoing_recalls":      fda_sum.get("ongoing_active", 0),
        "fda_risk_score":           fda_sum.get("regulatory_risk_score", 0.0),
        "score_headcount_growth":   b.get("headcount_growth", {}).get("score", ""),
        "score_headcount_source":   b.get("headcount_growth", {}).get("details", {}).get("data_source", ""),
        "score_expansions":         b.get("facility_expansions", {}).get("score", ""),
        "score_exec_turnover":      b.get("executive_turnover", {}).get("score", ""),
        "score_regulatory":         b.get("regulatory_pressure", {}).get("score", ""),
        "score_domain_alignment":   b.get("domain_alignment", {}).get("score", ""),
        "scraped_at":               datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }