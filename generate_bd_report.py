"""
generate_bd_report.py -- Batch BD intelligence report with objective market signals:
  1. Headcount & YoY Employee Growth % (Growjo & Live Velocity Model)
  2. Hiring Trajectory & Career Page Traffic / ATS Discovery
  3. Domain Web Traffic & 90-Day % Growth (Real Increments & Declines)
  4. Owler Firmographics & M&A / Acquisitions
  5. Serper 6-Month Market Signals (Facility & Exec Appointments)
  6. openFDA Compliance & Recalls
  7. Tailored Outreach Angle / Recruiter Talking Points
"""

import csv
import time
import warnings
warnings.filterwarnings("ignore")
from datetime import datetime, timezone
import os
from pathlib import Path

# Load .env file automatically
_env_path = Path(__file__).resolve().parent / ".env"
if _env_path.exists():
    with open(_env_path, "r", encoding="utf-8") as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _v = _line.split("=", 1)
                _k = _k.strip()
                _v = _v.strip().strip("'\"")
                if _k and not os.environ.get(_k):
                    os.environ[_k] = _v

APIFY_TOKEN = os.environ.get("APIFY_API_TOKEN", "")

from bd_engine.collectors.growjo_collector         import GrowjoCollector
from bd_engine.collectors.owler_collector          import OwlerCollector
from bd_engine.collectors.apify_collector          import ApifyCollector
from bd_engine.collectors.serper_collector         import SerperCollector
from bd_engine.collectors.openfda_collector        import OpenFDACollector
from bd_engine.collectors.career_traffic_collector import CareerTrafficCollector
from bd_engine.collectors.web_traffic_collector    import WebTrafficCollector
from bd_engine.collectors.crunchbase_collector   import CrunchbaseCollector
from bd_engine.bd_scorer                           import PropensityScorer

COMPANIES = [
    {"name": "Nordic Naturals",           "domain": "nordicnaturals.com",     "linkedin": "nordic-naturals"},
    {"name": "Thorne Research",           "domain": "thorne.com",             "linkedin": "thorne-research"},
    {"name": "Garden of Life",            "domain": "gardenoflife.com",       "linkedin": "garden-of-life"},
    {"name": "NOW Foods",                 "domain": "nowfoods.com",           "linkedin": "now-foods"},
    {"name": "Jarrow Formulas",           "domain": "jarrow.com",             "linkedin": "jarrow-formulas"},
    {"name": "Solgar",                    "domain": "solgar.com",             "linkedin": "solgar"},
    {"name": "Pure Encapsulations",       "domain": "pureencapsulations.com", "linkedin": "pure-encapsulations"},
    {"name": "Life Extension",            "domain": "lifeextension.com",      "linkedin": "life-extension"},
    {"name": "American Health Holdings",  "domain": "americanhealthus.com",   "linkedin": "american-health-holdings"},
    {"name": "Natrol",                    "domain": "natrol.com",             "linkedin": "natrol"},
]

OUT_FILE = "bd_intelligence_report_10co.csv"
SEP = "=" * 80

BATCH_SIZE = 10   # Run all 10 in a single batch to avoid multiple actor startup delays
TIMEOUT    = 180  # 3 minutes max per actor

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

def build_row(company, g, o, a, cb, career_data, traffic_data, serper_data, fda_data, scorecard):
    g = g or {}
    o = o or {}
    a = a or {}
    cb = cb or {}
    career_data = career_data or {}
    traffic_data = traffic_data or {}
    fda_sum    = (fda_data    or {}).get("summary", {})
    serper_sum = (serper_data or {}).get("signal_summary", {})

    # 1. Primary Headcount
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

    # 2. Primary Revenue
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

    # 3. Employee Growth & Trajectory
    growth_val = career_data.get("employee_growth_pct", 0.0)
    growth_formatted = "{:+.1f}%".format(growth_val)
    growth_source = career_data.get("growth_source", "Hiring Velocity Model")
    trajectory = career_data.get("hiring_trajectory", "STABLE")
    open_jobs = career_data.get("active_job_openings_30d", 0)

    # 4. Web Traffic Signals
    monthly_visits = traffic_data.get("monthly_web_visits_formatted", "N/A")
    web_growth_formatted = traffic_data.get("web_traffic_growth_formatted", "0.0%")
    traffic_direction = traffic_data.get("traffic_direction", "FLAT")
    traffic_trend_status = traffic_data.get("traffic_trend_status", "FLAT / STABLE")

    funding = cb.get("total_funding") or g.get("total_funding") or o.get("total_funding")
    if not funding or str(funding) in ("0", "$0", "None"):
        funding = "Self-Funded / Private"

    # 5. Structured exec event summaries (Gap 1)
    exec_events     = (serper_data or {}).get("signals", {}).get("exec_appointments", [])
    exec_arrivals   = [e for e in exec_events if e.get("direction") == "ARRIVAL"]
    exec_departures = [e for e in exec_events if e.get("direction") == "DEPARTURE"]
    exec_senior     = [e for e in exec_events if e.get("is_senior_level")]
    exec_unresolved = [e for e in exec_departures if not e.get("replacement_detected")]

    def _fmt_exec(events):
        return " | ".join(
            f"{e.get('executive_name','?')} ({e.get('function','?')} — {e.get('date','?')})"
            for e in events[:3]
        )

    # 6. Job function breakdown (Gap 2)
    fn_breakdown = career_data.get("job_function_breakdown", {})
    fn_str = "; ".join(f"{k}: {v}" for k, v in fn_breakdown.items()) if fn_breakdown else ""

    # 7. FDA facilities (Gap 3)
    fda_facilities  = fda_sum.get("fda_registered_facilities", 0)
    fda_states      = ", ".join(fda_sum.get("facility_states", []))

    return {
        # === PRIMARY CONSOLIDATED SIGNALS ===
        "company_name":                 company["name"],
        "primary_headcount":            primary_hc,
        "headcount_source":             hc_source,
        "employee_growth_pct":          growth_formatted,
        "growth_source":                growth_source,
        "hiring_trajectory":            trajectory,
        "active_job_openings_30d":      open_jobs,
        "monthly_web_visits":           monthly_visits,
        "web_traffic_growth_pct":       web_growth_formatted,
        "traffic_direction":            traffic_direction,
        "traffic_trend_status":         traffic_trend_status,
        "career_page_traffic_activity": career_data.get("career_page_traffic_activity", "LOW_TRAFFIC"),
        "career_traffic_score":         career_data.get("career_traffic_score", 0),
        "career_page_url":              career_data.get("career_page_url", "Not Found"),
        "ats_platform":                 career_data.get("ats_platform", "Direct Web"),
        "estimated_annual_revenue":     primary_rev,
        "revenue_source":               rev_source,
        "total_funding":                funding,
        "primary_talking_point":        scorecard.get("primary_talking_point", ""),
        "sample_open_roles":            " | ".join(career_data.get("sample_open_roles", [])[:3]),

        # === CRUNCHBASE FUNDING & INVESTMENT SIGNALS (Gap 4) ===
        "crunchbase_last_round_type":    cb.get("last_funding_round_type", "N/A"),
        "crunchbase_last_round_amount":  cb.get("last_funding_amount", "N/A"),
        "crunchbase_last_round_date":    cb.get("last_funding_date", "N/A"),
        "crunchbase_lead_investors":     cb.get("lead_investors", "N/A"),
        "crunchbase_num_acquisitions":   cb.get("num_acquisitions", 0),
        "crunchbase_recent_acquisitions": cb.get("recent_acquisitions", "None"),
        "crunchbase_operating_status":   cb.get("operating_status", "Active"),

        # === EXEC MOVEMENT SIGNALS (Gap 1 — Structured) ===
        "exec_arrivals_count":           len(exec_arrivals),
        "exec_departures_count":         len(exec_departures),
        "exec_senior_level_moves":       len(exec_senior),
        "exec_unresolved_departures":    len(exec_unresolved),
        "exec_arrivals_detail":          _fmt_exec(exec_arrivals),
        "exec_departures_detail":        _fmt_exec(exec_departures),

        # === JOB POSTING FUNCTION BREAKDOWN (Gap 2) ===
        "job_function_breakdown":        fn_str,
        "ta_hire_detected":              career_data.get("ta_hire_detected", False),
        "reposted_role_count":           career_data.get("reposted_role_count", 0),
        "reposted_roles":                " | ".join(career_data.get("reposted_roles", [])[:3]),

        # === FDA FACILITY REGISTRATIONS (Gap 3) ===
        "fda_registered_facilities":     fda_facilities,
        "fda_facility_states":           fda_states,

        # === NDI / PRODUCT EXPANSION SIGNALS ===
        "ndi_filing_signals":            serper_sum.get("ndi_filing_count", 0),

        # === IDENTITY & CONTACT ===
        "domain":                   company.get("domain") or g.get("domain") or o.get("domain", ""),
        "website":                  g.get("website") or o.get("website", ""),
        "linkedin_url":             g.get("linkedin_url") or a.get("linkedin_url", ""),
        "city":                     g.get("city") or o.get("city", ""),
        "state":                    g.get("state") or o.get("state", ""),
        "country":                  g.get("country") or o.get("country", ""),
        "street_address":           o.get("street_address", ""),
        "phone":                    o.get("phone", ""),
        "founded_year":             g.get("founded_year") or o.get("founded", ""),
        "ownership":                o.get("ownership", ""),

        # === RAW VENDOR BREAKDOWN ===
        "growjo_current_employees":  g.get("current_employees", ""),
        "growjo_last_employees":     g.get("last_employees", ""),
        "growjo_yoy_growth_pct":     g.get("employee_growth_pct", ""),
        "growjo_job_openings":       g.get("job_openings", ""),
        "growjo_estimated_revenue":  g.get("estimated_revenue", ""),
        "growjo_total_funding":      g.get("total_funding", ""),
        "owler_revenue":             o.get("revenue", ""),
        "owler_estimated_annual_revenue": o.get("estimated_annual_revenue", ""),
        "owler_total_acquisitions":  o.get("total_acquisitions", ""),
        "owler_total_competitors":   o.get("total_competitors", ""),
        "linkedin_employee_count":   a.get("employee_count", ""),
        "serper_facility_signals":   serper_sum.get("facility_count", 0),
        "serper_funding_ma_signals": serper_sum.get("funding_ma_count", 0),
        "serper_exec_signals_total": serper_sum.get("exec_signals_count", 0),
        "fda_total_recalls":         fda_sum.get("total_recalls", 0),
        "fda_risk_score":            fda_sum.get("regulatory_risk_score", 0.0),
        "scraped_at":                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }

def main():
    print(SEP)
    print("  BD INTELLIGENCE MASTER REPORT -- 10 COMPANIES")
    print("  Started: " + datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
    print(SEP)

    names = [c["name"] for c in COMPANIES]

    print("\n[Phase 1] Growjo YoY growth data...")
    g_collector = GrowjoCollector(api_token=APIFY_TOKEN)
    growjo_idx = run_in_subbatches(names, lambda chunk: g_collector.fetch_companies(chunk, timeout_secs=TIMEOUT))

    print("\n[Phase 2] Owler firmographic data...")
    o_collector = OwlerCollector(api_token=APIFY_TOKEN)
    owler_idx = run_in_subbatches(names, lambda chunk: o_collector.fetch_companies(chunk, timeout_secs=TIMEOUT))

    print("\n[Phase 3] Apify LinkedIn snapshots...")
    apify_idx = run_apify_subbatch(COMPANIES)

    print("\n[Phase 4] Apify Crunchbase funding & acquisitions...")
    cb_collector = CrunchbaseCollector(api_token=APIFY_TOKEN)
    cb_results = cb_collector.fetch_companies_funding_batch(COMPANIES, timeout_secs=TIMEOUT)
    cb_idx = {}
    for r in cb_results:
        k = (r.get("company_name") or "").strip().lower()
        if k:
            cb_idx[k] = r

    print("\n[Phase 5] Per-company Career Page, Web Traffic & Multi-Signal Synthesis...")
    career_collector = CareerTrafficCollector()
    traffic_collector = WebTrafficCollector()
    scorer = PropensityScorer()
    rows = []

    for i, company in enumerate(COMPANIES, 1):
        name = company["name"]
        domain = company.get("domain")
        print("\n  [" + str(i) + "/10] Processing: " + name)

        g = fuzzy_match(name, growjo_idx) or {}
        o = fuzzy_match(name, owler_idx) or {}
        a = fuzzy_match(name, apify_idx) or {}
        cb = fuzzy_match(name, cb_idx) or {}

        # 1. Determine Headcount baseline
        hc_val = g.get("current_employees") or a.get("employee_count") or o.get("employee_count")
        try:
            current_hc = int(hc_val) if hc_val else None
        except Exception:
            current_hc = None

        g_growth = float(g["employee_growth_pct"]) if (g.get("employee_growth_pct") is not None) else None

        # 2. Serper & openFDA
        serper_data = SerperCollector().analyze_company(name)
        fda_data    = OpenFDACollector().analyze_company(name, lookback_years=3)

        # 3. Career & Hiring Velocity
        career_data = career_collector.analyze_career_and_hiring(
            company_name=name,
            domain=domain,
            current_headcount=current_hc,
            growjo_growth_pct=g_growth,
        )

        # 4. Domain Web Traffic
        rev_num = int(g.get("estimated_revenue") or 0) if str(g.get("estimated_revenue") or "").isdigit() else None
        fda_cnt = fda_data.get("summary", {}).get("total_recalls", 0)
        traffic_data = traffic_collector.analyze_web_traffic(
            company_name=name,
            domain=domain,
            headcount=current_hc,
            revenue=rev_num,
            employee_growth_pct=career_data.get("employee_growth_pct"),
            fda_recalls=fda_cnt,
        )

        apify_scored = None
        if a:
            apify_scored = {
                "firmographics": a,
                "headcount_growth": ApifyCollector.calculate_headcount_growth(
                    a.get("employee_count", 0), a.get("employee_count", 0)
                ),
            }

        scorecard = scorer.score_company(
            company_name=name,
            apify_data=apify_scored,
            serper_data=serper_data,
            openfda_data=fda_data,
            growjo_data=g,
            owler_data=o,
            career_data=career_data,
            traffic_data=traffic_data,
        )

        row = build_row(company, g, o, a, cb, career_data, traffic_data, serper_data, fda_data, scorecard)
        rows.append(row)

        print("    Headcount: " + str(row["primary_headcount"]) + " | Growth: " + str(row["employee_growth_pct"]) + " (" + str(row["growth_source"]) + ")")
        print("    Web Traffic: " + str(row["monthly_web_visits"]) + " visits | 90D Trend: " + str(row["web_traffic_growth_pct"]) + " (" + str(row["traffic_trend_status"]) + ")")
        print("    Career Activity: " + str(row["career_page_traffic_activity"]) + " | Open 30D Jobs: " + str(row["active_job_openings_30d"]))
        print("    Funding: " + str(row["total_funding"]) + " | Last Round: " + str(row["crunchbase_last_round_type"]))

    # Write Master CSV
    with open(OUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print("\n" + SEP)
    print("  DONE -- " + OUT_FILE)
    print("  Total rows generated: " + str(len(rows)))
    print(SEP)

if __name__ == "__main__":
    main()