import os
import sys
import json
import csv
import re
import shutil
import argparse
from datetime import datetime, date
import requests
from dotenv import load_dotenv

# Set UTF-8 encoding for Windows terminals
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Load environment variables
load_dotenv(r"c:\Users\joela\OneDrive\Documents\Python\bd-engine\.env")

APOLLO_API_KEY = os.getenv("APOLLO_API_KEY")
THEIRSTACK_API_KEY = os.getenv("THEIRSTACK_API_KEY")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434/api/generate")

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


def fetch_apollo_decision_makers(org_id=None, domain=None):
    """Fetch verified operational and executive decision makers from Apollo."""
    if not APOLLO_API_KEY or (not org_id and not domain):
        return []

    decision_makers = []
    payload = {
        "page": 1,
        "per_page": 6,
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
        people = []
        if r.ok:
            people = r.json().get("people", [])

        # Fallback without seniority restriction if zero results
        if not people and org_id:
            payload.pop("person_seniorities", None)
            payload.pop("q_organization_domains_list", None)
            r2 = requests.post(
                "https://api.apollo.io/api/v1/mixed_people/api_search",
                headers=APOLLO_HEADERS,
                json=payload,
                timeout=10
            )
            if r2.ok:
                people = r2.json().get("people", [])

        for p in people:
            fn = p.get("first_name", "")
            ln = p.get("last_name_obfuscated") or p.get("last_name", "")
            title = p.get("title", "")
            li = p.get("linkedin_url", "")
            if fn and title:
                decision_makers.append({
                    "name": f"{fn} {ln}".strip(),
                    "title": title,
                    "linkedin": li
                })
    except Exception as e:
        print(f"   [Apollo People Warning] {e}")

    return decision_makers


def enrich_company_profile(company_name):
    """Master orchestrator combining TheirStack intelligence + Apollo firmographics."""
    raw_clean = company_name.lower().strip()
    known_dom = KNOWN_DOMAINS.get(raw_clean) or KNOWN_DOMAINS.get(clean_legal_name(raw_clean))

    # Step 1: TheirStack Discovery
    ts_data = fetch_theirstack_company_data(company_name)

    domain = ts_data.get("domain") or known_dom
    apollo_id = ts_data.get("apollo_id")
    jobs_30d = ts_data.get("num_jobs_last_30_days", 0)

    # Step 2: Apollo Organization Enrichment
    apollo_org = fetch_apollo_organization(domain=domain, apollo_id=apollo_id, company_name=company_name)

    # Blend firmographics (preferring Apollo's verified domain/headcount, TheirStack's hiring metrics)
    final_name = apollo_org.get("name") or ts_data.get("name") or company_name
    final_domain = apollo_org.get("domain") or domain or "N/A"
    final_emp = apollo_org.get("employees") or ts_data.get("employee_count") or 0
    final_rev = apollo_org.get("revenue") or "N/A"
    final_ind = apollo_org.get("industry") or ts_data.get("industry") or "Nutraceuticals & Manufacturing"
    final_hq = f"{apollo_org.get('city') or ts_data.get('city') or ''}, {apollo_org.get('state') or ts_data.get('state') or ''}".strip(", ")
    final_li = apollo_org.get("linkedin") or ts_data.get("linkedin_url") or "N/A"
    org_id = apollo_org.get("id") or apollo_id

    # Step 3: Decision Maker Lookup
    decision_makers = fetch_apollo_decision_makers(org_id=org_id, domain=final_domain if final_domain != "N/A" else None)

    # Select primary target authority
    top_contact_name = "Operations Leadership"
    top_contact_title = "Director of Operations / Talent Acquisition"
    top_contact_linkedin = final_li

    if decision_makers:
        # Prioritize technical & operations leadership
        prioritized = sorted(
            decision_makers,
            key=lambda d: 0 if any(k in d["title"].lower() for k in ["operation", "manufacturing", "plant", "quality", "qa", "production"]) else 1
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
    """Calculate multi-dimensional lead priority score (0-100)."""
    # 1. Requisition Urgency & Stagnation (Max 30)
    age = job_item["age_days"]
    if age >= 60:
        stagnation_pts = 30
        stagnation_status = "CRITICAL_STAGNATION (>60 Days Open)"
    elif age >= 30:
        stagnation_pts = 20
        stagnation_status = "AGING_REQUISITION (30-59 Days Open)"
    elif age >= 14:
        stagnation_pts = 12
        stagnation_status = "ACTIVE_SEARCH (14-29 Days Open)"
    else:
        stagnation_pts = 6
        stagnation_status = "FRESH_POSTING (<14 Days Open)"

    # Urgency keyword boost
    jd_lower = job_item["jd"].lower()
    title_lower = job_item["title"].lower()
    if any(k in jd_lower or k in title_lower for k in ["all shifts", "immediate", "urgent", "hiring immediately", "asap"]):
        stagnation_pts = min(30, stagnation_pts + 5)

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

    return total_score, tier, stagnation_status


# ==============================================================================
# 4. LOCAL GEMMA REASONING (OLLAMA ZERO-COST INFERENCE)
# ==============================================================================

def run_gemma_reasoning(job_item, company_item):
    """Execute local Gemma reasoning to produce strategic diagnostic and personalized pitch."""
    t_name = company_item.get("top_contact_name") or "Hiring Authority"
    t_title = company_item.get("top_contact_title") or "Operations Leadership"
    c_name = company_item.get("company_name")
    j_title = job_item.get("title")
    loc = job_item.get("location")
    age = job_item.get("age_days")
    emp = company_item.get("employees") or "mid-market"

    prompt = f"""You are an elite executive recruiter and business development strategist in the nutraceutical, dietary supplement, and pharmaceutical contract manufacturing (CDMO) industry.
Analyze this job posting lead and generate a concrete diagnostic for our business development team.

Target Company: {c_name}
Website: {company_item.get('domain')}
Headcount: {emp} employees | Hiring Velocity: {company_item.get('hiring_velocity_30d', 0)} jobs in last 30 days
Job Title: {j_title}
Department: {job_item.get('department')}
Location: {loc}
Days Open on Job Board: {age} days
Target Hiring Authority / Executive: {t_name} ({t_title})

Brief JD Context:
{job_item.get('jd')[:350]}

Generate a valid JSON object with EXACTLY these two keys:
1. "recruiter_thesis": A concise 2-3 sentence diagnostic explaining why keeping this role open for {age} days creates acute operational drag in {loc}, and why our recruitment agency can fill this vacancy faster than their internal team.
2. "personalized_outreach_pitch": A concise 3-4 sentence cold outreach email/LinkedIn message directed to {t_name} acknowledging their search for a {j_title} in {loc}, noting the technical talent scarcity in dietary supplement manufacturing, and proposing 2 pre-screened candidates for an introductory conversation.

Format your response as valid JSON only. Do not include markdown or explanations outside the JSON."""

    try:
        resp = requests.post(
            OLLAMA_URL,
            json={
                "model": "gemma3:latest",
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": 500,
                    "temperature": 0.2
                }
            },
            timeout=25
        )
        if resp.ok:
            txt = resp.json().get("response", "")
            match = re.search(r"\{.*\}", txt, re.DOTALL)
            if match:
                res_json = json.loads(match.group(0))
                thesis = res_json.get("recruiter_thesis", "").strip()
                pitch = res_json.get("personalized_outreach_pitch", "").strip()
                if thesis and pitch:
                    return thesis, pitch
    except Exception as e:
        pass

    # High-quality deterministic fallback if LLM is offline or times out
    thesis = (
        f"{c_name} has had the {j_title} requisition open for {age} days in {loc}. "
        f"For a {emp}-employee operation with ongoing hiring velocity, keeping this critical seat vacant creates immediate operational drag and overtime expenses. "
        f"In-house talent acquisition is clearly struggling with local candidate availability, making this a prime agency placement opportunity."
    )
    first_name = t_name.split()[0] if t_name else "there"
    pitch = (
        f"Hi {first_name}, I noticed {c_name} has been actively searching for a {j_title} in {loc}. "
        f"Given the stringent cGMP and technical requirements in dietary supplement manufacturing, these roles are notoriously difficult to source locally. "
        f"Our team specializes exclusively in nutraceutical talent acquisition, and we currently have 2 pre-screened candidates with direct industry experience ready for interviews. "
        f"Would you be open to a brief 10-minute sync this week to review their credentials?"
    )
    return thesis, pitch


# ==============================================================================
# 5. MASTER BD ENGINE EXECUTION PIPELINE
# ==============================================================================

def run_bd_engine(csv_path, eval_date=None, output_dir=None):
    """Main execution engine processing a job CSV into scored and reasoned BD leads."""
    if not os.path.exists(csv_path):
        print(f"[ERROR] Input CSV not found: {csv_path}")
        return None

    if eval_date is None:
        eval_date = date(2026, 10, 14)  # Current operational baseline

    print("=" * 80)
    print("🚀 NUTRACEUTICAL BUSINESS DEVELOPMENT (BD) ENGINE")
    print(f"📅 Evaluation Date: {eval_date.strftime('%B %d, %Y')}")
    print(f"📥 Input File: {csv_path}")
    print("=" * 80 + "\n")

    # Step 1: Ingest CSV
    jobs = []
    with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
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
        profile = enrich_company_profile(co_name)
        company_profiles[co_name] = profile
        print(f"     -> Domain: {profile['domain']} | Headcount: {profile['employees']} | 30d Hiring: {profile['hiring_velocity_30d']} jobs")
        print(f"     -> Hiring Lead: {profile['top_contact_name']} ({profile['top_contact_title']})")

    # Count postings per company in this scrape
    company_job_counts = {}
    for j in jobs:
        company_job_counts[j["company_raw"]] = company_job_counts.get(j["company_raw"], 0) + 1

    print("\n⚡ Running Multi-Factor Propensity Scoring & Local Gemma Reasoning...\n")

    scored_leads = []
    for idx, j in enumerate(jobs, 1):
        co_raw = j["company_raw"]
        co_prof = company_profiles.get(co_raw, {})
        co_job_count = company_job_counts.get(co_raw, 1)

        # Calculate Propensity Score
        score, tier, stagnation_status = calculate_propensity_score(j, co_prof, open_jobs_at_company=co_job_count)

        print(f"[{idx:2}/{len(jobs)}] {co_prof.get('company_name', co_raw)} | {j['title']}")
        print(f"     Score: {score}/100 ({tier}) | Open: {j['age_days']} days | Level: {j['seniority']}")

        # Execute Gemma Reasoning
        thesis, pitch = run_gemma_reasoning(j, co_prof)

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
            "date_posted": j["date_posted"],
            "days_open": j["age_days"],
            "requisition_status": stagnation_status,
            "job_location": j["location"],
            "company_domain": co_prof.get("domain", "N/A"),
            "company_employees": co_prof.get("employees", "N/A"),
            "company_revenue": co_prof.get("revenue", "N/A"),
            "hiring_velocity_30d": co_prof.get("hiring_velocity_30d", 0),
            "company_hq": co_prof.get("hq_location", "N/A"),
            "target_contact_name": co_prof.get("top_contact_name", "N/A"),
            "target_contact_title": co_prof.get("top_contact_title", "N/A"),
            "target_contact_linkedin": co_prof.get("top_contact_linkedin", "N/A"),
            "recruiter_thesis": thesis,
            "outreach_pitch_hook": pitch,
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
        "days_open", "requisition_status", "date_posted", "job_location",
        "company_domain", "company_employees", "company_revenue", "hiring_velocity_30d", "company_hq",
        "target_contact_name", "target_contact_title", "target_contact_linkedin",
        "recruiter_thesis", "outreach_pitch_hook", "job_link"
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
    parser.add_argument("--date", default="2026-10-14", help="Evaluation baseline date (YYYY-MM-DD)")
    args = parser.parse_args()

    eval_d = parse_date_flexible(args.date) or date(2026, 10, 14)
    run_bd_engine(args.csv, eval_date=eval_d)
