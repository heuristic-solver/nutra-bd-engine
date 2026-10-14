import os
import sys
import json
import time
import csv
from urllib.parse import urlparse
import requests
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")
load_dotenv(r"c:\Users\joela\OneDrive\Documents\Python\bd-engine\.env")

APOLLO_API_KEY = os.getenv("APOLLO_API_KEY")

if not APOLLO_API_KEY:
    print("[ERROR] APOLLO_API_KEY is missing from .env!")
    sys.exit(1)

HEADERS = {
    "Cache-Control": "no-cache",
    "Content-Type": "application/json",
    "X-Api-Key": APOLLO_API_KEY
}

# 1. Load companies from nutraceutical_kb.json
kb_path = r"c:\Users\joela\OneDrive\Documents\Python\company-research\matcher\nutraceutical_kb.json"
with open(kb_path, "r", encoding="utf-8") as f:
    kb = json.load(f)

def clean_domain(url_or_domain):
    if not url_or_domain:
        return ""
    raw = url_or_domain.strip().lower()
    if "://" in raw:
        parsed = urlparse(raw)
        netloc = parsed.netloc
    else:
        netloc = raw.split("/")[0]
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc

target_cohort = []
seen_domains = set()

for item in kb:
    name = item.get("company_name", "").strip()
    raw_web = item.get("domain") or item.get("known_website") or item.get("website")
    domain = clean_domain(raw_web)
    # Ensure it's a valid domain and not generic portal
    if domain and "." in domain and domain not in seen_domains and len(name) > 2:
        if domain not in ["linkedin.com", "facebook.com", "twitter.com", "instagram.com"]:
            seen_domains.add(domain)
            target_cohort.append({"name": name, "domain": domain})
    if len(target_cohort) >= 20:
        break

print(f"Selected {len(target_cohort)} Nutraceutical Companies from Database:")
for i, c in enumerate(target_cohort):
    print(f"  {i+1:2d}. {c['name']:35} -> {c['domain']}")

print("\n" + "="*70)
print("STARTING APOLLO INTELLIGENCE PIPELINE ACROSS 20 NUTRA COMPANIES")
print("="*70)

results = []
all_contacts = []

for idx, co in enumerate(target_cohort, 1):
    c_name = co["name"]
    c_domain = co["domain"]
    print(f"\n[{idx}/20] Processing: {c_name} ({c_domain})...")
    
    org_record = {
        "input_name": c_name,
        "input_domain": c_domain,
        "matched_name": "N/A",
        "apollo_id": "N/A",
        "website": f"https://{c_domain}",
        "linkedin_url": "N/A",
        "estimated_employees": "N/A",
        "employee_range": "N/A",
        "founded_year": "N/A",
        "industry": "N/A",
        "hq_city": "N/A",
        "hq_state": "N/A",
        "hq_country": "N/A",
        "annual_revenue": "N/A",
        "total_funding": "N/A",
        "latest_funding_round": "N/A",
        "active_tech_stack": [],
        "active_job_postings_count": 0,
        "active_job_titles": [],
        "decision_makers_found": 0,
        "key_decision_makers": []
    }
    
    # -------------------------------------------------------------
    # Step 1: Organization Match & Enrichment
    # -------------------------------------------------------------
    try:
        url_org = "https://api.apollo.io/api/v1/organizations/enrich"
        params = {"domain": c_domain, "name": c_name}
        resp_org = requests.get(url_org, params=params, headers=HEADERS, timeout=12)
        
        if resp_org.ok:
            data = resp_org.json().get("organization", {})
            if data:
                org_record["matched_name"] = data.get("name") or c_name
                org_record["apollo_id"] = data.get("id") or "N/A"
                org_record["linkedin_url"] = data.get("linkedin_url") or "N/A"
                org_record["estimated_employees"] = data.get("estimated_num_employees") or "N/A"
                org_record["founded_year"] = data.get("founded_year") or "N/A"
                org_record["industry"] = data.get("industry") or "N/A"
                org_record["hq_city"] = data.get("city") or "N/A"
                org_record["hq_state"] = data.get("state") or "N/A"
                org_record["hq_country"] = data.get("country") or "N/A"
                org_record["annual_revenue"] = data.get("annual_revenue_printed") or "N/A"
                org_record["total_funding"] = data.get("total_funding_printed") or "N/A"
                org_record["latest_funding_round"] = data.get("latest_funding_round_date") or "N/A"
                techs = data.get("current_technologies", [])
                org_record["active_tech_stack"] = [t.get("name") for t in techs[:8] if isinstance(t, dict)]
                print(f"  [Org Matched] {org_record['matched_name']} | Headcount: {org_record['estimated_employees']} | HQ: {org_record['hq_city']}, {org_record['hq_country']}")
            else:
                print("  [Org Not Matched] Empty organization payload")
        else:
            print(f"  [Org Match Failed] Status {resp_org.status_code}")
    except Exception as e:
        print(f"  [Org Match Exception] {e}")

    time.sleep(0.3)

    # -------------------------------------------------------------
    # Step 2: Decision Maker Search (POST /mixed_people/api_search)
    # -------------------------------------------------------------
    try:
        url_peop = "https://api.apollo.io/api/v1/mixed_people/api_search"
        payload = {
            "q_organization_domains_list": [c_domain],
            "person_seniorities": ["c_suite", "vp", "director", "head", "manager"],
            "page": 1,
            "per_page": 5
        }
        resp_peop = requests.post(url_peop, json=payload, headers=HEADERS, timeout=12)
        
        if resp_peop.ok:
            p_data = resp_peop.json()
            people = p_data.get("people", [])
            org_record["decision_makers_found"] = len(people)
            print(f"  [People Found] Retrieved {len(people)} senior decision-makers")
            
            for p in people:
                p_name = p.get("name") or f"{p.get('first_name', '')} {p.get('last_name', '')}".strip() or "Anonymous"
                p_title = p.get("title") or "Executive"
                p_seniority = p.get("seniority") or "N/A"
                p_departments = ", ".join(p.get("departments", [])) if p.get("departments") else "N/A"
                p_linkedin = p.get("linkedin_url") or "N/A"
                p_city = p.get("city") or p.get("state") or p.get("country") or "N/A"
                
                # Tenure / Start date
                start_dt = "N/A"
                emp_hist = p.get("employment_history", [])
                if emp_hist and isinstance(emp_hist, list):
                    start_dt = emp_hist[0].get("start_date") or "N/A"

                dm_summary = f"{p_name} ({p_title})"
                org_record["key_decision_makers"].append(dm_summary)
                
                contact_row = {
                    "Company Name": org_record["matched_name"],
                    "Domain": c_domain,
                    "Person Name": p_name,
                    "Title": p_title,
                    "Seniority": p_seniority,
                    "Departments": p_departments,
                    "Location": p_city,
                    "LinkedIn": p_linkedin,
                    "Start Date / Tenure": start_dt,
                    "Apollo Person ID": p.get("id") or "N/A"
                }
                all_contacts.append(contact_row)
                print(f"    • {p_name} | {p_title} ({p_seniority}) | Start: {start_dt}")
        else:
            print(f"  [People Search Status {resp_peop.status_code}] {resp_peop.text[:80]}")
    except Exception as e:
        print(f"  [People Search Exception] {e}")

    time.sleep(0.3)

    # -------------------------------------------------------------
    # Step 3: Active Job Postings (if org_id found)
    # -------------------------------------------------------------
    if org_record["apollo_id"] != "N/A":
        try:
            url_jobs = f"https://api.apollo.io/api/v1/organizations/{org_record['apollo_id']}/job_postings"
            resp_jobs = requests.get(url_jobs, headers=HEADERS, timeout=10)
            if resp_jobs.ok:
                j_data = resp_jobs.json()
                job_postings = j_data.get("job_postings", [])
                org_record["active_job_postings_count"] = len(job_postings)
                org_record["active_job_titles"] = [j.get("title") for j in job_postings[:5] if j.get("title")]
                if job_postings:
                    print(f"  [Active Hiring Signal] {len(job_postings)} open jobs: {', '.join(org_record['active_job_titles'][:3])}")
        except Exception:
            pass

    results.append(org_record)
    time.sleep(0.2)

# Save JSON results
json_out = r"c:\Users\joela\OneDrive\Documents\Python\bd-engine\apollo\apollo_20co_results.json"
with open(json_out, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, default=str)
print(f"\n[SAVED JSON] -> {json_out}")

# Save CSV 1: Company Enriched Level
csv_co_out = r"c:\Users\joela\OneDrive\Documents\Python\bd-engine\apollo\apollo_20co_companies_enriched.csv"
co_fieldnames = [
    "input_name", "matched_name", "input_domain", "estimated_employees", "founded_year",
    "industry", "hq_city", "hq_country", "annual_revenue", "total_funding",
    "active_tech_stack", "active_job_postings_count", "decision_makers_found", "key_decision_makers", "linkedin_url"
]

with open(csv_co_out, "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=co_fieldnames)
    writer.writeheader()
    for r in results:
        row = {k: r.get(k) for k in co_fieldnames}
        if isinstance(row["active_tech_stack"], list):
            row["active_tech_stack"] = "; ".join(row["active_tech_stack"])
        if isinstance(row["key_decision_makers"], list):
            row["key_decision_makers"] = " | ".join(row["key_decision_makers"])
        writer.writerow(row)
print(f"[SAVED CSV] -> {csv_co_out}")

# Save CSV 2: Decision Makers Level
csv_dm_out = r"c:\Users\joela\OneDrive\Documents\Python\bd-engine\apollo\apollo_20co_decision_makers.csv"
if all_contacts:
    dm_fieldnames = list(all_contacts[0].keys())
    with open(csv_dm_out, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=dm_fieldnames)
        writer.writeheader()
        writer.writerows(all_contacts)
    print(f"[SAVED CSV] -> {csv_dm_out} ({len(all_contacts)} decision-makers)")

print("\n" + "="*70)
print("COMPLETED APOLLO 20-COMPANY RUN SUCCESSFULLY!")
print("="*70)
