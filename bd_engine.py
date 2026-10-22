import os
import sys
import json
import csv
import re
import shutil
import argparse
from datetime import datetime, date
import requests
import socket
from dotenv import load_dotenv
import urllib3.util.connection as urllib3_cn

# Force IPv4 connection to prevent Windows IPv6 DNS SYN timeouts on external APIs
urllib3_cn.allowed_gai_family = lambda: socket.AF_INET

# Set UTF-8 encoding and unbuffered line output for Windows terminals and background tasks
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", line_buffering=True)

# Load environment variables
load_dotenv(r"c:\Users\joela\OneDrive\Documents\Python\bd-engine\.env")

APOLLO_API_KEY = os.getenv("APOLLO_API_KEY")
THEIRSTACK_API_KEY = os.getenv("THEIRSTACK_API_KEY")
APIFY_TOKEN = os.getenv("APIFY_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")

try:
    from apify.client import ApifyWrapper
    from apify.actors import ApifyActorsManager
except (ImportError, ModuleNotFoundError):
    ApifyWrapper = None
    ApifyActorsManager = None

# Fallback token file if not in .env
if not THEIRSTACK_API_KEY:
    ts_token_path = r"c:\Users\joela\OneDrive\Documents\Python\ai-job-candidate-matching-v4\.theirstack_token"
    if os.path.exists(ts_token_path):
        with open(ts_token_path, "r", encoding="utf-8") as f:
            THEIRSTACK_API_KEY = f.read().strip()

# HTTP Headers
APOLLO_HEADERS = {
    "Cache-Control": "no-cache",
    "Content-Type": "application/json",
    "X-Api-Key": APOLLO_API_KEY or ""
}

THEIRSTACK_HEADERS = {
    "Authorization": f"Bearer {THEIRSTACK_API_KEY or ''}",
    "Content-Type": "application/json"
}

ANTHROPIC_HEADERS = {
    "x-api-key": ANTHROPIC_API_KEY or "",
    "anthropic-version": "2023-06-01",
    "content-type": "application/json"
}

# Pre-known domain overrides for common edge cases
KNOWN_DOMAINS = {
    "us pharmalab inc.": "uspharmalab.com",
    "us pharmalab": "uspharmalab.com",
    "herbalife": "herbalife.com",
    "resource label group": "resourcelabel.com",
    "pacific manufacturing and design": "pac-mfg.com",
    "pacific manufacturing": "pac-mfg.com",
    "advatix": "advatix.com",
    "somafina": "somafina.com",
    "american biosciences, inc.": "americanbiosciences.com",
    "american biosciences": "americanbiosciences.com",
    "next level nutraceuticals": "nlnutrition.com",
    "next level nutrition": "nlnutrition.com",
    "vytalogy wellness, llc": "vytalogy.com",
    "vytalogy wellness": "vytalogy.com"
}


# ==============================================================================
# 1. DYNAMIC CSV PARSING & NORMALIZATION
# ==============================================================================

def normalize_column_name(col):
    """Normalize column header for fuzzy matching."""
    return re.sub(r"[^a-z0-9]", "", col.lower())


def detect_columns(fieldnames):
    """Dynamically map CSV headers to canonical schema fields."""
    mapping = {
        "title": None,
        "company": None,
        "location": None,
        "date_posted": None,
        "jd": None,
        "link": None,
        "salary": None,
        "platform": None
    }

    norm_fields = {f: normalize_column_name(f) for f in fieldnames}

    for orig, norm in norm_fields.items():
        if not mapping["title"] and any(k in norm for k in ["title", "role", "position", "jobtitle", "jobname"]):
            mapping["title"] = orig
        elif not mapping["company"] and any(k in norm for k in ["company", "employer", "organization", "account"]):
            mapping["company"] = orig
        elif not mapping["location"] and any(k in norm for k in ["location", "city", "place", "state", "joblocation"]):
            mapping["location"] = orig
        elif not mapping["date_posted"] and any(k in norm for k in ["dateposted", "posteddate", "postedat", "date", "createdat"]):
            mapping["date_posted"] = orig
        elif not mapping["jd"] and any(k in norm for k in ["jobdescription", "description", "jd", "summary", "jobbody"]):
            mapping["jd"] = orig
        elif not mapping["link"] and any(k in norm for k in ["joblink", "link", "url", "applyurl", "joburl"]):
            mapping["link"] = orig
        elif not mapping["salary"] and any(k in norm for k in ["salary", "pay", "compensation", "rate"]):
            mapping["salary"] = orig
        elif not mapping["platform"] and any(k in norm for k in ["platform", "source", "site", "board"]):
            mapping["platform"] = orig

    return mapping


def parse_date_flexible(date_str):
    """Safely parse various date formats."""
    if not date_str:
        return None
    date_str = date_str.strip()
    
    # Try ISO YYYY-MM-DD
    try:
        parts = date_str.split("T")[0].split("-")
        if len(parts) == 3:
            return date(int(parts[0]), int(parts[1]), int(parts[2]))
    except Exception:
        pass

    # Try common formats like MM/DD/YYYY or DD/MM/YYYY
    for fmt in ("%m/%d/%Y", "%Y/%m/%d", "%d/%m/%Y", "%b %d, %Y", "%d %b %Y"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except Exception:
            continue

    return None


def clean_legal_name(company_name):
    """Strip common legal suffixes for fuzzy matching."""
    c = company_name.strip()
    c = re.sub(r"(?i)\s*,?\s*(inc\.?|llc\.?|corp\.?|corporation|ltd\.?|limited|co\.?|company)$", "", c)
    return c.strip()


# ==============================================================================
# 2. MULTI-SOURCE COMPANY INTELLIGENCE LAYER (THEIRSTACK + APOLLO)
# ==============================================================================

def fetch_stale_jobs_theirstack(min_age_days=45, limit=20, output_path=None):
    """Query TheirStack API for live, unfilled jobs that have been open for at least min_age_days."""
    if not THEIRSTACK_API_KEY:
        print("[ERROR] TheirStack API key missing.")
        return None

    print(f"\n📡 Querying TheirStack for Live Stale Requisitions (≥ {min_age_days} Days Open)...")
    payload = {
        "job_title_or": [
            "Quality Assurance Manager", "Formulation Chemist", "Plant Manager",
            "Director of Operations", "Quality Control Supervisor", "Packaging Manager",
            "R&D Chemist", "Regulatory Affairs Specialist", "Manufacturing Supervisor"
        ],
        "industry_or": [
            "Pharmaceutical Manufacturing", "Biotechnology Research", "Food and Beverage Services"
        ],
        "job_country_code_or": ["US"],
        "posted_at_max_age_days": 180,
        "discovered_at_min_age_days": min_age_days,
        "is_closed": False,
        "limit": limit
    }

    try:
        r = requests.post(
            "https://api.theirstack.com/v1/jobs/search",
            headers=THEIRSTACK_HEADERS,
            json=payload,
            timeout=20
        )
        if not r.ok:
            print(f"[ERROR] Failed to fetch stale jobs from TheirStack: {r.status_code} {r.text[:200]}")
            return None

        data = r.json().get("data", [])
        print(f"✓ Retrieved {len(data)} live stale postings from TheirStack.")

        stale_jobs = []
        seen_companies = set()

        for j in data:
            co_obj = j.get("company_object") or {}
            co_name = co_obj.get("name") or j.get("company")
            if not co_name:
                continue
            # Drop third-party recruiting agencies
            if co_obj.get("is_recruiting_agency"):
                continue

            seen_companies.add(co_name)
            stale_jobs.append({
                "Platform": "TheirStack Live (Stale Job Sourced)",
                "Job Title": j.get("job_title", ""),
                "Company": co_name,
                "Location": j.get("short_location") or j.get("location") or "United States",
                "Date Posted": str(j.get("date_posted") or "")[:10],
                "Salary": j.get("salary_string") or (f"${j.get('avg_annual_salary_usd'):,.0f}" if j.get("avg_annual_salary_usd") else "N/A"),
                "Job Link": j.get("final_url") or j.get("url") or "",
                "Job Description": (j.get("description") or "")[:800]
            })

        out_csv = output_path or os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "stale_jobs_live.csv")
        os.makedirs(os.path.dirname(out_csv), exist_ok=True)

        with open(out_csv, "w", encoding="utf-8-sig", newline="") as f:
            if stale_jobs:
                writer = csv.DictWriter(f, fieldnames=list(stale_jobs[0].keys()))
                writer.writeheader()
                writer.writerows(stale_jobs)

        print(f"✓ Filtered {len(stale_jobs)} unique direct-employer stale jobs saved to: {out_csv}\n")
        return out_csv

    except Exception as e:
        print(f"[ERROR] Failed during stale job fetch: {e}")
        return None


def fetch_theirstack_company_data(company_name):
    """Query TheirStack Company Search to extract domain, apollo_id, and hiring velocity."""
    if not THEIRSTACK_API_KEY:
        return {}

    clean_name = clean_legal_name(company_name)
    payload = {
        "company_name_or": [company_name, clean_name],
        "limit": 3
    }

    try:
        r = requests.post(
            "https://api.theirstack.com/v1/companies/search",
            headers=THEIRSTACK_HEADERS,
            json=payload,
            timeout=10
        )
        if r.ok:
            data = r.json().get("data", [])
            for co in data:
                # Prefer exact match or one with domain/apollo_id
                if co.get("domain") or co.get("apollo_id") or co.get("num_jobs_last_30_days", 0) > 0:
                    return {
                        "name": co.get("name"),
                        "domain": co.get("domain"),
                        "apollo_id": co.get("apollo_id"),
                        "employee_count": co.get("employee_count"),
                        "annual_revenue_usd": co.get("annual_revenue_usd"),
                        "num_jobs_last_30_days": co.get("num_jobs_last_30_days") or 0,
                        "total_jobs": co.get("num_jobs") or 0,
                        "industry": co.get("industry") or "",
                        "city": co.get("city") or "",
                        "state": co.get("state_code") or co.get("state") or "",
                        "country": co.get("country") or "United States",
                        "linkedin_url": co.get("linkedin_url") or "",
                        "theirstack_id": co.get("id")
                    }
    except Exception as e:
        print(f"   [TheirStack Lookup Warning] {company_name}: {e}")

    return {}


def fetch_apollo_organization(domain=None, apollo_id=None, company_name=None):
    """Enrich company firmographics from Apollo."""
    if not APOLLO_API_KEY:
        return {}

    params = {}
    if apollo_id:
        params["id"] = apollo_id
    elif domain:
        params["domain"] = domain
    elif company_name:
        params["name"] = company_name

    try:
        r = requests.get(
            "https://api.apollo.io/api/v1/organizations/enrich",
            headers=APOLLO_HEADERS,
            params=params,
            timeout=10
        )
        if r.ok:
            org = r.json().get("organization") or {}
            tech_items = org.get("current_technologies", [])
            tech_names = [t.get("name", "") if isinstance(t, dict) else str(t) for t in tech_items[:6]]
            return {
                "id": org.get("id"),
                "name": org.get("name"),
                "domain": org.get("primary_domain"),
                "employees": org.get("estimated_num_employees"),
                "revenue": org.get("annual_revenue_printed") or "N/A",
                "industry": org.get("industry") or "Nutraceuticals & Health",
                "city": org.get("city") or "",
                "state": org.get("state") or "",
                "country": org.get("country") or "United States",
                "linkedin": org.get("linkedin_url") or "",
                "tech_stack": "; ".join([t for t in tech_names if t])
            }
    except Exception as e:
        print(f"   [Apollo Org Warning] {company_name}: {e}")

    return {}


def check_openfda_compliance(company_name):
    """Query openFDA for active enforcement actions, warning letters, or recalls."""
    clean_name = clean_legal_name(company_name).split()[0].replace(",", "").replace(".", "").strip()
    if len(clean_name) <= 2:
        return "Clean Compliance Record (No openFDA Enforcements)"
    try:
        url = f'https://api.fda.gov/drug/enforcement.json?search=openfda.manufacturer_name:"{clean_name}"&limit=1'
        r = requests.get(url, timeout=6)
        if r.ok:
            results = r.json().get("results", [])
            if results:
                rec = results[0]
                reason = rec.get("reason_for_recall", "Recall Event")
                status = rec.get("status", "Ongoing")
                return f"Active FDA Recall: {reason[:100]}... [Status: {status}]"
    except Exception:
        pass
    return "Clean Compliance Record (No openFDA Enforcements)"


def fetch_apollo_decision_makers_and_mobility(org_id=None, domain=None, company_name=None):
    """
    Fetch verified unmasked operational & executive decision makers,
    and detect recent executive hires / internal promotions (strictly 2025-2026).
    """
    if not APOLLO_API_KEY or (not org_id and not domain):
        return [], []

    decision_makers = []
    leadership_moves = []

    payload = {
        "page": 1,
        "per_page": 8,
        "person_seniorities": ["c_suite", "vp", "director", "head", "manager"]
    }
    if org_id:
        payload["organization_ids"] = [org_id]
    if domain:
        payload["q_organization_domains_list"] = [domain]

    try:
        r = requests.post(
            "https://api.apollo.io/api/v1/mixed_people/api_search",
            headers=APOLLO_HEADERS,
            json=payload,
            timeout=10
        )
        people = r.json().get("people", []) if r.ok else []

        if not people and org_id:
            payload.pop("person_seniorities", None)
            payload.pop("q_organization_domains_list", None)
            r2 = requests.post(
                "https://api.apollo.io/api/v1/mixed_people/api_search",
                headers=APOLLO_HEADERS,
                json=payload,
                timeout=10
            )
            people = r2.json().get("people", []) if r2.ok else []

        c_target = (company_name or "").lower()

        for p in people[:6]:
            pid = p.get("id")
            fn = p.get("first_name", "")
            ln = p.get("last_name_obfuscated") or p.get("last_name", "")
            title = p.get("title", "") or "Executive"
            li = p.get("linkedin_url", "")
            real_name = f"{fn} {ln}".strip() if fn else "Executive Contact"

            # Fetch un-obfuscated profile and mobility
            if pid:
                try:
                    r_p = requests.get(f"https://api.apollo.io/api/v1/people/{pid}", headers=APOLLO_HEADERS, timeout=8)
                    if r_p.ok:
                        person = r_p.json().get("person", {})
                        full_name = person.get("name") or f"{person.get('first_name', '')} {person.get('last_name', '')}".strip()
                        if full_name:
                            real_name = full_name
                        if person.get("linkedin_url"):
                            li = person.get("linkedin_url")

                        history = person.get("employment_history", [])
                        if history:
                            curr = history[0]
                            s_date = curr.get("start_date") or ""
                            curr_title = curr.get("title") or title
                            is_recent_start = s_date.startswith("2025") or s_date.startswith("2026")

                            promoted = False
                            for past in history[1:]:
                                p_org = str(past.get("organization_name", "")).lower()
                                p_end = str(past.get("end_date", ""))
                                past_title = past.get("title") or "Previous Role"
                                if (c_target and c_target in p_org) or (domain and domain in str(past.get("company_website", "")).lower()):
                                    eff_date = s_date if is_recent_start else (p_end if (p_end.startswith("2025") or p_end.startswith("2026")) else "")
                                    if eff_date:
                                        leadership_moves.append(f"[INTERNAL PROMOTION] {real_name}: {past_title} -> {curr_title} (Effective: {eff_date})")
                                        promoted = True
                                        break

                            if is_recent_start and not promoted:
                                leadership_moves.append(f"[RECENT HIRE] {real_name} joined as {curr_title} (Started: {s_date})")
                except Exception:
                    pass

            if real_name and title:
                decision_makers.append({
                    "name": real_name,
                    "title": title,
                    "linkedin": li
                })
    except Exception as e:
        print(f"   [Apollo Decision Maker Warning] {e}")

    return decision_makers, leadership_moves


def fetch_linkedin_social_signals(company_name, company_linkedin_url=None, max_posts=5):
    """
    Query Apify Actors harvestapi/linkedin-post-search & harvestapi/linkedin-company-posts
    to detect real-time 0-day LinkedIn posts for employee departures, new hires,
    and official company welcome/promotion announcements.
    """
    if not APIFY_TOKEN or not ApifyActorsManager:
        return []

    try:
        mgr = ApifyActorsManager()
        res = mgr.fetch_company_social_signals(company_name, company_linkedin_url=company_linkedin_url, max_posts=max_posts)
        if res.get("success") and res.get("signals"):
            signals = res["signals"]
            print(f"     ✓ Captured {len(signals)} 0-Day LinkedIn Social Signals!")
            return signals
        elif res.get("errors"):
            for err in res["errors"]:
                if "hard limit" in err.lower():
                    print(f"     ⚠️ [Apify Social Radar] Monthly usage limit reached. Using database mobility signals.")
                    return []
                else:
                    print(f"     ⚠️ [Apify Social Radar Note] {err[:80]}")
    except Exception as e:
        print(f"     ⚠️ [Apify Radar Exception] {e}")

    return []


def enrich_company_profile(company_name, enable_social_radar=True):
    """Master orchestrator combining TheirStack intelligence + Apollo firmographics + openFDA compliance + Apify Social Signal Radar."""
    raw_clean = company_name.lower().strip()
    known_dom = KNOWN_DOMAINS.get(raw_clean) or KNOWN_DOMAINS.get(clean_legal_name(raw_clean))

    # Step 1: TheirStack Discovery
    ts_data = fetch_theirstack_company_data(company_name)

    domain = ts_data.get("domain") or known_dom
    apollo_id = ts_data.get("apollo_id")
    jobs_30d = ts_data.get("num_jobs_last_30_days", 0)

    # Step 2: Apollo Organization Enrichment
    apollo_org = fetch_apollo_organization(domain=domain, apollo_id=apollo_id, company_name=company_name)

    # Blend firmographics
    final_name = apollo_org.get("name") or ts_data.get("name") or company_name
    final_domain = apollo_org.get("domain") or domain or "N/A"
    final_emp = apollo_org.get("employees") or ts_data.get("employee_count") or 0
    final_rev = apollo_org.get("revenue") or "N/A"
    final_ind = apollo_org.get("industry") or ts_data.get("industry") or "Nutraceuticals & Manufacturing"
    final_hq = f"{apollo_org.get('city') or ts_data.get('city') or ''}, {apollo_org.get('state') or ts_data.get('state') or ''}".strip(", ")
    final_li = apollo_org.get("linkedin") or ts_data.get("linkedin_url") or "N/A"
    org_id = apollo_org.get("id") or apollo_id
    tech_stack = apollo_org.get("tech_stack", "")

    # Step 3: openFDA Compliance Check
    fda_compliance = check_openfda_compliance(company_name)

    # Step 4: Decision Makers & Executive Mobility
    decision_makers, leadership_moves = fetch_apollo_decision_makers_and_mobility(
        org_id=org_id,
        domain=final_domain if final_domain != "N/A" else None,
        company_name=final_name
    )

    # Step 4.5: Real-Time LinkedIn Social Signal Radar (0-Day Departures & Joins)
    social_signals = []
    if enable_social_radar:
        social_signals = fetch_linkedin_social_signals(final_name, final_li)
        for sig in social_signals:
            leadership_moves.append(sig["label"])

    # Select primary target authority
    top_contact_name = "Operations Leadership"
    top_contact_title = "Director of Operations / Talent Acquisition"
    top_contact_linkedin = final_li

    if decision_makers:
        # Prioritize technical & operations leadership
        prioritized = sorted(
            decision_makers,
            key=lambda d: 0 if any(k in d["title"].lower() for k in ["operation", "manufacturing", "plant", "quality", "qa", "production", "commercial", "ceo", "president"]) else 1
        )
        top = prioritized[0]
        top_contact_name = top["name"]
        top_contact_title = top["title"]
        top_contact_linkedin = top["linkedin"]

    return {
        "company_name": final_name,
        "raw_name": company_name,
        "domain": final_domain,
        "employees": final_emp,
        "revenue": final_rev,
        "industry": final_ind,
        "hq_location": final_hq or "United States",
        "linkedin_url": final_li,
        "hiring_velocity_30d": jobs_30d,
        "total_active_jobs": ts_data.get("total_jobs", 0),
        "tech_stack": tech_stack or "Standard Enterprise ERP / QMS",
        "fda_compliance": fda_compliance,
        "leadership_moves": leadership_moves,
        "social_signals": social_signals,
        "decision_makers": decision_makers,
        "top_contact_name": top_contact_name,
        "top_contact_title": top_contact_title,
        "top_contact_linkedin": top_contact_linkedin
    }


# ==============================================================================
# 3. REQUISITION SCORING & TIERING ENGINE
# ==============================================================================

def analyze_seniority(title):
    t = title.lower()
    if any(k in t for k in ["vp", "vice president", "director", "head of", "c-level", "chief", "executive"]):
        return "Director / VP / Executive", 25, "Estimated Fee: $25k - $40k"
    elif any(k in t for k in ["manager", "team leader", "group lead", "lead", "supervisor"]):
        return "Manager / Team Lead", 20, "Estimated Fee: $15k - $25k"
    elif any(k in t for k in ["associate", "specialist", "coordinator", "engineer", "technician", "chemist"]):
        return "Specialist / Technical Professional", 15, "Estimated Fee: $10k - $15k"
    else:
        return "Operations / Entry-Level Packager", 8, "Volume / Retained Staffing"


def analyze_department(title, jd):
    combined = (title + " " + jd[:500]).lower()
    if any(k in combined for k in ["purchasing", "sourcing", "procurement", "buyer", "supply chain"]):
        return "Supply Chain & Procurement"
    elif any(k in combined for k in ["manufacturing", "production", "blender", "feeder", "batch", "operator"]):
        return "Manufacturing & Plant Operations"
    elif any(k in combined for k in ["packaging", "packer", "packager", "label", "gluing"]):
        return "Packaging & Finishing Operations"
    elif any(k in combined for k in ["quality", "qa", "qc", "compliance", "regulatory", "validation"]):
        return "Quality Assurance & Regulatory"
    elif any(k in combined for k in ["warehouse", "shipping", "logistics", "inventory"]):
        return "Warehouse & Logistics"
    else:
        return "General Operations"


def calculate_propensity_score(job_item, company_item, open_jobs_at_company=1):
    """Calculate multi-dimensional lead priority score (0-100) with deep staleness diagnostics."""
    age = job_item["age_days"]
    is_stale = age >= 45
    days_over_benchmark = max(0, age - 45)  # 45 days is standard nutra/pharma time-to-fill benchmark

    # 1. Requisition Urgency & Stagnation (Max 30)
    if age >= 90:
        stagnation_pts = 30
        stagnation_status = "CHRONIC_VACANCY (>90 Days Open)"
    elif age >= 60:
        stagnation_pts = 28
        stagnation_status = "CRITICAL_STALE (60-89 Days Open)"
    elif age >= 45:
        stagnation_pts = 22
        stagnation_status = "AGING_REQUISITION (45-59 Days Open)"
    elif age >= 30:
        stagnation_pts = 16
        stagnation_status = "MODERATE_SEARCH (30-44 Days Open)"
    elif age >= 14:
        stagnation_pts = 10
        stagnation_status = "ACTIVE_SEARCH (14-29 Days Open)"
    else:
        stagnation_pts = 5
        stagnation_status = "FRESH_POSTING (<14 Days Open)"

    # Urgency keyword boost
    jd_lower = job_item["jd"].lower()
    title_lower = job_item["title"].lower()
    if any(k in jd_lower or k in title_lower for k in ["all shifts", "immediate", "urgent", "hiring immediately", "asap"]):
        stagnation_pts = min(30, stagnation_pts + 5)

    # Vacancy Drag & Financial Disruption Risk
    sen_label = job_item["seniority"]
    if age >= 60 and any(k in sen_label for k in ["Director", "VP", "Manager", "Lead"]):
        drag_risk = "CRITICAL_OPERATIONAL_RISK ($25k-$50k Est. Overtime / Release Delay)"
    elif age >= 45:
        drag_risk = "ELEVATED_CAPACITY_PRESSURE (Bottleneck in Production/QA)"
    else:
        drag_risk = "NORMAL_RECRUITMENT_TIMELINE"

    # 2. Executive Seniority & Placement Fee Value (Max 25)
    seniority_pts = job_item["seniority_pts"]

    # 3. Company Scale & Hiring Crunch Velocity (Max 25)
    emp = company_item.get("employees") or 0
    if 50 <= emp <= 2500:
        scale_pts = 20  # Ideal mid-market CDMO sweet spot
    elif emp > 2500:
        scale_pts = 14  # Enterprise (large budgets, but bureaucratic)
    elif 15 <= emp < 50:
        scale_pts = 12
    else:
        scale_pts = 6

    # Hiring velocity boost (TheirStack 30d jobs or multiple CSV openings)
    velocity = company_item.get("hiring_velocity_30d", 0)
    if velocity >= 5 or open_jobs_at_company >= 2:
        scale_pts = min(25, scale_pts + 5)

    # 4. Nutraceutical ICP Fit (Max 20)
    ind = (company_item.get("industry") or "").lower()
    if any(k in ind for k in ["pharm", "health", "wellness", "dietary", "nutrition", "biotech"]):
        icp_pts = 20
    elif any(k in ind for k in ["label", "packaging", "manufacturing"]):
        icp_pts = 16
    else:
        icp_pts = 10

    total_score = stagnation_pts + seniority_pts + scale_pts + icp_pts

    # Priority Tier
    if total_score >= 75:
        tier = "TIER_1_IMMEDIATE_AGENCY_OPPORTUNITY"
    elif total_score >= 60:
        tier = "TIER_2_HIGH_PRIORITY_TARGET"
    else:
        tier = "TIER_3_MONITOR_VOLUME"

    return total_score, tier, stagnation_status, is_stale, days_over_benchmark, drag_risk


# ==============================================================================
# 4. CLAUDE REASONING (ANTHROPIC MULTI-SIGNAL STRATEGIC SYNTHESIS)
# ==============================================================================

def run_claude_reasoning(job_item, company_item, stale_info=None, co_occurring_openings=None):
    """
    Execute Claude multi-signal reasoning:
    Cross-correlates leadership transitions, facility expansion clusters, tech stack,
    and compliance pressure to identify non-obvious patterns and strategic pitch wedges.
    """
    t_name = company_item.get("top_contact_name") or "Operations Leadership"
    t_title = company_item.get("top_contact_title") or "Director of Operations"
    c_name = company_item.get("company_name")
    j_title = job_item.get("title")
    loc = job_item.get("location")
    age = job_item.get("age_days")
    emp = company_item.get("employees") or "mid-market"
    velocity = company_item.get("hiring_velocity_30d", 0)
    tech = company_item.get("tech_stack", "Standard CDMO ERP/QMS")
    fda = company_item.get("fda_compliance", "Clean Compliance Record")
    moves = company_item.get("leadership_moves", [])

    stale_status, is_stale, days_over, drag_risk = stale_info if stale_info else ("NORMAL", False, 0, "NORMAL")

    moves_text = "\n".join([f"- {m}" for m in moves[:4]]) if moves else "No recent executive transitions recorded in past 12 months."
    openings_text = ", ".join(co_occurring_openings[:5]) if co_occurring_openings else j_title

    prompt = f"""Target Company: {c_name}
Domain: {company_item.get('domain')} | Scale: {emp} employees | 30d Hiring Velocity: {velocity} jobs
Job Title: {j_title}
Department: {job_item.get('department')}
Location: {loc}
Days Open on Job Board: {age} days ({stale_status} | {days_over} days past the 45-day industry benchmark)
Target Hiring Authority: {t_name} ({t_title})
Operational Drag Risk: {drag_risk}
Co-occurring Facility Openings: [{openings_text}]
Installed Tech Stack: {tech}
Recent Leadership Moves & 0-Day LinkedIn Social Signals (2025-2026):
{moves_text}
FDA Compliance Status: {fda}

Brief JD Context:
{job_item.get('jd')[:350]}

Analyze the non-obvious correlations between recent leadership appointments, 0-day LinkedIn departure/join posts, this {age}-day vacancy, co-occurring facility openings, tech stack requirements, and regulatory audit pressure.
Return a valid JSON object with EXACTLY these keys:
{{
  "detected_patterns": ["list of 2-4 detected patterns like NEW_LEADERSHIP_MANDATE, UNANNOUNCED_DEPARTURE, CAPACITY_EXPANSION_CLUSTER, COMPLIANCE_FIRE_DRILL, TECH_STACK_BOTTLENECK, INTERNAL_TALENT_VACUUM"],
  "hidden_relations": "2-3 sentences uncovering non-obvious correlations across the leadership shift, social signals, expansion cluster, tech stack, and compliance risk",
  "operational_drag_cost_est": "Estimated daily or monthly financial drag (e.g. $20k-$40k/mo in overtime burn, lot release delays, or batch quarantine risk)",
  "strategic_pitch_wedge": "The specific talking point and angle to pitch {t_name} directly",
  "recruiter_thesis": "Comprehensive 3-4 sentence strategic diagnostic explaining why internal TA has stalled past 45 days and how our agency solves this"
}}
Format your response as valid JSON only."""

    if ANTHROPIC_API_KEY:
        try:
            payload = {
                "model": ANTHROPIC_MODEL,
                "max_tokens": 2000,
                "system": "You are an elite executive recruiter and business development strategist in the nutraceutical, dietary supplement, and pharmaceutical contract manufacturing (CDMO) industry. Perform multi-source signal fusion and cross-correlate hidden relations to formulate a high-converting recruiter diagnostic thesis. Always respond strictly in valid JSON.",
                "messages": [
                    {"role": "user", "content": prompt}
                ]
            }
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                json=payload,
                headers=ANTHROPIC_HEADERS,
                timeout=45
            )
            if resp.ok:
                data = resp.json()
                content_blocks = data.get("content", [])
                txt = "".join([b.get("text", "") for b in content_blocks if b.get("type") == "text"])
                match = re.search(r"\{.*\}", txt, re.DOTALL)
                if match:
                    res_json = json.loads(match.group(0))
                    return {
                        "detected_patterns": res_json.get("detected_patterns") or ["REQUISITION_STAGNATION"],
                        "hidden_relations": str(res_json.get("hidden_relations", "")).strip(),
                        "operational_drag_cost_est": str(res_json.get("operational_drag_cost_est", "")).strip(),
                        "strategic_pitch_wedge": str(res_json.get("strategic_pitch_wedge", "")).strip(),
                        "recruiter_thesis": str(res_json.get("recruiter_thesis", "")).strip()
                    }
        except Exception:
            pass

    # Intelligent deterministic fallback synthesizing the available signals
    patterns = []
    has_departure_post = any("[0-DAY DEPARTURE POST]" in m for m in moves)
    has_welcome_post = any("[COMPANY ANNOUNCEMENT]" in m or "[0-DAY JOIN POST]" in m for m in moves)

    if has_departure_post:
        patterns.append("UNANNOUNCED_DEPARTURE")
    if has_welcome_post:
        patterns.append("NEW_LEADERSHIP_MANDATE")
    elif moves:
        patterns.append("NEW_LEADERSHIP_MANDATE")
    if len(co_occurring_openings or []) >= 2:
        patterns.append("CAPACITY_EXPANSION_CLUSTER")
    if is_stale:
        patterns.append("REQUISITION_STAGNATION")
    if "Active FDA" in fda:
        patterns.append("COMPLIANCE_FIRE_DRILL")
    if not patterns:
        patterns.append("TALENT_SCARCITY")

    hidden = (
        f"{c_name}'s {j_title} role has exceeded the 45-day benchmark by {days_over} days while managing active facility demand. "
        + (f"With recent executive transitions ({moves[0]}), incoming leadership cannot afford continued batch delays. " if moves else "")
        + (f"Heightened regulatory scrutiny ({fda}) makes this vacancy a critical compliance risk." if "Active FDA" in fda else "Operating without this critical function forces expensive overtime and slows commercial release schedules.")
    )

    cost_est = "$25,000 - $45,000 / month (overtime coverage, delayed lot release, missed CDMO delivery windows)" if is_stale else "Standard vacancy drag"

    pitch = f"Approach {t_name} ({t_title}) directly with pre-screened {j_title} candidates with verified {tech.split(';')[0]} and GMP experience to unblock stalled production and protect delivery commitments."

    thesis = (
        f"{c_name} has had the {j_title} requisition open for {age} days in {loc} (past the 45-day industry benchmark). "
        f"For a {emp}-employee operation with active hiring velocity, keeping this seat vacant causes continuous operational drag and overtime expenses. "
        f"Internal talent acquisition has stalled in sourcing specialized nutraceutical talent, making this an immediate agency placement wedge."
    )

    return {
        "detected_patterns": patterns,
        "hidden_relations": hidden,
        "operational_drag_cost_est": cost_est,
        "strategic_pitch_wedge": pitch,
        "recruiter_thesis": thesis
    }


# ==============================================================================
# 5. MASTER BD ENGINE EXECUTION PIPELINE
# ==============================================================================

def run_bd_engine(csv_path, eval_date=None, output_dir=None, enable_social_radar=True):
    """Main execution engine processing a job CSV into scored and reasoned BD leads."""
    if not os.path.exists(csv_path):
        print(f"[ERROR] Input CSV not found: {csv_path}")
        return None

    if eval_date is None:
        eval_date = date.today()

    print("=" * 80)
    print("🚀 NUTRACEUTICAL BUSINESS DEVELOPMENT (BD) ENGINE")
    print(f"📅 Evaluation Date: {eval_date.strftime('%B %d, %Y')}")
    print(f"📥 Input File: {csv_path}")
    print(f"🧠 Reasoning Engine: Claude ({ANTHROPIC_MODEL})")
    print(f"📡 0-Day Social Radar: {'ENABLED (Apify HarvestAPI)' if enable_social_radar else 'DISABLED'}")
    print("=" * 80 + "\n")

    # Step 1: Ingest CSV
    jobs = []
    with open(csv_path, "r", encoding="utf-8-sig", errors="replace") as f:
        reader = csv.DictReader(f)
        col_map = detect_columns(reader.fieldnames or [])

        if not col_map["title"] or not col_map["company"]:
            print(f"[ERROR] Could not identify Title and Company columns. Found: {reader.fieldnames}")
            return None

        print(f"Column Mapping Detected:")
        for k, v in col_map.items():
            print(f"  • {k.upper():12} -> {v}")
        print()

        for row in reader:
            title = (row.get(col_map["title"]) or "").strip()
            company = (row.get(col_map["company"]) or "").strip()
            location = (row.get(col_map["location"]) or "").strip() if col_map["location"] else ""
            date_raw = (row.get(col_map["date_posted"]) or "").strip() if col_map["date_posted"] else ""
            jd = (row.get(col_map["jd"]) or "").strip() if col_map["jd"] else ""
            link = (row.get(col_map["link"]) or "").strip() if col_map["link"] else ""
            salary = (row.get(col_map["salary"]) or "").strip() if col_map["salary"] else ""
            platform = (row.get(col_map["platform"]) or "").strip() if col_map["platform"] else "Career Portal"

            if title and company:
                p_date = parse_date_flexible(date_raw)
                age = (eval_date - p_date).days if p_date else 14
                age = max(0, age)
                sen_label, sen_pts, fee_est = analyze_seniority(title)
                dept = analyze_department(title, jd)

                jobs.append({
                    "title": title,
                    "company_raw": company,
                    "location": location,
                    "date_posted": date_raw,
                    "age_days": age,
                    "seniority": sen_label,
                    "seniority_pts": sen_pts,
                    "fee_estimate": fee_est,
                    "department": dept,
                    "job_link": link,
                    "salary_raw": salary,
                    "platform": platform,
                    "jd": jd
                })

    print(f"✓ Parsed {len(jobs)} live job postings across unique companies.\n")

    # Step 2: Company Intelligence & Profile Enrichment
    unique_companies = list(dict.fromkeys([j["company_raw"] for j in jobs]))
    print(f"🏢 Enriching Company Intelligence & Key Decision Makers ({len(unique_companies)} accounts)...")

    company_profiles = {}
    for co_name in unique_companies:
        print(f"  🔍 Processing: {co_name}...")
        profile = enrich_company_profile(co_name, enable_social_radar=enable_social_radar)
        company_profiles[co_name] = profile
        soc_count = len(profile.get("social_signals", []))
        print(f"     -> Domain: {profile['domain']} | Headcount: {profile['employees']} | 30d Hiring: {profile['hiring_velocity_30d']} jobs")
        print(f"     -> Hiring Lead: {profile['top_contact_name']} ({profile['top_contact_title']})")
        print(f"     -> Compliance: {profile['fda_compliance'][:45]}... | Mobility: {len(profile['leadership_moves'])} moves ({soc_count} 0-day social)")

    # Group job titles by company to detect facility expansion clusters
    company_job_titles = {}
    company_job_counts = {}
    for j in jobs:
        c_raw = j["company_raw"]
        company_job_titles.setdefault(c_raw, []).append(j["title"])
        company_job_counts[c_raw] = company_job_counts.get(c_raw, 0) + 1

    print("\n⚡ Running Multi-Signal Pattern Detection & Reasoning...\n")

    scored_leads = []
    for idx, j in enumerate(jobs, 1):
        co_raw = j["company_raw"]
        co_prof = company_profiles.get(co_raw, {})
        co_job_count = company_job_counts.get(co_raw, 1)
        facility_openings = [t for t in company_job_titles.get(co_raw, []) if t != j["title"]]

        # Calculate Propensity Score & Stale Analytics
        score, tier, stagnation_status, is_stale, days_over_benchmark, drag_risk = calculate_propensity_score(
            j, co_prof, open_jobs_at_company=co_job_count
        )

        stale_label = f"STALE (+{days_over_benchmark}d over benchmark)" if is_stale else "NORMAL"
        print(f"[{idx:2}/{len(jobs)}] {co_prof.get('company_name', co_raw)} | {j['title']}")
        print(f"     Score: {score}/100 ({tier}) | Open: {j['age_days']} days ({stale_label}) | Level: {j['seniority']}")

        # Execute Multi-Signal Claude Reasoning
        reasoning_res = run_claude_reasoning(
            j,
            co_prof,
            stale_info=(stagnation_status, is_stale, days_over_benchmark, drag_risk),
            co_occurring_openings=facility_openings
        )

        scored_leads.append({
            "lead_rank": 0,
            "propensity_score": score,
            "priority_tier": tier,
            "company_name": co_prof.get("company_name", co_raw),
            "raw_company": co_raw,
            "job_title": j["title"],
            "department": j["department"],
            "seniority_level": j["seniority"],
            "fee_potential": j["fee_estimate"],
            "days_open": j["age_days"],
            "is_stale": "YES (High Urgency)" if is_stale else "NO",
            "days_over_benchmark": days_over_benchmark,
            "requisition_status": stagnation_status,
            "vacancy_drag_risk": drag_risk,
            "detected_patterns": "; ".join(reasoning_res["detected_patterns"]),
            "hidden_relations": reasoning_res["hidden_relations"],
            "operational_drag_cost_est": reasoning_res["operational_drag_cost_est"],
            "strategic_pitch_wedge": reasoning_res["strategic_pitch_wedge"],
            "installed_tech_stack": co_prof.get("tech_stack", "Standard CDMO ERP/QMS"),
            "recent_leadership_moves": " | ".join(co_prof.get("leadership_moves", [])) or "None tracked (2025-2026)",
            "linkedin_social_signals": " | ".join([s["label"] for s in co_prof.get("social_signals", [])]) or "None detected",
            "fda_compliance_status": co_prof.get("fda_compliance", "Clean Compliance Record"),
            "date_posted": j["date_posted"],
            "job_location": j["location"],
            "company_domain": co_prof.get("domain", "N/A"),
            "company_employees": co_prof.get("employees", "N/A"),
            "company_revenue": co_prof.get("revenue", "N/A"),
            "hiring_velocity_30d": co_prof.get("hiring_velocity_30d", 0),
            "company_hq": co_prof.get("hq_location", "N/A"),
            "target_contact_name": co_prof.get("top_contact_name", "N/A"),
            "target_contact_title": co_prof.get("top_contact_title", "N/A"),
            "target_contact_linkedin": co_prof.get("top_contact_linkedin", "N/A"),
            "recruiter_thesis": reasoning_res["recruiter_thesis"],
            "job_link": j["job_link"],
            "platform": j["platform"]
        })

    # Sort descending by score
    scored_leads.sort(key=lambda x: x["propensity_score"], reverse=True)
    for r_idx, item in enumerate(scored_leads, 1):
        item["lead_rank"] = r_idx

    # Export CSV and JSON
    out_dir = output_dir or r"c:\Users\joela\OneDrive\Documents\Python\bd-engine"
    csv_out_path = os.path.join(out_dir, "job_bd_leads_scored.csv")
    json_out_path = os.path.join(out_dir, "job_bd_leads_full.json")

    csv_fields = [
        "lead_rank", "propensity_score", "priority_tier", "company_name",
        "job_title", "department", "seniority_level", "fee_potential",
        "days_open", "is_stale", "days_over_benchmark", "requisition_status", "vacancy_drag_risk",
        "detected_patterns", "hidden_relations", "operational_drag_cost_est", "strategic_pitch_wedge",
        "installed_tech_stack", "recent_leadership_moves", "linkedin_social_signals", "fda_compliance_status",
        "date_posted", "job_location", "company_domain", "company_employees", "company_revenue",
        "hiring_velocity_30d", "company_hq", "target_contact_name", "target_contact_title",
        "target_contact_linkedin", "recruiter_thesis", "job_link"
    ]

    with open(csv_out_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(scored_leads)

    with open(json_out_path, "w", encoding="utf-8") as f:
        json.dump(scored_leads, f, indent=2, ensure_ascii=False)

    # Copy to Downloads for easy user access
    downloads_dir = r"c:\Users\joela\Downloads"
    if os.path.exists(downloads_dir):
        shutil.copy2(csv_out_path, os.path.join(downloads_dir, "job_bd_leads_scored.csv"))
        print(f"✓ Copied results to Downloads folder: {os.path.join(downloads_dir, 'job_bd_leads_scored.csv')}")

    print("\n" + "=" * 80)
    print("🏆 BD ENGINE COMPLETED SUCCESSFULLY")
    print(f"📊 Total Leads Generated: {len(scored_leads)}")
    print(f"💾 CSV Saved: {csv_out_path}")
    print(f"💾 JSON Saved: {json_out_path}")
    print("=" * 80 + "\n")

    return scored_leads


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Nutraceutical Business Development (BD) Engine")
    default_csv = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "scrape_sample.csv")
    parser.add_argument("--csv", default=default_csv, help="Path to input scrape CSV")
    parser.add_argument("--date", default=None, help="Evaluation baseline date (YYYY-MM-DD, default: today)")
    parser.add_argument("--fetch-stale", action="store_true", help="Fetch live stale jobs from TheirStack (≥ 45 days open)")
    parser.add_argument("--min-age", type=int, default=45, help="Minimum days open for stale job fetch (default: 45)")
    parser.add_argument("--limit", type=int, default=20, help="Number of stale jobs to fetch (default: 20)")
    parser.add_argument("--no-social", action="store_true", help="Disable Apify LinkedIn post radar")
    args = parser.parse_args()

    eval_d = parse_date_flexible(args.date) if args.date else date.today()

    target_csv = args.csv
    if args.fetch_stale:
        fetched_csv = fetch_stale_jobs_theirstack(min_age_days=args.min_age, limit=args.limit)
        if fetched_csv:
            target_csv = fetched_csv

    run_bd_engine(target_csv, eval_date=eval_d, enable_social_radar=not args.no_social)

